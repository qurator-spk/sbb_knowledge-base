import pandas as pd
import sqlite3
from tqdm import tqdm as tqdm
import click
import requests
import os
from flask import json


def parse_sentence(sent, normalization_map=None):
    entities = []
    entity_types = []
    entity = []
    ent_type = None

    for p in sent:

        if len(entity) > 0 and (p['prediction'] == 'O' or p['prediction'].startswith('B-')
                                or p['prediction'][2:] != ent_type):
            entities += len(entity) * [" ".join(entity)]
            entity_types += len(entity) * [ent_type]
            entity = []
            ent_type = None

        if p['prediction'] != 'O':
            entity.append(p['word'])

            if ent_type is None:
                ent_type = p['prediction'][2:]
        else:
            entities.append("")
            entity_types.append("")

    if len(entity) > 0:
        entities += len(entity) * [" ".join(entity)]
        entity_types += len(entity) * [ent_type]

    entity_ids = ["{}-{}".format(entity, ent_type) for entity, ent_type in zip(entities, entity_types)]

    if normalization_map is not None:
        text_json = json.dumps(
            ["".join([normalization_map[c] if c in normalization_map else c for c in p['word']]) for p in sent])

        tags_json = json.dumps([p['prediction'] for p in sent])

        entities_json = json.dumps(entity_ids)

        return entity_ids, entities, entity_types, text_json, tags_json, entities_json
    else:
        return entity_ids, entities, entity_types


def count_entities(ner, counter, min_len=4):

    type_agnostic = False if len(counter) == 3 and type(counter[counter.keys()[0]]) == dict else True

    for sent in ner:

        entity_ids, entities, entity_types = parse_sentence(sent)

        already_processed = set()

        for entity_id, entity, ent_type in zip(entity_ids, entities, entity_types):

            if len(entity) < min_len:
                continue

            if entity_id in already_processed:
                continue

            already_processed.add(entity_id)

            if type_agnostic:
                if entity_id in counter:
                    counter[entity_id] += 1
                else:
                    counter[entity_id] = 1
            else:
                if entity in counter[ent_type]:
                    counter[ent_type][entity] += 1
                else:
                    counter[ent_type][entity] = 1


@click.command()
@click.argument('sqlite-file', type=click.Path(exists=True), required=True, nargs=1)
@click.argument('pkl-file', type=click.Path(), required=True, nargs=1)
def ned_statistics(sqlite_file, pkl_file):

    with sqlite3.connect(sqlite_file) as con:
        num_docs = con.execute('select count(*) from tagged').fetchone()[0]

        counter = {'PER': {}, 'LOC': {}, 'ORG': {}}

        for rid, ppn, file_name, text, tags in tqdm(con.execute('select * from tagged'), total=num_docs):

            ner = \
                [[{'word': word, 'prediction': tag} for word, tag in zip(sen_text, sen_tags)]
                 for sen_text, sen_tags in zip(json.loads(text), json.loads(tags))]

            count_entities(ner, counter)

    df = pd.DataFrame.from_dict(counter)

    df.to_pickle(pkl_file)


@click.command()
@click.argument('sqlite-file', type=click.Path(exists=True), required=True, nargs=1)
@click.argument('lang-file', type=click.Path(exists=True), required=True, nargs=1)
@click.argument('el-endpoints', type=str, required=True, nargs=1)
@click.option('--chunk-size', default=100, help='size of chunks sent to EL-Linking system. Default: 100.')
@click.option('--noproxy', type=bool, is_flag=True, help='disable proxy. default: proxy is enabled.')
@click.option('--start-from-ppn', type=str, default=None)
def run_on_corpus(sqlite_file, lang_file, el_endpoints, chunk_size, noproxy, start_from_ppn):

    if noproxy:
        os.environ['no_proxy'] = '*'

    el_endpoints = json.loads(el_endpoints)

    lang = pd.read_pickle(lang_file)
    lang['ppn'] = lang.ppn.str.extract('PPN(.*)')

    lang = lang.set_index(['ppn', 'filename']).sort_index()

    with sqlite3.connect(sqlite_file) as con:

        con.execute('create table if not exists "entity_linking"'
                    '("index" integer primary key, "entity_id" TEXT, "page_title" TEXT, "wikidata" TEXT,'
                    '"proba" FLOAT, "ppn" TEXT, start_page INTEGER, stop_page INTEGER)')

        con.execute('create index if not exists idx_place on entity_linking(entity_id, ppn, start_page, stop_page);')
        con.execute('create index if not exists idx_wikidata on entity_linking(wikidata, ppn);')

        ppns = pd.read_sql('select ppn from tagged', con=con).drop_duplicates().reset_index(drop=True)

        ppns['ppn'] = ppns.ppn.astype(str)

        if start_from_ppn is not None:

            print('Skipping everything before PPN: {}'.format(start_from_ppn))
            ppns = ppns.iloc[ppns.loc[ppns.ppn == start_from_ppn].index[0]:]

        seq = tqdm(ppns.iterrows(), total=len(ppns))

        num_entities = 0

        def print_msg(_msg):

            seq.set_description("#overall: {} =>{}<=".format(num_entities, _msg), refresh=True)

        for i, row in seq:

            docs = pd.read_sql('select * from tagged where ppn==?', params=(row.ppn,), con=con)

            docs['page'] = docs.file_name.str.extract('.*?([0-9]+).*?').astype(int)

            docs = docs.merge(lang, left_on=['ppn', 'file_name'], right_index=True)

            docs = docs.sort_values('page')

            ner = []

            for doc_lang, lang_docs in docs.groupby('language', as_index=False):

                if doc_lang not in el_endpoints:
                    print_msg('Skipping for PPN{}, {} pages,language {}'.format(row.ppn, len(lang_docs), doc_lang))
                    continue

                for _, doc_row in lang_docs.iterrows():
                    ner += [[{'word': word, 'prediction': tag} for word, tag in zip(sen_text, sen_tags)]
                            for sen_text, sen_tags in zip(json.loads(doc_row.text), json.loads(doc_row.tags))]

                if len(ner) <= 0:
                    continue

                resp = requests.post(url=el_endpoints[doc_lang] + '/parse', json=ner)

                resp.raise_for_status()

                ner_parsed = json.loads(resp.content)

                if len(ner_parsed) <= 0:
                    continue

                num_entities += len(ner_parsed)

                start_page = lang_docs.page.min()
                stop_page = lang_docs.page.max()

                print_msg('Processing PPN {} start page {} stop page {} '
                          '#entities: {}'.format(row.ppn, start_page, stop_page, len(ner_parsed)))

                el_rest_endpoint = el_endpoints[doc_lang] + '/ned?threshold=0.01'

                keys = []

                for k in ner_parsed.keys():

                    tmp = pd.read_sql('select * from entity_linking where ppn=? and entity_id=? '
                                      'and start_page=? and stop_page=?',
                                      params=(row.ppn, k, str(start_page), str(stop_page)), con=con)

                    if len(tmp) > 0:
                        print_msg('Processing PPN {} found {}'.format(row.ppn, k))
                    else:
                        keys.append(k)

                for pos in range(0, len(keys), chunk_size):

                    chunk = keys[pos:pos + chunk_size]

                    chunk = {k: ner_parsed[k] for k in chunk}

                    try:
                        resp = requests.post(url=el_rest_endpoint, json=chunk, timeout=3600)

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

                    ned_result['ppn'] = row.ppn
                    ned_result['start_page'] = start_page
                    ned_result['stop_page'] = stop_page

                    ned_result.to_sql('entity_linking', con=con, if_exists='append', index=False)

