#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Roda - API Discovery + Checker (Türkçe)
Admin/Üye ayrımı | Key sistemi | Sabit menü | Dosyadan temizleme
"""

import os, json, re, time, random, string, threading, webbrowser, base64
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

def load_keys():
    if os.path.exists(KEYS_FILE):
        with open(KEYS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_keys(data):
    with open(KEYS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def is_key_valid(key):
    if key == MASTER_KEY:
        return True, "Admin"
    keys = load_keys()
    if key in keys:
        entry = keys[key]
        exp = entry.get("expires")
        if exp:
            if datetime.now() < datetime.fromisoformat(exp):
                return True, entry.get("note", "Kullanıcı")
            else:
                del keys[key]
                save_keys(keys)
        else:
            return True, entry.get("note", "Kullanıcı")
    return False, None

def is_admin(key):
    valid, role = is_key_valid(key)
    return valid and role == "Admin"

# ============================================================
# PLATFORMLAR
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
    {"name": "Valorant", "domain": "valorant.com", "icon": "fa-solid fa-crosshairs"},
    {"name": "Minecraft", "domain": "minecraft.net", "icon": "fa-solid fa-cube"},
]

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
            "/api/valorant", "/api/valorant/v1",
            "/api/minecraft", "/api/minecraft/v1",
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
    valid, role = is_key_valid(key)
    return jsonify({"success": valid, "user": role, "isAdmin": role == "Admin"})

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
    keys[new_key] = {"note": note, "expires": expires.isoformat(), "created": datetime.now().isoformat()}
    save_keys(keys)
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
        return jsonify({"success": r.status_code in [200, 204]})
    except:
        return jsonify({"success": False}), 500

@app.route("/api/fetch_proxies", methods=["GET"])
def fetch_proxies_route():
    try:
        proxies = fetch_proxies()
        return jsonify({"success": True, "proxies": proxies, "count": len(proxies)})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

# ============================================================
# HTML (SABİT MENÜ + API KEŞİF'TE PLATFORM BUTONLARI)
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
:root{--p:#ff6b00;--p2:#7c3aed;--g:#00e676;--r:#ff5252;--card:#12192e;--border:rgba(255,107,0,0.15);--bg:#0a0e1a;--sidebar:#060a16;--text:#e8edf5;--muted:#8a9bb0;--gold:#ffd740}
#login-screen{position:fixed;top:0;left:0;width:100%;height:100%;z-index:9999;display:flex;justify-content:center;align-items:center;background:var(--bg)}
#login-box{width:400px;padding:45px 40px;text-align:center;background:var(--card);border:1px solid var(--border);border-radius:28px;box-shadow:0 20px 50px rgba(255,107,0,0.08
