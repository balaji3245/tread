"use client";

import React from "react";
import { SymbolInfo, WsStatusData } from "@/types/market";
import { Info, ShieldAlert, ShieldCheck } from "lucide-react";

interface MarketStatsProps {
  symbolInfo: SymbolInfo | null;
  mt5Status: WsStatusData;
}

export const MarketStats: React.FC<MarketStatsProps> = ({ symbolInfo, mt5Status }) => {
  return (
    <div className="bg-neutral-950 border border-neutral-800/80 rounded-2xl p-4 flex flex-col h-full shadow-2xl">
      <div className="flex items-center justify-between pb-3 border-b border-neutral-800 mb-3">
        <div className="flex items-center gap-2">
          <Info className="w-4 h-4 text-amber-400" />
          <h2 className="text-xs font-bold uppercase tracking-wider text-neutral-300 font-mono">
            Symbol Specifications
          </h2>
        </div>
        <div className="flex items-center gap-1 text-[10px] text-emerald-400 font-mono bg-emerald-950/40 border border-emerald-800/40 px-2 py-0.5 rounded">
          <ShieldCheck className="w-3 h-3" />
          <span>Strict Read-Only</span>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-2.5 font-mono text-xs">
        <div className="bg-neutral-900/60 border border-neutral-800/80 rounded-lg p-2.5">
          <div className="text-[10px] text-neutral-400 uppercase">Broker Symbol</div>
          <div className="font-bold text-white mt-0.5">{symbolInfo?.symbol || "XAUUSD"}</div>
        </div>

        <div className="bg-neutral-900/60 border border-neutral-800/80 rounded-lg p-2.5">
          <div className="text-[10px] text-neutral-400 uppercase">Digits / Precision</div>
          <div className="font-bold text-white mt-0.5">{symbolInfo?.digits ?? 2} decimals</div>
        </div>

        <div className="bg-neutral-900/60 border border-neutral-800/80 rounded-lg p-2.5">
          <div className="text-[10px] text-neutral-400 uppercase">Point Size</div>
          <div className="font-bold text-white mt-0.5">{symbolInfo?.point ?? 0.01}</div>
        </div>

        <div className="bg-neutral-900/60 border border-neutral-800/80 rounded-lg p-2.5">
          <div className="text-[10px] text-neutral-400 uppercase">Currency Pair</div>
          <div className="font-bold text-white mt-0.5">
            {symbolInfo?.currency_base || "XAU"} / {symbolInfo?.currency_profit || "USD"}
          </div>
        </div>

        <div className="bg-neutral-900/60 border border-neutral-800/80 rounded-lg p-2.5">
          <div className="text-[10px] text-neutral-400 uppercase">Data Source</div>
          <div className="font-bold text-amber-400 mt-0.5">
            {mt5Status.is_mock ? "Simulation Fallback" : "MetaTrader 5 Desktop"}
          </div>
        </div>

        <div className="bg-neutral-900/60 border border-neutral-800/80 rounded-lg p-2.5">
          <div className="text-[10px] text-neutral-400 uppercase">Execution Security</div>
          <div className="font-bold text-emerald-400 mt-0.5">Zero Trading Scope</div>
        </div>
      </div>

      <div className="mt-4 pt-3 border-t border-neutral-800 text-[11px] text-neutral-400 flex items-start gap-2">
        <ShieldAlert className="w-3.5 h-3.5 text-neutral-500 shrink-0 mt-0.5" />
        <p className="leading-tight">
          This dashboard connects strictly via local read-only IPC/WebSocket. Order execution and portfolio access are disabled by design.
        </p>
      </div>
    </div>
  );
};
