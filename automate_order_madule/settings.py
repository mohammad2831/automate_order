from pathlib import Path
import socket
import redis
BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_URL = '/static/'
LOGIN_URL = '/login/'
SECRET_KEY = 'django-insecure-nl)6!suh1tuyi5vy^g$8pzswkwkkcsio#_t1&nm2pcgxkgq6^)'
DEBUG = True
STATIC_ROOT = BASE_DIR / 'staticfiles'
ALLOWED_HOSTS = ['app-rxg.ir', "www.app-rxg.ir", 'localhost','127.0.0.1','185.10.75.158', '94.182.155.166']


# ✅ مدل کاربر سفارشی
AUTH_USER_MODEL = 'order.User'

# ✅ اضافه کنید - برای احراز هویت
AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
]



LOGIN_URL = '/login/'
#LOGIN_REDIRECT_URL = '/'  # ✅ اضافه کنید




INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',


    'order.apps.OrderConfig',

]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'automate_order_madule.urls'

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





WSGI_APPLICATION = 'automate_order_madule.wsgi.application'


DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}


AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True


STATIC_URL = 'static/'




DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'





AUTH_USER_MODEL = 'order.User'


REDIS_PRICE = redis.Redis(
    host='redis-price',
    port=6379,
    db=0,
    decode_responses=True,
    socket_keepalive=True,
    retry_on_timeout=True,
    health_check_interval=30,
)

# چنل قیمت — حتماً با دو پروژه دیگه یکسان باشه!
CHANNEL_PRICE_LIVE = "prices:livedata"

# --- کش (اختیاری — برای ذخیره سفارشات موقت، وضعیت و ...) ---
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": "redis://redis-cache:6379/0",
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
        },
        "KEY_PREFIX": "autoorder",
    }
}

# --- STATIC (برای رفع خطای قبلی) ---
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'