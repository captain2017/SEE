# -*- coding: utf-8 -*-

# 失信关联人与对应代码提取

import re, json, os, copy
import string
from functools import reduce
from . import corp_detect as cpdt

path = os.popen("pwd").read().strip()+'/tools/'
_model_corp = cpdt.CorpRecognize(path+'train_char.txt', path+'corp_samples.txt', path+'noncorp_samples.txt')

patt1 = re.compile(u'[（|\(]+.*?[）|\)]*')
patt2 = re.compile('[0-9a-zA-Z]+')

code_pattern = re.compile(u'[a-zA-Z0-9\*﹡-]{9,20}')
sep_symbol = [u',', u';', u'/', 
              u'，', u'。', u'；']

split_pattern = re.compile('|'.join(sep_symbol[:]))
split_pattern2 = re.compile('|'.join(sep_symbol+[u':',u':', u'、']))

class BlackNameCodeTool:
    
    def __init__(self):
        self.code_type_pattern = { 'idno':u'[身份证]{2,4}[号码]+',
                                   'org':u'[组织机构]{2,6}[代码号]+',
                                   'credit':u'[社会信用]{2,6}[代码号]+', 
                                   'regno':u'[营业执照]{2,6}[代码号]+', }
        self.code_type_pattern = {key:re.compile(val) for key, val in self.code_type_pattern.items()}
        
    def process(self, name_info):
        code_map = {'idno':[], 'org':[], 'credit':[]}
        entity = []
        for type_, patt_ in self.code_type_pattern.items():
            _ = patt_.findall(name_info)
            if _:
                __ = re.split(patt_, name_info)[1:]
                code_map[type_] = [code_pattern.findall(item)[0] for item in __]
        _ = reduce(lambda x,y:x+y, code_map.values())
        
        if not _:
            codes = code_pattern.findall(name_info)
            if not codes:
                _t = patt1.findall(name_info)
                entity = name_info if not _t else name_info.split(_t[0])[0]
                entity = entity.split(u'等')[0]
                entity = re.split(split_pattern, entity)
            elif '*' in codes[0] or u'﹡' in codes[0]:
                code_ = codes[0]
                if len(code_) in (9, 10):
                    code_map['org'].append(code_)
                elif re.findall('[a-zA-Z]+', code_):
                    code_map['credit'].append(code_)
                elif len(code_) == 18:
                    code_map['idno'].append(code_)
                elif len(code_) == 15:
                    code_map['regno'].append(code_)
            else:
                code_ = codes[0]
                if checkIdcard(code_):
                    code_map['idno'].append(code_)
                elif check_organizationcode(code_):
                    code_map['org'].append(code_)
                elif re.findall('[a-zA-Z]+', code_):
                    code_map['credit'].append(code_)
                elif len(code_) == 15:
                    code_map['regno'].append(code_)
        _ = reduce(lambda x,y:x+y, code_map.values())
                    
        if not entity:
            _t = patt1.findall(name_info)
            entity = name_info if not _t else name_info.split(_t[0])[0]
            entity = entity.split(u'等')[0]
            entity = re.split(split_pattern, entity)
            
            if not entity:
                _t = patt2.findall(name_info)
                entity = name_info if not _t else name_info.split(_t[0])[0]
                entity = entity.split(u'等')[0]
                entity = re.split(split_pattern, entity)
        
        _ = list(set(_))
        if not _:
            if not entity:
                return []
            return [{'name':item, } for item in entity]
        else:
            if not entity:
                return code_map
        
        entity = [(item, name_info.find(item)) for item in entity]
        entity.sort(key=lambda x:-x[1])
        
        for key in list(code_map.keys()):
            if not code_map[key]:
                code_map.pop(key)
            else:
                code_map[key] = code_map[key][0]
        
        code_map['name'] = entity[0][0]
        other_entity = [item[0] for item in entity[1:]]
        if other_entity:
            __ = [{'name':item} for item in other_entity]
            return [code_map] + __
        return [code_map]
    
    def add_info1(self, name, idno):
        # 增加类型和曾用名
        info = name
        entity_array_ = self.process(info)
        #print(entity_array_)
        entity_array = copy.deepcopy(entity_array_)
        for i, d in enumerate(entity_array):
            if 'name' in d:
                name_ = d['name']
                d['type'] = _model_corp.entity_type(name_)
                _ = info.split(name_)[1]
                if u'曾用名' in _:
                    __ = _.split(u'曾用名')[1]
                    lst = re.split(split_pattern2, __)
                    for item in lst:
                        if len(item) >= 2:
                            d['alias'] = re.split(u'[），。,\.]+', item)[0]
                            break
                entity_array[i] = d
        if len(entity_array) == 1 and not re.findall('[^0-9A-Za-z\*\.]+', idno):
            code_ = idno
            if len(code_) in (9, 10):
                entity_array[0]['org'] = code_
            elif re.findall('[a-zA-Z]+', code_):
                entity_array[0]['credit'] = code_
            elif len(code_) == 18:
                entity_array[0]['idno'] = code_
            elif len(code_) == 15:
                entity_array[0]['regno'] = code_
        for i in range(len(entity_array)):
            entity_array[i]['name'] = entity_array[i]['name'].strip()
        return entity_array
    
    def get_(self, name, idno):
        # 去除号码标识和各类号码
        name = name.replace('(',u'（').replace(')',u'）')
        name_ = re.sub(u'[（|\(]+.*?[0-9a-zA-Z\*-]{9,20}[\)|）]*', '', name)
        name_ = re.sub(u'曾用名[:,，： ]*.*?[,， \)）]+', '', name_)
        name_ = re.sub(u'[住所地]{2,3}.{4,50}[ |,|。|，]?', '', name_)
        name_ = re.sub(u'[（\(]+.*?[\)）]+', '', name_)
        for pat in list(self.code_type_pattern.values()):
            name_ = re.sub(pat, '', name_)
        name_list = re.split(u'，|、|：|,|\.|:|;|；', name_)
        name_list = [item.lstrip(u'）').rstrip(u'（`') for item in name_list]
        # 获取实体名称
        name_list = [name__.strip('0123456789*.- \t\r\n') for name__ in name_list if name__]
        #print(name_list)
        name_, entity_array = name, []
        for _name in reversed(name_list):
            if not _name:
                continue
            map_ = {'name':_name}
            #print(map_)
            #print(name_, name_.split(_name))
            _t = name_.split(_name)
            name_, left_ = ''.join(_t[:-1]), _t[-1]
            # 获取号码
            _ = re.findall('[0-9a-zA-Z\*-]{9,20}', left_)
            code_ = _[0] if _ else ''
            #print(map_)
            if code_:
                for key, pat in self.code_type_pattern.items():
                    _ = pat.findall(left_)
                    if not _:
                        continue
                    map_[key] = code_
                if len(map_) == 1:
                    if checkIdcard(code_):
                        map_['idno'] = code_
                    elif check_organizationcode(code_) or len(code_) in (9,10):
                        map_['org'] = code_
                    elif re.findall('[a-zA-Z]{10,30}', code_):
                        map_['credit'] = code_
                    elif len(code_) == 15:
                        map_['regno'] = code_
            if len(map_) == 1 and idno:
                code_ = re.findall('[0-9a-zA-Z\.\*-]+', idno)
                code_ = code_[0] if code_ else ''
                if checkIdcard(code_):
                    map_['idno'] = code_
                elif check_organizationcode(code_) or len(code_) in (9,10):
                    map_['org'] = code_
                elif re.findall('[a-zA-Z]{10,30}', code_):
                    map_['credit'] = code_
                elif len(code_) == 15:
                    map_['regno'] = code_
            # 获取类型
            map_['type'] = _model_corp.entity_type(_name)
            # 获取曾用名
            #print(1, left_)
            if u'曾用名' in left_:
                __ = left_.split(u'曾用名')[1]
                lst = re.split(split_pattern, __)
                for item in lst:
                    if len(item) >= 2:
                        map_['alias'] = re.split(u'[），。,\.\)]+', item)[0]
                        break
            elif left_ and left_[0] in ('(', u'（'):
                _ = re.split(u'（|\(', left_)
                if _[1][0] == _name[0]:
                    map_['alias'] = re.split(u'[），。,\.\)]+', _[1])[0]
            entity_array.append(map_)
        return entity_array

    def get_info(self, name, idno, legal_person):
        d = {}
        d['party'] = self.get_(name, idno)
        d['legal_person'] = self.get_(legal_person, '') if re.sub(' |\t|\r|\n','',legal_person) not in ('*','不详','无','法定代表人','.','0','厂长','未知','暂无','暂无。','无法查询','查无','无该信息','卷宗内无此记录','情况不详') else [{'name':'', 'idno':''}]
        return d

def checkIdcard(idcard):
    Errors=['验证通过!','身份证号码位数不对!','身份证号码出生日期超出范围或含有非法字符!','身份证号码校验错误!','身份证地区非法!']
    area={"11":"北京","12":"天津","13":"河北","14":"山西","15":"内蒙古","21":"辽宁","22":"吉林","23":"黑龙江","31":"上海","32":"江苏","33":"浙江","34":"安徽","35":"福建","36":"江西","37":"山东","41":"河南","42":"湖北","43":"湖南","44":"广东","45":"广西","46":"海南","50":"重庆","51":"四川","52":"贵州","53":"云南","54":"西藏","61":"陕西","62":"甘肃","63":"青海","64":"宁夏","65":"新疆","71":"台湾","81":"香港","82":"澳门","91":"国外"}
    idcard=str(idcard)
    idcard=idcard.strip()
    idcard_list=list(idcard)
 
    #地区校验
    if idcard[:2] not in area or not area[(idcard)[0:2]]:
        return 0 #print (Errors[4])
    #15位身份号码检测
    if(len(idcard)==15):
        if((int(idcard[6:8])+1900) % 4 == 0 or((int(idcard[6:8])+1900) % 100 == 0 and (int(idcard[6:8])+1900) % 4 == 0 )):
            erg=re.compile('[1-9][0-9]{5}[0-9]{2}((01|03|05|07|08|10|12)(0[1-9]|[1-2][0-9]|3[0-1])|(04|06|09|11)(0[1-9]|[1-2][0-9]|30)|02(0[1-9]|[1-2][0-9]))[0-9]{3}$')#//测试出生日期的合法性
        else:
            ereg=re.compile('[1-9][0-9]{5}[0-9]{2}((01|03|05|07|08|10|12)(0[1-9]|[1-2][0-9]|3[0-1])|(04|06|09|11)(0[1-9]|[1-2][0-9]|30)|02(0[1-9]|1[0-9]|2[0-8]))[0-9]{3}$')#//测试出生日期的合法性
        if(re.match(ereg,idcard)):
            return 1 #print (Errors[0])
        return 0 #print (Errors[2])
    #18位身份号码检测
    elif(len(idcard)==18):
        #出生日期的合法性检查
        #闰年月日:((01|03|05|07|08|10|12)(0[1-9]|[1-2][0-9]|3[0-1])|(04|06|09|11)(0[1-9]|[1-2][0-9]|30)|02(0[1-9]|[1-2][0-9]))
        #平年月日:((01|03|05|07|08|10|12)(0[1-9]|[1-2][0-9]|3[0-1])|(04|06|09|11)(0[1-9]|[1-2][0-9]|30)|02(0[1-9]|1[0-9]|2[0-8]))
        if(int(idcard[6:10]) % 4 == 0 or (int(idcard[6:10]) % 100 == 0 and int(idcard[6:10])%4 == 0 )):
            ereg=re.compile('[1-9][0-9]{5}(19[0-9]{2}|20[0-9]{2})((01|03|05|07|08|10|12)(0[1-9]|[1-2][0-9]|3[0-1])|(04|06|09|11)(0[1-9]|[1-2][0-9]|30)|02(0[1-9]|[1-2][0-9]))[0-9]{3}[0-9Xx]$')#//闰年出生日期的合法性正则表达式
        else:
            ereg=re.compile('[1-9][0-9]{5}(19[0-9]{2}|20[0-9]{2})((01|03|05|07|08|10|12)(0[1-9]|[1-2][0-9]|3[0-1])|(04|06|09|11)(0[1-9]|[1-2][0-9]|30)|02(0[1-9]|1[0-9]|2[0-8]))[0-9]{3}[0-9Xx]$')#//平年出生日期的合法性正则表达式
        #//测试出生日期的合法性
        if(re.match(ereg,idcard)):
            #//计算校验位
            S = (int(idcard_list[0]) + int(idcard_list[10])) * 7 + (int(idcard_list[1]) + int(idcard_list[11])) * 9 + (int(idcard_list[2]) + int(idcard_list[12])) * 10 + (int(idcard_list[3]) + int(idcard_list[13])) * 5 + (int(idcard_list[4]) + int(idcard_list[14])) * 8 + (int(idcard_list[5]) + int(idcard_list[15])) * 4 + (int(idcard_list[6]) + int(idcard_list[16])) * 2 + int(idcard_list[7]) * 1 + int(idcard_list[8]) * 6 + int(idcard_list[9]) * 3
            Y = S % 11
            M = "F"
            JYM = "10X98765432"
            M = JYM[Y]#判断校验位
            if(M == idcard_list[17]):#检测ID的校验位
                return 1 #print (Errors[0])
    return 0

#--------------------------------------------------------------------------------------
#组织机构代码 http://blog.csdn.net/huilan_same/article/details/52103694?locationNum=12
CODEMAP = string.digits + string.ascii_uppercase # 用数字与大写字母拼接成CODEMAP，每个字符的index就是代表该字符的值
WMap = [3, 7, 9, 10, 5, 8, 4, 2] # 加权因子列表


def get_C9(bref):
    # C9=11-MOD（∑Ci(i=1→8)×Wi,11）
    # 通过本地计算出C9的值
    sum = 0
    for ind, i in enumerate(bref):
        Ci = CODEMAP.index(i)
        Wi = WMap[ind]
        sum += Ci * Wi

    C9 = 11 - (sum % 11)
    if C9 == 10:
        C9 = 'X'
    elif C9 == 11:
        C9 = '0'
    return str(C9)


def check_organizationcode(code):
    # 输入组织机构代码进行判断，如果正确，则输出'验证通过，组织机构代码证格式正确！'，错误则返回错误原因
    ERROR = '组织机构代码证错误!'
    if '-' in code:
        bref, C9_check = code.split('-')
    else:
        bref = code[:-1]
        C9_check = code[-1:]

    if len(bref) != 8 or len(C9_check) != 1:
        return 0 #ERROR + '（本体或校验码长度不符合要求）'
    else:
        try:
            C9_right = get_C9(bref)
        except ValueError:
            return 0  #ERROR + '(本体错误)'
        if C9_check != C9_right:
            return 0  #ERROR + '（校验码错误）'
        return 1 #'验证通过，组织机构代码证格式正确！'
        

m = BlackNameCodeTool()

if __name__ == '__main__':
    s = u'田英巧（身份证号330382199201173636）'
    #party = m.process(s)
    #party = m.get_info(s, '')
    print(check_organizationcode('XXXXXXX-X'))
