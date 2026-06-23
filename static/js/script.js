<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Roda</title>
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
.webhook-area{margin-top:10px;display:flex;gap:10px;flex-wrap:wrap;align-items:center}
.webhook-area input{flex:1;min-width:150px;padding:6px 12px;background:rgba(0,0,0,0.3);border:1px solid var(--border);border-radius:10px;color:#fff;font-size:12px;outline:none}
.webhook-area input:focus{border-color:var(--p)}
.webhook-area button{padding:6px 16px;background:linear-gradient(135deg,var(--p),var(--p2));color:#fff;border:none;border-radius:10px;font-weight:600;cursor:pointer;font-size:12px}
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
<script src="/static/js/script.js"></script>
</body>
</html>
