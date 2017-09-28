#-*- coding:utf-8 -*-
#裁判文书原被告清洗

import pymysql,chardet,re,codecs,time,json,os
import pandas as pd
from . import entity_extract as ee 
from . import corp_detect as cpdt


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

def ChargeFormat(charge):
    '''去掉文书的html、冗余字符等'''
    if not charge:
        return ''
    charge = re.sub(u'<.*?>', '', charge)
    charge = re.sub(' |\t|\r|\n|　','', charge)
    pun_list = ['Title','PubDate','Html','"','{','}','nbsp','\\xa0']
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
        self.sql_content = "select t_id,uuid,title,content from t_corp_judge where t_id > {} limit 1 "
        self.cursor_read = self.conn_read.cursor() 

        #入库数据库
        self.conn_insert=pymysql.connect(host='10.50.87.180',user="super_user",password="jkPsuDm2JS3",db="nono_test",local_infile=1,charset="utf8")
        self.sql_insert = "select max(t_id) from {0} "
        self.cursor_insert = self.conn_insert.cursor() 
        """
        self.path = os.popen("pwd").read().strip()+'/tools_t/' #linux中的相对路径
        with codecs.open(self.path + 'cause.txt','r','utf-8') as fc:
            self.cause_type_list = [line.strip().replace('\ufeff','') for line in fc.readlines()] #完整的案件类型

        with codecs.open(self.path +'role.txt','r','utf-8') as f:
            ff = f.readlines()
            self.role_list_no, self.role_list = [line.strip()[::-1].replace('\ufeff','') for line in ff], [line.strip().replace('\ufeff','') for line in ff] #标题角色匹配字典

        with codecs.open(self.path +'prep.txt','r','utf-8') as fpr: 
            self.prep = [line.strip().replace('\ufeff','') for line in fpr.readlines()] #原被告连接词：与、诉等

        with codecs.open(self.path +'otherword.txt','r','utf-8') as fo:
            self.other_word = [line.strip().replace('\ufeff','') for line in fo.readlines()] #原被告中本院在执行等冗余词
        
        with codecs.open(self.path +'delwords.txt','r','utf-8') as fd:
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
        for pp in self.role_list:
            if str_pd.find(pp) != -1 :
                role = pp
                per = self.PersonEnding(str_pd[str_pd.find(pp)+len(pp):])
                if not [per.find(pp) for pp in self.role_list if per.find(pp) != -1]:    
                    break
            else:
                role = ''
                per = self.PersonEnding(str_pd)
        return role, per

    def GetPD1(self,str_pd):  
        str__ = re.split('、|,|/|;|:|，|：|。',str_pd)
        role_l, per_l = [], []
        for item in str__:
            flag = False
            for ie in self.role_list:
                if ie in item and not flag:
                    role_l.append(ie)
                    per_l.append(self.PersonEnding(item[item.find(ie)+len(ie):]))
                    flag = True
                    break
            if (not flag):
                role_l.append('')
                per_l.append(self.PersonEnding(item))
        if role_l[0] and len(role_l) == 1:
            return role_l[0],  '，'.join(per_l)
        if role_l[0] and ''.join(role_l) == role_l[0] :
            return role_l[0],  '，'.join(per_l)
        return '', '，'.join(per_l)

    def Person_sub(self,text):

        span_ind = re.search('|'.join(self.role_list),text)
        if span_ind:
            text1 = text.replace(span_ind.group(),len(span_ind.group())*'$') #提取角色，将角色名替换
            return text1
        return text

    def PrepDivide(self,str_d):
        '''第一种获取原被告及角色方案
           输入含有原被告的句子，输出列表 例："原告A与被告B离婚纠纷一案" 得到 [['原告','被告'],[A,B]]'''
        
        str_d = re.sub(u'[\(|（][原|审|二|一|上|诉|申|请|执|行|被|罪|再|赔|异]+.*?[）|\)]', '', str_d)  #去掉括号内的角色  上诉人（原审原告）马小涛XX纠纷一案  得到 上诉人马小涛XX纠纷一案
        str_d = re.sub(u'[（|\(]+.{0,3}[简下]+称+.*?[\)|）]', '',str_d) #去掉括号内以下简称的问题
        person = self.ChargeSentence(str_d,2)  #调用ChargeSentence 函数，返回切割后的原被告句子
        #print('person',person)
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

    def PersonEnding(self,person_end):
        """
        去除本院执行等冗余数据
        """
        if len(person_end) < 2:
            return ''
        person_end = person_end.replace(' ','').strip()
        person_end = re.split('[\(|\（]\d+[\)|\）].*?号',person_end)[-1] #去带有案号的
        person_end = self.DelWords(person_end)   #去除带有冗余数据的原被告
        person_end = re.sub('|'.join(self.role_list),'',person_end) #去除清洗后仍存在的原被告角色
        person_end = person_end[:-2] if person_end and person_end[-2:] == '关于' else person_end
        person_end = person_end[:-1] if person_end and (person_end[-1] == '犯' or person_end[-1] == '为')  else person_end  #去掉郑某某犯的情况
        
        for line in self.other_word:
            other_ind = person_end.find(line)
            if other_ind != -1:
                return person_end[other_ind+len(line):]
        return person_end
        
    def PersonEtl2(self,charge):
        """第二种获取原被告及角色方案"""
        person_dic = m.extract_entity(charge)
        #print('dic',person_dic)
        p, d = person_dic['plaintiff'], person_dic['defandant']
        #print(p,d)
        p_, d_ = [line for line in p if self.DelWords(line)], [line for line in d if self.DelWords(line)]
        plaintiff, defandant  = '、'.join(p_) if p_ else '', '、'.join(d_) if d_ else ''
        return plaintiff,defandant

    def PersonEtl3(self,charge):
        """第三种获取原被告及角色方案"""
        person_dic = m.pattern_extract1(charge)
        p, d = person_dic['plaintiff'], person_dic['defandant']
        p_, d_ = [line for line in p if self.DelWords(line)], [line for line in d if self.DelWords(line)]
        plaintiff, defandant  = '、'.join(p_) if p_ else '', '、'.join(d_) if d_ else ''
        return plaintiff,defandant

    def PersonArray(self,title,charge):
        """
        在函数PrepDivide 的基础上，补充完善原被告及角色 得到 [['原告','被告'],[A,B]]
        """
        if title and '等' not in title:#and '二审' not in title:
            pd_list_title = self.PrepDivide(title)
            if len(pd_list_title[1][0]) >1 and len(pd_list_title[1][1])>1 :
               return  pd_list_title

        if charge:
            charge_reason = self.ChargeEtl(charge)  
            pd_list_charge = self.PrepDivide(charge_reason)
            if len(pd_list_charge[1][0]) >1 and len(pd_list_charge[1][1])>1 :
               return pd_list_charge

            pd_temp = self.PersonEtl2(charge)
            pt = pd_list_charge[1][0] if len(pd_list_charge[1][0]) > len(pd_temp[0]) else pd_temp[0]  #保留原有值
            dt = pd_list_charge[1][1] if len(pd_list_charge[1][1]) > len(pd_temp[1]) else pd_temp[1]
            
            if not pt and not dt:
                pd_temp1 = self.PersonEtl3(charge)
                pt = pd_temp1[0]
                dt = pd_temp1[1]
            return (['',''],[pt, dt])
        return (['',''],['',''])

    
    def TitleNameRole(self,name_list,charge,max_len):
        """根据当事人名字获取角色"""
        if not ''.join(name_list):
            return ['']
      
        charge = re.sub(u'\([原|审|二|一|上|诉|申|请|执|行|被|罪|再|赔|利]+.*?\)', '', charge)  
        charge = re.sub(u'（[原|审|二|一|上|诉|申|请|执|行|被|罪|再|赔|利]+.*?\）', '', charge)
        charge = re.sub(u'[（|\(]+.{0,3}[简下]+称+.*?[\)|）]', '',charge) 
        ll = []
        for name in name_list:
            ind = charge.find(name)
            if ind == -1:
                return ['其他当事人']*len(name_list)  #解决原告单独写的问题：原告马大涛、原告马小桃与被告王大敏、王小敏民间借贷纠纷一案
            
            text = charge[ind-max_len:ind] if max_len < ind else charge[:ind]
            text, ll_ = text[::-1], []
            for line in self.role_list_no:
                if line in text:
                    ll_.append((text.find(line), line))
            ll_.sort(key=lambda x:(x[0], -len(x[1])))
            ll.append(ll_[0][1][::-1] if ll_ else '其他当事人')
        return ll

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

        plaintiff = list(set(re.split('、|,|/|;|:|，|：|。',pd_temp[1][0])))  #返回去重后的原告列表
        defandant = list(set(re.split('、|,|/|;|:|，|：|。',pd_temp[1][1])))  
      
        role_pl = [pd_temp[0][0]]*len(plaintiff) if pd_temp[0][0] else self.TitleNameRole(plaintiff,charge,10) #返回原告角色列表
        role_de = [pd_temp[0][1]]*len(defandant) if pd_temp[0][1] else self.TitleNameRole(defandant,charge,10)
        
        pd_end = plaintiff + defandant
        role_end = role_pl + role_de
        entity_type = self.PersonLabel(plaintiff,defandant)  #以json格式返回关联人标识
        result_json = [{'name':a, 'type':b, 'role':c} for a, b, c in zip(pd_end, entity_type,role_end) if a] if ''.join(pd_end+role_end) else []
        return result_json #json.dumps(result_json,ensure_ascii=False)
    
    def PersonDB(self,t_file1):
        
        sql_insert = self.sql_insert.format(t_file1)
        self.cursor_insert.execute(sql_insert)

        max_id = self.cursor_insert.fetchall()[0][0]
        print(max_id)
        max_id = max_id if max_id else '0'
       
        #max_id =417 #4000657 #92001
        sql_content  = self.sql_content.format(max_id)
        self.cursor_read.execute(sql_content)
        data = self.cursor_read.fetchall()
       
        #data = (('1','90E568A6196B45D7A599283873AD55C7', '罪犯马','原告郑骆驼,男，罪犯马骆驼,'),)
        #f_tempcharge = codecs.open('/opt/app/BIN/programs-py/mysql-files/charge_person2.txt', 'w', 'utf-8')
        for item,(t_id,uuid,title,charge) in enumerate(data):
            if not title:
                title = ''  
            result = self.PersonResult(title,charge)
            #print(result)
        """
            s = "\t".join([str(t_id),uuid,title.replace('\n','').replace('\t',''),'、'.join(result[0]),'、'.join(result[1]),result[2]])
            #print('s',s)
            f_tempcharge.write(s)
            f_tempcharge.write('\n')
                    
        f_tempcharge.close()
         
        sql_load_charge = """
                #load data local infile '/opt/app/BIN/programs-py/mysql-files/charge_person2.txt'  into table q_charge_person_new fields terminated by '\t' lines terminated by '\n'(t_id,uuid,title,plaintiff,defandant,entity_type)
        """
        self.cursor_insert.execute(sql_load_charge)
        self.conn_insert.commit()
        """

if __name__ == '__main__':


    rcd = PersonETL()
    a = rcd.PersonResult('原告李银萍与被告徐刘平民间借贷纠纷一案','原告黄某某，非法经营一审刑事判决书让他回娘家')
    print(a)
    """
    for i in range(1):
        b = rcd.PersonDB('q_charge_person_new')  
    """
  

#os.remove('/opt/app/BIN/programs-py/mysql-files/charge_person2.txt')
    
















        


























































