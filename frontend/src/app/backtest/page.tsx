"use client";

import React, { useState, useEffect, useMemo, useCallback } from "react";
import Link from "next/link";
import { Header } from "@/components/market/Header";
import { useMarketWebSocket } from "@/hooks/useMarketWebSocket";
import { runBacktest, fetchSymbolInfo } from "@/lib/api";
import {
  BacktestConfig,
  BacktestResponse,
  BacktestTrade,
  SymbolInfo,
} from "@/types/market";
import {
  Activity,
  AlertCircle,
  ArrowDownRight,
  ArrowUpRight,
  BarChart3,
  Calendar,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  Clock,
  DollarSign,
  Download,
  Filter,
  Flame,
  Globe,
  HelpCircle,
  History,
  Layers,
  Percent,
  Play,
  RefreshCw,
  Search,
  Shield,
  ShieldAlert,
  Sparkles,
  TrendingDown,
  TrendingUp,
  XCircle,
  Zap,
} from "lucide-react";

export default function BacktestPage() {
  const [symbolInfo, setSymbolInfo] = useState<SymbolInfo | null>(null);

  // Configuration state
  const [capital, setCapital] = useState<number>(10000);
  const [riskPerTrade, setRiskPerTrade] = useState<number>(100);
  const [threshold, setThreshold] = useState<number>(7);
  const [slMultiplier, setSlMultiplier] = useState<number>(1.0);
  const [tp1Multiplier, setTp1Multiplier] = useState<number>(1.0);
  const [tp2Multiplier, setTp2Multiplier] = useState<number>(2.0);
  const [spread, setSpread] = useState<number>(0.30);
  const [maxHolding, setMaxHolding] = useState<number>(60);
  const [datePreset, setDatePreset] = useState<"1d" | "3d" | "7d" | "custom">("3d");
  const [startDate, setStartDate] = useState<string>("");
  const [endDate, setEndDate] = useState<string>("");
  const [executionMode, setExecutionMode] = useState<"fixed_spread" | "historical_spread">("fixed_spread");
  const [sameCandlePolicy, setSameCandlePolicy] = useState<"stop_first" | "tp_first">("stop_first");

  // Execution state
  const [isRunning, setIsRunning] = useState<boolean>(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [backtestResult, setBacktestResult] = useState<BacktestResponse | null>(null);

  // Filter state for trade journal
  const [tradeFilter, setTradeFilter] = useState<"ALL" | "WIN" | "LOSS" | "LONG" | "SHORT" | "EXPIRED">("ALL");
  const [searchQuery, setSearchQuery] = useState<string>("");

  const {
    connectionState,
    mt5Status,
    lastMessageTime,
    reconnectAttempt,
    manualReconnect,
  } = useMarketWebSocket();

  // Load symbol specifications
  useEffect(() => {
    fetchSymbolInfo()
      .then((info) => setSymbolInfo(info))
      .catch(() => {});
  }, []);

  // Run backtest function
  const handleRunBacktest = useCallback(async () => {
    setIsRunning(true);
    setErrorMsg(null);

    const now = new Date();
    let startIso: string | undefined = undefined;
    let endIso: string | undefined = now.toISOString();

    if (datePreset === "1d") {
      startIso = new Date(now.getTime() - 86400 * 1000).toISOString();
    } else if (datePreset === "3d") {
      startIso = new Date(now.getTime() - 86400 * 3 * 1000).toISOString();
    } else if (datePreset === "7d") {
      startIso = new Date(now.getTime() - 86400 * 7 * 1000).toISOString();
    } else if (datePreset === "custom" && startDate) {
      startIso = new Date(startDate).toISOString();
      if (endDate) endIso = new Date(endDate).toISOString();
    }

    const config: BacktestConfig = {
      symbol: "XAUUSD",
      start_date: startIso,
      end_date: endIso,
      timeframe_primary: "5m",
      timeframe_trigger: "1m",
      initial_capital: Number(capital),
      risk_per_trade_usd: Number(riskPerTrade),
      signal_threshold: Number(threshold),
      sl_atr_multiplier: Number(slMultiplier),
      tp1_atr_multiplier: Number(tp1Multiplier),
      tp2_atr_multiplier: Number(tp2Multiplier),
      max_holding_minutes: Number(maxHolding),
      assumed_spread: Number(spread),
      execution_mode: executionMode,
      same_candle_policy: sameCandlePolicy,
      max_concurrent_trades: 1,
      enable_long: true,
      enable_short: true,
    };

    try {
      const data = await runBacktest(config);
      setBacktestResult(data);
    } catch (err: any) {
      setErrorMsg(err.message || "Failed to execute historical backtest.");
    } finally {
      setIsRunning(false);
    }
  }, [
    capital,
    riskPerTrade,
    threshold,
    slMultiplier,
    tp1Multiplier,
    tp2Multiplier,
    spread,
    maxHolding,
    datePreset,
    startDate,
    endDate,
    executionMode,
    sameCandlePolicy,
  ]);

  // Initial backtest on mount
  useEffect(() => {
    handleRunBacktest();
  }, []);

  // Filtered trades list
  const filteredTrades = useMemo(() => {
    if (!backtestResult || !backtestResult.trades) return [];
    return backtestResult.trades.filter((t) => {
      if (tradeFilter === "WIN" && t.r_multiple <= 0) return false;
      if (tradeFilter === "LOSS" && t.r_multiple >= 0) return false;
      if (tradeFilter === "LONG" && t.direction !== "LONG") return false;
      if (tradeFilter === "SHORT" && t.direction !== "SHORT") return false;
      if (tradeFilter === "EXPIRED" && t.result !== "EXPIRED") return false;

      if (searchQuery) {
        const q = searchQuery.toLowerCase();
        return (
          t.id.toLowerCase().includes(q) ||
          t.signal_time_iso.toLowerCase().includes(q) ||
          t.result.toLowerCase().includes(q) ||
          t.direction.toLowerCase().includes(q)
        );
      }
      return true;
    });
  }, [backtestResult, tradeFilter, searchQuery]);

  const stats = backtestResult?.statistics;

  return (
    <div className="min-h-screen bg-neutral-950 text-neutral-100 flex flex-col font-sans selection:bg-amber-500/30 selection:text-amber-200">
      {/* Sticky Header */}
      <Header
        symbol={symbolInfo?.symbol || "XAUUSD"}
        connectionState={connectionState}
        mt5Status={mt5Status}
        lastMessageTime={lastMessageTime}
        reconnectAttempt={reconnectAttempt}
        onReconnect={manualReconnect}
      />

      <main className="flex-1 p-3 sm:p-5 max-w-[1700px] w-full mx-auto flex flex-col gap-5">
        {/* Page Title & Overview */}
        <div className="flex flex-wrap items-center justify-between gap-3 pb-2 border-b border-neutral-900">
          <div>
            <h1 className="text-xl font-black text-white font-mono flex items-center gap-2">
              <History className="w-5 h-5 text-amber-400" />
              <span>XAUUSD Historical Backtester & Signal Journal</span>
            </h1>
            <p className="text-xs text-neutral-400 mt-0.5">
              Deterministic historical replay engine evaluating the exact live multi-timeframe signal rules (Zero Look-Ahead Bias).
            </p>
          </div>

          <div className="flex items-center gap-2">
            <span className="text-[11px] font-mono px-2.5 py-1 rounded bg-neutral-900 text-amber-400 border border-neutral-800">
              Rule Source: Live SignalEngine (5m Context + 1m Trigger)
            </span>
          </div>
        </div>

        {/* Top Control Panel: Configuration & Parameters */}
        <div className="bg-neutral-950 border border-neutral-800/80 rounded-2xl p-4 sm:p-5 shadow-2xl space-y-4">
          <div className="flex items-center justify-between pb-3 border-b border-neutral-800/80">
            <div className="flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-amber-400" />
              <h2 className="text-xs font-bold uppercase tracking-wider text-neutral-200 font-mono">
                Backtest Configuration & Risk Parameters
              </h2>
            </div>

            {/* Quick Date Presets */}
            <div className="flex items-center gap-1 bg-neutral-900 p-1 rounded-lg border border-neutral-800 font-mono text-xs">
              <button
                onClick={() => setDatePreset("1d")}
                className={`px-2.5 py-1 rounded transition cursor-pointer ${
                  datePreset === "1d" ? "bg-amber-500 text-neutral-950 font-bold" : "text-neutral-400 hover:text-white"
                }`}
              >
                Last 24h
              </button>
              <button
                onClick={() => setDatePreset("3d")}
                className={`px-2.5 py-1 rounded transition cursor-pointer ${
                  datePreset === "3d" ? "bg-amber-500 text-neutral-950 font-bold" : "text-neutral-400 hover:text-white"
                }`}
              >
                Last 3 Days
              </button>
              <button
                onClick={() => setDatePreset("7d")}
                className={`px-2.5 py-1 rounded transition cursor-pointer ${
                  datePreset === "7d" ? "bg-amber-500 text-neutral-950 font-bold" : "text-neutral-400 hover:text-white"
                }`}
              >
                Last 7 Days
              </button>
              <button
                onClick={() => setDatePreset("custom")}
                className={`px-2.5 py-1 rounded transition cursor-pointer ${
                  datePreset === "custom" ? "bg-amber-500 text-neutral-950 font-bold" : "text-neutral-400 hover:text-white"
                }`}
              >
                Custom
              </button>
            </div>
          </div>

          {/* Configuration Inputs Grid */}
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3.5 text-xs font-mono">
            {/* Signal Threshold */}
            <div className="bg-neutral-900/60 border border-neutral-800 rounded-xl p-2.5 flex flex-col justify-between">
              <span className="text-[10px] text-neutral-400 uppercase">Min Score (0-10)</span>
              <div className="flex items-center justify-between mt-1">
                <input
                  type="number"
                  min={1}
                  max={10}
                  value={threshold}
                  onChange={(e) => setThreshold(Number(e.target.value))}
                  className="w-full bg-neutral-950 border border-neutral-800 rounded px-2 py-1 text-white font-bold text-sm"
                />
              </div>
            </div>

            {/* SL Multiplier */}
            <div className="bg-neutral-900/60 border border-neutral-800 rounded-xl p-2.5 flex flex-col justify-between">
              <span className="text-[10px] text-neutral-400 uppercase">Stop Loss (x ATR)</span>
              <input
                type="number"
                step="0.1"
                min={0.2}
                value={slMultiplier}
                onChange={(e) => setSlMultiplier(Number(e.target.value))}
                className="w-full bg-neutral-950 border border-neutral-800 rounded px-2 py-1 text-white font-bold text-sm mt-1"
              />
            </div>

            {/* TP1 Multiplier */}
            <div className="bg-neutral-900/60 border border-neutral-800 rounded-xl p-2.5 flex flex-col justify-between">
              <span className="text-[10px] text-neutral-400 uppercase">Take Profit (x ATR)</span>
              <input
                type="number"
                step="0.1"
                min={0.2}
                value={tp1Multiplier}
                onChange={(e) => setTp1Multiplier(Number(e.target.value))}
                className="w-full bg-neutral-950 border border-neutral-800 rounded px-2 py-1 text-white font-bold text-sm mt-1"
              />
            </div>

            {/* Assumed Spread */}
            <div className="bg-neutral-900/60 border border-neutral-800 rounded-xl p-2.5 flex flex-col justify-between">
              <span className="text-[10px] text-neutral-400 uppercase">Spread ($ USD)</span>
              <input
                type="number"
                step="0.05"
                min={0.0}
                value={spread}
                onChange={(e) => setSpread(Number(e.target.value))}
                className="w-full bg-neutral-950 border border-neutral-800 rounded px-2 py-1 text-white font-bold text-sm mt-1"
              />
            </div>

            {/* Max Holding Time */}
            <div className="bg-neutral-900/60 border border-neutral-800 rounded-xl p-2.5 flex flex-col justify-between">
              <span className="text-[10px] text-neutral-400 uppercase">Max Holding (Mins)</span>
              <input
                type="number"
                min={5}
                max={720}
                value={maxHolding}
                onChange={(e) => setMaxHolding(Number(e.target.value))}
                className="w-full bg-neutral-950 border border-neutral-800 rounded px-2 py-1 text-white font-bold text-sm mt-1"
              />
            </div>

            {/* Capital / Risk */}
            <div className="bg-neutral-900/60 border border-neutral-800 rounded-xl p-2.5 flex flex-col justify-between">
              <span className="text-[10px] text-neutral-400 uppercase">Risk per 1R ($ USD)</span>
              <input
                type="number"
                min={10}
                value={riskPerTrade}
                onChange={(e) => setRiskPerTrade(Number(e.target.value))}
                className="w-full bg-neutral-950 border border-neutral-800 rounded px-2 py-1 text-white font-bold text-sm mt-1"
              />
            </div>
          </div>

          {/* Custom Date Inputs if selected */}
          {datePreset === "custom" && (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-2 font-mono text-xs">
              <div>
                <label className="text-[10px] text-neutral-400 uppercase block mb-1">Start Date</label>
                <input
                  type="date"
                  value={startDate}
                  onChange={(e) => setStartDate(e.target.value)}
                  className="w-full bg-neutral-900 border border-neutral-800 rounded px-3 py-1.5 text-white font-mono"
                />
              </div>
              <div>
                <label className="text-[10px] text-neutral-400 uppercase block mb-1">End Date</label>
                <input
                  type="date"
                  value={endDate}
                  onChange={(e) => setEndDate(e.target.value)}
                  className="w-full bg-neutral-900 border border-neutral-800 rounded px-3 py-1.5 text-white font-mono"
                />
              </div>
            </div>
          )}

          {/* Action Row */}
          <div className="flex flex-wrap items-center justify-between gap-3 pt-2">
            <div className="text-[11px] font-mono text-neutral-400 flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-amber-400" />
              <span>Replay execution: Next 1m Open • Stop-Loss Conflict: Stop First</span>
            </div>

            <button
              onClick={handleRunBacktest}
              disabled={isRunning}
              className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-amber-500 hover:bg-amber-400 text-neutral-950 font-bold font-mono text-xs transition cursor-pointer shadow-lg shadow-amber-500/20 disabled:opacity-50"
            >
              {isRunning ? (
                <>
                  <RefreshCw className="w-4 h-4 animate-spin" />
                  <span>REPLAYING HISTORICAL DATA...</span>
                </>
              ) : (
                <>
                  <Play className="w-4 h-4 fill-neutral-950" />
                  <span>RUN HISTORICAL BACKTEST</span>
                </>
              )}
            </button>
          </div>

          {errorMsg && (
            <div className="bg-rose-950/40 border border-rose-800/60 p-3 rounded-xl text-rose-300 font-mono text-xs flex items-center gap-2">
              <AlertCircle className="w-4 h-4 text-rose-400 shrink-0" />
              <span>{errorMsg}</span>
            </div>
          )}
        </div>

        {/* Results Section */}
        {backtestResult && stats && (
          <div className="space-y-5">
            {/* 1. KPI Executive Summary Cards */}
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3.5 font-mono">
              {/* Total Trades */}
              <div className="bg-neutral-950 border border-neutral-800/80 rounded-2xl p-4 shadow-xl flex flex-col justify-between">
                <span className="text-[10px] uppercase text-neutral-500 font-bold tracking-wider">Total Trades</span>
                <div className="flex items-baseline justify-between mt-2">
                  <span className="text-2xl sm:text-3xl font-black text-white">{stats.total_trades}</span>
                  <span className="text-[10px] text-neutral-400">
                    L: {stats.long_trades} / S: {stats.short_trades}
                  </span>
                </div>
              </div>

              {/* Win Rate */}
              <div className="bg-neutral-950 border border-neutral-800/80 rounded-2xl p-4 shadow-xl flex flex-col justify-between">
                <span className="text-[10px] uppercase text-neutral-500 font-bold tracking-wider">Win Rate</span>
                <div className="flex items-baseline justify-between mt-2">
                  <span
                    className={`text-2xl sm:text-3xl font-black ${
                      stats.win_rate >= 50 ? "text-emerald-400" : "text-amber-400"
                    }`}
                  >
                    {stats.win_rate}%
                  </span>
                  <span className="text-[10px] text-neutral-400">
                    {stats.winning_trades}W / {stats.losing_trades}L
                  </span>
                </div>
              </div>

              {/* Total R / PnL */}
              <div className="bg-neutral-950 border border-neutral-800/80 rounded-2xl p-4 shadow-xl flex flex-col justify-between">
                <span className="text-[10px] uppercase text-neutral-500 font-bold tracking-wider">Total Return (R)</span>
                <div className="flex items-baseline justify-between mt-2">
                  <span
                    className={`text-2xl sm:text-3xl font-black ${
                      stats.total_r >= 0 ? "text-emerald-400" : "text-rose-400"
                    }`}
                  >
                    {stats.total_r > 0 ? "+" : ""}
                    {stats.total_r}R
                  </span>
                  <span className="text-[10px] text-neutral-300">
                    ${(stats.total_r * riskPerTrade).toFixed(0)}
                  </span>
                </div>
              </div>

              {/* Profit Factor */}
              <div className="bg-neutral-950 border border-neutral-800/80 rounded-2xl p-4 shadow-xl flex flex-col justify-between">
                <span className="text-[10px] uppercase text-neutral-500 font-bold tracking-wider">Profit Factor</span>
                <div className="flex items-baseline justify-between mt-2">
                  <span
                    className={`text-2xl sm:text-3xl font-black ${
                      stats.profit_factor >= 1.5
                        ? "text-emerald-400"
                        : stats.profit_factor >= 1.0
                        ? "text-amber-400"
                        : "text-rose-400"
                    }`}
                  >
                    {stats.profit_factor}
                  </span>
                  <span className="text-[10px] text-neutral-400">Gross P/L</span>
                </div>
              </div>

              {/* Max Drawdown */}
              <div className="bg-neutral-950 border border-neutral-800/80 rounded-2xl p-4 shadow-xl flex flex-col justify-between">
                <span className="text-[10px] uppercase text-neutral-500 font-bold tracking-wider">Max Drawdown</span>
                <div className="flex items-baseline justify-between mt-2">
                  <span className="text-2xl sm:text-3xl font-black text-rose-400">
                    {stats.max_drawdown_pct}%
                  </span>
                  <span className="text-[10px] text-neutral-400">${stats.max_drawdown.toFixed(0)}</span>
                </div>
              </div>

              {/* Avg R & Median */}
              <div className="bg-neutral-950 border border-neutral-800/80 rounded-2xl p-4 shadow-xl flex flex-col justify-between">
                <span className="text-[10px] uppercase text-neutral-500 font-bold tracking-wider">Avg Trade R</span>
                <div className="flex items-baseline justify-between mt-2">
                  <span
                    className={`text-2xl sm:text-3xl font-black ${
                      stats.average_r >= 0 ? "text-white" : "text-rose-400"
                    }`}
                  >
                    {stats.average_r > 0 ? "+" : ""}
                    {stats.average_r}R
                  </span>
                  <span className="text-[10px] text-neutral-400">Avg {stats.average_holding_minutes}m</span>
                </div>
              </div>
            </div>

            {/* 2. Equity Curve Chart */}
            <div className="bg-neutral-950 border border-neutral-800/80 rounded-2xl p-4 sm:p-5 shadow-2xl space-y-3 font-mono">
              <div className="flex items-center justify-between pb-2 border-b border-neutral-800/80">
                <div className="flex items-center gap-2">
                  <BarChart3 className="w-4 h-4 text-amber-400" />
                  <h3 className="text-xs font-bold uppercase tracking-wider text-neutral-200">
                    Simulated Equity & Drawdown Curve
                  </h3>
                </div>
                <span className="text-xs text-neutral-400">
                  Initial Capital: <strong className="text-white">${capital.toLocaleString()}</strong> • Period:{" "}
                  <span className="text-amber-400 font-semibold">{backtestResult.period.total_1m_candles} 1m Bars</span>
                </span>
              </div>

              {/* Equity Curve Visual Rendering */}
              {backtestResult.equity_curve && backtestResult.equity_curve.length > 1 ? (
                <div className="h-[200px] w-full bg-neutral-900/40 rounded-xl p-3 border border-neutral-800/60 relative flex flex-col justify-between overflow-hidden">
                  {/* Min / Max Labels */}
                  <div className="flex justify-between text-[10px] text-neutral-500 z-10">
                    <span>
                      Peak: $
                      {Math.max(...backtestResult.equity_curve.map((p) => p.equity)).toFixed(2)}
                    </span>
                    <span>
                      End: $
                      {backtestResult.equity_curve[backtestResult.equity_curve.length - 1].equity.toFixed(2)}
                    </span>
                  </div>

                  {/* SVG Chart Polyline */}
                  <svg className="w-full h-[140px] overflow-visible" preserveAspectRatio="none">
                    {(() => {
                      const pts = backtestResult.equity_curve;
                      const equities = pts.map((p) => p.equity);
                      const minEq = Math.min(...equities) * 0.998;
                      const maxEq = Math.max(...equities) * 1.002;
                      const range = maxEq - minEq || 1;

                      const pointsStr = pts
                        .map((p, idx) => {
                          const x = (idx / (pts.length - 1)) * 100;
                          const y = 100 - ((p.equity - minEq) / range) * 100;
                          return `${x},${y}`;
                        })
                        .join(" ");

                      return (
                        <>
                          <polyline
                            fill="none"
                            stroke="#f59e0b"
                            strokeWidth="2.5"
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            points={pointsStr}
                          />
                        </>
                      );
                    })()}
                  </svg>

                  <div className="flex justify-between text-[10px] text-neutral-500 z-10 border-t border-neutral-800/40 pt-1">
                    <span>Start: {backtestResult.period.start.slice(0, 16).replace("T", " ")}</span>
                    <span>End: {backtestResult.period.end.slice(0, 16).replace("T", " ")}</span>
                  </div>
                </div>
              ) : (
                <div className="h-[120px] flex items-center justify-center text-xs text-neutral-500 italic">
                  No trade executions in selected period to plot curve.
                </div>
              )}
            </div>

            {/* 3. Detailed Performance Breakdowns: LONG vs SHORT & Signal Strength */}
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 font-mono text-xs">
              {/* LONG vs SHORT Comparative (6 cols) */}
              <div className="lg:col-span-6 bg-neutral-950 border border-neutral-800/80 rounded-2xl p-4 shadow-xl space-y-3">
                <h3 className="text-xs font-bold uppercase tracking-wider text-neutral-200 pb-2 border-b border-neutral-800/80 flex items-center gap-1.5">
                  <Layers className="w-3.5 h-3.5 text-amber-400" />
                  <span>Directional Breakdown (LONG vs SHORT)</span>
                </h3>

                <div className="grid grid-cols-2 gap-3">
                  {/* LONG Card */}
                  <div className="bg-neutral-900/60 border border-emerald-900/40 rounded-xl p-3 space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="font-bold text-emerald-400 flex items-center gap-1">
                        <ArrowUpRight className="w-3.5 h-3.5" /> LONG SETUPS
                      </span>
                      <span className="text-[10px] text-neutral-400 bg-neutral-950 px-1.5 py-0.5 rounded border border-neutral-800">
                        {stats.by_direction?.LONG?.total_trades || 0} Trades
                      </span>
                    </div>
                    <div className="space-y-1 text-[11px]">
                      <div className="flex justify-between text-neutral-400">
                        <span>Win Rate:</span>
                        <span className="font-bold text-white">{stats.by_direction?.LONG?.win_rate || 0}%</span>
                      </div>
                      <div className="flex justify-between text-neutral-400">
                        <span>Total Return:</span>
                        <span
                          className={`font-bold ${
                            (stats.by_direction?.LONG?.total_r || 0) >= 0 ? "text-emerald-400" : "text-rose-400"
                          }`}
                        >
                          {stats.by_direction?.LONG?.total_r || 0}R
                        </span>
                      </div>
                      <div className="flex justify-between text-neutral-400">
                        <span>Profit Factor:</span>
                        <span className="font-bold text-white">{stats.by_direction?.LONG?.profit_factor || 0}</span>
                      </div>
                    </div>
                  </div>

                  {/* SHORT Card */}
                  <div className="bg-neutral-900/60 border border-rose-900/40 rounded-xl p-3 space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="font-bold text-rose-400 flex items-center gap-1">
                        <ArrowDownRight className="w-3.5 h-3.5" /> SHORT SETUPS
                      </span>
                      <span className="text-[10px] text-neutral-400 bg-neutral-950 px-1.5 py-0.5 rounded border border-neutral-800">
                        {stats.by_direction?.SHORT?.total_trades || 0} Trades
                      </span>
                    </div>
                    <div className="space-y-1 text-[11px]">
                      <div className="flex justify-between text-neutral-400">
                        <span>Win Rate:</span>
                        <span className="font-bold text-white">{stats.by_direction?.SHORT?.win_rate || 0}%</span>
                      </div>
                      <div className="flex justify-between text-neutral-400">
                        <span>Total Return:</span>
                        <span
                          className={`font-bold ${
                            (stats.by_direction?.SHORT?.total_r || 0) >= 0 ? "text-emerald-400" : "text-rose-400"
                          }`}
                        >
                          {stats.by_direction?.SHORT?.total_r || 0}R
                        </span>
                      </div>
                      <div className="flex justify-between text-neutral-400">
                        <span>Profit Factor:</span>
                        <span className="font-bold text-white">{stats.by_direction?.SHORT?.profit_factor || 0}</span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              {/* Signal Strength & Session Breakdown (6 cols) */}
              <div className="lg:col-span-6 bg-neutral-950 border border-neutral-800/80 rounded-2xl p-4 shadow-xl space-y-3">
                <h3 className="text-xs font-bold uppercase tracking-wider text-neutral-200 pb-2 border-b border-neutral-800/80 flex items-center gap-1.5">
                  <Activity className="w-3.5 h-3.5 text-amber-400" />
                  <span>Performance by Score Confluence (7 - 10)</span>
                </h3>

                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                  {[7, 8, 9, 10].map((score) => {
                    const sItem = stats.by_strength?.find((s) => s.strength === score);
                    return (
                      <div key={score} className="bg-neutral-900/50 border border-neutral-800/70 p-2.5 rounded-xl space-y-1">
                        <div className="flex items-center justify-between text-[10px] text-neutral-400">
                          <span>Score {score}/10</span>
                          <span className="text-white font-bold">{sItem?.total_trades || 0}t</span>
                        </div>
                        <div className="text-sm font-bold text-amber-400">{sItem?.win_rate || 0}%</div>
                        <div className="text-[10px] text-neutral-400">
                          {sItem ? `${sItem.total_r > 0 ? "+" : ""}${sItem.total_r}R` : "--"}
                        </div>
                      </div>
                    );
                  })}
                </div>

                {/* Session breakdown list */}
                <div className="pt-2 border-t border-neutral-800/60 flex flex-wrap gap-2 text-[10px]">
                  {stats.by_session?.map((sess) => (
                    <span
                      key={sess.session}
                      className="bg-neutral-900 border border-neutral-800 px-2 py-0.5 rounded text-neutral-300"
                    >
                      {sess.session}: <strong className="text-white">{sess.total_trades}t</strong> (
                      <span className={sess.total_r >= 0 ? "text-emerald-400" : "text-rose-400"}>
                        {sess.total_r > 0 ? "+" : ""}
                        {sess.total_r}R
                      </span>
                      )
                    </span>
                  ))}
                </div>
              </div>
            </div>

            {/* 4. Trade History & Signal Journal */}
            <div className="bg-neutral-950 border border-neutral-800/80 rounded-2xl p-4 sm:p-5 shadow-2xl space-y-3 font-mono">
              <div className="flex flex-wrap items-center justify-between gap-3 pb-3 border-b border-neutral-800/80">
                <div className="flex items-center gap-2">
                  <History className="w-4 h-4 text-amber-400" />
                  <h3 className="text-xs font-bold uppercase tracking-wider text-neutral-200">
                    Signal Journal & Simulated Trade History ({filteredTrades.length} Trades)
                  </h3>
                </div>

                {/* Filters */}
                <div className="flex flex-wrap items-center gap-2 text-xs">
                  <div className="flex items-center bg-neutral-900 border border-neutral-800 rounded-lg p-0.5">
                    {(["ALL", "WIN", "LOSS", "LONG", "SHORT", "EXPIRED"] as const).map((filterVal) => (
                      <button
                        key={filterVal}
                        onClick={() => setTradeFilter(filterVal)}
                        className={`px-2 py-1 rounded text-[11px] font-semibold transition cursor-pointer ${
                          tradeFilter === filterVal
                            ? "bg-amber-500 text-neutral-950 font-bold shadow"
                            : "text-neutral-400 hover:text-white"
                        }`}
                      >
                        {filterVal}
                      </button>
                    ))}
                  </div>

                  <div className="relative">
                    <input
                      type="text"
                      placeholder="Search ID/Date..."
                      value={searchQuery}
                      onChange={(e) => setSearchQuery(e.target.value)}
                      className="bg-neutral-900 border border-neutral-800 rounded-lg px-2.5 py-1 text-xs text-white placeholder-neutral-500 focus:outline-none focus:border-amber-500 w-36"
                    />
                  </div>
                </div>
              </div>

              {/* Trade Journal Table */}
              <div className="overflow-x-auto max-h-[480px] overflow-y-auto">
                <table className="w-full text-left text-xs text-neutral-300">
                  <thead className="bg-neutral-900/80 text-[10px] uppercase text-neutral-400 sticky top-0 border-b border-neutral-800">
                    <tr>
                      <th className="py-2.5 px-3">Signal Time (UTC)</th>
                      <th className="py-2.5 px-3">Type</th>
                      <th className="py-2.5 px-3">Score</th>
                      <th className="py-2.5 px-3">Entry</th>
                      <th className="py-2.5 px-3">Stop Loss</th>
                      <th className="py-2.5 px-3">TP1</th>
                      <th className="py-2.5 px-3">Exit</th>
                      <th className="py-2.5 px-3">Result</th>
                      <th className="py-2.5 px-3">Return (R)</th>
                      <th className="py-2.5 px-3">Holding</th>
                      <th className="py-2.5 px-3">Exit Reason</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-neutral-900/80 font-mono text-[11px]">
                    {filteredTrades.length > 0 ? (
                      filteredTrades.map((t) => (
                        <tr key={t.id} className="hover:bg-neutral-900/40 transition">
                          <td className="py-2 px-3 text-neutral-400">
                            {t.signal_time_iso.slice(0, 16).replace("T", " ")}
                          </td>
                          <td className="py-2 px-3">
                            <span
                              className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${
                                t.direction === "LONG"
                                  ? "bg-emerald-950/80 text-emerald-400 border border-emerald-800/60"
                                  : "bg-rose-950/80 text-rose-400 border border-rose-800/60"
                              }`}
                            >
                              {t.direction}
                            </span>
                          </td>
                          <td className="py-2 px-3 font-bold text-amber-400">{t.signal_strength}/10</td>
                          <td className="py-2 px-3 font-semibold text-white">${t.entry_price.toFixed(2)}</td>
                          <td className="py-2 px-3 text-rose-400/80">${t.stop_loss.toFixed(2)}</td>
                          <td className="py-2 px-3 text-emerald-400/80">${t.take_profit_1.toFixed(2)}</td>
                          <td className="py-2 px-3 text-white font-semibold">${t.exit_price.toFixed(2)}</td>
                          <td className="py-2 px-3">
                            <span
                              className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${
                                t.result.startsWith("TP")
                                  ? "bg-emerald-950 text-emerald-300 border border-emerald-700/60"
                                  : t.result === "STOP_LOSS"
                                  ? "bg-rose-950 text-rose-300 border border-rose-700/60"
                                  : "bg-neutral-800 text-neutral-300"
                              }`}
                            >
                              {t.result}
                            </span>
                          </td>
                          <td className="py-2 px-3 font-bold">
                            <span
                              className={
                                t.r_multiple > 0
                                  ? "text-emerald-400"
                                  : t.r_multiple < 0
                                  ? "text-rose-400"
                                  : "text-neutral-400"
                              }
                            >
                              {t.r_multiple > 0 ? "+" : ""}
                              {t.r_multiple}R
                            </span>
                          </td>
                          <td className="py-2 px-3 text-neutral-400">{t.holding_minutes}m</td>
                          <td className="py-2 px-3 text-[10px] text-neutral-400 truncate max-w-[200px]" title={t.exit_reason}>
                            {t.exit_reason}
                          </td>
                        </tr>
                      ))
                    ) : (
                      <tr>
                        <td colSpan={11} className="py-8 text-center text-neutral-500 italic">
                          No trades match the active filter criteria.
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>

            {/* 5. Mandatory Assumptions & Disclaimer Box */}
            <div className="bg-neutral-950 border border-neutral-800 rounded-2xl p-4 font-mono text-xs text-neutral-400 space-y-2">
              <div className="flex items-center gap-2 text-amber-400 font-bold">
                <ShieldAlert className="w-4 h-4" />
                <span>Execution Assumptions & Verification Disclaimers</span>
              </div>
              <p className="text-[11px] leading-relaxed text-neutral-400">
                Historical backtest results are simulations based on historical market data and stated execution assumptions.
                They do not guarantee future performance and do not represent actual executed trades.
              </p>
              <div className="flex flex-wrap gap-4 pt-1 text-[11px] text-neutral-300 border-t border-neutral-900">
                <span>
                  • <strong>Execution Mode:</strong> Fixed spread (${spread.toFixed(2)})
                </span>
                <span>
                  • <strong>Same-Candle Policy:</strong> Stop-Loss First
                </span>
                <span>
                  • <strong>Virtual Entry:</strong> Next 1m candle open
                </span>
                <span>
                  • <strong>Signal Model:</strong> Live rule-confluence engine
                </span>
              </div>
            </div>
          </div>
        )}
      </main>

      {/* Footer */}
      <footer className="w-full bg-neutral-950 border-t border-neutral-900 px-4 py-3 text-center text-xs font-mono text-neutral-400">
        <div className="max-w-7xl mx-auto flex flex-wrap items-center justify-between gap-2">
          <div>
            Exness MT5 <span className="text-amber-400 font-bold">XAUUSD</span> Historical Backtest Engine (Local-Only)
          </div>
          <div className="flex items-center gap-2">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
            <span>Strict Zero Look-Ahead Bias • Read-Only Architecture</span>
          </div>
        </div>
      </footer>
    </div>
  );
}
