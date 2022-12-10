



"""
总是写 {"code":1000,"data":None,"error":None}
比较烦,可以把经常出现的有规律的东西封装到类中
"""


class BaseResponse(object):
    def __init__(self):
        self.data=None
        self.code=1000
        self.error=None

    @property
    def dict(self):
        return self.__dict__


class TokenResponse(BaseResponse):

    def __init__(self):
        self.token = None
        super(TokenResponse, self).__init__()  # 继承父类的init方法,并派生出自己新的token字段

