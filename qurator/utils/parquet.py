import pandas as pd
import dask.dataframe as dd
import click
from tqdm import tqdm


@click.command()
@click.argument('parquet-file', type=click.Path(exists=True), required=True, nargs=1)
@click.argument('csv-file', type=click.Path(exists=False), required=True, nargs=1)
@click.option('--chunk-size', type=int, default=10**5, required=False, nargs=1,
              help="Perform conversion in chunks of size chunk-size. default: 10**5 ")
@click.option('--sep', type=str, default=";", required=False, nargs=1, help="CSV seperator. default: ;")
def to_csv(parquet_file, csv_file, chunk_size, sep):
    """
    Reads a Apache parquet file and converts it into a CSV file.

    PARQUET_FILE: Read from.

    CSV_FILE: Write to.
    """

    df = dd.read_parquet(parquet_file)

    chunk = list()

    for idx, row in tqdm(df.iterrows()):

        chunk.append(row)

        if len(chunk) > chunk_size:
            chunk = pd.DataFrame(chunk)

            chunk.to_csv(csv_file, mode='a', sep=sep)

            chunk = list()

    if len(chunk) > 0:
        chunk = pd.DataFrame(chunk)

        chunk.to_csv(csv_file, mode='a', sep=sep)
