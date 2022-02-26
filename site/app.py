
from inspect import istraceback
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
        try:
            if val.lower() in ['true, false']:
                input[key] = {'value':val, 'type':'bool'}
                print('bool!')
            else:
                raise AttributeError
        except AttributeError:
            try:
                float(val)
                print('number!')
                input[key] = {'value':val, 'type':'number'}
            except (ValueError, TypeError):
                if isinstance(val, str):
                    print('string!')
                    input[key] = {'value':val, 'type':'string'}
                elif isinstance(val, dict):
                    print(f'is dict:    {val}')
                    label_types(val)
                else:
                    print('what?')

        print(f'key: {key}    value: {val}')
        print()

        # except (ValueError, TypeError):
        #     if isinstance(val, str):

        #     else:

        #         print('iterable')
        #     #     input[key].update({'value':input[val], 'type':'interable'})
        #         label_types(input[key])
        # #print(f'key: {key}    value: {val}')
