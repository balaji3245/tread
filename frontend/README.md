# Exness XAUUSD Dashboard (Next.js Frontend)

This is the Next.js trading frontend for the **Exness XAUUSD Live Market Data Dashboard**.

---

## ⚡ How to Start the Entire Application

### Option 1: One-Click Startup Script (From Project Root)
```bash
cd ..
./start.sh
```

---

### Option 2: Manual Step-by-Step

#### 1. Start MetaTrader 5 Terminal (Background)
```bash
DISPLAY=:0.0 WINEARCH=win64 WINEPREFIX=$HOME/.wine_mt5 wine "$HOME/.wine_mt5/drive_c/Program Files/MetaTrader 5/terminal64.exe" &
```

#### 2. Start Python Backend (Wine IPC Bridge)
In a separate terminal:
```bash
cd ../backend
WINEARCH=win64 WINEPREFIX=$HOME/.wine_mt5 wine "C:\\Python311\\python.exe" -m uvicorn app.main:app --app-dir "/home/bhoot/Desktop/tread/backend" --host 127.0.0.1 --port 8000
```

#### 3. Start Next.js Frontend
In a separate terminal:
```bash
npm run dev
```

Open your browser at:
👉 **[http://localhost:3000](http://localhost:3000)**

---

## 🛠️ Build for Production

```bash
npm run build
npm start
```
