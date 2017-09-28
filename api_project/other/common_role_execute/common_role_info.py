# -*- coding: utf-8 -*-

# 共同原被告清洗

import pymysql as pm
import codecs, re, math, os

sql_total_get_ = "select name, uuid from {} where role = '{}' and type = '企业' limit {},{}"
sql_total_load_ = "load data local infile '{}' into table common_role_info character set utf8 fields terminated by '\t' lines terminated by '\n' (name,type,role,amount,related_name,uuid_list,source)"

table_ = {u'开庭': 't_court', u'文书': 't_doc'}

'''
sql_new_get_ = "select {}, uuid from t_court where create_time >= '{}' and role = '{}', type = '企业' limit {},{}"
sql_new_insert_ = ""
sql_new_update_ = ""
'''

file_path = '/opt/app/BIN/programs-py/mysql-files/tmp_data.txt'

symbols_ = ['0','1','2','3','4','5','6','7','8','9','A','B','C','D','E','F']
symbols = []
for _ in symbols_:
    for __ in symbols_:
        symbols.append(_+__)
symbols += symbols_

primes  = [2,3,5,7,11,13,17,19,23,29,31,37,41,43,47,53,59,61,67,71,73,79,83,89,97,101,103,107,109,113,127,131,137,139,149,151,157,163,167,173,179,181, \
           191,193,197,199,211,223,227,229,233,239,241,251,257,263,269,271,277,281,283,293,307,311,313,317,331,337,347,349,353,359,367,373,379,383,389, \
           397,401,409,419,421,431,433,439,443,449,457,461,463,467,479,487,491,499,503,509,521,523,541,547,557,563,569,571,577,587,593,599,601,607,613,617, \
           619,631,641,643,647,653,659,661,673,677,683,691,701,709,719,727,733,739,743,751,757,761,769,773,787,797,809,811,821,823,827,829,839,853,857,859, \
           863,877,881,883,887,907,911,919,929,937,941,947,953,967,971,977,983,991,997,1009,1013,1019,1021,1031,1033,1039,1049,1051,1061,1063,1069,1087,1091, \
           1093,1097,1103,1109,1117,1123,1129,1151,1153,1163,1171,1181,1187,1193,1201,1213,1217,1223,1229,1231,1237,1249,1259,1277,1279,1283,1289,1291,1297, \
           1301,1303,1307,1319,1321,1327,1361,1367,1373,1381,1399,1409,1423,1427,1429,1433,1439,1447,1451,1453,1459,1471,1481,1483,1487,1489,1493,1499,1511, \
           1523,1531,1543,1549,1553,1559,1567,1571,1579,1583,1597,1601,1607,1609,1613,1619,1621,1627,1637,1657,1663,1667,1669,1693,1697,1699,1709,1721,1723, \
           1733,1741,1747]
           
if len(primes) != len(symbols):
    quit()

prime_dict = {symbol:prime for prime, symbol in zip(primes, symbols)}
mod_ = 500 * 10000
def ModHash(s):
    _, m_hash = s, 1 #1 % mod_
    if len(_) & 1:
        __ = [a+b for a, b in zip(_[::2][:-1], _[1::2])] + [_[-1]]
    else:
        __ = [a+b for a, b in zip(_[::2], _[1::2])]
    for char in __:
        m_hash = ( m_hash * prime_dict[char] ) % mod_ if char in prime_dict else 0
    return m_hash
'''
def ModHash(s):
    _, m_hash = list(s), 1 #1 % mod_
    for char in _:
        m_hash = ( m_hash * prime_dict[char] ) % mod_
    return m_hash
'''

class CommonRoleInfo:
    
    def __init__(self):
        pass
        
    def compute_common_role(self, mode, source_db, target_db, role, source):
        # mode表示更新模式 'total'表示全部重新计算，'new'计算新增数据
        self.mode = mode
        (a1, b1, c1, d1), (a2, b2, c2, d2) = source_db, target_db
        self.source_conn, self.target_conn = pm.connect(host=a1, 
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
        
        self.source_cursor, self.target_cursor = self.source_conn.cursor(), \
                                                 self.target_conn.cursor()
        
        if self.mode == 'total':
            self.compute_total2(role, source)
        elif self.mode == 'new':
            self.compute_new(role, source)
        else:
            pass
            
        self.source_conn.close()
        self.target_conn.close()
        
    def compute_total(self, role, source, n_line=100 * 10000):
        name_uuid, i = {}, 0
        while 1:
            sql = sql_total_get_.format(table_[source], role, i*n_line, n_line)
            self.source_cursor.execute(sql)
            res = self.source_cursor.fetchall()
            
            if not res:
                break
            print("length of res is: ", len(res))
            for name, uuid in res:
                if len(name) <= 1:
                    continue
                if name in name_uuid:
                    name_uuid[name].append(uuid)
                else:
                    name_uuid[name] = [uuid]
            i += 1
            print("line %d complete." % (i*n_line))
        
        print("name to uuid finished...")            
        name_uuid = [(key, sorted(val)) for key, val in name_uuid.items()]
        name_uuid.sort(key=lambda x:(x[1][0], x[1][-1]))
        L = len(name_uuid)
        print("there are %d corps." % L)
        
        f = codecs.open(file_path, 'w', 'utf-8')
        for i in range(L-1):
            name, uuid_list = name_uuid[i]
            max_uuid = uuid_list[-1]
            uuid_list = set(uuid_list)
            
            for j in range(i+1, L):
                name2, uuid_list2 = name_uuid[j]
                if max_uuid >= uuid_list2[0]:
                    common_uuid = list(uuid_list & set(uuid_list2))
                    if common_uuid:
                        _ = [name, u"企业", role, str(len(common_uuid)), name2, ','.join(common_uuid), source]
                        f.write('\t'.join(_))
                        f.write('\n')
                        _[0], _[4] = _[4], _[0]
                        f.write('\t'.join(_))
                        f.write('\n')
                else:
                    break
            if not i % 10000:
                print("%d corps finished" % (i*10000))
        f.close()
        
        sql = sql_total_load_.format(file_path)
        self.target_cursor.execute(sql)
        self.target_conn.commit()
        os.remove(file_path)
    
    def compute_total2(self, role, source, n_line=100 * 10000):
        name_uuid, i = {}, 0
        while 1:
            sql = sql_total_get_.format(table_[source], role, i*n_line, n_line)
            self.source_cursor.execute(sql)
            res = self.source_cursor.fetchall()
            
            if not res:
                break
            print("length of res is: ", len(res))
            for name, uuid in res:
                if len(name) <= 1:
                    continue
                if name in name_uuid:
                    name_uuid[name].append(uuid)
                else:
                    name_uuid[name] = [uuid]
            i += 1
            print("line %d complete." % (i*n_line))
        
        print("name to uuid finished...")
        name_uuid = {key:(set(val), [ModHash(item) for item in val]) for key, val in name_uuid.items()}
        uuid_index, rel_set = [[] for i in range(mod_)], set([])
        f = codecs.open(file_path, 'w', 'utf-8')
        for __ in name_uuid:
            for item in name_uuid[__][1]:
                uuid_index[item].append(__)
        for ind, names in enumerate(uuid_index):
            if names:
                names = list(set(names))
                for i in range(len(names)-1):
                    for j in range(i+1, len(names)):
                        __ = ','.join(sorted([names[i], names[j]]))
                        if __ in rel_set:
                            continue
                        else:
                            _uuid = list(name_uuid[names[i]][0] & name_uuid[names[j]][0])
                            if not _uuid:
                                continue
                            rel_set.add(__)
                            s_uuid = ','.join(_uuid)
                            _ = [names[i], u"企业", role, str(len(_uuid)), names[j], s_uuid, source]
                            #print(_)
                            f.write('\t'.join(_))
                            f.write('\n')
                            _[0], _[4] = _[4], _[0]
                            f.write('\t'.join(_))
                            f.write('\n')
        f.close()
        
        sql = sql_total_load_.format(file_path)
        self.target_cursor.execute(sql)
        self.target_conn.commit()
        self.target_cursor.execute("delete from common_role_info where length(name) <= 15 or length(related_name) <= 15")
        self.target_conn.commit()
        self.target_cursor.execute("delete from common_role_info where name like '%第三人%' or related_name like '%第三人%'")
        self.target_conn.commit()
        os.remove(file_path)

            
if __name__ == '__main__':
    
    m = CommonRoleInfo()
    db1, db2 = ('10.50.87.181','super_user','pjHusHWN8sd','bigwave_api'), ('10.50.87.180', 'super_user', 'jkPsuDm2JS3', 'nono_test')
    #db2 = db1
    db1 = ('172.16.2.185','root2','123456','bigwave_api')
    m.compute_common_role('total', db1, db2, u'原告', u'开庭')
    m.compute_common_role('total', db1, db2, u'被告', u'开庭')
    m.compute_common_role('total', db1, db2, u'原告', u'文书')
    m.compute_common_role('total', db1, db2, u'被告', u'文书')
