# -*- coding: utf-8 -*-

# 共同利益人接口

from flask import Flask, request, Response
import json, os, requests

app = Flask(__name__)

@app.route('/v1/job/common-interest', methods=['POST'])
def common_interest():
    d = json.loads(request.get_data())
    if 'uuid' not in d:
        return Response(json.dumps({'error':'no uuid found'}), mimetype='application/json')
    os.system('nohup python main_process.py >> nohup.out &')
    uuid = d['uuid']
    with open('uuid.txt', 'w') as f:
        f.write(uuid)
    return Response('{"status":"It is running..."}', mimetype='application/json')

if __name__ == '__main__':
    
    app.run(host='10.50.87.150', port=8091)
