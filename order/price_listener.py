# order/price_listener.py
import threading
import time
from datetime import datetime
import logging
import redis
from django.utils import timezone

# تنظیم لاگر — فرمت زیبا و خوانا
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(message)s',
    datefmt='%H:%M:%S'
)
log = logging.getLogger("AUTO_ORDER")

# فقط یک ترد در کل برنامه
_monitor_thread = None
_monitor_lock = threading.Lock()

# اتصال به Redis
redis_price = redis.Redis(host='redis-price', port=6379, db=0, decode_responses=True)
redis_cache = redis.Redis(host='redis-cache', port=6379, db=0, decode_responses=True)

# کلیدهای قیمت
PRICE_KEYS = {
    ("naghd-farda", "buy"):  "naghd-farda-buy",
    ("naghd-farda", "sell"): "naghd-farda-sell",
    ("naghd-pasfarda", "buy"):  "naghd-pasfarda-buy",
    ("naghd-pasfarda", "sell"): "naghd-pasfarda-sell",
}

ACTIVE_ORDERS_SET = "auto_orders:active"
TOKEN_KEY = "auto_order:access_token"

from .order_sender import send_auto_order

def get_current_price(product: str, side: str):
    key = PRICE_KEYS.get((product, side))
    if not key:
        return None
    raw = redis_price.get(key)
    if not raw:
        return None
    try:
        return int(float(str(raw).replace(",", "").strip()))
    except:
        return None

def log_status_report():
    """هر چند ثانیه یک گزارش کامل از وضعیت قیمت‌ها و ربات‌ها چاپ کنه"""
    now = datetime.now().strftime("%H:%M:%S")

    # قیمت‌های لحظه‌ای
    prices = {}
    for (product, side), key in PRICE_KEYS.items():
        price = redis_price.get(key)
        try:
            price = int(float(str(price).replace(",", "").strip())) if price else None
        except:
            price = None
        prices[f"{product}-{side}"] = price

    log.info("═" * 70)
    log.info(f" وضعیت قیمت‌ها | {now}")
    log.info("─" * 70)
    log.info(f" نقد فردا خرید  : {prices['naghd-farda-buy']:,} تومان" if prices['naghd-farda-buy'] else " نقد فردا خرید  : ناموجود")
    log.info(f" نقد فردا فروش  : {prices['naghd-farda-sell']:,} تومان" if prices['naghd-farda-sell'] else " نقد فردا فروش  : ناموجود")
    log.info(f" نقد پس‌فردا خرید: {prices['naghd-pasfarda-buy']:,} تومان" if prices['naghd-pasfarda-buy'] else " نقد پس‌فردا خرید: ناموجود")
    log.info(f" نقد پس‌فردا فروش: {prices['naghd-pasfarda-sell']:,} تومان" if prices['naghd-pasfarda-sell'] else " نقد پس‌فردا فروش: ناموجود")
    log.info("─" * 70)

    # ربات‌های فعال
    order_ids = redis_cache.smembers(ACTIVE_ORDERS_SET)
    if not order_ids:
        log.info(" هیچ ربات فعالی وجود ندارد")
    else:
        log.info(f" ربات‌های فعال: {len(order_ids)} مورد")
        log.info("─" * 70)
        for order_id in sorted(order_ids):
            data = redis_cache.hgetall(order_id)
            if not data:
                continue
            try:
                side = "خرید" if data['side'] == 'buy' else "فروش"
                product = "نقد فردا" if data['product'] == 'naghd-farda' else "نقد پس‌فردا"
                target = int(float(data['target_price']))
                weight = float(data['weight'])
                current = get_current_price(data['product'], data['side'])
                status = "در انتظار"
                if current is not None:
                    if (data['side'] == 'buy' and current <= target) or (data['side'] == 'sell' and current >= target):
                        status = "هدف رسید! در حال ارسال..."
                    elif data['side'] == 'buy':
                        status = f"{current:,} → {target:,}"
                    else:
                        status = f"{target:,} ← {current:,}"

                log.info(f" {side} | {product} | وزن: {weight:.4f} گرم | هدف: {target:,} | فعلی: {current or '—'} | {status} | {order_id[-8:]}")
            except:
                log.warning(f" خطا در خواندن سفارش {order_id}")

    log.info("═" * 70)

def price_watcher():
    log.info("ناظر حرفه‌ای ربات معاملاتی شروع شد — لاگ کامل و زیبا")

    last_report = 0  # برای گزارش هر ۵ ثانیه

    while True:
        try:
            now = time.time()

            # گزارش وضعیت هر ۵ ثانیه
            if now - last_report >= 5:
                log_status_report()
                last_report = now

            # بررسی توکن
            token = redis_cache.get(TOKEN_KEY)
            if not token:
                time.sleep(10)
                continue

            order_ids = redis_cache.smembers(ACTIVE_ORDERS_SET)
            if not order_ids:
                time.sleep(3)
                continue

            orders_to_remove = []

            for order_id in order_ids:
                data = redis_cache.hgetall(order_id)
                if not data:
                    orders_to_remove.append(order_id)
                    continue

                try:
                    product = data['product']
                    side = data['side']
                    target_price = int(float(data['target_price']))
                    weight = float(data['weight'])

                    current_price = get_current_price(product, side)
                    if current_price is None:
                        continue

                    triggered = (
                        (side == "buy" and current_price >= target_price) or
                        (side == "sell" and current_price <= target_price)
                    )

                    if triggered:
                        log.info(f"هدف رسید! ارسال سفارش {order_id}")

                        success, msg = send_auto_order(
                            price=current_price,
                            side=side,
                            weight=weight,
                            product=product,
                            order_id=order_id
                        )

                        if success:
                            log.info(f"سفارش {order_id} با موفقیت ارسال شد!")
                            for _ in range(20):
                                print("\a", end="", flush=True)
                                time.sleep(0.08)
                        else:
                            log.error(f"خطا در ارسال {order_id}: {msg}")

                        orders_to_remove.append(order_id)

                except Exception as e:
                    log.error(f"خطا در سفارش {order_id}: {e}")
                    orders_to_remove.append(order_id)

            if orders_to_remove:
                count = len(orders_to_remove)
                redis_cache.srem(ACTIVE_ORDERS_SET, *orders_to_remove)
                for oid in orders_to_remove:
                    redis_cache.delete(oid)
                log.info(f"{count} سفارش اجرا و حذف شد.")

            time.sleep(1.5)

        except KeyboardInterrupt:
            log.info("ناظر متوقف شد.")
            break
        except Exception as e:
            log.critical(f"خطای بحرانی: {e}")
            time.sleep(10)

def start_monitor_once():
    global _monitor_thread
    with _monitor_lock:
        if _monitor_thread is None or not _monitor_thread.is_alive():
            _monitor_thread = threading.Thread(target=price_watcher, daemon=True)
            _monitor_thread.start()
            log.info("ناظر با لاگ حرفه‌ای فعال شد — هر ۵ ثانیه گزارش کامل")

# شروع خودکار
start_monitor_once()