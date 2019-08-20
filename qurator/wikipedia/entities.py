import sqlite3
import pandas as pd
import click
import numpy as np


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


def get_disambiguation(sqlite3_file):

    return get_pages('Begriffsklärung', sqlite3_file)


@click.command()
@click.argument('sqlite3-file', type=click.Path(), required=True, nargs=1)
@click.argument('entity-file', type=click.Path(), required=True, nargs=1)
def ner(sqlite3_file, entity_file):

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
