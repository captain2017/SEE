# -*- coding: utf-8 -*-

# 裁定结果

import pymysql as pm
import codecs, re, os

sep_symbol = [u',', u';', u':', u'，', u'。', u'：', u' ']
split_pattern = '|'.join(sep_symbol)

judge_start = [u'判决如下', u'裁定如下',u'决定如下',u'复查认为',u'审查认为',u'审理查明',u'双方当事人自愿达成如下协议',u'达成如下调解协议',u'特发出如下支付令']

path = os.popen("pwd").read().strip()+'/tools_t/' #linux中的相对路径
with codecs.open(path + "result_role.txt", 'r', 'utf-8') as f:
#with codecs.open('result_role.txt','r','utf-8') as f:
    fr = f.readlines()
    dr = [line.strip().replace('\ufeff','') for line in fr]
    da = '|'.join(dr)

judge_end2 = re.compile(da)
d, pun = [],  "。，;,；"
for i in pun:
    for j in dr:
        nn = i+j
        d.append(nn)
judge_end1 = '|'.join(d)

"""
db_info = ('10.50.87.180', 'super_user', 'jkPsuDm2JS3', 'nono_test')
a, b, c, d = db_info
conn = pm.connect(host=a, user=b, passwd=c, db=d, local_infile=1, charset='utf8')
cursor = conn.cursor()

#db_info1 = ('mysql.rdsmgx10o2xj6cx.rds.bj.baidubce.com', "data_sync", "data_sync_2017", "corp_doc")
db_info1 = ('10.50.87.180', 'super_user', 'jkPsuDm2JS3', 'corp_doc')
a1, b1, c1, d1 = db_info1
conn_read = pm.connect(host=a1, user=b1, passwd=c1, db=d1, charset='utf8')
cursor_read = conn_read.cursor()
"""

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

def Note(content):
    '''通知书类型的结果清洗'''
    if not content:
        return ''
    cno_list = re.findall(re.compile(u'[（|\(]\d+[）|\)].*?号' ),content) #找出文中的所以案号
    date_list = re.findall(r'(二[〇|?|０|○]{1,1}.{2,2}年.{1,5}月.{1,5}日)',content) #找出末尾二〇一六年一月四日
    if cno_list and date_list:
        c_ind = content.find(cno_list[0])
        pre = c_ind + len(cno_list[0])
        d_ind = content.find(date_list[-1])
        content = content[pre:d_ind]
        return content
    return ''

def DeterMIne(content):
    '''裁判文书裁定结果'''

    j_str = ''
    if not content:
        return ''
    for item in judge_start:
        if content.find(item) != -1:
            j_str = item
            break
    if not j_str:
        return ''
    s = content.split(j_str)[-1]
    lst = re.split(split_pattern, s)
    try:
        head = [item for item in lst if item][0]
    except:
        head = lst[0]
    s = s[s.find(head) :]
    #第一种方法 审判员前标点或结果中有被执行人等关键字
    __ = re.split(judge_end1, s)
    s1 = __[0] + '。' if len(__) >1 else ''
    if s1:
        return s1
    #第二种方法 审判员前无标点或结果中有被执行人等关键字
    s_, _s = s[:-25], s[-25:]
    _s_ = re.split(da, _s)[0]
    _s_ = re.sub(r'(二[〇|?|０|○]{1,1}.{2,2}年.{1,5}月.{1,5}日)','',_s_)
    s2 = s_ + _s_ 
    #s2 = s_ + re.split(da, _s)[0] + '。'
    if s2:
        s2 = s2 + '。' if s2[-1] != '。' else s2
        return s2
    return ''

def ChargeResult(content):
    '''裁判文书裁定结果'''
    content = ChargeFormat(content)
    res1 = DeterMIne(content)
    if res1:
        return res1
    if '通知书' in content:
        res2 = Note(content)
        if res2:
            return res2
    return ''
"""
def ChargeResultDB():

    n_line = 10000
    sql = "select max(t_id) from charge_result_test2"
    cursor.execute(sql)
    max_id = cursor.fetchall()
    max_id = max_id[0][0] if max_id[0][0] else 0
    print(max_id)

    #max_id = 14111991
    sql_charge = "select id, uuid, content from t_corp_judge where id > {} limit {}".format(max_id, n_line)
    cursor_read.execute(sql_charge)
    res = cursor_read.fetchall()
    if not res:
        return ''

    #res = ((1,'uuy','规定，决定如下： 驳回赵满仓的申诉。红烧鸡块二〇一四年十月三十一日'),)
    f_tempcharge = codecs.open('/opt/app/BIN/programs-py/mysql-files/charge_result2.txt', 'w', 'utf-8')
    for ind, (t_id, uuid, content) in enumerate(res):
        result = ChargeResult(content)
        #print(t_id, uuid, '---',result)
        s = "\t".join([str(t_id),result,uuid])
    
        f_tempcharge.write(s)
        f_tempcharge.write('\n')
    
    f_tempcharge.close()
   
    sql_load_charge = """
                #load data local infile '/opt/app/BIN/programs-py/mysql-files/charge_result2.txt' ignore into table charge_result_test2 fields terminated by '\t' lines terminated by '\n'(t_id,result,uuid)
""" 
    cursor.execute(sql_load_charge)
    conn.commit() 
"""    

if __name__ == '__main__':

    a = ChargeResult('西湖法院，裁定如下：驳回上诉。审判长：高小青')
    print(a)
    """
    for i in range(3000):
        a = ChargeResultDB()
        #print(a)
    """
#os.remove('/opt/app/BIN/programs-py/mysql-files/charge_result2.txt')
   
