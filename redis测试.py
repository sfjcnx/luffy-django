import redis
import json
from utils.redis_pool import POOL


conn=redis.Redis(connection_pool=POOL)
# conn.flushall()         # 清空Redis大字典里的所有键值对
# v=conn.keys()           # 查看Redis大字典中的所有键
# print(v)

"""
# 用户ID: 6
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

"""

# 添加到购物车中的第一个商品
# data_dict = {
#     11:{
#         'title':'21天从入门到放弃',
#         'src':'xxx.png'
#     }
# }
# conn.hset('luffy_shopping_car','6',json.dumps(data_dict))

"""
在添加第二件商品的时候,要注意
    因为redis内中的第一层具有数据结构,其他的都只能作为字符串存储,
    如果想在data_dict中添加第二条数据,则需要把data_dict从redis中拿出来
    又因为字符串在redis中是以字节的形式存储的,首先要把bytes的形式存储的,所以要先转换成字符串
    拿到字符串后,需要用json转换成字典进行操作.把第二个商品添加到data_dict中
    最后把拿到的字典转成字符串,传到redis中存储
    json天生就可以把bytes类型转换成字典
"""

# 把第二件商品添加到购物车
# car = conn.hget('luffy_shopping_car','6')
# car_str = car.decode('utf-8')
# car_dict=json.loads(car_str)
# car_dict2=json.loads(car)
# print(type(car_dict))
# print(type(car_dict2))


# 把第二件商品添加到购物车
car=conn.hget('luffy_shopping_car','6')
car_str=str(car,encoding='utf-8')
car_dict=json.loads(car_str)
# print(car_dict)
car_dict[12]={
    'title':'22天入门到放弃',
    'src':'cddd.png'
}
conn.hset('luffy_shopping_car','6',json.dumps(car_dict))
print(car_dict)




### decode 和 encode傻傻分不清楚怎么办?
# car_str=str(car,encoding='utf-8')    # 要什么类型的数据就直接强转,但还是不能够从bytes直接转到dict,中间的序列化还是不能少
# print(car_str)
# car_bytes=bytes(car_str,encoding='utf-8')
# print(car_bytes)





