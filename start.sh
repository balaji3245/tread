#!/usr/bin/env bash

# Exness XAUUSD Live Market Data Dashboard - One-Click Launcher
set -e

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd "$DIR"

echo "=========================================================="
echo "  🚀 Starting Exness XAUUSD Live Market Data Dashboard"
echo "=========================================================="

# 1. Start MetaTrader 5 in Wine (if not already running)
if pgrep -f "terminal64.exe" > /dev/null; then
    echo "✔ MetaTrader 5 terminal is already running."
else
    echo "➤ Launching MetaTrader 5 desktop terminal in Wine..."
    DISPLAY="${DISPLAY:-:0.0}" WINEARCH=win64 WINEPREFIX="$HOME/.wine_mt5" wine "$HOME/.wine_mt5/drive_c/Program Files/MetaTrader 5/terminal64.exe" > /dev/null 2>&1 &
    sleep 3
fi

# 2. Start Wine Python FastAPI Backend in background
echo "➤ Starting Python MT5 Live Backend on http://127.0.0.1:8000..."
WINEARCH=win64 WINEPREFIX="$HOME/.wine_mt5" wine "C:\\Python311\\python.exe" -m uvicorn app.main:app --app-dir "$DIR/backend" --host 127.0.0.1 --port 8000 --reload &
BACKEND_PID=$!

cleanup() {
    echo ""
    echo "🛑 Shutting down dashboard services..."
    kill $BACKEND_PID 2>/dev/null || true
    exit 0
}
trap cleanup SIGINT SIGTERM EXIT

sleep 2

# 3. Start Next.js Frontend
echo "➤ Starting Next.js Frontend on http://localhost:3000..."
echo "👉 Open http://localhost:3000 in your browser"
echo "=========================================================="
cd "$DIR/frontend"
npm run dev
