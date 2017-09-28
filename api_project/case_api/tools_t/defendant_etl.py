# -*- coding: utf-8 -*-

# 案由中的关联方清洗

'''
特点:
1.标识有司法词库信息 
2.特殊标点符号间隔
'''

import re, codecs, json,os
import pymysql as pm
from . import chinese_name_extract as cne
from . import corp_detect as cpdt
from functools import reduce
import requests, os

#path = os.popen("pwd").read().strip()+'/tools/'

_model_person = cne.ChineseNameTool('family_names.txt', 'chinese_names.txt')
_model_corp = cpdt.CorpRecognize('train_char.txt', 'corp_samples.txt', 'noncorp_samples.txt')
end_chars = _model_corp.corp_key_words

path = os.popen("pwd").read().strip()+'/tools_t/' #linux中的相对路径

with codecs.open(path + 'plaintiff.txt', 'r', 'utf-8') as f:
    plaintiff_word = [line.strip() for line in f.readlines()]
with codecs.open(path + 'defandant.txt', 'r', 'utf-8') as f:
    defandant_word = [line.strip() for line in f.readlines()]

def split_element(lst, split_s):
    ret = []
    for item in lst:
        ret.extend(item.split(split_s))
    return ret

g = lambda x: json.dumps(x, ensure_ascii=False).encode('utf-8')

class CaseReasonETL:
    
    def __init__(self, law_words_file, sep_file):
        with codecs.open(path + law_words_file, 'r', 'utf-8') as f:
            self.law_words2 = [line.strip() for line in f.readlines()]
            self.law_words = self.law_words2[:self.law_words2.index('----')]
            self.law_words2 = set(self.law_words2)
        with codecs.open(path + sep_file, 'r', 'utf-8') as f:
            self.sep_pattern = re.compile(u'|'.join([line.strip() for line in f.readlines()]))
    
    
    def get_person_name(self, s, max_L=4):
        if len(s) <= 1:
            return ''
        name = ''
        for i in range(2, min(len(s)+1, max_L+1)):
            ss = s[:i]
            if not _model_person.is_name(ss):
                return name
            name = ss
        return name
    '''
    def get_person_name(self, s):
        if len(s) <= 1:
            return ''
        if _model_person.is_name(s):
            return s
        else:
            return ''
    '''
    
    def get_corp_name(self, s):
        if len(s) < 4:
            return ''
        if _model_corp.entity_type(s) == u'企业':
            for item in end_chars:
                if item in s:
                    ss = [head+item for head in s.split(item)[:-1]]
                    return ''.join(ss)
            return s
        else:
            return ''
            
    def extract_each(self, s):
        s = s.split(u'审理')[1] if u'审理' in s else s
        pieces = re.split(self.sep_pattern, s)
        for law_word in self.law_words:
            pieces = split_element(pieces, law_word)
        pieces = [item if u'第三人' != item[:3] else item[3:] for item in pieces if item]
        pieces = [item for item in pieces if item]
        #print(1, pieces)
        corp_names = [self.get_corp_name(item) for item in pieces]
        person_names = [self.get_person_name(item) for item in pieces]
        #print(2, person_names)
        corp_names = [_[1:] if _[0] in (u')', u'）') else _ for _ in corp_names if _]
        person_names = [_[1:] if _[0] in (u')', u'）') else _ for _ in person_names if _]
        #person_names = reduce(lambda x,y:x+y, [_model_person.extractChineseName(item) for item in pieces])
        corp_names, person_names = [item for item in corp_names if item], \
                                   [item for item in person_names if item]
        for p_name in person_names[:]:
            for c_name in corp_names:
                if p_name in c_name:
                    person_names.remove(p_name)
                    break
        d = {}
        person_names = [item for item in person_names if item not in self.law_words2]
        corp_names = [item for item in corp_names if item not in self.law_words2]
        for item in person_names:
            d[item] = u'个人'
        for item in corp_names:
            d[item] = u'企业'
        return d
"""
def get_pl_de(case_reason, entity_type):
    p = entity_type
    pl_list, de_list = [], []
    if u'与' in case_reason:
        _ = re.split(u'与', case_reason)
    elif u'和' in case_reason:
        _ = re.split(u'和', case_reason)
    else:
        _ = [p]
    flag = 0
    if len(_) > 1:
        for s in _:
            for kw in defandant_word:
                if kw in s:
                    for __ in p:
                        if __ in s:
                            de_list.append(__)
                    flag = 1
                    break
            if flag:
                break
        '''
        if de_list:
            pl_list = list(set(p)-set(de_list))
            return ','.join(pl_list), ','.join(de_list)'''
        flag = 0
        for s in _:
            for kw in plaintiff_word:
                if kw in s:
                    for __ in p:
                        if __ in s:
                            pl_list.append(__)
                    flag = 1
                    break
            if flag:
                break
        '''
        if pl_list:
            de_list = list(set(p)-set(pl_list))
            return ','.join(pl_list), ','.join(de_list)'''
        pl_list = list(set(pl_list)-set(de_list))
        return pl_list, de_list

    pat = re.compile(u'[^上|申|反]+诉')        
    if pat.findall(case_reason):
        aa = re.split(u'诉', case_reason)
        pl, de = aa[0], aa[1]
        for item in p:
            if item in pl:
                pl_list.append(item)
            elif item in de:
                de_list.append(item)
    if pl_list or de_list:
        return pl_list, de_list
        
    return [], []
    
def entity_info(reason):
    entities = m.extract_each(reason)
    pl, de = get_pl_de(reason, entities)
    entity_array = []
    for key in entities:
        if u'法院' in key:
            continue
        d = {'name':key, 'type':entities[key]}
        if key in pl:
            d['role'] = u'原告'
        elif key in de:
            d['role'] = u'被告'
        else:
            d['role'] = ''
        entity_array.append(d)
    entity_array = json.dumps(entity_array, ensure_ascii=False)
    return entity_array
"""

m = CaseReasonETL('law_words.txt', 'sep_words.txt')

role_words = defandant_word+plaintiff_word+[u'第三人']

def certain_locations(w, text):
    locations = []
    while w in text:
        locations.append((w, text.find(w)))
        text = text.replace(w, 'X'*len(w))
    return locations
    
def get_role(reason, entity_type):
    _reason, locations, L = reason, [], len(reason)
    for w_ in role_words:
        while w_ in _reason:
            locations.append((w_, _reason.find(w_)))
            _reason = _reason.replace(w_, 'X' * len(w_), 1)
            
    pos_su, _key, key_ = certain_locations(u'诉', _reason), (u'上',u'申',u'撤', u'非'), (u'求',u'讼',u'状')
    pos_su = [(w, p) for w, p in pos_su if _reason[max(0, p-1)] not in _key and _reason[min(L-1, p+1)] not in key_]
    
    if not locations:
        if not pos_su:
            return [{'name':key, 'type':val, 'role':u'其他当事人'} for key, val in entity_type.items()]
        p = pos_su[0][1]
        return [{'name':key, 'type':val, 'role':u'原告' if _reason.find(key) < p else u'被告'} for key, val in entity_type.items()]
    
    _reason = reason
    name_role = {}
    locations.sort(key=lambda x:-x[1])
    for w_, pos_ in locations:
        _s, _reason = _reason[pos_+len(w_) :], _reason[: pos_]
        for key in entity_type:
            if key in _s:
                name_role[key] = w_
    
    entity_array = [{'name':key, 'type':val, 'role':name_role[key] if key in name_role else u'其他当事人'} for key, val in entity_type.items()]
    if pos_su:
        p = pos_su[0][1]
        for i, d in enumerate(entity_array):
            if d['role'] == u'其他当事人':
                d['role'] = u'原告' if reason.find(d['name']) < p else u'被告'
                entity_array[i] = d
    return entity_array

def entity_info(reason):
    reason = re.sub(u'[\(|（]+.{1,3}[原|审|二|一|上|诉|申|请|执|行|被|罪|再|赔|利]+审.*?[\)|）]+','', reason)
    _ = re.split(u'[（|\(]+\d{3,5}[\)|）]+.{1,3}\d+[刑民商]+[初再二终]+\d{2,6}号', reason)
    if len(_) == 1:
        reason = _[0]
    else:
        reason = _[0] if len(re.findall(u'[被执行申请原被告上诉]+', _[0])) >= 2  else _[1]
    entities = m.extract_each(reason)
    entity = {key:val for key, val in entities.items() if u'法院' not in key}
    s = get_role(reason, entity)
    return s
    
if __name__ == '__main__':
    
    a = u'北京市通州区住房和城乡建设委员会'
    #url = 'http://10.50.87.150:8000/reason_entity/?reason={}'.format(a.encode('utf-8'))
    print(entity_info('北京市通州区健身银行支行'))
    #print(m.extract_each(a))
    '''
    db = ('10.50.87.180', 'super_user', 'jkPsuDm2JS3', 'nono_test')
    a, b, c, d = db
    conn = pm.connect(host=a, user=b, passwd=c, db=d, charset='utf8')
    cursor = conn.cursor()
    step = 500000
    for i in range(8):
        sql = "select id, case_reason from t_ods_court where plaintiff = '' and defandant = '' and length(case_reason) >= 30 limit {},{}".format(i*step, step)
        cursor.execute(sql)
        res = cursor.fetchall()
        if not res:
            break
        
        for ind, reason in res:
            if not reason or len(reason) < 10:
                continue
            entity_array = entity_info(reason)
            #entity_array = requests.get('http://10.50.87.150:8000/reason_entity/?reason={}'.format(reason)).text
            sql_update = "update t_ods_court set entity_type = '{}' where id = {}".format(entity_array, ind)
            cursor.execute(sql_update)
            conn.commit()
        print(i+1)
        
    conn.close()'''
