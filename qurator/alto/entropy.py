import numpy as np
import pandas as pd
from tqdm import tqdm as tqdm
import click
from collections import Counter
import os
import sqlite3
from qurator.utils.parallel import run as prun


class EntropyTask:

    def __init__(self, chunk):

        self._chunk = chunk

    def __call__(self, *args, **kwargs):

        result = list()

        for i, r in self._chunk.iterrows():

            if type(r.text) != str:
                continue

            text = str(r.text)

            prob = {k: v / len(text) for k, v in Counter(text).items()}

            entropy = -1.0/len(text)*np.sum([prob[c] * np.log2(prob[c]) for c in text])

            ppn = r.ppn if str(r.ppn).startswith('PPN') else 'PPN' + r.ppn

            filename = str(r['file name'])

            result.append((ppn, filename, entropy))

        return pd.DataFrame(result, columns=['ppn', 'filename', 'entropy'])


def get_csv_chunks(alto_csv_file, chunksize):

    for ch in tqdm(pd.read_csv(alto_csv_file, chunksize=chunksize)):

        yield ch


def get_sqlite_chunks(alto_sqlite_file, chunksize):

    yield pd.DataFrame()

    with sqlite3.connect(alto_sqlite_file) as conn:

        conn.execute('pragma journal_mode=wal')

        total = int(conn.execute('select count(*) from text;').fetchone()[0] / chunksize)

        for ch in tqdm(pd.read_sql('select * from text', conn, chunksize=chunksize), total=total):

            yield ch


def get_chunk_tasks(chunks):

    for chunk in chunks:

        if len(chunk) == 0:
            continue

        yield EntropyTask(chunk)


@click.command()
@click.argument('alto-fulltext-file', type=click.Path(exists=True), required=True, nargs=1)
@click.argument('entropy-file', type=click.Path(), required=True, nargs=1)
@click.option('--chunksize', default=10**4, help='size of chunks used for processing alto-csv-file')
@click.option('--processes', default=6, help='number of parallel processes')
def main(alto_fulltext_file, entropy_file, chunksize, processes):
    """
    Read the documents of the corpus from <alto-csv-file> where each line of the .csv file describes one document.
    Foreach document compute its character entropy rate and store the result as a pickled pandas DataFrame
    in <entropy-file>.
    """

    os.makedirs(os.path.dirname(entropy_file), exist_ok=True)

    if alto_fulltext_file.endswith('.csv'):
        chunks = get_csv_chunks(alto_fulltext_file, chunksize)
    elif alto_fulltext_file.endswith('.sqlite3'):
        chunks = get_sqlite_chunks(alto_fulltext_file, chunksize)
    else:
        raise RuntimeError('Unsupported input file format.')

    entropy = list()
    for et in prun(get_chunk_tasks(chunks), processes=processes):

        entropy.append(et)

    entropy = pd.concat(entropy, axis=0)

    entropy.to_pickle(entropy_file)

    return


if __name__ == '__main__':
    main()
