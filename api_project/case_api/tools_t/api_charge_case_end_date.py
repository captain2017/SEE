#-*- coding:utf-8 -*-
#python 3
#裁判文书审结日期清洗

from . import CloseDate as cd
from . import DateFormat as df   #结案日期
from . import Base as base
import re

dateetl = df.DateFormat()  #审结日期清洗工具

def GetChargeDate(charge):
    '''文书中获取结案日期'''  
    if not charge:
        return ''
    close_date = re.findall(r'[二|一][〇|?|０|○|九]{1,1}.{2,2}年.*?月[一二三四五六七八九十]{1,3}日*',charge)
    #close_date = re.findall(r'[二|一][〇|?|０|○|九]{1,1}.{2,2}年.*?月.*?日',charge)
    if len(close_date) > 1:
        close_date = re.findall(r'([二|一][〇|?|０|○|九]{1,1}.{2,2}年.{1,5}月[一二三四五六七八九十]{1,3}日*).{0,6}书记员',charge)
    if len(close_date) == 1: #会出现多个日期，目前只取单个日期的值
        return close_date[0] if close_date[0][-1] == '日' else close_date[0]+'日'
    return ''


def CloseDate(charge):
        '''清洗close_date'''
        """
        if dateetl.Tformat(close_date) and close_date != '0000-00-00':  #找出非空日期，并规范化格式
            return str(close_date).strip().replace('/','-')  
        """
        new_close_date = GetChargeDate(charge)
        new_close_date = cd.QFormat(new_close_date)
        close_date_ = dateetl.Tformat(new_close_date) 
        return close_date_
        return ''#找不到值填充的，均以空字符串填充


charge = '裁定如下，审结日期二〇一七年七月八日'
#print(CloseDate(charge))