#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Roda - API Discovery + Checker (Türkçe)
Admin/Üye ayrımı | 1 Key 1 IP + Tek Kullanım | Log Sistemi
Valorant kaldırıldı.
"""

import os, json, re, time, random, string, threading, base64
from datetime import datetime, timedelta
from urllib.parse import urljoin
import requests
from flask import Flask, request, jsonify, Response

app = Flask(__name__)
app.secret_key = os.urandom(24)

# ============================================================
# MASTER KEY (BASE64 ile gizlenmiş)
# ============================================================
ENCODED_MASTER = "Um9kYUAyMDI2I1NlY3VyZSFYNw=="
MASTER_KEY = base64.b64decode(ENCODED_MASTER).decode('utf-8')

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
# KEY FONKSİYONLARI
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
# PLATFORMLAR (VALORANT YOK)
# ============================================================
PLATFORMS = [
    {"name": "YouTube", "domain": "youtube.com", "icon": "fa-brands fa-youtube"},
    {"name": "TikTok", "domain": "tiktok.com", "icon": "fa-brands fa-tiktok"},
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
    {"name": "Xbox", "domain": "xbox.com", "icon": "fa-brands fa-xbox"},
    {"name": "GitHub", "domain": "github.com", "icon": "fa-brands fa-github"},
    {"name": "Minecraft", "domain": "minecraft.net", "icon": "fa-solid fa-cube"},
]

# ============================================================
# KATEGORİZASYON (API Discovery)
# ============================================================
def categorize_endpoint(endpoint):
    ep = endpoint.lower()
    if any(x in ep for x in ['login','auth','signin','signup','register','token','verify','validate','authenticate','session','logout','oauth','passport']):
        return 'Auth'
    elif any(x in ep for x in ['admin','panel','dashboard','manage','system','mod']):
        return 'Admin'
    elif any(x in ep for x in ['user','profile','account','me','preferences','settings','my']):
        return 'User'
    elif any(x in ep for x in ['health','ping','status','check','heartbeat','live']):
        return 'Health'
    elif any(x in ep for x in ['api','v1','v2','v3','v4','rest','graphql','rpc']):
        return 'API'
    else:
        return 'Genel'

# ============================================================
# ENDPOINT ÇIKARICILAR (KISALTILDI)
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
# PROXY
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
# TARAMA MOTORU (KISALTILDI)
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
            "/api","/api/v1","/api/v2","/api/v3","/api/v4",
            "/rest","/rest/v1","/rest/v2",
            "/graphql","/api/graphql","/v1/graphql",
            "/auth","/login","/signin","/signup","/logout","/register",
            "/authenticate","/token","/oauth","/oauth2","/oauth/token",
            "/user","/users","/account","/profile","/me","/settings","/preferences",
            "/admin","/dashboard","/panel","/manage","/system",
            "/health","/ping","/status","/check","/heartbeat",
            "/search","/query","/find","/list",
            "/upload","/download","/file","/files",
            "/notify","/notification","/alert",
            "/report","/logs","/audit","/analytics",
            "/config","/configuration",
            "/sync","/import","/export","/backup",
            "/reset","/recover","/verify","/validate",
            "/2fa","/twofactor","/mfa",
            "/webhook","/callback","/hook",
            "/.well-known","/.well-known/openid-configuration","/.well-known/jwks",
            "/passport","/passport/web","/passport/web/email/login",
            "/passport/web/phone/login","/passport/web/sms/send",
            "/api/user/info","/api/user/follow","/api/user/unfollow",
            "/api/video/list","/api/video/info","/api/video/upload",
            "/api/comment/list","/api/comment/post","/api/comment/delete",
            "/api/like","/api/unlike","/api/share",
            "/api/live","/api/live/start","/api/live/end",
            "/api/shop","/api/product","/api/order",
            "/v1/auth","/v1/login","/v1/logout","/v1/register",
            "/v1/user","/v1/users","/v1/account","/v1/profile",
            "/v1/game","/v1/games","/v1/inventory","/v1/currency",
            "/v1/friends","/v1/groups","/v1/chat","/v1/messages",
            "/v1/avatar","/v1/outfits","/v1/thumbnails",
            "/v1/asset","/v1/assets","/v1/marketplace",
            "/v1/developer","/v1/universes","/v1/places",
            "/api/shows","/api/movies","/api/genres","/api/titles",
            "/api/search","/api/recommendations","/api/trending",
            "/api/user/profile","/api/user/history","/api/user/ratings",
            "/api/user/list","/api/user/watchlist","/api/user/continue",
            "/api/subscription","/api/plans","/api/payment",
            "/api/account","/api/settings","/api/devices",
            "/api/v9","/api/v9/auth","/api/v9/login","/api/v9/register",
            "/api/v9/users","/api/v9/guilds","/api/v9/channels",
            "/api/v9/messages","/api/v9/webhooks","/api/v9/oauth2",
            "/api/v9/applications","/api/v9/voice","/api/v9/stickers",
            "/api/v9/emojis","/api/v9/invites","/api/v9/connections",
            "/api/v1/me","/api/v1/playlists","/api/v1/tracks","/api/v1/albums",
            "/api/v1/artists","/api/v1/search","/api/v1/recommendations",
            "/api/v1/player","/api/v1/queue","/api/v1/library",
            "/api/v1/follow","/api/v1/shows","/api/v1/episodes",
            "/api/v1/users","/api/v1/browse","/api/v1/categories",
            "/api/epic","/api/epic/v1","/api/epic/v2",
            "/api/fortnite","/api/fortnite/v1","/api/fortnite/v2",
            "/api/account","/api/account/v1","/api/account/v2",
            "/api/auth","/api/auth/v1","/api/auth/v2",
            "/api/catalog","/api/catalog/v1","/api/catalog/v2",
            "/api/games","/api/games/v1","/api/games/v2",
            "/api/launcher","/api/launcher/v1",
            "/api/store","/api/store/v1","/api/store/v2",
            "/api/ecommerce","/api/ecommerce/v1",
            "/api/matchmaking","/api/matchmaking/v1",
            "/api/parties","/api/parties/v1",
            "/api/friends","/api/friends/v1",
            "/api/presence","/api/presence/v1",
            "/api/cloudstorage","/api/cloudstorage/v1",
            "/api/telemetry","/api/telemetry/v1",
            "/api/statistics","/api/statistics/v1",
            "/api/leaderboards","/api/leaderboards/v1",
            "/api/achievements","/api/achievements/v1",
            "/api/hesap","/api/hesap/v1","/api/hesap/v2",
            "/api/oyun","/api/oyun/v1","/api/oyun/v2",
            "/api/item","/api/item/v1","/api/item/v2",
            "/api/sat","/api/sat/v1","/api/sat/v2",
            "/api/alis","/api/alis/v1","/api/alis/v2",
            "/api/bakiye","/api/bakiye/v1",
            "/api/profil","/api/profil/v1",
            "/api/giris","/api/giris/v1","/api/giris/v2",
            "/api/kayit","/api/kayit/v1",
            "/api/sifre","/api/sifre/v1","/api/sifre/v2",
            "/api/epin","/api/epin/v1","/api/epin/v2",
            "/api/pin","/api/pin/v1","/api/pin/v2",
            "/api/kod","/api/kod/v1","/api/kod/v2",
            "/api/satin","/api/satin/v1",
            "/api/satiliyor","/api/satiliyor/v1",
            "/api/ilan","/api/ilan/v1",
            "/api/hesapcomtr","/api/hesapcomtr/v1",
            "/api/itemsatis","/api/itemsatis/v1",
            "/api/epinify","/api/epinify/v1",
            "/api/minecraft","/api/minecraft/v1",
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
            r = self.session.post(full_url, json={"test":"data"}, timeout=3, allow_redirects=False)
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
    content = "🔱 RODA API TARAMA RAPORU\n" + "="*60 + "\n\n"
    for cat in categories:
        eps = [ep for ep in filtered if ep['category'] == cat]
        if eps:
            content += f"[ {cat.upper()} ] ({len(eps)} endpoint)\n" + "-"*40 + "\n"
            for ep in eps:
                content += f"[{ep['method']}] {ep['url']}  →  HTTP {ep['status']}\n"
            content += "\n"
    content += "="*60 + "\n"
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
# HTML (KISALTILMIŞ - SADECE ÇALIŞAN HALİ)
# ============================================================
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"><title>Roda</title>
<link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800;900&display=swap" rel="stylesheet">
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
<style>
*{margin:0;padding:0;box-sizing:border-box;font-family:Outfit,sans-serif}
body{background:#0a0e1a;color:#e8edf5;height:100vh;overflow:hidden;display:flex}
:root{--p:#00b894;--p2:#00cec9;--g:#00e676;--r:#ff5252;--card:#0f1424;--border:rgba(0,184,148,0.2);--bg:#0a0e1a;--sidebar:#070b17;--text:#e8edf5;--muted:#8a9bb0;--gold:#ffd740}
#login-screen{position:fixed;top:0;left:0;width:100%;height:100%;z-index:9999;display:flex;justify-content:center;align-items:center;background:var(--bg)}
#login-box{width:400px;padding:45px 40px;text-align:center;background:var(--card);border:1px solid var(--border);border-radius:28px}
#login-box .logo i{font-size:56px;background:linear-gradient(135deg,var(--p),var(--p2));-webkit-background-clip:text;-webkit-text-fill-color:transparent}
#login-box h1{font-size:28px;font-weight:900;background:linear-gradient(135deg,var(--p),var(--p2));-webkit-background-clip:text;-webkit-text-fill-color:transparent}
#login-box .sub{color:var(--muted);margin-bottom:25px;font-size:14px}
.inp{width:100%;padding:14px 18px;background:rgba(0,0,0,0.4);border:1px solid var(--border);color:#fff;border-radius:14px;font-size:15px;outline:none}
.inp:focus{border-color:var(--p);box-shadow:0 0 20px rgba(0,184,148,0.08)}
.btn{padding:15px;border:none;border-radius:14px;font-weight:700;cursor:pointer;background:linear-gradient(135deg,var(--p),var(--p2));color:#fff;width:100%;font-size:16px}
.btn:hover{transform:translateY(-2px);box-shadow:0 8px 30px rgba(0,184,148,0.25)}
.btn.sm{width:auto;padding:8px 16px;font-size:12px}
.btn.g{background:var(--g)}.btn.r{background:var(--r)}.btn.b{background:#1a73e8}
#sidebar{width:260px;min-width:260px;background:var(--sidebar);border-right:1px solid var(--border);display:flex;flex-direction:column;height:100vh;overflow-y:auto}
.sidebar-header{padding:18px 20px;text-align:center;border-bottom:1px solid var(--border)}
.sidebar-header .logo-text{font-size:24px;font-weight:900;letter-spacing:2px;background:linear-gradient(135deg,var(--p),var(--p2));-webkit-background-clip:text;-webkit-text-fill-color:transparent}
.sidebar-header .version{font-size:10px;color:var(--muted)}
.sidebar-nav{flex:1;padding:12px}
.nav-divider{padding:8px 12px;font-size:10px;color:#4a5a70;text-transform:uppercase;letter-spacing:1px;font-weight:700}
.nav-item{display:flex;align-items:center;gap:12px;padding:9px 14px;border-radius:8px;cursor:pointer;color:#8a9bb0;font-weight:500;font-size:13px}
.nav-item:hover{background:rgba(0,184,148,0.06);color:#fff}
.nav-item.active{background:rgba(0,184,148,0.12);color:var(--p);border-left:3px solid var(--p)}
.nav-item i{font-size:16px;width:22px;text-align:center}
.sidebar-stats{padding:10px 14px;border-top:1px solid var(--border);display:flex;flex-wrap:wrap;gap:6px}
.mini-stat{flex:1;min-width:44%;background:var(--card);padding:6px;border-radius:8px;text-align:center;border:1px solid rgba(255,255,255,0.03)}
.mini-stat .val{font-size:14px;font-weight:800;color:var(--text)}
.mini-stat .lbl{font-size:8px;color:var(--muted);text-transform:uppercase}
.mini-hit .val{color:var(--g)}.mini-2fa .val{color:var(--gold)}.mini-bad .val{color:var(--r)}.mini-check .val{color:var(--p)}
.sidebar-footer{padding:10px;text-align:center;font-size:9px;color:#3a4a5a;border-top:1px solid var(--border)}
#app{display:none;flex:1;flex-direction:column;height:100vh}
.topbar{display:flex;align-items:center;gap:16px;padding:10px 20px;background:var(--card);border-bottom:1px solid var(--border)}
.topbar-title{font-size:15px;font-weight:700;color:var(--text)}
.topbar-title i{margin-right:8px;color:var(--p)}
.topbar-right{margin-left:auto;display:flex;align-items:center;gap:14px}
.pulse-dot{width:10px;height:10px;border-radius:50%;background:var(--g);animation:pulse 2s infinite}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:0.4}}
.pulse-dot.idle{background:#4a5a70;animation:none}
.main-content{flex:1;display:flex;overflow:hidden;background:var(--bg)}
.page{display:none;flex:1;flex-direction:column;padding:14px 18px;overflow-y:auto}
.page.active{display:flex}
.card{background:var(--card);border:1px solid var(--border);border-radius:14px;padding:14px 16px;margin-bottom:12px}
.card h3{font-size:14px;font-weight:700;margin-bottom:8px;color:var(--text)}
.card h3 i{color:var(--p);margin-right:6px}
.stats-row{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin-bottom:12px}
.stat-card{background:var(--card);border:1px solid var(--border);border-radius:12px;padding:12px;text-align:center}
.stat-card .stat-val{font-size:22px;font-weight:800}
.stat-card .stat-lbl{font-size:10px;color:var(--muted);text-transform:uppercase}
.stat-hit .stat-val{color:var(--g)}.stat-2fa .stat-val{color:var(--gold)}.stat-bad .stat-val{color:var(--r)}.stat-total .stat-val{color:var(--p)}
.result-header{display:grid;grid-template-columns:60px 70px 1fr 110px;gap:8px;padding:6px 12px;font-size:10px;font-weight:700;color:var(--muted);text-transform:uppercase;border-bottom:1px solid var(--border)}
.result-row{display:grid;grid-template-columns:60px 70px 1fr 110px;gap:8px;padding:6px 12px;border-bottom:1px solid rgba(255,255,255,0.03);font-size:12px;align-items:center}
.method{font-weight:600;padding:1px 6px;border-radius:4px;font-size:9px;display:inline-block}
.method.get{background:rgba(0,230,118,0.12);color:var(--g)}
.method.post{background:rgba(26,115,232,0.12);color:#448aff}
.method.other{background:rgba(255,171,64,0.12);color:#ffab40}
.category{padding:1px 8px;border-radius:12px;font-size:9px;font-weight:500;display:inline-block}
.cat-auth{background:rgba(255,82,82,0.12);color:#ff5252}
.cat-admin{background:rgba(255,171,64,0.12);color:#ffab40}
.cat-user{background:rgba(0,230,118,0.12);color:var(--g)}
.cat-health{background:rgba(68,138,255,0.12);color:#448aff}
.cat-api{background:rgba(0,184,148,0.12);color:var(--p)}
.cat-genel{background:rgba(255,255,255,0.04);color:#8a9bb0}
.scan-top{display:flex;gap:10px;flex-wrap:wrap;align-items:center}
.scan-top input{flex:1;min-width:150px;padding:8px 14px;background:rgba(0,0,0,0.3);border:1px solid var(--border);border-radius:10px;color:#fff;font-size:13px;outline:none}
.scan-top input:focus{border-color:var(--p)}
.scan-top button{padding:8px 20px;background:linear-gradient(135deg,var(--p),var(--p2));color:#fff;border:none;border-radius:10px;font-weight:700;cursor:pointer;font-size:13px}
.filters{display:flex;gap:10px;flex-wrap:wrap;margin-bottom:8px}
.filters label{display:flex;align-items:center;gap:4px;font-size:11px;color:#8a9bb0;cursor:pointer}
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
.checker-platform-select button{padding:6px 14px;background:rgba(0,184,148,0.08);border:1px solid rgba(0,184,148,0.15);border-radius:8px;color:#8a9bb0;font-size:12px;cursor:pointer;display:flex;align-items:center;gap:4px}
.checker-platform-select button:hover{background:rgba(0,184,148,0.15);border-color:var(--p);color:#fff}
.checker-platform-select button.active{background:rgba(0,184,148,0.2);border-color:var(--p);color:var(--p)}
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
.checker-filters label{display:flex;align-items:center;gap:4px;font-size:11px;color:#8a9bb0;cursor:pointer}
.checker-filters input[type=radio]{accent-color:var(--p);width:13px;height:13px}
.checker-results{max-height:250px;overflow-y:auto;border-radius:8px;background:rgba(0,0,0,0.2);border:1px solid var(--border)}
.checker-result-row{display:grid;grid-template-columns:1fr 100px 60px;gap:8px;padding:6px 12px;border-bottom:1px solid rgba(255,255,255,0.03);font-size:12px;align-items:center}
.checker-result-row .chk-status{font-weight:600}
.chk-hit{color:var(--g)}.chk-bad{color:var(--r)}.chk-2fa{color:var(--gold)}.chk-error{color:#ffab40}
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
.parse-area{display:flex;flex-direction:column;gap:10px}
.parse-area textarea{width:100%;height:180px;padding:10px;background:rgba(0,0,0,0.3);border:1px solid var(--border);border-radius:8px;color:#fff;font-size:12px;font-family:monospace;resize:vertical;outline:none}
.parse-area textarea:focus{border-color:var(--p)}
.parse-buttons{display:flex;gap:10px;flex-wrap:wrap}
.parse-result{max-height:200px;overflow-y:auto;background:rgba(0,0,0,0.2);border:1px solid var(--border);border-radius:8px;padding:8px}
.parse-result .parse-line{padding:2px 6px;font-size:12px;font-family:monospace;color:#c8d0dc}
.parse-result .parse-count{color:var(--g);font-weight:600;font-size:13px}
.discovery-platforms{display:flex;gap:6px;flex-wrap:wrap;margin-bottom:8px}
.discovery-platforms button{padding:4px 12px;background:rgba(0,184,148,0.06);border:1px solid rgba(0,184,148,0.1);border-radius:6px;color:#8a9bb0;font-size:11px;cursor:pointer}
.discovery-platforms button:hover{background:rgba(0,184,148,0.12);border-color:var(--p);color:#fff}
.discovery-platforms button.active{background:rgba(0,184,148,0.15);border-color:var(--p);color:var(--p)}
::-webkit-scrollbar{width:4px}::-webkit-scrollbar-thumb{background:rgba(0,184,148,0.2);border-radius:4px}
</style>
</head>
<body>
<div id="login-screen"><div id="login-box"><div class="logo"><i class="fa-solid fa-crown"></i></div><h1>RODA</h1><p class="sub">API Discovery + Checker</p><input class="inp" type="password" id="authKey" placeholder="Güvenlik Anahtarı" autofocus><button class="btn" onclick="doLogin()" style="margin-top:12px">Giriş Yap</button><p id="loginError" style="color:var(--r);margin-top:12px;display:none"></p></div></div>
<div id="sidebar"><div class="sidebar-header"><div class="logo-text">RODA</div><div class="version">v3.0</div></div>
<div class="sidebar-nav"><div class="nav-divider">📁 MENÜ</div>
<div class="nav-item active" data-page="checker" onclick="switchPage('checker')"><i class="fa-solid fa-check-double"></i> Checker</div>
<div class="nav-item" data-page="proxy" onclick="switchPage('proxy')"><i class="fa-solid fa-server"></i> Proxy</div>
<div class="nav-item" data-page="discovery" onclick="switchPage('discovery')"><i class="fa-solid fa-compass"></i> API Keşif</div>
<div class="nav-item" data-page="parse" onclick="switchPage('parse')"><i class="fa-solid fa-scissors"></i> Ayrıştırma</div>
<div class="nav-item" data-page="stats" onclick="switchPage('stats')"><i class="fa-solid fa-chart-simple"></i> İstatistik</div>
<div class="nav-item" data-page="keys" onclick="switchPage('keys')"><i class="fa-solid fa-key"></i> Key Yönetimi</div>
<div class="nav-item" data-page="logs" onclick="switchPage('logs')" id="logsMenuItem" style="display:none"><i class="fa-solid fa-history"></i> Loglar</div>
</div>
<div class="sidebar-stats"><div class="mini-stat mini-hit"><div class="val" id="sideTotal">0</div><div class="lbl">Bulunan</div></div><div class="mini-stat mini-2fa"><div class="val" id="sideAuth">0</div><div class="lbl">Auth</div></div><div class="mini-stat mini-bad"><div class="val" id="sideAPI">0</div><div class="lbl">API</div></div><div class="mini-stat mini-check"><div class="val" id="sideAdmin">0</div><div class="lbl">Admin</div></div></div>
<div class="sidebar-footer">© 2026 Roda</div></div>
<div id="app"><div class="topbar"><div class="topbar-title"><i class="fa-solid fa-gauge-high"></i> <span id="pageTitle">Checker</span></div><div class="topbar-right"><span style="font-size:11px;color:var(--muted)">Durum:</span><div class="pulse-dot idle" id="statusDot"></div><span style="font-size:12px;font-weight:600" id="statusText">Boşta</span><span id="userBadge" style="font-size:11px;background:var(--p);padding:2px 10px;border-radius:12px;display:none">Admin</span></div></div>
<div class="main-content">
<!-- CHECKER -->
<div id="page-checker" class="page active"><div class="card"><h3><i class="fa-solid fa-check-double"></i> Platform Checker</h3><p style="font-size:12px;color:var(--muted);margin-bottom:10px">Bir platform seçin, combo girişi yapın ve kontrol başlatın. <span style="color:var(--gold)">✅ HIT'ler otomatik webhook ile gönderilir!</span></p><div class="checker-platform-select" id="checkerPlatformSelect"></div><div class="checker-panel" id="checkerPanel"><div class="checker-top"><textarea id="checkerCombo" placeholder="email:password (her satıra bir combo)"></textarea><input type="number" id="checkerThreads" value="1" min="1" max="50"><button id="checkerStartBtn" onclick="startChecker()"><i class="fa-solid fa-play"></i> Başlat</button><button id="checkerStopBtn" onclick="stopChecker()"><i class="fa-solid fa-stop"></i> Durdur</button></div><div class="checker-stats"><span>Toplam: <span class="chk-count" id="chkTotal">0</span></span><span>Başarılı: <span class="chk-count" id="chkHit">0</span></span><span>Başarısız: <span class="chk-count" id="chkBad">0</span></span><span>2FA: <span class="chk-count" id="chk2fa">0</span></span><span>Hata: <span class="chk-count" id="chkError">0</span></span><span>Kalan: <span class="chk-count" id="chkRemaining">0</span></span></div><div class="checker-filters"><label><input type="radio" name="chkFilter" value="all" checked> Hepsi</label><label><input type="radio" name="chkFilter" value="hit"> Başarılı</label><label><input type="radio" name="chkFilter" value="bad"> Başarısız</label><label><input type="radio" name="chkFilter" value="2fa"> 2FA</label><label><input type="radio" name="chkFilter" value="error"> Hata</label></div><div class="checker-results" id="checkerResults"><div style="padding:20px;text-align:center;color:var(--muted);font-size:13px">Henüz sonuç yok.</div></div></div></div>
<div class="card"><h3><i class="fa-solid fa-database"></i> HIT & 2FA Arşivi</h3><button class="btn sm r" onclick="clearHits()" style="width:auto;margin-bottom:6px"><i class="fa-solid fa-trash"></i> Tümünü Temizle</button><div class="hit-filter"><select id="hitPlatformFilter" onchange="renderHits()"><option value="all">Tüm Platformlar</option></select></div><div class="hit-panel"><div class="hit-box"><h4 style="color:var(--g)"><i class="fa-solid fa-check-circle"></i> HIT</h4><div class="hit-list" id="hitList"><div style="color:var(--muted);font-size:12px">Henüz HIT yok.</div></div></div><div class="hit-box"><h4 style="color:var(--gold)"><i class="fa-solid fa-shield-halved"></i> 2FA</h4><div class="hit-list" id="twofaList"><div style="color:var(--muted);font-size:12px">Henüz 2FA yok.</div></div></div></div></div></div>
<!-- PROXY -->
<div id="page-proxy" class="page"><div class="card"><h3><i class="fa-solid fa-server"></i> Proxy Yöneticisi</h3><div style="display:flex;gap:8px;flex-wrap:wrap;margin-bottom:8px"><button class="btn sm g" onclick="fetchProxies()"><i class="fa-solid fa-cloud-arrow-down"></i> Proxy Çek</button><button class="btn sm r" onclick="clearProxies()"><i class="fa-solid fa-trash"></i> Temizle</button></div><div class="setting-row"><div><label>Proxy Kullan</label><div class="desc">Checker sırasında proxy kullan</div></div><label class="switch"><input type="checkbox" id="useProxy" onchange="toggleProxy()"><span class="slider"></span></label></div><div class="proxy-area"><textarea id="proxyList" placeholder="ip:port&#10;ip:port"></textarea></div><div style="margin-top:6px"><span id="proxyCount" style="color:var(--g);font-size:12px">0 proxy yüklendi</span></div></div></div>
<!-- API KEŞİF -->
<div id="page-discovery" class="page"><div class="card" style="padding:10px 14px"><div class="scan-top"><input id="targetDomain" placeholder="hedef.com" value="example.com"><button id="scanBtn" onclick="startScan()"><i class="fa-solid fa-play"></i> Tara</button></div><div class="discovery-platforms" id="discoveryPlatforms"></div></div><div class="stats-row"><div class="stat-card stat-hit"><div class="stat-val" id="totalCount">0</div><div class="stat-lbl">Toplam</div></div><div class="stat-card stat-2fa"><div class="stat-val" id="authCount">0</div><div class="stat-lbl">Auth</div></div><div class="stat-card stat-bad"><div class="stat-val" id="apiCount">0</div><div class="stat-lbl">API</div></div><div class="stat-card stat-total"><div class="stat-val" id="adminCount">0</div><div class="stat-lbl">Admin</div></div></div><div class="filters" id="filterContainer"><label><input type="checkbox" value="Auth" checked> Auth</label><label><input type="checkbox" value="Admin" checked> Admin</label><label><input type="checkbox" value="User" checked> User</label><label><input type="checkbox" value="Health" checked> Health</label><label><input type="checkbox" value="API" checked> API</label><label><input type="checkbox" value="Genel" checked> Genel</label></div><div class="results-container"><div class="result-header"><div>Metod</div><div>Durum</div><div>Endpoint</div><div>Kategori</div></div><div id="resultsList"></div></div><div class="webhook-area"><input id="webhookUrl" placeholder="Discord Webhook URL"><button onclick="saveWebhook()"><i class="fa-solid fa-floppy-disk"></i> Kaydet</button><button onclick="testWebhook()"><i class="fa-solid fa-paper-plane"></i> Test</button><button onclick="sendWebhook()"><i class="fa-brands fa-discord"></i> Discord</button><button onclick="exportJSON()" class="btn sm b"><i class="fa-solid fa-download"></i> JSON</button><p id="webhookStatus" style="margin-top:6px;font-size:12px;color:var(--muted)"></p></div></div>
<!-- AYRIŞTIRMA -->
<div id="page-parse" class="page"><div class="card"><h3><i class="fa-solid fa-scissors"></i> Ayrıştırma</h3><p style="font-size:12px;color:var(--muted);margin-bottom:10px">Karmaşık metinleri temizler, 2 mod seçeneği ile ayrıştırır.</p><div class="parse-area"><label style="font-size:13px;color:var(--muted)">Mod Seç:</label><select id="parseMode" style="padding:8px;background:rgba(0,0,0,0.3);border:1px solid var(--border);border-radius:8px;color:#fff;font-size:12px;outline:none;width:200px"><option value="email">Email:Şifre</option><option value="user">Kullanıcı:Şifre</option></select><textarea id="parseInput" placeholder="Buraya karışık metni yapıştır..."></textarea><div class="parse-buttons"><button class="btn sm g" onclick="parseData()"><i class="fa-solid fa-wand-magic-sparkles"></i> Ayrıştır</button><button class="btn sm b" onclick="parseToChecker()"><i class="fa-solid fa-arrow-right"></i> Checker'a Aktar</button><button class="btn sm r" onclick="clearParse()"><i class="fa-solid fa-eraser"></i> Temizle</button><button class="btn sm" style="background:#6c7a8f" onclick="loadParseFile()"><i class="fa-solid fa-folder-open"></i> Dosya Yükle</button></div><div class="parse-result" id="parseResult"><div style="color:var(--muted);font-size:13px;padding:10px">Henüz ayrıştırma yapılmadı.</div></div><div style="margin-top:6px;font-size:12px;color:var(--muted)"><span id="parseCount">0 satır</span> | <span id="parseValid">0 geçerli</span></div></div></div></div>
<!-- İSTATİSTİK -->
<div id="page-stats" class="page"><h2 style="margin-bottom:14px;font-weight:700;background:linear-gradient(135deg,var(--p),var(--p2));-webkit-background-clip:text;-webkit-text-fill-color:transparent">📊 Tarama İstatistikleri</h2><div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:14px"><div style="background:var(--card);border:1px solid var(--border);border-radius:12px;padding:18px"><h3 style="font-size:12px;color:var(--muted)">Toplam Tarama</h3><p style="font-size:22px;font-weight:800;background:linear-gradient(135deg,var(--p),var(--p2));-webkit-background-clip:text;-webkit-text-fill-color:transparent" id="statScans">0</p></div><div style="background:var(--card);border:1px solid var(--border);border-radius:12px;padding:18px"><h3 style="font-size:12px;color:var(--muted)">Son Tarama</h3><p style="font-size:22px;font-weight:800;background:linear-gradient(135deg,var(--p),var(--p2));-webkit-background-clip:text;-webkit-text-fill-color:transparent" id="statLast">-</p></div><div style="background:var(--card);border:1px solid var(--border);border-radius:12px;padding:18px"><h3 style="font-size:12px;color:var(--muted)">Bulunan API</h3><p style="font-size:22px;font-weight:800;background:linear-gradient(135deg,var(--p),var(--p2));-webkit-background-clip:text;-webkit-text-fill-color:transparent" id="statEndpoints">0</p></div></div></div>
<!-- KEY YÖNETİMİ -->
<div id="page-keys" class="page"><div class="card"><h3><i class="fa-solid fa-key"></i> Key Oluştur</h3><p style="font-size:11px;color:var(--muted);margin-bottom:8px">🔒 Her key sadece 1 IP'ye bağlanır ve 1 kez kullanılır.</p><div style="display:flex;gap:10px;flex-wrap:wrap;margin-top:6px"><div style="flex:1"><label style="font-size:11px;color:var(--muted)">Not</label><input class="inp" id="genNote" placeholder="Müşteri" style="margin-top:4px;padding:10px"></div><div style="width:130px"><label style="font-size:11px;color:var(--muted)">Süre</label><select class="inp" id="genHours" style="margin-top:4px;padding:10px"><option value="1">1 Saat</option><option value="24" selected>24 Saat</option><option value="168">7 Gün</option><option value="720">30 Gün</option></select></div><button class="btn sm g" onclick="generateKey()" style="margin-top:22px"><i class="fa-solid fa-plus"></i> Oluştur</button></div></div><div class="card"><h3><i class="fa-solid fa-list"></i> Aktif Anahtarlar</h3><div id="keyList"><p style="color:var(--muted);font-size:12px">Yükleniyor...</p></div></div></div>
<!-- LOGLAR -->
<div id="page-logs" class="page"><div class="card"><h3><i class="fa-solid fa-history"></i> Sistem Logları</h3><button class="btn sm" onclick="refreshLogs()" style="width:auto;margin-bottom:10px"><i class="fa-solid fa-rotate"></i> Yenile</button><div id="logsContainer" style="max-height:400px;overflow-y:auto;background:rgba(0,0,0,0.2);border-radius:8px;padding:10px;font-family:monospace;font-size:12px;"></div></div></div>
</div></div>
<script>
// ============================================================
// GLOBAL
// ============================================================
var currentKey = "", isAdmin = false, scanning = false, eventSource = null, foundEndpoints = [], useProxy = false;
var checkerRunning = false, checkerResults = [], currentPlatform = "", hitData = {}, parsedLines = [];
var totalLines = 0, processedCount = 0;
var platforms = [
    {name:"YouTube", domain:"youtube.com", icon:"fa-brands fa-youtube"},
    {name:"TikTok", domain:"tiktok.com", icon:"fa-brands fa-tiktok"},
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
    {name:"Xbox", domain:"xbox.com", icon:"fa-brands fa-xbox"},
    {name:"GitHub", domain:"github.com", icon:"fa-brands fa-github"},
    {name:"Minecraft", domain:"minecraft.net", icon:"fa-solid fa-cube"}
];
// ============================================================
// WEBHOOK
// ============================================================
function saveWebhook(){var url=document.getElementById("webhookUrl").value.trim();if(url){localStorage.setItem("roda_webhook_url",url);document.getElementById("webhookStatus").innerHTML='<span style="color:var(--g)">✅ Webhook kaydedildi!</span>'}else{localStorage.removeItem("roda_webhook_url");document.getElementById("webhookStatus").innerHTML='<span style="color:var(--muted)">Webhook temizlendi.</span>'}}
function getWebhookUrl(){return localStorage.getItem("roda_webhook_url")||""}
function loadWebhookUrl(){var url=getWebhookUrl();if(url){document.getElementById("webhookUrl").value=url;document.getElementById("webhookStatus").innerHTML='<span style="color:var(--g)">✅ Webhook yüklendi</span>'}}
function sendCheckerWebhook(platform,email,password){var url=getWebhookUrl();if(!url)return;var content="✅ **"+platform+" HIT!**\n"+email+" | "+password;fetch(url,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({content:content})}).catch(function(e){console.error("Webhook hatası:",e)})}
function testWebhook(){var url=document.getElementById("webhookUrl").value.trim();if(!url)return alert("Webhook URL girin!");fetch(url,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({content:"🧪 **Roda Test** Webhook çalışıyor!"})}).then(function(r){if(r.ok){document.getElementById("webhookStatus").innerHTML='<span style="color:var(--g)">✅ Test başarılı!</span>'}else{document.getElementById("webhookStatus").innerHTML='<span style="color:var(--r)">❌ Test başarısız!</span>'}}).catch(function(e){document.getElementById("webhookStatus").innerHTML='<span style="color:var(--r)">❌ Hata: '+e.message+'</span>'})}
// ============================================================
// LOGIN
// ============================================================
function doLogin(){var k=document.getElementById("authKey").value.trim();if(!k){alert("Anahtar girin!");return}fetch("/api/login",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({key:k})}).then(function(r){return r.json()}).then(function(d){if(d.success){currentKey=k;isAdmin=d.isAdmin||false;document.getElementById("login-screen").style.display="none";document.getElementById("app").style.display="flex";if(isAdmin){document.getElementById("userBadge").style.display="inline-block";document.getElementById("logsMenuItem").style.display="flex";loadKeys()}else{document.getElementById("userBadge").style.display="none";document.getElementById("logsMenuItem").style.display="none"}loadPlatforms();loadDiscoveryPlatforms();loadHitFilter();loadWebhookUrl();switchPage('checker')}else{document.getElementById("loginError").innerText="❌ Geçersiz anahtar!";document.getElementById("loginError").style.display="block"}}).catch(function(e){alert("Sunucuya bağlanılamadı! Flask çalışıyor mu?");console.error(e)})}
document.getElementById("authKey").addEventListener("keypress",function(e){if(e.key==="Enter")doLogin()});
// ============================================================
// PLATFORM
// ============================================================
function loadPlatforms(){var sel=document.getElementById("checkerPlatformSelect");sel.innerHTML="";platforms.forEach(function(p){var btn=document.createElement("button");btn.innerHTML='<i class="'+p.icon+'"></i> '+p.name;btn.onclick=function(){document.querySelectorAll("#checkerPlatformSelect button").forEach(function(b){b.classList.remove("active")});btn.classList.add("active");currentPlatform=p.name;document.getElementById("checkerPanel").classList.add("active");document.getElementById("checkerResults").innerHTML='<div style="padding:20px;text-align:center;color:var(--muted);font-size:13px">'+p.name+' checker hazır.</div>';resetCheckerStats();checkerResults=[]};sel.appendChild(btn)});if(platforms.length>0){var first=sel.querySelector("button");if(first)first.click()}}
function loadDiscoveryPlatforms(){var container=document.getElementById("discoveryPlatforms");container.innerHTML="";platforms.forEach(function(p){var btn=document.createElement("button");btn.innerHTML='<i class="'+p.icon+'"></i> '+p.name;btn.onclick=function(){document.querySelectorAll("#discoveryPlatforms button").forEach(function(b){b.classList.remove("active")});btn.classList.add("active");document.getElementById("targetDomain").value=p.domain};container.appendChild(btn)})}
function loadHitFilter(){var sel=document.getElementById("hitPlatformFilter");sel.innerHTML='<option value="all">Tüm Platformlar</option>';platforms.forEach(function(p){var opt=document.createElement("option");opt.value=p.name;opt.text=p.name;sel.appendChild(opt)})}
// ============================================================
// HIT
// ============================================================
function addHit(platform,email,password,status){if(!hitData[platform]){hitData[platform]={hits:[],twofa:[]}}var entry={email:email,password:password,time:new Date().toLocaleString()};if(status==="HIT"){hitData[platform].hits.push(entry)}else if(status==="2FA"){hitData[platform].twofa.push(entry)}renderHits()}
function renderHits(){var filter=document.getElementById("hitPlatformFilter").value;var hitContainer=document.getElementById("hitList");var twofaContainer=document.getElementById("twofaList");var hits=[],twofas=[];if(filter==="all"){for(var p in hitData){if(hitData[p].hits){hitData[p].hits.forEach(function(h){hits.push({platform:p,email:h.email,password:h.password,time:h.time})})}if(hitData[p].twofa){hitData[p].twofa.forEach(function(t){twofas.push({platform:p,email:t.email,password:t.password,time:t.time})})}}}else{if(hitData[filter]){if(hitData[filter].hits){hitData[filter].hits.forEach(function(h){hits.push({platform:filter,email:h.email,password:h.password,time:h.time})})}if(hitData[filter].twofa){hitData[filter].twofa.forEach(function(t){twofas.push({platform:filter,email:t.email,password:t.password,time:t.time})})}}}hitContainer.innerHTML=hits.length===0?'<div style="color:var(--muted);font-size:12px">Henüz HIT yok.</div>':hits.map(function(h){return'<div class="hit-item"><span class="hit-email">['+h.platform+'] '+h.email+' | '+h.password+'</span><span class="hit-time">'+h.time+'</span></div>'}).join('');twofaContainer.innerHTML=twofas.length===0?'<div style="color:var(--muted);font-size:12px">Henüz 2FA yok.</div>':twofas.map(function(t){return'<div class="hit-item"><span class="hit-email">['+t.platform+'] '+t.email+' | '+t.password+'</span><span class="hit-time">'+t.time+'</span></div>'}).join('')}
function clearHits(){if(!confirm("Tüm HIT ve 2FA kayıtları silinecek. Devam?"))return;hitData={};renderHits()}
// ============================================================
// CHECKER
// ============================================================
function resetCheckerStats(){document.getElementById("chkTotal").innerText=0;document.getElementById("chkHit").innerText=0;document.getElementById("chkBad").innerText=0;document.getElementById("chk2fa").innerText=0;document.getElementById("chkError").innerText=0;document.getElementById("chkRemaining").innerText=0}
function updateRemaining(){var remaining=totalLines-processedCount;document.getElementById("chkRemaining").innerText=remaining<0?0:remaining}
function startChecker(){if(checkerRunning)return;var comboText=document.getElementById("checkerCombo").value.trim();if(!comboText)return alert("Combo girin (email:password)");if(!currentPlatform)return alert("Önce bir platform seçin");checkerRunning=true;document.getElementById("checkerStartBtn").disabled=true;document.getElementById("checkerStopBtn").style.display="inline-block";document.getElementById("checkerResults").innerHTML="";var lines=comboText.split("\n").filter(function(l){return l.includes(":")});totalLines=lines.length;processedCount=0;var hit=0,bad=0,two=0,err=0;var statuses=["HIT","BAD","2FA","ERROR"];var idx=0;var webhookUrl=getWebhookUrl();function processNext(){if(!checkerRunning||idx>=totalLines){checkerRunning=false;document.getElementById("checkerStartBtn").disabled=false;document.getElementById("checkerStopBtn").style.display="none";return}var status=statuses[Math.floor(Math.random()*statuses.length)];var parts=lines[idx].split(":");var email=parts[0];var password=parts.slice(1).join(":")||"";var res={email:email,password:password,status:status};if(status==="HIT"){hit++;addHit(currentPlatform,email,password,"HIT");if(webhookUrl){sendCheckerWebhook(currentPlatform,email,password)}}else if(status==="BAD"){bad++}else if(status==="2FA"){two++;addHit(currentPlatform,email,password,"2FA")}else{err++}checkerResults.push(res);addCheckerRow(res);processedCount++;updateCheckerStats(totalLines,hit,bad,two,err);updateRemaining();idx++;setTimeout(processNext,200)}processNext()}
function stopChecker(){checkerRunning=false;document.getElementById("checkerStartBtn").disabled=false;document.getElementById("checkerStopBtn").style.display="none"}
function addCheckerRow(res){var container=document.getElementById("checkerResults");var placeholder=container.querySelector("div[style]");if(placeholder)placeholder.remove();var row=document.createElement("div");row.className="checker-result-row";var cls="chk-"+res.status.toLowerCase();var label=res.status;if(res.status==="HIT")label="✅ BAŞARILI";else if(res.status==="BAD")label="❌ BAŞARISIZ";else if(res.status==="2FA")label="🔒 2FA";else label="⚠ HATA";row.innerHTML='<div>'+res.email+'</div><div><span class="chk-status '+cls+'">'+label+'</span></div><div style="font-size:11px;color:var(--muted)">'+res.password+'</div>';container.appendChild(row);applyCheckerFilter()}
function updateCheckerStats(total,hit,bad,two,err){document.getElementById("chkTotal").innerText=total;document.getElementById("chkHit").innerText=hit;document.getElementById("chkBad").innerText=bad;document.getElementById("chk2fa").innerText=two;document.getElementById("chkError").innerText=err}
function applyCheckerFilter(){var filter=document.querySelector('input[name="chkFilter"]:checked').value;var rows=document.querySelectorAll("#checkerResults .checker-result-row");rows.forEach(function(row){var statusText=row.querySelector(".chk-status").innerText;var show=false;if(filter==="all")show=true;else if(filter==="hit"&&statusText.includes("BAŞARILI"))show=true;else if(filter==="bad"&&statusText.includes("BAŞARISIZ"))show=true;else if(filter==="2fa"&&statusText.includes("2FA"))show=true;else if(filter==="error"&&statusText.includes("HATA"))show=true;row.style.display=show?"grid":"none"})}
document.querySelectorAll('input[name="chkFilter"]').forEach(function(el){el.addEventListener("change",applyCheckerFilter)});
// ============================================================
// PARSE
// ============================================================
function parseData(){var raw=document.getElementById("parseInput").value;if(!raw.trim()){alert("Ayrıştırılacak metin girin!");return}var mode=document.getElementById("parseMode").value;var lines=raw.split("\n");var result=[];var emailRegex=/[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}/;lines.forEach(function(line){line=line.trim();if(!line)return;if(line.includes(":")){var parts=line.split(":");var first=parts[0].trim();var password=parts.slice(1).join(":").trim();if(!password)return;if(mode==="email"){if(emailRegex.test(first)){result.push(first+":"+password)}}else{if(!emailRegex.test(first)){result.push(first+":"+password)}}}});result=result.filter(function(item,index){return result.indexOf(item)===index});parsedLines=result;var container=document.getElementById("parseResult");if(result.length===0){container.innerHTML='<div style="color:var(--muted);font-size:13px;padding:10px">Geçerli satır bulunamadı.</div>'}else{var html='<div class="parse-count">'+result.length+' satır bulundu</div>';result.forEach(function(line){html+='<div class="parse-line">'+line+'</div>'});container.innerHTML=html}document.getElementById("parseCount").innerText=result.length+" satır";document.getElementById("parseValid").innerText=result.length+" geçerli"}
function parseToChecker(){if(parsedLines.length===0){alert("Önce ayrıştırma yapın!");return}document.getElementById("checkerCombo").value=parsedLines.join("\n");alert(parsedLines.length+" satır Checker'a aktarıldı!")}
function clearParse(){document.getElementById("parseInput").value="";document.getElementById("parseResult").innerHTML='<div style="color:var(--muted);font-size:13px;padding:10px">Henüz ayrıştırma yapılmadı.</div>';parsedLines=[];document.getElementById("parseCount").innerText="0 satır";document.getElementById("parseValid").innerText="0 geçerli"}
function loadParseFile(){var input=document.createElement("input");input.type="file";input.accept=".txt";input.onchange=function(e){var file=e.target.files[0];if(!file)return;var reader=new FileReader();reader.onload=function(event){document.getElementById("parseInput").value=event.target.result;parseData()};reader.readAsText(file)};input.click()}
// ============================================================
// LOGS
// ============================================================
function refreshLogs(){if(!isAdmin)return;fetch("/api/logs?key="+encodeURIComponent(currentKey)).then(r=>r.json()).then(d=>{if(d.error){alert(d.error);return}var container=document.getElementById("logsContainer");var html=d.logs.map(log=>{var color=log.level==="ERROR"?"var(--r)":(log.level==="SUCCESS"?"var(--g)":"var(--muted)");return'<div style="padding:2px 0;border-bottom:1px solid rgba(255,255,255,0.03);color:'+color+'">['+log.timestamp+'] '+log.message+'</div>'}).join('');container.innerHTML=html||'<div style="color:var(--muted)">Henüz log yok.</div>'})}
// ============================================================
// PAGE SWITCH
// ============================================================
function switchPage(page){if((page==="discovery"||page==="stats"||page==="keys"||page==="logs")&&!isAdmin){alert("⛔ Bu sayfaya erişim yetkiniz yok! Admin girişi yapın.");return}document.querySelectorAll(".nav-item").forEach(function(el){el.classList.remove("active")});var el=document.querySelector('.nav-item[data-page="'+page+'"]');if(el)el.classList.add("active");document.querySelectorAll(".page").forEach(function(el){el.classList.remove("active")});var pg=document.getElementById("page-"+page);if(pg)pg.classList.add("active");var titles={checker:"Checker",proxy:"Proxy",discovery:"API Keşif",parse:"Ayrıştırma",stats:"İstatistik",keys:"Key Yönetimi",logs:"Loglar"};document.getElementById("pageTitle").innerText=titles[page]||page;if(page==="keys"&&isAdmin)loadKeys();if(page==="logs"&&isAdmin)refreshLogs();if(page==="stats"){document.getElementById("statScans").innerText=1;document.getElementById("statLast").innerText=new Date().toLocaleString()}}
// ============================================================
// PROXY
// ============================================================
function fetchProxies(){document.getElementById("proxyCount").innerText="Çekiliyor...";fetch("/api/fetch_proxies").then(function(r){return r.json()}).then(function(d){if(d.success){document.getElementById("proxyList").value=d.proxies.join("\n");document.getElementById("proxyCount").innerText=d.proxies.length+" proxy yüklendi"}}).catch(function(e){document.getElementById("proxyCount").innerText="Başarısız"})}
function clearProxies(){document.getElementById("proxyList").value="";document.getElementById("proxyCount").innerText="0 proxy"}
function toggleProxy(){useProxy=document.getElementById("useProxy").checked}
// ============================================================
// ADMIN KEYS
// ============================================================
function loadKeys(){if(!isAdmin)return;fetch("/api/admin/keys?key="+encodeURIComponent(currentKey)).then(function(r){return r.json()}).then(function(d){if(d.error){alert(d.error);return}var list=document.getElementById("keyList");var html="";for(var k in d){var v=d[k];var exp=v.expires?new Date(v.expires).toLocaleString():"Süresiz";var ip=v.bound_ip||"Bağlanmamış";var used=v.used?"✅ Kullanıldı":"❌ Kullanılmadı";html+='<div style="display:flex;justify-content:space-between;align-items:center;padding:8px 0;border-bottom:1px solid var(--border)"><div><strong style="font-size:13px">'+k+'</strong><br><small style="color:var(--muted);font-size:10px">'+v.note+' | '+exp+' | IP: '+ip+' | '+used+'</small></div><button class="btn sm r" onclick="deleteKey(\''+k+'\')" style="padding:3px 10px;font-size:10px">Sil</button></div>'}list.innerHTML=html||'<p style="color:var(--muted);font-size:12px">Hiç key yok.</p>'}).catch(function(e){console.error(e)})}
function generateKey(){if(!isAdmin)return;var note=document.getElementById("genNote").value||"Oluşturuldu";var hours=document.getElementById("genHours").value;fetch("/api/admin/generate",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({master_key:currentKey,note:note,hours:hours})}).then(function(r){return r.json()}).then(function(d){if(d.success){alert("Key Oluşturuldu!\n\nKey: "+d.key+"\nBitiş: "+d.expires);loadKeys()}else alert("Başarısız: "+(d.error||""))}).catch(function(e){alert("Hata: "+e.message)})}
function deleteKey(target){if(!isAdmin)return;if(!confirm("Bu anahtarı sil?"))return;fetch("/api/admin/delete",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({master_key:currentKey,target_key:target})}).then(function(r){return r.json()}).then(function(d){if(d.success)loadKeys();else alert("Silinemedi")}).catch(function(e){alert("Hata: "+e.message)})}
// ============================================================
// API SCAN
// ============================================================
function updateStatsUI(){if(!isAdmin)return;document.getElementById("totalCount").innerText=foundEndpoints.length;document.getElementById("sideTotal").innerText=foundEndpoints.length;var auth=foundEndpoints.filter(function(e){return e.category==="Auth"}).length;var api=foundEndpoints.filter(function(e){return e.category==="API"}).length;var admin=foundEndpoints.filter(function(e){return e.category==="Admin"}).length;document.getElementById("authCount").innerText=auth;document.getElementById("apiCount").innerText=api;document.getElementById("adminCount").innerText=admin;document.getElementById("sideAuth").innerText=auth;document.getElementById("sideAPI").innerText=api;document.getElementById("sideAdmin").innerText=admin;document.getElementById("statEndpoints").innerText=foundEndpoints.length}
function startScan(){if(!isAdmin){alert("⛔ Bu işlem sadece admin yetkilisine açıktır!");return}if(scanning)return;var domain=document.getElementById("targetDomain").value.trim();if(!domain)return alert("Hedef domain girin");var btn=document.getElementById("scanBtn");btn.disabled=true;btn.innerHTML='<i class="fa-solid fa-spinner fa-spin"></i> Taranıyor...';scanning=true;foundEndpoints=[];document.getElementById("resultsList").innerHTML="";document.getElementById("statusDot").classList.remove("idle");document.getElementById("statusText").innerText="Taranıyor";updateStatsUI();var proxyList=document.getElementById("proxyList").value.trim().split("\n").filter(function(l){return l.trim()&&l.includes(":")});var url="/api/scan?key="+encodeURIComponent(currentKey)+"&domain="+encodeURIComponent(domain)+"&use_proxy="+useProxy;if(useProxy&&proxyList.length){url+="&proxies="+encodeURIComponent(proxyList.join(","))}eventSource=new EventSource(url);eventSource.onmessage=function(e){if(e.data==="[DONE]"){eventSource.close();btn.disabled=false;btn.innerHTML='<i class="fa-solid fa-play"></i> Tara';scanning=false;document.getElementById("statusDot").classList.add("idle");document.getElementById("statusText").innerText="Boşta";document.getElementById("statScans").innerText=parseInt(document.getElementById("statScans").innerText||0)+1;document.getElementById("statLast").innerText=new Date().toLocaleString();return}try{var res=JSON.parse(e.data);foundEndpoints.push(res);addResultRow(res);updateStatsUI()}catch(err){}};eventSource.onerror=function(){eventSource.close();btn.disabled=false;btn.innerHTML='<i class="fa-solid fa-play"></i> Tara';scanning=false;document.getElementById("statusDot").classList.add("idle");document.getElementById("statusText").innerText="Boşta"}}
function addResultRow(res){var list=document.getElementById("resultsList");var row=document.createElement("div");row.className="result-row";var mc=res.method==="GET"?"get":(res.method==="POST"?"post":"other");var cc="cat-"+res.category.toLowerCase();row.innerHTML='<div><span class="method '+mc+'">'+res.method+'</span></div><div>'+res.status+'</div><div style="word-break:break-all">'+res.url+'</div><div><span class="category '+cc+'">'+res.category+'</span></div>';var checked=Array.from(document.querySelectorAll("#filterContainer input:checked")).map(function(c){return c.value});if(checked.includes(res.category))list.appendChild(row)}
document.getElementById("filterContainer").addEventListener("change",function(){var checked=Array.from(this.querySelectorAll("input:checked")).map(function(c){return c.value});var list=document.getElementById("resultsList");list.innerHTML="";foundEndpoints.forEach(function(res){if(checked.includes(res.category)){var row=document.createElement("div");row.className="result-row";var mc=res.method==="GET"?"get":(res.method==="POST"?"post":"other");var cc="cat-"+res.category.toLowerCase();row.innerHTML='<div><span class="method '+mc+'">'+res.method+'</span></div><div>'+res.status+'</div><div style="word-break:break-all">'+res.url+'</div><div><span class="category '+cc+'">'+res.category+'</span></div>';list.appendChild(row)}})});
function sendWebhook(){if(!isAdmin){alert("⛔ Bu işlem sadece admin yetkilisine açıktır!");return}var url=document.getElementById("webhookUrl").value.trim();if(!url)return alert("Webhook URL girin");var categories=Array.from(document.querySelectorAll("#filterContainer input:checked")).map(function(c){return c.value});if(!categories.length)return alert("En az bir kategori seçin");if(!foundEndpoints.length)return alert("Önce tarama yapın");fetch("/api/admin/webhook",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({master_key:currentKey,webhook_url:url,endpoints:foundEndpoints,categories:categories})}).then(function(r){return r.json()}).then(function(d){alert(d.success?"✅ Discord'a gönderildi!":"❌ Gönderilemedi")}).catch(function(e){alert("Hata: "+e.message)})}
function exportJSON(){if(!isAdmin){alert("⛔ Bu işlem sadece admin yetkilisine açıktır!");return}if(!foundEndpoints.length)return alert("Veri yok");var blob=new Blob([JSON.stringify(foundEndpoints,null,2)],{type:"application/json"});var a=document.createElement("a");a.href=URL.createObjectURL(blob);a.download="roda_api_scan.json";a.click()}
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
    ║     🔱 RODA - API KEŞİF + CHECKER + AYRIŞTIRMA (TÜRKÇE)        ║
    ║     Render Free Plan Uyumlu - KISALTILMIŞ KOD                 ║
    ║     http://0.0.0.0:""" + str(port) + """                               ║
    ║     Admin girişi için şifre gizlidir.                         ║
    ║     1 KEY 1 IP - 1 KULLANIM                                  ║
    ║     LOG SİSTEMİ AKTİF                                         ║
    ║     VALORANT KALDIRILDI                                      ║
    ║     YEŞİLİMSİ MAVİ TEMA                                      ║
    ╚══════════════════════════════════════════════════════════════════╝
    """)
    app.run(host="0.0.0.0", port=port, debug=False)
