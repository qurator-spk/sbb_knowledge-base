import re
import pyarrow as pa
import pyarrow.parquet as pq
import pandas as pd
import numpy as np
import dask.dataframe as dd
# import os
from tqdm import tqdm as tqdm
from somajo import Tokenizer, SentenceSplitter
import click
import json
from qurator.wikipedia.entities import get_redirects, get_disambiguation
from qurator.utils.parallel import run as prun
import sqlite3
import html


def clean_text(raw_text):
    raw_text = re.sub(r'== Literatur ==.*$', r'', raw_text, flags=re.DOTALL)  # remove literature references

    raw_text = re.sub(r'== Filme ==.*$', r'', raw_text, flags=re.DOTALL)  # remove movie references

    raw_text = re.sub(r'<!--.*?-->', r' ', raw_text, flags=re.DOTALL)  # remove comments

    raw_text = re.sub(r'<[^<]*?/>', r' ', raw_text, flags=re.DOTALL)  # remove < ... />

    raw_text = re.sub(r'<[^/]+?>.*?</.+?>', ' ', raw_text, flags=re.DOTALL)  # remove stuff like <ref> .... </ref>

    while re.match(r'.*{\|.*?\|}.*', raw_text, flags=re.DOTALL):
        raw_text = re.sub(r'{\|((?!{\|).)*?\|}', r'', raw_text, flags=re.DOTALL)  # remove tables {| ...|}

    while re.match(r'.*{{[^{]+?}}.*', raw_text, flags=re.DOTALL):
        raw_text = re.sub(r'{{[^{]+?}}', r'', raw_text, flags=re.DOTALL)  # remove {{ ... }}

    raw_text = re.sub(r'={2,10}.*?={2,10}', r' ', raw_text, flags=re.DOTALL)  # remove == ... ==

    raw_text = re.sub(r'&nbsp;', r' ', raw_text)  # remove  "&nbsp;"

    # re-write wikipedia links to prepare for removal of file and http links ...
    raw_text = re.sub(r'\[\[([^|\[]*?)([|]?)([^|]+?)\]\]', r'{|\1\2\3|}', raw_text)

    # remove file and http links
    raw_text = re.sub(r'\[\[Datei:.+?\]\]', r'', raw_text)  # remove file links [[Datei: ....]]

    raw_text = re.sub(r'\[https?://.+?\]', r'', raw_text)  # remove http/https links [http: ....]

    # re-write wikipedia links back to standard wikipedia format
    raw_text = re.sub(r'{\|([^|\[]*?)([|]?)([^|]+?)\|}', r'[[\1\2\3]]', raw_text)

    return raw_text


# def iterate_page_links(all_entities, redirects, raw_text):
#     for m in re.finditer(r'\[\[([^|\[]*?)[|]?([^|]+?)\]\]', raw_text):
#
#         # page_title is the actual internal wikipedia page_title
#         page_title = (m[1] if len(m[1]) > 0 else m[2]).replace(' ', '_')
#
#         # surface text in the article
#         surface_text = m[2]
#
#         if page_title in all_entities.index:  # if the referenced page is an entity page ...
#
#             # print(page_title, surface_text, all_entities.loc[page_title].TYPE)
#
#             yield (page_title, surface_text, all_entities.loc[page_title].TYPE)
#
#         elif page_title in redirects.index:  # It could be a redirect otherwise
#
#             for re_count, (rd_from_title, redirect_to) in enumerate(redirects.loc[[page_title]].iterrows()):
#
#                 if redirect_to.rd_title in all_entities.index:  # redirect points to an entity
#
#                     if re_count == 0:  # first time, we also output the original surface text
#                         yield (redirect_to.rd_title, surface_text,
#                                all_entities.loc[redirect_to.rd_title].TYPE)
#
#                     yield (redirect_to.rd_title, redirect_to.rd_title.replace('_', ' '),
#                            all_entities.loc[redirect_to.rd_title].TYPE)
#
#
# def iterate_token_entities(all_entities, redirects, tokens, max_entity_len):
#     pos = 0
#     while pos < len(tokens):
#         for width in range(min(max_entity_len, len(tokens) - pos), 0, -1):
#
#             window = tokens[pos:pos + width]
#
#             surface_text = " ".join(window)
#             page_title = "_".join(window)
#
#             if len(surface_text) < 5:
#                 continue
#
#             if page_title in all_entities.index:  # if the surface text can be uniquely identified as entity
#
#                 yield (page_title, surface_text, all_entities.loc[page_title].TYPE)
#
#                 pos += width
#                 break
#
#             elif page_title in redirects.index:  # otherwise, it could be a redirect ...
#
#                 for re_count, (rd_from_title, redirect_to) in enumerate(redirects.loc[[page_title]].iterrows()):
#
#                     if redirect_to.rd_title in all_entities.index:  # redirect points to an entity
#
#                         if re_count == 0:  # first time, we also output the original surface text
#                             yield (redirect_to.rd_title, surface_text,
#                                    all_entities.loc[redirect_to.rd_title].TYPE)
#
#                         yield (redirect_to.rd_title, redirect_to.rd_title.replace('_', ' '),
#                                all_entities.loc[redirect_to.page_title].TYPE)
#
#                 pos += width
#                 break
#         else:
#             pos += 1
#
#
# def create_entity_map_from_tokens(all_entities, redirects, disambiguation, tokens, max_entity_len):
#     entity_map = dict()
#     forbidden = set()
#
#     for page_title, surface_text, entity_type in iterate_token_entities(all_entities, redirects, tokens,
#                                                                         max_entity_len):
#         if surface_text in forbidden:
#             continue
#
#         if surface_text in entity_map and entity_map[surface_text][0] != entity_type:
#             print('TT{} {} <==> {} forbidden.'.format(surface_text,
#                                                       (entity_type, page_title), entity_map[surface_text]))
#             forbidden.add(surface_text)
#             del entity_map[surface_text]
#             continue
#
#         entity_map[surface_text] = (entity_type, page_title)
#
#         if entity_type == 'PER':  # special treatment for PER entities
#
#             for part in surface_text.split(' '):
#
#                 if len(part) < 5:
#                     continue
#
#                 # ignore parts that lead to ambiguity
#                 if part in disambiguation.index \
#                         or '{}_(Begriffsklärung)'.format(part) in disambiguation.index:
#                     continue
#
#                 # skip if part already in entity map
#                 if part in entity_map:
#                     continue
#
#                 entity_map[part] = (entity_type, page_title)
#
#     return entity_map
#
#
# def create_entity_map_from_wiki_linkage(all_entities, redirects, disambiguation, raw_text):
#     entity_map = dict()
#     # forbidden = set()
#
#     for page_title, surface_text, entity_type in iterate_page_links(all_entities, redirects, raw_text):
#
#         # if surface_text in forbidden:
#         #    continue
#
#         if surface_text in entity_map:  # surface text has already been recorded
#
#             if page_title.replace('_', ' ') != surface_text:  # Skip, if not a canonical entity link.
#                 continue
#
#             # if entity_map[surface_text][0] != entity_type:
#             # else:
#             #     print('LL{} {} <==> {} forbidden.'.format(surface_text,
#             #                                             (entity_type, page_title), entity_map[surface_text]))
#             #     forbidden.add(surface_text)
#             #     del entity_map[surface_text]
#
#             # continue
#
#         print(surface_text, page_title, entity_type)
#
#         entity_map[surface_text] = (entity_type, page_title)
#
#         if entity_type == 'PER':
#
#             for part in surface_text.split(' '):
#
#                 if len(part) < 5:
#                     continue
#
#                 if part in disambiguation.index \
#                         or '{}_(Begriffsklärung)'.format(part) in disambiguation.index:
#                     continue
#
#                 if part in entity_map:
#                     continue
#
#                 entity_map[part] = (entity_type, page_title)
#
#     return entity_map
#
#
# def sentence_tagger(sentences, entity_map, max_entity_len):
#     """
#     Determine NER labels for a list of word-tokenized sentences
#
#     :param sentences: list of word tokenized sentences
#     :param entity_map: dictionary to lookup known entities
#     :param max_entity_len: maximum number of word tokens an entity can have
#     :return: pandas DataFrame that contains the labeled sentences.
#     """
#
#     gt = list()
#     for sen_num, sen in enumerate(sentences):
#
#         gt_sen = list()
#
#         pos = 0
#         while pos < len(sen):
#
#             for width in range(min(max_entity_len, len(sen) - pos), 0, -1):
#
#                 window = sen[pos:pos + width]
#
#                 surface_text = " ".join(window)
#
#                 try:
#                     if surface_text in entity_map:
#                         entity_type, page_title = entity_map[surface_text]
#                     else:
#                         continue
#
#                     for i, t in enumerate(window):
#                         gt_sen.append((sen_num, pos + i, t, 'B-' + entity_type, page_title)
#                                       if i == 0 else (sen_num, pos + i, t, 'I-' + str(entity_type)))
#                     pos += width
#                     break
#                 except KeyError:
#                     continue
#             else:
#                 gt_sen.append((sen_num, pos, sen[pos], 'O', None))
#                 pos += 1
#
#         gt.append(pd.DataFrame(gt_sen, columns=['sentence', 'token', 'word', 'type', 'page_title']))
#
#     return pd.concat(gt)


def tokenize_links(cleaned_text, all_entities, redirects):
    text_parts = []
    pos = 0

    for m in re.finditer(r'\[\[([^|\[]*?)[|]?([^|]+?)\]\]', cleaned_text):

        entity_type = 'O'

        text_parts.append((cleaned_text[pos:m.start()], '', entity_type))

        pos = m.end()

        # page_title is the actual internal wikipedia page_title
        page_title = (m[1] if len(m[1]) > 0 else m[2]).replace(' ', '_')

        # page title might contain an anker like: page#paragraph
        page_title = re.match(r'(.*?)[#]?([^#]*)', page_title)[2]

        # surface text in the article
        surface_text = m[2]

        if page_title in all_entities.index:  # if the referenced page is an entity page ...

            entity_type = all_entities.loc[page_title].TYPE

        elif page_title in redirects.index:  # It could be a redirect otherwise

            if len(redirects.loc[[page_title]]) > 1:
                raise RuntimeError('Multiple redirects!')

            redirect_target = redirects.loc[page_title].rd_title

            page_title = redirect_target

            if redirect_target in all_entities.index:
                entity_type = all_entities.loc[redirect_target].TYPE

        text_parts.append((surface_text, page_title, entity_type))

    text_parts.append((cleaned_text[pos:], '', 'O'))

    return text_parts


def tokenize_parts(tokenizer, text_parts):
    tokens = []
    meta = []

    for part in text_parts:
        # part[0] : surface text
        # part[1] : page title of linked entity if available otherwise ''
        # part[2] : type of entity or 'O'

        tmp = tokenizer.tokenize_paragraph(part[0])

        for tok_count, tok in enumerate(tmp):
            # some xml-tags cannot be removed correctly, for instance: '<ref name="20/7"> </ref>'
            tokens.append(tok.replace(' ', '_'))

            meta.append((part[1], part[2] if part[2] == 'O' else 'B-' + part[2] if tok_count == 0 else 'I-' + part[2]))

    return tokens, meta


def annotated_tokenization(raw_text, tokenizer, sentence_splitter, all_entities, redirects):
    text_parts = tokenize_links(clean_text(raw_text), all_entities, redirects)

    tokens, meta = tokenize_parts(tokenizer, text_parts)

    meta = [('', 'O')] + meta

    sentences = sentence_splitter.split(tokens)

    gt_sen = []
    pos = 1
    for sent_count, sent in enumerate(sentences):
        for word_count, tok in enumerate(sent):

            gt_sen.append((sent_count, word_count, tok, meta[pos][0], meta[pos][1]))

            pos += 1

    return pd.DataFrame(gt_sen, columns=['sentence', 'token', 'word', 'page_title', 'type'])


class EntityTask:
    tokenizer = None
    spl = None
    all_entities = None
    redirects = None
    disambiguation = None

    def __init__(self, page_id, page_text, page_title):

        self._page_id = page_id
        self._page_text = page_text
        self._page_title = page_title

    def __call__(self, *args, **kwargs):

        # print("<<<<<<<<<<<<<<{}>>>>>>>>>>>>>>>".format(self._page_title))

        # entity_map = create_entity_map_from_tokens(EntityTask.all_entities, EntityTask.redirects,
        #                                            EntityTask.disambiguation,
        #                                            EntityTask.tokenizer.tokenize(self._page_title), 5)
        #
        # tokens = EntityTask.tokenizer.tokenize_paragraph(clean_text(self._page_text))
        #
        # sentences = EntityTask.spl.split(tokens)
        #
        # entity_map.update(create_entity_map_from_wiki_linkage(EntityTask.all_entities, EntityTask.redirects,
        #                                                       EntityTask.disambiguation, self._page_text))
        #
        # # print(entity_map)
        #
        # if len(entity_map) == 0:
        #     return None
        #
        # max_entity_len = max([len(EntityTask.tokenizer.tokenize(k)) for k, v in entity_map.items()])
        #
        # gt = sentence_tagger(sentences, entity_map, max_entity_len)

        gt = annotated_tokenization(self._page_text, EntityTask.tokenizer, EntityTask.spl, EntityTask.all_entities,
                                    EntityTask.redirects)

        text = []
        tags = []
        link_titles = []
        for _, sentence in gt.groupby('sentence'):
            text += [sentence.word.tolist()]
            tags += [sentence.type.tolist()]
            link_titles += [sentence.page_title.tolist()]

        return {'page_id': self._page_id, 'text': json.dumps(text), 'tags': json.dumps(tags),
                'link_titles': json.dumps(link_titles), 'page_title': self._page_title}

    @staticmethod
    def initialize(all_entities, redirects, disambiguation):

        EntityTask.tokenizer = Tokenizer(split_camel_case=True, token_classes=False, extra_info=False)
        EntityTask.spl = SentenceSplitter()
        EntityTask.all_entities = all_entities
        EntityTask.redirects = redirects
        EntityTask.disambiguation = disambiguation

    @staticmethod
    def tag(page_id, page_text, page_title):

        tagged = EntityTask(page_id, page_text, page_title)()

        return pd.DataFrame(tagged, index=['0']).reset_index(drop=True).set_index('page_id')


def get_entity_tasks(full_text_file, selected_pages):
    fulltext = dd.read_parquet(full_text_file)

    for page_index, page in tqdm(fulltext.iterrows(), total=len(fulltext)):

        if page.page_id not in selected_pages.index:
            continue

        yield EntityTask(page.page_id, page.text, page.title)


@click.command()
@click.argument('full-text-file', type=click.Path(exists=True), required=True, nargs=1)
@click.argument('all-entities-file', type=click.Path(exists=True), required=True, nargs=1)
@click.argument('wikipedia-sqlite-file', type=click.Path(exists=True), required=True, nargs=1)
@click.argument('tagged-parquet', type=click.Path(exists=False), required=True, nargs=1)
@click.option('--processes', default=6, help='number of parallel processes')
def tag_entities(full_text_file, all_entities_file, wikipedia_sqlite_file, tagged_parquet, processes,
                 chunksize=10000):
    """
    full-text-file: apache parquet file that contains the per article fulltext
    all-entities-file: pickle file that contains a pandas dataframe that describes the entities
    wikipedia-sqlite-file: sqlite3 dump of wikipedia that contains the redirect table
    tagget-parquet: result parquet file
    prcoesses: number of parallel processes
    """

    all_entities = pd.read_pickle(all_entities_file)

    redirects, pages_namespace0 = get_redirects(all_entities, wikipedia_sqlite_file)

    print("Number of pages to tag: {}".format(len(pages_namespace0)))
    print("Number of redirects: {}".format(len(redirects)))

    disambiguation = get_disambiguation(wikipedia_sqlite_file)

    def write_tagged(tagged):

        if len(tagged) == 0:
            return

        df_tagged = pd.DataFrame.from_dict(tagged).reset_index(drop=True)

        df_tagged['range'] = (df_tagged['page_id'] / 10000).astype(int)

        # df_tagged = df_tagged.set_index('page_id')

        # noinspection PyArgumentList
        table = pa.Table.from_pandas(df_tagged)

        pq.write_to_dataset(table, root_path=tagged_parquet, partition_cols=['range'])

        return

    tagged_list = []

    for tg in prun(get_entity_tasks(full_text_file, pages_namespace0), processes=processes,
                   initializer=EntityTask.initialize, initargs=(all_entities, redirects, disambiguation)):

        if tg is None:
            continue

        tagged_list.append(tg)

        if len(tagged_list) > chunksize:
            write_tagged(tagged_list)
            tagged_list = []

    return


@click.command()
@click.argument('wikipedia-sqlite-file', type=click.Path(exists=True), required=True, nargs=1)
@click.argument('train-fraction', type=float, required=True, nargs=1)
@click.argument('dev-fraction', type=float, required=True, nargs=1)
@click.argument('test-fraction', type=float, required=True, nargs=1)
@click.argument('train-set-file', type=click.Path(exists=False), required=True, nargs=1)
@click.argument('dev-set-file', type=click.Path(exists=False), required=True, nargs=1)
@click.argument('test-set-file', type=click.Path(exists=False), required=True, nargs=1)
@click.argument('seed', type=int, default=41, required=False, nargs=1)
def train_test_split(wikipedia_sqlite_file, train_fraction, dev_fraction, test_fraction,
                     train_set_file, dev_set_file, test_set_file, seed):
    assert (train_fraction > 0.0)
    assert (dev_fraction > 0.0)
    assert (test_fraction > 0.0)
    assert (train_fraction + dev_fraction + test_fraction <= 1.0)

    with sqlite3.connect(wikipedia_sqlite_file) as cnx:
        pages = pd.read_sql('SELECT page_title, page_id FROM page WHERE page_namespace==0', cnx)

        pages['page_title'] = pages.page_title.astype(str)
        pages = pages.set_index('page_id')

        pages = pages.loc[(~pages.page_title.str.startswith('Liste_')) &
                          (~pages.page_title.str.endswith('Begriffsklärung)'))]

    num_samples = float(len(pages))

    random_state = np.random.RandomState(seed=seed)

    perm = random_state.permutation(int(num_samples))

    num_train = int(train_fraction * num_samples)
    num_dev = int(dev_fraction * num_samples)
    num_test = int(test_fraction * num_samples)

    pages.iloc[perm[0:num_train]].sort_index().to_pickle(train_set_file)
    pages.iloc[perm[num_train:num_train + num_dev]].sort_index().to_pickle(dev_set_file)
    pages.iloc[perm[num_train + num_dev:num_train + num_dev + num_test]].sort_index().to_pickle(test_set_file)


@click.command()
@click.argument('tagged-parquet-file', type=click.Path(exists=True), required=True, nargs=1)
@click.argument('wikipedia-sqlite-file', type=click.Path(exists=True), required=True, nargs=1)
@click.argument('articles', type=str, required=True, nargs=1)
def print_article_command_line(tagged_parquet_file, wikipedia_sqlite_file, articles):
    html_text = print_article(wikipedia_sqlite_file, articles=articles, tagged_parquet_file=tagged_parquet_file)

    wrapper = """<html>
        <head>
        <title>{}</title>
        </head>
        <body>{}/body>
        </html>"""

    print(wrapper.format(articles, html_text))


def print_article(data=None, tagged_parquet_file=None, articles=None, wikipedia_sqlite_file=None):
    if data is None:
        df_tagged = dd.read_parquet(tagged_parquet_file)

        with sqlite3.connect(wikipedia_sqlite_file) as cnx:
            pages = pd.read_sql('SELECT page_title, page_id FROM page WHERE page_namespace==0', cnx)

            pages['page_title'] = pages.page_title.astype(str)

            pages = pages.set_index('page_title').sort_index()

            articles = articles.split('|')

            data = df_tagged.loc[pages.loc[articles].page_id].compute()

    html_text = ''
    for page_id, data_row in data.iterrows():

        html_text += "<h2>{}</h2><hr>".format(data_row.page_title)

        # noinspection PyBroadException
        try:
            text = json.loads(data_row.text)
            tags = json.loads(data_row.tags)

            for sentence, sen_tags in zip(text, tags):

                for te, ta in zip(sentence, sen_tags):
                    if ta.endswith('PER'):
                        html_text += '<font color="red">' + html.escape(te) + '</font> '
                    elif ta.endswith('LOC'):
                        html_text += '<font color="green">' + html.escape(te) + '</font> '
                    elif ta.endswith('ORG'):
                        html_text += '<font color="blue">' + html.escape(te) + '</font> '
                    else:
                        html_text += '{} '.format(te) if ta == 'O' else ' '

                html_text += '<br>'
        except:
            print('Could not load content for "{}"'.format(page_id))

    return html_text
