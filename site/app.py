import os
import time
import json

from flask import Flask, render_template

from src.utils import split_config

app = Flask(__name__)


# TODO move config from hardcoded location
CONFIG_FILE = '/home/pi/Signifier/config.json'
CONFIG_DEFAULT = '/home/pi/Signifier/config_default.json'
config_dict = None

with open(CONFIG_FILE) as c:
    config_dict = json.load(c)

HOSTNAME = config_dict['general']['hostname']

for module in config_dict.values():
    print([type(v) for v in module.values()])

@app.route("/")
def index():
    settings, map_values, mappings, jobs, categories = split_config(config_dict)
    return render_template('index.html', hostname=HOSTNAME, config=config_dict)