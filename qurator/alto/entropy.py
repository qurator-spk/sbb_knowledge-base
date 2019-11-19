import numpy as np
import pandas as pd
from tqdm import tqdm as tqdm
import click
from collections import Counter
import os
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


def get_chunks(alto_csv_file, chunksize):

    for ch in tqdm(pd.read_csv(alto_csv_file, chunksize=chunksize)):

        yield ch


def get_chunk_tasks(chunks):

    for chunk in chunks:

        yield EntropyTask(chunk)


@click.command()
@click.argument('alto-csv-file', type=click.Path(exists=True), required=True, nargs=1)
@click.argument('entropy-file', type=click.Path(), required=True, nargs=1)
@click.option('--chunksize', default=10**4, help='size of chunks used for processing alto-csv-file')
@click.option('--processes', default=6, help='number of parallel processes')
def main(alto_csv_file, entropy_file, chunksize, processes):
    """
    Read the documents of the corpus from <alto-csv-file> where each line of the .csv file describes one document.
    Foreach document compute its character entropy rate and store the result as a pickled pandas DataFrame
    in <entropy-file>.
    """

    os.makedirs(os.path.dirname(entropy_file), exist_ok=True)

    entropy = list()
    for et in prun(get_chunk_tasks(get_chunks(alto_csv_file, chunksize)), processes=processes):

        entropy.append(et)

    entropy = pd.concat(entropy, axis=0)

    entropy.to_pickle(entropy_file)

    return


if __name__ == '__main__':
    main()
