import json
import datetime

from rest_framework.views import APIView
from rest_framework.response import Response
from utils.auth import LuffyAuth
from utils.response import BaseResponse
from django.conf import settings
from django_redis import get_redis_connection
from api import models


class PaymentViewSet(APIView):
    authentication_classes = [LuffyAuth,]
    conn = get_redis_connection('default')

    def post(self,request,*args,**kwargs):
        """
        解题思路:
            参数: 用户要结算的所有课程id
            1, 根据课程ID去redis中获取相应的课程(含价格)
            2, 获取优惠券(获取当前用户可用的所有优惠券)
                - 未使用
                - 有效期范围之内,      有效期开始时间<当前时间<有效期结束时间
        伪代码:
            从请求中获取所有的课程id,循环所有的课程id,拼接出购物车的key,校验如果缓存中没有拼接出的key,则提示让其先加入购物车



        """
        ret = BaseResponse()
        try:
            # 用户每次进入都要保证结算中心是清空的.删除 luffy_payment_coupon_1 和 luffy_payment_1_*
            key_list = self.conn.keys(settings.PAYMENT_KEY%(request.auth.user_id,'*',))
            key_list.append(settings.PAYMENT_COUPON_KEY%(request.auth.user_id,))   # 不管什么课程,都可以使用的优惠券
            self.conn.delete(*key_list)

            payment_dict={}
            global_coupon_dict={
                'coupon':{},
                'default_coupon':0,
            }
            # 1, 获取用户要结算的课程id
            course_id_list = request.data.get('courseids')
            for course_id in course_id_list:
                car_key=settings.SHOPPING_CAR_KEY%(request.auth.user_id,course_id)  #根据key去购物车中获取需要的数据(如:title,img,default_policy所选中的价格策略详情)
                # 1.1 检查用户要结算的课程是否已经加入购物车
                if not self.conn.exists(car_key):
                    ret.code = 1001
                    ret.error = "课程需要先加入购物车,方可结算"
                # 1.2 从购物车中获取信息,放到结算中心
                policy = json.loads(self.conn.hget(car_key, 'policy').decode('utf-8'))  # 获取此课程的所有价格策略
                default_policy = self.conn.hget(car_key, 'default_policy').decode('utf-8') # 用户选中(默认)的价格策略id
                policy_info = policy[default_policy] # 获取用户选中的价格策略信息
                payment_course_dict={
                    "course_id":str(course_id),
                    "title": self.conn.hget(car_key,'title').decode('utf-8'),
                    "img": self.conn.hget(car_key,'img').decode('utf-8'),
                    "policy_id":str(default_policy),
                    "coupon":{},
                    'default_coupon': 0,
                }
                payment_course_dict.update(policy_info)  # 把字典policy_info 合并到payment_course-dict
                # 1.3  装
                payment_dict[str(course_id)]=payment_course_dict

            # 2, 获取优惠券
            ctime=datetime.date.today()
            # 所有可用的优惠券: 全局的,专属课程的(含其他课程-未加入结算中心)   ---(满减券,折扣券,立减券)
            coupon_list=models.CouponRecord.objects.filter(
                account=request.auth.user,
                status=0,
                coupon__valid_begin_date__lte=ctime,
                coupon__valid_end_date__gte=ctime
            )
            for item in coupon_list:
                info={} # 单个优惠券的折扣信息: 优惠券类型,优惠券金额,符合折扣的条件
                # print(item.id, item.number, item.coupon.get_coupon_type_display(), item.coupon.coupon_type,
                #       item.coupon.object_id, )    # 3 56yufg8yui-fdg345 满减券 1 None
                # 先处理绑定课程的优惠券
                if not item.coupon.object_id:  # 未绑定课程的全局优惠券
                    coupon_id = item.id  # 获取优惠券id
                    coupon_type=item.coupon.coupon_type  # 获取优惠券类型

                    info["coupon_type"]=coupon_type  # 优惠券类型id
                    info['coupon_type_display']=item.coupon.get_coupon_type_display() # 优惠券类型名称
                    if coupon_type == 0:  # 立减券
                        info['money_equivalent_value'] = item.coupon.money_equivalent_value  # 等值获取
                    elif coupon_type == 1: # 满减券
                        info['money_equivalent_value'] = item.coupon.money_equivalent_value
                        info['minimum_consume'] = item.coupon.minimum_consume  # 最低消费
                    else: # 折扣券
                        info['off_percent'] = item.coupon.off_percent
                    global_coupon_dict['coupon'][coupon_id]=info   # 全局的多个优惠券,单独放起来,默认一个都不选

                # 优惠券绑定的 课程id
                coupon_course_id = str(item.coupon.object_id)
                # 优惠券 id
                coupon_id = item.id
                # 优惠券类型: 满减, 折扣, 立减
                coupon_type=item.coupon.coupon_type
                info['coupon_type'] = coupon_type
                info['coupon_type_display']=item.coupon.get_coupon_type_display()
                if coupon_type == 0: # 立减券
                    info['money_equivalent_value']=item.coupon.money_equivalent_value # 抵扣金额
                elif coupon_type ==1: # 满减券
                    info['money_equivalent_value']=item.coupon.money_equivalent_value
                    info['minimum_consume']=item.coupon.minimum_consume # 最低消费
                else:   # 折扣券
                    info['off_percent'] = item.coupon.off_percent  # 折扣力度

                if coupon_course_id not in payment_dict:
                    continue # 其余的没有用上的优惠券课程专属优惠券 略过
                # 将优惠券设置到指定的课程字典中
                payment_dict[coupon_course_id]['coupon'][coupon_id]=info
            # 3, 将绑定课程优惠券 + 全站优惠券, 写入redis中(结算中心)
            # 3.1 绑定优惠券的课程放到redis
            for cid,cinfo in payment_dict.items():
                pay_key = settings.PAYMENT_KEY %(request.auth.user_id,cid)
                cinfo['coupon']=json.dumps(cinfo['coupon'])
                self.conn.hmset(pay_key,cinfo)    # 绑定课程的信息放到redis

            # 3.2 将全局的优惠券写入redis   luffy_payment_coupon_1
            gcoupon_key= settings.PAYMENT_COUPON_KEY%(request.auth.user_id,)
            global_coupon_dict['coupon'] = json.dumps(global_coupon_dict['coupon'])
            self.conn.hmset(gcoupon_key,global_coupon_dict)

        except Exception as e:
            ret.code = 1009
            ret.error = "添加失败"
        return Response(ret.dict)

    def patch(self,request,*args,**kwargs):
        # 1, 用户提交要修改的优惠券
        ret = BaseResponse()
        try:
            course = request.data.get('courseid')  # 从请求体中获取课程id
            course_id = str(course) if course else course  # 无法确定课程id是否存在,稍后需要判断
            coupon_id = str(request.data.get('couponid'))  # 获取前端传过来的优惠券id
            redis_global_coupon_dict = settings.PAYMENT_COUPON_KEY%(request.auth.user_id,)  # 获取全局优惠券的key
            # 如果用户修改的是全局优惠券
            if not course_id:
                # 获取所有可用的全局优惠券
                coupon_dict=json.loads(self.conn.hget(redis_global_coupon_dict,'coupon').decode('utf-8'))
                if coupon_id == "0":
                    # 不使用优惠券  请求数据: {'couponid':0}
                    self.conn.hset(redis_global_coupon_dict,'default_coupon',coupon_id)
                    ret.data="修改成功"
                    return Response(ret.dict)
                # 使用优惠券. 请求数据: {'couponid':2}
                # 判断用户选择的优惠券是否合法
                if coupon_id not in coupon_dict:
                    ret.code = 1001
                    ret.error = "全站优惠券不存在"
                    return Response(ret.dict)
                # 选择的优惠券合法
                self.conn.hset(redis_global_coupon_dict,"default_coupon",coupon_id)  # 将默认的优惠券id改成用户指定的
                ret.data = '修改成功'
                return Response(ret.dict)

            # 修改指定课程的优惠券
            #  luffy_payment_1_1
            redis_payment_key = settings.PAYMENT_KEY%(request.auth.user_id,course_id)
            # 不使用优惠券
            if coupon_id == 0:
                self.conn.hset(redis_payment_key,'default_coupon',coupon_id)
                ret.data="修改成功"
                return Response(ret.dict)
            # 使用优惠券
            coupon_dict = json.loads(self.conn.hget(redis_payment_key,'coupon').decode("utf-8"))
            if coupon_id not in coupon_dict:
                ret.code = 1010,
                ret.error = "此课程专属优惠券不存在",
                return Response(ret.dict)
            self.conn.hset(redis_payment_key,'default_coupon',coupon_id)

        except Exception as e:
            ret.code=1111,
            ret.error = '修改失败'

        return Response(ret.dict)

    def get(self,request,*args,**kwargs):
        ret=BaseResponse()
        try:
            # 去redis中获取到数据,并返回给前端
            # "luffy_payment_1_*"
            redis_payment_key = settings.PAYMENT_KEY%(request.auth.user_id,'*')
            # "luffy_payment_coupon_1"
            redis_global_key = settings.PAYMENT_COUPON_KEY%(request.auth.user_id,)

            # 1. 获取绑定课程信息
            course_list = []     # [{},{}]
            for key in self.conn.scan_iter(redis_payment_key):
                info = {}  # 单个课程的结算信息,包含课程id,课程名称,图片,周期,与课程绑定的优惠券
                data = self.conn.hgetall(key)  # 将课程的所有信息从缓存中拿出来,需bytes转成字符串,个别需要反序列化
                for k,v in data.items():
                    kk = k.decode('utf-8')
                    if kk == "coupon":
                        info[kk] = json.loads(v.decode('utf-8'))
                    else:
                        info[kk]=v.decode('utf-8')
                course_list.append(info)  # 将每个课程的信息从缓存中拿出后放在列表中
            # 2. 全站优惠券
            global_coupon_dict = {
                'coupon': json.loads(self.conn.hget(redis_global_key,'coupon').decode('utf-8')),
                'default_coupon':self.conn.hget(redis_global_key,'default_coupon').decode('utf-8')
            }
            ret.data={
                "course_list":course_list,
                "global_coupon_dict":global_coupon_dict
            }
        except Exception as e:
            ret.code=1001
            ret.error = '获取失败'
        return Response(ret.dict)












