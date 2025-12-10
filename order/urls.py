from django.urls import path 
from .views import login_khakpour, verify_otp_khakpour, order_input_view,dashboard_view,login_view


urlpatterns = [
    path('login_khakpour/', login_khakpour, name='login_khakpour'),
    path('verify-otp_khakpour/', verify_otp_khakpour, name='verify_otp_khakpour'),
    path('input/', order_input_view, name='order_input'),
    path('dashbord/', dashboard_view, name='dashboard'),
    path('login/', login_view, name='login'),

]