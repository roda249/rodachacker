#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Roda - API Discovery Pro (Türkçe)
TikTok, CapCut, Roblox, Netflix, Discord, Spotify, Amazon, YouTube ve diğerleri için
"""

import os, json, re, time, random, string, threading, webbrowser
from datetime import datetime, timedelta
from urllib.parse import urljoin, urlparse
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
# TARAMA MOTORU
# ============================================================
class APIScanner:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'tr-TR,tr;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
        })
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
            # Platform özel
            "/api/login", "/api/signin", "/api/authenticate", "/api/token",
            "/api/user", "/api/users", "/api/account", "/api/profile",
            "/api/session", "/api/status", "/api/health", "/api/config",
            "/api/search", "/api/query", "/api/list", "/api/upload", "/api/download",
            "/api/notify", "/api/alert", "/api/report", "/api/logs",
            "/api/sync", "/api/import", "/api/export", "/api/backup",
            "/api/reset", "/api/recover", "/api/verify", "/api/validate",
            "/api/2fa", "/api/webhook", "/api/callback",
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
            # Amazon
            "/api/auth", "/api/signin", "/api/signup", "/api/logout",
            "/api/account", "/api/orders", "/api/order", "/api/cart",
            "/api/product", "/api/products", "/api/search", "/api/recommendations",
            "/api/review", "/api/reviews", "/api/wishlist", "/api/list",
            "/api/payment", "/api/shipping", "/api/address", "/api/prime",
            "/api/kindle", "/api/audible", "/api/music", "/api/video",
            "/api/aws", "/api/s3", "/api/ec2", "/api/lambda",
            # YouTube
            "/youtube/v3", "/api/youtube", "/api/youtube/v3",
            "/api/videos", "/api/video", "/api/video/list", "/api/video/info",
            "/api/channels", "/api/channel", "/api/channel/list", "/api/channel/info",
            "/api/playlists", "/api/playlist", "/api/playlist/list", "/api/playlist/info",
            "/api/search", "/api/search/list", "/api/search/suggest",
            "/api/comments", "/api/comment", "/api/comment/list", "/api/comment/post",
            "/api/live", "/api/live/stream", "/api/live/chat", "/api/live/events",
            "/api/subscriptions", "/api/subscription", "/api/subscribe", "/api/unsubscribe",
            "/api/history", "/api/watch", "/api/watchtime", "/api/analytics",
            "/api/upload", "/api/upload/video", "/api/upload/thumbnail",
            "/api/captions", "/api/caption", "/api/transcript",
            "/api/ratings", "/api/likes", "/api/dislikes",
            "/api/abuse", "/api/report", "/api/block",
            "/api/membership", "/api/members", "/api/sponsor",
            "/api/ads", "/api/ad", "/api/monetization",
            "/api/insights", "/api/trending", "/api/popular",
            "/api/feeds", "/api/feed", "/api/home", "/api/recommended",
            "/api/notifications", "/api/notification",
            "/api/messages", "/api/message", "/api/inbox",
            "/api/shorts", "/api/short", "/api/shorts/list",
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
    if key != MASTER_KEY:
        return jsonify({"error": "Yetkisiz"}), 401

    def generate():
        scanner = APIScanner()
        results = scanner.scan(domain)
        for res in results:
            yield f"data: {json.dumps(res, ensure_ascii=False)}\n\n"
        yield "data: [DONE]\n\n"

    return Response(generate(), mimetype="text/event-stream")

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
# HTML - TÜRKÇE ARAYÜZ
# ============================================================
HTML_TEMPLATE = r"""
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Roda - API Discovery</title>
<link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800;900&display=swap" rel="stylesheet">
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
<style>
*{margin:0;padding:0;box-sizing:border-box;font-family:Outfit,sans-serif}
body{background:#030712;color:#e2e8f0;height:100vh;overflow:hidden;display:flex}
:root{--p:#ec4899;--g:#10b981;--r:#ef4444;--card:#1e293b;--border:rgba(255,255,255,0.06)}
#login-screen{position:fixed;top:0;left:0;width:100%;height:100%;z-index:9999;display:flex;justify-content:center;align-items:center;background:#030712}
#login-box{width:400px;padding:45px 40px;text-align:center;background:var(--card);border:1px solid var(--border);border-radius:28px}
#login-box .logo i{font-size:56px;color:var(--p)}
#login-box h1{font-size:24px;font-weight:800;letter-spacing:2px;margin:10px 0}
.inp{width:100%;padding:15px 18px;background:rgba(0,0,0,0.4);border:1px solid var(--border);color:#fff;border-radius:14px;font-size:15px;outline:none}
.inp:focus{border-color:var(--p)}
.btn{padding:15px;border:none;border-radius:14px;font-weight:700;cursor:pointer;background:linear-gradient(135deg,var(--p),#8b5cf6);color:#fff;width:100%;font-size:15px;transition:all .3s}
.btn:hover{transform:translateY(-2px)}
.btn.sm{width:auto;padding:9px 16px;font-size:12px}
.btn.g{background:var(--g)}.btn.r{background:var(--r)}.btn.b{background:#3b82f6}
#sidebar{width:240px;min-width:240px;background:#020617;border-right:1px solid var(--border);display:flex;flex-direction:column;height:100vh}
.sidebar-header{padding:24px 20px;text-align:center;border-bottom:1px solid var(--border)}
.sidebar-header .logo-text{font-size:22px;font-weight:900;color:var(--p)}
.sidebar-nav{flex:1;padding:16px 10px;overflow-y:auto}
.nav-item{display:flex;align-items:center;gap:12px;padding:12px 16px;border-radius:12px;cursor:pointer;color:#94a3b8;font-weight:500;font-size:13px;transition:all .2s}
.nav-item:hover{background:var(--card);color:#fff}
.nav-item.active{background:rgba(236,72,153,0.15);color:var(--p)}
.nav-item i{font-size:18px;width:24px}
.sidebar-stats{padding:16px;border-top:1px solid var(--border);display:flex;flex-wrap:wrap;gap:8px}
.mini-stat{flex:1;min-width:45%;background:var(--card);padding:10px;border-radius:10px;text-align:center}
.mini-stat .val{font-size:16px;font-weight:800}
.mini-stat .lbl{font-size:9px;color:#94a3b8}
.mini-hit .val{color:var(--g)}.mini-2fa .val{color:#fbbf24}.mini-bad .val{color:var(--r)}.mini-check .val{color:var(--p)}
.sidebar-footer{padding:12px;text-align:center;font-size:10px;color:#94a3b8;border-top:1px solid var(--border)}
#app{display:none;flex:1;flex-direction:column;height:100vh}
.topbar{display:flex;align-items:center;gap:16px;padding:14px 24px;background:var(--card);border-bottom:1px solid var(--border)}
.topbar-title{font-size:15px;font-weight:700}
.topbar-title i{margin-right:8px;color:var(--p)}
.topbar-right{margin-left:auto;display:flex;align-items:center;gap:16px}
.pulse-dot{width:10px;height:10px;border-radius:50%;background:var(--g);animation:pulse 2s infinite}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:0.5}}
.pulse-dot.idle{background:#94a3b8;animation:none}
.main-content{flex:1;display:flex;overflow:hidden}
.page{display:none;flex:1;flex-direction:column;padding:20px 24px;overflow-y:auto}
.page.active{display:flex}
.card{background:var(--card);border:1px solid var(--border);border-radius:20px;padding:20px;margin-bottom:16px}
.card h3{font-size:14px;font-weight:700;margin-bottom:12px}
.stats-row{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:20px}
.stat-card{background:var(--card);border:1px solid var(--border);border-radius:16px;padding:18px;text-align:center}
.stat-card .stat-val{font-size:28px;font-weight:800}
.stat-card .stat-lbl{font-size:10px;color:#94a3b8;text-transform:uppercase;letter-spacing:1px}
.stat-hit .stat-val{color:var(--g)}.stat-2fa .stat-val{color:#fbbf24}.stat-bad .stat-val{color:var(--r)}.stat-total .stat-val{color:var(--p)}
.result-header{display:grid;grid-template-columns:70px 80px 1fr 120px;gap:12px;padding:10px 16px;font-size:10px;font-weight:700;color:#94a3b8;text-transform:uppercase;border-bottom:1px solid var(--border)}
.result-row{display:grid;grid-template-columns:70px 80px 1fr 120px;gap:12px;padding:12px 16px;border-bottom:1px solid var(--border);font-size:13px;align-items:center}
.hit{color:var(--g)}.bad{color:var(--r)}.twofa{color:#fbbf24}.error{color:#f59e0b}
.method{font-weight:600;padding:2px 10px;border-radius:6px;font-size:11px;display:inline-block}
.method.get{background:rgba(52,211,153,0.15);color:#34d399}
.method.post{background:rgba(96,165,250,0.15);color:#60a5fa}
.method.other{background:rgba(251,146,60,0.15);color:#fb923c}
.category{padding:2px 12px;border-radius:20px;font-size:11px;font-weight:500;display:inline-block}
.cat-auth{background:rgba(244,63,94,0.15);color:#f87171}
.cat-admin{background:rgba(251,146,60,0.15);color:#fb923c}
.cat-user{background:rgba(52,211,153,0.15);color:#34d399}
.cat-health{background:rgba(96,165,250,0.15);color:#60a5fa}
.cat-api{background:rgba(167,139,250,0.15);color:#a78bfa}
.cat-genel{background:rgba(255,255,255,0.05);color:#b0b3c0}
.setting-row{display:flex;align-items:center;justify-content:space-between;padding:14px 0;border-bottom:1px solid var(--border)}
.setting-row label{font-size:13px;font-weight:500}
.setting-row .desc{font-size:11px;color:#94a3b8}
.switch{position:relative;width:48px;height:26px}
.switch input{display:none}
.slider{position:absolute;top:0;left:0;right:0;bottom:0;background:var(--border);border-radius:26px;cursor:pointer;transition:.3s}
.slider:before{content:"";position:absolute;height:20px;width:20px;left:3px;bottom:3px;background:#fff;border-radius:50%;transition:.3s}
input:checked+.slider{background:var(--g)}
input:checked+.slider:before{transform:translateX(22px)}
.filters{display:flex;gap:14px;margin-bottom:14px;flex-wrap:wrap}
.filters label{display:flex;align-items:center;gap:6px;font-size:13px;color:#b0b3c0;cursor:pointer}
.filters input[type=checkbox]{accent-color:#ec4899;width:16px;height:16px}
.webhook-area{margin-top:14px;display:flex;gap:12px;align-items:center;flex-wrap:wrap}
.webhook-area input{flex:1;min-width:200px;padding:10px 16px;background:rgba(0,0,0,0.4);border:1px solid rgba(255,255,255,0.06);border-radius:14px;color:#fff;font-size:13px;outline:none;margin:0}
.webhook-area input:focus{border-color:#ec4899}
.webhook-area button{padding:10px 24px;background:linear-gradient(135deg,#ec4899,#8b5cf6);color:#fff;border:none;border-radius:14px;font-weight:600;cursor:pointer}
.scan-top{display:flex;gap:12px;margin-bottom:20px;flex-wrap:wrap}
.scan-top input{flex:1;min-width:200px;padding:12px 16px;background:rgba(0,0,0,0.4);border:1px solid rgba(255,255,255,0.06);border-radius:14px;color:#fff;font-size:14px;outline:none;margin:0}
.scan-top input:focus{border-color:#ec4899}
.scan-top button{padding:12px 28px;background:linear-gradient(135deg,#ec4899,#8b5cf6);color:#fff;border:none;border-radius:14px;font-weight:700;cursor:pointer}
.scan-top button:disabled{opacity:0.5;cursor:not-allowed}
::-webkit-scrollbar{width:5px}::-webkit-scrollbar-thumb{background:rgba(255,255,255,0.08);border-radius:4px}
</style>
</head>
<body>
<div id="login-screen">
<div id="login-box">
<div class="logo"><i class="fa-solid fa-crown"></i></div>
<h1>RODA</h1>
<p style="color:#94a3b8;margin-bottom:25px;font-size:14px">API Keşif Aracı</p>
<input class="inp" type="password" id="authKey" placeholder="Güvenlik Anahtarı" autofocus>
<button class="btn" onclick="doLogin()" style="margin-top:12px">Giriş Yap</button>
<p id="loginError" style="color:var(--r);margin-top:12px;display:none"></p>
</div>
</div>
<div id="sidebar">
<div class="sidebar-header"><div class="logo-text">RODA</div></div>
<div class="sidebar-nav">
<div class="nav-item active" data-page="discovery" onclick="switchPage('discovery')"><i class="fa-solid fa-compass"></i> Keşif</div>
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
<span style="font-size:12px;color:#94a3b8">Durum:</span>
<div class="pulse-dot idle" id="statusDot"></div>
<span style="font-size:12px;font-weight:600" id="statusText">Boşta</span>
</div>
</div>
<div class="main-content">
<div id="page-discovery" class="page active">
<div class="scan-top">
<input id="targetDomain" placeholder="hedef.com (örnek: youtube.com)" value="example.com">
<button id="scanBtn" onclick="startScan()"><i class="fa-solid fa-play"></i> Tara</button>
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
<div class="results-container" style="flex:1;overflow-y:auto;border-radius:18px;background:rgba(0,0,0,0.3);border:1px solid rgba(255,255,255,0.04)">
<div class="result-header"><div>Metod</div><div>Durum</div><div>Endpoint</div><div>Kategori</div></div>
<div id="resultsList"></div>
</div>
<div class="webhook-area">
<input id="webhookUrl" placeholder="Discord Webhook URL">
<button onclick="sendWebhook()"><i class="fa-brands fa-discord"></i> Discord'a Gönder</button>
<button onclick="exportJSON()" class="btn sm b"><i class="fa-solid fa-download"></i> JSON Çıkar</button>
</div>
</div>
<div id="page-stats" class="page">
<h2 style="margin-bottom:20px;font-weight:700;background:linear-gradient(135deg,#ec4899,#8b5cf6);-webkit-background-clip:text;-webkit-text-fill-color:transparent">📊 Tarama İstatistikleri</h2>
<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:20px">
<div style="background:rgba(0,0,0,0.35);border:1px solid rgba(255,255,255,0.04);border-radius:18px;padding:24px"><h3 style="font-size:13px;color:#94a3b8">Toplam Tarama</h3><p style="font-size:28px;font-weight:800;background:linear-gradient(135deg,#ec4899,#8b5cf6);-webkit-background-clip:text;-webkit-text-fill-color:transparent" id="statScans">0</p></div>
<div style="background:rgba(0,0,0,0.35);border:1px solid rgba(255,255,255,0.04);border-radius:18px;padding:24px"><h3 style="font-size:13px;color:#94a3b8">Son Tarama</h3><p style="font-size:28px;font-weight:800;background:linear-gradient(135deg,#ec4899,#8b5cf6);-webkit-background-clip:text;-webkit-text-fill-color:transparent" id="statLast">-</p></div>
<div style="background:rgba(0,0,0,0.35);border:1px solid rgba(255,255,255,0.04);border-radius:18px;padding:24px"><h3 style="font-size:13px;color:#94a3b8">Bulunan API</h3><p style="font-size:28px;font-weight:800;background:linear-gradient(135deg,#ec4899,#8b5cf6);-webkit-background-clip:text;-webkit-text-fill-color:transparent" id="statEndpoints">0</p></div>
</div>
</div>
<div id="page-keys" class="page">
<div class="card">
<h3>Anahtar Oluştur</h3>
<div style="display:flex;gap:10px;margin-top:12px;flex-wrap:wrap">
<div style="flex:1"><label style="font-size:11px;color:#94a3b8">Not</label><input class="inp" id="genNote" placeholder="Müşteri" style="margin-top:4px"></div>
<div style="width:140px"><label style="font-size:11px;color:#94a3b8">Süre</label><select class="inp" id="genHours" style="margin-top:4px;padding:14px"><option value="1">1 Saat</option><option value="24" selected>24 Saat</option><option value="168">7 Gün</option></select></div>
<button class="btn sm g" onclick="generateKey()"><i class="fa-solid fa-plus"></i> Oluştur</button>
</div>
</div>
<div class="card"><h3>Aktif Anahtarlar</h3><div id="keyList"><p style="color:#94a3b8;font-size:12px">Yükleniyor...</p></div></div>
</div>
</div>
</div>
<script>
var currentKey="", scanning=false, eventSource=null;
var foundEndpoints=[], stats={total:0,auth:0,api:0,admin:0};

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
var titles={discovery:"Keşif",stats:"İstatistik",keys:"Anahtarlar"};
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

eventSource=new EventSource("/api/scan?key="+encodeURIComponent(currentKey)+"&domain="+encodeURIComponent(domain));
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

async function loadKeys(){try{var r=await fetch("/api/admin/keys?key="+encodeURIComponent(currentKey));var d=await r.json();if(d.error)return;var list=document.getElementById("keyList");var html="";for(var k in d){var v=d[k];html+='<div style="display:flex;justify-content:space-between;align-items:center;padding:12px 0;border-bottom:1px solid var(--border)"><div><strong>'+k+'</strong><br><small style="color:#94a3b8">'+v.note+'</small></div><button class="btn sm r" onclick="deleteKey(\''+k+'\')">Sil</button></div>';}list.innerHTML=html;}catch(e){}}
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
    ╔══════════════════════════════════════════════════════════╗
    ║     🔱 RODA - API KEŞİF PRO (TÜRKÇE)                   ║
    ║     Anahtar: Roda12345                                 ║
    ║     http://127.0.0.1:5000                             ║
    ║     TikTok • CapCut • Roblox • Netflix • YouTube      ║
    ║     Discord • Spotify • Amazon ve daha fazlası        ║
    ╚══════════════════════════════════════════════════════════╝
    """)

    app.run(host="127.0.0.1", port=5000, debug=False)
