# -*- coding: utf-8 -*-
# 实体抽取

import numpy as np
from collections import Counter
import re, math, copy
import jieba
import pymysql as pm


sep_symbols = [u'，',u'：',u'。',u'；',u'？',u'！',u'、']

class ProbSentenceDetermine(object):
    
    _discount_func = [lambda x:1./x, ]
    
    def __init__(self, text_list, n_gram=2, dis_func=0):
        dis_func = self._discount_func[0]
        self.n_gram, self.discount = n_gram, [dis_func(i+1) for i in range(n_gram)]
        self.text_list = [list(jieba.cut(text)) for text in text_list if text]
        self._word_prob = self.word_prob()
        self.text_list = None
        
    def word_prob(self):
        _word_prob = {}
        for i, line in enumerate(self.text_list):
            for j in range(len(line)):
                word, word_after = line[j], line[j+1 : j+self.n_gram+1]
                if word not in _word_prob:
                    _word_prob[word] = {}
                for w_, disc_ in zip(word_after, self.discount[:len(word_after)]):
                    if w_ in _word_prob[word]:
                        _word_prob[word][w_] += disc_
                    else:
                        _word_prob[word][w_] = float(disc_)
        for key_ in list(_word_prob.keys()):
            dic_ = _word_prob[key_]
            sum_all = sum(list(dic_.values()))
            if sum_all < len(self.text_list) / 500:
                _word_prob.pop(key_)
            for key2 in dic_:
                dic_[key2] /= sum_all
        return _word_prob
        
    def predict_prob_pair(self, x, y, default=0.001):
        if x not in self._word_prob:
            return 0
        if y not in self._word_prob[x]:
            return default
        return self._word_prob[x][y]
        
    def predict_sentence(self, s, inc_ratio=10, _threshold=0.01):
        words = list(jieba.cut(s))
        prob = 1.
        for a, b in zip(words[:-1], words[1:]):
            prob *= self.predict_prob_pair(a, b)
            prob = min(1., prob*inc_ratio) if prob >= _threshold else 0
        return prob
        
class ExtractCorp(ProbSentenceDetermine):
    
    def __init__(self, text_list):
        self.corp_ends = [u'农场', u'超市', u'委员会', u'部', u'分行', u'支行', u'中心公司', u'分公司', u'公司', u'厂', u'集团', u'银行', u'合作社', u'学院', \
                          u'电视台', u'信用社', u'酒店', u'医院', u'局', u'所', u'会', u'社', u'学校', u'院', u'小学', u'中学', u'大学',u'大厦',u'饭店', \
                          u'中心', u'铺', u'店', u'台', u'站', u'牧场', u'城', u'大厦', u'大楼',u'小区',u'社区', u'队']
        super(ExtractCorp, self).__init__(text_list)
    """    
    def _local_join(self, lst, start, end, max_corp_len=25):
        #return lst[: start] + [''.join(lst[start : end])] + lst[end :]
        pre_str = ''.join(lst[start : end])
        if len(pre_str) > max_corp_len:
            return None
        return lst[: start] + ['X'] + lst[end :]
        
    def corp_extract(self, s, threshold=0.05):
        _word_list = list(jieba.cut(s))
        #print(_word_list)
        for i, w_ in enumerate(_word_list):
            ind = -1
            for item in self.corp_ends:
                if item in w_ and w_[-len(item) :] == item:
                    ind = i-1
                    break
            if ind > 0:
                quasi_corps = []
                while ind > 0:
                    quasi_list = self._local_join(_word_list, ind, i+1)
                    print(quasi_list)
                    if not quasi_list:
                        break
                    quasi_str = ''.join(quasi_list[ind-1 : ind+2])
                    is_sentence = self.predict_sentence(quasi_str)
                    if is_sentence >= threshold:
                        quasi_corps.append((is_sentence, ''.join(_word_list[ind : i+1])))
                    ind -= 1
                if quasi_corps:
                    quasi_corps.sort(key=lambda x:-x[0])
                    return quasi_corps[0][1]
        return None"""
    
    def fix(self, a, b, c):
        if a and a[-1] == u'诉' and len(a) > 1 and a[-2] not in (u'上',u'申',u'转',u'起',u'公'):
            a = u'诉'
        if u'审理' == a[-2 :]:
            a  = u'审理'
        if c and c[0] == u'诉' and len(c) > 1 and c[1] not in (u'讼',u'求',u'状',u'纸',u'辨'):
            c = u'诉'
        return a, b, c
        
    def corp_extract(self, s, threshold=0.05, max_corp_len=25):
        s = s.replace('X', 'Z')
        s = re.sub('\d+','',s)
        ind = 0
        for item in self.corp_ends:
            if item in  s:
                ind_, endL = s.find(item), len(item)
                if ind_ > 0:
                    ind = ind_
                    break
        if ind <= 0:
            return ''
        pos = ind
        quasi_corps = []
        while pos >= 0:
            quasi_str = s[: pos].replace('Z','') + 'X' + s[ind+endL :].replace('Z','')
            #print("0###", quasi_str)
            if ind + endL - pos > max_corp_len:
                break
            _ = list(jieba.cut(quasi_str))
            Xind = _.index('X')
            a, b, c = _[max(0, Xind-1)], 'X', _[Xind+1] if _[-1] != 'X' else ''
            a, b, c = self.fix(a, b, c)
            a = a if a != 'X' else ''
            quasi_str = ''.join((a, b, c))
            #print("1###", quasi_str)
            is_sentence = self.predict_sentence(quasi_str)
            if is_sentence >= threshold:
                quasi_corps.append((is_sentence, s[pos : ind+endL]))
            pos -= 1
        if quasi_corps:
            quasi_corps.sort(key=lambda x:-x[0])
            return quasi_corps[0][1]
        return ''
        
        
if __name__ == '__main__':
    
    text_list = [u'在拉萨市城关区人民法院民一中法庭开庭审理X诉X合同纠纷一案', \
                 u'在墨脱县人民法院巴宜区法院科技法庭开庭审理X故意伤害罪一案', \
                 u'在拉萨市城关区人民法院民一小法庭1开庭审理X诉X等民间借贷纠纷一案', \
                 u'上诉人X、X与上诉人X等人种植回收合同纠纷一案', \
                 u'原告X诉X合同案']
                 
    m = ExtractCorp(text_list)
    
    s = [u'在杭州开庭审理中新力合股份有限公司民间借贷纠纷一案', \
         u'本院于3月20日在第二审判庭开庭审理温州市财政局诉温州市第一中学一案', \
         u'上诉人温州银行乐清支行与被上诉人马涛合同纠纷一案', \
         u'原告刘科与黄振宝汽车修理厂合同案']
    
    # 开始抽取企业名称     
    for ss in s:
        _ = m.corp_extract(ss)
        print(_ if _ else None)
        
    print(m.predict_sentence('X与X合同纠纷一案'))
