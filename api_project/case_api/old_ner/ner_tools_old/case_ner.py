# -*- coding: utf-8 -*-

# 司法NER工具

import re, codecs, os, json
import pymysql as pm
import jieba, time

path = os.popen("pwd").read().strip()

try:
    from . import ner
    path += '/ner_tools/'
except:
    import ner
    path += '/'

t1 = time.time()

role_words = [u'原审第三人', u'被上诉人', u'被申请人', u'被申诉人', u'被执行人', u'被告人', u'被告', u'罪犯', u'原审原告', u'原审执行人', u'原审申请人', u'第三人', u'当事人', \
              u'申请执行人', u'原告', u'上诉人', u'执行人', u'申请人', u'申诉人', u'原审被告', u'原审被执行人, u‘二审被上诉人', u'原审被申请人', u'债权人',u'债务人', u'再审申请人' ]
role_words.sort(key=lambda x:-len(x))

ExtractCorp = ner.ExtractCorp
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

print("preparing samples...")
samples = get_samples() + get_more_samples()
print("%d training data's been created..." % len(samples))
print("finish generating samples...")

def split_element(lst, split_s):
    ret = []
    for item in lst:
        ret.extend(item.split(split_s))
    return ret

class CaseNER(ExtractCorp):
    """
        司法NER类
    """
    pop_keys = [u'人']
     
    def __init__(self, text_list, law_file):
        super(CaseNER, self).__init__(text_list)
        
        for item in self.pop_keys:
            self._word_prob.pop(item)
        with codecs.open(law_file, 'r', 'utf-8') as f:
            self.law_words = [line.strip() for line in re.split('-+', f.read())[0].split('\n')]
            self.law_words = [item for item in self.law_words if item]
        self.base_split_pattern = re.compile('|'.join([u',',u';',u'\?',u':',u'\.',u'？',u'，',u'。',u'：',u'；',u'/',u'、',u'与']))
        self._split = lambda x:re.split(self.base_split_pattern, x)
    """    
    def fix(self, a, b, c):
        if a[-1] == u'诉' and len(a) > 1 and a[-2] not in (u'上',u'申',u'转',u'起',u'公'):
            a = u'诉'
        if u'审理' == a[-2 :]:
            a  = u'审理'
        if c[0] == u'诉' and len(c) > 1 and c[1] not in (u'讼',u'求',u'状',u'纸',u'辨'):
            c = u'诉'
        return a, b, c"""
    
    def person_extract(self, part, s, max_len=12, threshold=0.05):
        person_list, pos = [], s.find(part)
        quasi_names = []
        for tmpL in range(2, min(len(part)+1, max_len+1)):
            for i in range(len(part)-tmpL+1):
                _ = ''.join((s[: pos+i], 'Y', s[pos+i+tmpL :]))
                #print('1##', _)
                _ = list(jieba.cut(_))
                #print('######', s[pos+i : pos+i+tmpL], _)
                #print('2##', _)
                ind = _.index('Y') if 'Y' in _ else -1
                if ind == -1:
                    continue
                a, b, c = _[max(0, ind-1)], 'X', _[min(len(_)-1, ind+1)]
                a, b, c = self.fix(a, b, c)
                #print('a, b, c', a, b, c)
                new_s = ''.join((a, b, c) if a != 'Y' else (b, c))
                is_sentence = self.predict_sentence(new_s)
                if is_sentence >= threshold:
                    quasi_names.append((is_sentence, s[pos+i : pos+i+tmpL]))
                    #print(_)
        if not quasi_names:
            return ''
        quasi_names.sort(key=lambda x:-x[0])
        return quasi_names[0][1]
        
    def process(self, s):
        s_ = s #re.sub('[\(（]+.*?[\)）]+', '', s)
        corps = []
        # 先获取企业名称
        while 1:
            corp = self.corp_extract(s_).replace('R','').replace('X','')
            if not corp:
                break
            corps.append(corp)
            s_ = s_.replace(corp, 'X')
        #print(s_) 
        s_ = re.sub('[\(（]+.*?[\)）]+', '',s_)        
        # 获取人名
        pieces = self._split(s_)
        for law_word in self.law_words:
            pieces = split_element(pieces, law_word)
        persons = [re.sub('R|X','',self.person_extract(part, s_)) for part in pieces if len(part) > 1]
        persons = [name for name in persons if name and 'X' not in name]
        
        return corps,  persons
        
m = CaseNER(samples, law_file)
t2 = time.time()

samples = None

print("It takes %s seconds to train..." % str(t2-t1))

def entity_extract(s):
    s = re.sub('等+人*', '', s)
    s = replace_casetype(s)
    #print(s)
    corps, persons = m.process(s)
    return corps, persons
    
if __name__ == '__main__':
    
    #print(replace_casetype("本院定于2017年9月21日上午08:50在第二法庭公开开庭审理被告人李茂菁、苏海波、李来德、麦贤娜涉嫌犯盗窃罪一案。"))
    
    s = [u'在杭州开庭审理中新力合股份有限公司民间借贷纠纷一案', \
         u'本院于3月20日在第二审判庭开庭审理温州市财政局诉田英巧一案', \
         u'上诉人温州银行乐清支行与被上诉人旦增曲培合同纠纷一案', \
         u'原告珠扎多吉、刘科与黄振宝汽车修理厂合同案', \
         u'在墨脱县人民法院巴宜区法院科技法庭开庭审理古鲁尼玛故意伤害罪一案', \
         u'在拉萨市城关区人民法院民一中法庭(科技法庭)开庭审理甲央汪修（别名江央）诉旦增曲培合同纠纷一案', \
         u'在拉萨市城关区人民法院民一小法庭1（科技法庭）开庭审理珠扎多吉诉朱云龙等民间借贷纠纷一案', \
         u'在新疆维吾尔自治区吐鲁番市中级人民法院第五审判法庭开庭审理乃吉米丁·吐尔逊诉地力夏提·玉努斯民间借贷纠纷一案', \
         u'在伊宁县人民法院五号法庭开庭审理马兰诉依布拉黒木等继承纠纷一案', \
         u'在克拉玛依市独山子区人民法院2号法庭开庭审理刘萍诉玛丽亚木汗·阿不拉等民间借贷纠纷一案', \
         u'上诉人关却尖措与被上诉人旦正、桑却、公德健康权、身体权纠纷一案', \
         u'诉田英巧一案',
        ]
    #s = s[:5]
    #s_ = [replace_casetype(ss) for ss in s]
    #s_ = [ss for ss in s if ss_]
    db_info = ('10.50.87.180', 'super_user', 'jkPsuDm2JS3', 'nono_test')
    samples = []
    a, b, c, d = db_info
    conn = pm.connect(host=a, user=b, passwd=c, db=d, charset='utf8')
    cursor = conn.cursor()
    n_line = 100
    i = 20000 + 3
    sql = "select case_reason from t_ods_court where char_length(case_reason) >= 10 and plaintiff = '' and defandant = '' limit {},{}".format(i*n_line, n_line)
    cursor.execute(sql)
    res = cursor.fetchall()
    if not res:
        print("empty set...")
    s = [tup[0] for tup in res if tup]
    for ss in s:
        _ = entity_extract(ss)
        print(ss, '--partners:', _)
