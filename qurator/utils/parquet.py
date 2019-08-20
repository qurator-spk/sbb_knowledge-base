import pandas as pd
import dask.dataframe as dd
import click
from tqdm import tqdm


@click.command()
@click.argument('parquet-file', type=click.Path(exists=True), required=True, nargs=1)
@click.argument('csv-file', type=click.Path(exists=False), required=True, nargs=1)
@click.argument('chunk-size', type=int, default=100000, required=False, nargs=1)
@click.argument('sep', type=str, default=";", required=False, nargs=1)
def to_csv(parquet_file, csv_file, chunk_size, sep):

    df = dd.read_parquet(parquet_file)

    chunk = list()

    for _, row in tqdm(df.reset_index().iterrows()):

        chunk.append(row)

        if len(chunk) > chunk_size:
            chunk = pd.DataFrame(chunk)

            chunk.to_csv(csv_file, mode='a', sep=sep)

            chunk = list()

    if len(chunk) > 0:
        chunk = pd.DataFrame(chunk)

        chunk.to_csv(csv_file, mode='a', sep=sep)
