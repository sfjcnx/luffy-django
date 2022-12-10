from django.conf.urls import url, include
from api.views import course,shoppingcar,payment,order,pay_after


urlpatterns = [
    url(r'^coursecategory/$', course.CourseCategoryView.as_view({'get': 'list'})),

    url(r'^course/$', course.CourseView.as_view({'get': 'list'})),
    url(r'^course/(?P<pk>\d+)/$', course.CourseView.as_view({'get': 'retrieve'})),

    url(r'^shopping_car/$',shoppingcar.ShoppingCarViewSet.as_view()),
    url(r'^payment/$',payment.PaymentViewSet.as_view()),
    url(r'^oreder/$',order.OrderViewSet.as_view()),
    url(r'^show/$',pay_after.show),
    url(r'^check_order/$',pay_after.check_order),
    url(r'^order_list/$', pay_after.order_list),
]




