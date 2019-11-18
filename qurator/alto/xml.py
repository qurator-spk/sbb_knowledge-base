import os
import numpy as np
import warnings
import xml.etree.ElementTree as ElementTree
from tqdm import tqdm
import csv
import click

with warnings.catch_warnings():
    warnings.simplefilter("ignore")


@click.command()
@click.argument('source-dir', type=click.Path(), required=True, nargs=1)
@click.argument('output-file', type=click.Path(), required=True, nargs=1)
def to_csv(source_dir, output_file):
    """
    Extract text from a bunch of alto XML files into one big CSV file.
    """

    # Listing all sub-directories which are named with PPn
    ppn_list = os.listdir(source_dir)

    headers = ['file name', 'text', 'wc', 'ppn']

    # Extracting features needed for text mining.
    with open(output_file, 'w') as f:
        writer = csv.writer(f)
        writer.writerow(headers)

        for ppn in tqdm(ppn_list):

            current_ppn_dir = os.listdir(source_dir + '/' + ppn)
            for filename in current_ppn_dir:

                if not filename.endswith(".xml"):
                    continue

                try:
                    tree = ElementTree.parse(source_dir + '/' + ppn + '/' + filename)
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

                    writer.writerow([filename, " ".join(text_s), " ".join(wc_s), ppn])

                except RuntimeError as e:
                    print(e)
                    pass
