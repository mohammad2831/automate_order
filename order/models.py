from django.db import models
from django.contrib.auth.models import AbstractUser

class User(AbstractUser):
    # ✅ بدون blank=True و null=True
    phone_number = models.CharField(max_length=11, unique=True)
    full_name = models.CharField(max_length=150, blank=True)

    groups = models.ManyToManyField(
        'auth.Group',
        related_name='order_users_groups',
        blank=True,
    )
    
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        related_name='order_users_permissions',
        blank=True,
    )
    
    USERNAME_FIELD = 'phone_number'
    REQUIRED_FIELDS = ['username']  # ✅ email را هم می‌توانید حذف کنید
    
    def __str__(self):
        return self.phone_number

class Bot_Order(models.Model):
    TYPE_CHOICES1 = (
        ('buy', ' buy'),
        ('sell', 'sell'),
    )
    TYPE_CHOICES2= (
        ('send', ' send'),
        ('expired', 'expired'),
        ('pending', 'pending'),
        ('canceled', 'canceled'),
    )
    TYPE_CHOICES3=  (
        ('naghd-farda','naghd-farda'),
        ('naghd-pasfarda','naghd-pasfarda'),
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    side = models.CharField(max_length=10, choices=TYPE_CHOICES1)
    weight = models.FloatField() 
    price =  models.BigIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(auto_now=True)
    status = models.CharField(max_length=10, choices=TYPE_CHOICES2)
    active = models.BooleanField(default=True)
    product = models.CharField(max_length=15,choices=TYPE_CHOICES3)
