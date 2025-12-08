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
PRICE_KEY = "naghd-farda-buy"

TARGET_KEY_Buy = "auto_order:target_price_buy"
TARGET_KEY_SELL = "auto_order:target_price_sell"

WEIGHT_KEY_BUY = "auto_order:buy_weight"
WEIGHT_KEY_SELL = "auto_order:sell_weight"

ENABLED_KEY_BUY = "auto_order:enabled_buy"
ENABLED_KEY_SELL = "auto_order:enabled_sell"

TOKEN_KEY = "auto_order:access_token"

# اتصال ردیس
redis_price = redis.Redis(host='redis-price', port=6379, db=0, decode_responses=True)
redis_cache = redis.Redis(host='redis-cache', port=6379, db=0, decode_responses=True)


def price_watcher():
    log.info("ناظر سفارش خودکار شروع شد — پشتیبانی از خرید و فروش همزمان")

    global _order_sent_buy, _order_sent_sell

    while True:
        try:
            current_time = datetime.now().strftime("%H:%M:%S")
            # reset_daily_flags()  # اگر می‌خوای هر روز ریست بشه، این خط رو فعال کن

            # قیمت لحظه‌ای بازار
            price_raw = redis_price.get(PRICE_KEY)
            if not price_raw:
                log.debug(f"[{current_time}] قیمت لحظه‌ای موجود نیست.")
                time.sleep(3)
                continue

            try:
                current_price = int(float(str(price_raw).replace(",", "").strip()))
            except:
                log.error(f"تبدیل قیمت ناموفق: {price_raw}")
                time.sleep(3)
                continue

            # توکن لاگین
            token_exists = bool(redis_cache.get(TOKEN_KEY))

            # وضعیت BUY
            enabled_buy = redis_cache.get(ENABLED_KEY_BUY) == "true"
            target_buy_raw = redis_cache.get(TARGET_KEY_BUY)
            weight_buy_raw = redis_cache.get(WEIGHT_KEY_BUY)

            # وضعیت SELL
            enabled_sell = redis_cache.get(ENABLED_KEY_SELL) == "true"
            target_sell_raw = redis_cache.get(TARGET_KEY_SELL)
            weight_sell_raw = redis_cache.get(WEIGHT_KEY_SELL)

            # پردازش BUY
            if enabled_buy and token_exists and target_buy_raw and weight_buy_raw:
                try:
                    target_price = int(float(target_buy_raw))
                    weight = float(weight_buy_raw)

                    if current_price <= target_price and not _order_sent_buy:
                        log.info("قیمت هدف خرید رسید! در حال ارسال سفارش خرید...")
                        success, result = send_auto_order(current_price, side="buy", weight=weight)

                        if success:
                            log.info("سفارش خرید با موفقیت ارسال شد!")
                            with _order_sent_lock:
                                _order_sent_buy = True
                            for _ in range(30):
                                print("\a", end="", flush=True)
                                time.sleep(0.1)
                        else:
                            log.error(f"خطا در ارسال سفارش خرید: {result}")
                    else:
                        status = "در انتظار" if current_price > target_price else "سفارش قبلاً ارسال شده"
                        log.info(
                            f"[{current_time}] خرید | هدف: {target_price:,} | "
                            f"فعلی: {current_price:,} | وزن: {weight:.6f} گرم | وضعیت: {status}"
                        )
                except Exception as e:
                    log.error(f"خطا در پردازش خرید: {e}")
            else:
                missing = []
                if not enabled_buy: missing.append("غیرفعال")
                if not token_exists: missing.append("توکن")
                if not target_buy_raw: missing.append("هدف")
                if not weight_buy_raw: missing.append("وزن")
                log.info(f"[{current_time}] خرید غیرفعال | دلیل: {', '.join(missing)}")

            # پردازش SELL
            if enabled_sell and token_exists and target_sell_raw and weight_sell_raw:
                try:
                    target_price = int(float(target_sell_raw))
                    weight = float(weight_sell_raw)

                    if current_price >= target_price and not _order_sent_sell:
                        log.info("قیمت هدف فروش رسید! در حال ارسال سفارش فروش...")
                        success, result = send_auto_order(current_price, side="sell", weight=weight)

                        if success:
                            log.info("سفارش فروش با موفقیت ارسال شد!")
                            with _order_sent_lock:
                                _order_sent_sell = True
                            for _ in range(30):
                                print("\a", end="", flush=True)
                                time.sleep(0.1)
                        else:
                            log.error(f"خطا در ارسال سفارش فروش: {result}")
                    else:
                        status = "در انتظار" if current_price < target_price else "سفارش قبلاً ارسال شده"
                        log.info(
                            f"[{current_time}] فروش | هدف: {target_price:,} | "
                            f"فعلی: {current_price:,} | وزن: {weight:.6f} گرم | وضعیت: {status}"
                        )
                except Exception as e:
                    log.error(f"خطا در پردازش فروش: {e}")
            else:
                missing = []
                if not enabled_sell: missing.append("غیرفعال")
                if not token_exists: missing.append("توکن")
                if not target_sell_raw: missing.append("هدف")
                if not weight_sell_raw: missing.append("وزن")
                log.info(f"[{current_time}] فروش غیرفعال | دلیل: {', '.join(missing)}")

            time.sleep(2.5)

        except Exception as e:
            log.critical(f"خطای بحرانی در ناظر: {e}")
            time.sleep(10)


def start_monitor_once():
    global _monitor_thread
    with _monitor_lock:
        if _monitor_thread is None or not _monitor_thread.is_alive():
            _monitor_thread = threading.Thread(target=price_watcher, daemon=True)
            _monitor_thread.start()
            log.info("ناظر سفارش خودکار (خرید + فروش) فعال شد — تنها یک نمونه در حال اجراست")


# شروع خودکار هنگام ایمپورت
start_monitor_once()