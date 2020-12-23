import pandas as pd
import requests
import json
import click
from pprint import pprint
import re
from qurator.wikidata.entities import load_entities


@click.command()
@click.argument('out-file', type=click.Path(exists=False), required=True, nargs=1)
@click.option('--endpoint', type=str, default=None,
              help="SPARQL endpoint. Default https://query.wikidata.org/bigdata/namespace/wdq/sparql.")
@click.option('--query', type=str, default=None, help="SPARQL query.")
@click.option('--query-file', type=click.Path(exists=True), default=None, help="Read query from file")
@click.option('--analytic', type=bool, default=False, is_flag=True,
              help="Run query in analytic mode (Blazegraph specific).")
@click.option('--demo', type=bool, default=False, is_flag=True, help="Run demo query.")
@click.option('--lang', type=str, default=None, help="Replace __LANG__ in query by this value. Default: empty.")
@click.option('--site', type=str, default=None, help="Replace __SITE__ in query by this value. Default: empty.")
def cli_run_sparql(out_file, endpoint=None, query=None, query_file=None, analytic=False, demo=False, lang=None,
                   site=None):
    """
    Runs a SPARQL query QUERY on ENDPOINT and saves the results as pickled pandas DataFrame in OUT_FILE.
    """
    if demo:
        pass
    elif query is None and query_file is None:
        raise RuntimeError("Either query or query file required.")
    elif query is not None and query_file is not None:
        raise RuntimeError("Either command line query or query file supported.")
    elif query is None:

        with open(query_file, "r") as file:

            query = file.read()

    if lang is not None:
        query = re.sub("__LANG__", lang, query)

    if site is not None:
        query = re.sub("__SITE__", site, query)

    ret = run_sparql(endpoint, query, analytic)

    ret.to_pickle(out_file)


def run_sparql(endpoint=None, query=None, analytic=False):

    if endpoint is None:  # use wikidata.org endpoint as default

        endpoint = 'https://query.wikidata.org/bigdata/namespace/wdq/sparql'

    if query is None:  # test query as default
        query = 'SELECT ?pres ?presLabel ?spouse ?spouseLabel WHERE {\
                ?pres wdt:P31 wd:Q5 .\
                ?pres wdt:P39 wd:Q11696 .\
                ?pres wdt:P26 ?spouse .\
                SERVICE wikibase:label {\
                 bd:serviceParam wikibase:language "en" .\
                }\
              }'

        print('Running demo query:')

    if analytic:
        endpoint += "&analytic=true"
        
    resp = requests.get(url=endpoint, params={'query': query, 'analytic': str.lower(str(analytic))},
                        headers={'Accept': 'application/json'})

    resp.raise_for_status()

    result = json.loads(resp.content)

    tmp = [pd.DataFrame.from_dict(r).loc[['value']] for r in result['results']['bindings']]

    ret = pd.concat(tmp).reset_index(drop=True)

    return ret


@click.command()
@click.argument('path', type=click.Path(exists=True), required=True, nargs=1)
@click.argument('lang', type=str, required=True, nargs=1)
@click.argument('site', type=str, required=True, nargs=1)
@click.argument('out-file', type=click.Path(exists=False), required=True, nargs=1)
def join_entities(path, lang, site, out_file):
    """
    Load entities of language LANG from files in PATH, join them and write them as joined pandas DataFrame to OUT_FILE.
    """

    ent = load_entities(path, lang, site)

    ent.to_pickle(out_file)
