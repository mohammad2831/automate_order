from django.shortcuts import render, redirect
from django.contrib import messages
from .auth_utils import send_otp_request, get_token_request
from django.core.cache import cache
import redis


redis_cache = redis.Redis(
    host='redis-cache',
    port=6379,
    db=0,
    decode_responses=True,
    socket_keepalive=True,
    retry_on_timeout=True
)


def login_khakpour(request):
    if request.method == "POST":
        phone = request.POST.get('phone_number').strip()
        if len(phone) != 11 or not phone.startswith('09'):
            messages.error(request, 'شماره موبایل معتبر نیست')
            return render(request, 'auth/login.html')

        result = send_otp_request(phone)
        if result.get('success'):
            messages.success(request, 'کد تأیید با موفقیت ارسال شد')
            request.session['phone_for_otp'] = phone
            return redirect('verify_otp_khakpour')
        else:
            messages.error(request, result.get('data', {}).get('message', 'خطا در ارسال کد'))
    
    return render(request, 'auth/login.html')


def verify_otp_khakpour(request):
    if request.method == "POST":
        phone = request.session.get('phone_for_otp')
        code = request.POST.get('otp_code')

        if not phone:
            messages.error(request, 'دوره زمانی منقضی شده')
            return redirect('login_khakpour')

        result = get_token_request(phone, code)

        if result.get('token'):
            # ذخیره توکن در سشن یا کوکی
            request.session['khakpour_token'] = result['token']
            messages.success(request, 'ورود با موفقیت انجام شد')
            return redirect('order_input')

        else:
            messages.error(request, result.get('error', 'کد تأیید اشتباه است'))

    return render(request, 'auth/verify_otp.html')




def order_input_view(request):
    # چک لاگین
    if not request.session.get('khakpour_token'):
        messages.error(request, 'ابتدا باید وارد شوید')
        return redirect('login_khakpour')

    if request.method == "POST":
        try:
            weight = float(request.POST.get('weight', 0))
            cost = float(request.POST.get('cost', 0))

            if weight <= 0 or cost <= 0:
                raise ValueError("وزن و قیمت باید بزرگتر از صفر باشند")

            target_price = int(cost)

            # ذخیره مستقیم در redis-cache — نه cache!
            redis_cache.set("auto_order:weight", weight, ex=None)
            redis_cache.set("auto_order:target_price", target_price, ex=None)
            redis_cache.set("auto_order:enabled", "true", ex=None)

            messages.success(
                request,
                f"ربات فعال شد! وزن: {weight:,.6f} گرم | هدف: {target_price:,} تومان"
            )
            return redirect('order_input')

        except Exception as e:
            messages.error(request, "لطفاً وزن و قیمت معتبر وارد کنید")

    # نمایش وضعیت فعلی (از redis-cache واقعی)
    status = {
        "weight": redis_cache.get("auto_order:weight") or "",
        "target_price": redis_cache.get("auto_order:target_price") or "",
        "enabled": redis_cache.get("auto_order:enabled") == "true",
        "current_price": redis_cache.get("abshode-kart-buy"),
    }

    return render(request, 'auth/order_input.html', {"status": status})