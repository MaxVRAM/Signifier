
import os
import sys
import time

import subprocess

from flask import Flask
from flask import request
from flask import redirect
from flask import send_file
from flask import render_template
from werkzeug.utils import secure_filename

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
app.secret_key = b'_5#y2L"sdb/fae\n\xec]/'


app.config['UPLOAD_FOLDER'] = CONFIG_PATH
@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        print(f'User posted: {request}')

        print(request.files)
        
        if 'file' not in request.files:
            print('No file part in POST')
            return redirect(request.url)
        file = request.files['file']
        print(file)
        print(file.filename)
        print(file.filename in CONFIG_FILES.values())
        if file.filename == '':
            print('No file selected')
            return redirect(request.url)
        if file is not None and file.filename in CONFIG_FILES.values():
            print('hello?')
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            print(f'Config file has been updated: {file.filename}')
            return render_template('index.html', hostname=HOSTNAME)

    return render_template('index.html', hostname=HOSTNAME)


@app.route('/download/<filename>')
def download_config(filename):
    if filename in CONFIG_FILES.values():
        file_path = os.path.join(CONFIG_PATH, filename)
        if os.path.isfile(file_path):
            print(f'Remote user requesting download of {file_path}')
            return send_file(file_path, as_attachment=True, attachment_filename='')
    return render_template('index.html', hostname=HOSTNAME)


@app.route('/download_default/<filename>')
def download_default(filename):
    if filename in CONFIG_FILES.values():
        file_path = os.path.join(DEFAULTS_PATH, filename)
        if os.path.isfile(file_path):
            print(f'Remote user requesting download of {file_path}')
            return send_file(file_path, as_attachment=True, attachment_filename='')
    return render_template('index.html', hostname=HOSTNAME)


@app.route('/restart_signifier')
def restart_signifier():
    print('Remote user requested reboot of this machine. Restarting in 5 seconds...')
    time.sleep(5)
    subprocess.call(['sudo', '/sbin/reboot'])
    #os.system("reboot")
    return render_template('index.html', hostname=HOSTNAME)

