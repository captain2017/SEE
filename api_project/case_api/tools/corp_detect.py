# -*- coding: utf-8 -*-

import numpy as np
import random as rd
from collections import Counter
from sklearn.linear_model import logistic as lgst
import time, codecs, re
from functools import reduce

post_fix = ['Corporation', 'Corp.', 'Incorporated', 'Inc.', 'Company', 'Co.', \
            'Limited', 'Ltd.', 'ltd', 'PLC', 'LLP', 'LLC', 'Pte', 'PVT', 'PTY', 'EST', 'FZC', 'FZCO', \
            'FZE', 'JSC', 'OJSC', 'SDN', 'BHD', 'PT', 'TBK', 'GmbH', 'AG', 'A.G', 'S.A.R.L', 'S.A', \
            'B.V', 'N.V', 'A/S', 'S.P.A', 'S.R.L', 'AB', 'OY', 'S.R.O', 'S.A', 'de C.V', 'OOO', 'OAO', 'ZAO', 'AO', \
            'K.K', 'Y.K', 'APS', 'Lda', 'Ltda', 'SP.Z.O.O', 'TIC', 'EIRL', 'D.O.O', 'A.D', 'SRL', 'SA']
            
def isEngCorp(name, ratio=.4):
    name_ = name[-int(len(name)*ratio) :]
    for pf in post_fix:
        if pf in name_:
            return u'企业'
    return u'个人'

def get_dict(fp, max_L=300):
    # 返回max_L大小的常用字符字典，后面的样本全采用这个集合作为标准
    with codecs.open(fp, 'r', 'utf-8') as f:
        s = [line.strip()#.decode('utf-8') \
             for line in f.readlines()]
        
    s = [list(set(item)) for item in s]
    ss = reduce(lambda x,y:x+y, s)
    char_count = [(key, val) for key, val in Counter(ss).items()]
    char_count.sort(key=lambda x:x[1], reverse=True)
    L = max_L
    
    char_map = {char:i for i, char in enumerate([tup[0] for tup in char_count[:L]])}
    return char_map


def short_text_dict(text, char_map, L):
    vector = np.array([0.] * L)
    for item in text:
        if item in char_map:
            vector[char_map[item]] = 1.
    return vector

def short_text_process(fp, char_map):
    with codecs.open(fp, 'r', 'utf-8') as f:
        s = [line.strip()#.decode('utf-8') \
             for line in f.readlines()]        
    L = len(char_map)
    matrix = [np.array([0.] * L) for i in range(len(s))]
    
    for i, ss in enumerate(s):
        matrix[i] = short_text_dict(ss, char_map, L)
    return matrix

def random_sample(X, ratio=(1, 2)):
    rd.seed(int(time.time()))
    a, b = ratio
    s = [rd.randint(1, b) for i in range(len(X))]
    
    trains, tests = [], []
    for item, i in zip(X, s):
        if 1 <= i <= a:
            trains.append(item)
        else:
            tests.append(item)
    return trains, tests
    
def label_process(fp, lab_type=int):
    '''
        fp -- input label file.
        lab_type -- label's type, default int.
    '''
    with codecs.open(fp, 'r', 'utf-8') as f:
        s = [lab_type(line.strip()) for line in f.readlines()]
        
    return s

def check_length(a, b):
    if len(a) == len(b):
        pass
    else:
        print("Length Error!")
        quit()


def CorpFitModel(train_set, train_label):
    ''' 
        train_set, test_set -- shape [n_sample, n_feature]
    '''
    
    check_length(train_set, train_label)
    fit_model = lgst.LogisticRegression()
    fit_model.fit(train_set, train_label)   
    return fit_model
    
def CorpDetect(fit_model, test_set):
    result = fit_model.predict_proba(test_set)
    return result

def GetCorp(fit_model, test_set):
    result = fit_model.predict_proba(test_set)
    res = [0. if p0 >= p1 else 1. for p0, p1 in result]
    return [test_set[i] for i, lab in enumerate(res) if lab == 1.]

def isCorp(fit_model, char_map, text):
    p0, p1 = CorpDetect(fit_model, [short_text_dict(text, char_map, len(char_map))])[0]
    return u'企业' if p1 >= p0 else u'个人'
    
class CorpRecognize:
    '''
        >>>m = CorpRecognize('train_char.txt', 'corp_samples.txt', 'noncorp_samples.txt')
        >>>m.entity_type(u'阿里巴巴有限公司')
        ...u'企业'
        >>>
    '''
    def __init__(self, char_file, corp_sample_file, noncorp_sample_file, max_L=200):
        self.char_map = get_dict(char_file, max_L=200)
        train_set_corp = short_text_process(corp_sample_file, self.char_map)
        train_set_noncorp = short_text_process(noncorp_sample_file, self.char_map)
        train_label_corp = [1.] * len(train_set_corp)
        train_label_noncorp = [0.] * len(train_set_noncorp)
        
        train_set = train_set_corp + train_set_noncorp
        train_label = train_label_corp + train_label_noncorp
        
        self.fit_model = CorpFitModel(train_set, train_label)
        self.corp_key_words = [u'连锁店', u'委员会', u'分行', u'支行', u'公司', u'厂', u'集团', u'银行', u'合作社', u'院', \
                                u'信用社', u'酒店', u'医院', u'局', u'所', u'会', u'社', u'办事处', u'政府',u'营业部', \
                                    u'电视台',u'中心',u'队',u'LIMITED', u'CO.', u'COORP', u'LTD',u'城',u'大厦', \
                                    u'农场', u'超市',u'学校', u'学院', u'小学', u'中学',u'连锁店',u'店']
        
    def entity_type(self, text):
        if not re.sub("[0-9a-zA-Z\.\*\',，/ ]+", '', text):
            return isEngCorp(text)
        text = text.upper()
        if len(text) <= 1 or (len(text) <= 3 and (u'诉' in text or u'告' in text)):
            return u'未知'
                
        if len(text.strip()) in (2, 3):
            return u'个人'

        for item in self.corp_key_words:
            if item in text:
                return u'企业'
            
        return isCorp(self.fit_model, self.char_map, text)

if __name__ == '__main__':
    '''
    char_map = get_dict('train_char.txt', max_L=200)
    
    all_corp = short_text_process('corp_samples.txt', char_map)
    train_set_corp, test_set_corp = random_sample(all_corp, ratio=(1,2))
    all_corp = None
    train_label_corp, test_label_corp = [1.] * len(train_set_corp), \
                                        [1.] * len(test_set_corp)
    
    all_noncorp = short_text_process('noncorp_samples.txt', char_map)
    train_set_noncorp, test_set_noncorp = random_sample(all_noncorp, ratio=(1,2))
    all_noncorp = None
    train_label_noncorp, test_label_noncorp = [0.] * len(train_set_noncorp), \
                                              [0.] * len(test_set_noncorp)
    
    if len(train_set_corp) == len(train_label_corp) and len(train_set_noncorp) == len(train_label_noncorp):
        train_set = train_set_corp + train_set_noncorp
        train_label = train_label_corp + train_label_noncorp
        test_set = test_set_corp + test_set_noncorp
        test_label = test_label_corp + test_label_noncorp
    else:
        print("Set-Label Length Error!")
        
    fit_model = CorpFitModel(train_set, train_label)
    result = CorpDetect(fit_model, test_set)
    res = [0. if p0 >= p1 else 1. for p0, p1 in result]

    effect = [(i-j)**2 for i, j in zip(test_label, res)]
    print("The pricision is :", 1 - sum(effect) / len(effect))
    '''
    m = CorpRecognize('train_char.txt', 'corp_samples.txt', 'noncorp_samples.txt')
    print(m.entity_type(u' '))
