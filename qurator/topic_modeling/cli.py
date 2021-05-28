import sqlite3
import pandas as pd
from scipy.sparse import csr_matrix
import click
import gensim
from gensim.models.ldamulticore import LdaMulticore
from tqdm import tqdm
from qurator.utils.parallel import run as prun
import json
from ..sbb.ned import count_entities as _count_entities
import os

def count_entities(ner):
    counter = {}

    _count_entities(ner, counter)

    df = pd.DataFrame.from_dict(counter, orient='index', columns=['count'])

    return df


class CountJob:

    voc = None
    con = None

    def __init__(self, ppn, part):
        self._ppn = ppn
        self._part = part

    def __call__(self, *args, **kwargs):

        df = pd.read_sql('SELECT * from tagged where ppn=?', con=CountJob.con, params=(self._ppn,))

        df['page'] = df.file_name.str.extract('([1-9][0-9]*)').astype(int)

        df = df.loc[(df.page >= self._part.start_page.min()) & (df.page <= self._part.stop_page.max())]

        cnt = []
        for _, row in df.iterrows():
            ner = \
                [[{'word': word, 'prediction': tag} for word, tag in zip(sen_text, sen_tags)]
                 for sen_text, sen_tags in zip(json.loads(row.text), json.loads(row.tags))]

            counter = count_entities(ner)

            counter = counter.merge(self._part, left_index=True, right_on='entity_id')

            counter['on_page'] = row.page

            cnt.append(counter)

        cnt = pd.concat(cnt)

        weighted_cnt = []
        for (qid, page_title), qpart in cnt.groupby(['wikidata', 'page_title']):

            weighted_count = qpart[['count']].T.dot(qpart[['proba']]).iloc[0].iloc[0]

            weighted_cnt.append((qid, page_title, weighted_count))

        weighted_cnt = pd.DataFrame(weighted_cnt, columns=['wikidata', 'page_title', 'wcount']).\
            sort_values('wcount', ascending=False).reset_index(drop=True)

        tmp = pd.DataFrame([(qid, CountJob.voc[qid], wcount)
                            for qid, wcount in zip(weighted_cnt.wikidata.tolist(), weighted_cnt.wcount.tolist())],
                           columns=['wikidata', 'voc_index', 'wcount'])

        return tmp

    @staticmethod
    def initialize(voc, sqlite_file):

        CountJob.voc = voc
        CountJob.con = sqlite3.connect(sqlite_file)


def read_corpus(sqlite_file, processes):

    with sqlite3.connect(sqlite_file) as con:

        print('Reading entity linking table ...')
        df = pd.read_sql('SELECT * from entity_linking', con=con)
        print('done.')

        df = df.loc[(df.proba > 0.25) & (df.page_title.str.len() > 2)]

        voc = {qid: i for i, qid in enumerate(df.loc[df.wikidata.str.startswith('Q')].wikidata.unique())}

        data = []
        counter = 0
        position = [counter]

        def get_jobs():
            for ppn, part in tqdm(df.groupby('ppn')):
                yield CountJob(ppn, part)

        for tmp in prun(get_jobs(), initializer=CountJob.initialize, initargs=(voc, sqlite_file), processes=processes):

            data.append(tmp)
            counter += len(tmp)
            position.append(counter)

        data = pd.concat(data)

    m = csr_matrix((data.wcount.values, data.voc_index.values, position), dtype=float)

    corpus = gensim.matutils.Sparse2Corpus(m, documents_columns=False)

    return corpus, voc


@click.command()
@click.argument('sqlite-file', type=click.Path(exists=True), required=True, nargs=1)
@click.argument('model-file', type=click.Path(exists=False), required=True, nargs=1)
@click.option('--num-topics', default=10, help='Number of topics in LDA topic model. Default 10.')
@click.option('--entities-file', default=None, help="Knowledge-base of entity linking step.")
@click.option('--processes', default=4, help='Number of workers.')
@click.option('--corpus-file', default=None, help="Write corpus to this file.")
def run_lda(sqlite_file, model_file, num_topics, entities_file, processes, corpus_file):
    """
    Reads entity linking data from SQLITE_FILE.
    Computes LDA-topic model and stores it in MODEL_FILE.
    """

    if corpus_file is None or not os.path.exists(corpus_file):
        corpus, voc = read_corpus(sqlite_file, processes=processes)
    else:
        corpus = gensim.corpora.MmCorpus(corpus_file)

    # print("Number of documents: {}. Number of terms: {}.", corpus.num_docs, corpus.num_terms)

    if corpus_file is not None:
        print('Writing corpus to disk ...')

        gensim.corpora.MmCorpus.serialize(corpus_file, corpus)

        print('done.')

    if entities_file is not None:

        print("Reading id2work information from entities table ...")
        with sqlite3.connect(entities_file) as con:
            entities = pd.read_sql('SELECT * from entities', con=con).set_index('QID')

        entities = entities.merge(pd.DataFrame.from_dict(voc, orient='index', columns=['voc_index']),
                                  left_index=True, right_index=True)

        id2word = {row.voc_index: row.label for _, row in entities.iterrows()}

        print('done')
    else:
        id2word = {v: k for k, v in voc.items()}

    lda = LdaMulticore(corpus=corpus, num_topics=num_topics, id2word=id2word, workers=processes)

    lda.save(model_file)

