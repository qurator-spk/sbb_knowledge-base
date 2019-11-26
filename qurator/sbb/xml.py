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

with warnings.catch_warnings():
    warnings.simplefilter("ignore")


def alto_iterate_string_elements(xml_file):

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

        yield content, wc, string_elem


def alto_xml_files_from_dir(source_dir):

    # Listing all sub-directories which are named with PPN
    ppn_list = os.listdir(source_dir)

    for ppn in tqdm(ppn_list):

        current_ppn_dir = os.listdir(source_dir + '/' + ppn)
        for filename in current_ppn_dir:

            if not filename.endswith(".xml"):
                continue

            yield ppn, filename


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
                    alto_iterate_string_elements(self._source_dir + '/' + self._ppn + '/' + self._filename):

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
                    print('Not found: {}, {}', self._ppn, self._filename)
                    return None, None

            ner_text = [unicodedata.normalize('NFC', w) for s in json.loads(df.text.iloc[0]) for w in s]
            ner_tags = [t for s in json.loads(df.tags.iloc[0]) for t in s]

            string_contents = []
            word_confidences = []
            string_elements = []

            for content, wc, string_elem in \
                    alto_iterate_string_elements(self._source_dir + '/' + self._ppn + '/' + self._filename):

                string_contents.append(unicodedata.normalize('NFC', content))
                word_confidences.append(wc)
                string_elements.append(string_elem)

            assert len(ner_text) >= len(string_contents)

            tagged_string_contents = []
            ner_pos = 0
            for content, wc, string_elem in zip(string_contents, word_confidences, string_elements):

                if not content.startswith(ner_text[ner_pos]):
                    continue

                ner_word = ner_text[ner_pos]
                ner_tag = {ner_tags[ner_pos]}
                ner_pos += 1

                while ner_word != content:
                    ner_word += ner_text[ner_pos]
                    ner_tag.add(ner_tags[ner_pos])
                    ner_pos += 1

                tagged_string_contents.append((content, ner_tag))

            import ipdb;ipdb.set_trace()

            return self._filename, self._ppn

        except Exception as e:

            raise e
            # print(e)
            # print(self._ppn, self._filename, self._source_dir, self._dest_dir)
            # return None, None

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

        print(ppn, filename)

        break
