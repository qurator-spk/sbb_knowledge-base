import pandas as pd
import sqlite3
from tqdm import tqdm as tqdm
import click
import requests
import os
import json


@click.command()
@click.argument('sqlite-file', type=click.Path(exists=True), required=True, nargs=1)
@click.argument('el-endpoint', type=str, required=True, nargs=1)
@click.option('--entity-types', type=str, default=None, help='Process only these particular types of entities.')
@click.option('--min-count-per-doc', type=int, default=None, help='Process only if number of entities per wiki-page is'
                                                                  'above this threshold.')
@click.option('--noproxy', type=bool, is_flag=True, help='disable proxy. default: proxy is enabled.')
def run_on_tagged(sqlite_file, el_endpoint, entity_types, min_count_per_doc, noproxy):
    """
    SQLITE_FILE: Wikipedia - NER/NEL - tagged sqlite database.
    """

    if noproxy:
        os.environ['no_proxy'] = '*'

    if entity_types is not None:
        entity_types = set(entity_types.split('|'))

    with sqlite3.connect(sqlite_file) as con:

        num_tagged = con.execute('select count(*) from tagged').fetchone()[0]

        con.execute('CREATE TABLE IF NOT EXISTS "entity_linking" '
                    '("entity_id" TEXT, "page_title" TEXT, "wikidata" TEXT, '
                    '"proba" REAL, "on_page_id" INTEGER, "on_page" TEXT, "gt" TEXT);')

        con.execute('create index if not exists idx_place on entity_linking(on_page);')
        con.execute('create index if not exists idx_entity_id on entity_linking(entity_id, on_page);')

        cursor = con.cursor()

        cursor.execute('SELECT * FROM tagged ORDER BY RANDOM()')
        # cursor.execute('SELECT * FROM tagged')

        seq = tqdm(cursor, total=num_tagged)

        for page_id, text, tags, link_titles, page_title in seq:

            seq.set_description("{}".format(page_title), refresh=True)

            ner = [[{'word': word, 'prediction': tag, 'gt': link}
                    for word, tag, link in zip(sen_text, sen_tags, sen_links)]
                   for sen_text, sen_tags, sen_links in
                   zip(json.loads(text), json.loads(tags), json.loads(link_titles))]

            resp = requests.post(url=el_endpoint + '/parse', json=ner)

            resp.raise_for_status()

            ner_parsed = json.loads(resp.content)

            if entity_types is not None:
                ner_parsed = {key: item for key, item in ner_parsed.items() if key[-3:] in entity_types}

            if min_count_per_doc is not None and len(ner_parsed) < min_count_per_doc:
                continue

            try:
                resp = requests.post(url=el_endpoint + '/ned?threshold=0.01', json=ner_parsed, timeout=1800)

                resp.raise_for_status()
            except requests.HTTPError as e:
                print(e)
                continue

            ned_result = json.loads(resp.content)

            ned_result = \
                pd.DataFrame([(e, l, ra['wikidata'], ra['proba_1'])
                              for e, r in
                              [(e, r['ranking'])
                               if 'ranking' in r else (e, [['-', {'proba_1': 0.0, 'wikidata': '-'}]])
                               for e, r in ned_result.items()] for l, ra in r],
                             columns=['entity_id', 'page_title', 'wikidata', 'proba'])

            ned_result['on_page_id'] = page_id
            ned_result['on_page'] = page_title

            gt = pd.DataFrame([(k, v['gt'][0]) for k, v in ner_parsed.items()], columns=['entity_id', 'gt'])

            ned_result = ned_result.merge(gt, on='entity_id')

            ned_result.to_sql('entity_linking', con=con, if_exists='append', index=False)
