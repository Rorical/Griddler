from flask import Flask, request, jsonify
from flask_cors import CORS, cross_origin
import pimg

app = Flask(__name__)

cors = CORS(app)
app.config['CORS_HEADERS'] = 'Content-Type'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

ALLOWED_EXTENSIONS = set(['png', 'jpg', 'jpeg'])
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS

pm = None
@app.before_first_request
def init():
    global pm
    pm = pimg.Pimg()

@app.route('/ping')
@cross_origin()
def ping():
    return 'pong'

@app.route('/query',  methods=['POST', 'GET'])
@cross_origin()
def query():
    if request.method == "POST":
        file = request.files['file']
        if file and allowed_file(file.filename):
            result = pm.search(file.read())
            return jsonify({"status": 0, "result": result})
    elif request.method == "GET":
        url = request.args.get("imgurl","")
        if url and allowed_file(url):
            result = pm.searchurl(url)
            if type(result) == int:
                return jsonify({"status": result})
            return jsonify({"status": 0, "result": result})
    return jsonify({"status":-1})
if __name__ == '__main__':
    app.run("0.0.0.0",port=8800)