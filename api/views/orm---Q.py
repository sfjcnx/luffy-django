

import datetime
from django.db.models import Q
# 补充 ---关于Q
ctime=datetime.date.today()
# 1, 表达式
Q(Q(account=request.auth.user) & Q(status=0))|Q(coupon__valid_begin_date__Ite=ctime)

# 2,方法
q=Q()

q1=Q()
q1.connector("AND")
q1.children.append('account',request.auth.user)
q1.children.append('status',0)
q1.children.append('coupon__valid_begin_date__Ite',ctime)

q2=Q()
q2.connector("AND")
q2.children.append('coupon__valid_end_date__gte',ctime)

q.add(q1,'OR')  # 以OR的形式把q加进来
q.add(q2,'OR')  # q = Q(q1|q2)





