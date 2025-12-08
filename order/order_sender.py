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

WEIGHT_KEY_BUY = "auto_order:weight_buy"
WEIGHT_KEY_SELL = "auto_order:weight_sell"

ENABLED_KEY_BUY = "auto_order:enabled_buy"
ENABLED_KEY_SELL = "auto_order:enabled_sell"

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
def disable_auto_order(side: str):
    """غیرفعال کردن و پاک کردن تنظیمات فقط برای یک سمت (buy یا sell)"""
    if side == "buy":
        redis_cache.set(ENABLED_KEY_BUY, "false")
        redis_cache.delete(WEIGHT_KEY_BUY)
        redis_cache.delete(TARGET_KEY_BUY)
        log.info("ربات خرید خودکار غیرفعال و تنظیمات پاک شد.")
    elif side == "sell":
        redis_cache.set(ENABLED_KEY_SELL, "false")
        redis_cache.delete(WEIGHT_KEY_SELL)
        redis_cache.delete(TARGET_KEY_SELL)
        log.info("ربات فروش خودکار غیرفعال و تنظیمات پاک شد.")



        def send_auto_order(current_price: int, side: str = "buy", weight: float = None):
    """
    ارسال سفارش خودکار خرید یا فروش
    :param current_price: قیمت لحظه‌ای بازار
    :param side: "buy" یا "sell"
    :param weight: وزن (اگر None باشه از ردیس می‌خونه)
    :return: (success: bool, message)
    """
    if side not in ["buy", "sell"]:
        return False, "side باید buy یا sell باشد"

    # ───── تعیین کلیدها بر اساس سمت ─────
    enabled_key = ENABLED_KEY_BUY if side == "buy" else ENABLED_KEY_SELL
    weight_key = WEIGHT_KEY_BUY if side == "buy" else WEIGHT_KEY_SELL

    # 1. چک کردن فعال بودن ربات (برای این سمت)
    if redis_cache.get(enabled_key) != "true":
        log.warning(f"سفارش {side.upper()} نادیده گرفته شد: ربات غیرفعال است")
        return False, f"ربات {side} غیرفعال است"

    # 2. توکن
    token = get_token_from_redis()
    if not token:
        disable_auto_order(side)
        return False, "توکن نامعتبر"

    # 3. وزن — اولویت با پارامتر، در غیر اینصورت از ردیس
    if weight is None:
        weight_raw = redis_cache.get(weight_key)
        if not weight_raw:
            log.error(f"وزن {side} در ردیس موجود نیست")
            disable_auto_order(side)
            return False, "وزن مشخص نشده"
        try:
            weight = float(weight_raw)
        except ValueError:
            log.error(f"وزن {side} نامعتبر است: {weight_raw}")
            disable_auto_order(side)
            return False, "وزن نامعتبر"
    if weight <= 0:
        log.error("وزن باید بزرگتر از صفر باشد")
        return False, "وزن نامعتبر"

    # 4. محاسبه مبلغ کل
    total_price = int(weight * current_price)

    # 5. پیلود داینامیک
    payload = {
        "side": side,  # اینجا مهم است: buy یا sell
        "type": "market_price",
        "price": str(current_price),
        "quantity": weight,
        "total_price": total_price,
        "product_id": PRODUCT_ID,
        "input": "unit",
        "note": f"سفارش خودکار {side.upper()} - وزن: {weight:.6f} گرم - قیمت واحد: {current_price:,} تومان",
    }

    # 6. هدرها
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
        log.info(f"در حال ارسال سفارش خودکار {side.upper()} به API...")
        log.info(f"وزن: {weight:.6f} گرم | قیمت: {current_price:,} | مبلغ کل: {total_price:,} تومان")

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
            message = result.get("message", "موفقیت‌آمیز")
            log.info(f"سفارش {side.upper()} با موفقیت ارسال شد!")
            log.info(f"پیام سرور: {message}")

            # غیرفعال کردن فقط این سمت
            disable_auto_order(side)

            # بوق پیروزی!
            for _ in range(50):
                print("\a", end="", flush=True)
                time.sleep(0.08)

            return True, message

        else:
            error_text = response.text or response.reason
            log.error(f"خطا در ارسال سفارش {side.upper()}: {response.status_code} — {error_text}")
            disable_auto_order(side)
            return False, f"خطا {response.status_code}: {error_text}"

    except requests.exceptions.RequestException as e:
        log.error(f"خطای شبکه در ارسال سفارش {side.upper()}: {e}")
        disable_auto_order(side)
        return False, f"خطای شبکه: {str(e)}"
    except Exception as e:
        log.error(f"خطای غیرمنتظره در سفارش {side.upper()}: {e}")
        disable_auto_order(side)
        return False, str(e)