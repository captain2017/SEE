#-*- coding:utf-8 -*-
import re,datetime

#审结日期：建立日期转换字典
dic = {'〇':'0','０':'0','○':'0','元':'1','—':'1','一':'1','二':'2','三':'3','四':'4','五':'5','六':'6','七':'7','八':'8','九':'9'}
#月、日 日期列表
date_str=set(['〇','０','○','元','—','一','二','三','四','五','六','七','八','九','十'])
#年日期列表
date_str_year=set(['〇','０','○','元','—','一','二','三','四','五','六','七','八','九'])

def is_chinese(uchar):
    """判断一个unicode是否是汉字"""
    return  uchar >= u'\u4e00' and uchar<=u'\u9fa5'

def type_to_date(us):
    '''close_date 月日排除多余字符'''
    return 1 if len([item for item in list(us) if item in date_str]) == len(list(us)) else 0

def type_to_date_year(us):
    '''close_date 年排除多余字符'''
    return 1 if len([item for item in list(us) if item in date_str_year]) == len(list(us)) else 0

#定义年转换函数
def nstr_to_year(us):
    '''close_date 年转换函数'''
    try:
        us1=us.replace('?','〇')
        if is_chinese(us1) and type_to_date_year(us1) == 1:
            return ''.join([dic[year_str] for year_str in us1])
        else:
            return '0000'
    except:
        return '0000'
 
#定义月、日转换函数
def nstr_to_date(us):
    '''close_date月、日转换函数'''
    try:
        if is_chinese(us) and type_to_date(us) == 1 :
            if len(us) == 1:
                return '0' + dic[us] if us != '十' else '10'
            elif len(us) == 2:
                return '1' + dic[us[1]] if us[0] == '十' else dic[us[0]] + '0'
            elif len(us) == 3:
                return dic[us[0]] + dic[us[2]]
        return '00'
    except:
        return '00'

def QFormat(close_date):

    close_date_ = re.findall(re.compile(r'(.*?)年(.*?)月(.*?)日'),close_date)
    for year,month,date in close_date_:
        year, month, date = nstr_to_year(year), nstr_to_date(month), nstr_to_date(date)
        close_date__ = [year,month,date]
        return '-'.join(close_date__)
    return ''

a = QFormat('1980年3月20日')
#print(a)