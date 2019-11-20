import pandas as pd
import sqlite3
from tqdm import tqdm as tqdm
import click
import requests
import os
import json


def create_connection(db_file):

    conn = sqlite3.connect(db_file)

    conn.execute('pragma journal_mode=wal')

    return conn


@click.command()
@click.argument('fulltext-sqlite-file', type=click.Path(), required=True, nargs=1)
@click.argument('selection-file', type=click.Path(), required=True, nargs=1)
@click.argument('ner-endpoint', type=str, required=True, nargs=1)
@click.argument('tagged-sqlite-file', type=click.Path(), required=True, nargs=1)
@click.option('--chunksize', type=int, default=10**4, help='size of chunks used for processing. default: 10**4')
@click.option('--noproxy', type=bool, default=False, help='disable proxy. default: enabled.')
def on_db_file(fulltext_sqlite_file, selection_file, ner_endpoint, tagged_sqlite_file, chunksize, noproxy):
    """
    Reads the text content per page of digitalized collections from sqlite file <fulltext-sqlite-file>.
    Considers only a subset of documents that is defined by <selection-file>.
    Performs NER on the text content using the REST endpoint <ner-endpoint>.
    Writes the NER results back to another sqlite file <tagged-sqlite-file>.
    Writes results in chunks of size <chunksize>.
    Suppress proxy with --noproxy=True
    """

    if noproxy:
        os.environ['no_proxy'] = '*'

    se = pd.read_pickle(selection_file)

    se = se.loc[se.selected]

    with create_connection(fulltext_sqlite_file) as read_conn, create_connection(tagged_sqlite_file) as write_conn:

        tagged = []

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

            resp = requests.post(url=ner_endpoint, json={'text': df.text.iloc[0]})

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

            tagged.append({'id': num, 'ppn': ppn, 'filenname': row.filename, 'text': json.dumps(sentences),
                           'tags': json.dumps(tags)})

            if len(tagged) > chunksize:
                # noinspection PyTypeChecker
                df_tagged = pd.DataFrame.from_dict(tagged).reset_index(drop=True).set_index('id')

                df_tagged.to_sql('tagged', con=write_conn, if_exists='append', index_label='id')

                tagged = []

        write_conn.execute('create index idx_ppn on tagged(ppn);')

    return
