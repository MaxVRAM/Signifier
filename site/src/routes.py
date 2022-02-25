from flask import render_template
from flask import request
from app import app


@app.route("/")
def hello_world():
    return "<p>Hello, World!</p>"


@app.route('/upload', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        f = request.files['the_file']
        f.save('uploaded_file.txt')
