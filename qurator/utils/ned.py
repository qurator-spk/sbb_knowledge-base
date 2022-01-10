import os
import requests
import json


def ned(tsv, ner_result, ned_rest_endpoint, json_file=None, threshold=None, priority=None, max_candidates=None,
        max_dist=None, not_after=None):

    return_full = json_file is not None

    if json_file is not None and os.path.exists(json_file):

        print('Loading {}'.format(json_file))

        with open(json_file, "r") as fp:
            ned_result = json.load(fp)

    else:

        resp = requests.post(url=ned_rest_endpoint + '/parse', json=ner_result)

        resp.raise_for_status()

        ner_parsed = json.loads(resp.content)

        ned_rest_endpoint = ned_rest_endpoint + '/ned?return_full=' + str(int(return_full)).lower()

        if priority is not None:
            ned_rest_endpoint += "&priority=" + str(int(priority))

        if return_full:
            ned_rest_endpoint += "&threshold=0.01"  # The JSON representation of the full results permits evaluation
            # for an arbitrary threshold >= 0.01

        elif threshold is not None:
            ned_rest_endpoint += "&threshold=" + str(float(threshold))

        if max_candidates is not None:
            ned_rest_endpoint += "&max_candidates=" + str(int(max_candidates))

        if max_dist is not None:
            ned_rest_endpoint += "&max_dist=" + str(float(max_dist))

        if not_after is not None:
            ner_parsed['__CONTEXT__'] = \
                {
                    'time': {
                        'not_after': not_after
                    }
                }

        resp = requests.post(url=ned_rest_endpoint, json=ner_parsed, timeout=3600000)

        resp.raise_for_status()

        ned_result = json.loads(resp.content)

    rids = []
    entity = ""
    entity_type = None
    tsv['ID'] = '-'
    tsv['conf'] = '-'

    def check_entity(tag):
        nonlocal entity, entity_type, rids

        if (entity != "") and ((tag == 'O') or tag.startswith('B-') or (tag[2:] != entity_type)):

            eid = entity + "-" + entity_type

            if eid in ned_result:
                if 'ranking' in ned_result[eid]:
                    ranking = ned_result[eid]['ranking']

                    tmp = "|".join([ranking[i][1]['wikidata']
                                    for i in range(len(ranking))
                                    if threshold is None or ranking[i][1]['proba_1'] >= threshold])
                    tsv.loc[rids, 'ID'] = tmp if len(tmp) > 0 else '-'

                    tmp = ",".join([str(ranking[i][1]['proba_1'])
                                    for i in range(len(ranking))
                                    if threshold is None or ranking[i][1]['proba_1'] >= threshold])

                    tsv.loc[rids, 'conf'] = tmp if len(tmp) > 0 else '-'
                else:
                    tsv.loc[rids, 'ID'] = 'NIL'
                    tsv.loc[rids, 'conf'] = '-'
            else:
                tsv.loc[rids, 'ID'] = 'NIL'
                tsv.loc[rids, 'conf'] = '-'

            rids = []
            entity = ""
            entity_type = None

    ner_tmp = tsv.copy()
    ner_tmp.loc[~ner_tmp['NE-TAG'].isin(['O', 'B-PER', 'B-LOC', 'B-ORG', 'I-PER', 'I-LOC', 'I-ORG']), 'NE-TAG'] = 'O'

    for rid, row in ner_tmp.iterrows():

        check_entity(row['NE-TAG'])

        if row['NE-TAG'] != 'O':

            entity_type = row['NE-TAG'][2:]

            entity += " " if entity != "" else ""

            entity += str(row['TOKEN'])

            rids.append(rid)

    check_entity('O')

    return tsv, ned_result
