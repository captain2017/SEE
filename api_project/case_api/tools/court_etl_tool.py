# -*- coding: utf-8 -*-

# using Python3 grammar

# 开庭信息清洗

import pymysql as pm
import re, codecs, os, json
import datetime as dt
import hashlib as hl
from . import corp_detect as cpdt
from . import case_reason_etl as cre
import requests

path = os.popen("pwd").read().strip()+'/tools/'
_model_ = cpdt.CorpRecognize(path+'train_char.txt',
                             path+'corp_samples.txt',
                             path+'noncorp_samples.txt')
_entity_reason = cre.entity_info

special_characters = [u'：', u'案由', u' ', u'，', u'。', \
                      u'、', u'【', u'】', u'？', u',', u':', u'*', u'.', \
                      u'?', u'!', u':', u';', u'@', u"'", u'&', \
                      u'#', u'%', u'^', u'￥', u'！', u'；']
                      
number_dict = {u'一':'1', u'二':'2', u'三':'3', u'四':'4', u'五':'5', \
	             u'六':'6', u'七':'7', u'八':'8', u'九':'9'}

sep_symbol = [u',', u';', u':', u'与', u'/', 
              u'，', u'。', u'：', u'、']

split_pattern = re.compile('|'.join(sep_symbol))

role_words = [u'被上诉人', u'被申请人', u'被申诉人', u'被执行人', u'被告人', u'被告', u'罪犯', u'原审原告', u'原审执行人', u'原审申请人', u'第三人', u'当事人', \
              u'申请执行人', u'原告', u'上诉人', u'执行人', u'申请人', u'申诉人', u'原审被告', u'原审被执行人, u‘二审被上诉人', u'原审被申请人', u'债权人',u'债务人' ]
role_words.sort(key=lambda x:-len(x))

"""
defendant_words = [u'被上诉人', u'被申请人', u'被申诉人', u'被执行人', u'被告人', u'被告', u'罪犯', u'原审原告', u'原审执行人', u'原审申请人']
plaintiff_words = [u'申请执行人', u'原告', u'上诉人', u'执行人', u'申请人', u'申诉人', u'原审被告', u'原审被执行人, u‘二审被上诉人', u'原审被申请人']
"""


def split_element(lst, split_s):
    ret = []
    for item in lst:
        ret.extend(item.split(split_s))
    return ret

def get_md5(s):
    ''' 获取字符串的md5值 '''
    myMD5 = hl.md5()
    myMD5.update(s)
    return myMD5.hexdigest().upper()

def number_transfer(uchar):
    return number_dict[uchar] if uchar in number_dict else 0

def LocalSearch(str_all, min_substr_len):
    '''
        str_all -- a list or tuple of strings.
        min_substr_len -- minimum length of keys.
    '''
    
    d = {}
    for i, line in enumerate(str_all):
        L = len(line)
        
        if L < min_substr_len:
            d[line] = i
            continue
        
        N = min_substr_len
        while N <= L:
            for ind in range(L-N+1):
                s = line[ind : ind+N]
                if s in d:
                    d[s].append(i)
                else:
                    d[s] = [i]
            N += 1
    
    return d
    
def nstr_to_date(us):
    us = us.replace(' ','')
    if not re.sub('\d+', '', us):
        if len(us) == 1:    return '0'+us
        elif len(us) == 2:  return us
        else:   return '00'
    try:    
        if len(us) == 1:
            return '0' + number_dict[us] if us != u'十' else '10'
        elif len(us) == 2:
            return '1' + number_dict[us[-1]] if us.index(u'十') == 0 \
                   else number_dict[us[0]] + '0'
        elif len(us) == 3:
            return number_dict[us[0]] + number_dict[us[-1]]
        else:
            return '00'
    except:
        return '00'
                      
def isChinese(uchar):
    return u'\u4e00' <= uchar <= u'\u9fa5'
    
def isEnglish(uchar):
    return (u'\u0041'<=uchar<=u'\u005a') or (u'\u0061'<=uchar<=u'\u007a')
    
def isNumber(uchar):
    return u'\u0030' <= uchar <= u'\u0039'

class CourtETLTool:
    ''' 开庭信息清洗 '''
    
    must_replace_patterns = ['[\(（]+附民[\)）+]', ]
    
    def __init__(self):
        self.SPChars = set(special_characters)        #待去除的开头结尾特殊字符
        with codecs.open(path+'court_all.txt', 'r', 'utf-8') as f:
            self.court_all = [line.strip().split('\t') for line in f.readlines()]
            self.court_local = LocalSearch([line[0] for line in self.court_all], 6)
        with codecs.open(path+'law_words.txt', 'r', 'utf-8') as f:
            self.law_words2 = [line.strip() for line in f.readlines()]
            self.law_words = self.law_words2[:self.law_words2.index('----')]
            self.law_words2 = set(self.law_words2)
    
    def get_md5_value(self, s):
        '''
            计算字段的md5值，仅保留字段中的中英文和数字，
            s为unicode对象
        '''
        foo = lambda x: isChinese(x) or isEnglish(s) or isNumber(x)
        ss = ''.join( list( filter(foo, s) ) )
        return get_md5( ss.encode('utf-8') )

    def RemoveSPCharsOfTwoSides(self, s):
        res_str, foo = s, lambda x:str(int(not (isNumber(x) or x in self.SPChars) ))

        if not res_str:
            return ''
        ind1, ind2 = ''.join(list(map(foo, res_str))).find('1'), \
                     len(res_str)-''.join(list(map(foo, res_str[::-1]))).find('1')
        if 0 <= ind1 <= ind2:
            return res_str[ind1 : ind2]
        else:
            return res_str
    
    def etl_case_reason(self, str_in):
        ''' 清洗cause_reason '''
        res_str = str_in
        # 去除首尾特殊字符
        res_str = self.RemoveSPCharsOfTwoSides(res_str)
        if not res_str:
            return ''
        # 切割
        res_str = re.split(u'第\d{2,6}.*号', res_str)[-1]
        #res_str = res_str.split(u'审理')[-1] if res_str else ''
        res_str = res_str.split(u'发布')[0] if res_str else ''
        
        return res_str.replace(u'【','').replace(u'】','') if len(res_str) > 1 else ''
        
    def etl_plaintiff(self, str_in):
        ''' 清洗plaintiff '''
        res_str = str_in
        # 去除首尾特殊字符
        res_str = self.RemoveSPCharsOfTwoSides(res_str)
        if not res_str:
            return ''
        # 切割
        eng_entity = re.findall('[A-Za-z| |\.|,]+', res_str)
        #print(eng_entity)
        if u'法庭' in res_str or u'审理' in res_str:
            _ = _entity_reason(res_str)
            return ','.join([item['name'] for item in _])
        res_str = re.split(u'第\d{2,6}.*号', res_str)[-1]

        if len(re.sub('[0-9]+','',res_str)) <= 1:
            return ''

        _ = re.split(split_pattern, res_str)
        if len(_) > 1:
            _ = [re.sub(u' |\t|\n|\r','',item) for item in _ if item]
        else:
            _ = re.split(' |\t|\n|\r',_[0])
        _ = [re.sub(u'[(|（]*[a-zA-Z]+[)|）]*','',item) for item in _ if item]
        for item in self.law_words:
            _ = split_element(_, item)
        _ = [self.RemoveSPCharsOfTwoSides(item).strip() for item in _ if item]
        _ = [re.sub('[(|（]*[a-zA-Z]+[)|）]*','',item).lstrip(u'）)').rstrip(u'（(') for item in _ if item]
        res_str = ','.join([item for item in _ if item and item not in self.law_words2 and len(item) > 1] + eng_entity)
        
        return res_str.replace('"','').replace("'",'').replace('\\',',')
        
    def etl_defandant(self, str_in):
        ''' 清洗defandant '''
        res_str = str_in
        # 去除首尾特殊字符
        res_str = self.RemoveSPCharsOfTwoSides(res_str)
        if not res_str:
            return ''
        # 切割
        eng_entity = re.findall('[A-Za-z| |\.|,]+', res_str)
        if u'法庭' in res_str or u'审理' in res_str:
            _ = _entity_reason(res_str)
            return ','.join([item['name'] for item in _])
        if len(re.sub('[0-9]+','',res_str)) <= 1:
            return ''

        _ = re.split(split_pattern, res_str)
        if len(_) > 1:
            _ = [re.sub(u' |\t|\n|\r','',item) for item in _ if item]
        else:
            _ = re.split(' |\t|\n|\r',_[0])
        _ = [re.sub(u'[(|（]*[a-zA-Z]+[)|）]*','',item) for item in _ if item]
        for item in self.law_words:
            _ = split_element(_, item)
        _ = [self.RemoveSPCharsOfTwoSides(item).strip() for item in _ if item]
        _ = [re.sub('[(|（]*[a-zA-Z]+[)|）]*','',item) for item in _ if item]
        res_str = ','.join([item for item in _ if item and item not in self.law_words2 and len(item) > 1])
        
        return res_str.replace('"','').replace("'",'').replace('\\',',')
        
    def etl_court(self, str_in):
        ''' 清洗court '''
        res_str = str_in
        # 去除首尾特殊字符
        res_str = self.RemoveSPCharsOfTwoSides(res_str)
        if not res_str:
            return ''	
        if re.findall('\d+', res_str):
            return ''
        return res_str
        
    def etl_court_detail(self, str_in):
        ''' 清洗court_detail '''
        res_str = str_in

        if res_str:
            if not re.sub('\d{1,4}[^0-9]+', '', res_str):
                return res_str
            #res_str = self.RemoveSPCharsOfTwoSides(res_str)
            if ':' in res_str or u'时' in res_str:
                return ''
            if len(list(filter(lambda x: isNumber(x) or isEnglish(x), list(res_str)))) == len(res_str):
                return ''
        
        return res_str
        
    def etl_open_date(self, str_in, case_reason):
        ''' 清洗open_date '''
        if str_in:
            return str(str_in)
        
        target_pattern = re.compile(u'[一|二].{1,3}年.{1,2}月.{1,3}日')
        if not case_reason:
            return '0000-00-00'
        date_info = target_pattern.findall(case_reason)
        
        if date_info:
            date_info = date_info[0]
            year = date_info.split(u'年')[0]
            month = date_info.split(u'月')[0].split(u'年')[-1]
            day = date_info.split(u'日')[0].split(u'月')[-1]
            
            _ = [number_transfer(item) for i, item in enumerate(year)]
            if len(_) == 3:
                _.insert(1, 0)
            year = ''.join(map(str, _))
            month = nstr_to_date(month)
            day = nstr_to_date(day)
            d = '-'.join((year, month, day))
            return d
        else:
            return '0000-00-00'
        
    def etl_cause_no(self, str_in):
        ''' 清洗case_no '''
        if not str_in:
            return ''
        res_str = str_in
        if not list(filter(isChinese, list(res_str))):
            return ''
        res_str = res_str.replace('(',u'（').replace(')', u'）')
        year_pat = re.compile(u'（\d{4,4}）')
        year = year_pat.findall(res_str)
        if year:
            return res_str
        _ = list(res_str)
        
        if not re.findall(u'\d+.?年', res_str):
            try:
                if _[0] != u'（' and _[4] == u'）':
                    _.insert(0, u'（')
                elif _[0] == u'（' and _[5] != u'）':
                    _.insert(5, u'）')
            except:
                pass
            return ''.join(_)
        else:
            return res_str
        
    def etl_accept_department(self, str_in):
        ''' 清洗accept_department '''
        return str_in
        
    def etl_judge(self, str_in):
        ''' 清洗judge '''
        res_str, foo = str_in, lambda x:str(int(isChinese(x)))

        if not res_str:
            return ''
        ind1, ind2 = ''.join(list(map(foo, res_str))).find('1'), \
                     len(res_str)-''.join(list(map(foo, res_str[::-1]))).find('1')
        if 0 <= ind1 <= ind2:
            return res_str[ind1 : ind2]
        else:
            return ''
            
    def etl_province(self, str_in, court):
        ''' 清洗province '''
        if not court or court[:2] == str_in[:2]:
            return str_in

        if court in self.court_local:
            lst = self.court_local[court]
            return self.court_all[lst[0]][1] if len(lst) == 1 else str_in
        return str_in

    def get_entity(self, plaintiff, defandant):
        pl_list, de_list = re.split(split_pattern,plaintiff), re.split(split_pattern,defandant)
        d1 = [{'name':item, 'type':_model_.entity_type(item), 'role':u'原告'} for item in pl_list if item]
        d2 = [{'name':item, 'type':_model_.entity_type(item), 'role':u'被告'} for item in de_list if item]
        return d1+d2 #json.dumps(d1+d2, ensure_ascii=False)
        
    def parser_litigant(self, litigant):
        for pat in self.must_replace_patterns:
            litigant = re.sub(pat, '', litigant)
        _t, role_info = litigant, []
        for w_ in role_words:
            if w_ in _t:
                role_info.append((w_, _t.find(w_)))
                _t = _t.replace(w_, 'X'*len(w_))
        role_info.sort(key=lambda x:-x[1])
        
        if not role_info:
            linkers = self.etl_plaintiff(litigant).split(',')
            return [{'name':item, 'type':_model_.entity_type(item), 'role':u'其他当事人'} for item in linkers if len(item) > 1]
        
        _t, linkers = litigant, []
        for w_, pos_ in role_info:
            _ = _t[pos_+len(w_) :]
            _ = self.etl_plaintiff(_).split(',')
            linkers.extend([{'name':item, 'type':_model_.entity_type(item), 'role':w_} for item in _ if len(item) > 1])
            _t = _t[: pos_]
        if _t:
            _ = self.etl_plaintiff(_t).split(',')
            linkers.extend([{'name':item, 'type':_model_.entity_type(item), 'role':u'其他当事人'} for item in _ if len(item) > 1])
        return linkers
    """
    此部分暂时不用
    def parser_litigant(self, litigant):
        defendant_info, plaintiff_info = None, None
        _t = litigant
        for w_ in defendant_words:
            if w_ in litigant:
                defendant_info = (w_, litigant.find(w_), u'被告')
                _t = litigant.replace(w_, 'X'*len(w_))
                break
        for w_ in plaintiff_words:
            if w_ in litigant and :
                plaintiff_info = (w_, _t.find(w_), u'原告')
                break
        if defendant_info or plaintiff_info:
            defendant_info = defendant_info if defendant_info else ('', -1, '')
            plaintiff_info = plaintiff_info if plaintiff_info else ('', -1, '')
            
            a_, b_ = sorted([defendant_info, plaintiff_info], key=lambda x:x[1])
            _, d = litigant.split(b_[0]), []
            if _[1]:
                __ = self.etl_plaintiff(_[1]).split(',')
                d.extend([{'name':item, 'type':_model_.entity_type(item), 'role':b_[0]} for item in __ if len(item) > 1])
            
            if a_[0]:
                __ = self.etl_plaintiff(_[0].split(a_[0])[-1]).split(',')
                d.extend([{'name':item, 'type':_model_.entity_type(item), 'role':a_[0]} for item in __ if len(item) > 1])
            else:
                __ = self.etl_plaintiff(_[0]).split(',')
                d.extend([{'name':item, 'type':_model_.entity_type(item), 'role':u'其他当事人'} for item in __ if len(item) > 1])
            
            return d
            
        linkers = self.etl_plaintiff(litigant).split(',')
        return [{'name':item, 'type':_model_.entity_type(item), 'role':u'其他当事人'} for item in linkers if len(item) > 1]
    """
    
if __name__ == '__main__':
    
    m = CourtETLTool()
    print(m.parser_litigant(u'上诉人：田英巧，被执行人，王敏、马涛，，第三人:王雨薇'))
