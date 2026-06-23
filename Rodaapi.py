<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ROADA v3.0</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            background: #0a0e17;
            color: #00ffc8;
            font-family: 'Segoe UI', Tahoma, sans-serif;
            padding: 20px;
            min-height: 100vh;
        }
        .container { max-width: 1400px; margin: 0 auto; }
        h1 { color: #00ffc8; text-shadow: 0 0 20px #00ffc8; margin-bottom: 10px; font-size: 2.5rem; }
        .sub { color: #8899aa; margin-bottom: 30px; }
        
        .flex-row { display: flex; gap: 15px; flex-wrap: wrap; }
        .platform-grid {
            display: grid;
            grid-template-columns: repeat(5, 1fr);
            gap: 8px;
            background: #111b26;
            padding: 15px;
            border-radius: 12px;
            border: 1px solid #1f3a4b;
            flex: 2;
            min-width: 300px;
        }
        .platform-btn {
            background: #162230;
            color: #7a9bb5;
            border: 1px solid #1f3a4b;
            padding: 8px 5px;
            border-radius: 6px;
            cursor: pointer;
            font-size: 13px;
            text-align: center;
            transition: 0.2s;
        }
        .platform-btn:hover, .platform-btn.active {
            background: #00ffc8;
            color: #0a0e17;
            border-color: #00ffc8;
            box-shadow: 0 0 15px #00ffc855;
        }
        .platform-btn.test-btn { background: #2a3f4f; color: #ffaa00; border-color: #ffaa00; }
        .platform-btn.test-btn:hover { background: #ffaa00; color: #0a0e17; }

        .stats-box {
            background: #111b26;
            border: 1px solid #1f3a4b;
            border-radius: 12px;
            padding: 20px;
            flex: 1;
            min-width: 250px;
        }
        .stats-grid { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 10px; }
        .stat-item { text-align: center; }
        .stat-num { font-size: 28px; font-weight: bold; }
        .stat-label { font-size: 12px; color: #8899aa; }

        .input-area {
            margin: 20px 0;
            display: flex;
            gap: 15px;
            flex-wrap: wrap;
        }
        .input-area textarea {
            flex: 3;
            min-height: 120px;
            background: #0d1620;
            color: #00ffc8;
            border: 1px solid #1f3a4b;
            border-radius: 8px;
            padding: 12px;
            font-family: monospace;
            font-size: 14px;
            resize: vertical;
        }
        .action-buttons {
            display: flex;
            flex-direction: column;
            gap: 10px;
            flex: 1;
        }
        .btn {
            padding: 12px 25px;
            border: none;
            border-radius: 8px;
            font-weight: bold;
            cursor: pointer;
            transition: 0.2s;
            font-size: 16px;
        }
        .btn-start { background: #00c8a0; color: #0a0e17; }
        .btn-start:hover { background: #00ffc8; box-shadow: 0 0 30px #00ffc866; }
        .btn-stop { background: #ff4444; color: white; }
        .btn-stop:hover { background: #ff6666; }

        .logs-container {
            background: #0d1620;
            border: 1px solid #1f3a4b;
            border-radius: 12px;
            padding: 10px;
            margin: 20px 0;
        }
        .logs-header { display: flex; justify-content: space-between; margin-bottom: 5px; color: #8899aa; }
        .logs-box {
            height: 350px; /* BÜYÜK LOG ALANI */
            overflow-y: scroll;
            background: #050a10;
            border-radius: 8px;
            padding: 10px;
            font-family: 'Courier New', monospace;
            font-size: 13px;
            color: #bbd9e6;
            white-space: pre-wrap;
            word-break: break-all;
        }
        .logs-box::-webkit-scrollbar { width: 6px; }
        .logs-box::-webkit-scrollbar-track { background: #0a0e17; }
        .logs-box::-webkit-scrollbar-thumb { background: #00ffc8; border-radius: 10px; }

        .result-tabs {
            display: flex;
            gap: 5px;
            margin-top: 10px;
        }
        .tab-btn {
            background: #162230;
            color: #7a9bb5;
            border: 1px solid #1f3a4b;
            padding: 6px 15px;
            border-radius: 20px;
            cursor: pointer;
        }
        .tab-btn.active { background: #00ffc8; color: #0a0e17; }
        .result-content {
            background: #0d1620;
            border: 1px solid #1f3a4b;
            border-radius: 8px;
            padding: 10px;
            max-height: 200px;
            overflow-y: auto;
            font-size: 13px;
            font-family: monospace;
            margin-top: 10px;
        }

        @media (max-width: 700px) { .platform-grid { grid-template-columns: repeat(3, 1fr); } }
    </style>
</head>
<body>
<div class="container">
    <h1>🔓 ROADA v3.0</h1>
    <div class="sub">Checker | Proxy Destekli | 2FA Ayrıştırmalı | Webhook</div>

    <div class="flex-row">
        <!-- Platformlar -->
        <div class="platform-grid" id="platformGrid">
            <!-- Sol -->
            <div class="platform-btn active" data-platform="steam">Steam</div>
            <div class="platform-btn" data-platform="youtube">YouTube</div>
            <div class="platform-btn" data-platform="tiktok">TikTok</div>
            <div class="platform-btn" data-platform="spotify">Spotify</div>
            <div class="platform-btn" data-platform="roblox">Roblox</div>
            <div class="platform-btn" data-platform="netflix">Netflix</div>
            <div class="platform-btn" data-platform="capcut">CapCut</div>
            <div class="platform-btn" data-platform="discord">Discord</div>
            <div class="platform-btn" data-platform="epicgames">Epic Games</div>
            <div class="platform-btn" data-platform="hasepcom">Hasepcom.tr</div>
            <!-- Sağ -->
            <div class="platform-btn" data-platform="itemsatis">Itemsatış</div>
            <div class="platform-btn" data-platform="epinity">Epinity</div>
            <div class="platform-btn" data-platform="twitch">Twitch</div>
            <div class="platform-btn" data-platform="playstation">PlayStation</div>
            <div class="platform-btn" data-platform="xbox">Xbox</div>
            <div class="platform-btn" data-platform="github">GitHub</div>
            <div class="platform-btn" data-platform="valorant">Valorant</div>
            <div class="platform-btn" data-platform="minecraft">Minecraft</div>
            <div class="platform-btn" data-platform="duolingo">Duolingo</div>
            <div class="platform-btn" data-platform="pubg">PUBG</div>
            <!-- TEST BUTONU -->
            <div class="platform-btn test-btn" id="testConnectionBtn" style="grid-column: span 2;">🔌 Test Steam Connection</div>
        </div>

        <!-- İstatistikler -->
        <div class="stats-box">
            <div class="stats-grid">
                <div class="stat-item"><div class="stat-num" id="total">0</div><div class="stat-label">Toplam</div></div>
                <div class="stat-item"><div class="stat-num" id="success" style="color:#00ff88;">0</div><div class="stat-label">Başarılı</div></div>
                <div class="stat-item"><div class="stat-num" id="fail" style="color:#ff4444;">0</div><div class="stat-label">Başarısız</div></div>
                <div class="stat-item"><div class="stat-num" id="twofa" style="color:#ffaa00;">0</div><div class="stat-label">2FA</div></div>
                <div class="stat-item"><div class="stat-num" id="error" style="color:#ff66aa;">0</div><div class="stat-label">Hata</div></div>
                <div class="stat-item"><div class="stat-num" id="remaining">0</div><div class="stat-label">Kalan</div></div>
            </div>
        </div>
    </div>

    <!-- Combo Giriş ve Butonlar -->
    <div class="input-area">
        <textarea id="comboInput" placeholder="kullanici_adi:sifre&#10;kullanici2:sifre2&#10;..."></textarea>
        <div class="action-buttons">
            <button class="btn btn-start" id="startBtn">▶ BAŞLAT</button>
            <button class="btn btn-stop" id="stopBtn">⏹ DURDUR</button>
            <span style="color:#8899aa;font-size:12px;">Proxy: <span id="proxyStatus">Yükleniyor...</span></span>
        </div>
    </div>

    <!-- LOG ALANI (BÜYÜK) -->
    <div class="logs-container">
        <div class="logs-header"><span>📋 Sistem Logları</span><span id="logCount">0</span></div>
        <div class="logs-box" id="logBox">🟢 Sistem hazır. Proxy'ler yükleniyor...</div>
    </div>

    <!-- Sonuçlar (HIT & 2FA Arşivi) -->
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

    // Platform seçimi
    document.querySelectorAll('.platform-btn:not(.test-btn)').forEach(btn => {
        btn.addEventListener('click', function() {
            document.querySelectorAll('.platform-btn:not(.test-btn)').forEach(b => b.classList.remove('active'));
            this.classList.add('active');
            selectedPlatform = this.dataset.platform;
        });
    });

    // Test Connection
    document.getElementById('testConnectionBtn').addEventListener('click', async function() {
        const platform = selectedPlatform;
        addLog(`🔌 ${platform} bağlantısı test ediliyor...`);
        try {
            const resp = await fetch('/test_connection', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ platform: platform })
            });
            const data = await resp.json();
            addLog(`✅ Test sonucu: ${data.message}`);
        } catch(e) {
            addLog(`❌ Test hatası: ${e.message}`);
        }
    });

    // Başlat
    document.getElementById('startBtn').addEventListener('click', async function() {
        const combos = document.getElementById('comboInput').value;
        if (!combos.trim()) {
            alert('Lütfen combo girin!');
            return;
        }
        addLog(`🚀 ${selectedPlatform} kontrolü başlatılıyor...`);
        try {
            const resp = await fetch('/start', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ platform: selectedPlatform, combos: combos })
            });
            const data = await resp.json();
            if (data.error) {
                addLog(`❌ Hata: ${data.error}`);
            } else {
                addLog(`✅ Başlatıldı. Toplam: ${data.total} hesap.`);
                if (updateInterval) clearInterval(updateInterval);
                updateInterval = setInterval(fetchStatus, 1000);
            }
        } catch(e) {
            addLog(`❌ Başlatma hatası: ${e.message}`);
        }
    });

    // Durdur
    document.getElementById('stopBtn').addEventListener('click', async function() {
        try {
            await fetch('/stop', { method: 'POST' });
            addLog('⏹️ Kontrol durduruldu.');
            if (updateInterval) clearInterval(updateInterval);
        } catch(e) {
            addLog(`❌ Durdurma hatası: ${e.message}`);
        }
    });

    // Durum çekme
    async function fetchStatus() {
        try {
            const resp = await fetch('/status');
            const data = await resp.json();
            
            document.getElementById('total').textContent = data.total || 0;
            document.getElementById('success').textContent = data.success || 0;
            document.getElementById('fail').textContent = data.fail || 0;
            document.getElementById('twofa').textContent = data.twofa || 0;
            document.getElementById('error').textContent = data.error || 0;
            document.getElementById('remaining').textContent = data.remaining || 0;
            document.getElementById('logCount').textContent = (data.logs || []).length;

            // Logları göster (en son 30)
            if (data.logs && data.logs.length > 0) {
                const logBox = document.getElementById('logBox');
                const lastLogs = data.logs.slice(-30);
                logBox.innerHTML = lastLogs.join('\n');
                logBox.scrollTop = logBox.scrollHeight;
            }

            // HIT ve 2FA listelerini güncelle
            if (data.hits && data.hits.length > 0) {
                document.getElementById('hitsContent').innerHTML = data.hits.join('\n');
            }
            if (data.twofa_list && data.twofa_list.length > 0) {
                document.getElementById('twofaContent').innerHTML = data.twofa_list.join('\n');
            }

            if (!data.is_running) {
                if (updateInterval) clearInterval(updateInterval);
                if (data.total > 0 && data.remaining === 0) {
                    addLog('🏁 Tüm işlemler tamamlandı!');
                }
            }
        } catch(e) {
            console.error('Status fetch error', e);
        }
    }

    function addLog(msg) {
        const logBox = document.getElementById('logBox');
        const timestamp = new Date().toLocaleTimeString();
        logBox.innerHTML += `\n[${timestamp}] ${msg}`;
        logBox.scrollTop = logBox.scrollHeight;
    }

    // Proxy durumu kontrolü
    async function loadProxyStatus() {
        try {
            const resp = await fetch('/status');
            const data = await resp.json();
            // Proxy sayısını almak için ayrı bir endpoint yok, ama dosyadan okuyalım.
            const proxyResp = await fetch('/test_connection', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify({platform:'dummy'})});
            const proxyData = await proxyResp.json();
            document.getElementById('proxyStatus').textContent = 'Proxy durumu kontrol edildi.';
        } catch(e) {
            document.getElementById('proxyStatus').textContent = 'Proxy yüklenemedi.';
        }
    }
    loadProxyStatus();

    // Tab geçişleri
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
            this.classList.add('active');
            const tab = this.dataset.tab;
            document.getElementById('hitsContent').style.display = tab === 'hits' ? 'block' : 'none';
            document.getElementById('twofaContent').style.display = tab === 'twofa' ? 'block' : 'none';
        });
    });

    // İlk log
    addLog('🟢 ROADA v3.0 hazır. Proxy\'ler yükleniyor...');
</script>
</body>
</html>
