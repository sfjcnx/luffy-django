import json
from rest_framework.views import APIView
from rest_framework.viewsets import GenericViewSet, ViewSetMixin
from rest_framework.response import Response
from django_redis import get_redis_connection
from utils.response import BaseResponse
from utils.auth import LuffyAuth
from api import models
from django.core.exceptions import ObjectDoesNotExist
from utils.exception import PricePolicyInvalid
from django.conf import settings      # django中内置的setting,+ 我们自己添加的


class ShoppingCarViewSet(APIView):
    conn=get_redis_connection('default')  # 类下的全局,下面用加self
    # authentication_classes = [LuffyAuth,]

    def post(self,request,*args,**kwargs):
        ret = BaseResponse()
        try:
            # 1.获取用户提交的课程ID 和价格策略ID
            course_id=int(request.data.get('courseid'))  # 你永远不知道用户传过来的值是什么类型的,只能把它转成自己想要的
            policy_id=int(request.data.get('policyid'))
            # 2 获取专题课信息
            course=models.Course.objects.get(id=course_id)
            # 3 获取该课程相关的所有价格策略
            price_policy_list=course.price_policy.all()
            price_policy_dict={}
            for item in price_policy_list:
                price_policy_dict[item.id]={
                    "period":item.valid_period,
                    'period_display':item.get_valid_period_display(),
                    "price":item.price,
                }

            # print(price_policy_dict)
                # print(item.id)                          # 拿每个价格策略的id
                # print(item.valid_period)                # 数字形式的周期
                # print(item.get_valid_period_display())  # 文字形式的周期
                # print(item.price)                       # 每个周期对应多少钱
            # 4 判断用户提交的价格策略是否合法
            if policy_id not in price_policy_dict:
                # 价格策略不合法
                raise PricePolicyInvalid('价格策略不合法')
            # 5, 将购物信息添加到redis中
            # conn =get_redis_connection('default')
            car_key=settings.SHOPPING_CAR_KEY%(request.auth.user_id,course_id,)
            car_dict = {
                'title':course.name,
                'img':course.course_img,
                'default_policy':policy_id,
                'policy': json.dumps(price_policy_dict)
            }
            self.conn.hmset(car_key,car_dict)
            ret.data='添加成功'

        except PricePolicyInvalid as e:
            ret.code=2001
            ret.error=e.msg

        except ObjectDoesNotExist as e:
            ret.code = 2001
            ret.error = '课程不存在'
        except Exception as e:
            ret.code = 1001,
            ret.error='添加购物车失败,稍后重试'
        return Response(ret.dict)

    def delete(self,request,*args,**kwargs):
        """
        购物车中删除课程,有可能是一个,也有可能是多个,所以即使只有一个值,前端也需要传进来一个列表过来,
        :param request:
        :param args:
        :param kwargs:
        :return:
        """
        ret=BaseResponse()
        try:
            course_id_list=request.data.get('courseids')
            key_list=[ settings.SHOPPING_CAR_KEY%(request.auth.user_id,course_id) for course_id in course_id_list]
            self.conn.delete(*key_list)
        except Exception as e:
            ret.code=1001
            ret.error='删除失败,请稍后再试'
        return Response(ret.dict)

    def patch(self,request,*args,**kwargs):
        """
        修改课程的价格策略
        :param request:
        :param args:
        :param kwargs:
        :return:
        """
        ret = BaseResponse()
        try:
            # 1. 获取课程ID和价格策略ID
            course_id=str(request.data.get('courseid'))
            policy_id =str(request.data.get('policyid'))

            # 2. 拼接课程的key
            key = settings.SHOPPING_CAR_KEY%(request.auth.user_id,course_id)

            # 检查传过来的课程是否存在
            if not self.conn.exists(key):
                ret.code=1001
                ret.error= "购物车中不存在此课程"
                return Response(ret.dict)
            # 3. 在redis中获取所有的价格策略
            policy_dict = json.loads(str(self.conn.hget(key,'policy'),encoding='utf-8'))
            if policy_id not in policy_dict:
                ret.code=1002
                ret.error="价格策略不合法"
                return Response(ret.dict)
            # 4, 在购物车中修改该课程默认的价格策略
            self.conn.hset(key,'default_policy',policy_id)
            ret.data='修改成功'
        except Exception as e:
            ret.code=1004
            ret.error='修改失败'

        return Response(ret.dict)

    def get(self,request,*args,**kwargs):
        """
        查看购物车中的所有商品
        :param request:
        :param args:
        :param kwargs:
        :return:
        """
        ret=BaseResponse()
        try:
            key_match=settings.SHOPPING_CAR_KEY%(request.auth.user_id,"*")

            course_list = []
            for key in self.conn.keys(key_match):
                info_tuple={
                    'title':self.conn.hget(key,'title').decode('utf-8'),
                    'img':self.conn.hget(key,'img').decode('utf-8'),
                    'policy':json.loads(self.conn.hget(key,'policy').decode('utf-8')),
                    'default_policy':self.conn.hget(key,'default_policy').decode('utf-8')
                },
                for i in info_tuple:
                    course_list.append(i)
            ret.data=course_list
        except Exception as e:
            ret.code=1003
            ret.error="获取信息失败"
        return Response(ret.dict)


"""
购物车的存储格式(redis中的数据):
{
    shopping_car_1_2:{
        "title":"CRM客户关系管理系统开发实战--专题",
        "img": "CRM.jpg",
        "policy":{
            4:{
                "period":210,
                "period_dieplay":"12个月",
                "price":122
            }
        },
        "default_policy":4
    },
    shopping_car_1_1:{
        "title":"爬虫开发-专题",
        "policy":{
            "1":{
                "period":30,
                "period_display":"1个月",
                "price":399
            },
            "2":{
                "period":60,
                "period_display":"两个月",
                "price":599
            },
            "3":{
                "period":180,
                "period_display":"六个月",
                "price":799
            }
        },
        "default_policy":"2"
    }
}

"""













