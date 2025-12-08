from django.shortcuts import render, redirect
from django.contrib import messages
from .auth_utils import send_otp_request, get_token_request
from django.core.cache import cache
import redis
import time
from datetime import datetime, timedelta

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
            
            # دریافت وضعیت فعال‌سازی
            enable_buy = 'enable_buy' in request.POST
            enable_sell = 'enable_sell' in request.POST
            
            # --- مدیریت ربات خرید ---
            if enable_buy:
                buy_weight = float(request.POST.get('buy_weight', 0))
                buy_cost = float(request.POST.get('buy_cost', 0))
                buy_dedline = int(request.POST.get('buy_dedline', 0))
                
                if buy_weight <= 0 or buy_cost <= 0 or buy_dedline <= 0:
                    raise ValueError("وزن، قیمت یا مهلت زمانی خرید باید بزرگتر از صفر باشند")

                target_price_buy = int(buy_cost)
                
                # ذخیره با زمان انقضا (TTL)
                redis_cache.set("auto_order:buy_weight", buy_weight, ex=buy_dedline)
                redis_cache.set("auto_order:target_price_buy", target_price_buy, ex=buy_dedline)
                redis_cache.set("auto_order:enabled_buy", "true", ex=buy_dedline)
                buy_message = f"خرید: {buy_weight:,.6f} گرم @ {target_price_buy:,} تومان فعال شد."
            else:
                # اگر غیرفعال شد، کلیدهای مربوطه را حذف کن
                redis_cache.delete("auto_order:buy_weight", "auto_order:target_price_buy", "auto_order:enabled_buy")
                buy_message = "ربات خرید غیرفعال شد."

            
            # --- مدیریت ربات فروش ---
            if enable_sell:
                sell_weight = float(request.POST.get('sell_weight', 0))
                sell_cost = float(request.POST.get('sell_cost', 0))
                sell_dedline = int(request.POST.get('sell_dedline', 0)) 
                
                if sell_weight <= 0 or sell_cost <= 0 or sell_dedline <= 0:
                    raise ValueError("وزن، قیمت یا مهلت زمانی فروش باید بزرگتر از صفر باشند")
                    
                target_price_sell = int(sell_cost)
                
                # ذخیره با زمان انقضا (TTL)
                redis_cache.set("auto_order:sell_weight", sell_weight, ex=sell_dedline)
                redis_cache.set("auto_order:target_price_sell", target_price_sell, ex=sell_dedline)
                redis_cache.set("auto_order:enabled_sell", "true", ex=sell_dedline)
                sell_message = f"فروش: {sell_weight:,.6f} گرم @ {target_price_sell:,} تومان فعال شد."
            else:
                 # اگر غیرفعال شد، کلیدهای مربوطه را حذف کن
                redis_cache.delete("auto_order:sell_weight", "auto_order:target_price_sell", "auto_order:enabled_sell")
                sell_message = "ربات فروش غیرفعال شد."


            messages.success(request, f"تنظیمات با موفقیت ثبت شد. | {buy_message} | {sell_message}")
            return redirect('order_input')

        except ValueError as ve:
            messages.error(request, f"خطا در داده ورودی: {ve}")
        except Exception as e:
            messages.error(request, f"خطای عمومی: لطفاً داده‌های معتبر وارد کنید. ({e})")

    # 4. نمایش وضعیت فعلی (GET Request)
    
    # ... بقیه کد مربوط به format_ttl و بخش GET request را از ویو قبلی کپی کنید.
    # به ویژه بخش:
    # def format_ttl(ttl): ...
    # buy_ttl = redis_cache.ttl("auto_order:enabled_buy")
    # ...
    
    # فقط مطمئن شوید که بخش دریافت وضعیت (status) برای هر دو عملیات کامل است:
    buy_ttl = redis_cache.ttl("auto_order:enabled_buy")
    sell_ttl = redis_cache.ttl("auto_order:enabled_sell")

    def format_ttl(ttl):
        if ttl is None or ttl < 0:
            return None
        exp_time = datetime.now() + timedelta(seconds=ttl)
        return exp_time.strftime("%H:%M:%S")
        
    status = {
        "buy_weight": redis_cache.get("auto_order:buy_weight") or "",
        "target_price_buy": redis_cache.get("auto_order:target_price_buy") or "",
        # بررسی می‌کنیم که آیا کلید enabled وجود دارد و True است.
        "enabled_buy": redis_cache.get("auto_order:enabled_buy") == b"true" and buy_ttl > 0, 
        "buy_exp_time": format_ttl(buy_ttl),
        
        "sell_weight": redis_cache.get("auto_order:sell_weight") or "",
        "target_price_sell": redis_cache.get("auto_order:target_price_sell") or "",
        "enabled_sell": redis_cache.get("auto_order:enabled_sell") == b"true" and sell_ttl > 0,
        "sell_exp_time": format_ttl(sell_ttl),

        "current_price": redis_cache.get("abshode-kart-buy"),
    }
    
    # تبدیل بایت به رشته برای نمایش در قالب
    for key in status:
        if isinstance(status[key], bytes):
            status[key] = status[key].decode('utf-8')

    return render(request, 'auth/order_input.html', {"status": status})
