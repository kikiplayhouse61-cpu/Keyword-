# 🤖 GC Keyword Alert System

Telegram groups monitor karo — jab bhi koi configured keyword send kare, turant notification milegi apne private bot pe.

---

## ✅ Features

- Apne joined groups automatically monitor karta hai
- Case-insensitive multi-word keyword matching
- Single static dashboard — ek hi message, bar bar update hota hai
- Alert history, statistics, keyword management — sab Telegram se
- SQLite persistent database — Railway restart ke baad bhi data safe
- Telethon StringSession — har baar login nahi karna padta
- Rate limit handling, dedup protection, auto-reconnect

---

## 📋 Step 1 — Zaruri cheezein banao

### 1A. Telegram API credentials lo

1. `https://my.telegram.org/apps` kholo apne mobile browser mein
2. Apne Telegram number se login karo
3. "Create Application" pe click karo
4. `API ID` aur `API Hash` copy karo — ye dono chahiye

### 1B. Bot banao

1. Telegram mein `@BotFather` search karo
2. `/newbot` bhejo
3. Bot ka naam aur username daal do
4. `Bot Token` copy karo (format: `123456789:AAABBB...`)

### 1C. Apna Telegram ID pata karo

1. `@userinfobot` pe `/start` bhejo
2. Wahan `Id:` ke aage jo number hai, copy karo — ye tera `OWNER_ID` hai

---

## 📋 Step 2 — Session generate karo (sirf ek baar, apne PC ya laptop pe)

> ⚠️ Ye step apne **personal computer** pe karna hai, Railway pe nahi.
> Agar PC nahi hai, kisi friend ke PC pe karo ya Termux (Android) use karo.

### Termux se karna hai toh:

```bash
pkg update && pkg install python git
pip install telethon
git clone https://github.com/TERA_USERNAME/telegram-keyword-alert
cd telegram-keyword-alert
python scripts/generate_session.py
```

Script kuch aise dikhega:
```
Enter your API_ID: 12345678
Enter your API_HASH: abcdef123456...
```

Phir phone number maangega, OTP maangega — sab daal do.

Script ek **Session String** print karega (1BVtsOKABu... aisa kuch).

> 🔒 Ye session string bilkul secret hai. Kisi ko mat batana. GitHub pe mat daalna.

---

## 📋 Step 3 — GitHub repository banao

1. `https://github.com` pe jao, login karo
2. `+` icon → `New repository` → naam do `telegram-keyword-alert` → `Create`
3. Files upload karo:
   - GitHub repository mein `Add file → Upload files` click karo
   - Poora project folder select karo aur upload karo
   - Commit karo

Ya Termux/PC se git use karo:
```bash
cd telegram-keyword-alert
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/TERA_USERNAME/telegram-keyword-alert.git
git push -u origin main
```

> ⚠️ `.env` file aur `.session` files kabhi GitHub pe mat daalna — `.gitignore` already handle kar raha hai.

---

## 📋 Step 4 — Railway pe deploy karo

1. `https://railway.app` kholo
2. GitHub se login karo
3. `New Project → Deploy from GitHub repo` → apni repo select karo
4. Project ban jayega

### Volume add karo (database ke liye):

1. Railway project mein `+ New` click karo → `Volume`
2. Mount path daalo: `/data`
3. Volume project se attach karo

### Environment variables daalo:

Railway project → `Variables` tab → Ye sab add karo:

| Variable | Value |
|---|---|
| `API_ID` | Tera API ID (number) |
| `API_HASH` | Tera API Hash |
| `BOT_TOKEN` | BotFather se mila token |
| `OWNER_ID` | Tera Telegram ID |
| `TELETHON_SESSION_STRING` | Step 2 mein generate hua string |
| `DATABASE_PATH` | `/data/keyword_alert.db` |
| `TIMEZONE` | `Asia/Kolkata` |
| `LOG_LEVEL` | `INFO` |

5. Variables save karo → Railway automatically redeploy karega
6. `Logs` tab mein dekho — `System fully operational` aana chahiye

---

## 📋 Step 5 — Bot use karna

1. Apne bot ko Telegram mein search karo (jo BotFather ne banaya)
2. `/start` bhejo
3. Dashboard appear hoga

### Dashboard buttons:

| Button | Kya karta hai |
|---|---|
| ▶️ START | Monitoring shuru karo |
| ⏹ STOP | Monitoring pause karo |
| ➕ Add Keyword | Naya keyword add karo |
| ➖ Remove Keyword | Keyword delete karo |
| 🔑 My Keywords | Sare keywords dekho / enable-disable karo |
| 👥 My Groups | Monitored groups dekho |
| 📜 Alert History | Purane alerts dekho |
| 📊 Statistics | Stats dekho |
| ⚙️ Settings | Notifications on/off, history clear karo |
| 🔄 Refresh | Dashboard refresh karo |

---

## 📋 Troubleshooting

### "Session is not authorized" error

Session string expire ho gayi. Dobara `scripts/generate_session.py` chalaao aur naya session Railway mein daalo.

### "database is locked" error

Purana version tha — ye version fix kar diya hai WAL mode se.

### "No such column: id" error

Database migration issue tha — is version mein auto-migration hai, delete nahi hoga data.

### Bot respond nahi kar raha

1. Railway logs dekho
2. BOT_TOKEN sahi hai ya nahi check karo
3. Bot ko `/start` bhejo — `OWNER_ID` match hona chahiye

### Groups nahi dikh rahe

Dashboard → ⚙️ Settings → 🔄 Reload Groups dabao.
Naye groups tabhi dikhenge jab unse koi message aaye ya reload karo.

### Railway pe band ho gaya

Railway free tier pe `$5/month` credit deta hai. Paid plan lo ya `Railway Hobby` use karo for 24/7 uptime.

---

## 📋 Testing (optional, development ke liye)

```bash
pip install pytest pytest-asyncio
python -m pytest tests/ -v
```

---

## 📁 Project Structure

```
telegram-keyword-alert/
├── app/
│   ├── config.py          # Environment variables
│   ├── database.py        # SQLite operations
│   ├── dashboard.py       # Dashboard text builder
│   ├── handlers.py        # Bot command & callback handlers
│   ├── keyboards.py       # Inline keyboard layouts
│   ├── monitoring.py      # Monitoring state
│   ├── notifications.py   # Alert queue & formatting
│   ├── scheduler.py       # Periodic cleanup tasks
│   ├── telegram_bot.py    # PTB application setup
│   ├── telegram_user.py   # Telethon userbot
│   └── utils.py           # Helpers (time, matching, pagination)
├── scripts/
│   └── generate_session.py   # Local session generator
├── tests/
│   ├── test_database.py
│   ├── test_keywords.py
│   └── test_notifications.py
├── main.py                # Entry point
├── requirements.txt
├── Dockerfile
├── railway.json
├── .env.example
├── .gitignore
└── README.md
```

---

## 🔒 Security Notes

- Session string kisi ko mat batana
- `.env` file GitHub pe mat daalna
- Sirf `OWNER_ID` wala user dashboard control kar sakta hai
- Sare other users ko `⛔ Unauthorized` milega

---

## 📞 Support

Kuch kaam nahi kar raha toh Railway logs (`Logs` tab) dekho — wahan exact error milega.
