from django.contrib import admin

from .models import Bot_Order, User
admin.site.register(User)
admin.site.register(Bot_Order)