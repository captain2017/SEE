# -*- coding: utf-8 -*-

# 司法NER工具

import re, codecs, os, json
import pymysql as pm
import jieba, time, math, copy
from collections import Counter
import numpy as np

x = jieba.cut('')
del x

path = os.popen("pwd").read().strip()
path += '/tools/'

role_words = [u'原审第三人', u'被上诉人', u'被申请人', u'被申诉人', u'被执行人', u'被告人', u'被告', u'罪犯', u'原审原告', u'原审执行人', u'原审申请人', u'第三人', u'当事人', \
              u'申请执行人', u'原告', u'上诉人', u'执行人', u'申请人', u'申诉人', u'原审被告', u'原审被执行人, u‘二审被上诉人', u'原审被申请人', u'债权人',u'债务人', u'再审申请人' ]
role_words.sort(key=lambda x:-len(x))

#ExtractCorp = ner.ExtractCorp
law_file = path + 'law_words.txt'
more_sample_file, this_sep = path + 'more_samples.txt', 'tyqsb'
case_type_file = path + 'case_types.txt'

with codecs.open(case_type_file, 'r', 'utf-8') as f:
    _ = [line.strip() for line in f.readlines()]
    case_types = {}
    for line in _:
        if line[:2] in case_types:
            case_types[line[:2]].append(line)
        else:
            case_types[line[:2]] = [line]
            #print(case_types[line[:2]])
    _ = None
    for key in case_types:
        case_types[key].sort(key=lambda x:-len(x))

def replace_casetype(text):
    for w_ in role_words:
        text = text.replace(w_, 'R')
    for i in range(len(text)-1):
        if text[i : i+2] in case_types:
            for w_ in case_types[text[i : i+2]]:
                text = text.replace(w_, '案')
    return re.sub('案+', '案', text)

def get_samples(loops=4):
    db_info = ('10.50.87.180', 'super_user', 'jkPsuDm2JS3', 'nono_test')
    samples = []
    a, b, c, d = db_info
    conn = pm.connect(host=a, user=b, passwd=c, db=d, charset='utf8')
    cursor = conn.cursor()
    n_line = 50 * 10000
    for i in range(loops):
        sql = "select case_reason, entity_type from t_ods_court where char_length(case_reason) >= 10 and plaintiff = '' and defandant = '' limit {},{}".format(i*n_line, n_line)
        cursor.execute(sql)
        res = cursor.fetchall()
        if not res:
            break
        for reason_, entity_ in res:
            entity = json.loads(entity_)
            for _ in entity:
                if len(_['name']) > 1:
                    reason_ = replace_casetype(reason_.replace(_['name'], 'X'))
            if 'X' in reason_:
                samples.append(reason_)
    conn.close()
    return samples


def replace_all(s, lst):
    for item in lst:
        s = s.replace(item, 'X')
    return s

def get_more_samples():
    with codecs.open(more_sample_file, 'r', 'utf-8') as f:
        samples = [line.strip().split('\t') for line in f.readlines()]
        samples = [replace_all(replace_casetype(line[0]), line[1].split(this_sep))  for line in samples]
    return samples * 10000

def split_element(lst, split_s):
    ret = []
    for item in lst:
        ret.extend(item.split(split_s))
    return ret

class ProbSentenceDetermine(object):
    
    _discount_func = [lambda x:1./x, ]
    
    def __init__(self, text_list, mode=1, n_gram=2, dis_func=0):
        """
           when mode = 0, text_list is an ordinary sentence list;
           when mode = 1, text_list is like (wordA, wordB, prob).
        """
        dis_func = self._discount_func[0]
        self.n_gram, self.discount = n_gram, [dis_func(i+1) for i in range(n_gram)]
        self.text_list = text_list if mode else [list(jieba.cut(text)) for text in text_list if text]
        self._word_prob = self.read_prob() if mode else self.word_prob()
        self.text_list = None
        
    def read_prob(self):
        _word_prob = {}
        for line in self.text_list:
            _ = line
            if len(_) != 3:
                continue
            base_word, follow_word, proba = _
            if base_word in _word_prob:
                _word_prob[base_word][follow_word] = proba
            else:
                _word_prob[base_word] = {follow_word:proba}
        return _word_prob
        
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
                continue
            for key2 in list(dic_.keys()):
                dic_[key2] /= sum_all
                if dic_[key2] < 0.01:
                    dic_.pop(key2)
            _word_prob[key_] = dic_
        _word_prob = {key:_word_prob[key]  for key in _word_prob}
        return _word_prob
        
    def predict_prob_pair(self, x, y, default=0.001):
        if x not in self._word_prob:
            return 0
        if y not in self._word_prob[x]:
            return default
        return self._word_prob[x][y]
        
    def predict_series(self, series, inc_ratio=10, _threshold=0.01):
        words = series
        prob = 1.
        for a, b in zip(words[:-1], words[1:]):
            prob *= self.predict_prob_pair(a, b)
            prob = min(1., prob*inc_ratio) if prob >= _threshold else 0
        #print(words, prob)
        return prob
        
    def predict_sentence(self, s, inc_ratio=10, _threshold=0.01):
        words = list(jieba.cut(s))
        return self.predict_series(words, inc_ratio=inc_ratio, _threshold=_threshold)


class CaseNER(ProbSentenceDetermine):
    """
        司法NER类
    """
    
    pop_keys = [u'人']
    
    def __init__(self, law_file, mode=1):
        if mode == 0:
            samples = get_samples() + get_more_samples()
            print("samples amount is : ", len(samples))
            super(CaseNER, self).__init__(samples, mode=mode)
            self.write_db()
            
        elif mode == 1:
            samples = self.read_db()
            super(CaseNER, self).__init__(samples, mode=mode)
            
        else:
            raise ValueError("No such mode:{}".format(mode))
            
        for item in self.pop_keys:
            if item in self._word_prob:
                self._word_prob.pop(item)
            
        with codecs.open(law_file, 'r', 'utf-8') as f:
            self.law_words = [line.strip() for line in re.split('-+', f.read())[0].split('\n')]
            self.law_words = [item for item in self.law_words if item]
            self.law_words.sort(key=lambda x:-len(x))
        sep_string, law_string = '|'.join([u',',u';',u'\?',u':',u'\.',u'？',u'，',u'。',u'：',u'；',u'/',u'、',u'与','R','X','C',u'案']), \
                                 '|'.join(self.law_words)
        self.base_split_pattern = re.compile(sep_string)
        self.law_split_pattern = re.compile(law_string+'|'+sep_string)
        self._split = lambda x:re.split(self.base_split_pattern, x)
        self.law_split = lambda x:re.split(self.law_split_pattern, x)
        
        self.corp_ends = [u'农场', u'超市', u'委员会', u'部', u'分行', u'支行', u'中心公司', u'分公司', u'公司', u'厂', u'集团', u'银行', u'合作社', u'学院', \
                          u'电视台', u'信用社', u'酒店', u'医院', u'局', u'所', u'会', u'社', u'学校', u'院', u'小学', u'中学', u'大学',u'大厦',u'饭店', \
                          u'中心', u'铺', u'店', u'台', u'站', u'牧场', u'城', u'大厦', u'大楼',u'小区',u'社区', u'队']
        self.corp_ends2 = set([item[-1] for item in self.corp_ends])
        
    def write_db(self):
        db_info = ('10.50.87.180', 'super_user', 'jkPsuDm2JS3', 'nono_test')
        a, b, c, d = db_info
        conn = pm.connect(host=a, user=b, passwd=c, db=d, charset='utf8')
        cursor = conn.cursor()
        sql = "truncate table word_prob"
        cursor.execute(sql)
        conn.commit()
        
        sql = "insert into word_prob(base_word,follow_word,prob) values('{}','{}',{})"
        
        for base_word, info in self._word_prob.items():
            for follow_word, proba in info.items():
                sql_ = sql.format(base_word, follow_word, proba)
                cursor.execute(sql_)
                conn.commit()
        
        conn.close()
        
    def read_db(self):
        db_info = ('10.50.87.180', 'super_user', 'jkPsuDm2JS3', 'nono_test')
        a, b, c, d = db_info
        conn = pm.connect(host=a, user=b, passwd=c, db=d, charset='utf8')
        cursor = conn.cursor()
        cursor.execute("select base_word, follow_word, prob from word_prob")
        res = cursor.fetchall()
        
        return [(tup[0], tup[1], float(tup[2])) for tup in res]
        
    def find_corp_end(self, s):
        for item in self.corp_ends:
            if item in s:
                return item, s.find(item)
        return ()
        
    def fix_head(self, s):
        if not s:
            return s
        if s[-1] == u'诉' and len(s) > 1 and s[-2] not in (u'上',u'申',u'转',u'起',u'公'):
            return u'诉'
        if s[-2:] == u'审理':
            return u'审理'
        return s
        
    def fix_tail(self, s):
        if not s:
            return ''
        if s[0] == u'诉' and len(s) > 1 and s[1] not in (u'讼',u'求',u'状',u'纸',u'辨'):
            return u'诉'
        return s
    
    def extract_one_corp(self, content, min_corp_len=4, max_corp_len=25, threshold=0.05):
        #print("Enter corp!")
        end = self.find_corp_end(content)
        if not end:
            return ''
        end, end_len, end_pos = end[0], len(end[0]), end[1]
        end_pos += end_len
        i = end_pos - min_corp_len
        if i < 0:
            return self.extract_one_corp(content.replace(end,'C', 1))
        if re.findall('[CRX]+', content[i:end_pos]):
            return ''
        left_ = content[end_pos :]
        if left_:
            tail = list(jieba.cut(left_))[0]
            tail = self.fix_tail(tail)
            if self.predict_series(['X', tail]) < threshold:
                return self.extract_one_corp(content.replace(end,'C', 1))
        else:
            tail = ''
            
        quasi_corps = []
        _ = self.law_split(content[:i])[-1]
        xxx = content[:i].find(_)
        while i >= max(0, xxx) and end_pos - i <= max_corp_len:
            if content[i] in ('X','C','R'):
                break
            head = list(jieba.cut(content[:i]))
            head = self.fix_head(head[-1]) if head else ''
            series = [head, 'X', tail]
            if not (head or tail):
                break
            else:
                if head and tail:
                    p = self.predict_series(series)
                elif head:
                    p = self.predict_series([head, 'X'])
                else:
                    p = self.predict_series(['X', tail])
                
                if p >= threshold:
                    quasi_corps.append((content[i : end_pos], p))
            i -= 1
        
        quasi_corps.sort(key=lambda x:(-x[1],-len(x[0])))
        return self._split(quasi_corps[0][0])[-1] if quasi_corps else ''
        
    def extract_corps(self, content):
        corp_names = []
        while 1:
            name_ = self.extract_one_corp(content)
            if not name_:
                break
            if '和' not in name_:
                corp_names.append(name_)
            else:
                pos = name_.find('和')
                if name_[pos-1] in self.corp_ends2:
                    corp_names.extend(name_.split('和'))
                else:
                    corp_names.append(name_)
            content = content.replace(name_, 'X')
        return corp_names
        
    def standard_content(self, content):
        if u'审理' in content:
            lst = content.split(u'审理')
            if re.findall('[\d年月日法院庭]+', lst[0]) or len(lst[-1]) >= len(lst[0]):
                content = ''.join(lst[1:])
            elif len(lst[-1]) < 6:
                content = ''.join(lst[:-1])
        return content
        
    def extract_persons(self, content, min_len=2, max_len=12, threshold=0.05):
        content = self.standard_content(content)
        person_names = []
        pieces = self.law_split(content)
        #print(pieces)
        for piece in pieces:
            if not piece or len(piece) < min_len:
                continue
            quasi_persons = []
            i = min_len
            max_len_ = min(max_len, len(piece))
            start_pos = content.find(piece)
            head = list(jieba.cut(content[: start_pos]))
            head = self.fix_head(head[-1]) if head else ''
            if head and self.predict_series([head, 'X']) < threshold:
                continue
            while i <= max_len_:
                if content[start_pos+i-1] in ('X','R','C'):
                    break
                end_pos = i + start_pos
                tail = list(jieba.cut(content[end_pos :]))
                tail = self.fix_tail(tail[0]) if tail else ''
                series = [head, 'X', tail]
                #print(content[start_pos:end_pos], series)
                if not (head or tail):
                    break
                else:
                    if head and tail:
                        p = self.predict_series(series)
                    elif head:
                        p = self.predict_series([head, 'X'])
                    else:
                        p = self.predict_series(['X', tail])
                    
                    if p >= threshold:
                        quasi_persons.append((content[start_pos : end_pos], p))
                i += 1
            quasi_persons.sort(key=lambda x:(-x[1], -len(x[0])))
            if quasi_persons:
                name_ = quasi_persons[0][0]
                if '和' not in name_:
                    person_names.append(name_)
                else:
                    pos = name_.find('和')
                    if (pos-len(name_)/2)**2 <= 1:
                        person_names.extend(name_.split('和'))
                    else:
                        person_names.append(name_)
        return person_names
        
    def extract_all(self, content):
        #print('=========================')
        if not content:
            return [], []
        t11 = time.time()
        corp_names = self.extract_corps(content)
        t12 = time.time()
        if corp_names:
            for name_ in corp_names:
                content = content.replace(name_, 'X')
        t13 = time.time()
        #print('++++++++++++++++++++++++++')
        #print("content", content)
        person_names = self.extract_persons(content)
        t14 = time.time()
        #print('-*-*-*-*-', t12-t11,t14-t13)
        corpNames, l = '|'.join(corp_names), []
        for i, name in enumerate(person_names):
            if name in corpNames:
                l.append(i)
        return corp_names, [person_names[i] for i in range(len(person_names)) if i not in l]

#samples = None
t1 = time.time()
m = CaseNER(law_file, mode=1)
t2 = time.time()

print("It takes %s seconds to train..." % str(t2-t1))

def entity_extract(s):
    s = re.sub('等+人*', '', s)
    s = replace_casetype(s)
    #print(s)
    corps, persons = m.extract_all(s)
    return corps, persons
    
if __name__ == '__main__':
    """ss = '原告郑来萍诉被告王茂胜民间借贷纠纷一案'
    print(ss) 
    print(entity_extract(ss))
    quit()"""
    db_info = ('10.50.87.180', 'super_user', 'jkPsuDm2JS3', 'nono_test')
    samples = []
    a, b, c, d = db_info
    conn = pm.connect(host=a, user=b, passwd=c, db=d, charset='utf8')
    cursor = conn.cursor()
    n_line = 1000
    i = 200 + 10
    sql = "select case_reason from t_ods_court where char_length(case_reason) >= 10 and plaintiff = '' and defandant = '' limit {},{}".format(i*n_line, n_line)
    cursor.execute(sql)
    res = cursor.fetchall()
    if not res:
        print("empty set...")
    s = [tup[0] for tup in res if tup]
    t1 = time.time()
    for ss in s:
        _ = entity_extract(ss)
        print(ss, '--partners:', _)
    t2 = time.time()
    print("******total", len(s), t2-t1, 'seconds')
