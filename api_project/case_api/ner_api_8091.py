# -*- coding: utf-8 -*-

# 案由实体识别新接口

from flask import Flask, request, Response
from ner_tools import case_ner as cner
import json, codecs

_ner = cner.entity_extract

app = Flask(__name__)

@app.route('/v1/case_ner', methods=['POST'])
def case_ner():
    d = json.loads(request.get_data())
    if 'text' in d:
        corps, persons  = _ner(d['text'])
        return Response(json.dumps({'corps':corps, 'persons':persons}, ensure_ascii=False), mimetype='application/json')
    else:
        return Response('{"error_type":"No text found!"}', mimetype='application/json')

if __name__  == '__main__':
    
    app.run(host='10.50.87.162', port=8091, threaded=True)
