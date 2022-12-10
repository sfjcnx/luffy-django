import json
import redis
conn = redis.Redis(host='10.0.0.210',port=6379)
# conn.delete('luffy_payment_coupon_1')
v = conn.keys()
print(v)

# 清空结算中心的所有数据
# 方式一(推荐使用,生成器节省内存空间)
# for key in conn.scan_iter('luffy_payment_1_*'):
#     print(key)
#     conn.delete(key)

# 方式二 (慎用,如果符合条件的key过多,redis一不小心就会宕机)
# key_list=conn.keys('luffy_payment_1_*')
# print(type(key_list))
# conn.delete(*key_list)











