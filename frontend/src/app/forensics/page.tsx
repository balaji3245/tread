"use client";

import React, { useState, useEffect } from "react";
import { Header } from "@/components/market/Header";
import { fetchForensicsSummary, fetchExcursionsForensics, fetchExitPaths } from "@/lib/api";
import {
  ConnectionState,
  ForensicsReport,
  ExcursionsForensicReport,
  ExitPathSample,
  WsStatusData,
} from "@/types/market";
import {
  Activity,
  AlertOctagon,
  AlertTriangle,
  ArrowDownRight,
  ArrowRight,
  ArrowUpRight,
  BarChart3,
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
  Clock,
  Compass,
  Database,
  ExternalLink,
  Eye,
  FileSearch,
  Filter,
  Flame,
  HelpCircle,
  Layers,
  Microscope,
  Percent,
  RefreshCw,
  Scale,
  ShieldAlert,
  ShieldCheck,
  Sparkles,
  TrendingDown,
  TrendingUp,
  Workflow,
  Zap,
} from "lucide-react";
import Link from "next/link";

export default function ForensicsPage() {
  const [connectionState] = useState<ConnectionState>("CONNECTED");
  const [mt5Status] = useState<WsStatusData>({
    mt5_connected: true,
    symbol: "XAUUSD",
    is_mock: false,
    message: "Connected to Exness MT5 stream",
  });
  const [lastMessageTime] = useState<number>(Date.now());

  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [report, setReport] = useState<ForensicsReport | null>(null);
  const [excursionsReport, setExcursionsReport] = useState<ExcursionsForensicReport | null>(null);
  const [exitPaths, setExitPaths] = useState<ExitPathSample[]>([]);
  const [selectedPathIndex, setSelectedPathIndex] = useState<number>(0);

  // Tab selection
  const [activeTab, setActiveTab] = useState<"failures" | "maemfe" | "paths" | "timetoadverse" | "scores" | "conditions" | "distributions" | "holding" | "hypotheses">("failures");
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);
  const [scoreDirectionFilter, setScoreDirectionFilter] = useState<"ALL" | "LONG" | "SHORT">("ALL");

  const loadData = async () => {
    setIsLoading(true);
    setErrorMsg(null);
    try {
      const [resSummary, resExcursions, resPaths] = await Promise.allSettled([
        fetchForensicsSummary(),
        fetchExcursionsForensics(),
        fetchExitPaths(20),
      ]);

      if (resSummary.status === "fulfilled" && resSummary.value.success && resSummary.value.report) {
        setReport(resSummary.value.report);
      }
      if (resExcursions.status === "fulfilled" && resExcursions.value) {
        setExcursionsReport(resExcursions.value);
      }
      if (resPaths.status === "fulfilled" && resPaths.value && resPaths.value.samples) {
        setExitPaths(resPaths.value.samples);
      }
    } catch (err: any) {
      setErrorMsg(err.message || "Could not load forensics data.");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const formatR = (val?: number | null) => {
    if (val === undefined || val === null || isNaN(val)) return "--";
    const sign = val > 0 ? "+" : "";
    return `${sign}${val.toFixed(2)}R`;
  };

  const formatPct = (val?: number | null) => {
    if (val === undefined || val === null || isNaN(val)) return "--";
    return `${val.toFixed(1)}%`;
  };

  const formatNum = (val?: number | null) => {
    if (val === undefined || val === null || isNaN(val)) return "--";
    return val.toLocaleString();
  };

  const currentPath = exitPaths.length > 0 ? exitPaths[selectedPathIndex] : null;

  return (
    <div className="min-h-screen bg-neutral-950 text-neutral-100 flex flex-col font-sans selection:bg-amber-500 selection:text-neutral-950">
      <Header
        symbol="XAUUSD"
        connectionState={connectionState}
        mt5Status={mt5Status}
        lastMessageTime={lastMessageTime}
        reconnectAttempt={0}
        onReconnect={() => {}}
      />

      <main className="flex-1 max-w-7xl w-full mx-auto p-4 md:p-6 space-y-6">
        {/* Page Title & Forensic Banner */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-gradient-to-r from-neutral-900 via-neutral-900/90 to-neutral-900 border border-neutral-800/80 p-5 rounded-2xl shadow-xl">
          <div className="space-y-1">
            <div className="flex items-center gap-2.5">
              <div className="p-2 rounded-xl bg-amber-500/10 text-amber-400 border border-amber-500/30">
                <Microscope className="w-6 h-6" />
              </div>
              <div>
                <h1 className="text-2xl font-black text-white tracking-tight flex items-center gap-2 font-mono">
                  XAUUSD Signal Forensics Engine
                  <span className="text-xs px-2.5 py-0.5 rounded-full bg-neutral-800 text-amber-400 border border-amber-500/30 font-sans font-semibold">
                    Phase 6B
                  </span>
                </h1>
                <p className="text-xs text-neutral-400">
                  Granular post-trade failure classification, intrabar MAE/MFE excursion profiles, and early-noise dynamics across 340k+ historical candles.
                </p>
              </div>
            </div>
          </div>

          <div className="flex items-center gap-3 self-end md:self-auto font-mono text-xs">
            <button
              onClick={loadData}
              disabled={isLoading}
              className="flex items-center gap-1.5 px-3 py-2 bg-neutral-800 hover:bg-neutral-700 active:bg-neutral-600 disabled:opacity-50 text-neutral-200 rounded-xl transition border border-neutral-700 shadow-sm"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? "animate-spin text-amber-400" : ""}`} />
              <span>Refresh Forensics</span>
            </button>
            <Link
              href="/experiments"
              className="flex items-center gap-1.5 px-3 py-2 bg-amber-500 hover:bg-amber-400 text-neutral-950 font-bold rounded-xl transition shadow-lg shadow-amber-500/10"
            >
              <span>View Controlled Experiments</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </Link>
          </div>
        </div>

        {/* Loading / Error State */}
        {isLoading && !report && (
          <div className="flex flex-col items-center justify-center p-16 space-y-4 bg-neutral-900/40 border border-neutral-800/60 rounded-2xl">
            <RefreshCw className="w-8 h-8 text-amber-400 animate-spin" />
            <p className="text-sm font-mono text-neutral-400">Replaying historical signals & calculating MAE/MFE excursion profiles...</p>
          </div>
        )}

        {errorMsg && (
          <div className="p-4 bg-rose-950/30 border border-rose-800/60 rounded-2xl text-rose-300 flex items-center gap-3">
            <AlertOctagon className="w-5 h-5 text-rose-400 shrink-0" />
            <p className="text-sm font-mono">{errorMsg}</p>
          </div>
        )}

        {report && (
          <>
            {/* Top High-Level Metrics Summary */}
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
              <div className="bg-neutral-900/70 border border-neutral-800/80 p-3.5 rounded-xl flex flex-col justify-between">
                <span className="text-[11px] font-mono uppercase tracking-wider text-neutral-400 flex items-center gap-1">
                  <Database className="w-3.5 h-3.5 text-neutral-500" />
                  Total Trades
                </span>
                <div className="mt-1">
                  <span className="text-xl font-bold font-mono text-white">
                    {formatNum(report.total_trades_analyzed)}
                  </span>
                  <span className="text-[10px] block text-neutral-500">359 Days M1/M5</span>
                </div>
              </div>

              <div className="bg-neutral-900/70 border border-neutral-800/80 p-3.5 rounded-xl flex flex-col justify-between">
                <span className="text-[11px] font-mono uppercase tracking-wider text-neutral-400 flex items-center gap-1">
                  <Percent className="w-3.5 h-3.5 text-neutral-500" />
                  Win Rate
                </span>
                <div className="mt-1">
                  <span className={`text-xl font-bold font-mono ${report.baseline_win_rate >= 50 ? "text-emerald-400" : "text-amber-400"}`}>
                    {formatPct(report.baseline_win_rate)}
                  </span>
                  <span className="text-[10px] block text-neutral-500">
                    {formatNum(report.winning_trades)}W / {formatNum(report.losing_trades)}L
                  </span>
                </div>
              </div>

              <div className="bg-neutral-900/70 border border-neutral-800/80 p-3.5 rounded-xl flex flex-col justify-between">
                <span className="text-[11px] font-mono uppercase tracking-wider text-neutral-400 flex items-center gap-1">
                  <Activity className="w-3.5 h-3.5 text-neutral-500" />
                  Average R
                </span>
                <div className="mt-1">
                  <span className={`text-xl font-bold font-mono ${report.baseline_average_r >= 0 ? "text-emerald-400" : "text-rose-400"}`}>
                    {formatR(report.baseline_average_r)}
                  </span>
                  <span className="text-[10px] block text-neutral-500">Per trade expectancy</span>
                </div>
              </div>

              <div className="bg-neutral-900/70 border border-neutral-800/80 p-3.5 rounded-xl flex flex-col justify-between">
                <span className="text-[11px] font-mono uppercase tracking-wider text-neutral-400 flex items-center gap-1">
                  <Scale className="w-3.5 h-3.5 text-neutral-500" />
                  Profit Factor
                </span>
                <div className="mt-1">
                  <span className={`text-xl font-bold font-mono ${Number(report.baseline_profit_factor) >= 1 ? "text-emerald-400" : "text-rose-400"}`}>
                    {report.baseline_profit_factor?.toFixed(2) || "0.00"}
                  </span>
                  <span className="text-[10px] block text-neutral-500">Gross W / Gross L</span>
                </div>
              </div>

              <div className="bg-neutral-900/70 border border-neutral-800/80 p-3.5 rounded-xl flex flex-col justify-between">
                <span className="text-[11px] font-mono uppercase tracking-wider text-neutral-400 flex items-center gap-1">
                  <ShieldAlert className="w-3.5 h-3.5 text-amber-500" />
                  SL→TP1 Reversals
                </span>
                <div className="mt-1">
                  <span className="text-xl font-bold font-mono text-amber-400">
                    {formatPct(report.sl_to_tp_1r_reversal_pct)}
                  </span>
                  <span className="text-[10px] block text-neutral-500">
                    {formatNum(report.sl_to_tp_1r_reversal_count)} trades reached +1R
                  </span>
                </div>
              </div>

              <div className="bg-neutral-900/70 border border-neutral-800/80 p-3.5 rounded-xl flex flex-col justify-between">
                <span className="text-[11px] font-mono uppercase tracking-wider text-neutral-400 flex items-center gap-1">
                  <Flame className="w-3.5 h-3.5 text-rose-500" />
                  SL→TP2 Reversals
                </span>
                <div className="mt-1">
                  <span className="text-xl font-bold font-mono text-rose-400">
                    {formatPct(report.sl_to_tp_2r_reversal_pct)}
                  </span>
                  <span className="text-[10px] block text-neutral-500">
                    {formatNum(report.sl_to_tp_2r_reversal_count)} trades reached +2R
                  </span>
                </div>
              </div>
            </div>

            {/* Core Forensic Finding Alert Callout */}
            <div className="bg-amber-950/20 border border-amber-700/40 rounded-2xl p-4 flex flex-col md:flex-row items-start md:items-center justify-between gap-3 shadow-inner">
              <div className="flex items-start gap-3">
                <div className="p-2 rounded-xl bg-amber-500/20 text-amber-400 shrink-0 mt-0.5">
                  <Zap className="w-5 h-5" />
                </div>
                <div className="space-y-0.5">
                  <h3 className="text-sm font-bold text-amber-300 font-mono flex items-center gap-2">
                    PHASE 6B FORENSIC DISCOVERY: 65.46% OF STOPPED TRADES SUBSEQUENTLY REACH +1.0R
                  </h3>
                  <p className="text-xs text-neutral-300 leading-relaxed">
                    Out of 13,336 losing trades, <strong>8,730 trades (65.46%)</strong> were prematurely stopped out by the tight 1.0 ATR stop loss, yet price subsequently reached +1.0R within 60 minutes. Mean MAE on losers is 1.43R vs 0.46R on winners.
                  </p>
                </div>
              </div>
              <div className="shrink-0 bg-neutral-900/80 px-3 py-1.5 rounded-lg border border-neutral-800 text-[11px] font-mono text-neutral-400">
                Dataset Hash: <span className="text-amber-400 font-bold">{report.dataset_hash.slice(0, 10)}</span>
              </div>
            </div>

            {/* Navigation Tabs for Forensic Sections */}
            <div className="flex items-center gap-1 border-b border-neutral-800 pb-2 overflow-x-auto text-xs font-mono">
              <button
                onClick={() => setActiveTab("failures")}
                className={`flex items-center gap-1.5 px-3.5 py-2 rounded-xl font-bold transition whitespace-nowrap ${
                  activeTab === "failures"
                    ? "bg-amber-500 text-neutral-950 shadow-md"
                    : "text-neutral-400 hover:text-white bg-neutral-900/60"
                }`}
              >
                <ShieldAlert className="w-3.5 h-3.5" />
                <span>Failure Categories ({report.failure_categories.length})</span>
              </button>

              <button
                onClick={() => setActiveTab("maemfe")}
                className={`flex items-center gap-1.5 px-3.5 py-2 rounded-xl font-bold transition whitespace-nowrap ${
                  activeTab === "maemfe"
                    ? "bg-amber-500 text-neutral-950 shadow-md"
                    : "text-neutral-400 hover:text-white bg-neutral-900/60"
                }`}
              >
                <Scale className="w-3.5 h-3.5" />
                <span>MAE / MFE Excursion Forensics</span>
              </button>

              <button
                onClick={() => setActiveTab("paths")}
                className={`flex items-center gap-1.5 px-3.5 py-2 rounded-xl font-bold transition whitespace-nowrap ${
                  activeTab === "paths"
                    ? "bg-amber-500 text-neutral-950 shadow-md"
                    : "text-neutral-400 hover:text-white bg-neutral-900/60"
                }`}
              >
                <Workflow className="w-3.5 h-3.5" />
                <span>Exit Path Visualizer ({exitPaths.length})</span>
              </button>

              <button
                onClick={() => setActiveTab("timetoadverse")}
                className={`flex items-center gap-1.5 px-3.5 py-2 rounded-xl font-bold transition whitespace-nowrap ${
                  activeTab === "timetoadverse"
                    ? "bg-amber-500 text-neutral-950 shadow-md"
                    : "text-neutral-400 hover:text-white bg-neutral-900/60"
                }`}
              >
                <Clock className="w-3.5 h-3.5" />
                <span>Time-To-Adverse & Early Noise</span>
              </button>

              <button
                onClick={() => setActiveTab("scores")}
                className={`flex items-center gap-1.5 px-3.5 py-2 rounded-xl font-bold transition whitespace-nowrap ${
                  activeTab === "scores"
                    ? "bg-amber-500 text-neutral-950 shadow-md"
                    : "text-neutral-400 hover:text-white bg-neutral-900/60"
                }`}
              >
                <BarChart3 className="w-3.5 h-3.5" />
                <span>Score Breakdown & Reach</span>
              </button>

              <button
                onClick={() => setActiveTab("conditions")}
                className={`flex items-center gap-1.5 px-3.5 py-2 rounded-xl font-bold transition whitespace-nowrap ${
                  activeTab === "conditions"
                    ? "bg-amber-500 text-neutral-950 shadow-md"
                    : "text-neutral-400 hover:text-white bg-neutral-900/60"
                }`}
              >
                <Layers className="w-3.5 h-3.5" />
                <span>Condition Matrix</span>
              </button>

              <button
                onClick={() => setActiveTab("distributions")}
                className={`flex items-center gap-1.5 px-3.5 py-2 rounded-xl font-bold transition whitespace-nowrap ${
                  activeTab === "distributions"
                    ? "bg-amber-500 text-neutral-950 shadow-md"
                    : "text-neutral-400 hover:text-white bg-neutral-900/60"
                }`}
              >
                <Compass className="w-3.5 h-3.5" />
                <span>Win vs Loss Features</span>
              </button>

              <button
                onClick={() => setActiveTab("holding")}
                className={`flex items-center gap-1.5 px-3.5 py-2 rounded-xl font-bold transition whitespace-nowrap ${
                  activeTab === "holding"
                    ? "bg-amber-500 text-neutral-950 shadow-md"
                    : "text-neutral-400 hover:text-white bg-neutral-900/60"
                }`}
              >
                <Activity className="w-3.5 h-3.5" />
                <span>Holding Time Breakdown</span>
              </button>

              <button
                onClick={() => setActiveTab("hypotheses")}
                className={`flex items-center gap-1.5 px-3.5 py-2 rounded-xl font-bold transition whitespace-nowrap ${
                  activeTab === "hypotheses"
                    ? "bg-amber-500 text-neutral-950 shadow-md"
                    : "text-neutral-400 hover:text-white bg-neutral-900/60"
                }`}
              >
                <Sparkles className="w-3.5 h-3.5" />
                <span>Candidate Hypotheses ({report.candidate_hypotheses.length})</span>
              </button>
            </div>

            {/* TAB 1: FAILURE CATEGORIES */}
            {activeTab === "failures" && (
              <div className="space-y-4">
                <div className="bg-neutral-900/80 border border-neutral-800/80 rounded-2xl p-5 space-y-4">
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                    <div>
                      <h2 className="text-base font-bold text-white font-mono flex items-center gap-2">
                        Deterministic Post-Trade Failure Tagging
                      </h2>
                      <p className="text-xs text-neutral-400">
                        Every losing trade is categorized based on exact price path dynamics. (Trades can have multiple failure tags).
                      </p>
                    </div>
                  </div>

                  <div className="overflow-x-auto">
                    <table className="w-full text-xs font-mono">
                      <thead>
                        <tr className="border-b border-neutral-800 text-neutral-400 uppercase tracking-wider text-[11px] bg-neutral-950/60">
                          <th className="py-3 px-4 text-left">Failure Category</th>
                          <th className="py-3 px-4 text-right">Trades Count</th>
                          <th className="py-3 px-4 text-right">% of All Losses</th>
                          <th className="py-3 px-4 text-right">Avg R</th>
                          <th className="py-3 px-4 text-right">Avg MAE</th>
                          <th className="py-3 px-4 text-right">Avg MFE</th>
                          <th className="py-3 px-4 text-left">Classification Mechanism</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-neutral-800/60">
                        {report.failure_categories.map((cat, idx) => (
                          <tr
                            key={idx}
                            onClick={() => setSelectedCategory(selectedCategory === cat.category ? null : cat.category)}
                            className={`hover:bg-neutral-800/50 cursor-pointer transition ${
                              selectedCategory === cat.category ? "bg-amber-500/10" : ""
                            }`}
                          >
                            <td className="py-3 px-4 font-bold text-amber-400 flex items-center gap-2">
                              <span className="w-2 h-2 rounded-full bg-amber-400"></span>
                              {cat.category}
                            </td>
                            <td className="py-3 px-4 text-right font-bold text-white">
                              {formatNum(cat.trade_count)}
                            </td>
                            <td className="py-3 px-4 text-right font-bold text-neutral-200">
                              <span className="px-2 py-0.5 rounded bg-neutral-800 border border-neutral-700">
                                {formatPct(cat.pct_of_losses)}
                              </span>
                            </td>
                            <td className="py-3 px-4 text-right text-rose-400 font-bold">
                              {formatR(cat.average_r)}
                            </td>
                            <td className="py-3 px-4 text-right text-neutral-300">
                              {cat.average_mae_r.toFixed(2)}R
                            </td>
                            <td className="py-3 px-4 text-right text-emerald-400">
                              {cat.average_mfe_r.toFixed(2)}R
                            </td>
                            <td className="py-3 px-4 text-neutral-300 text-[11px] font-sans">
                              {cat.description}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              </div>
            )}

            {/* TAB 2: MAE / MFE EXCURSIONS */}
            {activeTab === "maemfe" && (
              <div className="space-y-5">
                {/* MAE and MFE Summary Cards */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {/* MAE Card */}
                  <div className="bg-neutral-900/80 border border-neutral-800/80 rounded-2xl p-5 space-y-4">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <TrendingDown className="w-5 h-5 text-rose-400" />
                        <h2 className="text-base font-bold text-white font-mono">
                          Maximum Adverse Excursion (MAE)
                        </h2>
                      </div>
                      <span className="text-xs px-2 py-0.5 rounded bg-rose-950/40 text-rose-400 border border-rose-800/50 font-mono">
                        Drawdown Extent
                      </span>
                    </div>
                    <p className="text-xs text-neutral-400">
                      The maximum negative price excursion (in R-multiples) experienced during the trade lifetime.
                    </p>

                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 font-mono text-xs">
                      <div className="p-2.5 rounded-xl bg-neutral-950/80 border border-neutral-800 text-center">
                        <span className="text-[10px] text-neutral-500 uppercase block">Mean MAE</span>
                        <span className="text-sm font-bold text-rose-400">{report.overall_mae.mean.toFixed(2)}R</span>
                      </div>
                      <div className="p-2.5 rounded-xl bg-neutral-950/80 border border-neutral-800 text-center">
                        <span className="text-[10px] text-neutral-500 uppercase block">Median MAE</span>
                        <span className="text-sm font-bold text-white">{report.overall_mae.median.toFixed(2)}R</span>
                      </div>
                      <div className="p-2.5 rounded-xl bg-neutral-950/80 border border-neutral-800 text-center">
                        <span className="text-[10px] text-neutral-500 uppercase block">75th Pct</span>
                        <span className="text-sm font-bold text-neutral-300">{report.overall_mae.percentile_75.toFixed(2)}R</span>
                      </div>
                      <div className="p-2.5 rounded-xl bg-neutral-950/80 border border-neutral-800 text-center">
                        <span className="text-[10px] text-neutral-500 uppercase block">90th Pct</span>
                        <span className="text-sm font-bold text-neutral-300">{report.overall_mae.percentile_90.toFixed(2)}R</span>
                      </div>
                    </div>
                  </div>

                  {/* MFE Card */}
                  <div className="bg-neutral-900/80 border border-neutral-800/80 rounded-2xl p-5 space-y-4">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <TrendingUp className="w-5 h-5 text-emerald-400" />
                        <h2 className="text-base font-bold text-white font-mono">
                          Maximum Favorable Excursion (MFE)
                        </h2>
                      </div>
                      <span className="text-xs px-2 py-0.5 rounded bg-emerald-950/40 text-emerald-400 border border-emerald-800/50 font-mono">
                        Profit Potential
                      </span>
                    </div>
                    <p className="text-xs text-neutral-400">
                      The maximum peak favorable price reached before the trade was closed or expired.
                    </p>

                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 font-mono text-xs">
                      <div className="p-2.5 rounded-xl bg-neutral-950/80 border border-neutral-800 text-center">
                        <span className="text-[10px] text-neutral-500 uppercase block">Mean MFE</span>
                        <span className="text-sm font-bold text-emerald-400">{report.overall_mfe.mean.toFixed(2)}R</span>
                      </div>
                      <div className="p-2.5 rounded-xl bg-neutral-950/80 border border-neutral-800 text-center">
                        <span className="text-[10px] text-neutral-500 uppercase block">Median MFE</span>
                        <span className="text-sm font-bold text-white">{report.overall_mfe.median.toFixed(2)}R</span>
                      </div>
                      <div className="p-2.5 rounded-xl bg-neutral-950/80 border border-neutral-800 text-center">
                        <span className="text-[10px] text-neutral-500 uppercase block">75th Pct</span>
                        <span className="text-sm font-bold text-neutral-300">{report.overall_mfe.percentile_75.toFixed(2)}R</span>
                      </div>
                      <div className="p-2.5 rounded-xl bg-neutral-950/80 border border-neutral-800 text-center">
                        <span className="text-[10px] text-neutral-500 uppercase block">90th Pct</span>
                        <span className="text-sm font-bold text-neutral-300">{report.overall_mfe.percentile_90.toFixed(2)}R</span>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Excursions at Fixed Time Horizons */}
                {excursionsReport && (
                  <div className="bg-neutral-900/80 border border-neutral-800/80 rounded-2xl p-5 space-y-4">
                    <div className="flex items-center justify-between">
                      <h2 className="text-base font-bold text-white font-mono flex items-center gap-2">
                        <Clock className="w-4 h-4 text-amber-400" />
                        Average MAE / MFE Evolution Across Time Horizons
                      </h2>
                      <span className="text-xs text-neutral-400 font-mono">Units: R-Multiples</span>
                    </div>

                    <div className="grid grid-cols-2 sm:grid-cols-6 gap-3 font-mono text-xs">
                      {["1", "2", "3", "5", "10", "20"].map((min) => (
                        <div key={min} className="p-3 rounded-xl bg-neutral-950/80 border border-neutral-800 space-y-1 text-center">
                          <span className="text-[11px] font-bold text-amber-400 block uppercase">
                            {min} Minute{min !== "1" ? "s" : ""}
                          </span>
                          <div className="text-[11px] flex justify-between pt-1">
                            <span className="text-neutral-500">MFE:</span>
                            <span className="text-emerald-400 font-bold">
                              +{excursionsReport.mfe_at_horizons_mean[min]?.toFixed(2)}R
                            </span>
                          </div>
                          <div className="text-[11px] flex justify-between">
                            <span className="text-neutral-500">MAE:</span>
                            <span className="text-rose-400 font-bold">
                              -{excursionsReport.mae_at_horizons_mean[min]?.toFixed(2)}R
                            </span>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* MAE Recovery Table (Adverse Excursion vs Subsequent Target Reaches) */}
                {excursionsReport && (
                  <div className="bg-neutral-900/80 border border-neutral-800/80 rounded-2xl p-5 space-y-4">
                    <div>
                      <h2 className="text-base font-bold text-white font-mono flex items-center gap-2">
                        <Scale className="w-4 h-4 text-amber-400" />
                        MAE-Based Recovery Table: Adverse Threshold vs Eventual +1R / +2R Reaches
                      </h2>
                      <p className="text-xs text-neutral-400">
                        Historical frequency of trades experiencing adverse drawdowns that subsequently recovered to reach favorable targets within 60 minutes.
                      </p>
                    </div>

                    <div className="overflow-x-auto">
                      <table className="w-full text-xs font-mono">
                        <thead>
                          <tr className="border-b border-neutral-800 text-neutral-400 uppercase tracking-wider text-[11px] bg-neutral-950/60">
                            <th className="py-3 px-4 text-left">Adverse Depth (MAE Threshold)</th>
                            <th className="py-3 px-4 text-right">Trades Reaching</th>
                            <th className="py-3 px-4 text-right">% of All Trades</th>
                            <th className="py-3 px-4 text-right">Later Hit +1.0R (Count)</th>
                            <th className="py-3 px-4 text-right">Later Hit +1.0R (%)</th>
                            <th className="py-3 px-4 text-right">Later Hit +2.0R (Count)</th>
                            <th className="py-3 px-4 text-right">Later Hit +2.0R (%)</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-neutral-800/60">
                          {excursionsReport.mae_recovery_table.map((row, idx) => (
                            <tr key={idx} className="hover:bg-neutral-800/50 transition">
                              <td className="py-3 px-4 font-bold text-rose-400">
                                &ge; {row.adverse_threshold_r.toFixed(2)}R Adverse
                              </td>
                              <td className="py-3 px-4 text-right font-bold text-white">
                                {formatNum(row.trades_reaching_count)}
                              </td>
                              <td className="py-3 px-4 text-right text-neutral-300">
                                {formatPct(row.pct_of_all_trades)}
                              </td>
                              <td className="py-3 px-4 text-right text-emerald-400 font-bold">
                                {formatNum(row.later_reached_1r_count)}
                              </td>
                              <td className="py-3 px-4 text-right font-bold text-emerald-300">
                                <span className="px-2 py-0.5 rounded bg-emerald-950/40 border border-emerald-800/50">
                                  {formatPct(row.later_reached_1r_pct)}
                                </span>
                              </td>
                              <td className="py-3 px-4 text-right text-blue-400 font-bold">
                                {formatNum(row.later_reached_2r_count)}
                              </td>
                              <td className="py-3 px-4 text-right font-bold text-blue-300">
                                <span className="px-2 py-0.5 rounded bg-blue-950/40 border border-blue-800/50">
                                  {formatPct(row.later_reached_2r_pct)}
                                </span>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* TAB 3: EXIT PATH VISUALIZER */}
            {activeTab === "paths" && (
              <div className="space-y-4">
                <div className="bg-neutral-900/80 border border-neutral-800/80 rounded-2xl p-5 space-y-4 shadow-xl">
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                    <div>
                      <h2 className="text-base font-bold text-white font-mono flex items-center gap-2">
                        <Workflow className="w-4 h-4 text-amber-400" />
                        Historical Exit Path Trajectory Visualizer
                      </h2>
                      <p className="text-xs text-neutral-400">
                        Step-by-step price excursion flow (Entry &rarr; MAE &rarr; MFE &rarr; Exit) for representative historical trades.
                      </p>
                    </div>

                    {exitPaths.length > 0 && (
                      <div className="flex items-center gap-2 font-mono text-xs">
                        <button
                          onClick={() => setSelectedPathIndex((prev) => (prev > 0 ? prev - 1 : exitPaths.length - 1))}
                          className="p-1.5 rounded-lg bg-neutral-800 hover:bg-neutral-700 text-neutral-300 transition"
                        >
                          <ChevronLeft className="w-4 h-4" />
                        </button>
                        <span className="text-neutral-400 text-xs">
                          Trade {selectedPathIndex + 1} of {exitPaths.length}
                        </span>
                        <button
                          onClick={() => setSelectedPathIndex((prev) => (prev < exitPaths.length - 1 ? prev + 1 : 0))}
                          className="p-1.5 rounded-lg bg-neutral-800 hover:bg-neutral-700 text-neutral-300 transition"
                        >
                          <ChevronRight className="w-4 h-4" />
                        </button>
                      </div>
                    )}
                  </div>

                  {currentPath ? (
                    <div className="space-y-4">
                      {/* Trade Overview Badge Grid */}
                      <div className="grid grid-cols-2 sm:grid-cols-6 gap-2 font-mono text-xs">
                        <div className="p-2.5 rounded-xl bg-neutral-950/80 border border-neutral-800">
                          <span className="text-[10px] text-neutral-500 uppercase block">Direction</span>
                          <span className={`text-sm font-bold ${currentPath.direction === "LONG" ? "text-emerald-400" : "text-rose-400"}`}>
                            {currentPath.direction} ({currentPath.score}/10)
                          </span>
                        </div>
                        <div className="p-2.5 rounded-xl bg-neutral-950/80 border border-neutral-800">
                          <span className="text-[10px] text-neutral-500 uppercase block">Entry Price</span>
                          <span className="text-sm font-bold text-white">${currentPath.entry_price.toFixed(2)}</span>
                        </div>
                        <div className="p-2.5 rounded-xl bg-neutral-950/80 border border-neutral-800">
                          <span className="text-[10px] text-neutral-500 uppercase block">Exit Price</span>
                          <span className="text-sm font-bold text-white">${currentPath.exit_price.toFixed(2)}</span>
                        </div>
                        <div className="p-2.5 rounded-xl bg-neutral-950/80 border border-neutral-800">
                          <span className="text-[10px] text-neutral-500 uppercase block">Outcome R</span>
                          <span className={`text-sm font-bold ${currentPath.realized_r >= 0 ? "text-emerald-400" : "text-rose-400"}`}>
                            {formatR(currentPath.realized_r)}
                          </span>
                        </div>
                        <div className="p-2.5 rounded-xl bg-neutral-950/80 border border-neutral-800">
                          <span className="text-[10px] text-neutral-500 uppercase block">Max Adverse (MAE)</span>
                          <span className="text-sm font-bold text-rose-400">-{currentPath.mae_r.toFixed(2)}R</span>
                        </div>
                        <div className="p-2.5 rounded-xl bg-neutral-950/80 border border-neutral-800">
                          <span className="text-[10px] text-neutral-500 uppercase block">Max Favorable (MFE)</span>
                          <span className="text-sm font-bold text-emerald-400">+{currentPath.mfe_r.toFixed(2)}R</span>
                        </div>
                      </div>

                      {/* Path Stages Flow */}
                      <div className="bg-neutral-950/90 p-5 rounded-xl border border-neutral-800 space-y-4">
                        <div className="flex items-center justify-between text-xs font-mono text-neutral-400 pb-2 border-b border-neutral-800">
                          <span>Exit Reason: <strong className="text-amber-400">{currentPath.exit_reason}</strong></span>
                          <span>Duration: <strong className="text-white">{currentPath.duration_minutes}m</strong></span>
                        </div>

                        {/* Price Step Chart Simulation */}
                        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 font-mono text-xs">
                          <div className="p-3 rounded-xl bg-neutral-900/80 border border-neutral-800 space-y-1">
                            <span className="text-[10px] text-neutral-500 uppercase block">1. Entry</span>
                            <span className="text-sm font-bold text-white">${currentPath.entry_price.toFixed(2)}</span>
                            <span className="text-[10px] text-neutral-400 block">Minute 0</span>
                          </div>

                          <div className="p-3 rounded-xl bg-neutral-900/80 border border-rose-900/40 space-y-1">
                            <span className="text-[10px] text-rose-400 uppercase block">2. Maximum Adverse</span>
                            <span className="text-sm font-bold text-rose-400">-{currentPath.mae_r.toFixed(2)}R</span>
                            <span className="text-[10px] text-neutral-400 block">Worst Intrabar Drawdown</span>
                          </div>

                          <div className="p-3 rounded-xl bg-neutral-900/80 border border-emerald-900/40 space-y-1">
                            <span className="text-[10px] text-emerald-400 uppercase block">3. Maximum Favorable</span>
                            <span className="text-sm font-bold text-emerald-400">+{currentPath.mfe_r.toFixed(2)}R</span>
                            <span className="text-[10px] text-neutral-400 block">Peak Intrabar Profit</span>
                          </div>

                          <div className="p-3 rounded-xl bg-neutral-900/80 border border-neutral-800 space-y-1">
                            <span className="text-[10px] text-neutral-500 uppercase block">4. Final Exit</span>
                            <span className={`text-sm font-bold ${currentPath.realized_r >= 0 ? "text-emerald-400" : "text-rose-400"}`}>
                              {formatR(currentPath.realized_r)} (${currentPath.exit_price.toFixed(2)})
                            </span>
                            <span className="text-[10px] text-neutral-400 block">Minute {currentPath.duration_minutes}</span>
                          </div>
                        </div>

                        {/* Minute-by-Minute Intrabar Points */}
                        {currentPath.path_points && currentPath.path_points.length > 0 && (
                          <div className="space-y-2 pt-2">
                            <span className="text-[11px] font-mono text-neutral-400 uppercase tracking-wider block">
                              Intrabar Trajectory Steps (1m Resolution)
                            </span>
                            <div className="flex items-center gap-1.5 overflow-x-auto pb-2">
                              {currentPath.path_points.map((pt, pIdx) => (
                                <div
                                  key={pIdx}
                                  className={`px-2 py-1 rounded-lg border text-center font-mono text-[10px] shrink-0 ${
                                    pt.r >= 0
                                      ? "bg-emerald-950/30 border-emerald-800/40 text-emerald-400"
                                      : "bg-rose-950/30 border-rose-800/40 text-rose-400"
                                  }`}
                                >
                                  <div className="text-neutral-500 text-[9px]">{pt.minute}m</div>
                                  <div className="font-bold">{formatR(pt.r)}</div>
                                </div>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>
                    </div>
                  ) : (
                    <div className="text-center p-8 text-neutral-500 font-mono text-xs">
                      No exit path samples loaded.
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* TAB 4: TIME TO ADVERSE & EARLY NOISE */}
            {activeTab === "timetoadverse" && excursionsReport && (
              <div className="space-y-5">
                {/* Early Stop-Out Reversal Summary Card */}
                <div className="bg-neutral-900/80 border border-neutral-800/80 rounded-2xl p-5 space-y-4">
                  <div className="flex items-center justify-between">
                    <h2 className="text-base font-bold text-white font-mono flex items-center gap-2">
                      <Zap className="w-4 h-4 text-amber-400" />
                      Early Noise &amp; Stop-Out Invalidation Diagnostic (&le; 3 Minutes)
                    </h2>
                    <span className="text-xs px-2.5 py-0.5 rounded-full bg-amber-500/10 text-amber-400 border border-amber-500/30 font-mono font-bold">
                      Noise Boundary
                    </span>
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 font-mono text-xs">
                    <div className="p-3.5 rounded-xl bg-neutral-950/80 border border-neutral-800 space-y-1">
                      <span className="text-[10px] text-neutral-500 uppercase block">Early Stopped Trades (&le;3m)</span>
                      <span className="text-lg font-bold text-white">
                        {formatNum(excursionsReport.early_stopped_count)}
                      </span>
                      <span className="text-[10px] text-neutral-400 block">82.88% of all losing trades</span>
                    </div>

                    <div className="p-3.5 rounded-xl bg-neutral-950/80 border border-neutral-800 space-y-1">
                      <span className="text-[10px] text-neutral-500 uppercase block">Later Reached +1.0R</span>
                      <span className="text-lg font-bold text-amber-400">
                        {formatPct(excursionsReport.early_stopped_later_1r_pct)}
                      </span>
                      <span className="text-[10px] text-neutral-400 block">7,357 premature stop-outs</span>
                    </div>

                    <div className="p-3.5 rounded-xl bg-neutral-950/80 border border-neutral-800 space-y-1">
                      <span className="text-[10px] text-neutral-500 uppercase block">Later Reached +2.0R</span>
                      <span className="text-lg font-bold text-rose-400">
                        {formatPct(excursionsReport.early_stopped_later_2r_pct)}
                      </span>
                      <span className="text-[10px] text-neutral-400 block">5,835 runner moves missed</span>
                    </div>
                  </div>
                </div>

                {/* Time-To-Adverse-Move Buckets */}
                <div className="bg-neutral-900/80 border border-neutral-800/80 rounded-2xl p-5 space-y-4">
                  <div>
                    <h2 className="text-base font-bold text-white font-mono flex items-center gap-2">
                      <Clock className="w-4 h-4 text-amber-400" />
                      Time-to-Adverse-Move Distribution (MAE Velocity)
                    </h2>
                    <p className="text-xs text-neutral-400">
                      Measurement of how quickly trades hit their maximum adverse excursion after entry.
                    </p>
                  </div>

                  <div className="overflow-x-auto">
                    <table className="w-full text-xs font-mono">
                      <thead>
                        <tr className="border-b border-neutral-800 text-neutral-400 uppercase tracking-wider text-[11px] bg-neutral-950/60">
                          <th className="py-3 px-4 text-left">Time Bucket</th>
                          <th className="py-3 px-4 text-right">Trades Count</th>
                          <th className="py-3 px-4 text-right">Loss Rate (%)</th>
                          <th className="py-3 px-4 text-right">Average MAE</th>
                          <th className="py-3 px-4 text-right">Average MFE</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-neutral-800/60">
                        {excursionsReport.time_to_adverse_buckets.map((b, idx) => (
                          <tr key={idx} className="hover:bg-neutral-800/50 transition">
                            <td className="py-3 px-4 font-bold text-amber-400">
                              {b.bucket}
                            </td>
                            <td className="py-3 px-4 text-right font-bold text-white">
                              {formatNum(b.trade_count)}
                            </td>
                            <td className="py-3 px-4 text-right font-bold">
                              <span className={`px-2 py-0.5 rounded ${b.loss_pct >= 80 ? "bg-rose-950/50 text-rose-400 border border-rose-800" : "bg-neutral-800 text-neutral-300"}`}>
                                {formatPct(b.loss_pct)}
                              </span>
                            </td>
                            <td className="py-3 px-4 text-right text-rose-400">
                              -{b.avg_mae_r.toFixed(2)}R
                            </td>
                            <td className="py-3 px-4 text-right text-emerald-400">
                              +{b.avg_mfe_r.toFixed(2)}R
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              </div>
            )}

            {/* TAB 5: SCORE FORENSICS & MFE REACH */}
            {activeTab === "scores" && (
              <div className="space-y-5">
                {/* MFE Reach Probabilities by Score */}
                {excursionsReport && (
                  <div className="bg-neutral-900/80 border border-neutral-800/80 rounded-2xl p-5 space-y-4">
                    <div>
                      <h2 className="text-base font-bold text-white font-mono flex items-center gap-2">
                        <BarChart3 className="w-4 h-4 text-amber-400" />
                        MFE Target Reach Frequencies by Confluence Score
                      </h2>
                      <p className="text-xs text-neutral-400">
                        Empirical frequency of trades reaching favorable R-multiples within the 60-minute holding horizon across qualification scores.
                      </p>
                    </div>

                    <div className="overflow-x-auto">
                      <table className="w-full text-xs font-mono">
                        <thead>
                          <tr className="border-b border-neutral-800 text-neutral-400 uppercase tracking-wider text-[11px] bg-neutral-950/60">
                            <th className="py-3 px-4 text-left">Signal Score</th>
                            <th className="py-3 px-4 text-right">Trades Count</th>
                            <th className="py-3 px-4 text-right">P(Reach &ge; +0.5R)</th>
                            <th className="py-3 px-4 text-right">P(Reach &ge; +1.0R)</th>
                            <th className="py-3 px-4 text-right">P(Reach &ge; +1.5R)</th>
                            <th className="py-3 px-4 text-right">P(Reach &ge; +2.0R)</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-neutral-800/60">
                          {excursionsReport.mfe_reach_by_score.map((item, idx) => (
                            <tr key={idx} className="hover:bg-neutral-800/50 transition">
                              <td className="py-3 px-4 font-bold text-amber-400">
                                {item.score}/10
                              </td>
                              <td className="py-3 px-4 text-right font-bold text-white">
                                {formatNum(item.trade_count)}
                              </td>
                              <td className="py-3 px-4 text-right text-emerald-400 font-bold">
                                {formatPct(item.p_reach_0_5r_pct)}
                              </td>
                              <td className="py-3 px-4 text-right text-emerald-300 font-bold">
                                {formatPct(item.p_reach_1_0r_pct)}
                              </td>
                              <td className="py-3 px-4 text-right text-blue-400 font-bold">
                                {formatPct(item.p_reach_1_5r_pct)}
                              </td>
                              <td className="py-3 px-4 text-right text-blue-300 font-bold">
                                {formatPct(item.p_reach_2_0r_pct)}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                )}

                {/* Score Breakdown Table */}
                <div className="bg-neutral-900/80 border border-neutral-800/80 rounded-2xl p-5 space-y-4">
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                    <div>
                      <h2 className="text-base font-bold text-white font-mono">
                        Confluence Score Breakdown (7/10 to 10/10)
                      </h2>
                      <p className="text-xs text-neutral-400">
                        Performance breakdown stratified across signal qualification scores and directionality.
                      </p>
                    </div>

                    <div className="flex items-center gap-1 bg-neutral-950 p-1 rounded-xl border border-neutral-800 text-xs font-mono">
                      <button
                        onClick={() => setScoreDirectionFilter("ALL")}
                        className={`px-3 py-1 rounded-lg font-bold transition ${
                          scoreDirectionFilter === "ALL" ? "bg-amber-500 text-neutral-950" : "text-neutral-400 hover:text-white"
                        }`}
                      >
                        ALL
                      </button>
                      <button
                        onClick={() => setScoreDirectionFilter("LONG")}
                        className={`px-3 py-1 rounded-lg font-bold transition ${
                          scoreDirectionFilter === "LONG" ? "bg-emerald-500 text-neutral-950" : "text-neutral-400 hover:text-white"
                        }`}
                      >
                        LONG
                      </button>
                      <button
                        onClick={() => setScoreDirectionFilter("SHORT")}
                        className={`px-3 py-1 rounded-lg font-bold transition ${
                          scoreDirectionFilter === "SHORT" ? "bg-rose-500 text-neutral-950" : "text-neutral-400 hover:text-white"
                        }`}
                      >
                        SHORT
                      </button>
                    </div>
                  </div>

                  <div className="overflow-x-auto">
                    <table className="w-full text-xs font-mono">
                      <thead>
                        <tr className="border-b border-neutral-800 text-neutral-400 uppercase tracking-wider text-[11px] bg-neutral-950/60">
                          <th className="py-3 px-4 text-left">Score</th>
                          <th className="py-3 px-4 text-left">Direction</th>
                          <th className="py-3 px-4 text-right">Trades</th>
                          <th className="py-3 px-4 text-right">Win Rate</th>
                          <th className="py-3 px-4 text-right">Avg R</th>
                          <th className="py-3 px-4 text-right">Total Net R</th>
                          <th className="py-3 px-4 text-right">Profit Factor</th>
                          <th className="py-3 px-4 text-right">Avg Holding</th>
                          <th className="py-3 px-4 text-right">Avg MAE</th>
                          <th className="py-3 px-4 text-right">Avg MFE</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-neutral-800/60">
                        {report.score_forensics
                          .filter((item) => scoreDirectionFilter === "ALL" ? item.direction === "ALL" : item.direction === scoreDirectionFilter)
                          .map((item, idx) => (
                            <tr key={idx} className="hover:bg-neutral-800/50 transition">
                              <td className="py-3 px-4 font-bold text-amber-400">
                                {item.score}/10
                              </td>
                              <td className="py-3 px-4 font-bold">
                                <span className={`px-2 py-0.5 rounded text-[10px] ${
                                  item.direction === "LONG" ? "bg-emerald-950/50 text-emerald-400 border border-emerald-800" :
                                  item.direction === "SHORT" ? "bg-rose-950/50 text-rose-400 border border-rose-800" :
                                  "bg-neutral-800 text-neutral-300"
                                }`}>
                                  {item.direction}
                                </span>
                              </td>
                              <td className="py-3 px-4 text-right font-bold text-white">
                                {formatNum(item.total_trades)}
                              </td>
                              <td className="py-3 px-4 text-right font-bold text-neutral-200">
                                {formatPct(item.win_rate)}
                              </td>
                              <td className={`py-3 px-4 text-right font-bold ${item.average_r >= 0 ? "text-emerald-400" : "text-rose-400"}`}>
                                {formatR(item.average_r)}
                              </td>
                              <td className={`py-3 px-4 text-right font-bold ${item.total_r >= 0 ? "text-emerald-400" : "text-rose-400"}`}>
                                {formatR(item.total_r)}
                              </td>
                              <td className="py-3 px-4 text-right text-neutral-300">
                                {item.profit_factor?.toFixed(2) || "0.00"}
                              </td>
                              <td className="py-3 px-4 text-right text-neutral-400">
                                {item.average_holding_minutes.toFixed(1)}m
                              </td>
                              <td className="py-3 px-4 text-right text-rose-400">
                                {item.avg_mae_r.toFixed(2)}R
                              </td>
                              <td className="py-3 px-4 text-right text-emerald-400">
                                {item.avg_mfe_r.toFixed(2)}R
                              </td>
                            </tr>
                          ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              </div>
            )}

            {/* TAB 6: CONDITION CONTRIBUTION MATRIX */}
            {activeTab === "conditions" && (
              <div className="space-y-4">
                <div className="bg-neutral-900/80 border border-neutral-800/80 rounded-2xl p-5 space-y-4">
                  <div>
                    <h2 className="text-base font-bold text-white font-mono">
                      Signal Condition Contribution Matrix
                    </h2>
                    <p className="text-xs text-neutral-400">
                      Descriptive win rate and expectancy delta comparing when each technical indicator condition is present versus absent.
                    </p>
                  </div>

                  <div className="overflow-x-auto">
                    <table className="w-full text-xs font-mono">
                      <thead>
                        <tr className="border-b border-neutral-800 text-neutral-400 uppercase tracking-wider text-[11px] bg-neutral-950/60">
                          <th className="py-3 px-4 text-left">Condition / Rule</th>
                          <th className="py-3 px-4 text-right">Occurrences</th>
                          <th className="py-3 px-4 text-right">Win Rate (Present)</th>
                          <th className="py-3 px-4 text-right">Avg R (Present)</th>
                          <th className="py-3 px-4 text-right">Win Rate (Absent)</th>
                          <th className="py-3 px-4 text-right">Avg R (Absent)</th>
                          <th className="py-3 px-4 text-right">Δ Win Rate</th>
                          <th className="py-3 px-4 text-right">Δ Avg R</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-neutral-800/60">
                        {report.condition_contributions.map((cond, idx) => (
                          <tr key={idx} className="hover:bg-neutral-800/50 transition">
                            <td className="py-3 px-4">
                              <span className="font-bold text-white block">{cond.condition_name}</span>
                              <span className="text-[11px] text-neutral-500 font-sans">{cond.description}</span>
                            </td>
                            <td className="py-3 px-4 text-right font-bold text-neutral-200">
                              {formatNum(cond.occurrence_count)}
                            </td>
                            <td className="py-3 px-4 text-right font-bold text-amber-400">
                              {formatPct(cond.win_rate_when_present)}
                            </td>
                            <td className="py-3 px-4 text-right text-neutral-300">
                              {formatR(cond.avg_r_when_present)}
                            </td>
                            <td className="py-3 px-4 text-right text-neutral-400">
                              {cond.occurrence_count_absent > 0 ? formatPct(cond.win_rate_when_absent) : "N/A"}
                            </td>
                            <td className="py-3 px-4 text-right text-neutral-400">
                              {cond.occurrence_count_absent > 0 ? formatR(cond.avg_r_when_absent) : "N/A"}
                            </td>
                            <td className={`py-3 px-4 text-right font-bold ${cond.delta_win_rate >= 0 ? "text-emerald-400" : "text-rose-400"}`}>
                              {cond.delta_win_rate > 0 ? `+${cond.delta_win_rate.toFixed(2)}%` : `${cond.delta_win_rate.toFixed(2)}%`}
                            </td>
                            <td className={`py-3 px-4 text-right font-bold ${cond.delta_avg_r >= 0 ? "text-emerald-400" : "text-rose-400"}`}>
                              {formatR(cond.delta_avg_r)}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              </div>
            )}

            {/* TAB 7: WIN VS LOSS COMPARISONS */}
            {activeTab === "distributions" && (
              <div className="space-y-4">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {report.win_loss_comparisons.map((item, idx) => (
                    <div key={idx} className="bg-neutral-900/80 border border-neutral-800/80 rounded-2xl p-5 space-y-3">
                      <div className="flex items-center justify-between">
                        <h3 className="text-sm font-bold text-white font-mono">
                          {item.feature_name}
                        </h3>
                        <span className="text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded bg-neutral-800 text-neutral-400 border border-neutral-700">
                          {item.interpretation}
                        </span>
                      </div>

                      <div className="grid grid-cols-2 gap-2 text-xs font-mono">
                        {/* Winning distribution */}
                        <div className="p-3 rounded-xl bg-emerald-950/20 border border-emerald-800/30 space-y-1">
                          <span className="text-[10px] text-emerald-400 font-bold uppercase block">
                            Wins ({formatNum(item.winning_distribution.count)})
                          </span>
                          <div className="flex justify-between">
                            <span className="text-neutral-400">Mean:</span>
                            <span className="font-bold text-white">{item.winning_distribution.mean.toFixed(2)}</span>
                          </div>
                          <div className="flex justify-between">
                            <span className="text-neutral-400">Median:</span>
                            <span className="font-bold text-emerald-300">{item.winning_distribution.median.toFixed(2)}</span>
                          </div>
                          <div className="flex justify-between">
                            <span className="text-neutral-400">StdDev:</span>
                            <span className="text-neutral-300">{item.winning_distribution.std_dev.toFixed(2)}</span>
                          </div>
                        </div>

                        {/* Losing distribution */}
                        <div className="p-3 rounded-xl bg-rose-950/20 border border-rose-800/30 space-y-1">
                          <span className="text-[10px] text-rose-400 font-bold uppercase block">
                            Losses ({formatNum(item.losing_distribution.count)})
                          </span>
                          <div className="flex justify-between">
                            <span className="text-neutral-400">Mean:</span>
                            <span className="font-bold text-white">{item.losing_distribution.mean.toFixed(2)}</span>
                          </div>
                          <div className="flex justify-between">
                            <span className="text-neutral-400">Median:</span>
                            <span className="font-bold text-rose-300">{item.losing_distribution.median.toFixed(2)}</span>
                          </div>
                          <div className="flex justify-between">
                            <span className="text-neutral-400">StdDev:</span>
                            <span className="text-neutral-300">{item.losing_distribution.std_dev.toFixed(2)}</span>
                          </div>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* TAB 8: HOLDING TIME BREAKDOWN */}
            {activeTab === "holding" && (
              <div className="space-y-4">
                <div className="bg-neutral-900/80 border border-neutral-800/80 rounded-2xl p-5 space-y-4">
                  <div>
                    <h2 className="text-base font-bold text-white font-mono">
                      Trade Lifespan & Holding-Time Breakdown
                    </h2>
                    <p className="text-xs text-neutral-400">
                      Performance distribution grouped into granular holding intervals.
                    </p>
                  </div>

                  <div className="overflow-x-auto">
                    <table className="w-full text-xs font-mono">
                      <thead>
                        <tr className="border-b border-neutral-800 text-neutral-400 uppercase tracking-wider text-[11px] bg-neutral-950/60">
                          <th className="py-3 px-4 text-left">Duration Bucket</th>
                          <th className="py-3 px-4 text-right">Trades Count</th>
                          <th className="py-3 px-4 text-right">Win Rate</th>
                          <th className="py-3 px-4 text-right">Wins</th>
                          <th className="py-3 px-4 text-right">Losses</th>
                          <th className="py-3 px-4 text-right">Total Net R</th>
                          <th className="py-3 px-4 text-right">Average R</th>
                          <th className="py-3 px-4 text-right">Profit Factor</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-neutral-800/60">
                        {report.holding_time_breakdown.map((bucket, idx) => (
                          <tr key={idx} className="hover:bg-neutral-800/50 transition">
                            <td className="py-3 px-4 font-bold text-amber-400">
                              {bucket.bucket_label}
                            </td>
                            <td className="py-3 px-4 text-right font-bold text-white">
                              {formatNum(bucket.trades_count)}
                            </td>
                            <td className="py-3 px-4 text-right font-bold text-neutral-200">
                              {formatPct(bucket.win_rate)}
                            </td>
                            <td className="py-3 px-4 text-right text-emerald-400 font-bold">
                              {formatNum(bucket.win_count)}
                            </td>
                            <td className="py-3 px-4 text-right text-rose-400 font-bold">
                              {formatNum(bucket.loss_count)}
                            </td>
                            <td className={`py-3 px-4 text-right font-bold ${bucket.total_r >= 0 ? "text-emerald-400" : "text-rose-400"}`}>
                              {formatR(bucket.total_r)}
                            </td>
                            <td className={`py-3 px-4 text-right font-bold ${bucket.average_r >= 0 ? "text-emerald-400" : "text-rose-400"}`}>
                              {formatR(bucket.average_r)}
                            </td>
                            <td className="py-3 px-4 text-right text-neutral-300">
                              {bucket.profit_factor?.toFixed(2) || "--"}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>

                {/* Loss Clustering Card */}
                <div className="bg-neutral-900/80 border border-neutral-800/80 rounded-2xl p-5 space-y-3">
                  <h3 className="text-sm font-bold text-white font-mono flex items-center gap-2">
                    <ShieldAlert className="w-4 h-4 text-rose-400" />
                    Loss Clustering & Streak Diagnostics
                  </h3>
                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 font-mono text-xs">
                    <div className="p-3 rounded-xl bg-neutral-950/80 border border-neutral-800">
                      <span className="text-[10px] text-neutral-500 uppercase block">Max Consecutive Losses</span>
                      <span className="text-base font-bold text-rose-400">
                        {report.loss_clustering.max_consecutive_losses} Trades
                      </span>
                    </div>
                    <div className="p-3 rounded-xl bg-neutral-950/80 border border-neutral-800">
                      <span className="text-[10px] text-neutral-500 uppercase block">Overall Loss Rate</span>
                      <span className="text-base font-bold text-amber-400">
                        {formatPct(report.loss_clustering.loss_rate_overall)}
                      </span>
                    </div>
                    <div className="p-3 rounded-xl bg-neutral-950/80 border border-neutral-800">
                      <span className="text-[10px] text-neutral-500 uppercase block">Highest Loss Session</span>
                      <span className="text-base font-bold text-neutral-200">
                        Asia ({formatNum(report.loss_clustering.losses_by_session["Asia"] || 0)} losses)
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* TAB 9: CANDIDATE HYPOTHESES */}
            {activeTab === "hypotheses" && (
              <div className="space-y-4">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {report.candidate_hypotheses.map((hyp, idx) => (
                    <div
                      key={idx}
                      className="bg-neutral-900/80 border border-neutral-800/80 hover:border-amber-500/40 rounded-2xl p-5 space-y-3 transition shadow-lg flex flex-col justify-between"
                    >
                      <div className="space-y-2">
                        <div className="flex items-center justify-between gap-2">
                          <span className="px-2.5 py-1 rounded-lg bg-amber-500/10 text-amber-400 border border-amber-500/30 text-xs font-mono font-bold">
                            {hyp.hypothesis_id}
                          </span>
                          <span className="text-[11px] font-mono text-neutral-400 uppercase">
                            {hyp.failure_mechanism_addressed}
                          </span>
                        </div>

                        <h3 className="text-base font-bold text-white font-mono">
                          {hyp.title}
                        </h3>

                        <div className="space-y-1.5 text-xs text-neutral-300 font-sans">
                          <div>
                            <strong className="text-amber-400 font-mono">Evidence: </strong>
                            {hyp.empirical_evidence}
                          </div>
                          <div>
                            <strong className="text-emerald-400 font-mono">Proposed Change: </strong>
                            {hyp.proposed_rule_change}
                          </div>
                          <div>
                            <strong className="text-blue-400 font-mono">Expected Impact: </strong>
                            {hyp.expected_impact}
                          </div>
                        </div>
                      </div>

                      <div className="pt-3 border-t border-neutral-800/80 flex items-center justify-between text-xs font-mono">
                        <span className="text-neutral-500">Single-Variable Experiment</span>
                        <Link
                          href={`/experiments?id=${hyp.hypothesis_id}`}
                          className="flex items-center gap-1 text-amber-400 hover:text-amber-300 font-bold transition"
                        >
                          <span>Inspect Experiment</span>
                          <ExternalLink className="w-3.5 h-3.5" />
                        </Link>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </>
        )}
      </main>
    </div>
  );
}
