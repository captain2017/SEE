# -*- coding: utf-8 -*-

# 案件类型提取

import re, json, codecs
import os
import pymysql as pm
import time
from functools import reduce

def time_it(func):
    def wrapper(self, content):
        t11 = time.time()
        res = func(self, content)
        t22 = time.time()
        print("It took {} seconds".format(t22-t11))
        return res
    return wrapper


path = os.popen("pwd").read().strip() + '/tools/'
case_type_file = path + 'grade_case_types.txt'

with codecs.open(case_type_file, 'r', 'utf-8') as f:
    case_types = [line.strip().split('\t') for line in f.readlines()]
    case_type_first = {line[1]:line[0] for line in case_types}
    case_type_second = {line[2]:line[1] for line in case_types if line[2] != 'N'}
    case_types = sorted(list(set(reduce(lambda x,y:x+y, case_types))), key=lambda x:-len(x))
    case_types.remove('N')

def combine(tuple_list):
    d = {}
    for a, b in tuple_list:
        if b in d:
            d[b].append(a)
        else:
            d[b] = [a]
    lst = [{'second':key, 'third':list(filter(bool, val))} for key, val in d.items()]
    return lst
    
class StrSearchTool(object):
    
    def __init__(self, target_strings):
        self.target_strings = re.compile('|'.join(target_strings))
        
    def extract_target_strings(self, text):
        strings = list(set(self.target_strings.findall(text)))
        d = []
        for s in strings:
            if s in case_type_second:
                _ = {'first':case_type_first[case_type_second[s]], 'second':case_type_second[s], 'third':s}
            elif s in case_type_first:
                _ = {'first':case_type_first[s], 'second':s, 'third':''}
            else:
                _ = {'first':s, 'second':'', 'third':''}
            d.append(_)
        return d


class CaseTypeTool(StrSearchTool):
    
    def __init__(self, case_types):
        super(CaseTypeTool, self).__init__(case_types)
        self.case_types = self.target_strings
        self.get_case_type = self.extract_target_strings
        self.jsonify = lambda x:x #json.dumps(x, ensure_ascii=False)
    
    #@time_it
    def process_case_reason(self, case_reason):
        if not case_reason:
            return self.jsonify([])
            
        this_case_type = self.get_case_type(case_reason)
        if this_case_type:
            return self.jsonify(this_case_type)
            
        return self.jsonify([])

class DocCaseType(CaseTypeTool):
    def __init__(self, case_types):
        super(DocCaseType, self).__init__(case_types)
        self.get_doc_case_type = self.process_case_reason
    
    #@time_it
    def ChargeFormat(self,charge):
        '''去掉文书的html、冗余字符等'''
        if not charge:
            return ''
        charge = re.sub(u'[<|＜].*?[>|＞]', '', charge)
        charge = re.sub(' |\t|\r|\n|　|    | ','', charge)
        charge = re.sub('&[a-zA-Z0-9;]{0,20}','',charge) 
        pun_list = ['Title','PubDate','Html','"','{','}','nbsp;','amp;divide;','\\xa0','nbsp']
        for item in pun_list:
            charge = charge.replace(item,'')
        return charge

    #@time_it
    def ChargeEtl(self,charge):
        '''提取含有一案的句子'''
        for item in charge.split('。'):
            if '一案' in item and ')一案' not in item:
                return item.split('一案')[0]
        return '' 
    
    #@time_it2
    def doc_case_type(self,title,content):
        '''提取案件类型'''
        
        content = self.ChargeFormat(content)
        text = title + content
        return self.get_doc_case_type(text)

_court_tool = CaseTypeTool(case_types)
_doc_tool = DocCaseType(case_types)
    
if __name__ == '__main__':
    
    m = CaseTypeTool(case_types)
    print(m.process_case_reason("常州东风轴承有限公司与常州市同方机械油品有限公司,曹留英等人一般婚约财产纠纷"))
