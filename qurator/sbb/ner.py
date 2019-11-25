import pandas as pd
import sqlite3
from tqdm import tqdm as tqdm
import click
import requests
import os
import json
from qurator.utils.parallel import run as prun


def create_connection(db_file):

    conn = sqlite3.connect(db_file)

    conn.execute('pragma journal_mode=wal')

    return conn


class NERTask:

    def __init__(self, num, ppn, file_name, fulltext, ner_endpoint):

        self._num = num
        self._ppn = ppn
        self._file_name = file_name
        self._fulltext = fulltext
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

        return self._num, self._ppn, self._file_name, json.dumps(sentences), json.dumps(tags)

    @staticmethod
    def get_all(fulltext_sqlite_file, selection_file, ner_endpoint):

        se = pd.read_pickle(selection_file)

        se = se.loc[se.selected]

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

                yield NERTask(num, ppn, row.filename, df.text.iloc[0], ner_endpoint[num % len(ner_endpoint)])


@click.command()
@click.argument('fulltext-sqlite-file', type=click.Path(), required=True, nargs=1)
@click.argument('selection-file', type=click.Path(), required=True, nargs=1)
@click.argument('tagged-sqlite-file', type=click.Path(), required=True, nargs=1)
@click.argument('ner-endpoint', type=str, required=True, nargs=-1)
@click.option('--chunksize', type=int, default=10**4, help='size of chunks used for processing. default: 10**4')
@click.option('--noproxy', type=bool, default=False, help='disable proxy. default: enabled.')
def on_db_file(fulltext_sqlite_file, selection_file, tagged_sqlite_file, ner_endpoint, chunksize, noproxy):
    """
    Reads the text content per page of digitalized collections from sqlite file <fulltext-sqlite-file>.
    Considers only a subset of documents that is defined by <selection-file>.
    Performs NER on the text content using the REST endpoint <ner-endpoint>.
    Writes the NER results back to another sqlite file <tagged-sqlite-file>.
    Writes results in chunks of size <chunksize>.
    Suppress proxy with --noproxy=True
    """

    print(ner_endpoint)

    if noproxy:
        os.environ['no_proxy'] = '*'

    with create_connection(tagged_sqlite_file) as write_conn:

        tagged = []

        for num, ppn, file_name, text, tags in\
            prun(NERTask.get_all(fulltext_sqlite_file, selection_file, ner_endpoint),
                 processes=len(ner_endpoint)):

            tagged.append({'id': num, 'ppn': ppn, 'file_name': file_name, 'text': text, 'tags': tags})

            if len(tagged) > chunksize:
                # noinspection PyTypeChecker
                df_tagged = pd.DataFrame.from_dict(tagged).reset_index(drop=True).set_index('id')

                df_tagged.to_sql('tagged', con=write_conn, if_exists='append', index_label='id')

                tagged = []

        write_conn.execute('create index idx_ppn on tagged(ppn);')

    return
