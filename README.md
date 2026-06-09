# 🤖 RASCH TEST BOT — O'RNATISH YO'RIQNOMASI

## 📋 TALABLAR
- Python 3.10+
- pip

---

## 🚀 O'RNATISH (LOKAL)

### 1. Papkaga kiring
```bash
cd rasch_bot/bot
```

### 2. Virtual muhit yarating
```bash
python -m venv venv
source venv/bin/activate        # Linux/Mac
venv\Scripts\activate           # Windows
```

### 3. Kutubxonalarni o'rnating
```bash
pip install -r ../requirements.txt
```

### 4. config.py ni tahrirlang
```python
BOT_TOKEN = "YANGI_TOKENINGIZ"       # ⚠️ MUHIM!
CARD_OWNER = "Ism Familiya"          # Karta egasi
```

### 5. Botni ishga tushiring
```bash
python main.py
```

---

## ☁️ RAILWAY DA DEPLOY QILISH (BEPUL)

### 1. railway.app ga kiring
### 2. GitHub ga yuklang (yoki ZIP yuklang)
### 3. Environment Variables qo'shing:
```
BOT_TOKEN = yangi_tokeningiz
```
### 4. Start command:
```
pip install -r requirements.txt && cd bot && python main.py
```

---

## 👨‍💼 ADMIN BUYRUQLARI

| Buyruq | Vazifa |
|--------|--------|
| `/admin` | Admin panel |
| `/addquestion` | Yangi savol qo'shish |
| `/setdaily` | Savollar ro'yxatini ko'rish |
| `/confirmdaily 1,2,3` | Bugungi test belgilash |
| `/stats` | Wright Map statistika |

---

## 📱 FOYDALANUVCHI MENYUSI

| Tugma | Vazifa |
|-------|--------|
| 📝 Bugungi test | Testni boshlash |
| 📊 Mening natijalarim | Shaxsiy statistika |
| 🏆 Reyting | Top-10 reyting |
| 💳 To'lov | To'lov qilish |
| ℹ️ Bot haqida | Rasch modeli haqida |

---

## 💳 TO'LOV JARAYONI

1. Foydalanuvchi "💳 To'lov" bosadi
2. Tur tanlaydi (7,000 yoki 20,000 so'm)
3. Karta raqami ko'rsatiladi
4. Foydalanuvchi pul o'tkazadi → screenshot yuboradi
5. Admin botga screenshot keladi
6. Admin "✅ Tasdiqlash" bosadi
7. Foydalanuvchiga ruxsat beriladi

---

## 🧮 RASCH MODELI

**Formula:** `P(to'g'ri) = e^(θ-b) / (1 + e^(θ-b))`

- **θ (theta)** — foydalanuvchi qobiliyati (-4 dan +4)
- **b** — savol qiyinlik darajasi (-4 dan +4)

**Savol qo'shishda b qiymati:**
- `-2.0` → Juda oson
- `0.0` → O'rta qiyinlikdagi
- `+2.0` → Juda qiyin

---

## ⚠️ MUHIM ESLATMALAR

1. **Token** ni hech kimga ko'rsatmang
2. **Karta raqami** ni bot kodi ichida saqlang — suhbatda yubormang
3. Railway bepul rejimda har oyda 500 soat ishlaydi
4. SQLite lokal uchun yaxshi, production uchun PostgreSQL tavsiya etiladi

---

## 📞 Murojaat: @rodrygo_11goes
