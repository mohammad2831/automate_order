from django.shortcuts import render, redirect
from django.contrib import messages
from .auth_utils import send_otp_request, get_token_request
from django.core.cache import cache
import redis
import time
from datetime import datetime, timedelta
from .models import Bot_Order, User
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from django.contrib.auth import authenticate, login
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from datetime import datetime, timedelta
from django.utils import timezone
import uuid

redis_cache = redis.Redis(
    host='redis-cache',
    port=6379,
    db=0,
    decode_responses=True,
    socket_keepalive=True,
    retry_on_timeout=True
)



redis_price = redis.Redis(
    host='redis-price',
    port=6379,
    db=0,
    decode_responses=True,
    socket_keepalive=True,
    retry_on_timeout=True
)

def format_ttl(seconds):
    if seconds <= 0:
        return "منقضی شده"
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    return f"{hours:02d}:{minutes:02d}"

def login_view(request):
    # اگر کاربر قبلاً لاگین کرده، مستقیم ببرش داشبورد
    if request.user.is_authenticated:
        return redirect('/order/dashbord/')

    if request.method == "POST":
        phone_number = request.POST.get('phone_number', '').strip()
        password = request.POST.get('password', '')

        # اعتبارسنجی ورودی
        if not phone_number:
            messages.error(request, 'لطفاً شماره موبایل را وارد کنید')
        elif not password:
            messages.error(request, 'لطفاً رمز عبور را وارد کنید')
        else:
            # احراز هویت
            user = authenticate(request, username=phone_number, password=password)

            if user is not None:
                if user.is_active:
                    login(request, user)
                    messages.success(request, 'خوش آمدید!')
                    return redirect('/order/dashboard/')
                else:
                    messages.error(request, 'حساب شما غیرفعال است. با پشتیبانی تماس بگیرید.')
            else:
                messages.error(request, 'شماره موبایل یا رمز عبور اشتباه است.')

    # GET request یا POST ناموفق → نمایش فرم
    return render(request, 'auth/login.html')


@login_required
def dashboard_view(request):
    return render(request, 'auth/dashbord.html', {})

def verify_otp_khakpour(request):
    if request.method == "POST":
        phone = request.session.get('phone_for_otp')
        code = request.POST.get('otp_code', '').strip()

        if not phone:
            messages.error(request, 'جلسه منقضی شده است. لطفاً دوباره تلاش کنید.')
            return redirect('login_khakpour')

        if len(code) != 4 or not code.isdigit():
            messages.error(request, 'کد تأیید باید 4 رقم باشد')
            return render(request, 'auth/verify_otp_khakpour.html', {'phone': phone})

        # دریافت توکن از API خاکپور
        result = get_token_request(phone, code)

        if result.get('token'):
            token = result['token']

            # ذخیره توکن در Redis (مهم!)
            cache.set("auto_order:access_token", token, timeout=23*3600)  # ۲۳ ساعت

            # پاک کردن جلسه
            if 'phone_for_otp' in request.session:
                del request.session['phone_for_otp']

            # پیام موفقیت حرفه‌ای
            messages.success(
                request,
                'شما با موفقیت در پنل خاکپور لاگین شدید!<br>'
                'ربات معاملاتی اکنون فعال است و آماده فعالیت می‌باشد.'
            )

            # برگشت به داشبورد
            return redirect('order_input')  # یا هر نام ویوی داشبوردت

        else:
            error_msg = result.get('error', 'کد تأیید اشتباه است')
            messages.error(request, error_msg)

    # اگر GET بود یا خطا داد، صفحه تأیید رو نشون بده
    phone = request.session.get('phone_for_otp', '')
    return render(request, 'auth/verify_otp_khakpour.html', {'phone': phone})


def login_khakpour(request):
    if request.method == "POST":
        phone = request.POST.get('phone_number', '').strip()
        
        if len(phone) != 11 or not phone.startswith('09'):
            messages.error(request, 'شماره موبایل باید ۱۱ رقمی و با ۰۹ شروع شود')
            return render(request, 'auth/login_khakpour.html')  # درست

        result = send_otp_request(phone)
        if result.get('success'):
            messages.success(request, 'کد تأیید با موفقیت ارسال شد')
            request.session['phone_for_otp'] = phone
            return redirect('verify_otp_khakpour')
        else:
            error_msg = result.get('data', {}).get('message', 'خطا در ارسال کد تأیید')
            messages.error(request, error_msg)
            return render(request, 'auth/login_khakpour.html')  # اینجا هم درست

    # GET request → نمایش صفحه لاگین خاکپور
    return render(request, 'auth/login_khakpour.html')  # این خط مهم بود!

#@login_required


@login_required
def order_input_view(request):
    user = request.user

    if request.method == "POST":
        try:
            # ——— غیرفعال کردن ربات ———
            if 'stop_bot' in request.POST:
                bot_type = request.POST['stop_bot']  # 'buy' یا 'sell'

                order_ids = redis_cache.smembers("auto_orders:active")
                removed = False

                for oid in order_ids:
                    data = redis_cache.hgetall(oid)
                    if (data.get('user_id') == str(user.id) and 
                        data.get('side') == bot_type):
                        redis_cache.srem("auto_orders:active", oid)
                        redis_cache.delete(oid)
                        removed = True

                        # بروزرسانی دیتابیس
                        recent = Bot_Order.objects.filter(
                            user=user, side=bot_type, active=True
                        ).order_by('-created_at').first()
                        if recent:
                            recent.active = False
                            recent.status = 'canceled'
                            recent.finished_at = timezone.now()
                            recent.save()

                if removed:
                    messages.success(request, f"ربات {'خرید' if bot_type=='buy' else 'فروش'} با موفقیت غیرفعال شد.")
                else:
                    messages.info(request, "رباتی برای غیرفعال کردن یافت نشد.")

                return redirect('order_input')

            # ——— ایجاد ربات جدید ———
            bot_type = request.POST.get('bot_type')
            product = request.POST.get('product')
            weight = float(request.POST.get('weight', 0))
            target_price = int(float(request.POST.get('target_price', 0)))
            
            # مهم: کاربر ساعت انتخاب کرده
            hours = int(request.POST.get('dedline_hours', 24))
            dedline_seconds = hours * 3600  # تبدیل به ثانیه

            enable_bot = 'enable_bot' in request.POST

            # اعتبارسنجی
            if weight <= 0 or target_price <= 0 or hours < 1:
                raise ValueError("مقادیر وارد شده نامعتبر است.")

            # ایجاد سفارش در دیتابیس
            order = Bot_Order.objects.create(
                user=user,
                side=bot_type,
                weight=weight,
                price=target_price,
                status='send',
                active=True,
                product=product
            )

            message = f"سفارش {'خرید' if bot_type=='buy' else 'فروش'} ({weight} گرم) ثبت شد."

            # اگر فعال‌سازی فوری بود → در Redis ذخیره کن
            if enable_bot:
                order_id = f"order:{uuid.uuid4().hex[:12]}"

                redis_cache.hset(order_id, mapping={
                    "user_id": str(user.id),
                    "side": bot_type,
                    "weight": str(weight),
                    "target_price": str(target_price),
                    "product": product,
                    "created_at": timezone.now().isoformat(),
                    "expires_in_hours": str(hours),  # برای نمایش بهتر
                })

                redis_cache.sadd("auto_orders:active", order_id)
                redis_cache.expire(order_id, dedline_seconds + 3600)  # ۱ ساعت اضافه برای اطمینان

                messages.success(request, 
                    f"ربات {'خرید' if bot_type=='buy' else 'فروش'} با موفقیت فعال شد! "
                    f"مدت زمان: {hours} ساعت"
                )
            else:
                messages.success(request, "سفارش ثبت شد (غیرفعال)")

        except ValueError as e:
            messages.error(request, f"خطا: {e}")
        except Exception as e:
            messages.error(request, f"خطای غیرمنتظره: {str(e)}")

        return redirect('order_input')

    # ——— GET: نمایش داشبورد ———
    status = {
        "enabled_buy": False,
        "enabled_sell": False,
        "buy_weight": "", "target_price_buy": "", "buy_exp_time": "منقضی شده",
        "sell_weight": "", "target_price_sell": "", "sell_exp_time": "منقضی شده",
        "current_price": redis_cache.get("naghd-farda-buy") or "در حال بارگذاری...",
    }

    # بررسی ربات‌های فعال این کاربر
    active_orders = redis_cache.smembers("auto_orders:active")
    for oid in active_orders:
        data = redis_cache.hgetall(oid)
        if data and data.get('user_id') == str(user.id):
            side = data['side']
            ttl = redis_cache.ttl(oid)
            exp_time = format_ttl(ttl) if ttl > 0 else "منقضی شده"

            if side == 'buy':
                status.update({
                    "enabled_buy": True,
                    "buy_weight": data.get('weight', ''),
                    "target_price_buy": data.get('target_price', ''),
                    "buy_exp_time": exp_time,
                })
            elif side == 'sell':
                status.update({
                    "enabled_sell": True,
                    "sell_weight": data.get('weight', ''),
                    "target_price_sell": data.get('target_price', ''),
                    "sell_exp_time": exp_time,
                })

    # تاریخچه سفارش‌ها
    history = Bot_Order.objects.filter(user=user).order_by('-created_at')[:10]

    context = {
        "status": status,
        "history": history,
    }

    return render(request, 'auth/dashbord.html', context)