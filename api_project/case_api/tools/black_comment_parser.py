# -*- coding: utf-8 -*-

# 失信comment拆解

import re, requests, json

url = 'http://10.50.87.150:8080/v1/base/model_rec'

class BlackComment:
    
    def __init__(self):
        self.ind = 0
        
    def search_name(self, s):
        s = s[self.ind :]
        _ = re.findall(u'[被执行人]{3,}', s)
        if not _:
            return ''
        s_ = s.split(_[0])[1]
        s_ = re.split(',|，|。|;|；|在| ', s_)[0]
        #print('s_', s_) 
        s_ = s_ if s_ and s_[0] not in ('-',) else re.split('-+',s_)[-1]
        self.ind += s.find(s_)+len(s_)
        return s_
        
    def search_sex(self, s):
        s = s[self.ind :]
        sex_symbols = re.findall(u'男|女', s)
        if not sex_symbols:
            return ''
        sex = sex_symbols[0]
        self.ind += s.find(sex)+len(sex)
        return sex
        
    def search_idno(self, s):
        _ = re.split(u'[居民身份证号码省]{3,6}', s)
        if len(_) == 1:
            return ''
        idno = re.findall('[0-9A-Za-z\*\(（\)）]{9,18}', _[1])
        if not idno:
            return ''
        return idno[0]
        
    def search_orgcode(self, s):
        orgcode = re.findall('[0-9A-Za-z\*-]{9,10}', s)
        if orgcode:
            return orgcode[0]
        return ''
        
    def search_caseno(self, left):
        _ = re.findall(u'[（\(]+\d{4}[\)）]+[^A-Za-z号]*?号', left)
        if not _:
            _ = re.findall(u'[^本院]+?\d+号',left)
            if not _:
                return ''
            else:
                return _[0]
        return _[0]
        
    def search_all(self, s):
        party, left = {}, s
        partners, names = [], set()
        while 1:
            name_ = self.search_name(left)
            if not name_:
                self.ind = 0
                break
            if name_ in names:
                left = left[left.find(name_)+len(name_) :]
                self.ind = 0
                continue
            names.add(name_) 
            data = {'name':name_}
            data = json.dumps(data, ensure_ascii=False)
            res = requests.post(url, data=data.encode('utf-8'), headers={'access_key':'upgcredit'}).text
            res = json.loads(res)
            type_ = res['type']
            
            if type_ == u'个人':
                sex_ = self.search_sex(s)
                idno_ = self.search_idno(s)
                self.ind = 0
                partners.append({'name':name_, 'type':type_, 'sex':sex_, 'idno':idno_})
                left = left.split(name_, 1)[1]
            elif type_ == u'企业':
                orgcode_ = self.search_orgcode(s)
                self.ind = 0
                partners.append({'name':name_, 'type':type_, 'idno':orgcode_})
                left = left.split(name_, 1)[1]
            else:
                left = left.split(name_, 1)[1]
                self.ind = 0
            #print('left', left)
        
        party['party'] = partners
        caseno_ = self.search_caseno(left)
        if caseno_:
            party['caseno'] = caseno_
            left = left.split(caseno_)[-1]
        left = re.split(u'，|。|,|\.|；|;', left, 1)[-1]
        
        party['other'] = left
        
        return party
        
if __name__ == '__main__':
    
    m = BlackComment()
    print(m.search_all('失信被执行人-昆山瑞褀宏光电材料有限公司 57668531-3  主要负责人卢俊锋， 在本院（2014）苏中执字第0303号中，拒不履行生效法律文书确定的义务，隐匿财产并规避执行。'))
