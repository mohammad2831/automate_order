# order/order_sender.py
import requests
import logging
import redis

log = logging.getLogger("order_sender")

# ───── تنظیمات ثابت API ─────
API_URL = "https://api.khakpourgold.com/order"
PRODUCT_ID = "e04c3186-be34-4669-9e0a-c4cec1380080"  # آبشده کارت

# اتصال به redis-cache
redis_cache = redis.Redis(
    host='redis-cache',
    port=6379,
    db=0,
    decode_responses=True,
    socket_keepalive=True,
    retry_on_timeout=True
)

# کلیدهای ردیس — همه یکسان و منظم
TOKEN_KEY = "auto_order:access_token"
WEIGHT_KEY = "auto_order:weight"
ENABLED_KEY = "auto_order:enabled"

# پروکسی (در صورت نیاز)
PROXIES = None  # یا فعالش کن: {"http": "...", "https": "..."}

def get_token_from_redis():
    token = redis_cache.get(TOKEN_KEY)
    if not token:
        log.error("توکن در ردیس پیدا نشد!")
        return None
    return token

def get_weight_from_redis():
    weight_raw = redis_cache.get(WEIGHT_KEY)
    if not weight_raw:
        log.error("وزن در ردیس پیدا نشد!")
        return None
    try:
        return float(weight_raw)
    except ValueError:
        log.error("وزن در ردیس نامعتبر است!")
        return None

def disable_auto_order():
    """بعد از ارسال سفارش، ربات رو غیرفعال کن"""
    redis_cache.set(ENABLED_KEY, "false")
    redis_cache.delete(WEIGHT_KEY)
    redis_cache.delete("auto_order:target_price")  # قیمت هدف دیگه لازم نیست
    log.info("ربات سفارش خودکار غیرفعال شد و تنظیمات پاک شدند")
def send_auto_order(current_price: int):
    """
    ارسال سفارش خودکار با استفاده از کوکی (نه Bearer Token)
    فقط قیمت لحظه‌ای رو می‌گیره، بقیه رو خودش از ردیس می‌خونه
    """
    # 1. چک کردن فعال بودن ربات
    if redis_cache.get(ENABLED_KEY) != "true":
        log.warning("سفارش نادیده گرفته شد: ربات غیرفعال است")
        return False, "ربات غیرفعال است"

    # 2. خواندن توکن (همون مقدار رمزنگاری‌شده کوکی)
    token = get_token_from_redis()
    if not token:
        log.error("توکن در ردیس پیدا نشد!")
        disable_auto_order()
        return False, "توکن معتبر نیست"

    # 3. خواندن وزن
    weight = get_weight_from_redis()
    if not weight or weight <= 0:
        log.error("وزن نامعتبر است")
        disable_auto_order()
        return False, "وزن نامعتبر"

    # 4. محاسبه مبلغ کل
    total_price = int(weight * current_price)

    # 5. پیلود
    payload = {
        "side": "buy",
        "type": "market_price",
        "price": str(current_price),
        "quantity": weight,
        "total_price": total_price,
        "product_id": PRODUCT_ID,
        "input": "unit",
        "note": f"سفارش خودکار - وزن: {weight:.6f} گرم - قیمت: {current_price:,} تومان",
    }

    # 6. هدرها — بدون Authorization!
    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:143.0) Gecko/20100101 Firefox/143.0",
        "Accept": "application/json, text/plain, */*",
        "Content-Type": "application/json",
        "X-Verify": "YOUR_REAL_X_VERIFY_CODE",  # حتماً مقدار واقعی رو بذار!
        "Origin": "https://panel.khakpourgold.com",
        "Referer": "https://panel.khakpourgold.com/",
        "Cache-Control": "no-cache",
    }

    # مهم: توکن فقط در کوکی فرستاده میشه!
    cookies = {
        "access_token_web": token
    }

    try:
        log.info("در حال ارسال سفارش خودکار به API خاکپور...")
        response = requests.post(
            API_URL,
            headers=headers,
            json=payload,
            cookies=cookies,    # این خط حیاتیه!
            proxies=PROXIES,
            timeout=20
        )

        if response.status_code in (200, 201):
            result = response.json()
            log.info("سفارش خودکار با موفقیت ارسال شد!")
            log.info(f"وزن: {weight:.6f} گرم | قیمت: {current_price:,} | مبلغ کل: {total_price:,} تومان")
            log.info(f"پاسخ سرور: {result.get('message', 'موفق')}")

            # غیرفعال کردن ربات بعد از موفقیت
            disable_auto_order()

            # بوق انفجاری!
            for _ in range(60):
                print("\a", end="", flush=True)
                time.sleep(0.08)

            return True, result

        else:
            error_msg = response.text or response.reason
            log.error(f"خطا در ارسال سفارش: {response.status_code} - {error_msg}")
            disable_auto_order()
            return False, f"HTTP {response.status_code}: {error_msg}"

    except requests.exceptions.RequestException as e:
        log.error(f"خطا در ارتباط با API: {e}")
        disable_auto_order()
        return False, f"خطای شبکه: {str(e)}"
    except Exception as e:
        log.error(f"خطای غیرمنتظره: {e}")
        disable_auto_order()
        return False, str(e)