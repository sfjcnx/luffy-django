import redis

#创建连接池
POOL=redis.ConnectionPool(host='10.0.0.210',port=6379,max_connections=1000)

"""
利用redis的特性, 提升效率
在模块中创建连接池,形成单例模式,所有程序都可以过来连接.
使用的时候直接导入即可,不需要多次创建连接池,造成资源浪费
"""