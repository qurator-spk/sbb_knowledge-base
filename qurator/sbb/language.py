import pandas as pd
from tqdm import tqdm as tqdm
import click
import os
import sqlite3

from qurator.utils.parallel import run as prun
from langid.langid import LanguageIdentifier, model


class LanguageTask:

    identifier = None

    def __init__(self, chunk):

        self._chunk = chunk

    def __call__(self, *args, **kwargs):

        result = list()

        for i, r in self._chunk.iterrows():

            if type(r.text) != str:
                continue

            ppn = r.ppn if str(r.ppn).startswith('PPN') else 'PPN' + r.ppn
            filename = str(r['file_name'])

            lang, conf = LanguageTask.identifier.classify(str(r.text))

            result.append((ppn, filename, lang, conf))

        return pd.DataFrame(result, columns=['ppn', 'filename', 'language', 'confidence'])

    @staticmethod
    def initialize():

        LanguageTask.identifier = LanguageIdentifier.from_modelstring(model, norm_probs=True)


def get_csv_chunks(alto_csv_file, chunksize):

    for ch in tqdm(pd.read_csv(alto_csv_file, chunksize=chunksize)):

        if len(ch) == 0:
            continue

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

        yield LanguageTask(chunk)


@click.command()
@click.argument('alto-fulltext-file', type=click.Path(exists=True), required=True, nargs=1)
@click.argument('language-file', type=click.Path(), required=True, nargs=1)
@click.option('--chunksize', default=10**4, help='size of chunks used for processing alto-csv-file')
@click.option('--processes', default=6, help='number of parallel processes. default: 6.')
def main(alto_fulltext_file, language_file, chunksize, processes):
    """
    Read the documents of the corpus from ALTO_FULLTEXT_FILE where each line of the .csv file
    describes one page.

    Foreach page classify its language by means of langid.
    Store the classification results as a pickled pandas DataFrame in LANGUAGE_FILE.
    """

    target_path = os.path.dirname(language_file)

    if len(target_path) > 0 and not os.path.exists(target_path):
        os.makedirs(target_path, exist_ok=True)

    if alto_fulltext_file.endswith('.csv'):
        chunks = get_csv_chunks(alto_fulltext_file, chunksize)
    elif alto_fulltext_file.endswith('.sqlite3'):
        chunks = get_sqlite_chunks(alto_fulltext_file, chunksize)
    else:
        raise RuntimeError('Unsupported input file format.')

    language = list()
    for lan in prun(get_chunk_tasks(chunks), processes=processes,
                    initializer=LanguageTask.initialize):

        language.append(lan)

    language = pd.concat(language, axis=0)

    language.to_pickle(language_file)

    return


if __name__ == '__main__':
    main()




