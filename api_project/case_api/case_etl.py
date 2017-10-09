# -*- coding: utf-8 -*-

# 包含以下应用

'''
1. 开庭案由清洗 --   /v1/court/case_reason     郑巨隆开发
2. 开庭原被告清洗 -- /v1/court/plaintiff_defendant  郑巨隆开发
3. 法院规范清洗 --  /v1/court/court_name  田英巧开发
4. 当事人类型识别 -- /v1/court/party_type  郑巨隆开发
5. 当事人清洗  -- /v1/court/party   郑巨隆开发
6. 失信主体识别 -- /v1/discredit    郑巨隆开发
7. 文书原被告清洗 -- /v1/doc/palintiff_defendant   田英巧开发
8. 当事人实体识别-独立接口 -- /v1/base/model_rec   郑巨隆开发
9. 文书裁定结果清洗 -- /v1/doc/result 田英巧开发
10.文书原被告、裁定结果清洗 --/v1/doc/recognize   田英巧开发
11. 失信comment清洗 -- /v1/discredit_comment    郑巨隆开发
'''

from flask import Flask, request, Response
import json, codecs
from tools import case_reason_etl as cre
from tools import court_etl_tool as cet
from tools_t import api_court_outside as aco
from tools import black_name_code_extract as bnce
#from tools_t import api_charge_person as acp
from tools import uni_party as up
#from tools_t import api_charge_result as acr
from tools_t import api_charge_recognize as acre
from tools import black_comment_parser as bcp

ak_file, header_file = 'aks.txt', 'headers.txt'

with codecs.open(ak_file, 'r', 'utf=8') as f:
    access_keys = set([line.strip() for line in f.readlines()])

def print_header(func):
    def wrapper():
        header = dict(request.headers)
        print(header)
        if 'Access-Key' not in header or header['Access-Key'] not in access_keys:
            return "error access_key"
        header['Is TYQ SB?'] = 'Yes!'
        header_log = json.dumps(header, ensure_ascii=False)
        with codecs.open(header_file, 'a', 'utf-8') as f:
            f.write(header_log)
            f.write('\n')
        return func()
    return wrapper

case_reason_tool = cre.entity_info   # 案由清洗函数
_court_etl_tool = cet.CourtETLTool() # 开庭清洗工具
court_name_tool = aco.CourtETL()  #法院规范清洗工具
_model_corp = cre._model_corp    # 当事人类型分类器
_black_tool = bnce.m            # 失信主体工具
#person_tool = acp.PersonETL()  #文书原被告清洗函数
_parser_partner = up.parser_party  #统一当事人分流入口
recognize_tool = acre.PersonETL()  #文书原被告裁定结果清洗函数
_black_comment_parser = bcp.BlackComment()

app = Flask(__name__)

@app.route('/v1/court/case_reason', methods=['POST'])
def case_reason():
    d = json.loads(request.get_data())
    if 'case_reason' in d:
        reason_ = d['case_reason']
    else:
        return Response('{"error_type":"No case_reason found."}', mimetype='application/json')
    s = _parser_partner(reason_)
    return Response(json.dumps({'party':s}, ensure_ascii=False), mimetype='application/json')
    """
    s = case_reason_tool(reason_)
    for i, d in enumerate(s):
        s[i]['role'] = s[i]['role'] if s[i]['role'] else u'其他当事人'
    return Response(json.dumps({'party':s}, ensure_ascii=False), mimetype='application/json')"""

@app.route('/v1/court/plaintiff_defendant', methods=['POST'])
def court_linker():
    d = json.loads(request.get_data())
    if 'plaintiff' in d and 'defendant' in d:
        plaintiff, defendant = d['plaintiff'], d['defendant']
    else:
        return Response('{"error_type":"Neither plaintiff nor defendant found."}', mimetype='application/json')
    s = _parser_partner(plaintiff, role="原告") + _parser_partner(defendant, role="被告")
    return Response(json.dumps({'party':s}, ensure_ascii=False), mimetype='application/json')
    """
    plaintiff, defendant = _court_etl_tool.etl_plaintiff(plaintiff), _court_etl_tool.etl_plaintiff(defendant)
    s = _court_etl_tool.get_entity(plaintiff, defendant)
    return Response(json.dumps({'party':s}, ensure_ascii=False), mimetype='application/json')"""

@app.route('/v1/court/court_name', methods=['POST'])
def CourtName():
    d = json.loads(request.get_data())
    #print(d)
    if 'court_name' in d and 'content' in d :
        court_name, content = d['court_name'], d['content']
    else:
        return Response('{"error_type":"Neither court_name nor content found."}', mimetype='application/json')
   # court_name, content = request.form.get('court_name',default=''), request.form.get('content',default='')
    result  = court_name_tool.norm_court(court_name, content)
    end = {"court":result[0],"province":result[1],"city":result[2]}
    return Response(json.dumps(end, ensure_ascii=False), mimetype='application/json')

@app.route('/v1/court/party_type', methods=['POST'])
def party_type():
    d = json.loads(request.get_data())
    if 'party' in d:
        _ = d['party']
        for i, dd in enumerate(_):
            _[i]['type'] = _model_corp.entity_type(dd['name']) if 'name' in dd else u'其他当事人'
        d['party'] = _
    else:
        return Response('{"error_type":"No party found."}', mimetype='application/json')
    return Response(json.dumps(d, ensure_ascii=False), mimetype='application/json')

@app.route('/v1/court/party', methods=['POST'])
def paser_litigant():
    d = json.loads(request.get_data())
    if 'party' in d:
        #s = _court_etl_tool.parser_litigant(d['party'])
        s = _parser_partner(d['party'])
        d['party'] = s
        return Response(json.dumps(d, ensure_ascii=False), mimetype='application/json')
    else:
        return Response('{"error_type":"No party found."}', mimetype='application/json')

@app.route('/v1/discredit', methods=['POST'])
def discredit():
    d = json.loads(request.get_data())
    keys_ = ['alias','credit','idno','name','org','reg','type']
    if 'name' in d and 'idno' in d and 'legal_person' in d:
        s = _black_tool.get_info(d['name'], d['idno'], d['legal_person'])
        for i, d_ in enumerate(s['party']):
            for key in keys_:
                if key not in d_:
                    d_[key] = ''
            s['party'][i] = d_
        for i, d_ in enumerate(s['legal_person']):
            if 'idno' not in d_:
                d_['idno'] = ''
            s['legal_person'][i] = d_
        return Response(json.dumps(s, ensure_ascii=False), mimetype='application/json')
    else:
         return Response('{"error_type":"No name, legal_person and idno found."}', mimetype='application/json')
"""
@app.route('/v1/doc/plaintiff_defendant', methods=['POST'])
def ChargePerson():
    d = json.loads(request.get_data())
    if 'title' in d and 'content' in d:
        title, content = d['title'], d['content']
    else:
        return Response('{"error_type":"Neither title nor content found."}', mimetype='application/json')
    s = person_tool.PersonResult(title,content)
    return Response(json.dumps({'party':s}, ensure_ascii=False), mimetype='application/json')
"""
@app.route('/v1/base/model_rec', methods=['POST'])
@print_header
def model_rec():
    d = json.loads(request.get_data())
    if 'name' in d:
        typ = _model_corp.entity_type(d['name'])
        return Response(json.dumps({'type':typ}, ensure_ascii=False), mimetype='application/json')
    else:
        return Response('{"error_type":"No name found."}', mimetype='application/json')
"""
@app.route('/v1/doc/result', methods=['POST'])
def charge_result():
    d = json.loads(request.get_data())
    if 'content' in d :
        content = d['content']
    else:
        return Response('{"error_type":"No content found."}', mimetype='application/json')
    s = acr.ChargeResult(content)
    return Response(json.dumps({'result':s}, ensure_ascii=False), mimetype='application/json')
"""
@app.route('/v1/doc/recognize', methods=['POST'])
def ChargeRec():
    d = json.loads(request.get_data())
    if 'title' in d and 'content' in d:
        title, content = d['title'], d['content']
    else:
        return Response('{"error_type":"Neither title nor content found."}', mimetype='application/json')
    s = recognize_tool.PersonResult(title,content)
    return Response(json.dumps({'party':s[0],'result':s[1]}, ensure_ascii=False), mimetype='application/json')

@app.route('/v1/discredit_comment', methods=['POST'])
def DiscreditComment():
    d = json.loads(request.get_data())
    if 'comment' in d:
        res = _black_comment_parser.search_all(d['comment'])
        return Response(json.dumps(res, ensure_ascii=False), mimetype='application/json')
    else:
        return Response('{"error_type":"No comment found."}', mimetype='application/json')

if __name__ == '__main__':
    
    app.run(host='10.50.87.150', port=8080, threaded=True)
