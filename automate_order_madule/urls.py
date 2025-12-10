"automate_order_madule URL Configuration"

from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('order/', include('order.urls')),
]
