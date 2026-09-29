"use client";

import React, { useEffect, useRef, useState } from "react";
import { MarketTick } from "@/types/market";
import { ArrowDown, ArrowUp, Clock, DollarSign, TrendingDown, TrendingUp, Zap } from "lucide-react";

interface PriceDisplayProps {
  tick: MarketTick | null;
  dayOpenPrice?: number;
  dayHighPrice?: number;
  dayLowPrice?: number;
}

export const PriceDisplay: React.FC<PriceDisplayProps> = ({
  tick,
  dayOpenPrice,
  dayHighPrice,
  dayLowPrice,
}) => {
  const prevBidRef = useRef<number | null>(null);
  const [bidDirection, setBidDirection] = useState<"up" | "down" | "neutral">("neutral");
  const [askDirection, setAskDirection] = useState<"up" | "down" | "neutral">("neutral");

  useEffect(() => {
    if (!tick) return;

    if (prevBidRef.current !== null) {
      if (tick.bid > prevBidRef.current) {
        setBidDirection("up");
        setAskDirection("up");
      } else if (tick.bid < prevBidRef.current) {
        setBidDirection("down");
        setAskDirection("down");
      }
    }
    prevBidRef.current = tick.bid;

    const timer = setTimeout(() => {
      setBidDirection("neutral");
      setAskDirection("neutral");
    }, 800);

    return () => clearTimeout(timer);
  }, [tick?.bid, tick?.ask]);

  if (!tick) {
    return (
      <div className="bg-neutral-950 border border-neutral-800/80 rounded-2xl p-6 flex flex-col items-center justify-center h-full min-h-[450px] shadow-2xl animate-pulse">
        <div className="w-3 h-3 rounded-full bg-amber-500 animate-ping mb-3" />
        <div className="text-neutral-400 font-mono text-xs text-center">
          Awaiting live XAUUSD tick data from MT5...
        </div>
      </div>
    );
  }

  const bidStr = tick.bid.toFixed(2);
  const askStr = tick.ask.toFixed(2);
  const spreadStr = tick.spread.toFixed(2);
  const spreadPoints = Math.round(tick.spread * 100);

  // Split bid into whole and decimal parts for trading-terminal style typography
  const bidWhole = bidStr.split(".")[0];
  const bidDec = bidStr.split(".")[1] || "00";

  const askWhole = askStr.split(".")[0];
  const askDec = askStr.split(".")[1] || "00";

  // Calculate day change if open price is available
  const open = dayOpenPrice || tick.bid;
  const changeUsd = tick.bid - open;
  const changePct = open > 0 ? (changeUsd / open) * 100 : 0;
  const isPositive = changeUsd >= 0;

  const high = Math.max(dayHighPrice || tick.bid, tick.bid);
  const low = Math.min(dayLowPrice || tick.bid, tick.bid);

  return (
    <div className="bg-neutral-950 border border-neutral-800/80 rounded-2xl p-3 flex flex-col justify-between shadow-xl space-y-2">
      {/* Top Header */}
      <div className="flex items-center justify-between pb-2 border-b border-neutral-800/80">
        <div className="flex items-center gap-1.5">
          <Zap className="w-3.5 h-3.5 text-amber-400" />
          <h2 className="text-[11px] font-bold uppercase tracking-wider text-neutral-200 font-mono">
            Live Market Pricing
          </h2>
        </div>
        <span className="text-[9px] font-mono px-1.5 py-0.5 rounded bg-neutral-900 text-amber-400 border border-neutral-800 font-semibold">
          XAUUSD
        </span>
      </div>

      {/* BID (SELL) Box */}
      <div
        className={`bg-neutral-900/80 border rounded-xl p-2.5 transition-all duration-300 relative overflow-hidden ${
          bidDirection === "up"
            ? "border-emerald-500/60 shadow-[0_0_15px_rgba(16,185,129,0.15)] bg-emerald-950/20"
            : bidDirection === "down"
            ? "border-rose-500/60 shadow-[0_0_15px_rgba(244,63,94,0.15)] bg-rose-950/20"
            : "border-neutral-800/90"
        }`}
      >
        <div className="flex items-center justify-between mb-0.5">
          <span className="text-[10px] font-bold uppercase tracking-wider text-neutral-400">
            BID (SELL)
          </span>
          <span className="text-[9px] text-neutral-500 font-mono">Liquidity</span>
        </div>
        <div className="flex items-baseline font-mono tracking-tight justify-between">
          <div className="flex items-baseline">
            <span className="text-2xl sm:text-3xl font-black text-white">
              {bidWhole}.
            </span>
            <span className="text-2xl sm:text-3xl font-black text-amber-400">
              {bidDec}
            </span>
          </div>
          <div>
            {bidDirection === "up" && (
              <span className="flex items-center text-[10px] font-bold text-emerald-400 bg-emerald-950/60 border border-emerald-800/60 px-1.5 py-0.5 rounded">
                <ArrowUp className="w-3 h-3 mr-0.5 animate-bounce" /> UP
              </span>
            )}
            {bidDirection === "down" && (
              <span className="flex items-center text-[10px] font-bold text-rose-400 bg-rose-950/60 border border-rose-800/60 px-1.5 py-0.5 rounded">
                <ArrowDown className="w-3 h-3 mr-0.5 animate-bounce" /> DOWN
              </span>
            )}
          </div>
        </div>
      </div>

      {/* SPREAD Bar */}
      <div className="bg-neutral-900/90 border border-neutral-800 rounded-xl px-3 py-1.5 flex items-center justify-between shadow-inner">
        <span className="text-[10px] font-bold uppercase tracking-wider text-neutral-400 font-mono">
          SPREAD
        </span>
        <div className="flex items-center gap-1.5 font-mono">
          <span className="text-xs font-black text-amber-400">
            ${spreadStr}
          </span>
          <span className="text-[9px] text-neutral-400 bg-neutral-950 px-1 py-0.5 rounded border border-neutral-800">
            {spreadPoints} pts
          </span>
        </div>
      </div>

      {/* ASK (BUY) Box */}
      <div
        className={`bg-neutral-900/80 border rounded-xl p-2.5 transition-all duration-300 relative overflow-hidden ${
          askDirection === "up"
            ? "border-emerald-500/60 shadow-[0_0_15px_rgba(16,185,129,0.15)] bg-emerald-950/20"
            : askDirection === "down"
            ? "border-rose-500/60 shadow-[0_0_15px_rgba(244,63,94,0.15)] bg-rose-950/20"
            : "border-neutral-800/90"
        }`}
      >
        <div className="flex items-center justify-between mb-0.5">
          <span className="text-[10px] font-bold uppercase tracking-wider text-neutral-400">
            ASK (BUY)
          </span>
          <span className="text-[9px] text-neutral-500 font-mono">Offer</span>
        </div>
        <div className="flex items-baseline font-mono tracking-tight justify-between">
          <div className="flex items-baseline">
            <span className="text-2xl sm:text-3xl font-black text-white">
              {askWhole}.
            </span>
            <span className="text-2xl sm:text-3xl font-black text-amber-400">
              {askDec}
            </span>
          </div>
          <div>
            {askDirection === "up" && (
              <span className="flex items-center text-[10px] font-bold text-emerald-400 bg-emerald-950/60 border border-emerald-800/60 px-1.5 py-0.5 rounded">
                <ArrowUp className="w-3 h-3 mr-0.5 animate-bounce" /> UP
              </span>
            )}
            {askDirection === "down" && (
              <span className="flex items-center text-[10px] font-bold text-rose-400 bg-rose-950/60 border border-rose-800/60 px-1.5 py-0.5 rounded">
                <ArrowDown className="w-3 h-3 mr-0.5 animate-bounce" /> DOWN
              </span>
            )}
          </div>
        </div>
      </div>

      {/* 24h Stats & Session Metrics */}
      <div className="bg-neutral-900/60 border border-neutral-800/80 rounded-xl p-2.5 font-mono space-y-1.5 text-[11px]">
        <div className="flex items-center justify-between pb-1 border-b border-neutral-800/60">
          <span className="text-neutral-400 text-[10px] uppercase">24h Change</span>
          <span
            className={`font-bold flex items-center gap-1 ${
              isPositive ? "text-emerald-400" : "text-rose-400"
            }`}
          >
            {isPositive ? <TrendingUp className="w-3 h-3" /> : <TrendingDown className="w-3 h-3" />}
            <span>
              {isPositive ? "+" : ""}
              {changeUsd.toFixed(2)} ({isPositive ? "+" : ""}
              {changePct.toFixed(2)}%)
            </span>
          </span>
        </div>

        <div className="flex items-center justify-between">
          <span className="text-neutral-400 text-[10px] uppercase">Session High</span>
          <span className="font-bold text-white">${high.toFixed(2)}</span>
        </div>

        <div className="flex items-center justify-between">
          <span className="text-neutral-400 text-[10px] uppercase">Session Low</span>
          <span className="font-bold text-white">${low.toFixed(2)}</span>
        </div>

        <div className="flex items-center justify-between pt-1 border-t border-neutral-800/60">
          <span className="text-neutral-400 text-[10px] uppercase">Last Tick</span>
          <span className="font-semibold text-neutral-300" title={tick.timestampISO} suppressHydrationWarning>
            {new Date(tick.timestamp).toLocaleTimeString()}
          </span>
        </div>
      </div>
    </div>
  );
};
