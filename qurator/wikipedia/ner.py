import warnings
with warnings.catch_warnings():
    warnings.filterwarnings("ignore", category=FutureWarning)

    import re
    import pandas as pd
    import numpy as np
    from tqdm import tqdm as tqdm
    from somajo import SentenceSplitter
    from somajo import SoMaJo as Tokenizer
    import click
    import json
    from qurator.wikipedia.entities import get_redirects, get_disambiguation
    from qurator.utils.parallel import run as prun
    import sqlite3
    import logging

logger = logging.getLogger(__name__)


def create_connection(db_file):

    conn = sqlite3.connect(db_file)

    conn.execute('pragma journal_mode=wal')

    return conn


def clean_text(raw_text):

    try:

        # remove literature references
        raw_text = re.sub(r'== (Literatur|Références|References|Bibliographie|Further reading) ==.*$', r'',
                          raw_text, flags=re.DOTALL)

        # remove movie references
        raw_text = re.sub(r'== (Filme|Film|Filmographie|Œuvres) ==.*$', r'', raw_text, flags=re.DOTALL)

        raw_text = re.sub(r'<!--.*?-->', r' ', raw_text, flags=re.DOTALL)  # remove comments

        raw_text = re.sub(r'<[^<]*?/>', r' ', raw_text, flags=re.DOTALL)  # remove < ... />

        raw_text = re.sub(r'<[^/]+?>.*?</.+?>', ' ', raw_text, flags=re.DOTALL)  # remove stuff like <ref> .... </ref>

        iterations=0
        while re.match(r'.*{\|.*?\|}.*', raw_text, flags=re.DOTALL) and iterations < 1000:
            raw_text = re.sub(r'{\|((?!{\|).)*?\|}', r'', raw_text, flags=re.DOTALL)  # remove tables {| ...|}
            iterations += 1

        iterations=0
        while re.match(r'.*{{[^{]+?}}.*', raw_text, flags=re.DOTALL) and iterations < 1000:
            raw_text = re.sub(r'{{[^{]+?}}', r'', raw_text, flags=re.DOTALL)  # remove {{ ... }}
            iterations += 1

        raw_text = re.sub(r'={2,10}.*?={2,10}', r' ', raw_text, flags=re.DOTALL)  # remove == ... ==

        raw_text = re.sub(r'&nbsp;', r' ', raw_text)  # remove  "&nbsp;"

        # re-write wikipedia links to prepare for removal of file and http links ...
        raw_text = re.sub(r'\[\[([^|\[]*?)([|]?)([^|]+?)\]\]', r'{|\1\2\3|}', raw_text)

        # remove file and http links
        raw_text = re.sub(r'\[\[(Datei|Fichier|File):.+?\]\]', r'', raw_text)  # remove file links [[Datei: ....]]

        raw_text = re.sub(r'\[https?://.+?\]', r'', raw_text)  # remove http/https links [http: ....]

        # re-write wikipedia links back to standard wikipedia format
        raw_text = re.sub(r'{\|([^|\[]*?)([|]?)([^|]+?)\|}', r'[[\1\2\3]]', raw_text)

        return raw_text
    except:
        logger.error('clean_text: Problem!!!!: {}'.format(raw_text))

        return ''


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

        tmp = tokenizer.tokenize_text([part[0]])

        for sen in tmp:
            for tok_count, tok in enumerate(sen):
                # some xml-tags cannot be removed correctly, for instance: '<ref name="20/7"> </ref>'
                tokens.append(tok.text.replace(' ', '_'))

                meta.append((part[1], part[2] if part[2] == 'O' else 'B-' + part[2] if tok_count == 0 else 'I-' + part[2]))

    return tokens, meta


def annotated_tokenization(raw_text, tokenizer, sentence_splitter, all_entities, redirects):
    result_columns = ['sentence', 'token', 'word', 'page_title', 'type']

    text_parts = tokenize_links(clean_text(raw_text), all_entities, redirects)

    if len(text_parts) == 0:
        return pd.DataFrame([], columns=result_columns)

    tokens, meta = tokenize_parts(tokenizer, text_parts)

    meta = [('', 'O')] + meta

    sentences = sentence_splitter.split(tokens)

    gt_sen = []
    pos = 1
    for sent_count, sent in enumerate(sentences):
        for word_count, tok in enumerate(sent):

            gt_sen.append((sent_count, word_count, tok, meta[pos][0], meta[pos][1]))

            pos += 1

    return pd.DataFrame(gt_sen, columns=result_columns)


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

        # EntityTask.tokenizer = Tokenizer(split_camel_case=True, token_classes=False, extra_info=False)
        EntityTask.tokenizer = Tokenizer('de_CMC', split_camel_case=True)
        EntityTask.spl = SentenceSplitter()
        EntityTask.all_entities = all_entities
        EntityTask.redirects = redirects
        EntityTask.disambiguation = disambiguation

    @staticmethod
    def tag(page_id, page_text, page_title):

        tagged = EntityTask(page_id, page_text, page_title)()

        return pd.DataFrame(tagged, index=['0']).reset_index(drop=True).set_index('page_id')

    @staticmethod
    def get_from_sqlite(fulltext_sqlite, selected_pages):

        with create_connection(fulltext_sqlite) as read_conn:

            total = int(read_conn.execute('select count(*) from text;').fetchone()[0])

            pos = read_conn.cursor().execute('SELECT page_id, text, title from text')

            for page_id, text, title in tqdm(pos, total=total):

                if page_id not in selected_pages.index:
                    continue

                yield EntityTask(page_id, text, title)


@click.command()
@click.argument('fulltext-sqlite', type=click.Path(exists=True), required=True, nargs=1)
@click.argument('all-entities-file', type=click.Path(exists=True), required=True, nargs=1)
@click.argument('wikipedia-sqlite-file', type=click.Path(exists=True), required=True, nargs=1)
@click.argument('tagged-sqlite', type=click.Path(exists=False), required=True, nargs=1)
@click.option('--processes', default=6, help='number of parallel processes. default: 6.')
def tag_entities2sqlite(fulltext_sqlite, all_entities_file, wikipedia_sqlite_file, tagged_sqlite, processes,
                        chunksize=10000):
    """
    FULLTEXT_SQLITE: SQLITE file that contains the per article fulltext.
    (see extract-wiki-full-text-sqlite)

    ALL_ENTITIES_FILE: pickle file that contains a pandas dataframe that describes the entities
    (see extract-wiki-ner-entities).

    WIKIPEDIA_SQLITE_FILE: sqlite3 dump of wikipedia that contains the redirect table.

    TAGGED_SQLITE: result sqlite file. The file provides per article access to the fulltext where all relevant
    entities according to ALL_ENTITIES_FILE have been tagged.
    """

    all_entities = pd.read_pickle(all_entities_file)

    redirects, pages_namespace0 = get_redirects(all_entities, wikipedia_sqlite_file)

    print("Number of pages to tag: {}".format(len(pages_namespace0)))
    print("Number of redirects: {}".format(len(redirects)))

    disambiguation = get_disambiguation(wikipedia_sqlite_file)

    first_write = True

    with create_connection(tagged_sqlite) as write_conn:

        def write_tagged(tagged):

            nonlocal first_write

            if len(tagged) == 0:
                return

            df_tagged = pd.DataFrame.from_dict(tagged).reset_index(drop=True).set_index('page_id')

            df_tagged.to_sql('tagged', con=write_conn, if_exists='append', index_label='page_id')

            if first_write:

                try:
                    write_conn.execute('create index idx_ppn on tagged(page_id);')
                    write_conn.execute('create index idx_page_title on tagged(page_title);')
                except sqlite3.OperationalError:
                    logger.error('Could not create database index!!!')

                first_write = False

            return

        tagged_list = []

        for tg in prun(EntityTask.get_from_sqlite(fulltext_sqlite, pages_namespace0), processes=processes,
                       initializer=EntityTask.initialize, initargs=(all_entities, redirects, disambiguation)):

            if tg is None:
                continue

            tagged_list.append(tg)

            if len(tagged_list) > chunksize:
                write_tagged(tagged_list)
                tagged_list = []

        write_tagged(tagged_list)

    return


@click.command()
@click.argument('wikipedia-sqlite-file', type=click.Path(exists=True), required=True, nargs=1)
@click.argument('train-fraction', type=float, required=True, nargs=1)
@click.argument('dev-fraction', type=float, required=True, nargs=1)
@click.argument('test-fraction', type=float, required=True, nargs=1)
@click.argument('train-set-file', type=click.Path(exists=False), required=True, nargs=1)
@click.argument('dev-set-file', type=click.Path(exists=False), required=True, nargs=1)
@click.argument('test-set-file', type=click.Path(exists=False), required=True, nargs=1)
@click.option('--seed', type=int, default=41, help="Random number seed. default: 41.")
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
