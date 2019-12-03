import pandas as pd
import sqlite3
from tqdm import tqdm as tqdm
import click
import requests
import os
from flask import json
from qurator.utils.parallel import run as prun
import unicodedata
import logging

logger = logging.getLogger(__name__)


def create_connection(db_file):

    conn = sqlite3.connect(db_file)

    conn.execute('pragma journal_mode=wal')

    return conn


class NERTask:

    def __init__(self, num, ppn, file_name, fulltext, ner_endpoint):

        self._num = num
        self._ppn = ppn
        self._file_name = file_name
        self._fulltext = "" if fulltext is None else fulltext
        self._ner_endpoint = ner_endpoint

    def __call__(self, *args, **kwargs):

        resp = requests.post(url=self._ner_endpoint, json={'text': self._fulltext})

        result_sentences = json.loads(resp.content)

        sentences = []
        tags = []

        for rsen in result_sentences:

            sen = []
            ta = []

            for part in rsen:
                sen.append(part['word'])
                ta.append(part['prediction'])

            sentences.append(sen)
            tags.append(ta)

        original_text = unicodedata.normalize('NFC', self._fulltext.replace(" ", ""))

        received_text = unicodedata.normalize('NFC',
                                              "".join([pred['word'] for rsen in result_sentences for pred in rsen]).
                                              replace(" ", ""))

        return self._num, self._ppn, self._file_name, json.dumps(sentences), json.dumps(tags), original_text, \
               received_text

    @staticmethod
    def get_all(fulltext_sqlite_file, selection_file, ner_endpoint, start_row):

        se = pd.read_pickle(selection_file)

        se = se.loc[start_row:].loc[se.selected]

        with create_connection(fulltext_sqlite_file) as read_conn:

            for num, (idx, row) in enumerate(tqdm(se.iterrows(), total=len(se))):

                if row.ppn.startswith('PPN'):
                    ppn = row.ppn[3:]

                df = pd.read_sql_query("select file_name, text from text where ppn=? and file_name=?;", read_conn,
                                       params=(ppn, row.filename))

                if len(df) == 0:

                    ppn = row.ppn

                    df = pd.read_sql_query("select file_name, text from text where ppn=? and file_name=?;", read_conn,
                                           params=(ppn, row.filename))

                    if len(df) == 0:
                        print("PPN {} with file {} not found!!!".format(ppn, row.filename))
                        continue

                yield NERTask(idx, ppn, row.filename, df.text.iloc[0], ner_endpoint[num % len(ner_endpoint)])


@click.command()
@click.argument('fulltext-sqlite-file', type=click.Path(), required=True, nargs=1)
@click.argument('selection-file', type=click.Path(), required=True, nargs=1)
@click.argument('model-name', type=str, required=True, nargs=1)
@click.argument('ner-endpoint', type=str, required=True, nargs=-1)
@click.option('--chunksize', type=int, default=10**4, help='size of chunks used for processing. default: 10**4')
@click.option('--noproxy', is_flag=True, help='disable proxy. default: enabled.')
@click.option('--processes', type=int, default=None)
@click.option('--outfile', type=click.Path(), default=None)
def on_db_file(fulltext_sqlite_file, selection_file, model_name, ner_endpoint, chunksize, noproxy,
               processes, outfile):
    """
    Reads the text content per page of digitalized collections from sqlite file <fulltext-sqlite-file>.
    Considers only a subset of documents that is defined by <selection-file>.
    Performs NER on the text content using the REST endpoint[s] <ner-endpoint ...>.
    Writes the NER results back to another sqlite file <tagged-sqlite-file>.
    Writes results in chunks of size <chunksize>.
    Suppress proxy with --noproxy=True
    """

    if noproxy:
        os.environ['no_proxy'] = '*'

    logging.info('Using endpoints: {}'.format(ner_endpoint))

    model_name = model_name.replace(" ", "")

    ner_endpoint_tmp = []
    for endpoint in ner_endpoint:

        models = json.loads(requests.get("{}/models".format(endpoint)).content)

        models = pd.DataFrame.from_dict(models)[['name', 'id']]

        models['name'] = models['name'].str.replace(" ", "")

        models = models.set_index('name')

        ner_endpoint_tmp.append("{}/ner/{}".format(endpoint, models.loc[model_name]['id']))

    ner_endpoint = ner_endpoint_tmp

    if outfile is None:
        tagged_sqlite_file = os.path.splitext(
            os.path.basename(fulltext_sqlite_file))[0] + "-ner-" + model_name + ".sqlite3"
    else:
        tagged_sqlite_file = outfile

    start_row = 0
    if os.path.exists(tagged_sqlite_file):

        with create_connection(tagged_sqlite_file) as read_conn:

            start_row = read_conn.execute('select max(id) from tagged').fetchone()[0] + 1

            logger.info('Starting from idx: {}'.format(start_row))

    with create_connection(tagged_sqlite_file) as write_conn:

        tagged = []

        for num, ppn, file_name, text, tags, original_text, received_text in\
            prun(NERTask.get_all(fulltext_sqlite_file, selection_file, ner_endpoint, start_row),
                 processes=len(ner_endpoint) if processes is None else processes):

            tagged.append({'id': num, 'ppn': ppn, 'file_name': file_name, 'text': text, 'tags': tags})

            try:
                assert original_text == received_text
            except AssertionError:
                logging.warning('PPN: {}, file_name: {}\n\n\nInput and output differ:\n\nInput: {}\n\nOutput:{}'.
                                format(ppn, file_name, original_text, received_text))

            if len(tagged) > chunksize:
                # noinspection PyTypeChecker
                df_tagged = pd.DataFrame.from_dict(tagged).reset_index(drop=True).set_index('id')

                df_tagged.to_sql('tagged', con=write_conn, if_exists='append', index_label='id')

                tagged = []

        if len(tagged) > 0:
            # noinspection PyTypeChecker
            df_tagged = pd.DataFrame.from_dict(tagged).reset_index(drop=True).set_index('id')

            df_tagged.to_sql('tagged', con=write_conn, if_exists='append', index_label='id')

        try:
            write_conn.execute('create index idx_ppn on tagged(ppn);')
        except sqlite3.OperationalError:
            pass

    return


@click.command()
@click.argument('ner-endpoint', type=str, required=True, nargs=-1)
@click.option('--noproxy', type=bool, is_flag=True, help='disable proxy. default: enabled.')
def show_models(ner_endpoint, noproxy):

    if noproxy:
        os.environ['no_proxy'] = '*'

    for endpoint in ner_endpoint:

        models = json.loads(requests.get("{}/models".format(endpoint)).content)

        models = pd.DataFrame.from_dict(models).set_index('id')[['name']]

        models['name'] = models['name'].str.replace(" ", "")

        print("\n{}:".format(endpoint))
        print(models)
        print('\n\n')
