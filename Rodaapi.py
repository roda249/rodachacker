@app.route("/api/admin/change_master", methods=["POST"])
def change_master():
    data = request.json
    old_key = data.get("old_key")
    new_key = data.get("new_key")
    
    # Eski şifre doğrulaması
    if old_key != MASTER_KEY:
        return jsonify({"success": False, "error": "Eski şifre yanlış!"}), 401
    
    if not new_key or len(new_key) < 8:
        return jsonify({"success": False, "error": "Yeni şifre en az 8 karakter olmalı!"}), 400
    
    # Yeni şifreyi base64 encode et ve kaydet
    encoded = base64.b64encode(new_key.encode('utf-8')).decode('utf-8')
    
    # MASTER_KEY'i güncelle (kalıcı olarak dosyaya yaz)
    with open("master.key", "w", encoding="utf-8") as f:
        f.write(encoded)
    
    # Global değişkeni güncelle
    global MASTER_KEY
    MASTER_KEY = new_key
    
    return jsonify({"success": True, "message": "Master key başarıyla değiştirildi!"})
