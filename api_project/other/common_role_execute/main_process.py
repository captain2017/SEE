# -*- coding: utf-8 -*-

# 共同利益人主流程

import pymysql as pm
import os, requests

url = 'http://172.16.2.199:34100/v1/job/update'
with open('uuid.txt', 'r') as f:
    uuid = f.readlines()[-1].strip()

path = os.popen('pwd').read().strip() + '/'
success = 1

db_180 = ('10.50.87.180', 'super_user', 'jkPsuDm2JS3', 'nono_test')
db_181 = ('172.16.2.185','root2','123456','bigwave_api') #('10.50.87.181','super_user','pjHusHWN8sd','bigwave_api')


# 清空 common_role_info 表
a, b, c, d = db_180
conn = pm.connect(host=a, user=b, passwd=c, db=d, charset='utf8')
cursor = conn.cursor()

cursor.execute("truncate table common_role_info")
conn.commit()
conn.close()


# 执行 common_role_info.py 生成新的common_role_info 表
res = os.system("python {}common_role_info.py".format(path))
success = 0 if res != 0 or success == 0 else 1

if not success:
    data = '{"uuid":"%s","success":%d}' % (uuid,0)
    print(data)
    s = requests.post(url, data=data.encode('utf-8'), headers={"Content-Type":"application/json"}).text
    print(s)
    quit()

# 创建 common_interest_copy 表
a, b, c, d = db_181
conn = pm.connect(host=a, user=b, passwd=c, db=d, charset='utf8')
cursor = conn.cursor()

sql = """
CREATE TABLE `common_interest_copy` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `name` varchar(150) NOT NULL DEFAULT '' COMMENT '主体名',
  `type` varchar(16) NOT NULL DEFAULT '' COMMENT '类型：个人或企业',
  `total` int(11) NOT NULL DEFAULT '-1' COMMENT '总数：所有amount的和',
  `related_name` varchar(150) NOT NULL DEFAULT '' COMMENT '关联方名称',
  `role` varchar(16) NOT NULL DEFAULT '' COMMENT '角色：原告或被告',
  `court_amount` int(11) NOT NULL DEFAULT '-1' COMMENT '开庭数',
  `court_uuid_list` text NOT NULL COMMENT '开庭uuid列表',
  `doc_amount` int(11) NOT NULL DEFAULT '-1' COMMENT '文书数',
  `doc_uuid_list` text NOT NULL COMMENT '文书uuid列表',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=10148456 DEFAULT CHARSET=utf8;

"""

cursor.execute(sql)
conn.commit()

# 执行 generate_final_table.py 生成 common_interest_copy 表
res = os.system("python {}common_interest.py".format(path))
success = 0 if res != 0 or success == 0 else success

if not success:
    data = '{"uuid":"%s","success":%d}' % (uuid,0)
    print(data)
    s = requests.post(url, data=data.encode('utf-8'), headers={"Content-Type":"application/json"}).text
    print(s)
    quit()

# 删除 common_interest 表 并修改 common_interest_copy 为 common_interest
try:
    cursor.execute("drop table common_interest")
    conn.commit()
except:
    pass
finally:
    cursor.execute("alter table common_interest_copy rename common_interest")
    conn.commit()

conn.close()

# 发送结束请求
data = '{"uuid":"%s","success":%d}' % (uuid,success)
print(data)
s = requests.post(url, data=data.encode('utf-8'), headers={"Content-Type":"application/json"}).text
print(s)

