import json
import datetime
import time
from django.db.models import F
from django.db import transaction
from rest_framework.views import APIView
from rest_framework.response import Response
from django.shortcuts import redirect
from utils.auth import LuffyAuth
import random
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist,RequestAborted
from django_redis import get_redis_connection
from api import models
from api.views.pay_after import alipay

def generate_order_num():
    """
    生成订单编号, 且必须唯一
    :return:
    """
    while True:
        order_num = time.strftime('%Y%m%d%H%M%S', time.localtime()) + str(random.randint(111, 999))
        if not models.Order.objects.filter(order_number=order_num).exists():
            break
    return order_num


def generate_transaction_num():
    """
    生成流水编号, 且必须唯一
    :return:
    """
    while True:
        transaction_number = time.strftime('%Y%m%d%H%M%S', time.localtime()) + str(random.randint(111, 999))
        if not models.TransactionRecord.objects.filter(transaction_number=transaction_number).exists():
            break
    return transaction_number

class OrderViewSet(APIView):
    authentication_classes = [LuffyAuth, ]
    conn = get_redis_connection('default')
    def post(self,request,*args,**kwargs):
        """
        去支付
        :param request:
        :param args:
        :param kwargs:
        :return:
        1, 获取用户提交数据
                {
                    balance : 1000, 贝里抵扣
                    money : 900     最终支付金额
                }
            balance = request.data.get("balance")
            money = request.data.get("money")
        2, 数据验证
            - balance和money大于等于0
            - 个人账户的贝里余额是否大于等于1000贝里
            if user.auth.user.balance < balance:
                抛异常--> 账户贝里余额不足
        优惠券ID_list = [1,3,5]
        3, 去结算中心处理课程信息  # 目的: 计算出总价和划线价格
            for course_dict in redis的结算中心获取:
                - 获取课程ID
                - 根据course_id去数据库中检查,此课程的状态

                - 获取价格策略 course_dict[policy_id]
                - 根据policy_id 去数据库检查,此价格策略的状态

                - 获取用户使用的优惠券ID course_dict['default_coupon']
                - 根据优惠券ID检查优惠券是否过期

                - 获取原价 + 获取优惠券类型
                    - 立减 :
                        判断: 优惠券金额>原价: 折后价=0
                        else:
                            划线价格 = 原价 - 优惠券金额
                    - 满减: 是否满足限制条件
                        划线价格  = 原价 - 优惠券金额
                    - 折扣:
                        划线价格  = 原价*80/100
        4. 全栈优惠券
            - 去数据库校验全站优惠券的合法性
            - 应用优惠券
                - 立减:
                    0 = 划线价格  - 优惠券金额  # 优惠券金额 > 实际支付金额
                    或
                    折后金额 = 划线价格  - 优惠券金额
                - 满减: 是否满足限制
                    折后价格 = 划线价格  - 优惠劵金额
                - 折扣:
                    折后金额 = 划线价格 *80/100
             --->实际支付金额
        5, 贝里抵扣
        6, 总金额的校验
              实际支付 - 贝里 == money     # money是前端传过来的最终需要支付的金额
        7, 为当前课程生成订单
            - 事务: 要成功都成功,要失败都失败, 数据库操作放在最后做统一做事务.这样就不会出现乱扣费的情况
                - 订单创建一条数据 Order  # Order表和OrderDetail表是一对多的关系,OrderDetail表存放的是一个订单中的每一个商品的详细信息
                    - 订单详细表创建一条数据 OrderDetail       EnrolledCourse
                    - 订单详细表创建一条数据 OrderDetail       EnrolledCourse
                    - 订单详细表创建一条数据 OrderDetail       EnrolledCourse

                - 如果有贝里支付
                    - 贝里金额扣除    account
                    - 交易记录      TransactionRecode
                - 优惠券状态更新   CouponRecord

                注意:
                    如果支付宝支付金额0,表示订单状态: 已支付
                    如果支付宝支付金额110, 表示订单状态: 未支付
                        - 生成url(含订单号)
                        - 回调函数: 更新订单状态
        """
        userd_coupon_list = []
        current_time = datetime.datetime.now()

        # 1. 获取用户提交的数据
        balance = int(request.data.get("balance"))
        money = int(request.data.get("money"))
        # 2, 数据验证
        if balance<0 and money<0:
            raise RequestAborted("支付金额不合法")
        if request.auth.user.balance < balance:
            raise RequestAborted("贝里账户余额不足")
        # 3, 去结算中心处理课程信息
        payment_keys =settings.PAYMENT_KEY%(request.auth.user_id,'*')
        # 3.1. 获取绑定课程信息
        course_list = []  # [{},{}]
        for key in self.conn.scan_iter(payment_keys):
            info = {}
            data = self.conn.hgetall(key)
            for k, v in data.items():
                kk = k.decode('utf-8')
                if kk == "coupon":
                    info[kk] = json.loads(v.decode('utf-8'))
                else:
                    info[kk] = v.decode('utf-8')
            course_list.append(info)
        # 3.2 处理课程信息
        origin_price_list = []
        line_price_list = []
        ctime = time.time()
        for course_dict in course_list:
            course_obj = models.Course.objects.filter(id=course_dict["cid"]).first()
            course_status = course_obj.status
            if course_status != 0:
                raise ObjectDoesNotExist("课程不存在或已下线")
            if course_dict["policy_id"] not in course_obj.price_policy.all():
                raise ObjectDoesNotExist("价格策略不存在或已下线")
            valid_begin_date=models.CouponRecord.objects.filter(id=course_dict['default_coupon']).first().coupon.valid_begin_date
            valid_end_date = models.CouponRecord.objects.filter(id=course_dict['default_coupon']).first().coupon.valid_end_date
            valid_begin_date = get_time(valid_begin_date)
            valid_end_date = get_time(valid_end_date)
            if valid_begin_date>ctime and valid_end_date<ctime:
                raise  ObjectDoesNotExist("优惠券已过期")
            origin_price = int(course_dict['price'])
            line__price = None
            coupon_type = course_dict['coupon']["default_coupon"]['coupon_type']
            if coupon_type == 0:
                coupon_price = course_dict['coupon']["default_coupon"]['money_equivalent_value']
                if origin_price - int(coupon_price) <=0:
                    line__price = 0
                else:
                    line__price = origin_price - int(coupon_price)
            if coupon_type == 1:
                coupon_price = course_dict['coupon']["default_coupon"]['money_equivalent_value']
                minimum_consume = course_dict['coupon']["default_coupon"]['minimum_consume']
                if origin_price >= minimum_consume:
                    line__price = origin_price - int(coupon_price)
            if coupon_type == 2:
                off_percent = course_dict['coupon']["default_coupon"]['off_percent']
                line__price = origin_price*int(off_percent)
            origin_price_list.append(origin_price)
            line_price_list.append(line__price)
            userd_coupon_list.append(course_dict['default_coupon'])
        _origin_price_sum = 0
        for i in origin_price_list:
            _origin_price_sum+=i
        _line_price_sum = 0
        for i in line_price_list:
            _line_price_sum += i
        # 4 全栈优惠券
        actual_pay = None
        redis_global_key = settings.PAYMENT_COUPON_KEY%(request.auth.user_id,)
        global_coupon_dict = {
            'coupon': json.loads(self.conn.hget(redis_global_key, 'coupon').decode('utf-8')),
            'default_coupon': self.conn.hget(redis_global_key, 'default_coupon').decode('utf-8')
        }
        global_begin_date=models.CouponRecord.objects.filter(id=global_coupon_dict['default_coupon']).filter().coupon.valid_begin_date
        global_end_date=models.CouponRecord.objects.filter(id=global_coupon_dict['default_coupon']).filter().coupon.valid_end_date
        global_begin_date = get_time(global_begin_date)
        global_end_date = get_time( global_end_date)
        if global_begin_date > ctime and global_end_date < ctime:
            raise ObjectDoesNotExist("优惠券已过期,不可用")
        coupon_type = global_coupon_dict['coupon']["default_coupon"]['coupon_type']
        if coupon_type == 0:
            coupon_price = global_coupon_dict['coupon']["default_coupon"]['money_equivalent_value']
            if _line_price_sum - int(coupon_price) <= 0:
                actual_pay = 0
            else:
                actual_pay = _line_price_sum - int(coupon_price)
        if coupon_type == 1:
            coupon_price = global_coupon_dict['coupon']["default_coupon"]['money_equivalent_value']
            minimum_consume = global_coupon_dict['coupon']["default_coupon"]['minimum_consume']
            if _line_price_sum >= minimum_consume:
                actual_pay = _line_price_sum- int(coupon_price)
        if coupon_type == 2:
            off_percent = global_coupon_dict['coupon']["default_coupon"]['off_percent']
            actual_pay = _line_price_sum * int(off_percent)
        userd_coupon_list.append(global_coupon_dict['default_coupon'])
        # 5,贝里抵扣
        if balance:
            actual_pay -= balance/100
        # 6,总金额的校验
        if money+balance/100 != actual_pay:
            raise Exception('总价、优惠券抵扣、贝里抵扣和实际支付的金额不符')
        # 7, 为当前课程生成订单
        with transaction.atomic():
            if actual_pay - balance/100 == 0:
                order_object = models.Order.objects.create(
                    payment_type=3,
                    order_number=generate_order_num(),
                    account=request.user,
                    actual_amount=0,
                    status=0,  # 支付成功，优惠券和贝里已够支付
                    pay_time=current_time
                )
            else:           # 创建订单
                order_object = models.Order.objects.create(
                    payment_type=1,
                    order_number=generate_order_num(),
                    account=request.user,
                    actual_amount=actual_pay,
                    status=1,  # 待支付
                    pay_time=current_time,

                )
            for item in course_list:   # 创建订单详情
                order_detail = models.OrderDetail.objects.create(
                    order=order_object,
                    content_object = models.Course.objects.get(id=item['cid']),
                    original_price = item['price'],
                    price= line_price_list.pop(0),
                    valid_period_display = item['valid_period_display'],
                    valid_period = item['valid_period']
                )
            models.Account.objects.filter(id=request.auth.user_id).update(balance=F(balance)-balance)  # 贝里扣除
            models.TransactionRecord.objects.create( # 生成贝里交易记录
                account=request.auth.user,
                amount=balance,
                balance = request.auth.user.balance-balance,
                transaction_number=1,
                content_object=order_object,
                # transaction_number=generate_transaction_num()
            )
            models.CouponRecord.objects.filter(account=request.auth.user_id,id___in=userd_coupon_list).update(
                status=1,
                used_time=current_time
            )
            if order_object.payment_type == 1:

                query_params = alipay.direct_pay(
                    subject='路飞学城',  # 商品简单描述
                    out_trade_no=order_object.order_number,  # 商户订单号
                    total_amount=order_object.actual_amount,  # 交易金额(单位: 元 保留俩位小数)
                )
        pay_url = "https://openapi.alipaydev.com/gateway.do?{0}".format(query_params)
        return redirect(pay_url)

import time
def get_time(a1):
    # 先转换为时间数组
    timeArray = time.strptime(a1, "%Y-%m-%d %H:%M:%S")

    # 转换为时间戳
    timeStamp = int(time.mktime(timeArray))
    return timeStamp



