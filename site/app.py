
import os
import json

from flask import Flask
from flask import request
from flask import render_template

HOSTNAME = os.getenv('HOST')
SIG_PATH = os.getenv('SIGNIFIER')
SITE_PATH = os.path.join(SIG_PATH, 'site')
CONFIG_PATH = os.path.join(SIG_PATH, 'cfg')
DEFAULTS_PATH = os.path.join(SIG_PATH, 'sys', 'config_defaults')
CONFIG_FILES = {'config':'config.json',
                'values':'values.json',
                'rules':'rules.json'}
config = {}
values = {}
rules = {}


app = Flask(__name__)


@app.route("/")
def index():
    current_config = get_config('config')
    default_config = get_config('config', 'default')
    label_types(default_config)
    print(json.dumps(default_config))
    return render_template('index.html',
                           current_config=current_config,
                           default_config=default_config)


@app.route('/upload', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        f = request.files['the_file']
        if f is not None:
            f.save('uploaded_file.txt')


def get_config(file:str, *args):
    if 'default' in args:
        path = DEFAULTS_PATH
    else:
        path = CONFIG_PATH
    if file in CONFIG_FILES.keys():
        with open(os.path.join(path, CONFIG_FILES[file])) as c:
            try:
                return json.load(c)
            except json.decoder.JSONDecodeError:
                return {}


def label_types(input:dict):
    for key, val in input.items():
        if key != 'param_type':
            if isinstance(val, dict):
                label_types(val)
            else:
                val_type = type(val).__name__
                if val_type in ['int', 'float']:
                    val_type = 'number'
                input[key] = {'value':val, 'param_type':f'{val_type}'}
