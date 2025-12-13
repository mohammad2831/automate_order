# order/order_sender.py
import requests
import logging
import redis
from django.utils import timezone
import time

log = logging.getLogger("order_sender")

# تنظیمات ثابت API
API_URL = "https://api.khakpourgold.com/order"
PRODUCT_ID = "e04c3186-be34-4669-9e0a-c4cec1380080"  # آبشده کارت
PRODUCT_ID_NAGHD = "aa96c755-c862-4464-bf80-04654b71cd58"  # نقد فردا

# پروکسی (در صورت نیاز)
PROXIES = None

# اتصال به Redis
redis_cache = redis.Redis(
    host='redis-cache',
    port=6379,
    db=0,
    decode_responses=True,
    socket_keepalive=True,
    retry_on_timeout=True
)

# کلیدهای عمومی
TOKEN_KEY = "auto_order:access_token"
ACTIVE_ORDERS_SET = "auto_orders:active"

def get_token():
    token = redis_cache.get(TOKEN_KEY)
    if not token:
        log.error("توکن در ردیس پیدا نشد!")
        return None
    return token

def remove_order_from_redis(order_id: str):
    """حذف یک سفارش خاص از Redis (هم Hash و هم از SET)"""
    redis_cache.srem(ACTIVE_ORDERS_SET, order_id)
    redis_cache.delete(order_id)
    log.info(f"سفارش {order_id} از Redis حذف شد.")

def send_auto_order(price: int, side: str, weight: float, product: str, order_id: str):
    """
    ارسال سفارش خودکار — فقط برای یک سفارش خاص
    :param price: قیمت لحظه‌ای
    :param side: 'buy' یا 'sell'
    :param weight: وزن
    :param product: 'naghd-farda' یا 'naghd-pasfarda'
    :param order_id: آیدی منحصربه‌فرد سفارش در Redis
    :return: (success: bool, message)
    """
    if side not in ["buy", "sell"]:
        remove_order_from_redis(order_id)
        return False, "نوع سفارش نامعتبر"

    token = get_token()
    if not token:
        remove_order_from_redis(order_id)
        return False, "توکن لاگین وجود ندارد"

    if weight <= 0:
        remove_order_from_redis(order_id)
        return False, "وزن نامعتبر"

    total_price = int(weight * price)

    # پیلود داینامیک
    payload = {
        "side": side,
        "type": "market_price",
        "price": str(price),
        "quantity": weight,
        "total_price": total_price,
        "product_id": PRODUCT_ID_NAGHD,
        "input": "unit",
        "note": f"",
    }

    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:143.0) Gecko/20100101 Firefox/143.0",
        "Accept": "application/json, text/plain, */*",
        "Content-Type": "application/json",
        "X-Verify": "YOUR_REAL_X_VERIFY_CODE_HERE",  # حتماً عوض کن!
        "Origin": "https://panel.khakpourgold.com",
        "Referer": "https://panel.khakpourgold.com/",
    }

    cookies = {
        "access_token_web": token
    }

    try:
        log.info(f"ارسال سفارش {order_id} | {side.upper()} | {product} | وزن: {weight:.6f} گرم | قیمت: {price:,}")

        response = requests.post(
            API_URL,
            headers=headers,
            json=payload,
            cookies=cookies,
            proxies=PROXIES,
            timeout=20
        )

        if response.status_code in (200, 201):
            result = response.json()
            message = result.get("message", "سفارش با موفقیت ثبت شد")
            log.info(f"سفارش {order_id} با موفقیت ارسال شد! پیام سرور: {message}")

            # بوق پیروزی!
            for _ in range(30):
                print("\a", end="", flush=True)
                time.sleep(0.08)

            # حذف سفارش از Redis
            remove_order_from_redis(order_id)
            return True, message

        else:
            error_text = response.text or response.reason
            log.error(f"خطا در ارسال سفارش {order_id}: {response.status_code} — {error_text}")

            # حتی اگر خطا داد، سفارش رو حذف کن (جلوگیری از ارسال دوباره)
            remove_order_from_redis(order_id)
            return False, f"خطا {response.status_code}: {error_text}"

    except requests.exceptions.RequestException as e:
        log.error(f"خطای شبکه در سفارش {order_id}: {e}")
        remove_order_from_redis(order_id)
        return False, f"خطای شبکه: {str(e)}"

    except Exception as e:
        log.error(f"خطای غیرمنتظره در سفارش {order_id}: {e}")
        remove_order_from_redis(order_id)
        return False, str(e)