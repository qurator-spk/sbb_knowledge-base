import pandas as pd
from tqdm import tqdm as tqdm
import click
import os

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
            filename = str(r['file name'])

            lang, conf = LanguageTask.identifier.classify(str(r.text))

            result.append((ppn, filename, lang, conf))

        return pd.DataFrame(result, columns=['ppn', 'filename', 'language', 'confidence'])

    @staticmethod
    def initialize():

        LanguageTask.identifier = LanguageIdentifier.from_modelstring(model, norm_probs=True)


def get_chunks(alto_csv_file, chunksize):

    for ch in tqdm(pd.read_csv(alto_csv_file, chunksize=chunksize)):

        yield ch


def get_chunk_tasks(chunks):

    for chunk in chunks:

        yield LanguageTask(chunk)


@click.command()
@click.argument('alto-csv-file', type=click.Path(exists=True), required=True, nargs=1)
@click.argument('language-file', type=click.Path(), required=True, nargs=1)
@click.option('--chunksize', default=10**4, help='size of chunks used for processing alto-csv-file')
@click.option('--processes', default=6, help='number of parallel processes')
def main(alto_csv_file, language_file, chunksize, processes):
    """
    Read the documents of the corpus from <alto-csv-file> where each line of the .csv file describes one document.
    Foreach document classify its language by means of langid.
    Store the classification results as a pickled pandas DataFrame in <language-file>.
    """

    target_path = os.path.dirname(language_file)

    if not os.path.exists(target_path):
        os.makedirs(target_path, exist_ok=True)

    language = list()
    for lan in prun(get_chunk_tasks(get_chunks(alto_csv_file, chunksize)), processes=processes,
                    initializer=LanguageTask.initialize):

        language.append(lan)

    language = pd.concat(language, axis=0)

    language.to_pickle(language_file)

    return


if __name__ == '__main__':
    main()




