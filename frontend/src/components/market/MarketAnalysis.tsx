"use client";

import React from "react";
import { MarketSignal } from "@/types/market";
import {
  Activity,
  AlertTriangle,
  ArrowDownRight,
  ArrowUpRight,
  CheckCircle2,
  Clock,
  Gauge,
  Layers,
  ShieldAlert,
  Sparkles,
  TrendingDown,
  TrendingUp,
  Zap,
} from "lucide-react";

interface MarketAnalysisProps {
  signal: MarketSignal | null;
  isLoading?: boolean;
}

export const MarketAnalysis: React.FC<MarketAnalysisProps> = ({ signal, isLoading }) => {
  if (!signal) {
    return (
      <div className="bg-neutral-950 border border-neutral-800/80 rounded-2xl p-5 flex flex-col items-center justify-center min-h-[220px] shadow-2xl animate-pulse">
        <div className="w-3 h-3 rounded-full bg-amber-500 animate-ping mb-3" />
        <div className="text-neutral-400 font-mono text-xs text-center">
          Initializing Multi-Timeframe XAUUSD Market Analysis...
        </div>
      </div>
    );
  }

  const isLong = signal.type === "LONG_SETUP";
  const isShort = signal.type === "SHORT_SETUP";
  const isWait = signal.type === "WAIT";

  const scorePct = Math.round((signal.strength / (signal.maxStrength || 10)) * 100);

  return (
    <div className="bg-neutral-950 border border-neutral-800/80 rounded-2xl p-4 sm:p-5 flex flex-col gap-4 shadow-2xl relative overflow-hidden font-sans">
      {/* Top Header */}
      <div className="flex flex-wrap items-center justify-between gap-2 pb-3 border-b border-neutral-800/80">
        <div className="flex items-center gap-2">
          <div className="w-6 h-6 rounded-md bg-amber-500/10 border border-amber-500/30 flex items-center justify-center text-amber-400">
            <Activity className="w-3.5 h-3.5" />
          </div>
          <div>
            <h2 className="text-sm font-bold uppercase tracking-wider text-neutral-100 font-mono flex items-center gap-2">
              <span>Market Analysis & Setup Engine</span>
              <span className="text-[10px] font-mono font-normal px-2 py-0.5 rounded bg-neutral-900 text-neutral-400 border border-neutral-800">
                1m + 5m Context
              </span>
            </h2>
          </div>
        </div>

        {/* Signal Classification Badge */}
        <div className="flex items-center gap-2">
          {isLong && (
            <div className="flex items-center gap-1.5 px-3 py-1 rounded-lg bg-emerald-950/80 border border-emerald-500/60 text-emerald-300 shadow-[0_0_15px_rgba(16,185,129,0.2)] font-mono text-xs font-black tracking-wide">
              <ArrowUpRight className="w-4 h-4 text-emerald-400 animate-bounce" />
              <span>LONG SETUP DETECTED</span>
            </div>
          )}
          {isShort && (
            <div className="flex items-center gap-1.5 px-3 py-1 rounded-lg bg-rose-950/80 border border-rose-500/60 text-rose-300 shadow-[0_0_15px_rgba(244,63,94,0.2)] font-mono text-xs font-black tracking-wide">
              <ArrowDownRight className="w-4 h-4 text-rose-400 animate-bounce" />
              <span>SHORT SETUP DETECTED</span>
            </div>
          )}
          {isWait && (
            <div className="flex items-center gap-1.5 px-3 py-1 rounded-lg bg-neutral-900 border border-amber-700/50 text-amber-400 font-mono text-xs font-bold tracking-wide">
              <Clock className="w-3.5 h-3.5 text-amber-400" />
              <span>WAIT / NO VALID SETUP</span>
            </div>
          )}
        </div>
      </div>

      {/* Main Grid: Multi-Timeframe Score & Context */}
      <div className="grid grid-cols-1 md:grid-cols-12 gap-3.5">
        {/* Signal Strength & Score Meter (5 cols) */}
        <div className="md:col-span-5 bg-neutral-900/60 border border-neutral-800/80 rounded-xl p-3.5 flex flex-col justify-between gap-3">
          <div className="flex items-center justify-between">
            <span className="text-xs font-mono font-semibold text-neutral-400 flex items-center gap-1.5">
              <Gauge className="w-3.5 h-3.5 text-amber-400" />
              <span>Setup Confluence Score</span>
            </span>
            <span className="text-xs font-mono font-bold text-white bg-neutral-950 px-2 py-0.5 rounded border border-neutral-800">
              {signal.strength} / {signal.maxStrength} points
            </span>
          </div>

          {/* Segmented Progress Bar */}
          <div className="space-y-1.5">
            <div className="w-full bg-neutral-950 rounded-full h-2.5 p-0.5 border border-neutral-800 overflow-hidden">
              <div
                className={`h-full rounded-full transition-all duration-500 ${
                  isLong
                    ? "bg-emerald-500 shadow-[0_0_10px_rgba(16,185,129,0.5)]"
                    : isShort
                    ? "bg-rose-500 shadow-[0_0_10px_rgba(244,63,94,0.5)]"
                    : "bg-amber-500/80"
                }`}
                style={{ width: `${Math.max(5, scorePct)}%` }}
              />
            </div>
            <div className="flex justify-between text-[10px] font-mono text-neutral-500">
              <span>0 (Weak)</span>
              <span>Threshold: 7/10</span>
              <span>10 (Max)</span>
            </div>
          </div>

          {/* Timeframe Direction Badges */}
          <div className="grid grid-cols-2 gap-2 pt-1 border-t border-neutral-800/60 font-mono text-xs">
            <div className="bg-neutral-950/70 p-2 rounded-lg border border-neutral-800 flex flex-col">
              <span className="text-[10px] text-neutral-500 uppercase">5M Primary Trend</span>
              <span
                className={`font-bold mt-0.5 flex items-center gap-1 ${
                  signal.trend_5m === "BULLISH"
                    ? "text-emerald-400"
                    : signal.trend_5m === "BEARISH"
                    ? "text-rose-400"
                    : "text-neutral-300"
                }`}
              >
                {signal.trend_5m === "BULLISH" && <TrendingUp className="w-3 h-3" />}
                {signal.trend_5m === "BEARISH" && <TrendingDown className="w-3 h-3" />}
                {signal.trend_5m}
              </span>
            </div>

            <div className="bg-neutral-950/70 p-2 rounded-lg border border-neutral-800 flex flex-col">
              <span className="text-[10px] text-neutral-500 uppercase">1M Structure</span>
              <span
                className={`font-bold mt-0.5 flex items-center gap-1 ${
                  signal.structure_1m === "BULLISH"
                    ? "text-emerald-400"
                    : signal.structure_1m === "BEARISH"
                    ? "text-rose-400"
                    : "text-neutral-300"
                }`}
              >
                {signal.structure_1m === "BULLISH" && <TrendingUp className="w-3 h-3" />}
                {signal.structure_1m === "BEARISH" && <TrendingDown className="w-3 h-3" />}
                {signal.structure_1m}
              </span>
            </div>
          </div>
        </div>

        {/* Reasons & Active Confirmations (7 cols) */}
        <div className="md:col-span-7 bg-neutral-900/60 border border-neutral-800/80 rounded-xl p-3.5 flex flex-col justify-between gap-2.5">
          <div className="space-y-2">
            <div className="text-xs font-mono font-semibold text-neutral-300 flex items-center gap-1.5">
              <Sparkles className="w-3.5 h-3.5 text-amber-400" />
              <span>Setup Rationale & Conditions</span>
            </div>

            {/* Reasons List */}
            <div className="space-y-1.5 max-h-[140px] overflow-y-auto pr-1">
              {signal.reasons && signal.reasons.length > 0 ? (
                signal.reasons.map((r, i) => (
                  <div
                    key={i}
                    className="flex items-start gap-2 text-xs font-mono text-neutral-300 bg-neutral-950/50 p-1.5 rounded-lg border border-neutral-800/60"
                  >
                    <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 shrink-0 mt-0.5" />
                    <span>{r}</span>
                  </div>
                ))
              ) : (
                <div className="text-xs font-mono text-neutral-500 italic">
                  No active confirmation criteria currently satisfied.
                </div>
              )}
            </div>

            {/* Warnings List if any */}
            {signal.warnings && signal.warnings.length > 0 && (
              <div className="space-y-1 pt-1 border-t border-neutral-800/60">
                {signal.warnings.map((w, i) => (
                  <div
                    key={i}
                    className="flex items-center gap-2 text-[11px] font-mono text-amber-400 bg-amber-950/30 px-2 py-1 rounded-md border border-amber-800/40"
                  >
                    <AlertTriangle className="w-3 h-3 text-amber-400 shrink-0" />
                    <span>{w}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Bottom Technical Indicator Matrix & Key Levels */}
      <div className="grid grid-cols-1 md:grid-cols-12 gap-3 pt-1 border-t border-neutral-900">
        {/* Indicator Matrix (8 cols) */}
        <div className="md:col-span-8 grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs font-mono">
          {/* EMA 1m / 5m */}
          <div className="bg-neutral-900/40 border border-neutral-800/60 rounded-lg p-2 flex flex-col">
            <span className="text-[10px] text-neutral-500">1M EMA (9/21/50)</span>
            <span className="font-semibold text-neutral-200 mt-0.5">
              {signal.indicators.ema9_1m?.toFixed(2) || "--"} / {signal.indicators.ema21_1m?.toFixed(2) || "--"}
            </span>
          </div>

          {/* RSI 1m / 5m */}
          <div className="bg-neutral-900/40 border border-neutral-800/60 rounded-lg p-2 flex flex-col">
            <span className="text-[10px] text-neutral-500">RSI (1M / 5M)</span>
            <span className="font-semibold text-neutral-200 mt-0.5">
              <strong className="text-amber-400">{signal.indicators.rsi_1m?.toFixed(1) || "--"}</strong> /{" "}
              <span>{signal.indicators.rsi_5m?.toFixed(1) || "--"}</span>
            </span>
          </div>

          {/* MACD 1m */}
          <div className="bg-neutral-900/40 border border-neutral-800/60 rounded-lg p-2 flex flex-col">
            <span className="text-[10px] text-neutral-500">1M MACD Hist</span>
            <span
              className={`font-semibold mt-0.5 ${
                (signal.indicators.macdHist_1m || 0) >= 0 ? "text-emerald-400" : "text-rose-400"
              }`}
            >
              {(signal.indicators.macdHist_1m || 0) > 0 ? "+" : ""}
              {signal.indicators.macdHist_1m?.toFixed(2) || "--"}
            </span>
          </div>

          {/* ATR 1m */}
          <div className="bg-neutral-900/40 border border-neutral-800/60 rounded-lg p-2 flex flex-col">
            <span className="text-[10px] text-neutral-500">1M ATR (Vol)</span>
            <span className="font-semibold text-neutral-200 mt-0.5">
              ${signal.indicators.atr_1m?.toFixed(2) || "--"}
            </span>
          </div>
        </div>

        {/* Support & Resistance Mini Levels (4 cols) */}
        <div className="md:col-span-4 flex items-center justify-between gap-2 bg-neutral-900/40 border border-neutral-800/60 rounded-lg p-2 font-mono text-xs">
          <div className="flex flex-col">
            <span className="text-[10px] text-emerald-400 uppercase">Nearest Support</span>
            <span className="font-bold text-white">
              {signal.supportLevels && signal.supportLevels.length > 0
                ? `$${signal.supportLevels[0].price.toFixed(2)}`
                : "--"}
            </span>
          </div>
          <div className="w-px h-6 bg-neutral-800" />
          <div className="flex flex-col text-right">
            <span className="text-[10px] text-rose-400 uppercase">Nearest Resistance</span>
            <span className="font-bold text-white">
              {signal.resistanceLevels && signal.resistanceLevels.length > 0
                ? `$${signal.resistanceLevels[0].price.toFixed(2)}`
                : "--"}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
};
