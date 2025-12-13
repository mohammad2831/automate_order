# order/apps.py
from django.apps import AppConfig
import threading

# قفل سراسری — تضمین می‌کنه فقط یک بار ترد اجرا بشه
_startup_lock = threading.Lock()


class OrderConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'order'                  # اسم اپت
    verbose_name = "سفارش خودکار"
'''
    def ready(self):
        """
        این متد فقط وقتی که همه اپ‌ها لود شدن اجرا میشه
        و دقیقاً همونجاییه که ما ناظر قیمت رو شروع می‌کنیم
        """
        # اگر در حال migrate یا check هستیم، ترد رو شروع نکن
        import sys
        if 'migrate' in sys.argv or 'makemigrations' in sys.argv or 'check' in sys.argv:
            return

        # فقط یک بار در کل برنامه اجرا بشه (حتی با چند ورکر)
        with _startup_lock:
            try:
                # ایمپورت داخل متد — جلوگیری از circular import
                from .price_listener import start_monitor_once
                start_monitor_once()
            except Exception as e:
                # اگر خطایی بود، فقط لاگ کن — برنامه کرش نکنه
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"خطا در شروع ناظر قیمت: {e}")

'''