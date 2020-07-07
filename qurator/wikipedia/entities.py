import sqlite3
import pandas as pd
import click
import numpy as np
from tqdm import tqdm as tqdm


def _get_cats(cat_links, category, found, cnx):
    found = found.union({category})

    try:
        cats = cat_links.loc[[category]]
    except KeyError:
        return found, pd.DataFrame(columns=cat_links.columns)

    tmp = list()
    tmp.append(cats)

    for _, row in cats.dropna().iterrows():

        if row.page_title in found:
            continue

        found, add_cats = _get_cats(cat_links, row.page_title, found, cnx)
        tmp.append(add_cats)

    cats = pd.concat(tmp, sort=False)

    return found, cats


def get_sub_cats(category, cnx):
    cat_pages = pd.read_sql_query("SELECT page_id, page_title FROM page WHERE page_namespace==14", cnx)

    cat_links = pd.read_sql_query("SELECT cl_to, cl_from FROM categorylinks", cnx)

    cat_links['cl_to'] = cat_links.cl_to.astype(str)

    cat_links = \
        cat_links.merge(cat_pages, left_on='cl_from', right_on='page_id', how='left').\
                    set_index('cl_to').sort_index()

    found = set()

    found, cats = _get_cats(cat_links, category, found, cnx)

    return cats.drop_duplicates().sort_index()


def get_category_pages(cats, cnx):

    pages = pd.read_sql_query("SELECT page_id, page_title FROM page WHERE page_namespace==0", cnx). \
        set_index('page_id'). \
        sort_index()

    page_ids = set(cats.cl_from.tolist())

    cat_pages = pages.reindex(page_ids).dropna()

    cat_pages['page_title'] = cat_pages.page_title.astype(str)

    cat_pages = cat_pages.dropna()

    cat_pages = cat_pages.loc[~cat_pages.page_title.str.startswith('Liste_')]

    return cat_pages


def get_redirects(all_entities, sqlite3_file):
    """
    From https://www.mediawiki.org/wiki/Manual:Redirect_table:

    rd_from: Contains the page_id of the source page.
    rd_namespace: Contains the number of the target's Namespace.
    rd_title: Contains the sanitized title of the target page.
    It is stored as text, with spaces replaced by underscores.

    :param all_entities: pandas DataFrame that contains all entities to be considered.
    :param sqlite3_file: sqlite database file to read from
    :return:
    """

    with sqlite3.connect(sqlite3_file) as cnx:

        redirects = pd.read_sql('SELECT rd_title, rd_from FROM redirect', cnx).set_index('rd_from')

        page = pd.read_sql('SELECT page_title, page_id FROM page WHERE page_namespace==0', cnx).\
            set_index('page_id').sort_index()

    redirects['rd_title'] = redirects.rd_title.astype(str)
    page['page_title'] = page.page_title.astype(str)

    # map rd_from (that is an ID) to the page table
    redirects = redirects.merge(page, left_index=True, right_index=True).\
        rename(columns={'page_title': 'rd_from_title'})

    # consider only those redirects that target an entity
    redirects = all_entities.merge(redirects, left_index=True, right_on='rd_title').\
        reset_index(drop=True).\
        set_index('rd_from_title').\
        sort_index()

    return redirects, page


def get_pages(category, sqlite3_file):

    with sqlite3.connect(sqlite3_file) as cnx:

        beg_cats = get_sub_cats(category, cnx)

        beg_pages = get_category_pages(beg_cats, cnx).\
                        reset_index().\
                        set_index('page_title').\
                        sort_index()

    return beg_pages


@click.command()
@click.argument('sqlite3-file', type=click.Path(exists=True), required=True, nargs=1)
@click.argument('entity-file', type=click.Path(exists=True), required=True, nargs=1)
@click.argument('output-file', type=click.Path(), required=True, nargs=1)
def redirects2entities(sqlite3_file, entity_file, output_file):
    """
    Resolves all redirects from entity_file into the target entity.

    SQLITE3_FILE: Wikipedia database as sqlite3 file.

    ENTITY_FILE: File that contains a pickled pandas DataFrame with all PER,LOC and ORG entities.

    OUTPUT_FILE: Write pickled DataFrame with mapped redirects+entities into this file.
    """

    all_entities = pd.read_pickle(entity_file)

    redirects, page = get_redirects(all_entities, sqlite3_file)

    redirects = redirects.sort_index()
    all_entities = all_entities.sort_index()

    tmp = []

    for page_title, row in tqdm(all_entities.iterrows(), total=len(all_entities)):

        entity_type = row.TYPE

        if page_title not in redirects.index:  # It could be a redirect otherwise
            tmp.append((page_title, entity_type))
            continue

        if len(redirects.loc[[page_title]]) > 1:
            raise RuntimeError('Multiple redirects!')

        page_title = redirects.loc[page_title, 'rd_title']

        if page_title in all_entities.index:
            continue

        tmp.append((page_title, entity_type))

    output = pd.DataFrame(tmp, columns=['page_title', 'TYPE']).set_index('page_title')

    output.to_pickle(output_file)


def get_disambiguation(sqlite3_file):

    return get_pages('Begriffsklärung', sqlite3_file)


@click.command()
@click.argument('sqlite3-file', type=click.Path(exists=True), required=True, nargs=1)
@click.argument('entity-file', type=click.Path(), required=True, nargs=1)
def extract(sqlite3_file, entity_file):
    """
    Runs recursively through the super categories "Organisation", "Geographisches Objekt", "Frau", "Mann"
    in order to determine all ORG, LOC, PER entities from the german wikipedia.

    SQLITE3_FILE: German Wikipedia database as sqlite3 file.

    ==>REQUIRED tables: page, categorylinks, redirects.

    ENTITY_FILE: Result file. Contains a pickled pandas DataFrame with all PER,LOC and ORG entities.
    For other non-german languages, ENTITY_FILE can be mapped via wikidata-QIDs (see wikidatamapping).
    """

    with sqlite3.connect(sqlite3_file) as cnx:

        org_cat = get_sub_cats('Organisation', cnx)

        org_pages = get_category_pages(org_cat, cnx)

        geo_cat = get_sub_cats('Geographisches_Objekt', cnx)

        geographic_notion_cats = get_sub_cats('Geographischer_Begriff', cnx)

        geographic_notion_pages = get_category_pages(geographic_notion_cats, cnx)

        loc_pages = get_category_pages(geo_cat, cnx)

        frau_cat = get_sub_cats('Frau', cnx)

        mann_cat = get_sub_cats('Mann', cnx)

        per_pages = pd.concat([get_category_pages(frau_cat, cnx),
                               get_category_pages(mann_cat, cnx)]).drop_duplicates()

    org_pages = org_pages.loc[~org_pages.index.isin(per_pages.index) & ~org_pages.index.isin(loc_pages.index)]

    loc_pages = loc_pages.loc[~loc_pages.index.isin(per_pages.index) &
                              ~loc_pages.index.isin(geographic_notion_pages.index)]

    all_entities = pd.concat([per_pages, loc_pages, org_pages])

    all_entities['TYPE'] = np.nan
    all_entities.loc[per_pages.index, 'TYPE'] = 'PER'
    all_entities.loc[loc_pages.index, 'TYPE'] = 'LOC'
    all_entities.loc[org_pages.index, 'TYPE'] = 'ORG'

    all_entities = all_entities.set_index('page_title').sort_index()

    all_entities.to_pickle(entity_file)


@click.command()
@click.argument('output-dir', type=click.Path(exists=True), required=True, nargs=1)
@click.argument('languages', type=str, required=True, nargs=1)
@click.argument('entity-file', type=click.Path(exists=True), required=True, nargs=1)
@click.argument('entity_wikipedia', type=click.Path(exists=True), required=True, nargs=1)
@click.argument('other_wikipedias', nargs=-1, type=click.Path(exists=True))
def wikidatamapping(output_dir, languages, entity_file, entity_wikipedia, other_wikipedias):
    """

    OUTPUT_DIR: directory to write result files

    LANGUAGES: string that contains the language identifiers of all the wikipedia's in correct order,
    separated by '|'. Example: 'DE|FR|EN'

    ENTITY_FILE: Pickled DataFrame contains the considered entities (created by extract-wiki-ner-entities).

    ENTITY_WIKIPEDIA: The wikipedia sqlite database file from where the ENTITY_FILE has been obtained.

    OTHER_WIKIPEDIAS: List of wikipedia sqlite database files of other languages that should be mapped onto the
    ENTITY_FILE.

    OUTPUT: wikidata-mapping.pkl: pickled DataFrame containing the mapping plus single per language entity
    files, for instance:

            de-wikipedia-ner-entities.pkl

            fr-wikipedia-ner-entities.pkl

            en-wikipedia-ner-entities.pkl
    """

    languages = languages.split('|')

    all_entities = pd.read_pickle(entity_file)

    qid_query = "select page.page_title, page_props.pp_value from page join page_props "\
                "on page.page_id==page_props.pp_page "\
                "where page.page_namespace==0 and page_props.pp_propname=='wikibase_item'"

    with sqlite3.connect(entity_wikipedia) as db:

        tmp = pd.read_sql(qid_query, db).\
            rename(columns={'pp_value': 'QID', 'page_title': languages[0]})

        mapping = all_entities.merge(tmp, left_index=True, right_on=languages[0])

    for lang, other_wikipedia in zip(languages[1:], other_wikipedias):

        with sqlite3.connect(other_wikipedia) as db:
            tmp = pd.read_sql(qid_query, db).\
                rename(columns={'pp_value': 'QID', 'page_title': lang})

        mapping = mapping.merge(tmp, on='QID', how='left')

    mapping = mapping.set_index('QID').reset_index().sort_values('QID')

    mapping.to_pickle("{}/wikidata-mapping.pkl".format(output_dir))

    for lang in languages:

        tmp = mapping[[lang, 'TYPE']].\
            dropna(how='any').\
            rename(columns={lang: 'page_title'}).\
            drop_duplicates(subset='page_title').\
            set_index('page_title').\
            sort_index()

        tmp.to_pickle("{}/{}-wikipedia-ner-entities.pkl".format(output_dir, lang.lower()))
