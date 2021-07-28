import os
import logging
from flask import Flask, send_from_directory, redirect, jsonify, send_file
import pandas as pd
from sqlite3 import Error
import sqlite3
from qurator.sbb.xml import get_entity_coordinates

import io
from PIL import Image, ImageDraw


app = Flask(__name__)

app.config.from_json('config.json' if not os.environ.get('CONFIG') else os.environ.get('CONFIG'))

logger = logging.getLogger(__name__)


class Digisam:

    _conn = None

    def __init__(self, data_path):

        self._data_path = data_path

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

    def get(self, ppn):

        if Digisam._conn is None:
            Digisam._conn = self.create_connection(self._data_path)

        df = pd.read_sql_query("select file_name, text from text where ppn=?;", Digisam._conn, params=(ppn,)). \
            sort_values('file_name')

        return df


digisam = Digisam(app.config['FULLTEXT_PATH'])


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

    df = digisam.get(ppn)

    if len(df) == 0:

        df = digisam.get('PPN' + ppn)

        if len(df) == 0:

            if ppn.startswith('PPN'):
                df = digisam.get(ppn[3:])

            if len(df) == 0:

                return 'bad request!', 400

    text = ''
    for row_index, row_data in df.iterrows():

        if row_data.text is None:
            continue

        text += row_data.text + " "

    ret = {'text': text, 'ppn': ppn}

    return jsonify(ret)


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
