import os
import logging
from flask import Flask, send_from_directory, redirect, jsonify, send_file
import pandas as pd
from sqlite3 import Error
import sqlite3
from qurator.sbb.xml import get_entity_coordinates

import io
from PIL import Image, ImageDraw
import json

app = Flask(__name__)

app.config.from_json('config.json' if not os.environ.get('CONFIG') else os.environ.get('CONFIG'))

logger = logging.getLogger(__name__)


class Digisam:

    _fulltext_conn = None
    _ner_el_conn = None

    def __init__(self, fulltext_path, ner_el_path):

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

        if Digisam._fulltext_conn is None:
            Digisam._fulltext_conn = self.create_connection(self._fulltext_data_path)

        df = pd.read_sql_query("select file_name, text from text where ppn=?;", Digisam._fulltext_conn, params=(ppn,)).\
            sort_values('file_name')

        return df

    def get_ner(self, ppn):

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

    def get_el(self, ppn, threshold):

        if Digisam._ner_el_conn is None:
            Digisam._ner_el_conn = self.create_connection(self._ner_el_path)

        df = pd.read_sql('select * from entity_linking where ppn=?', params=(ppn,), con=Digisam._ner_el_conn)

        df = df.loc[df.proba > threshold]

        el_result = \
            {entity_id:
                 {'ranking': [[row.page_title, {'proba_1': row.proba, 'wikidata': row.wikidata}]
                              for _, row in candidates.iterrows()]}
             for entity_id, candidates in df.groupby('entity_id')}

        return el_result


digisam = Digisam(fulltext_path=app.config['FULLTEXT_PATH'],
                  ner_el_path=app.config['NER+EL-PRECOMPUTATION'])


@app.route('/')
def entry():
    return redirect("/index.html", code=302)


@app.route('/ppnexamples')
def get_ppnexamples():
    return jsonify(app.config['PPN_EXAMPLES'])


@app.route('/topic_models')
def get_topic_models():
    return jsonify(app.config['TOPIC_MODELS'])


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
