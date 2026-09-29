# Exness XAUUSD Live Market Data Dashboard

A **local-only, read-only live market data terminal** that receives real-time **XAUUSD (Gold)** market data from an Exness-connected MetaTrader 5 desktop terminal and displays it in a modern trading dashboard built with Next.js and TradingView Lightweight Charts.

---

## ⚡ How to Start (Quick Guide)

### Option 1: One-Click Startup (Recommended for Linux)
Run the automated launcher from the project root:
```bash
./start.sh
```
This automatically starts:
1. MetaTrader 5 Desktop Terminal in Wine
2. Python MT5 Live WebSocket/REST Backend (`http://127.0.0.1:8000`)
3. Next.js Frontend (`http://localhost:3000`)

---

### Option 2: Step-by-Step Manual Startup (Linux / Kali via Wine)

#### Step 1: Start MetaTrader 5 Terminal
```bash
DISPLAY=:0.0 WINEARCH=win64 WINEPREFIX=$HOME/.wine_mt5 wine "$HOME/.wine_mt5/drive_c/Program Files/MetaTrader 5/terminal64.exe" &
```
*(Make sure `XAUUSD` is visible in Market Watch and your Exness account is logged in).*

#### Step 2: Start Python Backend (Wine IPC Bridge)
In a new terminal:
```bash
cd /home/bhoot/Desktop/tread/backend
WINEARCH=win64 WINEPREFIX=$HOME/.wine_mt5 wine "C:\\Python311\\python.exe" -m uvicorn app.main:app --app-dir "/home/bhoot/Desktop/tread/backend" --host 127.0.0.1 --port 8000
```

#### Step 3: Start Next.js Frontend
In a new terminal:
```bash
cd /home/bhoot/Desktop/tread/frontend
npm run dev
```

#### Step 4: Open Browser
👉 Open **[http://localhost:3000](http://localhost:3000)** in your browser.

---

### Option 3: Manual Startup on Windows (Native MT5)

#### Step 1: Start MT5
Open the MetaTrader 5 desktop application and log in to your Exness account.

#### Step 2: Start Backend
```cmd
cd backend
.venv\Scripts\activate
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

#### Step 3: Start Frontend
```cmd
cd frontend
npm run dev
```

---

## 🔒 Strict Scope & Security Guarantee

* **Market-Data Only**: This application is strictly for market-data visualization.
* **Zero Trading Operations**: It does NOT place trades, modify orders, cancel positions, access account balance, access equity, calculate margin, or perform any trading action whatsoever.
* **Local-Only**: Runs 100% locally on your machine with no external cloud servers, databases, or paid market data providers.

---

## 🏛️ System Architecture

```text
                    EXNESS
                       │
                       ▼
               MetaTrader 5
               Desktop Terminal
                       │  (IPC Tick Stream)
                       ▼
             Python FastAPI Backend
             (Symbol Discovery & Aggregation)
                       │
             ┌─────────┴─────────┐
             │                   │
        REST API            WebSocket
     (OHLC History)       (Live Ticks & 1m/5m Candles)
             │                   │
             └─────────┬─────────┘
                       ▼
                Next.js Frontend
          (Lightweight Charts + Live Tickers)
                       │
                       ▼
              http://localhost:3000
```

---

## 📦 Project Structure

```text
.
├── start.sh                     # One-click startup script for Linux
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app & WebSocket endpoint
│   │   ├── config.py            # Pydantic settings & env loader
│   │   ├── mt5_client.py        # MT5 connector & XAUUSD symbol resolver
│   │   ├── market_data.py       # Tick polling loop & broadcast coordinator
│   │   ├── candles.py           # Real-time 1m & 5m OHLC candle aggregators
│   │   ├── websocket_manager.py # WebSocket client manager
│   │   └── routes/
│   │       ├── health.py        # /health endpoint
│   │       └── market.py        # /api/market/xauusd/tick, /candles, /info
│   ├── tests/
│   │   └── test_backend.py      # Unit & integration tests
│   ├── requirements.txt         # Python dependencies
│   ├── .env.example             # Backend environment template
│   └── .env                     # Local backend configuration
│
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   │   ├── layout.tsx       # Root layout & dark terminal theme
│   │   │   ├── page.tsx         # Main dashboard page
│   │   │   └── globals.css      # Tailwind styles & theme
│   │   ├── components/
│   │   │   ├── market/
│   │   │   │   ├── Header.tsx       # MT5 & WS status badges, clocks
│   │   │   │   ├── PriceDisplay.tsx # Prominent Bid/Ask, spread, 24h stats
│   │   │   │   ├── TickStream.tsx   # Live scrolling tick feed
│   │   │   │   └── MarketStats.tsx  # Symbol specifications & scope
│   │   │   ├── charts/
│   │   │   │   └── CandlestickChart.tsx # Lightweight Charts real-time candlestick
│   │   │   └── ui/
│   │   │       └── ConnectionBanner.tsx # Disconnection & reconnect alerts
│   │   ├── hooks/
│   │   │   └── useMarketWebSocket.ts    # WebSocket hook with backoff reconnect
│   │   ├── lib/
│   │   │   ├── api.ts          # REST client helpers
│   │   │   └── config.ts       # Frontend configuration
│   │   └── types/
│   │       └── market.ts       # TypeScript data interfaces
│   ├── package.json
│   ├── .env.local.example      # Frontend environment template
│   └── .env.local              # Local frontend configuration
│
├── README.md
└── .gitignore
```

---

## 🔍 Features & Behavior

### 1. Symbol Discovery
The backend does not hardcode symbol names. It automatically scans MT5 for candidate symbols:
* `XAUUSD`
* `XAUUSDm` (Exness Mini)
* `XAUUSD.` / `XAUUSD#` / `XAUUSD_i` / `XAUUSD.ecn` / `XAUUSD.pro`
* `GOLD`

It enables the symbol in Market Watch and exposes it to the dashboard.

### 2. Real-Time Candlestick Charting
* Built with **TradingView Lightweight Charts** for high-performance 60fps canvas rendering.
* Supports **1-minute (`1m`)** and **5-minute (`5m`)** timeframes.
* Real-time forming candle updates: dynamically modifies the active candle as ticks arrive without redrawing historical candles.
* Zoom, pan, crosshair tooltip (OHLC, Change), fit content, and manual refresh.

### 3. Connection & Resilience
* **MT5 Disconnection**: Clearly displays `● MT5 Disconnected` status and alert banner.
* **WebSocket Reconnection**: Automatically reconnects with exponential backoff (`1s → 2s → 4s → 8s → 16s → max 30s`).
* **Stale Data Warning**: Flags market data as `STALE DATA` if no tick has arrived beyond the configured threshold (default 5.0 seconds).
* **Simulation Fallback Mode**: When running on development machines without MT5 or when testing offline, a realistic Brownian gold tick generator can be enabled via `MT5_MOCK_FALLBACK=true` in `.env`.

---

## 🧪 Running Tests

Run backend tests:
```bash
cd backend
PYTHONPATH=. .venv/bin/pytest tests/test_backend.py -v
```

Run frontend type check & build:
```bash
cd frontend
npm run build
```

---

## ⚙️ Configuration Reference

### Backend (`backend/.env`)

| Variable | Default | Description |
|---|---|---|
| `BACKEND_HOST` | `127.0.0.1` | Local bind address |
| `BACKEND_PORT` | `8000` | Local port |
| `MT5_SYMBOL` | `XAUUSD` | Preferred Gold symbol |
| `HISTORICAL_CANDLE_COUNT` | `300` | Number of historical candles |
| `TICK_POLL_INTERVAL_MS` | `100` | Polling frequency in milliseconds |
| `STALE_DATA_THRESHOLD_SECONDS` | `5.0` | Stale data threshold |
| `MT5_PATH` | `C:\Program Files\MetaTrader 5\terminal64.exe` | Path to MT5 terminal executable |
| `MT5_MOCK_FALLBACK` | `false` | Fallback if MT5 not connected (`false` for live real data) |

### Frontend (`frontend/.env.local`)

| Variable | Default | Description |
|---|---|---|
| `NEXT_PUBLIC_BACKEND_URL` | `http://localhost:8000` | REST API endpoint |
| `NEXT_PUBLIC_WS_URL` | `ws://localhost:8000/ws/market/xauusd` | WebSocket stream URL |

