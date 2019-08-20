import re
import pandas as pd
from tqdm import tqdm as tqdm
import click
import codecs
import os

from qurator.utils.parallel import run as prun


class ChunkTask:

    selection = None

    def __init__(self, chunk, min_line_len):

        self._chunk = chunk
        self._min_line_len = min_line_len

    def __call__(self, *args, **kwargs):

        return ChunkTask.reformat_chunk(self._chunk, self._min_line_len)

    @staticmethod
    def reformat_chunk(chunk, min_line_len):
        """
        Process a chunk of documents.

        :param chunk: pandas DataFrame that contains one document per row.
        :param min_line_len: Break the document text up in lines that have this minimum length.
        :return: One big text where the documents are separated by an empty line.
        """

        text = ''

        for i, r in chunk.iterrows():

            if type(r.text) != str:
                continue

            ppn = r.ppn if str(r.ppn).startswith('PPN') else 'PPN' + r.ppn

            filename = str(r['file name'])

            if not ChunkTask.selection.loc[(ppn, filename)].selected.iloc[0]:
                continue

            for se in sentence_split(str(r.text), min_line_len):

                text += se

            text += '\n\n'

        return text

    @staticmethod
    def initialize(selection_file):

        ChunkTask.selection = \
            pd.read_pickle(selection_file).\
                reset_index().\
                set_index(['ppn', 'filename']).\
                sort_index()


def get_chunks(alto_csv_file, chunksize):

    for ch in tqdm(pd.read_csv(alto_csv_file, chunksize=chunksize)):

        yield ch


def get_chunk_tasks(chunks, min_len_len):

    for chunk in chunks:

        yield ChunkTask(chunk, min_len_len)


def sentence_split(s, min_len):
    """
    Reformat text of an entire document such that each line has at least length min_len
    :param s: str
    :param min_len: minimum line length
    :return: reformatted text
    """

    parts = s.split(' ')

    se = ''
    for p in parts:

        se += ' ' + p

        if len(se) > min_len and len(p) > 2 and re.match(r'.*([^0-9])[.]$', p):
            yield se + '\n'
            se = ''

    yield se + '\n'


@click.command()
@click.argument('alto-csv-file', type=click.Path(exists=True), required=True, nargs=1)
@click.argument('selection-file', type=click.Path(exists=True), required=True, nargs=1)
@click.argument('corpus-file', type=click.Path(), required=True, nargs=1)
@click.option('--chunksize', default=10**4)
@click.option('--processes', default=6)
@click.option('--min-line-len', default=80)
def main(alto_csv_file, selection_file, corpus_file, chunksize, processes, min_line_len):

    os.makedirs(os.path.dirname(corpus_file), exist_ok=True)

    print('Open {}.'.format(corpus_file))
    corpus_fh = codecs.open(corpus_file, 'w+', 'utf-8')
    corpus_fh.write(u'\ufeff')

    for text in prun(get_chunk_tasks(get_chunks(alto_csv_file, chunksize), min_line_len),
                     processes=processes, initializer=ChunkTask.initialize, initargs=(selection_file,)):

        corpus_fh.write(text)

    corpus_fh.close()

    return


if __name__ == '__main__':
    main()




