import os
import numpy as np
import warnings
import xml.etree.ElementTree as ElementTree
from tqdm import tqdm
import csv
import click
import sqlite3
import pandas as pd
import json
import unicodedata
from qurator.utils.parallel import run as prun
import logging

with warnings.catch_warnings():
    warnings.simplefilter("ignore")

logger = logging.getLogger(__name__)


def alto_iterate_string_elements(xml_file=None, root=None):

    if root is None:
        tree = ElementTree.parse(xml_file)
        root = tree.getroot()

    for string_elem in root.iter('{http://www.loc.gov/standards/alto/ns-v2#}String'):
        if 'WC' in string_elem.attrib:
            wc = string_elem.attrib['WC']
        else:
            wc = str(np.NAN)

        if 'CONTENT' in string_elem.attrib:
            content = string_elem.attrib['CONTENT']
        else:
            content = str(np.NAN)

        yield unicodedata.normalize('NFC', content), wc, string_elem


def alto_xml_files_from_dir(source_dir):

    # Listing all sub-directories which are named with PPN
    ppn_list = os.listdir(source_dir)

    for ppn in tqdm(ppn_list):

        current_ppn_dir = os.listdir(source_dir + '/' + ppn)
        for filename in current_ppn_dir:

            if not filename.endswith(".xml"):
                continue

            yield ppn, filename


def alto_add_entity_map(root, entity_map):

    if len(entity_map) == 0:
        return

    root.attrib['{http://www.w3.org/2001/XMLSchema-instance}schemaLocation'] = \
        'http://www.loc.gov/standards/alto/ns-v2# http://www.loc.gov/standards/alto/alto.xsd'

    tags = ElementTree.Element('ns0:Tags')

    layout = root.find('.//{http://www.loc.gov/standards/alto/ns-v2#}Layout')

    if layout is None:
        return

    tags_pos = [c for c in root.getchildren()].index(layout)

    root.insert(tags_pos, tags)

    for entity_id, (entity_label, entity_type) in entity_map.items():
        named_entity_elem = ElementTree.Element('ns0:NamedEntityTag')

        try:
            assert entity_type in {'PER', 'LOC', 'ORG'}
        except AssertionError:
            import ipdb;ipdb.set_trace()

        named_entity_elem.set('ID', entity_type + str(entity_id))
        named_entity_elem.set('LABEL', entity_label)

        tags.append(named_entity_elem)


def alto_add_entity_references(entity_map, tagged_contents):

    for string_elem, entity_id in tagged_contents:

        if entity_id is None:
            continue

        entity_label, entity_type = entity_map[entity_id]

        try:
            assert entity_type in {'PER', 'LOC', 'ORG'}
        except AssertionError:
            import ipdb;ipdb.set_trace()

        string_elem.set('TAGREFS', entity_type + str(entity_id))


class ExtractTask:

    def __init__(self, source_dir, ppn,  filename):

        self._source_dir = source_dir
        self._ppn = ppn
        self._filename = filename

    def __call__(self, *args, **kwargs):

        try:
            string_contents = []
            word_confidences = []

            for content, wc, _ in \
                    alto_iterate_string_elements(xml_file=self._source_dir + '/' + self._ppn + '/' + self._filename):

                string_contents.append(content)
                word_confidences.append(wc)

            return self._filename, " ".join(string_contents), json.dumps(word_confidences), self._ppn

        except Exception as e:
            print(e)
            print(self._ppn, self._filename, self._source_dir)
            return None, None, None, None

    @staticmethod
    def get_all(source_dir):

        for ppn, filename in alto_xml_files_from_dir(source_dir):

            yield ExtractTask(source_dir, ppn, filename)


def to_csv(source_dir, output_file, processes):

    with open(output_file, 'w') as f:
        writer = csv.writer(f)
        writer.writerow(['file_name', 'text', 'wc', 'ppn'])

        for filename, text, wc, ppn in prun(ExtractTask.get_all(source_dir), processes=processes):

            if filename is None:
                continue

            writer.writerow([filename, text, wc, ppn])


def to_sqlite(source_dir, output_file, processes):

    with sqlite3.connect(output_file) as conn:

        conn.execute('pragma journal_mode=wal')

        for idx, (filename, text, wc, ppn) in\
                enumerate(prun(ExtractTask.get_all(source_dir), processes=processes)):

            if filename is None:
                continue

            pd.DataFrame({'id': idx, 'file_name': filename, 'text': text, 'wc': wc, 'ppn': ppn}, index=[idx]).\
                reset_index(drop=True).set_index('id').\
                to_sql('text', con=conn, if_exists='append', index_label='id')

        conn.execute('create index idx_ppn on text(ppn);')


@click.command()
@click.argument('source-dir', type=click.Path(), required=True, nargs=1)
@click.argument('output-file', type=click.Path(), required=True, nargs=1)
@click.option('--processes', default=6, help='number of parallel processes')
def altotool(source_dir, output_file, processes):
    """
    Extract text from a bunch of alto XML files into one big CSV(.csv) or SQLITE3(.sqlite3) file.

    SOURCE_DIR: The directory that contains subfolders with the ALTO xml files.
    OUTPUT_FILE: Write the extracted fulltext to this file (either .csv or .sqlite3).
    """

    if output_file.endswith('.sqlite3'):
        to_sqlite(source_dir, output_file, processes)
    elif output_file.endswith('.csv'):
        to_csv(source_dir, output_file, processes)
    else:
        raise RuntimeError("Output format not supported.")

###################################


class AnnotateTask:

    conn = None

    def __init__(self, source_dir, dest_dir, ppn,  filename):

        self._source_dir = source_dir
        self._dest_dir = dest_dir
        self._ppn = ppn
        self._filename = filename

    def __call__(self, *args, **kwargs):

        try:
            df = pd.read_sql_query("select text, tags from tagged where ppn=? and file_name=?;", AnnotateTask.conn,
                                   params=(self._ppn, self._filename))
            if len(df) == 0:
                self._ppn = 'PPN' + self._ppn

                df = pd.read_sql_query("select text, tags from tagged where ppn=? and file_name=?;", AnnotateTask.conn,
                                       params=(self._ppn, self._filename))

                if len(df) == 0:
                    logger.info('Not found: {}, {}'.format(self._ppn, self._filename))
                    return None, None

            tree = ElementTree.parse(self._source_dir + '/' + self._ppn + '/' + self._filename)
            root = tree.getroot()

            entity_list, tagged_contents = AnnotateTask.tag_content(root, df)

            entity_map, tagged_contents = AnnotateTask.remap_entities(entity_list, tagged_contents)

            alto_add_entity_map(root, entity_map)

            alto_add_entity_references(entity_map, tagged_contents)

            ppn_path = self._dest_dir + '/' + self._ppn
            if not os.path.exists(ppn_path):
                os.makedirs(ppn_path, exist_ok=True)

            tree.write(ppn_path + '/' + self._filename)

            return self._filename, self._ppn

        except Exception as exx:
            import ipdb;ipdb.set_trace()

            logger.error(exx)

    @staticmethod
    def tag_content(root, ner_data):

        entity_list = list()

        def iterate_ner_tags():

            nonlocal entity_list

            _text = json.loads(ner_data.text.iloc[0])
            _tags = json.loads(ner_data.tags.iloc[0])

            eid = 0
            for sen_tok, sen_tag in zip(_text, _tags):
                entity = list()
                entity_type = set()
                for tok, tag in zip(sen_tok, sen_tag):

                    assert len(entity_type) < 2

                    tag = 'O' if tag == 'O' else tag[2:]

                    try:
                        assert tag in {'O', 'PER', 'LOC', 'ORG'}
                    except AssertionError:
                        import ipdb;
                        ipdb.set_trace()

                    if len(entity) > 0 and tag not in entity_type:
                        entity_list[-1] = (eid, " ".join(entity), list(entity_type)[0])
                        eid += 1
                        entity = list()
                        entity_type = set()

                    if tag != 'O':
                        if len(entity) == 0:
                            entity_list.append((eid, "", None))

                        entity += [tok]
                        entity_type.add(tag)

                        entity_list[-1] = (eid, " ".join(entity), list(entity_type)[0])

                    yield unicodedata.normalize('NFC', tok), eid if tag != 'O' else None

        ner_sequence = iterate_ner_tags()
        tagged_contents = []
        ner_concat = ''
        for content, wc, string_elem in alto_iterate_string_elements(root=root):

            entity_ids = set()
            while content != ner_concat:

                assert len(content) >= len(ner_concat)

                ner_text, entity_id = next(ner_sequence)

                ner_concat += ner_text

                if entity_id is not None:
                    entity_ids.add(entity_id)

            tagged_contents.append((string_elem, entity_ids))
            ner_concat = ''

        return entity_list, tagged_contents

    @staticmethod
    def remap_entities(entity_list, tagged_contents):

        entity_label_to_id = dict()
        entity_map = dict()

        id_map = dict()
        for entity_id, entity_label, entity_type in entity_list:

            if entity_label in entity_label_to_id:
                id_map[entity_id] = entity_label_to_id[entity_label]
            else:
                entity_label_to_id[entity_label] = entity_id
                id_map[entity_id] = entity_id

                entity_map[entity_id] = (entity_label, entity_type)

        tagged_contents_tmp = []
        for string_elem, entity_ids in tagged_contents:

            if len(entity_ids) == 0 or len(entity_ids) > 1:
                tagged_contents_tmp.append((string_elem, None))
                continue

            entity_id = list(entity_ids)[0]

            tagged_contents_tmp.append((string_elem, id_map[entity_id]))

        return entity_map, tagged_contents_tmp

    @staticmethod
    def initialize(tagged_sqlite_file):

        AnnotateTask.conn = sqlite3.connect(tagged_sqlite_file)

        AnnotateTask.conn.execute('pragma journal_mode=wal')

    @staticmethod
    def get_all(source_dir, dest_dir):

        for ppn, filename in alto_xml_files_from_dir(source_dir):

            yield AnnotateTask(source_dir, dest_dir, ppn, filename)


@click.command()
@click.argument('tagged-sqlite-file', type=click.Path(), required=True, nargs=1)
@click.argument('source-dir', type=click.Path(), required=True, nargs=1)
@click.argument('dest-dir', type=click.Path(), required=True, nargs=1)
@click.option('--processes', default=0, help='number of parallel processes')
def altoannotator(tagged_sqlite_file, source_dir, dest_dir, processes):

    if not os.path.exists(dest_dir):

        os.mkdir(dest_dir)

    for ppn, filename, in prun(AnnotateTask.get_all(source_dir, dest_dir), processes=processes,
                               initializer=AnnotateTask.initialize, initargs=(tagged_sqlite_file,)):
        if ppn is None:
            continue

        # print(ppn, filename)
