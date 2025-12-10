# settings.py
import os
from pathlib import Path
import redis

# ───── مسیرها ─────
BASE_DIR = Path(__file__).resolve().parent.parent
CSRF_COOKIE_SECURE = False
SESSION_COOKIE_SECURE = False
SECURE_SSL_REDIRECT = False
SECURE_PROXY_SSL_HEADER = None
USE_X_FORWARDED_HOST = False
CSRF_COOKIE_HTTPONLY = False  # اختیاری، ولی بهتره باشه
# ───── امنیت و سرور ─────
SECRET_KEY = os.getenv(
    'DJANGO_SECRET_KEY',
    'django-insecure-change-this-in-production-please-very-long-random-string'
)

# در سرور حتماً False باشه!
DEBUG = os.getenv('DJANGO_DEBUG', 'False') == 'True'

ALLOWED_HOSTS = [
    'app-rxg.ir',
    'www.app-rxg.ir',
    'localhost',
    '127.0.0.1',
    '185.10.75.158',
    '94.182.155.166',
    '[::1]',  # برای IPv6 لوکال
]

# دامنه‌های معتبر برای CSRF (در سرور حتماً تنظیم کن)
CSRF_TRUSTED_ORIGINS = [
    "https://app-rxg.ir",
    "https://www.app-rxg.ir",
    "http://localhost:8000",  # فقط در توسعه
]

# ───── اپلیکیشن‌ها ─────
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # اپ شما
    'order.apps.OrderConfig',
]

# ───── میدلورها — ترتیب خیلی مهم است! ─────
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',        # حتماً فعال!
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# ───── URL و WSGI ─────
ROOT_URLCONF = 'automate_order_madule.urls'
WSGI_APPLICATION = 'automate_order_madule.wsgi.application'

# ───── تمپلیت‌ها ─────
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

# ───── دیتابیس ─────
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# ───── مدل کاربر سفارشی ─────
AUTH_USER_MODEL = 'order.User'

# ───── اعتبارسنجی رمز عبور ─────
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# ───── زبان و زمان ─────
LANGUAGE_CODE = 'fa-ir'
TIME_ZONE = 'Asia/Tehran'
USE_I18N = True
USE_TZ = True

# ───── فایل‌های استاتیک ─────
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# ───── لاگین و ریدایرکت ─────
LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/order_input/'  # بعد از لاگین بره داشبورد
LOGOUT_REDIRECT_URL = '/login/'

# ───── امنیت کوکی‌ها و CSRF (برای HTTPS و داکر) ─────
#SESSION_COOKIE_SECURE = not DEBUG
#CSRF_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_HTTPONLY = False  # برای جاوااسکریپت نیازه
SESSION_COOKIE_SAMESITE = 'Lax'

# ───── کش Redis (django-redis) ─────
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": "redis://redis-cache:6379/0",
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            " CONNECTION_POOL_KWARGS": {"max_connections": 20},
        },
        "KEY_PREFIX": "autoorder",
    }
}

# ───── اتصال مستقیم به Redis (برای price_listener و ...) ─────
REDIS_PRICE = redis.Redis(
    host='redis-price',
    port=6379,
    db=0,
    decode_responses=True,
    socket_keepalive=True,
    retry_on_timeout=True,
    health_check_interval=30,
)

REDIS_CACHE = redis.Redis(
    host='redis-cache',
    port=6379,
    db=0,
    decode_responses=True,
    socket_keepalive=True,
    retry_on_timeout=True,
)

# ───── کانال قیمت زنده (Pub/Sub) ─────
CHANNEL_PRICE_LIVE = "prices:livedata"

# ───── کلید توکن خاکپور ─────
KHAKPOUR_TOKEN_CACHE_KEY = "auto_order:access_token"

# ───── تنظیمات لاگ (اختیاری — خیلی حرفه‌ای) ─────
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
    'loggers': {
        'AUTO_ORDER': {
            'level': 'INFO',
            'handlers': ['console'],
            'propagate': False,
        },
    },
}

# ───── تنظیمات نهایی ─────
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'