# order/price_listener.py
import threading
import time
from datetime import datetime
import logging
import redis

# فقط یک بار ترد اجرا بشه (حتی با چند ورکر)
from .order_sender import send_auto_order# تنظیم لاگر با فرمت کامل و زیبا
logging.basicConfig(level=logging.INFO)
log = logging.getLogger("AUTO_ORDER")

_monitor_thread = None
_monitor_lock = threading.Lock()

def start_monitor_once():
    global _monitor_thread
    with _monitor_lock:
        if _monitor_thread is None or not _monitor_thread.is_alive():
            _monitor_thread = threading.Thread(target=price_watcher, daemon=True)
            _monitor_thread.start()
            log.info("ناظر سفارش خودکار فعال شد — فقط یک نمونه در حال اجراست")

# کلیدها
PRICE_KEY = "abshode-kart-buy"
TARGET_KEY = "auto_order:target_price"
WEIGHT_KEY = "auto_order:weight"
ENABLED_KEY = "auto_order:enabled"
TOKEN_KEY = "auto_order:access_token"

# اتصال ردیس
redis_price = redis.Redis(host='redis-price', port=6379, db=0, decode_responses=True)
redis_cache = redis.Redis(host='redis-cache', port=6379, db=0, decode_responses=True)


def price_watcher():
    log.info("شروع نظارت لحظه‌ای بر قیمت و سفارش خودکار...")

    while True:
        try:
            current_time = datetime.now().strftime("%H:%M:%S")

            # 1. وضعیت فعال بودن ربات
            enabled = redis_cache.get(ENABLED_KEY) == "true"
            token_exists = bool(redis_cache.get(TOKEN_KEY))

            # 2. وزن و قیمت هدف
            weight_raw = redis_cache.get(WEIGHT_KEY)
            target_raw = redis_cache.get(TARGET_KEY)

            # 3. قیمت لحظه‌ای
            price_raw = redis_price.get(PRICE_KEY)
            if not price_raw:
                log.info(f"[{current_time}] قیمت لحظه‌ای هنوز در ردیس نیست...")
                time.sleep(3)
                continue

            try:
                current_price = int(float(str(price_raw).replace(",", "").strip()))
            except:
                current_price = 0

            # لاگ لحظه‌ای — همیشه نمایش داده میشه
            if enabled and weight_raw and target_raw and token_exists:
                try:
                    weight = float(weight_raw)
                    target_price = int(float(target_raw))
                    diff = current_price - target_price

                    status = "فعال - در انتظار رسیدن قیمت"
                    if current_price > target_price:
                        status = "قیمت هدف رسید! در حال ارسال سفارش..."

                    log.info(
                        f"[{current_time}] ربات: فعال | "
                        f"وزن: {weight:.6f} گرم | "
                        f"هدف: {target_price:,} | "
                        f"قیمت فعلی: {current_price:,} | "
                        f"تفاوت: {diff:+,} | "
                        f"وضعیت: {status}"
                    )

                    # فقط یک بار ارسال کن
                    if current_price > target_price:
                        log.warning("در حال ارسال سفارش خودکار...")
                        success, result = send_auto_order(current_price)

                        if success:
                            log.info("سفارش با موفقیت ارسال شد!")
                            for _ in range(50):
                                print("\a", end="", flush=True)
                                time.sleep(0.08)
                        else:
                            log.error(f"سفارش ارسال نشد: {result}")

                except Exception as e:
                    log.error(f"خطا در پردازش مقادیر: {e}")

            else:
                # ربات غیرفعاله یا چیزی کمه
                missing = []
                if not enabled:
                    missing.append("ربات غیرفعال")
                if not token_exists:
                    missing.append("توکن لاگین")
                if not weight_raw:
                    missing.append("وزن")
                if not target_raw:
                    missing.append("قیمت هدف")

                log.info(
                    f"[{current_time}] ربات غیرفعال | "
                    f"قیمت فعلی: {current_price:,} | "
                    f"در انتظار: {', '.join(missing)}"
                )

            time.sleep(2.5)  # هر ۲.۵ ثانیه یه بار چک کنه — بهینه و خوانا

        except Exception as e:
            log.error(f"خطای غیرمنتظره در ناظر: {e}")
            time.sleep(10)


# شروع خودکار
start_monitor_once()