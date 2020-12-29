import pandas as pd
import sqlite3
import click


@click.command()
@click.argument('df-file', type=click.Path(exists=True), required=True, nargs=1)
@click.argument('sqlite-file', type=click.Path(), required=True, nargs=1)
@click.argument('table-name', type=str, required=True, nargs=1)
def to_sqlite(df_file, sqlite_file, table_name):

    df = pd.read_pickle(df_file)

    with sqlite3.connect(sqlite_file) as conn:

        df.to_sql(name=table_name, con=conn, if_exists='replace')
