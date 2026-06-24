#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Roda - API Discovery + Checker (Türkçe)
TikTok, CapCut, Roblox, Netflix, Discord, Spotify, Epic Games, Hesapcomtr, Itemsatış, Epinify ve diğerleri
"""

import os, json, re, time, random, string, threading, webbrowser
from datetime import datetime, timedelta
from urllib.parse import urljoin
import requests
from flask import Flask, request, jsonify, Response

app = Flask(__name__)

# ============================================================
# ANAHTAR
# ============================================================
MASTER_KEY = "Roda12345"
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

# ============================================================
# KATEGORİZASYON
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
# ENDPOINT ÇIKARICILAR (aynı)
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
# TARAMA MOTORU (Proxy destekli)
# ============================================================
class APIScanner:
    def __init__(self, proxy_list=None):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'tr-TR,tr;q=0.9,en;q=0.8',
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
            # Genel
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
            # TikTok / CapCut
            "/passport", "/passport/web", "/passport/web/email/login",
            "/passport/web/phone/login", "/passport/web/sms/send",
            "/api/user/info", "/api/user/follow", "/api/user/unfollow",
            "/api/video/list", "/api/video/info", "/api/video/upload",
            "/api/comment/list", "/api/comment/post", "/api/comment/delete",
            "/api/like", "/api/unlike", "/api/share",
            "/api/live", "/api/live/start", "/api/live/end",
            "/api/shop", "/api/product", "/api/order",
            # Roblox
            "/v1/auth", "/v1/login", "/v1/logout", "/v1/register",
            "/v1/user", "/v1/users", "/v1/account", "/v1/profile",
            "/v1/game", "/v1/games", "/v1/inventory", "/v1/currency",
            "/v1/friends", "/v1/groups", "/v1/chat", "/v1/messages",
            "/v1/avatar", "/v1/outfits", "/v1/thumbnails",
            "/v1/asset", "/v1/assets", "/v1/marketplace",
            "/v1/developer", "/v1/universes", "/v1/places",
            # Netflix
            "/api/shows", "/api/movies", "/api/genres", "/api/titles",
            "/api/search", "/api/recommendations", "/api/trending",
            "/api/user/profile", "/api/user/history", "/api/user/ratings",
            "/api/user/list", "/api/user/watchlist", "/api/user/continue",
            "/api/subscription", "/api/plans", "/api/payment",
            "/api/account", "/api/settings", "/api/devices",
            # Discord
            "/api/v9", "/api/v9/auth", "/api/v9/login", "/api/v9/register",
            "/api/v9/users", "/api/v9/guilds", "/api/v9/channels",
            "/api/v9/messages", "/api/v9/webhooks", "/api/v9/oauth2",
            "/api/v9/applications", "/api/v9/voice", "/api/v9/stickers",
            "/api/v9/emojis", "/api/v9/invites", "/api/v9/connections",
            # Spotify
            "/api/v1/me", "/api/v1/playlists", "/api/v1/tracks", "/api/v1/albums",
            "/api/v1/artists", "/api/v1/search", "/api/v1/recommendations",
            "/api/v1/player", "/api/v1/queue", "/api/v1/library",
            "/api/v1/follow", "/api/v1/shows", "/api/v1/episodes",
            "/api/v1/users", "/api/v1/browse", "/api/v1/categories",
            # Epic Games
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
            # Hesapcomtr / Itemsatış / Epinify
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
    key = request.json.get("key", "").strip()
    valid, user = is_key_valid(key)
    return jsonify({"success": valid, "user": user})

@app.route("/api/scan", methods=["GET"])
def scan():
    key = request.args.get("key")
    domain = request.args.get("domain")
    proxy_list = request.args.get("proxies", "").split(",") if request.args.get("proxies") else []
    use_proxy = request.args.get("use_proxy", "false").lower() == "true"
    if key != MASTER_KEY:
        return jsonify({"error": "Yetkisiz"}), 401

    def generate():
        proxy_list_filtered = [p.strip() for p in proxy_list if p.strip() and ':' in p]
        scanner = APIScanner(proxy_list_filtered if use_proxy else None)
        results = scanner.scan(domain)
        for res in results:
            yield f"data: {json.dumps(res, ensure_ascii=False)}\n\n"
        yield "data: [DONE]\n\n"

    return Response(generate(), mimetype="text/event-stream")

@app.route("/api/fetch_proxies", methods=["GET"])
def fetch_proxies_route():
    try:
        proxies = fetch_proxies()
        return jsonify({"success": True, "proxies": proxies, "count": len(proxies)})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route("/api/webhook", methods=["POST"])
def webhook():
    data = request.json
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

@app.route("/api/admin/keys")
def admin_keys():
    if request.args.get("key") != MASTER_KEY:
        return jsonify({"error": "Yetkisiz"}), 401
    return jsonify(load_keys())

@app.route("/api/admin/generate", methods=["POST"])
def admin_generate():
    d = request.json
    if d.get("master_key") != MASTER_KEY:
        return jsonify({"error": "Yetkisiz"}), 401
    note = d.get("note", "Oluşturuldu")
    hours = int(d.get("hours", 24))
    expires = datetime.now() + timedelta(hours=hours)
    new_key = "RODA-" + "".join(random.choices(string.ascii_uppercase + string.digits, k=16))
    keys = load_keys()
    keys[new_key] = {"note": note, "expires": expires.isoformat(), "created": datetime.now().isoformat()}
    save_keys(keys)
    return jsonify({"success": True, "key": new_key, "expires": expires.strftime("%Y-%m-%d %H:%M:%S")})

@app.route("/api/admin/delete", methods=["POST"])
def admin_delete():
    d = request.json
    if d.get("master_key") != MASTER_KEY:
        return jsonify({"error": "Yetkisiz"}), 401
    keys = load_keys()
    target = d.get("target_key", "")
    if target in keys:
        del keys[target]
        save_keys(keys)
        return jsonify({"success": True})
    return jsonify({"success": False})

# ============================================================
# HTML - YENİ TEMA + PLATFORM LİSTESİ + CHECKER BÖLÜMÜ
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
:root{--p:#00bcd4;--p2:#0d47a1;--g:#00e676;--r:#ff5252;--card:#12192e;--border:rgba(0,188,212,0.12);--bg:#0a0e1a;--sidebar:#060a16;--text:#e8edf5;--muted:#6b7a8f;--gold:#ffd740}
#login-screen{position:fixed;top:0;left:0;width:100%;height:100%;z-index:9999;display:flex;justify-content:center;align-items:center;background:var(--bg)}
#login-box{width:400px;padding:45px 40px;text-align:center;background:var(--card);border:1px solid var(--border);border-radius:28px;box-shadow:0 20px 50px rgba(0,188,212,0.08)}
#login-box .logo i{font-size:56px;background:linear-gradient(135deg,var(--p),var(--p2));-webkit-background-clip:text;-webkit-text-fill-color:transparent}
#login-box h1{font-size:28px;font-weight:900;letter-spacing:1px;color:var(--text)}
#login-box .sub{color:var(--muted);margin-bottom:25px;font-size:14px}
.inp{width:100%;padding:14px 18px;background:rgba(0,0,0,0.4);border:1px solid var(--border);color:#fff;border-radius:14px;font-size:15px;outline:none;transition:0.3s}
.inp:focus{border-color:var(--p);box-shadow:0 0 20px rgba(0,188,212,0.08)}
.btn{padding:15px;border:none;border-radius:14px;font-weight:700;cursor:pointer;background:linear-gradient(135deg,var(--p),var(--p2));color:#fff;width:100%;font-size:16px;transition:0.3s}
.btn:hover{transform:translateY(-2px);box-shadow:0 8px 30px rgba(0,188,212,0.25)}
.btn.sm{width:auto;padding:8px 16px;font-size:12px}
.btn.g{background:var(--g)}.btn.r{background:var(--r)}.btn.b{background:#1a73e8}
#sidebar{width:260px;min-width:260px;background:var(--sidebar);border-right:1px solid var(--border);display:flex;flex-direction:column;height:100vh;overflow-y:auto}
.sidebar-header{padding:18px 20px;text-align:center;border-bottom:1px solid var(--border)}
.sidebar-header .logo-text{font-size:24px;font-weight:900;letter-spacing:2px;color:var(--p)}
.sidebar-header .version{font-size:10px;color:var(--muted);letter-spacing:1px;margin-top:2px}
.sidebar-nav{flex:1;padding:12px 12px;overflow-y:auto}
.nav-divider{padding:8px 12px;font-size:10px;color:#4a5a70;text-transform:uppercase;letter-spacing:1px;font-weight:700;margin-top:6px}
.platform-grid{display:grid;grid-template-columns:1fr 1fr;gap:6px;margin-top:6px}
.platform-btn{padding:5px 8px;background:rgba(0,188,212,0.06);border:1px solid rgba(0,188,212,0.08);border-radius:6px;color:#8a9bb0;font-size:11px;cursor:pointer;transition:0.2s;text-align:center}
.platform-btn:hover{background:rgba(0,188,212,0.12);border-color:var(--p);color:#fff}
.platform-btn.active{background:rgba(0,188,212,0.15);border-color:var(--p);color:var(--p)}
.nav-item{display:flex;align-items:center;gap:12px;padding:9px 14px;border-radius:8px;cursor:pointer;color:#8a9bb0;font-weight:500;font-size:13px;transition:0.2s;margin-top:2px}
.nav-item:hover{background:rgba(0,188,212,0.06);color:#fff}
.nav-item.active{background:rgba(0,188,212,0.12);color:var(--p);border-left:3px solid var(--p)}
.nav-item i{font-size:16px;width:22px;text-align:center}
.sidebar-stats{padding:10px 14px;border-top:1px solid var(--border);display:flex;flex-wrap:wrap;gap:6px}
.mini-stat{flex:1;min-width:44%;background:var(--card);padding:6px 4px;border-radius:8px;text-align:center;border:1px solid rgba(255,255,255,0.03)}
.mini-stat .val{font-size:14px;font-weight:800;color:var(--text)}
.mini-stat .lbl{font-size:8px;color:var(--muted);text-transform:uppercase;letter-spacing:0.5px}
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
.stat-card .stat-lbl{font-size:10px;color:var(--muted);text-transform:uppercase;letter-spacing:0.5px}
.stat-hit .stat-val{color:var(--g)}.stat-2fa .stat-val{color:var(--gold)}.stat-bad .stat-val{color:var(--r)}.stat-total .stat-val{color:var(--p)}
.result-header{display:grid;grid-template-columns:60px 70px 1fr 110px;gap:8px;padding:6px 12px;font-size:10px;font-weight:700;color:var(--muted);text-transform:uppercase;border-bottom:1px solid var(--border)}
.result-row{display:grid;grid-template-columns:60px 70px 1fr 110px;gap:8px;padding:6px 12px;border-bottom:1px solid rgba(255,255,255,0.03);font-size:12px;align-items:center}
.result-row:hover{background:rgba(0,188,212,0.03)}
.hit{color:var(--g)}.bad{color:var(--r)}.twofa{color:var(--gold)}.error{color:#ffab40}
.method{font-weight:600;padding:1px 6px;border-radius:4px;font-size:9px;display:inline-block}
.method.get{background:rgba(0,230,118,0.12);color:var(--g)}
.method.post{background:rgba(26,115,232,0.12);color:#448aff}
.method.other{background:rgba(255,171,64,0.12);color:#ffab40}
.category{padding:1px 8px;border-radius:12px;font-size:9px;font-weight:500;display:inline-block}
.cat-auth{background:rgba(255,82,82,0.12);color:#ff5252}
.cat-admin{background:rgba(255,171,64,0.12);color:#ffab40}
.cat-user{background:rgba(0,230,118,0.12);color:var(--g)}
.cat-health{background:rgba(68,138,255,0.12);color:#448aff}
.cat-api{background:rgba(0,188,212,0.12);color:var(--p)}
.cat-genel{background:rgba(255,255,255,0.04);color:#8a9bb0}
.scan-top{display:flex;gap:10px;flex-wrap:wrap;align-items:center}
.scan-top input{flex:1;min-width:150px;padding:8px 14px;background:rgba(0,0,0,0.3);border:1px solid var(--border);border-radius:10px;color:#fff;font-size:13px;outline:none}
.scan-top input:focus{border-color:var(--p)}
.scan-top button{padding:8px 20px;background:linear-gradient(135deg,var(--p),var(--p2));color:#fff;border:none;border-radius:10px;font-weight:700;cursor:pointer;display:flex;align-items:center;gap:6px;font-size:13px}
.scan-top button:disabled{opacity:0.5;cursor:not-allowed}
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
.checker-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:8px;margin-top:8px}
.checker-btn{padding:8px 12px;background:rgba(0,188,212,0.06);border:1px solid rgba(0,188,212,0.1);border-radius:10px;color:#8a9bb0;font-size:12px;cursor:pointer;transition:0.2s;text-align:center;display:flex;align-items:center;justify-content:center;gap:6px}
.checker-btn:hover{background:rgba(0,188,212,0.12);border-color:var(--p);color:#fff}
.checker-btn i{font-size:14px}
::-webkit-scrollbar{width:4px}::-webkit-scrollbar-thumb{background:rgba(0,188,212,0.2);border-radius:4px}
</style>
</head>
<body>
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
<div class="sidebar-header"><div class="logo-text">RODA</div><div class="version">v2.0</div></div>
<div class="sidebar-nav">
<div class="nav-divider">⚡ PLATFORMLAR</div>
<div class="platform-grid" id="platformList"></div>
<div class="nav-divider" style="margin-top:12px">📁 MENÜ</div>
<div class="nav-item active" data-page="discovery" onclick="switchPage('discovery')"><i class="fa-solid fa-compass"></i> Keşif</div>
<div class="nav-item" data-page="proxy" onclick="switchPage('proxy')"><i class="fa-solid fa-server"></i> Proxy</div>
<div class="nav-item" data-page="checker" onclick="switchPage('checker')"><i class="fa-solid fa-check-double"></i> Checker</div>
<div class="nav-item" data-page="stats" onclick="switchPage('stats')"><i class="fa-solid fa-chart-simple"></i> İstatistik</div>
<div class="nav-item" data-page="keys" onclick="switchPage('keys')"><i class="fa-solid fa-key"></i> Anahtarlar</div>
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
<div class="topbar-title"><i class="fa-solid fa-gauge-high"></i> <span id="pageTitle">Keşif</span></div>
<div class="topbar-right">
<span style="font-size:11px;color:var(--muted)">Durum:</span>
<div class="pulse-dot idle" id="statusDot"></div>
<span style="font-size:12px;font-weight:600" id="statusText">Boşta</span>
</div>
</div>
<div class="main-content">
<!-- DISCOVERY -->
<div id="page-discovery" class="page active">
<div class="card" style="padding:10px 14px">
<div class="scan-top">
<input id="targetDomain" placeholder="hedef.com (örn: youtube.com)" value="example.com">
<button id="scanBtn" onclick="startScan()"><i class="fa-solid fa-play"></i> Tara</button>
</div>
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
<button onclick="sendWebhook()"><i class="fa-brands fa-discord"></i> Discord</button>
<button onclick="exportJSON()" class="btn sm b"><i class="fa-solid fa-download"></i> JSON</button>
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
<div><label>Proxy Kullan</label><div class="desc">Tarama sırasında proxy kullan</div></div>
<label class="switch"><input type="checkbox" id="useProxy" onchange="toggleProxy()"><span class="slider"></span></label>
</div>
<div class="proxy-area">
<textarea id="proxyList" placeholder="ip:port&#10;ip:port"></textarea>
</div>
<div style="margin-top:6px"><span id="proxyCount" style="color:var(--g);font-size:12px">0 proxy yüklendi</span></div>
</div>
</div>
<!-- CHECKER -->
<div id="page-checker" class="page">
<div class="card">
<h3><i class="fa-solid fa-check-double"></i> Platform Checker'lar</h3>
<p style="font-size:12px;color:var(--muted);margin-bottom:10px">Her platform için özel checker araçlarına buradan erişin.</p>
<div class="checker-grid" id="checkerGrid"></div>
</div>
</div>
<!-- STATS -->
<div id="page-stats" class="page">
<h2 style="margin-bottom:14px;font-weight:700;background:linear-gradient(135deg,var(--p),var(--p2));-webkit-background-clip:text;-webkit-text-fill-color:transparent">📊 Tarama İstatistikleri</h2>
<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:14px">
<div style="background:var(--card);border:1px solid var(--border);border-radius:12px;padding:18px"><h3 style="font-size:12px;color:var(--muted)">Toplam Tarama</h3><p style="font-size:22px;font-weight:800;background:linear-gradient(135deg,var(--p),var(--p2));-webkit-background-clip:text;-webkit-text-fill-color:transparent" id="statScans">0</p></div>
<div style="background:var(--card);border:1px solid var(--border);border-radius:12px;padding:18px"><h3 style="font-size:12px;color:var(--muted)">Son Tarama</h3><p style="font-size:22px;font-weight:800;background:linear-gradient(135deg,var(--p),var(--p2));-webkit-background-clip:text;-webkit-text-fill-color:transparent" id="statLast">-</p></div>
<div style="background:var(--card);border:1px solid var(--border);border-radius:12px;padding:18px"><h3 style="font-size:12px;color:var(--muted)">Bulunan API</h3><p style="font-size:22px;font-weight:800;background:linear-gradient(135deg,var(--p),var(--p2));-webkit-background-clip:text;-webkit-text-fill-color:transparent" id="statEndpoints">0</p></div>
</div>
</div>
<!-- KEYS -->
<div id="page-keys" class="page">
<div class="card">
<h3><i class="fa-solid fa-key"></i> Anahtar Oluştur</h3>
<div style="display:flex;gap:10px;flex-wrap:wrap;margin-top:6px">
<div style="flex:1"><label style="font-size:11px;color:var(--muted)">Not</label><input class="inp" id="genNote" placeholder="Müşteri" style="margin-top:4px;padding:10px"></div>
<div style="width:130px"><label style="font-size:11px;color:var(--muted)">Süre</label><select class="inp" id="genHours" style="margin-top:4px;padding:10px"><option value="1">1 Saat</option><option value="24" selected>24 Saat</option><option value="168">7 Gün</option></select></div>
<button class="btn sm g" onclick="generateKey()" style="margin-top:22px"><i class="fa-solid fa-plus"></i> Oluştur</button>
</div>
</div>
<div class="card"><h3><i class="fa-solid fa-list"></i> Aktif Anahtarlar</h3><div id="keyList"><p style="color:var(--muted);font-size:12px">Yükleniyor...</p></div></div>
</div>
</div>
</div>
<script>
var currentKey="", scanning=false, eventSource=null;
var foundEndpoints=[];
var useProxy=false;

// PLATFORM LİSTESİ (güncel)
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
];

// CHECKER LİSTESİ (tüm platformlar için ayrı butonlar)
var checkerList = [
    {name:"YouTube Checker", icon:"fa-brands fa-youtube"},
    {name:"TikTok Checker", icon:"fa-brands fa-tiktok"},
    {name:"Spotify Checker", icon:"fa-brands fa-spotify"},
    {name:"Roblox Checker", icon:"fa-solid fa-gamepad"},
    {name:"Netflix Checker", icon:"fa-solid fa-film"},
    {name:"CapCut Checker", icon:"fa-solid fa-scissors"},
    {name:"Discord Checker", icon:"fa-brands fa-discord"},
    {name:"Epic Checker", icon:"fa-solid fa-crown"},
    {name:"Hesapcomtr Checker", icon:"fa-solid fa-user"},
    {name:"Itemsatış Checker", icon:"fa-solid fa-cart-shopping"},
    {name:"Epinify Checker", icon:"fa-solid fa-ticket"},
    {name:"Twitch Checker", icon:"fa-brands fa-twitch"},
    {name:"Steam Checker", icon:"fa-brands fa-steam"},
    {name:"PlayStation Checker", icon:"fa-solid fa-play"},
    {name:"Xbox Checker", icon:"fa-brands fa-xbox"},
    {name:"GitHub Checker", icon:"fa-brands fa-github"},
];

function loadPlatforms(){
    var container=document.getElementById("platformList");
    container.innerHTML="";
    platforms.forEach(function(p){
        var btn=document.createElement("div");
        btn.className="platform-btn";
        btn.innerHTML='<i class="'+p.icon+'"></i> '+p.name;
        btn.onclick=function(){
            document.getElementById("targetDomain").value=p.domain;
            document.querySelectorAll(".platform-btn").forEach(function(b){b.classList.remove("active");});
            btn.classList.add("active");
        };
        container.appendChild(btn);
    });
}

function loadCheckers(){
    var container=document.getElementById("checkerGrid");
    container.innerHTML="";
    checkerList.forEach(function(c){
        var btn=document.createElement("div");
        btn.className="checker-btn";
        btn.innerHTML='<i class="'+c.icon+'"></i> '+c.name;
        btn.onclick=function(){
            alert("🔧 "+c.name+" yakında hazır olacak!\nAPI'ler toplandıktan sonra buradan çalıştırabilirsin.");
        };
        container.appendChild(btn);
    });
}

async function doLogin(){
var k=document.getElementById("authKey").value.trim();
if(!k) return alert("Anahtar girin");
try{
var r=await fetch("/api/login",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({key:k})});
var d=await r.json();
if(d.success){
currentKey=k;
document.getElementById("login-screen").style.display="none";
document.getElementById("app").style.display="flex";
loadKeys();
loadPlatforms();
loadCheckers();
}else{
document.getElementById("loginError").innerText="Geçersiz anahtar!";
document.getElementById("loginError").style.display="block";
}
}catch(e){alert("Sunucu hatası");}
}

function switchPage(page){
document.querySelectorAll(".nav-item").forEach(function(el){el.classList.remove("active");});
var el=document.querySelector('.nav-item[data-page="'+page+'"]');
if(el)el.classList.add("active");
document.querySelectorAll(".page").forEach(function(el){el.classList.remove("active");});
var pg=document.getElementById("page-"+page);
if(pg)pg.classList.add("active");
var titles={discovery:"Keşif",proxy:"Proxy",checker:"Checker",stats:"İstatistik",keys:"Anahtarlar"};
document.getElementById("pageTitle").innerText=titles[page]||"";
if(page==="keys")loadKeys();
}

function updateStatsUI(){
document.getElementById("totalCount").innerText=foundEndpoints.length;
document.getElementById("sideTotal").innerText=foundEndpoints.length;
var auth=foundEndpoints.filter(function(e){return e.category==="Auth";}).length;
var api=foundEndpoints.filter(function(e){return e.category==="API";}).length;
var admin=foundEndpoints.filter(function(e){return e.category==="Admin";}).length;
document.getElementById("authCount").innerText=auth;
document.getElementById("apiCount").innerText=api;
document.getElementById("adminCount").innerText=admin;
document.getElementById("sideAuth").innerText=auth;
document.getElementById("sideAPI").innerText=api;
document.getElementById("sideAdmin").innerText=admin;
document.getElementById("statEndpoints").innerText=foundEndpoints.length;
}

function startScan(){
if(scanning)return;
var domain=document.getElementById("targetDomain").value.trim();
if(!domain)return alert("Hedef domain girin");
var btn=document.getElementById("scanBtn");
btn.disabled=true;btn.innerHTML='<i class="fa-solid fa-spinner fa-spin"></i> Taranıyor...';
scanning=true;foundEndpoints=[];document.getElementById("resultsList").innerHTML="";
document.getElementById("statusDot").classList.remove("idle");
document.getElementById("statusText").innerText="Taranıyor";
updateStatsUI();

var proxyList=document.getElementById("proxyList").value.trim().split("\n").filter(function(l){return l.trim() && l.includes(":");});
var url="/api/scan?key="+encodeURIComponent(currentKey)+"&domain="+encodeURIComponent(domain)+"&use_proxy="+useProxy;
if(useProxy && proxyList.length){
    url+="&proxies="+encodeURIComponent(proxyList.join(","));
}
eventSource=new EventSource(url);
eventSource.onmessage=function(e){
if(e.data==="[DONE]"){
eventSource.close();btn.disabled=false;btn.innerHTML='<i class="fa-solid fa-play"></i> Tara';
scanning=false;document.getElementById("statusDot").classList.add("idle");
document.getElementById("statusText").innerText="Boşta";
document.getElementById("statScans").innerText=parseInt(document.getElementById("statScans").innerText||0)+1;
document.getElementById("statLast").innerText=new Date().toLocaleString();
return;
}
try{var res=JSON.parse(e.data);foundEndpoints.push(res);addResultRow(res);updateStatsUI();}catch(err){}
};
eventSource.onerror=function(){eventSource.close();btn.disabled=false;btn.innerHTML='<i class="fa-solid fa-play"></i> Tara';
scanning=false;document.getElementById("statusDot").classList.add("idle");
document.getElementById("statusText").innerText="Boşta";};
}

function addResultRow(res){
var list=document.getElementById("resultsList");
var row=document.createElement("div");row.className="result-row";
var mc=res.method==="GET"?"get":(res.method==="POST"?"post":"other");
var cc="cat-"+res.category.toLowerCase();
row.innerHTML='<div><span class="method '+mc+'">'+res.method+'</span></div><div>'+res.status+'</div><div style="word-break:break-all">'+res.url+'</div><div><span class="category '+cc+'">'+res.category+'</span></div>';
var checked=Array.from(document.querySelectorAll("#filterContainer input:checked")).map(function(c){return c.value;});
if(checked.includes(res.category))list.appendChild(row);
}

document.getElementById("filterContainer").addEventListener("change",function(){
var checked=Array.from(this.querySelectorAll("input:checked")).map(function(c){return c.value;});
var list=document.getElementById("resultsList");list.innerHTML="";
foundEndpoints.forEach(function(res){
if(checked.includes(res.category)){
var row=document.createElement("div");row.className="result-row";
var mc=res.method==="GET"?"get":(res.method==="POST"?"post":"other");
var cc="cat-"+res.category.toLowerCase();
row.innerHTML='<div><span class="method '+mc+'">'+res.method+'</span></div><div>'+res.status+'</div><div style="word-break:break-all">'+res.url+'</div><div><span class="category '+cc+'">'+res.category+'</span></div>';
list.appendChild(row);
}
});
});

async function sendWebhook(){
var url=document.getElementById("webhookUrl").value.trim();
if(!url)return alert("Webhook URL girin");
var categories=Array.from(document.querySelectorAll("#filterContainer input:checked")).map(function(c){return c.value;});
if(!categories.length)return alert("En az bir kategori seçin");
if(!foundEndpoints.length)return alert("Önce tarama yapın");
try{
var r=await fetch("/api/webhook",{method:"POST",headers:{"Content-Type":"application/json"},
body:JSON.stringify({webhook_url:url,endpoints:foundEndpoints,categories:categories})});
var d=await r.json();
alert(d.success?"✅ Discord'a gönderildi!":"❌ Gönderilemedi");
}catch(e){alert("Hata: "+e.message);}
}

function exportJSON(){
if(!foundEndpoints.length)return alert("Veri yok");
var blob=new Blob([JSON.stringify(foundEndpoints,null,2)],{type:"application/json"});
var a=document.createElement("a");a.href=URL.createObjectURL(blob);a.download="roda_api_scan.json";a.click();
}

async function fetchProxies(){
document.getElementById("proxyCount").innerText="Çekiliyor...";
try{
var r=await fetch("/api/fetch_proxies");
var d=await r.json();
if(d.success){
document.getElementById("proxyList").value=d.proxies.join("\n");
document.getElementById("proxyCount").innerText=d.proxies.length+" proxy yüklendi";
}
}catch(e){document.getElementById("proxyCount").innerText="Başarısız";}
}

function clearProxies(){
document.getElementById("proxyList").value="";
document.getElementById("proxyCount").innerText="0 proxy";
}
function toggleProxy(){useProxy=document.getElementById("useProxy").checked;}

async function loadKeys(){try{var r=await fetch("/api/admin/keys?key="+encodeURIComponent(currentKey));var d=await r.json();if(d.error)return;var list=document.getElementById("keyList");var html="";for(var k in d){var v=d[k];html+='<div style="display:flex;justify-content:space-between;align-items:center;padding:8px 0;border-bottom:1px solid var(--border)"><div><strong style="font-size:13px">'+k+'</strong><br><small style="color:var(--muted);font-size:10px">'+v.note+'</small></div><button class="btn sm r" onclick="deleteKey(\''+k+'\')" style="padding:3px 10px;font-size:10px">Sil</button></div>';}list.innerHTML=html;}catch(e){}}
async function generateKey(){var note=document.getElementById("genNote").value||"Oluşturuldu";var hours=document.getElementById("genHours").value;try{var r=await fetch("/api/admin/generate",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({master_key:currentKey,note:note,hours:hours})});var d=await r.json();if(d.success){alert("Anahtar Oluşturuldu!\n\nAnahtar: "+d.key+"\nBitiş: "+d.expires);loadKeys();}else alert("Başarısız");}catch(e){alert("Hata");}}
async function deleteKey(target){if(!confirm("Bu anahtarı sil?"))return;try{await fetch("/api/admin/delete",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({master_key:currentKey,target_key:target})});loadKeys();}catch(e){alert("Hata");}}
document.getElementById("authKey").addEventListener("keypress",function(e){if(e.key==="Enter")doLogin();});
</script>
</body>
</html>
"""

# ============================================================
# BAŞLAT
# ============================================================
if __name__ == "__main__":
    if not os.path.exists(KEYS_FILE):
        save_keys({MASTER_KEY: {"note": "Master Admin", "expires": "2099-12-31T23:59:59"}})

    threading.Timer(1.5, lambda: webbrowser.open("http://127.0.0.1:5000")).start()

    print("""
    ╔══════════════════════════════════════════════════════════════════╗
    ║     🔱 RODA - API KEŞİF + CHECKER (TÜRKÇE)                     ║
    ║     Anahtar: Roda12345                                         ║
    ║     http://127.0.0.1:5000                                     ║
    ║     YouTube • TikTok • Spotify • Roblox • Netflix             ║
    ║     CapCut • Discord • Epic Games • Hesapcomtr               ║
    ║     Itemsatış • Epinify • Twitch • Steam • PlayStation      ║
    ║     Xbox • GitHub                                            ║
    ╚══════════════════════════════════════════════════════════════════╝
    """)

    app.run(host="127.0.0.1", port=5000, debug=False)
