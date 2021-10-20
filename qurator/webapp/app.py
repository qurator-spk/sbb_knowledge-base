import os
import logging
from flask import Flask, request, send_from_directory, redirect, jsonify, send_file
import pandas as pd
from sqlite3 import Error
import sqlite3
from qurator.sbb.xml import get_entity_coordinates
from flask_htpasswd import HtPasswdAuth

import io
from PIL import Image, ImageDraw
import json
import random
import string
import re
import numpy as np

from multiprocessing import Semaphore

app = Flask(__name__)

app.config.from_json('config.json' if not os.environ.get('CONFIG') else os.environ.get('CONFIG'))

app.config['FLASK_HTPASSWD_PATH'] = app.config['PASSWD_FILE'] \
    if not os.environ.get('PASSWD_FILE') else os.environ.get('PASSWD_FILE')

app.config['FLASK_AUTH_REALM'] = app.config['AUTH_REALM']
app.config['FLASK_SECRET'] = \
    ''.join(random.SystemRandom().choice(string.ascii_uppercase + string.digits) for _ in range(40))

htpasswd = HtPasswdAuth(app)

logger = logging.getLogger(__name__)


class Digisam:

    _fulltext_conn = None
    _ner_el_conn = None
    _meta_data = None

    def __init__(self, fulltext_path, ner_el_path):

        self._sem = Semaphore(1)

        self._fulltext_data_path = fulltext_path
        self._ner_el_path = ner_el_path

    @staticmethod
    def create_connection(db_file):
        try:
            logger.debug('Connection to database: {}'.format(db_file))

            conn = sqlite3.connect(db_file, check_same_thread=False)

            conn.execute('pragma journal_mode=wal')

            return conn
        except Error as e:
            logger.error(e)

        return None

    def get_fulltext(self, ppn):

        with self._sem:

            if Digisam._fulltext_conn is None:
                Digisam._fulltext_conn = self.create_connection(self._fulltext_data_path)

        df = pd.read_sql_query("select file_name, text from text where ppn=?;", Digisam._fulltext_conn, params=(ppn,)).\
            sort_values('file_name')

        return df

    def get_ner(self, ppn):

        with self._sem:
            if Digisam._ner_el_conn is None:
                Digisam._ner_el_conn = self.create_connection(self._ner_el_path)

        docs = pd.read_sql('select * from tagged where ppn==?', params=(ppn,), con=Digisam._ner_el_conn)

        if docs is None or len(docs) == 0:
            return []

        docs['page'] = docs.file_name.str.extract('.*?([0-9]+).*?').astype(int)

        ner_result = []
        for _, doc_row in docs.sort_values('page').iterrows():
            ner_result += [[{'word': word, 'prediction': tag} for word, tag in zip(sen_text, sen_tags)]
                           for sen_text, sen_tags in zip(json.loads(doc_row.text), json.loads(doc_row.tags))]

        return ner_result

    def get_el_con(self):

        with self._sem:
            if Digisam._ner_el_conn is None:
                Digisam._ner_el_conn = self.create_connection(self._ner_el_path)

                Digisam._ner_el_conn. \
                    execute('create table if not exists "entity_linking_gt"'
                            '("index" integer primary key,"user" TEXT, "entity_id" TEXT, "page_title" TEXT, '
                            '"wikidata" TEXT, "ppn" TEXT, start_page INTEGER, stop_page INTEGER, "label", TEXT)')

                Digisam._ner_el_conn. \
                    execute('create index if not exists idx_place_gt on '
                            'entity_linking_gt(entity_id, wikidata, ppn, start_page, stop_page, user);')

                Digisam._ner_el_conn. \
                    execute('create index if not exists idx_ppn_gt on '
                            'entity_linking_gt(ppn, user);')

        return self._ner_el_conn

    def get_el(self, ppn, threshold):

        df = pd.read_sql('select * from entity_linking where ppn=?', params=(ppn,), con=self.get_el_con())

        df = df.loc[df.proba > threshold]

        el_result = \
            {entity_id:
                 {'ranking': [[row.page_title, {'proba_1': row.proba, 'wikidata': row.wikidata,
                                                'start_page': row.start_page, 'stop_page': row.stop_page}]
                              for _, row in candidates.iterrows()]}
             for entity_id, candidates in df.groupby('entity_id')}

        return el_result

    def get_meta_data(self, ppn):

        with self._sem:
            if self._meta_data is None:

                roles = ['name{}_role_roleTerm'.format(i) for i in range(0, 75)]

                self._meta_data = pd.read_pickle(app.config['META_DATA'])

                has_author = self._meta_data.loc[
                    ((self._meta_data[roles] == 'aut').sum(axis=1) > 0)
                    | ((self._meta_data[roles] == 'asn').sum(axis=1) > 0)]

                aut_roles = pd.DataFrame((has_author[roles] == 'aut').
                                         idxmax(axis=1).str.replace("role_roleTerm", "displayForm"),
                                         columns=['aut_column'])

                asn_roles = pd.DataFrame((has_author[roles] == 'asn').
                                         idxmax(axis=1).str.replace("role_roleTerm", "displayForm"),
                                         columns=['asn_column'])

                self._meta_data = self._meta_data.merge(aut_roles, left_index=True, right_index=True, how="outer")
                self._meta_data = self._meta_data.merge(asn_roles, left_index=True, right_index=True, how="outer")

        if ppn in self._meta_data.index:

            return self._meta_data.loc[ppn].astype(str).to_dict()

        if 'PPN' + ppn in self._meta_data.index:

            return self._meta_data.loc['PPN' + ppn].astype(str).to_dict()


digisam = Digisam(fulltext_path=app.config['FULLTEXT_PATH'],
                  ner_el_path=app.config['NER+EL-PRECOMPUTATION'])


class TopicModels:

    def __init__(self, model_dir):
        self._model_dir = model_dir
        self._models = {}
        self._corpus = {}

        self._config = pd.DataFrame.from_dict(app.config['TOPIC_MODELS']).dropna(how="any")

    def get_model(self, file):

        abs_file = os.path.join(self._model_dir, file)

        if file in self._models:
            return self._models[file]['model']

        with open(abs_file, 'r') as f:
            ret = json.load(f)

        token_table = pd.DataFrame.from_dict(ret['token.table'])

        docs = []
        for key, val in ret['docs'].items():
            tmp = pd.DataFrame.from_dict(val)
            tmp['topic'] = key
            docs.append(tmp)

        docs = pd.concat(docs)

        del ret['docs']

        self._models[file] = {'model': ret, 'tokens': token_table, 'docs': docs}

        return ret

    def get_tokens(self, file):

        if file not in self._models:
            self.get_model(file)

        return self._models[file]['tokens']

    def get_docs(self, file):

        if file not in self._models:
            self.get_model(file)

        return self._models[file]['docs']

    def get_corpus(self, file):

        corpus_file = self._config.loc[self._config.data == file].corpus.iloc[0]

        if corpus_file in self._corpus:

            return self._corpus[corpus_file]

        abs_file = os.path.join(self._model_dir, corpus_file)

        corpus = pd.read_pickle(abs_file).reset_index(drop=True)

        self._corpus[corpus_file] = corpus

        return corpus


topic_models = TopicModels(app.config['TOPIC_MODEL_DIR'])


@app.route('/')
def entry():
    return redirect("/index.html", code=302)


@app.route('/authenticate')
@htpasswd.required
def authenticate(user):

    return jsonify({'user': user})


@app.route('/auth-test')
@htpasswd.required
def auth_test(user):

    return jsonify({'user': user})


@app.after_request
def after(response):

    if request.url.endswith('auth-test'):
            response.headers.remove('WWW-Authenticate')

    return response


@app.route('/meta_data', methods=['POST'])
@app.route('/meta_data/<ppn>', methods=['GET'])
def get_meta_data(ppn=None):
    
    def author_filter(_meta):
        
        _author = _meta[_meta["aut_column"]] if _meta["aut_column"] != 'nan' is not None else None

        _author = _author if _author is not None else \
            _meta[_meta["asn_column"]] if _meta["asn_column"] != 'nan' is not None else None

        _author = _author if _author is not None and _author != 'None' else _meta["originInfo-publication0_publisher"]
        _author = _author if _author is not None and _author != 'None' else ""
        
        return _author

    if request.method == 'GET':

        meta = digisam.get_meta_data(ppn)

        return jsonify({"title": meta.get("titleInfo_title", "Unknown"), "author": author_filter(meta),
                        "date": meta["originInfo-publication0_dateIssued"]})
    else:
        data = request.json

        ret = {}

        for ppn in data['ppns']:
            meta = digisam.get_meta_data(ppn)

            ret[ppn] = {"title": meta.get("titleInfo_title", "Unknown"), "author": author_filter(meta),
                        "date": meta["originInfo-publication0_dateIssued"]}

        return jsonify(ret)


@app.route('/ppnexamples')
def get_ppnexamples():
    return jsonify(app.config['PPN_EXAMPLES'])


@app.route('/topic_docs/<file>/<topic>')
@app.route('/topic_docs/<file>/<topic>/<order_by>')
def get_topic_docs(file, topic, order_by=None):

    docs = topic_models.get_docs(file)

    topic_docs = docs.loc[docs.topic == topic]

    if order_by is not None:
        order_by_qids = re.findall('Q[0-9]+', order_by)

        corpus = topic_models.get_corpus(file)

        tmp = topic_docs.merge(corpus, on="ppn")

        tmp = tmp.loc[tmp.wikidata.isin(order_by_qids)]

        topic_docs = \
            pd.DataFrame([(ppn, part.title.iloc[0], part.wcount.sum()) for ppn, part in tmp.groupby('ppn')],
                         columns=['ppn', 'title', 'wcount']).sort_values('wcount', ascending=False).\
                reset_index(drop=True)

    ret = [row.ppn for _, row in topic_docs.iterrows()]

    return jsonify(ret)


@app.route('/topic_models')
@app.route('/topic_models/<file>')
def get_topic_models(file=None):

    if file is None or len(file) == 0:

        return jsonify(
            [i for _, i in
             pd.DataFrame.from_dict(app.config['TOPIC_MODELS']).dropna(how="any").to_dict(orient="index").items()])
    else:
        ret = topic_models.get_model(file)

        return jsonify(ret)


@app.route('/suggestion/<file>/<text>')
def get_suggestion(file, text):

    search_parts = re.findall(r'Q[0-9]+\w*\((.*?)\)', text)

    if len(search_parts) > 0:
        search_str = search_parts[-1]
    else:
        search_str = text

    tokens = topic_models.get_tokens(file)

    sugg = tokens.loc[tokens.Term.str.contains(search_str)].drop_duplicates('Term').sort_values('Freq', ascending=False)

    return jsonify(sugg.Term.tolist())


@app.route('/digisam-fulltext/<ppn>')
def fulltext(ppn):

    df = digisam.get_fulltext(ppn)

    if len(df) == 0:

        df = digisam.get_fulltext('PPN' + ppn)

        if len(df) == 0:

            if ppn.startswith('PPN'):
                df = digisam.get_fulltext(ppn[3:])

            if len(df) == 0:

                return 'bad request!', 400

    text = ''
    for row_index, row_data in df.iterrows():

        if row_data.text is None:
            continue

        text += row_data.text + " "

    ret = {'text': text, 'ppn': ppn}

    return jsonify(ret)


@app.route('/digisam-ner/<ppn>')
def ner(ppn):

    ner_result = digisam.get_ner(ppn)

    if len(ner_result) == 0:

        ner_result = digisam.get_ner('PPN' + ppn)

        if len(ner_result) == 0:

            if ppn.startswith('PPN'):
                ner_result = digisam.get_ner(ppn[3:])

            if len(ner_result) == 0:
                return 'bad request!', 400

    return jsonify(ner_result)


@app.route('/digisam-el/<ppn>/<threshold>')
def el(ppn, threshold=0.15):

    threshold = float(threshold)

    el_result = digisam.get_el(ppn, threshold)

    if len(el_result) == 0:

        el_result = digisam.get_el('PPN' + ppn)

        if len(el_result) == 0:

            if ppn.startswith('PPN'):
                el_result = digisam.get_el(ppn[3:])

            if len(el_result) == 0:
                return 'bad request!', 400

    return jsonify(el_result)


@app.route('/annotate/<ppn>', methods=['GET', 'POST'])
@htpasswd.required
def annotations(user, ppn):

    if request.method == 'GET':

        gt = pd.read_sql("SELECT * from entity_linking_gt WHERE user=? AND ppn=?",
                         con=digisam.get_el_con(), params=(user, ppn)).reset_index()

        ret = {}

        for entity_id, entries in gt.groupby('entity_id'):

            tmp = {}
            for page_title, candidates in entries.groupby('page_title'):

                last_label = candidates.sort_values('index', ascending=False).iloc[0].label

                if last_label == '?':
                    continue

                tmp[page_title] = last_label

            if len(tmp) == 0:
                continue

            tmp['length'] = len(tmp)

            ret[entity_id] = tmp

        # print(ret)

        return jsonify(ret)

    annotation = request.json

    print(user, annotation)

    new_entry = pd.DataFrame.from_dict(annotation['candidate'][1], orient='index').T

    new_entry = new_entry.drop(columns=['proba_1'])

    new_entry['page_title'] = annotation['candidate'][0]
    new_entry['label'] = annotation['label']
    new_entry['entity_id'] = annotation['entity']
    new_entry['ppn'] = ppn
    new_entry['user'] = user

    new_entry.to_sql('entity_linking_gt', con=digisam.get_el_con(), if_exists='append', index=False)

    return "OK", 200


def find_file(path, ppn, page, ending):

    file = (8 - len(str(page))) * '0' + page

    if os.path.exists("{}/{}/{}{}".format(path, ppn, file, ending)):
        return "{}/{}/{}{}".format(path, ppn, file, ending)
    elif os.path.exists("{}/PPN{}/{}{}".format(path, ppn, file, ending)):
        return "{}/PPN{}/{}{}".format(path, ppn, file, ending)
    elif ppn.startswith('PPN') and os.path.exists("{}/{}/{}{}".format(path, ppn[3:], file, ending)):
        return "{}/{}/{}{}".format(path, ppn[3:], file, ending)
    else:
        return None


@app.route('/image/<ppn>/<page>')
def get_image(ppn, page):

    image_file = find_file(app.config['IMAGE_PATH'], ppn, page, '.tif')

    if image_file is None:
        return 'bad request!', 400

    img = Image.open(image_file)

    img = img.convert('RGB')

    alto_file = find_file(app.config['ALTO_PATH'], ppn, page, '.xml')

    if alto_file is not None:

        ner_coordinates, entity_map = get_entity_coordinates(alto_file, img)

        draw = ImageDraw.Draw(img, 'RGBA')

        for idx, row in ner_coordinates.iterrows():

            draw.rectangle(xy=((row.x0, row.y0), (row.x1, row.y1)),
                           fill=(255 if row.ner_id.startswith('PER') else 0,
                                 255 if row.ner_id.startswith('LOC') else 0,
                                 255 if row.ner_id.startswith('ORG') else 0, 50))
    buffer = io.BytesIO()
    img.save(buffer, "JPEG")
    buffer.seek(0)

    return send_file(buffer, mimetype='image/jpeg')


@app.route('/<path:path>')
def send_js(path):
    return send_from_directory('static', path)

