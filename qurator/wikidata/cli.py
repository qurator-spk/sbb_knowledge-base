import pandas as pd
import requests
import json
import click


@click.command()
@click.argument('out-file', type=click.Path(exists=False), required=True, nargs=1)
@click.option('--endpoint', type=str, default=None,
              help="SPARQL endpoint. Default https://query.wikidata.org/bigdata/namespace/wdq/sparql.")
@click.option('--query', type=str, default=None, help="SPARQL query.")
@click.option('--query-file', type=click.Path(exists=True), default=None, help="Read query from file")
def cli_run_sparql(out_file, endpoint=None, query=None, query_file=None):
    """
    Runs a SPARQL query QUERY on ENDPOINT and saves the results as pickled pandas DataFrame in OUT_FILE.
    """

    if query is None and query_file is None:
        raise RuntimeError("Either query or query file required.")

    if query is None:

        with open(query_file, "r") as file:

            query = file.read()

    ret = run_sparql(endpoint, query)

    ret.to_pickle(out_file)


def run_sparql(endpoint=None, query=None):

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

    resp = requests.get(url=endpoint, params={'query': query}, headers={'Accept': 'application/json'})

    resp.raise_for_status()

    result = json.loads(resp.content)

    tmp = [pd.DataFrame.from_dict(r).loc[['value']] for r in result['results']['bindings']]

    ret = pd.concat(tmp).reset_index(drop=True)

    return ret

