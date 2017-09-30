# -*- coding: utf-8 -*-

# 获取裁判文书关联方

#import corp_detect as cpdt
from . import chinese_name_extract as cne
import codecs, re, os, time, json
from functools import reduce
import pymysql as pm

'''
_model_ = cpdt.CorpRecognize('train_char.txt', 
                             'corp_samples.txt', 
                             'noncorp_samples.txt')
'''
_model_ = cne.ChineseNameTool('family_names.txt',
                              'chinese_names.txt')
sep_symbol = [u',', u';', u':', u' ', u'/', 
              u'，', u'。', u'：']
split_pattern = re.compile('|'.join(sep_symbol))

def head_strip(s):
    for i, item in enumerate(s):
        if item not in sep_symbol:
            return s[i: ]
    return ''
    
def split_first(s):
    for i, item in enumerate(s):
        if item in sep_symbol:
            return s[: i]
    return s

class ChargeEntity:
    def __init__(self, family_name_file, plaintiff_file, defandant_file):

        self.path = os.popen("pwd").read().strip()+'/tools_t/' #linux中的相对路径
        with codecs.open(self.path + family_name_file, 'r', 'utf-8') as f:
            L = reduce(lambda x,y:x+y, \
                      [line.strip().split('\t') for line in f.readlines()])
            self.family_names = set(list(L))
        #print(self.family_names)
        with codecs.open(self.path + plaintiff_file, 'r', 'utf-8') as f:
            self.plaintiff_words = [line.strip().replace('\ufeff','') for line in f.readlines()]
            self.plaintiff_words = [line for line in self.plaintiff_words if line]
        with codecs.open(self.path + defandant_file, 'r', 'utf-8') as f:
            self.defandant_words = [line.strip().replace('\ufeff','') for line in f.readlines()]
            self.defandant_words = [line for line in self.defandant_words if line]
            
        self.corp_key_words = [u'公司', u'厂', u'集团', u'分行', u'支行', u'银行', u'合作社', u'院', \
                               u'信用社', u'酒店', u'医院', u'局', u'所', u'会', u'办事处', u'政府',u'营业部',\
                               u'电视台',u'中心',u'队',u'LIMITED', u'CO.', u'COORP', u'LTD',u'维修部',u'娱乐城',u'报社']
            
    def str_head_type(self, s):
        if len(s) <= 1:
            return ''
        if len(s) <= 4 and (s[0] in self.family_names or s[:2] in self.family_names):
            """
            if _model_.entity_type(s) == u'个人':
                return 'person'
            """
            if _model_.is_name(s):
                return u'个人'
        if len(s) <= 30:
            for item in self.corp_key_words:
                if s[-len(item):] == item:
                    return u'企业'
        return ''
        
    def get_word(self, charge):
        self.pl_word, self.de_word = [], []
        for item in self.plaintiff_words:
            if charge.find(item) >= 0:
                self.pl_word.append(item)
        for item in self.defandant_words:
            if charge.find(item) >= 0:
                self.de_word.append(item)
                
    def get_target_list(self, charge, key_words):
        charge = re.sub(u'[\(|（]+.{0,2}[原|审|二|一|上|诉|申|请|执|行|被|罪|再|赔|利|反]+.*?[）|\)]', '', charge)  
        charge = re.sub(u'[原|一|二]+审+[原|被|告|执|行|人|申|请|上|罪|犯]{2,10}','',charge) #去掉同一个角色出现多次的问题  注意仍保留以再字开头的角色
        charge = re.sub(u'[（|\(]+.{0,3}[简下]+称+.*?[\)|）]', '',charge) #去掉括号内的以下简称等内容
        target_list = []
        for key_word in key_words:
            text, L = charge, len(key_word)
            #print(key_word)
            while 1:
                loc = text.find(key_word)
                if loc == -1:
                    break
                text = head_strip( text[loc+L :] )
                ___ = split_first(text)
                _ = ___.split('、')
                for tmp_text in _:
                    if len(tmp_text) > 30:
                        break
                    if self.str_head_type(tmp_text):
                        if tmp_text in target_list:
                            break
                        if u'原审' in tmp_text:
                            continue
                        target_list.append(tmp_text)
                    else:
                        break
                text = text[len(_[0]) :]
        return target_list

    def sense_detect(self, s):
        sense_list = [u'诉', u'申请']
        for item in sense_list:
            if item in s:
                return 0
        return 1
    
    def wash_list(self, lst):
        Lst = sorted(lst, key=lambda x:len(x))
        L = []
        for i in range(len(lst)-1):
            for j in range(i+1, len(lst)):
                if Lst[i] in Lst[j]:
                    L.append(j)
        L = set(L)
        return [Lst[ind] for ind in range(len(Lst)) if ind not in L and self.sense_detect(Lst[ind])]
                
    def extract_entity(self, charge):
        text_list = re.split(split_pattern, charge)[:50]
        self.get_word(charge)
        plaintiff_list, defandant_list = [], []
        if self.de_word:
            defandant_list = self.get_target_list(charge, self.de_word)
        if self.pl_word:
            plaintiff_list = self.get_target_list(charge, self.pl_word)
            for i in range(len(plaintiff_list)):
                if plaintiff_list[i] in defandant_list:
                    plaintiff_list = plaintiff_list[:i]
                    break                
        d = {'plaintiff':self.wash_list(plaintiff_list),
             'defandant':self.wash_list(defandant_list)}
        
        return d #json.dumps(d, ensure_ascii=False)

    def pattern_extract1(self, charge):
        charge = re.sub(u'[\(|（]+.{0,2}[原|审|二|一|上|诉|申|请|执|行|被|罪|再|赔|利|反]+.*?[）|\)]', '', charge)  
        charge = re.sub(u'[原|一|二|再]+审+[原|被|告|执|行|人|申|请|上|罪|犯]{2,10}','',charge)
        charge = re.sub(u'[（|\(]+.{0,3}[简下]+称+.*?[\)|）]', '',charge) 

        de_list, pl_list = [], []
        #s = '[:|：|,|，| |。]?[省|市|区|县|街|路|巷|道|州|镇|乡|村]'#省市区县街路巷道州镇乡村
        for item in self.defandant_words:
            for itw in ['男女']: #'省市区县街路巷道州镇乡村',
                pat_str = "%s[:|：|,|，| ]?(.*?)[:|：|,|，| |。]{1,1}.{0,10}[%s]+" % (item, itw)
                pattern = re.compile(pat_str)
                entity = pattern.findall(charge)
                if entity:
                    for _ in entity:
                        de_list.append(_)

        for item in self.plaintiff_words:
            for itw in ['男女']:#'省市区县街路巷道州镇乡村',
                pattern = re.compile("%s[:|：|,|，| ]?(.*?)[:|：|,|，| |。]{1,1}.{0,10}[%s]+" % (item, itw))
                entity = pattern.findall(charge)
                if entity:
                    for _ in entity:
                        if _ not in de_list:
                            pl_list.append(_)

        d = {'plaintiff':self.wash_list(pl_list),
             'defandant':self.wash_list(de_list)}

        return d 




if __name__ == '__main__':
    
    #conn = pm.connect(host='10.10.168.44', user='root', passwd='root', charset='utf8')
    #cursor = conn.cursor()
    #sql = "select id, content from test.t_ods_document limit 1"
    #cursor.execute(sql)
    #res = cursor.fetchall()
    m = ChargeEntity('family_names.txt', 'plaintiff.txt', 'defandant.txt')
    #for ind, charge in res:
        #print(ind, '--', m.extract_entity(charge))

    #conn.close()
    print(m.extract_entity('dhjkdh'))