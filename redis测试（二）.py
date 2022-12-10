


import json
import redis
from utils.redis_pool import POOL

conn = redis.Redis(host='10.0.0.210',port=6379)
"""
----> 第一版  有瑕疵且繁琐
redis={
    luffy_shopping_car:{
        6:{
            11:{
                'title':'21天入门到放弃'
                'src':'xxx.png'
            }
        }
    }
}

----> 第二版  更改数据结构,更完善
{
    luffy_shopping_car_6_11:{
        'title':'21天入门到放弃',
        'src':'xxx.png'
    },
     luffy_shopping_car_6_12:{
        'title':'22天入门到放弃',
        'src':'xxx.png'
    },
}

"""
# conn.flushall()

# 把商品添加到购物车
# redis_key="luffy_shopping_car_%s_%s"%(6,12)
# conn.hmset(redis_key,{'title':'21天入门到放弃','src':'xxx.png'})

# 删除商品
# conn.delete("luffy_shopping_car_6_12")
# print(conn.keys())
# 修改购物车中的课程
# conn.hset("luffy_shopping_car_6_11",'src','x1.png')
# print(conn.hget("luffy_shopping_car_6_11",'src'))

# 查看指定用户购物车的所有商品
# print(conn.keys())  # 默认不填,就是redis大字典中的所有的key
# print(conn.keys("luffy_shopping_car_6_*"))   # keys还支持模糊查询

# 取出用户ID为6的购物车下所有商品 , 如果'购物车'中的商品过多,可以用scan_iter先做成生成器,然后遍历取值,也不会占用过多的内存空间
# for item in conn.scan_iter("luffy_shopping_car_6_*",count=100):
#     course=conn.hgetall(item)
#     print(course)


# print(conn.keys())
#
# conn.hgetall('luffy_shopping_car_1_1')

# for key in conn.scan_iter('luffy_shopping_car_1_*'):
#     title=conn.hget(key,'title')
#     img = conn.hget(key, 'img')
#     default_policy = conn.hget(key, 'default_policy')
#     policy = conn.hget(key, 'policy')
#
#     print(str(title,encoding='utf-8'))
#     print(str(img,encoding='utf-8'))
#     print(str(default_policy,encoding='utf-8'))
#     print(json.loads(str(policy,encoding='utf-8')))

print(conn.keys())

print(conn.exists('luffy_shopping_car_1_2'))   # exists判断()中的key是否存在于redis中


