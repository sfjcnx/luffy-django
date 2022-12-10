
# _*_ coding: utf-8 _*_

"""
创建时间: 2022/6/24
版本号: v1
文档名: account.py
编辑人: alex
用途: 用户登录控制
源存储位置:  api\views\account.py
修改及增加功能记录:
    修改时间:
        1.
        2.
    增加功能时间:
导入模块的先后顺序有讲究:
    内置模块
    第三方模块
    自己写的模块
"""

import uuid

from rest_framework.views import APIView
from rest_framework.response import Response

from api.models import *
from utils.response import TokenResponse


# 方案一. 按照逻辑一板一眼的垒代码
# class LoginView(APIView):
#     """
#     用于用户认证相关接口
#     """
#     def post(self,request,*args,**kwargs):
#         ret={"code":1000}
#         try:
#             username = request.data.get('user')
#             pwd = request.data.get('pwd')
#             user = Account.objects.get(username=username,password=pwd)
#             if not user:
#                 ret['code']=1001
#                 ret['error']='用户名或密码不存在'
#             else:
#                 uid=str(uuid.uuid4())
#                 UserAuthToken.objects.update_or_create(user=user,defaults={'token':uid})
#                 ret['token']=uid
#         except Exception as e:
#             ret['code']=1003
#             ret['error']= '获取信息失败'
#         return Response(ret)


# 方案二 把经常要写的 [ code, data, error ]  封装到类中,方便调用


class LoginView(APIView):

    def post(self,request,*args,**kwargs):
        '''
        用户认证
        :param request: 请求相关的传参
        :param args: URL传参
        :param kwargs: URL关键字传参
        :return:
        '''
        ret=TokenResponse()
        try:
            user=request.data.get('user')
            pwd=request.data.get('pwd')
            user_obj=Account.objects.get(username=user,password=pwd)
            if not user:
                ret.code=1001,
                ret.error="用户名或者密码错误"
            uid=str(uuid.uuid4())
            UserAuthToken.objects.update_or_create(user_obj,defaults={'token':uid})
            ret.token=uid
        except Exception as e:
            ret.code=1003
            ret.error='获取信息失败,请稍后再试'
        return Response(ret.dict)    # ret是一个对象,但是对象是不能被序列化的,ret.dict是一个字典