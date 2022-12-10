from rest_framework.authentication import BaseAuthentication
from api import models
from rest_framework.exceptions import AuthenticationFailed
from api.views.account import LoginView


class LuffyAuth(BaseAuthentication):
    def authenticate(self, request):
        """
        用户请求认证
        因为用户不可能时时刻刻把用户名和密码放在前端(不安全,容易被盗号) 所以token(随机字符串)就能找到对应的用户
        :param request:
        :return:
        """
        # http://www....sdfsgfgh/?token=adsfgh
        token = request.query_params.get('token')
        obj=models.UserAuthToken.objects.filter(token=token).first()
        if not obj:
            raise AuthenticationFailed({'code':1001,'error':'认证失败'})

        return(obj.user.username,obj)








