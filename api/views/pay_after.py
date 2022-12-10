from django.shortcuts import render, HttpResponse, redirect
from api import models
import uuid
from utils.alipay import AliPay  # 导入sdk

alipay = AliPay(appid=2021000120606070,
                app_notify_url="http://127.0.0.1:8000/check_order/",  # POST,发送支付状态信息
                return_url="http://127.0.0.1:8000/show/",  # GET,将用户浏览器地址重定向回原网站
                app_private_key_path="keys/app_private_2048.txt",
                alipay_public_key_path="keys/alipay_public_2048.txt",
                debug=True,  # 默认True测试环境、False正式环境
                )

def check_order(request):
    """
    POST请求，支付宝通知支付信息，我们修改订单状态
    :param request:
    :return:
    """
    if request.method == 'POST':

        from urllib.parse import parse_qs
        body_str = request.body.decode('utf-8')
        post_data = parse_qs(body_str)

        post_dict = {}
        for k, v in post_data.items():
            post_dict[k] = v[0]
        sign = post_dict.pop('sign', None)
        status = alipay.verify(post_dict, sign)
        if status:
            # 支付成功，获取订单号将订单状态更新
            out_trade_no = post_dict['out_trade_no']
            models.Order.objects.filter(order_number=out_trade_no).update(status=0)
            return HttpResponse('success')
        else:
            return HttpResponse('支持失败')
    else:
        return HttpResponse('只支持POST请求')


def show(request):
    """
    回到我们页面
    :param request:
    :return:
    """
    if request.method == "GET":
        params = request.GET.dict()
        sign = params.pop('sign', None)
        status = alipay.verify(params, sign)
        if status:
            return HttpResponse('支付成功')
        else:
            return HttpResponse('失败')
    else:
        return HttpResponse('只支持GET请求')


def order_list(request):
    """
    查看所有订单状态
    :param request:
    :return:
    """
    orders = models.Order.objects.all()
    return render(request, 'order_list.html', {'orders': orders})