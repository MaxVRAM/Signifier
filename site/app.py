
import os
import json

from flask import Flask
from flask import request
from flask import render_template

HOSTNAME = os.getenv('HOST')
SIG_PATH = os.getenv('SIGNIFIER')
SITE_PATH = os.path.join(SIG_PATH, 'site')
CFG_PATH = os.path.join(SIG_PATH, 'cfg')
print(f'{SIG_PATH}')
DEFAULTS_PATH = os.path.join(SIG_PATH, 'sys', 'default_configs')
CONFIG_FILES = {'config':'config.json',
                'values':'values.json',
                'rules':'rules.json'}
config = {}
values = {}
rules = {}


app = Flask(__name__)


@app.route("/")
def index():
    return render_template('index.html',
                           hostname='testHost',
                           config=get_config('config'))


@app.route('/upload', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        f = request.files['the_file']
        if f is not None:
            f.save('uploaded_file.txt')


def get_config(file:str):
    if file in CONFIG_FILES.keys():
        with open(os.path.join(CFG_PATH, CONFIG_FILES[file])) as c:
            try:
                return json.load(c)
            except json.decoder.JSONDecodeError:
                return {}
