import pandas as pd
import sqlite3
from tqdm import tqdm as tqdm
import itertools
import click


@click.command()
@click.argument('csv-file', type=click.Path(exists=True), required=True, nargs=1)
@click.argument('sqlite-file', type=click.Path(), required=True, nargs=1)
@click.argument('table', type=str, required=True, nargs=1)
@click.argument('columns', type=str, required=False, nargs=-1)
@click.option('--chunksize', default=10**4, help='size of chunks used for processing alto-csv-file. default:10**4')
@click.option('--index-on', type=str, default=None, help='Create an additional SQL index for this column.')
def to_sqlite(csv_file, sqlite_file, table, columns, chunksize, index_on):
    """
    Reads the CSV_FILE and converts it into SQLITE_FILE that can be used for faster access.

    TABLE: Write the CSV data into table <TABLE>.

    [COLUMNS]: If provided, defines a subset of CSV columns that is to be considered.
    """

    with sqlite3.connect(sqlite_file) as conn:

        conn.execute('pragma journal_mode=wal')

        for ch, count in zip(tqdm(pd.read_csv(csv_file, chunksize=chunksize)), itertools.count()):

            if len(columns) > 0:
                ch_text = ch.loc[:, columns]

            ch_text['id'] = [i for i in range(count * chunksize, count * chunksize + len(ch_text))]

            ch_text = ch_text.reset_index(drop=True).set_index('id')

            ch_text.to_sql(table, con=conn, if_exists='append', index_label='id')

        if index_on is not None:
            conn.execute('create index idx_{} on {}({});'.format(index_on, table, index_on))
