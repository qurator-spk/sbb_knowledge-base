import os
import numpy as np
import warnings
import xml.etree.ElementTree as ElementTree
from tqdm import tqdm
import csv
import click
import sqlite3
import pandas as pd
import json
from qurator.utils.parallel import run as prun

with warnings.catch_warnings():
    warnings.simplefilter("ignore")


class ExtractTask:

    def __init__(self, source_dir, ppn,  filename):

        self._source_dir = source_dir
        self._ppn = ppn
        self._filename = filename

    def __call__(self, *args, **kwargs):

        try:
            tree = ElementTree.parse(self._source_dir + '/' + self._ppn + '/' + self._filename)
            root = tree.getroot()

            text_s = []
            wc_s = []

            for str_ind in root.iter('{http://www.loc.gov/standards/alto/ns-v2#}String'):
                if 'WC' in str_ind.attrib:
                    wc_s.append(str_ind.attrib['WC'])
                else:
                    wc_s.append(str(np.NAN))

                if 'CONTENT' in str_ind.attrib:
                    text_s.append(str_ind.attrib['CONTENT'])
                else:
                    text_s.append(str(np.NAN))

            return self._filename, " ".join(text_s), json.dumps(wc_s), self._ppn

        except Exception as e:
            print(e)
            print(self._ppn, self._filename, self._source_dir)
            return None, None, None, None

    @staticmethod
    def get_all(source_dir):

        # Listing all sub-directories which are named with PPN
        ppn_list = os.listdir(source_dir)

        for ppn in tqdm(ppn_list):

            current_ppn_dir = os.listdir(source_dir + '/' + ppn)
            for filename in current_ppn_dir:

                if not filename.endswith(".xml"):
                    continue

                yield ExtractTask(source_dir, ppn, filename)


def to_csv(source_dir, output_file, processes):

    with open(output_file, 'w') as f:
        writer = csv.writer(f)
        writer.writerow(['file_name', 'text', 'wc', 'ppn'])

        for filename, text, wc, ppn in prun(ExtractTask.get_all(source_dir), processes=processes):

            if filename is None:
                continue

            writer.writerow([filename, text, wc, ppn])


def to_sqlite(source_dir, output_file, processes):

    with sqlite3.connect(output_file) as conn:

        conn.execute('pragma journal_mode=wal')

        for idx, (filename, text, wc, ppn) in\
                enumerate(prun(ExtractTask.get_all(source_dir), processes=processes)):

            if filename is None:
                continue

            pd.DataFrame({'id': idx, 'file_name': filename, 'text': text, 'wc': wc, 'ppn': ppn}, index=[idx]).\
                reset_index(drop=True).set_index('id').\
                to_sql('text', con=conn, if_exists='append', index_label='id')

        conn.execute('create index idx_ppn on text(ppn);')


@click.command()
@click.argument('source-dir', type=click.Path(), required=True, nargs=1)
@click.argument('output-file', type=click.Path(), required=True, nargs=1)
@click.option('--processes', default=6, help='number of parallel processes')
def altotool(source_dir, output_file, processes):
    """
    Extract text from a bunch of alto XML files into one big CSV(.csv) or SQLITE3(.sqlite3) file.

    SOURCE_DIR: The directory that contains subfolders with the ALTO xml files.
    OUTPUT_FILE: Write the extracted fulltext to this file (either .csv or .sqlite3).
    """

    if output_file.endswith('.sqlite3'):
        to_sqlite(source_dir, output_file, processes)
    elif output_file.endswith('.csv'):
        to_csv(source_dir, output_file, processes)
    else:
        raise RuntimeError("Output format not supported.")
