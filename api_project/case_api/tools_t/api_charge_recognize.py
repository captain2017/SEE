#-*- coding:utf-8 -*-
#裁判文书原被告清洗

import pymysql,chardet,re,codecs,json,os
import pandas as pd
from . import entity_extract as ee 
from . import corp_detect as cpdt
from . import defendant_etl as defd
from . import api_charge_result as acr
from . import api_charge_case_end_date as acced

eng = '[（|\(]+[^\)）]*?([a-zA-Z’ ,.，&]+).*?[\)|）]*'  #用于EnglishName函数

m = ee.ChargeEntity('family_names.txt', 'plaintiff.txt', 'defandant.txt') #用于PersonEtl函数
recognize_corp = cpdt.CorpRecognize
corp_recognize =recognize_corp('train_char.txt', 'corp_samples.txt', 'noncorp_samples.txt') #用于PersonLabel函数


def CauseTypeSearch(cause_type_all):
    """案件类型字典
    cause_type_all -- a list or tuple of cause_type.
    """
    dic, first_str_all = {}, []
    for i,line in enumerate(cause_type_all):
        first_two_str = line[0:2]       
        if first_two_str not in first_str_all:
            first_str_all.append(first_two_str)        
        for i, str_da in enumerate(first_str_all):
            if line[0:2] == str_da:
                if str_da in dic :
                    dic[str_da].append(line)
                else:
                    dic[str_da] = [line]
                dic[str_da].sort(key=lambda x:-len(x))
    return dic

def EnglishName(pdname):
    '''取括号内的英文'''
    eng_list = re.findall(re.compile(eng),pdname)
    d = pdname
    for ii in eng_list:
        d = re.sub('[（|\(]+[^，、]*?%s[^，、]*?[\)|）]+' % ii,'',d)
    return d, eng_list
    return pdname, []

def ChargeFormat(charge):
    '''去掉文书的html、冗余字符等'''
    if not charge:
        return ''
    charge = re.sub(u'[<|＜].*?[>|＞]', '', charge)
    charge = re.sub(' |\t|\r|\n|　|    | ','', charge)
    charge = re.sub('&[a-zA-Z0-9;]{0,20}','',charge) 
    pun_list = ['Title','PubDate','Html','"','{','}','nbsp;','amp;divide;','\\xa0','nbsp']
    for item in pun_list:
        charge = charge.replace(item,'')
    return charge


class PersonETL:
    def __init__(self):

        """
        self.conn_read=pymysql.connect(host='mysql.rdsmgx10o2xj6cx.rds.bj.baidubce.com',user="data_sync",password="data_sync_2017",db="corp_doc",charset="utf8")
        self.cursor_read = self.conn_read.cursor()
        self.sql_content = "select tc.id,tc.uuid,tc.title,tj.content from t_corp_judge tc ,t_corp_judge_content tj where tc.id >{} and tc.uuid = tj.uuid  limit 1"
        #self.sql_title = "select uuid,id,title from t_corp_judge  where id >{} limit 1"
        """
        """
        self.conn_read = pymysql.connect(host='10.50.87.180',user="super_user",password="jkPsuDm2JS3",db="corp_doc",local_infile=1,charset="utf8")
        self.sql_content = "select t_id,uuid,title,content from t_corp_judge where t_id > {} limit 10"
        self.cursor_read = self.conn_read.cursor() 

        #入库数据库
        self.conn_insert=pymysql.connect(host='10.50.87.180',user="super_user",password="jkPsuDm2JS3",db="nono_test",local_infile=1,charset="utf8")
        self.sql_insert = "select max(t_id) from {0} "
        self.cursor_insert = self.conn_insert.cursor() 
        """
        self.path = os.popen("pwd").read().strip()+'/tools_t/' #linux中的相对路径
        with codecs.open(self.path + 'cause.txt','r','utf-8') as fc:
            self.cause_type_list = [line.strip().replace('\ufeff','') for line in fc.readlines()] #完整的案件类型

        with codecs.open(self.path + 'role.txt','r','utf-8') as f:
            ff = f.readlines()
            self.role_list_no, self.role_list = [line.strip()[::-1].replace('\ufeff','') for line in ff], [line.strip().replace('\ufeff','') for line in ff] #标题角色匹配字典

        with codecs.open(self.path + 'prep.txt','r','utf-8') as fpr: 
            self.prep = [line.strip().replace('\ufeff','') for line in fpr.readlines()] #原被告连接词：与、诉等

        with codecs.open(self.path + 'otherword.txt','r','utf-8') as fo:
            self.other_word = [line.strip().replace('\ufeff','') for line in fo.readlines()] #原被告中本院在执行等冗余词
        
        with codecs.open(self.path + 'delwords.txt','r','utf-8') as fd:
            self.del_word = [line.strip().replace('\ufeff','') for line in fd.readlines()]

        self.cause_type_all = CauseTypeSearch(self.cause_type_list)
    

    def ChargeSentence(self,charge,min_substr_len):  
        '''
            #从裁判文书中获取案件类型前面的字符串  例；AHSHH离婚纠纷一案，则获得结果为AHSHH 
            charge -- a list or tuple of strings.   
            min_substr_len -- minimum length of keys.
        '''
        L = len(charge)
        if L < min_substr_len: 
            return charge  #当待比对的案件纠纷长度小于最小案件类型，返回原值
        N = min_substr_len
        for ind in range(L-N+1):
            s = charge[ind : ind+N]
            if s in self.cause_type_all:
                a = self.cause_type_all[s]
                for i in range(len(a)):
                    if a[i] in charge:
                        inde = charge.index(a[i])
                        return charge[0:inde]
        return ''             

    def ChargeEtl(self,charge):
        '''提取含有一案的句子'''
        for item in charge.split('。'):
            if '一案' in item and ')一案' not in item:
                return item.split('一案')[0]
        return ''

    def GetPD(self,str_pd):
        p_l = []
        for item in self.role_list:
            if item in str_pd:
                ind = str_pd.find(item)
                p_l.append([item, ind,str_pd[len(item)+ind:]])
                str_pd = str_pd[:ind]
        if len(str_pd) > 1:
            p_l.append(['',-1,str_pd])
        p_l.sort(key=lambda x:x[1], reverse = 0)
        p_str, role_l = '', []
        for it in p_l:
            p_str = p_str + it[2]
            role_l.append(it[0])
        if not role_l:
            return '',self.PersonEnding(str_pd)

        role_l[0] = '' if ['' for role in self.role_list if role in p_str] else role_l[0] #预防某些角色无法被清洗   原审被告徐刘平、被告李留一
        if role_l[0] and len(role_l) == 1:
            return role_l[0], self.PersonEnding(p_str)
        if role_l[0] and ''.join(role_l) == role_l[0] :
            return role_l[0], self.PersonEnding(p_str)
        return '',self.PersonEnding(p_str)

    def Person_sub(self,text):

        span_ind = re.search('|'.join(self.role_list),text)
        if span_ind:
            text1 = text.replace(span_ind.group(),len(span_ind.group())*'$') #提取角色，将角色名替换
            return text1
        return text

    def PersonEtl1(self,str_d):
        '''第一种获取原被告及角色方案 PrepDivide 
           输入含有原被告的句子，输出列表 例："原告A与被告B离婚纠纷一案" 得到 [['原告','被告'],[A,B]]'''
       
        str_d = re.sub(u'[\(|（]+.{0,2}[原|审|二|一|上|诉|申|请|执|行|被|罪|再|赔|异|反]+.*?[）|\)]', '', str_d)  #去掉括号内的角色  上诉人（原审原告）马小涛XX纠纷一案  得到 上诉人马小涛XX纠纷一案
        str_d = re.sub(u'[（|\(]+.{0,3}[简下]+称+.*?[\)|）]', '',str_d) #去掉括号内以下简称的问题
        person = self.ChargeSentence(str_d,2)  #调用ChargeSentence 函数，返回切割后的原被告句子
     
        per_temp = self.Person_sub(person) 
        per_temp = self.Person_sub(per_temp) 
     
        for line in self.prep:
            ind =  per_temp.find(line)
            if ind != -1 :
                pl_se, de_se = person[:ind], person[ind+len(line):]
                pl, de = self.GetPD(pl_se), self.GetPD(de_se)
                return [pl[0],de[0]],[pl[1],de[1]]   #person[ind_p+len(pp):ind]
        return (['',''],['',''])

    def DelWords(self,person_end):
        for item in self.del_word:  #去脏数据 河南省郑州市中级人民法院不予受理通知书司建生、 范桂枝
            if item in re.sub('\d+','',person_end):
                return ''
        return person_end
   
    def DelNum(self,person):
        '''去掉当事人中的数字'''
        num_list = re.findall('\d+',person)
        if num_list:
            num_len = len(num_list[-1])
            num_ind = person.find(num_list[-1])
            ind = num_len + num_ind
            if ind == len(person):
                return person
            return person[ind:] if person[ind] != ')' and person[ind] != '）' else person[ind +1:]
        return person

    def PersonEnding(self,person_end):
        """
        去除本院执行等冗余数据
        """
        if len(person_end) < 2:
            return ''
        person_end = person_end.replace(' ','').replace('（）','').replace('【】','').replace('　','').strip()
        person_end = re.split('[\(|\（|\[|〔]\d+[\)|\）|\]|〕].*?号',person_end)[-1] #去带有案号的
        person_end = self.DelWords(person_end)   #去除带有冗余数据的原被告
        if not person_end:
            return ''
        person_end = self.DelNum(person_end)
        if person_end.find('（') == 0 or person_end.find('(') == 0:
            return ''
        person_end = re.sub('|'.join(self.role_list),'',person_end) #去除清洗后仍存在的原被告角色
        person_end = person_end[:-2] if person_end and person_end[-2:] == '关于' else person_end
        person_end = person_end[:-1] if person_end and (person_end[-1] == '犯' or person_end[-1] == '为')  else person_end  #去掉郑某某犯的情况
        person_end = person_end[1:] if person_end and person_end[0] in ['-','.','_','`','－','；','.','∶','①','】','㈠','㈡','㈢','㈣','㈦','㈧','就'] else person_end
        for line in self.other_word:
            other_ind = person_end.find(line)
            if other_ind != -1:
                return person_end[other_ind+len(line):]
        return person_end
        
    def PersonEtl2(self,charge):
        """第二种获取原被告及角色方案"""
        person_dic = m.extract_entity(charge)

        p, d = person_dic['plaintiff'], person_dic['defandant']
        p_, d_ = [self.PersonEnding(line) for line in p if self.DelWords(line)], [self.PersonEnding(line) for line in d if self.DelWords(line)]
        plaintiff, defandant  = '、'.join(p_) if p_ else '', '、'.join(d_) if d_ else ''
        return plaintiff,defandant

    def PersonEtl3(self,title):
        '''第三种获取原被告及角色方案 ——只处理刑事案件的被告 CrimeCauseETL'''
        if title and '等' not in title and '罪' in title and '书' in title:
            defendant = self.ChargeSentence(title.strip(),2)
            return '', self.PersonEnding(defendant)
        return '', ''

    def PersonEtl4(self,charge):
        """第四种获取原被告及角色方案"""
        person_dic = m.pattern_extract1(charge)
        p, d = person_dic['plaintiff'], person_dic['defandant']
        p_, d_ = [self.PersonEnding(line) for line in p if self.DelWords(line)], [self.PersonEnding(line) for line in d if self.DelWords(line)]
        plaintiff, defandant  = '、'.join(p_) if p_ else '', '、'.join(d_) if d_ else ''
        return plaintiff,defandant

    def PersonArray(self,title,charge):
        """
        通过四种清洗方案，补充完善原被告及角色 得到 [['原告','被告'],[A,B]]
        """
        if title and '等' not in title:#and '二审' not in title:
            pd_list_title = self.PersonEtl1(title)
            #print(pd_list_title)
            if len(pd_list_title[1][0]) >1 and len(pd_list_title[1][1])>1 :
               #print('初始方法',pd_list_title)
               return  pd_list_title

        if charge:
            charge_reason = self.ChargeEtl(charge)  
            pd_list_charge = self.PersonEtl1(charge_reason)
            #print('charge',pd_list_charge)
            if len(pd_list_charge[1][0]) >1 and len(pd_list_charge[1][1])>1 :
               #print('第一种方法')
               return pd_list_charge
            #print('第二种方法')
            pd_temp = self.PersonEtl2(charge)
            #print(pd_temp)
            pt = pd_list_charge[1][0] if len(pd_list_charge[1][0]) > len(pd_temp[0]) else pd_temp[0]  #保留原有值
            dt = pd_list_charge[1][1] if len(pd_list_charge[1][1]) > len(pd_temp[1]) else pd_temp[1]
            if pt or dt:
                return (['',''],[pt, dt])
            #print('第三种方法')
            pd_temp1 = self.PersonEtl3(title)
            pt1, dt1 = pd_temp1[0], pd_temp1[1]
            if not pt1 and not dt1:
                #print('第四种方法')
                pd_temp2 = self.PersonEtl4(charge)
                pt1 = pd_temp2[0]
                dt1 = pd_temp2[1]
            return (['',''],[pt1, dt1])
        return (['',''],['',''])

    def Role(self,name,charge,max_len=10):
        '''单个实体找对应角色'''
        ch_ = charge
        while 1:
            ind = ch_.find(name)
            if ind == -1:
                break
            text = ch_[max(ind-max_len, 0) :ind]
            text, ll_ = text[::-1], []
            for line in self.role_list_no:
                if line in text:
                    ll_.append((text.find(line), line))
            ll_.sort(key=lambda x:(x[0], -len(x[1])))
            if ll_:
                role = ll_[0][1][::-1]
                return role
            ch_ = ch_[ind+len(name) :]
        return '其他当事人'

    def TitleNameRole(self,name_list,charge):
        """根据当事人名字获取角色"""
        if not ''.join(name_list):
            return ['']
        charge = re.sub(u'[\(|（]+.{0,2}[原|审|二|一|上|诉|申|请|执|行|被|罪|再|赔|利|反]+.*?[）|\)]', '', charge)  #反诉被告
        charge = re.sub(u'[（|\(]+.{0,3}[简下]+称+.*?[\)|）]', '',charge) 

        name__ = []
        for indd in range(len(name_list)):
            charge = charge.replace(name_list[indd],'＃'+str(indd))
            name__.append('＃'+str(indd))

        return [self.Role(name, charge) for name in name__]
        
    def PersonLabel(self,plaintiff,defandant):
            #person = plaintiff + '、' + defandant  #以顿号合并原被告
            person = plaintiff + defandant
            ps = re.split('、|,|/|;|:|，|：|。',','.join(person))
            per_label = []
            for item in ps: 
                res = corp_recognize.entity_type(item) #cpdt.isCorp(fit_model, char_map, item)
                per_label.append(res)
            return per_label

    def PersonResult(self,title,charge):
        charge = ChargeFormat(charge)
        pd_temp = self.PersonArray(title,charge)
      
        pe_eng = EnglishName(pd_temp[1][0]) #原告字符串
        de_eng = EnglishName(pd_temp[1][1]) #被告字符串

        plaintiff = list(set(re.split('、|,|/|;|:|，|：|。',pe_eng[0])))  #返回去重后的原告列表pd_temp[1][0]
        defandant = list(set(re.split('、|,|/|;|:|，|：|。',de_eng[0]))) # pd_temp[1][1]
        defandant = [defd.entity_info(i)[0]['name']  if len(i) >3 and defd.entity_info(i) and i[-1] != '）' and i[-1] != ')' else i for i in defandant]
        pd_eng = pe_eng[1] + de_eng[1]   #原告与被告的英文名字列表
       
        role_pl = [pd_temp[0][0]]*len(plaintiff) if pd_temp[0][0] else self.TitleNameRole(plaintiff,charge) #返回原告角色列表
        role_de = [pd_temp[0][1]]*len(defandant) if pd_temp[0][1] else self.TitleNameRole(defandant,charge)
        role_pdeng = ['其他当事人'] * len(pd_eng) if pd_eng else [] #英文

        pd_end = plaintiff + defandant + pd_eng
        role_end = role_pl + role_de + role_pdeng
        entity_type = self.PersonLabel(plaintiff,defandant)  #以json格式返回关联人标识
        eng_entity_type = ['个人'] * len(pd_eng) if pd_eng else [] #英文
        entity_type = entity_type + eng_entity_type #英文
        result_json = [{'name':a, 'type':b, 'role':c} for a, b, c in zip(pd_end, entity_type,role_end) if a] if ''.join(pd_end+role_end) else []
        charge_result = acr.ChargeResult(charge)
        close_date = acced.CloseDate(charge)
        return  result_json, charge_result,close_date       #plaintiff, defandant, json.dumps(result_json,ensure_ascii=False)
    """
    def PersonDB(self,t_file1):
        '''连接数据库获取数据'''
        sql_insert = self.sql_insert.format(t_file1)
        self.cursor_insert.execute(sql_insert)
        
        max_id = self.cursor_insert.fetchall()[0][0]
        print(max_id)
        max_id = max_id if max_id else '0'
       
        #max_id =16991 #4000657 #92001
        sql_content  = self.sql_content.format(max_id)
        self.cursor_read.execute(sql_content)
        data = self.cursor_read.fetchall()
       
        #data = (('1','90E568A6196B45D7A599283873AD55C7', '原告郑巨龙(kjj.,kk)与被告王大mm敏、汪小敏、王中敏(jjj)离婚纠纷一案','原告郑骆驼,男，罪犯马骆驼,'),)
        f_tempcharge = codecs.open('/opt/app/BIN/programs-py/mysql-files/charge_person5.txt', 'w', 'utf-8')
        for item,(t_id,uuid,title,charge) in enumerate(data):
            if not title:
                title = ''  
         
            result = self.PersonResult(title,charge)
            #print(result)
            s = "\t".join([str(t_id),uuid,title.replace('\n','').replace('\t',''),'、'.join(result[0]),'、'.join(result[1]),result[2]])
            #print('s',s)
       
            f_tempcharge.write(s)
            f_tempcharge.write('\n')            
        f_tempcharge.close()
         
        sql_load_charge = """
                #load data local infile '/opt/app/BIN/programs-py/mysql-files/charge_person5.txt'  into table q_charge_person_new4 fields terminated by '\t' lines terminated by '\n'(t_id,uuid,title,plaintiff,defandant,entity_type)
    """
        self.cursor_insert.execute(sql_load_charge)
        self.conn_insert.commit()
        """

if __name__ == '__main__':


    rcd = PersonETL()
    a = rcd.PersonResult('郑巨荣与王敏离婚纠纷一案','原告郑巨荣，男，35岁，被告王敏，女，18岁')
    """
    for i in range(10):
        b = rcd.PersonDB('q_charge_person_new4')
    """
#os.remove('/opt/app/BIN/programs-py/mysql-files/charge_person5.txt')
    
    


















        


























































