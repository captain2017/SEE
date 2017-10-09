# -*- coding: utf-8 -*-
# API里的装饰器工具，主要用来做特殊统计使用的方法

from flask import Flask, request, Response
import json


def write_header(func):
    def wrapper():
        header = dict(request.headers)
        header['Is TYQ SB?'] = 'Yes!'
        print(json.dumps(header, ensure_ascii=False))
        return func()
    return wrapper

app = Flask(__name__)



@app.route('/test/', methods=['POST'])
@write_header
def test():
    d = json.loads(request.get_data())
    return Response(d['input'])

if __name__ == '__main__':
    app.run(host='10.50.87.150', port=8081)
