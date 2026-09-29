"use client";

import React, { useEffect, useState } from "react";
import { Eye, ShieldAlert, CheckCircle2, Clock, Ban, TrendingUp, TrendingDown, RefreshCw, BarChart2, Activity } from "lucide-react";
import { fetchShadowJournal, fetchShadowStatus, fetchShadowSummary } from "@/lib/api";

export const ShadowMonitoring: React.FC = () => {
  const [status, setStatus] = useState<any>(null);
  const [summary, setSummary] = useState<any>(null);
  const [journal, setJournal] = useState<any[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [lastRefreshed, setLastRefreshed] = useState<Date>(new Date());

  const loadData = async () => {
    try {
      setLoading(true);
      const [st, sm, jn] = await Promise.all([
        fetchShadowStatus().catch(() => null),
        fetchShadowSummary().catch(() => null),
        fetchShadowJournal(20).catch(() => []),
      ]);
      if (st) setStatus(st);
      if (sm) setSummary(sm);
      if (jn) setJournal(jn);
      setLastRefreshed(new Date());
    } catch (e) {
      console.error("Failed to load shadow monitoring data:", e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 5000); // 5s poll
    return () => clearInterval(interval);
  }, []);

  const isMarketActive = status?.market_feed_status === "ACTIVE";

  return (
    <div className="bg-neutral-900/90 border border-neutral-800 rounded-2xl p-4 sm:p-6 shadow-xl flex flex-col gap-5 font-sans">
      {/* Top Banner: Status and Security Disclaimer */}
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-neutral-800/80 pb-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-purple-500/20 border border-purple-500/40 flex items-center justify-center text-purple-400 font-bold">
            <Eye className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-lg font-bold text-white font-mono flex items-center gap-2">
                H006 SHADOW VALIDATION
                <span className="text-xs px-2 py-0.5 rounded bg-purple-500/20 text-purple-300 border border-purple-500/30 font-mono">
                  V6F-H006
                </span>
              </h2>
              <span
                className={`text-[11px] font-bold px-2.5 py-0.5 rounded-full border ${
                  isMarketActive
                    ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/30 animate-pulse"
                    : "bg-amber-500/10 text-amber-400 border-amber-500/30"
                }`}
              >
                {status?.market_feed_status || "MARKET_INACTIVE"}
              </span>
            </div>
            <p className="text-xs text-neutral-400 mt-0.5">
              Frozen Candidate (0.15 ATR Retrace, 120s Timeout) • Live Baseline: <span className="text-neutral-300 font-mono">phase6-baseline-v1</span>
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {/* Strictly Read-Only Disclaimer Pill */}
          <div className="flex items-center gap-1.5 px-3 py-1 rounded-lg bg-rose-950/40 text-rose-300 border border-rose-800/60 text-xs font-mono font-semibold">
            <ShieldAlert className="w-3.5 h-3.5 text-rose-400" />
            <span>PAPER / SHADOW — NO REAL ORDERS</span>
          </div>

          <button
            onClick={loadData}
            disabled={loading}
            className="p-1.5 rounded-lg bg-neutral-800 hover:bg-neutral-700 text-neutral-300 transition text-xs flex items-center gap-1 cursor-pointer border border-neutral-700"
            title="Refresh Shadow State"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin text-purple-400" : ""}`} />
          </button>
        </div>
      </div>

      {/* Main KPI Grid */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
        <div className="bg-neutral-950/70 border border-neutral-800/90 rounded-xl p-3 flex flex-col">
          <span className="text-[11px] text-neutral-400 font-mono">Signals Recorded</span>
          <span className="text-xl font-bold font-mono text-white mt-1">
            {summary?.signals_count ?? status?.total_journal_entries ?? 0}
          </span>
          <span className="text-[10px] text-neutral-500 font-mono mt-0.5">
            Checkpoint: {status?.checkpoint_milestone || "0/100 Signals"}
          </span>
        </div>

        <div className="bg-neutral-950/70 border border-neutral-800/90 rounded-xl p-3 flex flex-col">
          <span className="text-[11px] text-neutral-400 font-mono">Filled / Converted</span>
          <span className="text-xl font-bold font-mono text-purple-400 mt-1">
            {summary?.filled_count ?? 0}
          </span>
          <span className="text-[10px] text-neutral-500 font-mono mt-0.5">
            {summary?.signals_count ? `${Math.round((summary.filled_count / summary.signals_count) * 100)}% Conversion` : "Waiting for signals"}
          </span>
        </div>

        <div className="bg-neutral-950/70 border border-neutral-800/90 rounded-xl p-3 flex flex-col">
          <span className="text-[11px] text-neutral-400 font-mono">Timeouts / Invals</span>
          <span className="text-xl font-bold font-mono text-amber-400 mt-1">
            {(summary?.timeouts_count ?? 0) + (summary?.invalidations_count ?? 0)}
          </span>
          <span className="text-[10px] text-neutral-500 font-mono mt-0.5">
            {summary?.timeouts_count ?? 0} TO | {summary?.invalidations_count ?? 0} Inval
          </span>
        </div>

        <div className="bg-neutral-950/70 border border-neutral-800/90 rounded-xl p-3 flex flex-col">
          <span className="text-[11px] text-neutral-400 font-mono">Shadow Win Rate</span>
          <span className="text-xl font-bold font-mono text-emerald-400 mt-1">
            {summary?.virtual_trades_count && summary.virtual_trades_count > 0 ? `${summary.win_rate_pct}%` : "—"}
          </span>
          <span className="text-[10px] text-neutral-500 font-mono mt-0.5">
            {summary?.wins ?? 0}W / {summary?.losses ?? 0}L ({summary?.virtual_trades_count ?? 0} trades)
          </span>
        </div>

        <div className="bg-neutral-950/70 border border-neutral-800/90 rounded-xl p-3 flex flex-col">
          <span className="text-[11px] text-neutral-400 font-mono">Shadow Expectancy</span>
          <span className={`text-xl font-bold font-mono mt-1 ${
            (summary?.expectancy_r ?? 0) >= 0 ? "text-emerald-400" : "text-rose-400"
          }`}>
            {summary?.virtual_trades_count && summary.virtual_trades_count > 0 ? `${summary.expectancy_r > 0 ? "+" : ""}${summary.expectancy_r}R` : "—"}
          </span>
          <span className="text-[10px] text-neutral-500 font-mono mt-0.5">
            Net R: {summary?.total_net_r ?? 0}R
          </span>
        </div>

        <div className="bg-neutral-950/70 border border-neutral-800/90 rounded-xl p-3 flex flex-col">
          <span className="text-[11px] text-neutral-400 font-mono">Shadow Profit Factor</span>
          <span className="text-xl font-bold font-mono text-cyan-400 mt-1">
            {summary?.virtual_trades_count && summary.virtual_trades_count > 0 ? summary.profit_factor : "—"}
          </span>
          <span className="text-[10px] text-neutral-500 font-mono mt-0.5">
            Final OOS PF: 1.21
          </span>
        </div>
      </div>

      {/* Active State Details (Pending Signal or Active Virtual Position) */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Pending Signal Card */}
        <div className="bg-neutral-950/60 border border-neutral-800 rounded-xl p-4 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between">
              <span className="text-xs font-mono font-semibold text-neutral-300 flex items-center gap-1.5">
                <Clock className="w-3.5 h-3.5 text-amber-400" />
                Pending Retracement Setup
              </span>
              <span className="text-[10px] font-mono text-neutral-500">Max Wait: 120s</span>
            </div>
            {status?.pending_signal ? (
              <div className="mt-3 flex flex-col gap-1.5 font-mono text-xs">
                <div className="flex justify-between">
                  <span className="text-neutral-400">Signal:</span>
                  <span className="font-bold text-white">{status.pending_signal.signal_id}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-neutral-400">Direction:</span>
                  <span className={status.pending_signal.direction === "LONG" ? "text-emerald-400 font-bold" : "text-rose-400 font-bold"}>
                    {status.pending_signal.direction}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-neutral-400">Target Fill Price:</span>
                  <span className="text-amber-300 font-bold">${status.pending_signal.target_price.toFixed(2)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-neutral-400">Invalidation Price:</span>
                  <span className="text-rose-400">${status.pending_signal.invalidation_price.toFixed(2)}</span>
                </div>
              </div>
            ) : (
              <p className="text-xs text-neutral-500 font-mono mt-3 italic">
                No signal currently in 2-minute retracement waiting window.
              </p>
            )}
          </div>
        </div>

        {/* Active Virtual Trade Card */}
        <div className="bg-neutral-950/60 border border-neutral-800 rounded-xl p-4 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between">
              <span className="text-xs font-mono font-semibold text-neutral-300 flex items-center gap-1.5">
                <Activity className="w-3.5 h-3.5 text-purple-400" />
                Active Virtual Position (Concurrency: 1)
              </span>
              <span className="text-[10px] font-mono text-purple-400">Paper Only</span>
            </div>
            {status?.active_virtual_trade ? (
              <div className="mt-3 flex flex-col gap-1.5 font-mono text-xs">
                <div className="flex justify-between">
                  <span className="text-neutral-400">Virtual Trade:</span>
                  <span className="font-bold text-white">{status.active_virtual_trade.trade_id}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-neutral-400">Entry Price:</span>
                  <span className="text-purple-300 font-bold">${status.active_virtual_trade.entry_price.toFixed(2)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-neutral-400">SL / TP1 / TP2:</span>
                  <span className="text-neutral-300">
                    ${status.active_virtual_trade.stop_loss.toFixed(2)} / ${status.active_virtual_trade.take_profit_1.toFixed(2)} / ${status.active_virtual_trade.take_profit_2.toFixed(2)}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-neutral-400">Max Excursions (MFE/MAE):</span>
                  <span className="text-neutral-300">
                    +{status.active_virtual_trade.peak_mfe_r}R / -{status.active_virtual_trade.peak_mae_r}R
                  </span>
                </div>
              </div>
            ) : (
              <p className="text-xs text-neutral-500 font-mono mt-3 italic">
                No active virtual trade open.
              </p>
            )}
          </div>
        </div>
      </div>

      {/* Recent Immutable Shadow Journal Table */}
      <div className="flex flex-col gap-2">
        <div className="flex items-center justify-between">
          <span className="text-xs font-mono font-semibold text-neutral-300">
            Recent Shadow Journal Entries (Append-Only JSONL)
          </span>
          <span className="text-[11px] font-mono text-neutral-500">
            {journal.length} records shown
          </span>
        </div>

        <div className="overflow-x-auto rounded-xl border border-neutral-800/80">
          <table className="w-full text-left font-mono text-xs border-collapse">
            <thead>
              <tr className="bg-neutral-950 text-neutral-400 border-b border-neutral-800 text-[11px]">
                <th className="p-2.5">Time (UTC)</th>
                <th className="p-2.5">Event</th>
                <th className="p-2.5">Dir</th>
                <th className="p-2.5">State</th>
                <th className="p-2.5">Entry / Target</th>
                <th className="p-2.5">Delay</th>
                <th className="p-2.5">Result</th>
                <th className="p-2.5">Outcome Reason</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-neutral-800/60 bg-neutral-950/40">
              {journal.length === 0 ? (
                <tr>
                  <td colSpan={8} className="p-4 text-center text-neutral-500 italic">
                    Shadow journal is ready. Awaiting live market signals from Exness MT5 stream.
                  </td>
                </tr>
              ) : (
                journal.map((j, idx) => (
                  <tr key={idx} className="hover:bg-neutral-900/50 transition">
                    <td className="p-2.5 text-neutral-400 text-[11px] whitespace-nowrap">
                      {j.timestamp_utc?.slice(11, 19) || "—"}
                    </td>
                    <td className="p-2.5 text-neutral-300 font-bold whitespace-nowrap">
                      {j.event_id}
                    </td>
                    <td className="p-2.5">
                      <span className={j.signal_direction === "LONG" ? "text-emerald-400 font-bold" : "text-rose-400 font-bold"}>
                        {j.signal_direction}
                      </span>
                    </td>
                    <td className="p-2.5">
                      <span className={`px-1.5 py-0.5 rounded text-[10px] font-semibold ${
                        j.entry_state?.includes("FILLED")
                          ? "bg-purple-500/20 text-purple-300 border border-purple-500/30"
                          : j.entry_state === "TIMED_OUT"
                          ? "bg-amber-500/20 text-amber-300 border border-amber-500/30"
                          : j.entry_state === "INVALIDATED"
                          ? "bg-rose-500/20 text-rose-300 border border-rose-500/30"
                          : "bg-neutral-800 text-neutral-400"
                      }`}>
                        {j.entry_state}
                      </span>
                    </td>
                    <td className="p-2.5 text-neutral-300">
                      ${(j.virtual_entry_price || j.retracement_target || j.signal_price)?.toFixed(2)}
                    </td>
                    <td className="p-2.5 text-neutral-400">
                      {j.delay_seconds !== null && j.delay_seconds !== undefined ? `${j.delay_seconds}s` : "—"}
                    </td>
                    <td className="p-2.5">
                      {j.r_multiple !== null && j.r_multiple !== undefined ? (
                        <span className={`font-bold ${j.r_multiple >= 0 ? "text-emerald-400" : "text-rose-400"}`}>
                          {j.r_multiple > 0 ? "+" : ""}{j.r_multiple}R
                        </span>
                      ) : (
                        <span className="text-neutral-500">—</span>
                      )}
                    </td>
                    <td className="p-2.5 text-neutral-400 text-[11px]">
                      {j.exit_reason || j.cancellation_reason || "—"}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
