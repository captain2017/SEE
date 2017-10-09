# -*- coding: utf-8 -*-

# 当事人清洗统一接口，依靠规则判定走哪个入口

from . import court_etl_tool as cet
from . import case_reason_etl as cre
import os, codecs, re

path = os.popen("pwd").read().strip()+'/tools/'

with codecs.open(path+'law_words.txt', 'r', 'utf-8') as f:
    law_words = [line.strip() for line in f.readlines()]
    law_words = law_words[: law_words.index('----')]
    law_set = set(law_words)

_court_tool = cet.CourtETLTool()
_reason_tool = cre.entity_info

role_words = [u'被上诉人', u'被申请人', u'被申诉人', u'被执行人', u'被告人', u'被告', u'罪犯', u'原审原告', u'原审执行人', u'原审申请人', u'第三人', \
              u'申请执行人', u'原告', u'上诉人', u'执行人', u'申请人', u'申诉人', u'原审被告', u'原审被执行人, u‘二审被上诉人', u'原审被申请人', u'债权人',u'债务人' ]

role_set = set(role_words)

prov_keys = set([u'省',u'市',u'区',u'县',u'乡',u'村',u'镇',u'街',u'路'])

def split_element(lst, split_s):
    ret = []
    for item in lst:
        ret.extend(item.split(split_s))
    return ret

def parser_party(text, role=""):
    text = text[2:] if text[:2] in (u'告】',u'人】') else text
    text = re.sub(u'原文|原被告','',text)
    text_, key_ = text, []
    for item in law_words:
        if item in text_:
            key_.append(item)
            text_ = text_.replace(item, '')
    key_, entity_array = set(key_), []
    #print(key_)
    if key_ - role_set:
        #print(1)
        entity_array = _reason_tool(text)
    else:
        #print(2)
        entity_array = _court_tool.parser_litigant(text)

    if not role:
        entity_array = [d for d in entity_array if d['name'][-1] not in prov_keys or len(d['name']) < 5]
        return entity_array
    
    for i in range(len(entity_array)):
        if entity_array[i]['role'] == u'其他当事人':
            entity_array[i]['role'] = role
    entity_array = [d for d in entity_array if d['name'][-1] not in prov_keys or len(d['name']) < 5]
    return entity_array
