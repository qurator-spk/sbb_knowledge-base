import json
import os
import click
import pandas as pd
import requests

from .ned import ned
from .ner import ner
from .tsv import read_tsv, write_tsv


@click.command()
@click.argument('tsv-file', type=click.Path(exists=True), required=True, nargs=1)
@click.argument('tsv-out-file', type=click.Path(), required=True, nargs=1)
@click.option('--ner-rest-endpoint', type=str, default=None,
              help="REST endpoint of sbb_ner service. See https://github.com/qurator-spk/sbb_ner for details.")
@click.option('--ned-rest-endpoint', type=str, default=None,
              help="REST endpoint of sbb_ned service. See https://github.com/qurator-spk/sbb_ned for details.")
@click.option('--ned-json-file', type=str, default=None)
@click.option('--noproxy', type=bool, is_flag=True, help='disable proxy. default: proxy is enabled.')
@click.option('--ned-threshold', type=float, default=None, help='Minimum overall confidence for returned candidates. ')
@click.option('--ned-priority', type=int, default=1,
              help="Processing priority on the server. Default 1. Higher: 0 Lower: 2")
@click.option('--max-candidates', type=int, default=None,
              help="Number of candidates to consider per entity.")
@click.option('--max-dist', type=float, default=None, help='Maximum nearest neighbour distance.')
@click.option('--not-after', type=int, default=None,
              help="Consider only entities that already existed before this year. Default: Don't use.")
@click.option('--not-after-context-field', type=str, default=None,
              help="Determine not-after date from this context field.")
@click.option('--context-split', type=bool, is_flag=True, help="Perform EL for different contexts.")
def find_entities(tsv_file, tsv_out_file, ner_rest_endpoint, ned_rest_endpoint, ned_json_file, noproxy, ned_threshold,
                  ned_priority, max_candidates, max_dist, not_after, not_after_context_field, context_split):

    if noproxy:
        os.environ['no_proxy'] = '*'

    tsv, urls, contexts = read_tsv(tsv_file)

    try:
        if ner_rest_endpoint is not None:

            if not context_split:
                tsv, ner_result = ner(tsv, ner_rest_endpoint)
            else:
                ner_results = []
                for url_id, part in tsv.groupby('url_id', as_index=False):
                    part, part_result = ner(part, ner_rest_endpoint)
                    ner_results.append((part, part_result))

        elif os.path.exists(tsv_file):

            print('Using NER information that is already contained in file: {}'.format(tsv_file))

            tmp = tsv.copy()
            tmp['sen'] = (tmp['No.'] == 0).cumsum()
            tmp.loc[~tmp['NE-TAG'].isin(['O', 'B-PER', 'B-LOC', 'B-ORG', 'I-PER', 'I-LOC', 'I-ORG']), 'NE-TAG'] = 'O'

            if not context_split:

                ner_result = [[{'word': str(row.TOKEN), 'prediction': row['NE-TAG']} for _, row in sen.iterrows()]
                              for _, sen in tmp.groupby('sen')]
            else:
                ner_results = []
                for part in tmp.groupby('url_id', as_index=False):
                    part_result = \
                        [[{'word': str(row.TOKEN), 'prediction': row['NE-TAG']} for _, row in sen.iterrows()]
                         for _, sen in part.groupby('sen')]

                    ner_results.append((part, part_result))
        else:
            raise RuntimeError("Either NER rest endpoint or NER-TAG information within tsv_file required.")

        if ned_rest_endpoint is not None:

            if not context_split:
                tsv, ned_result = ned(tsv, ner_result, ned_rest_endpoint, json_file=ned_json_file,
                                      threshold=ned_threshold, priority=ned_priority, max_candidates=max_candidates,
                                      max_dist=max_dist, not_after=not_after)

                if ned_json_file is not None and not os.path.exists(ned_json_file):

                    with open(ned_json_file, "w") as fp_json:
                        json.dump(ned_result, fp_json, indent=2, separators=(',', ': '))
            else:

                ned_result = [None] * len(ner_results)

                if ned_json_file is not None and os.path.exists(ned_json_file):
                    with open(ned_json_file, "r") as fp:
                        ned_result = json.load(fp)

                parts = []
                for idx, (part, part_ner_result) in enumerate(ner_results):

                    _not_after = not_after
                    if not_after_context_field is not None and not_after_context_field in contexts[idx]:
                        _not_after = contexts[idx][not_after_context_field]

                    part, ned_result[idx] = \
                        ned(part, part_ner_result, ned_rest_endpoint, json_file=ned_json_file,
                            threshold=ned_threshold, priority=ned_priority, max_candidates=max_candidates,
                            max_dist=max_dist, not_after=_not_after, ned_result=ned_result[idx])

                    parts.append(part)

                if ned_json_file is not None and not os.path.exists(ned_json_file):
                    with open(ned_json_file, "w") as fp_json:
                        json.dump(ned_result, fp_json, indent=2, separators=(',', ': '))

                tsv = pd.concat(parts)

        write_tsv(tsv, urls, contexts, tsv_out_file)

    except requests.HTTPError as e:
        print(e)
