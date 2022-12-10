


class PricePolicyInvalid(Exception):
    """
    注意自己写的类, 要继承自Exception
    创建一个捕捉异常的类,
    用于捕捉用户传过来的价格策略id是否存在,如果不存在则报错
    """
    def __init__(self,msg):
        self.msg = msg