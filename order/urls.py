from django.urls import path 
from .views import login_khakpour, verify_otp_khakpour, order_input_view


urlpatterns = [
    path('login/', login_khakpour, name='login_khakpour'),
    path('verify-otp/', verify_otp_khakpour, name='verify_otp_khakpour'),
    path('input/', order_input_view, name='order_input'),
]