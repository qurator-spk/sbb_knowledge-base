import warnings
with warnings.catch_warnings():
    warnings.filterwarnings("ignore", category=FutureWarning)

    from xml.etree.ElementTree import iterparse
    from tqdm import tqdm as tqdm
    import re
    import pandas as pd
#    import pyarrow as pa
#    import pyarrow.parquet as pq
    import click
    import sqlite3


def _get_namespace(tag):
    namespace = re.match("^{(.*?)}", tag).group(1)
    if not namespace.startswith("http://www.mediawiki.org/xml/export-"):
        raise ValueError("%s not recognized as MediaWiki database dump"
                         % namespace)
    return namespace


# @click.command()
# @click.argument('wikipedia-xml-file', type=click.Path(exists=True), required=True, nargs=1)
# @click.argument('parquet-file', type=click.Path(), required=True, nargs=1)
# @click.option('--chunk-size', default=2*10**4, help='size of parquet chunks. default:2*10**4')
# def to_parquet(wikipedia_xml_file, parquet_file, chunk_size):
#     """
#     Takes a wikipedia xml multistream dump file, extracts page_id, page_title and page_text of each article
#     and writes that information into a chunked apache parquet file that can be read for instance by means of dask.
#
#     WIKIPEDIA_XML_FILE: wikipedia multistream xml dump of all pages.
#
#     PARQUET_FILE: result file.
#     """
#
#     context = iter(iterparse(wikipedia_xml_file, events=("end",)))
#
#     def write_pages(pages):
#
#         if len(pages) == 0:
#             return
#
#         df_pages = pd.DataFrame.from_dict(pages).reset_index(drop=True)
#
#         df_pages['range'] = (df_pages['page_id'] / 10000).astype(int)
#
#         # noinspection PyArgumentList
#         table = pa.Table.from_pandas(df_pages)
#
#         pq.write_to_dataset(table, root_path=parquet_file, partition_cols=['range'])
#
#         return
#
#     parse_xml(chunk_size, context, write_pages)
#
#     return


@click.command()
@click.argument('wikipedia-xml-file', type=click.Path(exists=True), required=True, nargs=1)
@click.argument('sqlite-file', type=click.Path(), required=True, nargs=1)
@click.option('--chunk-size', default=2*10**4, help='size of parquet chunks. default:2*10**4')
def to_sqlite(wikipedia_xml_file, sqlite_file, chunk_size):
    """
    Takes a wikipedia xml multistream dump file, extracts page_id, page_title and page_text of each article
    and writes that information into a sqlite file.

    WIKIPEDIA_XML_FILE: wikipedia multistream xml dump of all pages.

    SQLITE_FILE: result file.
    """

    context = iter(iterparse(wikipedia_xml_file, events=("end",)))

    def create_connection(db_file):

        co = sqlite3.connect(db_file)

        co.execute('pragma journal_mode=wal')

        return co

    with create_connection(sqlite_file) as conn:

        def write_pages(pages):

            if len(pages) == 0:
                return

            df_pages = pd.DataFrame.from_dict(pages).reset_index(drop=True)

            df_pages.to_sql('text', con=conn, if_exists='append', index_label='id')

            return

        parse_xml(chunk_size, context, write_pages)

        conn.execute('create index idx_page_id on text(page_id);')
        conn.execute('create index idx_title on text(title);')

    return


def parse_xml(chunk_size, context, write_pages):

    root = page_tag = text_path = id_path = title_path = None

    pages = []
    for event, elem in tqdm(context):

        if root is None:
            root = elem

            namespace = _get_namespace(elem.tag)
            ns_mapping = {"ns": namespace}
            page_tag = "{%(ns)s}page" % ns_mapping
            text_path = "./{%(ns)s}revision/{%(ns)s}text" % ns_mapping
            id_path = "./{%(ns)s}id" % ns_mapping
            title_path = "./{%(ns)s}title" % ns_mapping

            continue

        if elem.tag == page_tag:

            text_elem = elem.find(text_path)

            if text_elem is None:
                continue

            pages.append({'page_id': int(elem.find(id_path).text),
                          'title': elem.find(title_path).text,
                          'text': text_elem.text})

            elem.clear()
            root.clear()

        if len(pages) > chunk_size:
            write_pages(pages)
            pages = []

    write_pages(pages)
