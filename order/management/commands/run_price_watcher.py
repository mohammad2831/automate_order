# order/management/commands/run_price_watcher.py
from django.core.management.base import BaseCommand
from order.price_listener import price_watcher  

class Command(BaseCommand):
    help = "اجرای ناظر قیمت ربات‌های خودکار (price_watcher)"

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("ناظر قیمت شروع شد..."))
        price_watcher()