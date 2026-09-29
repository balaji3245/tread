"use client";

import React from "react";
import { ConnectionState, WsStatusData } from "@/types/market";
import { AlertCircle, AlertTriangle, RefreshCw, ServerOff, WifiOff } from "lucide-react";

interface ConnectionBannerProps {
  connectionState: ConnectionState;
  mt5Status: WsStatusData;
  onRetry: () => void;
}

export const ConnectionBanner: React.FC<ConnectionBannerProps> = ({
  connectionState,
  mt5Status,
  onRetry,
}) => {
  // Show nothing if everything is healthy and connected
  if (connectionState === "CONNECTED" && mt5Status.mt5_connected) {
    return null;
  }

  const isWsDisconnected = connectionState !== "CONNECTED";
  const isMt5Disconnected = connectionState === "CONNECTED" && !mt5Status.mt5_connected;

  return (
    <div className="w-full px-4 py-2 bg-gradient-to-r from-rose-950/80 via-neutral-900 to-rose-950/80 border-b border-rose-800/60 shadow-lg text-xs font-mono">
      <div className="max-w-7xl mx-auto flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2.5 text-rose-300">
          {isWsDisconnected ? (
            <WifiOff className="w-4 h-4 text-rose-400 shrink-0 animate-pulse" />
          ) : (
            <ServerOff className="w-4 h-4 text-amber-400 shrink-0" />
          )}

          <div>
            <span className="font-bold text-rose-200 uppercase tracking-wide mr-2">
              {isWsDisconnected ? "Backend Stream Offline" : "MT5 Disconnected"}
            </span>
            <span className="text-neutral-300">
              {isWsDisconnected
                ? "Connecting to local backend at ws://localhost:8000. Ensure Python backend is running."
                : mt5Status.message || "MetaTrader 5 terminal is not responding. Ensure MT5 is running with XAUUSD symbol in Market Watch."}
            </span>
          </div>
        </div>

        <button
          onClick={onRetry}
          className="flex items-center gap-1.5 px-3 py-1 bg-rose-900/60 hover:bg-rose-800/80 border border-rose-700/60 text-white rounded-lg transition cursor-pointer font-sans text-xs font-medium"
        >
          <RefreshCw className="w-3.5 h-3.5" />
          <span>Retry Connection</span>
        </button>
      </div>
    </div>
  );
};
