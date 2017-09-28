# -*- coding: utf-8 -*-

# 生成最终表，按行扩展

import pymysql as pm
import codecs, os

db1, db2 = ('10.50.87.180', 'super_user', 'jkPsuDm2JS3', 'nono_test'), ('172.16.2.185','root2','123456','bigwave_api') #('10.50.87.181','super_user','pjHusHWN8sd','bigwave_api')
#db2 = db1

(a1, b1, c1, d1), (a2, b2, c2, d2) = db1, db2
source_conn, target_conn = pm.connect(host=a1, 
                                      user=b1, 
                                      passwd=c1, 
                                      db=d1, 
                                      charset='utf8', 
                                      local_infile=1), \
                           pm.connect(host=a2,
                                      user=b2,
                                      passwd=c2,
                                      db=d2,
                                      charset='utf8', 
                                      local_infile=1)
                                          
source_cursor, target_cursor = source_conn.cursor(), \
                               target_conn.cursor()

file_path = '/opt/app/BIN/programs-py/mysql-files/tmp_data.txt'
sql = "select name, type, related_name, source, amount, uuid_list from common_role_info where role = '{}' limit {},{}"

def combine_common(role):
    i, n_line = 0, 100 * 10000
    pair_dict, key_sep = {}, 'tyqsb'
    
    while 1:
        sql_ = sql.format(role, i*n_line, n_line)
        source_cursor.execute(sql_)
        res = source_cursor.fetchall()
        
        if not res:
            break
            
        for tup in res:
            tup = list(tup)
            _ = key_sep.join(tup[:3])
            if _ in pair_dict:
                if tup[3] in pair_dict[_]:
                    continue
                else:
                    pair_dict[_][tup[3]] = tup[4:]
            else:
                pair_dict[_] = {tup[3]:tup[4:]}
                
        i += 1
    
    f = codecs.open(file_path, 'w', 'utf-8')    
    for pair_key, pair_val in pair_dict.items():
        _ = pair_key.split(key_sep)
        total = sum([val[0] for val in list(pair_val.values())])
        _.insert(2, total)
        _.append(role)
        _.extend(pair_val[u'开庭'] if u'开庭' in pair_val else [0, ''])
        _.extend(pair_val[u'文书'] if u'文书' in pair_val else [0, ''])
        
        if len(_) != 9:
            print(str(pair_key) + str(_))
            continue
        
        f.write('\t'.join([str(item) for item in _]))
        f.write('\n')
    f.close()
    
    load_ = "load data local infile '{}' into table common_interest_copy character set utf8 fields terminated by '\t' lines terminated by '\n' (name,type,total,related_name,role,court_amount,court_uuid_list,doc_amount,doc_uuid_list)".format(file_path)
    target_cursor.execute(load_)
    target_conn.commit()
    os.remove(file_path)

# 合并主函数
def combine_main():
    for role in (u'原告', u'被告'):
        combine_common(role)
        
combine_main()

source_conn.close()
target_conn.close()
