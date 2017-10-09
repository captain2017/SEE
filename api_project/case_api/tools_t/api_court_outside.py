#-*- coding:utf-8 -*-
#python 3 -- 法院清洗 

import pandas as pd
import pymysql,codecs,os,re
from functools import reduce

def is_chinese(uchar):
    """判断一个unicode是否是汉字"""
    return  uchar >= u'\u4e00' and uchar<=u'\u9fa5'
    
def is_number(uchar):
    """判断一个unicode是否是数字"""
    return uchar >= u'\u0030' and uchar<=u'\u0039'
       
def is_alphabet(uchar):
    """判断一个unicode是否是英文字母"""
    return (uchar >= u'\u0041' and uchar<=u'\u005a') or (uchar >= u'\u0061' and uchar<=u'\u007a')
 
def is_other(uchar):
    """判断是否非汉字，数字和英文字符"""
    return  (is_chinese(uchar) or is_number(uchar) or is_alphabet(uchar))


def CourtLocalSearch(str_all, min_substr_len):
    '''裁判文书规范法院列表遍历
        str_all -- a list or tuple of strings. #str_all为完整规范化的法院列表
        min_substr_len -- minimum length of keys.#为自定义需要比对的法院名称最小长度 '''  
    d = {}  
    for i, line in enumerate(str_all):
        L = len(line)     
        if L < min_substr_len:
            '''当待比对的法院长度大于规范化的法院长度，返回原值所在的索引'''
            d['line'] = i
            continue

        N = min_substr_len
        while N <= L:
            '''当待比对的法院长度小于规范化的法院长度，则根据最小字符串长度截取规范化的法院长度，依次截取下去'''
            for ind in range(L-N+1):
                s = line[ind : ind+N]
                if s in d:
                    d[s].append(i)
                else:
                    d[s] = [i]
            N += 1   
    return d

#LCS算法用于验证
def LCS(sa, sb):
    '''
        Longest Common Continuous Series长度，采用动态规划算法
        sa, sb -- iterable object
        time complexity -- if sa, sb have lengths m, n correspondly,
                           then wunder the principal theorem, 
                           we conclude that the time complexity is O(m * n).
    '''
    la, lb = len(sa)+1, len(sb)+1
    str_array = [['']*lb for i in range(la)]  #将所有列表置空

    for i in range(1, la):
        for j in range(1, lb):
            if sa[i-1] == sb[j-1]:
                str_array[i][j] = str_array[i-1][j-1] + sa[i-1]
            else:
                a, b = str_array[i-1][j], str_array[i][j-1]
                str_array[i][j] = a if len(a) >= len(b) else b
    return str_array[-1][-1]

def DecLCS(sa,sb):
	min_len = min(len(sa), len(sb))
	res = LCS(sa, sb)
	dis_pro = (len(res) / min_len) if min_len > 0 else 1

	return dis_pro == 1.0

def ProvinceDic(court_province_list):
		"""获取相关省市"""
		d = {}
		for court, province, city in court_province_list:
			d[court] = [province, city]
		return d

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

class CourtETL:
	def __init__(self):

		#读取法院名称库
		self.path = os.popen("pwd").read().strip()+'/tools_t/' #linux中的相对路径
		with codecs.open(self.path + "court.txt", 'r', 'utf-8') as fc:
		#with codecs.open('court.txt','r','utf-8') as fc:
			f_t = fc.readlines()
			self.court_all = [line.strip().replace('\ufeff','').split(',')[0] for line in f_t]
			self.court_province = [line.strip().replace('\ufeff','').split(',') for line in f_t]
			self.courtall_city = [line[0]+line[2] for line in self.court_province]  #生成新的法院，例浙江杭州市西湖区人民法院杭州市

		#调用法院遍历函数
		self.dic = CourtLocalSearch(self.court_all,5) 
		self.province_dic = ProvinceDic(self.court_province)
	
		#用于单个字符串的字典
		self.intersect = lambda x,y:x&y
		self.court_all_ = self.create_court_word_dict(self.court_all)
		self.courtall_city_ = self.create_court_word_dict(self.courtall_city)

	def create_court_word_dict(self,court_list):
		"""
		创建单个字符串的法院字典。例杭州市西湖区人民法院的字典：{'杭':{22,33}} 22,23表示带有‘杭’字的法院索引
		"""
		char_to_court = {}
		for i, court in enumerate(court_list): #self.court_all
		    for uchar in court:
		        if uchar in char_to_court:
		            char_to_court[uchar].append(i)
		        else:
		            char_to_court[uchar] = [i]

		for uchar, courts in char_to_court.items():
		    char_to_court[uchar] = set(courts)
		return char_to_court

	def get_court(self, s,char_to_court):
		"""
		根据函数create_court_word_dict生成的字典，进行法院的提取
		"""
		if not s:
			return ''
		courts_ = [char_to_court[char] if char in char_to_court else set() for char in s]
		courts_index = reduce(self.intersect, courts_)
		return [self.court_all[item] for item in courts_index]

	def FindChargeCourt(self,charge,court,max_substr_len):

		if not court:
		    court = ''
		L = max_substr_len
		b = charge.find('法院')
		if b != -1:
		    N = 1
		    while N<=L:
		        s = charge[max(b-N,0):b]

		        if s in self.dic and  len(self.dic[s]) ==1:
		            return self.court_all[self.dic[s][0]]

		        if len(self.get_court(s,self.court_all_)) == 1:
		        	return self.get_court(s,self.court_all_)[0] 

		        if len(self.get_court(s,self.courtall_city_)) == 1:
		        	return self.get_court(s,self.courtall_city_)[0]
		        N +=1
		    return court
		

	def is_court(self,court,charge):
	    '''匹配court字典函数'''

	    if court in self.dic and len(self.dic[court]) == 1:
	    	court1 = self.court_all[self.dic[court][0]]
	    	return court1, self.province_dic[court1][0], self.province_dic[court1][1]

	    if len(self.get_court(court,self.court_all_)) == 1:
	    	court2 = self.get_court(court,self.court_all_)[0]
	    	return court2, self.province_dic[court2][0], self.province_dic[court2][1]

	    if len(self.get_court(court,self.courtall_city_)) == 1:
	    	court3 = self.get_court(court,self.courtall_city_)[0]
	    	return court3, self.province_dic[court3][0], self.province_dic[court3][1]

	    if charge:
	    	court4 = self.FindChargeCourt(charge,court,33)
	    	if court4 in self.province_dic:
	    		return court4, self.province_dic[court4][0], self.province_dic[court4][1]
	    return court, '其他', '其他'


	def norm_court(self,court,charge):
		"""规范化法院名称，以自建立的法院字典为准"""
		charge = ChargeFormat(charge)
		if not court:
			court = ''
		court = ''.join(list(filter(is_other,list(str(court))))) #去掉非中英文与数字的特殊符号
		court_ = self.is_court(court,charge)
		court_list = self.get_court(court_[0],self.court_all_)  #进行最后的规范化
		if len(court_list) == 1 and DecLCS(court,court_list[0]): #get_court 函数无顺序，所以用LCS算法判断
		 	return court_list[0], self.province_dic[court_list[0]][0], self.province_dic[court_list[0]][1]
		return court_

	


if __name__ == '__main__':

	a = CourtETL()
	print(a.norm_court('杭西湖','杭西'))
	"""
	#定义读取文书数据库
	conn_content=pymysql.connect(host='mysql.rdsmgx10o2xj6cx.rds.bj.baidubce.com',user="data_sync",password="data_sync_2017",db="corp_doc",charset="utf8")
	sql_content = "select tj.uuid,tj.court_name,tc.content from t_corp_judge tj,t_corp_judge_content tc where  tj.uuid = tc.uuid  limit 100000, 10000"
	cursor_content = conn_content.cursor()
	cursor_content.execute(sql_content)
	data = cursor_content.fetchall()
	for uuid,court,content in data:
		print(court,'----------',a.norm_court(court,content),'------------',uuid)
	"""
	
