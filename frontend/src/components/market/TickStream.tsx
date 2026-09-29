"use client";

import React from "react";
import { MarketTick } from "@/types/market";
import { ArrowDown, ArrowUp, Zap } from "lucide-react";

interface TickStreamProps {
  ticks: MarketTick[];
}

export const TickStream: React.FC<TickStreamProps> = ({ ticks }) => {
  return (
    <div className="w-full bg-neutral-950 border border-neutral-800/80 rounded-2xl p-4 shadow-2xl">
      {/* Stream Header */}
      <div className="flex items-center justify-between pb-3 border-b border-neutral-800 mb-3">
        <div className="flex items-center gap-2">
          <Zap className="w-4 h-4 text-amber-400" />
          <h2 className="text-xs font-bold uppercase tracking-wider text-neutral-200 font-mono">
            Live Tick Stream
          </h2>
        </div>
        <div className="flex items-center gap-3">
          <span className="text-[10px] font-mono bg-neutral-900 px-2 py-0.5 rounded text-neutral-400 border border-neutral-800">
            Streaming Real-Time
          </span>
          <span className="text-[10px] font-mono bg-amber-500/10 text-amber-400 px-2 py-0.5 rounded border border-amber-500/30">
            Last {ticks.length} ticks
          </span>
        </div>
      </div>

      {/* Horizontal / Grid Stream Container */}
      <div className="overflow-x-auto pb-1 scrollbar-thin scrollbar-thumb-neutral-800">
        {ticks.length === 0 ? (
          <div className="text-neutral-500 text-center py-6 text-xs font-mono">
            Awaiting ticks from MetaTrader 5 terminal...
          </div>
        ) : (
          <div className="flex gap-2.5 min-w-max">
            {ticks.map((t, idx) => {
              const isUp = idx < ticks.length - 1 ? t.bid >= ticks[idx + 1].bid : true;
              const timeStr = new Date(t.timestamp).toLocaleTimeString([], {
                hour12: false,
                hour: "2-digit",
                minute: "2-digit",
                second: "2-digit",
              });
              const ms = String(t.timestamp % 1000).padStart(3, "0");

              return (
                <div
                  key={`${t.timestamp}-${idx}`}
                  className={`flex flex-col gap-1 p-2.5 rounded-xl border min-w-[170px] transition-all ${
                    idx === 0
                      ? "bg-neutral-900/90 border-amber-500/40 shadow-lg shadow-amber-500/5 ring-1 ring-amber-500/20"
                      : "bg-neutral-950/60 border-neutral-800/80 hover:bg-neutral-900/50"
                  }`}
                >
                  <div className="flex items-center justify-between text-[10px] font-mono text-neutral-400">
                    <span className="flex items-center gap-1 font-semibold">
                      {isUp ? (
                        <ArrowUp className="w-3 h-3 text-emerald-400 shrink-0" />
                      ) : (
                        <ArrowDown className="w-3 h-3 text-rose-400 shrink-0" />
                      )}
                      <span className={idx === 0 ? "text-amber-300 font-bold" : "text-neutral-300"}>
                        {timeStr}.{ms}
                      </span>
                    </span>
                    <span className="text-[9px] text-neutral-400 bg-neutral-900 px-1 rounded">
                      #{idx + 1}
                    </span>
                  </div>

                  <div className="flex items-baseline justify-between font-mono mt-0.5">
                    <span className="text-[10px] uppercase text-neutral-400">Bid</span>
                    <span className={`text-sm font-black ${isUp ? "text-emerald-400" : "text-rose-400"}`}>
                      ${t.bid.toFixed(2)}
                    </span>
                  </div>

                  <div className="flex items-center justify-between text-[10px] font-mono text-neutral-400 pt-1 border-t border-neutral-800/60">
                    <span>Spr: <strong className="text-neutral-300">${t.spread.toFixed(2)}</strong></span>
                    <span>Ask: <strong className="text-neutral-300">${t.ask.toFixed(2)}</strong></span>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
};
