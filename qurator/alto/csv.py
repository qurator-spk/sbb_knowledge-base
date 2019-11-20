import pandas as pd
import sqlite3
from tqdm import tqdm as tqdm
import itertools
import click


def create_connection(db_file):

    conn = sqlite3.connect(db_file)

    conn.execute('pragma journal_mode=wal')

    return conn


@click.command()
@click.argument('alto-csv-file', type=click.Path(exists=True), required=True, nargs=1)
@click.argument('sqlite-file', type=click.Path(), required=True, nargs=1)
@click.option('--chunksize', default=10**4, help='size of chunks used for processing alto-csv-file. default:10**4')
def to_sqlite(alto_csv_file, sqlite_file, chunksize):
    """
    Reads the ALTO_CSV_FILE and converts it into SQLITE_FILE that can be used for more performant access.
    """

    with create_connection(sqlite_file) as conn:

        for ch, count in zip(tqdm(pd.read_csv(alto_csv_file, chunksize=chunksize)), itertools.count()):
            ch_text = ch.loc[:, ['file_name', 'ppn', 'text']]

            ch_text['id'] = [i for i in range(count * chunksize, count * chunksize + len(ch_text))]

            ch_text = ch_text.reset_index(drop=True).set_index('id')

            ch_text.to_sql('text', con=conn, if_exists='append', index_label='id')

        conn.execute('create index idx_ppn on text(ppn);')

    return
