"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { ConnectionState, WsStatusData } from "@/types/market";
import { Activity, AlertTriangle, CheckCircle2, Clock, FlaskConical, History, LayoutDashboard, Microscope, RefreshCw, Server, ShieldCheck, Wifi, WifiOff } from "lucide-react";
import { STALE_DATA_THRESHOLD_SECONDS } from "@/lib/config";

interface HeaderProps {
  symbol: string;
  connectionState: ConnectionState;
  mt5Status: WsStatusData;
  lastMessageTime: number;
  reconnectAttempt: number;
  onReconnect: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  symbol,
  connectionState,
  mt5Status,
  lastMessageTime,
  reconnectAttempt,
  onReconnect,
}) => {
  const pathname = usePathname();
  const [mounted, setMounted] = useState<boolean>(false);
  const [now, setNow] = useState<number>(0);

  useEffect(() => {
    setMounted(true);
    setNow(Date.now());
    const timer = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(timer);
  }, []);

  const elapsedSeconds = mounted && lastMessageTime > 0 ? (now - lastMessageTime) / 1000 : 999;
  const isStale = mounted && lastMessageTime > 0 && elapsedSeconds > STALE_DATA_THRESHOLD_SECONDS;

  // Format UTC and Local time safely on client
  const timeUTC = mounted && now > 0 ? new Date(now).toUTCString().slice(17, 25) + " UTC" : "--:--:-- UTC";
  const timeLocal = mounted && now > 0 ? new Date(now).toLocaleTimeString() : "--:--:--";

  return (
    <header className="w-full bg-neutral-950 border-b border-neutral-800/80 px-4 py-3 flex flex-wrap items-center justify-between gap-4 sticky top-0 z-40 shadow-xl backdrop-blur-md bg-neutral-950/90">
      {/* Left: Branding & Nav Tabs */}
      <div className="flex items-center gap-5">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-amber-400 via-amber-500 to-yellow-600 flex items-center justify-center font-bold text-neutral-950 shadow-lg shadow-amber-500/20 text-sm tracking-wider">
            Au
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-xl font-black tracking-tight text-white font-mono">
                {symbol || "XAUUSD"}
              </h1>
              <span className="text-[10px] uppercase font-bold tracking-widest px-2 py-0.5 rounded bg-amber-500/10 text-amber-400 border border-amber-500/30">
                Gold / USD
              </span>
              {mt5Status.is_mock && (
                <span className="text-[10px] uppercase font-bold tracking-widest px-1.5 py-0.5 rounded bg-blue-500/10 text-blue-400 border border-blue-500/30">
                  Simulation
                </span>
              )}
            </div>
            <p className="text-[11px] text-neutral-400 font-medium flex items-center gap-1.5">
              <span>Exness MT5 Live Market Feed</span>
              <span className="text-neutral-600">•</span>
              <span className="text-neutral-500">Read-Only Terminal</span>
            </p>
          </div>
        </div>

        {/* Navigation Tabs */}
        <nav className="hidden sm:flex items-center bg-neutral-900/90 border border-neutral-800 p-1 rounded-xl font-mono text-xs">
          <Link
            href="/"
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg font-bold transition ${
              pathname === "/"
                ? "bg-amber-500 text-neutral-950 shadow-md"
                : "text-neutral-400 hover:text-white"
            }`}
          >
            <LayoutDashboard className="w-3.5 h-3.5" />
            <span>Live Terminal</span>
          </Link>
          <Link
            href="/backtest"
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg font-bold transition ${
              pathname === "/backtest"
                ? "bg-amber-500 text-neutral-950 shadow-md"
                : "text-neutral-400 hover:text-white"
            }`}
          >
            <History className="w-3.5 h-3.5" />
            <span>Backtest</span>
          </Link>
          <Link
            href="/validation"
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg font-bold transition ${
              pathname === "/validation"
                ? "bg-amber-500 text-neutral-950 shadow-md"
                : "text-neutral-400 hover:text-white"
            }`}
          >
            <ShieldCheck className="w-3.5 h-3.5" />
            <span>Validation</span>
          </Link>
          <Link
            href="/forensics"
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg font-bold transition ${
              pathname === "/forensics"
                ? "bg-amber-500 text-neutral-950 shadow-md"
                : "text-neutral-400 hover:text-white"
            }`}
          >
            <Microscope className="w-3.5 h-3.5" />
            <span>Signal Forensics</span>
          </Link>
          <Link
            href="/experiments"
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg font-bold transition ${
              pathname === "/experiments"
                ? "bg-amber-500 text-neutral-950 shadow-md"
                : "text-neutral-400 hover:text-white"
            }`}
          >
            <FlaskConical className="w-3.5 h-3.5" />
            <span>Experiments</span>
          </Link>
        </nav>
      </div>


      {/* Center: Live Clocks */}
      <div className="hidden md:flex items-center gap-4 bg-neutral-900/80 border border-neutral-800 rounded-lg px-3 py-1.5 font-mono text-xs">
        <div className="flex items-center gap-1.5 text-neutral-300">
          <Clock className="w-3.5 h-3.5 text-neutral-400" />
          <span className="text-neutral-400 text-[11px]">UTC:</span>
          <span className="font-semibold text-white" suppressHydrationWarning>
            {timeUTC}
          </span>
        </div>
        <div className="w-px h-3 bg-neutral-800" />
        <div className="text-neutral-400">
          <span className="text-neutral-400 text-[11px] mr-1.5">Local:</span>
          <span className="font-semibold text-neutral-200" suppressHydrationWarning>
            {timeLocal}
          </span>
        </div>
      </div>

      {/* Right: Status Pills & Reconnect */}
      <div className="flex items-center gap-2.5 flex-wrap">
        {/* Data Freshness Indicator */}
        {mounted && connectionState === "CONNECTED" && mt5Status.mt5_connected && (
          <div
            className={`flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-mono font-medium border ${
              isStale
                ? "bg-amber-950/40 text-amber-400 border-amber-700/50 animate-pulse"
                : "bg-emerald-950/40 text-emerald-400 border-emerald-700/50"
            }`}
          >
            <span
              className={`w-2 h-2 rounded-full ${
                isStale ? "bg-amber-400" : "bg-emerald-400 animate-ping"
              }`}
            />
            <span>{isStale ? `STALE (${Math.round(elapsedSeconds)}s)` : "LIVE"}</span>
          </div>
        )}

        {/* MT5 Status Pill */}
        <div
          className={`flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium border ${
            mt5Status.mt5_connected
              ? "bg-emerald-950/40 text-emerald-300 border-emerald-800/50"
              : "bg-rose-950/40 text-rose-300 border-rose-800/50"
          }`}
          title={mt5Status.message}
        >
          <Server className="w-3.5 h-3.5" />
          <span>{mt5Status.mt5_connected ? "MT5 Connected" : "MT5 Disconnected"}</span>
        </div>

        {/* WebSocket Status Pill */}
        <div
          className={`flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium border ${
            connectionState === "CONNECTED"
              ? "bg-emerald-950/30 text-emerald-400 border-emerald-800/40"
              : connectionState === "RECONNECTING" || connectionState === "CONNECTING"
              ? "bg-amber-950/30 text-amber-400 border-amber-800/40 animate-pulse"
              : "bg-rose-950/30 text-rose-400 border-rose-800/40"
          }`}
        >
          {connectionState === "CONNECTED" ? (
            <Wifi className="w-3.5 h-3.5" />
          ) : (
            <WifiOff className="w-3.5 h-3.5" />
          )}
          <span className="capitalize">
            {connectionState === "CONNECTED"
              ? "WS Online"
              : connectionState === "RECONNECTING"
              ? `Reconnecting (${reconnectAttempt})`
              : "WS Offline"}
          </span>
        </div>

        {/* Reconnect button */}
        {connectionState !== "CONNECTED" && (
          <button
            onClick={onReconnect}
            className="flex items-center gap-1 px-2.5 py-1 rounded-lg bg-neutral-800 hover:bg-neutral-700 text-neutral-200 text-xs font-medium transition cursor-pointer border border-neutral-700"
            title="Manual Reconnect"
          >
            <RefreshCw className="w-3 h-3" />
            <span>Retry</span>
          </button>
        )}
      </div>
    </header>
  );
};
