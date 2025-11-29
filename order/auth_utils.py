# Module_Get_Price/auth_utils.py
import requests
import json
import re
from django.conf import settings
from requests.packages.urllib3.exceptions import InsecureRequestWarning
from django.core.cache import cache 
from django.conf import settings
import urllib.parse  # این خط رو اضافه کن!
import redis

# از 'rest_framework.response.Response' در فایل utils استفاده نکنید؛
# این شیء مخصوص ویوها است، نه توابع کمکی.

# نادیده گرفتن هشدار مربوط به verify=False
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

# فرض می‌کنیم کلید Redis و redis_client تعریف شده‌اند (این بخش در منطق API استفاده نمی‌شود)
# from .get_data_khakpour import redis_client #REDIS_TOKEN_KEY

API_BASE_URL = "https://api.khakpourgold.com/auth"

# تنظیمات پروکسی
# اگر 'USE_PROXY' در settings=True باشد، از پروکسی استفاده می‌شود.
PROXY_SETTINGS = {
    'http': 'http://127.0.0.1:10808',
    'https': 'http://127.0.0.1:10808',
} if getattr(settings, 'USE_PROXY', False) else None


def send_otp_request(mobile: str) -> dict:
    """
    مرحله ۱: درخواست ارسال کد تایید (OTP)
    """
    url = f"{API_BASE_URL}/send-otp"
    payload = {"mobile": mobile}
    headers = {"Content-Type": "application/json"}
    
    try:
        response = requests.post(
            url, 
            json=payload, 
            headers=headers,
            proxies=PROXY_SETTINGS,
            verify=False, # معادل --insecure
            timeout=15
        )
        
        # در صورت موفقیت (HTTP 204)
        if response.status_code == 204:
            return {
                'success': True, 
                'status_code': 200, 
                'message': 'OTP sent successfully.'
            } 
        
        # در صورت خطای ثبت نام (422)
        elif response.status_code == 422:
            try:
                error_data = response.json()
            except json.JSONDecodeError:
                error_data = {"message": response.text}
                
            return {
                'success': False, 
                'status_code': 422, 
                'data': error_data  # حاوی پیام فارسی خطای API
            } 
        
        # در صورت سایر خطاها
        else:
            try:
                error_data = response.json()
            except json.JSONDecodeError:
                error_data = response.text
                
            return {
                'success': False, 
                'status_code': response.status_code, 
                'data': {'message': f"Unexpected status code: {response.status_code}", 'details': error_data}
            }

    except requests.exceptions.RequestException as e:
        return {
            'success': False, 
            'status_code': 503, 
            'data': {'message': f"Network Error: {e}"}
        }








def get_token_request(mobile: str, code: str) -> dict:
    url = f"{API_BASE_URL}/token"
    payload = {"mobile": mobile, "code": code}

    try:
        response = requests.post(
            url,
            json=payload,
            headers={"Content-Type": "application/json"},
            verify=False,  # فقط در توسعه! در production حتماً True
            timeout=15
        )

        print(f"Status: {response.status_code}")
        print(f"Headers: {dict(response.headers)}")

        # مرحله 1: چک وضعیت
        if response.status_code not in [200, 204]:
            return {"error": "Login failed", "status": response.status_code}

        # مرحله 2: استخراج از کوکی
        cookie_token = None

        # روش 1: از response.cookies (پیشنهادی)
        if 'access_token_web' in response.cookies:
            cookie_token = response.cookies['access_token_web']
            print(f"Token found in cookie: {cookie_token[:50]}...")

        # روش 2: از هدر Set-Cookie (اگر روش 1 کار نکرد)
        if not cookie_token:
            set_cookie = response.headers.get('Set-Cookie', '')
            if 'access_token_web=' in set_cookie:
                # استخراج مقدار بعد از =
                start = set_cookie.find('access_token_web=') + 17
                end = set_cookie.find(';', start)
                if end == -1:
                    end = len(set_cookie)
                cookie_token = set_cookie[start:end]
                print(f"Token extracted from header: {cookie_token[:50]}...")

        # مرحله 3: اگر توکن پیدا نشد
        if not cookie_token:
            return {"error": "Token not found in cookies or body"}

        # مرحله 4: ذخیره در ردیس
        redis_cache = redis.Redis(host='redis-cache', port=6379, db=0, decode_responses=True)
        redis_cache.set("auto_order:access_token", cookie_token, ex=None)  # یا ex=60*60*24*30

        print(f"Token saved in Redis: {cookie_token[:50]}...")

        return {
            "token": cookie_token,
            "status_code": response.status_code,
            "source": "cookie"
        }

    except requests.RequestException as e:
        return {"error": f"Request failed: {str(e)}"}
    except Exception as e:
        return {"error": f"Unexpected error: {str(e)}"}