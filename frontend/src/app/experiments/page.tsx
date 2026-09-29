"use client";

import React, { useState, useEffect, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { Header } from "@/components/market/Header";
import { fetchExperimentsList, runExperiments, fetchExperimentAudit, triggerExperimentAudit } from "@/lib/api";
import {
  ConnectionState,
  ExperimentAuditReport,
  ExperimentResult,
  WsStatusData,
} from "@/types/market";
import {
  Activity,
  AlertCircle,
  AlertOctagon,
  AlertTriangle,
  ArrowDownRight,
  ArrowRight,
  ArrowUpRight,
  BarChart3,
  CheckCircle2,
  Clock,
  Database,
  ExternalLink,
  Filter,
  Flame,
  FlaskConical,
  Hash,
  HelpCircle,
  History,
  Layers,
  Lock,
  Microscope,
  Percent,
  Play,
  RefreshCw,
  Scale,
  SearchCode,
  ShieldAlert,
  ShieldCheck,
  Sparkles,
  TrendingDown,
  TrendingUp,
  Workflow,
  Zap,
} from "lucide-react";
import Link from "next/link";

function ExperimentsContent() {
  const searchParams = useSearchParams();
  const initialId = searchParams.get("id");

  const [connectionState] = useState<ConnectionState>("CONNECTED");
  const [mt5Status] = useState<WsStatusData>({
    mt5_connected: true,
    symbol: "XAUUSD",
    is_mock: false,
    message: "Connected to Exness MT5 stream",
  });
  const [lastMessageTime] = useState<number>(Date.now());

  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isRunning, setIsRunning] = useState<boolean>(false);
  const [isAuditing, setIsAuditing] = useState<boolean>(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [experiments, setExperiments] = useState<ExperimentResult[]>([]);
  const [selectedExpId, setSelectedExpId] = useState<string | null>(initialId || "EXP-001");
  const [auditReport, setAuditReport] = useState<ExperimentAuditReport | null>(null);
  const [activeTab, setActiveTab] = useState<"overview" | "audit" | "walkforward" | "robustness">("overview");

  const loadData = async () => {
    setIsLoading(true);
    setErrorMsg(null);
    try {
      const res = await fetchExperimentsList();
      if (res.success && res.experiments) {
        setExperiments(res.experiments);
        const currentId = selectedExpId || (res.experiments.length > 0 ? res.experiments[0].experiment_id : "EXP-001");
        setSelectedExpId(currentId);
        loadAudit(currentId);
      } else {
        setErrorMsg("Failed to load experiments from backend.");
      }
    } catch (err: any) {
      setErrorMsg(err.message || "Failed to load experiments.");
    } finally {
      setIsLoading(false);
    }
  };

  const loadAudit = async (expId: string) => {
    try {
      const res = await fetchExperimentAudit(expId);
      if (res.success && res.audit) {
        setAuditReport(res.audit);
      }
    } catch (err) {
      // Audit may not have run yet, which is normal
      setAuditReport(null);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  useEffect(() => {
    if (initialId) {
      setSelectedExpId(initialId);
      loadAudit(initialId);
    }
  }, [initialId]);

  const handleSelectExp = (id: string) => {
    setSelectedExpId(id);
    loadAudit(id);
  };

  const handleRunAll = async () => {
    setIsRunning(true);
    setErrorMsg(null);
    try {
      const res = await runExperiments();
      if (res.success && res.results) {
        setExperiments(res.results);
        if (selectedExpId) {
          loadAudit(selectedExpId);
        }
      }
    } catch (err: any) {
      setErrorMsg(err.message || "Failed to execute experiments runner.");
    } finally {
      setIsRunning(false);
    }
  };

  const handleTriggerAudit = async () => {
    if (!selectedExpId) return;
    setIsAuditing(true);
    setErrorMsg(null);
    try {
      const res = await triggerExperimentAudit(selectedExpId);
      if (res.success && res.audit) {
        setAuditReport(res.audit);
        setActiveTab("audit");
      }
    } catch (err: any) {
      setErrorMsg(err.message || `Failed to audit experiment ${selectedExpId}.`);
    } finally {
      setIsAuditing(false);
    }
  };

  const selectedExp = experiments.find((e) => e.experiment_id === selectedExpId) || experiments[0];

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

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "PROMISING":
        return <span className="px-2.5 py-0.5 rounded-full text-xs font-mono font-bold bg-emerald-950/60 text-emerald-400 border border-emerald-700/60">PROMISING</span>;
      case "NEEDS_MORE_DATA":
        return <span className="px-2.5 py-0.5 rounded-full text-xs font-mono font-bold bg-amber-950/60 text-amber-400 border border-amber-700/60">NEEDS MORE DATA</span>;
      case "REJECTED":
        return <span className="px-2.5 py-0.5 rounded-full text-xs font-mono font-bold bg-rose-950/60 text-rose-400 border border-rose-800/60">REJECTED</span>;
      case "FINAL_OOS_PENDING":
        return <span className="px-2.5 py-0.5 rounded-full text-xs font-mono font-bold bg-blue-950/60 text-blue-400 border border-blue-700/60">FINAL OOS PENDING</span>;
      default:
        return <span className="px-2.5 py-0.5 rounded-full text-xs font-mono font-bold bg-neutral-800 text-neutral-300 border border-neutral-700">{status}</span>;
    }
  };

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
        {/* Header Title Banner */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-gradient-to-r from-neutral-900 via-neutral-900/90 to-neutral-900 border border-neutral-800/80 p-5 rounded-2xl shadow-xl">
          <div className="space-y-1">
            <div className="flex items-center gap-2.5">
              <div className="p-2 rounded-xl bg-amber-500/10 text-amber-400 border border-amber-500/30">
                <FlaskConical className="w-6 h-6" />
              </div>
              <div>
                <h1 className="text-2xl font-black text-white tracking-tight flex items-center gap-2 font-mono">
                  Controlled Strategy Experiments & Validation Audit
                  <span className="text-xs px-2.5 py-0.5 rounded-full bg-neutral-800 text-amber-400 border border-amber-500/30 font-sans font-semibold">
                    Phase 6B
                  </span>
                </h1>
                <p className="text-xs text-neutral-400">
                  Single-variable hypothesis testing, independent trade reconciliation, timing verification, and walk-forward validation against frozen baseline (<code>phase6-baseline-v1</code>).
                </p>
              </div>
            </div>
          </div>

          <div className="flex items-center gap-3 self-end md:self-auto font-mono text-xs">
            <button
              onClick={handleTriggerAudit}
              disabled={isAuditing || !selectedExpId}
              className="flex items-center gap-1.5 px-3 py-2 bg-neutral-800 hover:bg-neutral-700 active:bg-neutral-600 disabled:opacity-50 text-amber-400 font-bold rounded-xl transition border border-amber-500/30 shadow-sm"
            >
              <SearchCode className={`w-3.5 h-3.5 ${isAuditing ? "animate-spin text-amber-400" : ""}`} />
              <span>{isAuditing ? "Auditing..." : "Audit Candidate"}</span>
            </button>
            <button
              onClick={handleRunAll}
              disabled={isRunning}
              className="flex items-center gap-1.5 px-3 py-2 bg-amber-500 hover:bg-amber-400 active:bg-amber-600 disabled:opacity-50 text-neutral-950 font-bold rounded-xl transition shadow-lg shadow-amber-500/10 cursor-pointer"
            >
              <Play className={`w-3.5 h-3.5 ${isRunning ? "animate-spin text-neutral-950" : ""}`} />
              <span>{isRunning ? "Running Suite..." : "Re-Execute Suite"}</span>
            </button>
            <button
              onClick={loadData}
              disabled={isLoading}
              className="flex items-center gap-1.5 px-3 py-2 bg-neutral-800 hover:bg-neutral-700 active:bg-neutral-600 disabled:opacity-50 text-neutral-200 rounded-xl transition border border-neutral-700 shadow-sm"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? "animate-spin text-amber-400" : ""}`} />
              <span>Refresh</span>
            </button>
          </div>
        </div>

        {/* Frozen Baseline Status Callout */}
        <div className="bg-neutral-900/60 border border-neutral-800 p-4 rounded-2xl flex flex-wrap items-center justify-between gap-4 font-mono text-xs">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-xl bg-amber-500/10 text-amber-400 border border-amber-500/20">
              <Lock className="w-4 h-4" />
            </div>
            <div>
              <span className="text-neutral-400 text-[11px] block">Immutable Frozen Baseline:</span>
              <span className="font-bold text-white text-sm">phase6-baseline-v1</span>
            </div>
          </div>
          <div className="flex items-center gap-6 text-[11px] text-neutral-400">
            <div>Threshold: <span className="text-white font-bold">&gt;= 7/10</span></div>
            <div>SL: <span className="text-white font-bold">1.0 ATR</span></div>
            <div>TP1 / TP2: <span className="text-white font-bold">1.0 / 2.0 ATR</span></div>
            <div>Max Holding: <span className="text-white font-bold">60 min</span></div>
            <div>Spread: <span className="text-white font-bold">$0.30</span></div>
            <div>Policy: <span className="text-amber-400 font-bold">stop_first</span></div>
            <div>Concurrency: <span className="text-white font-bold">1 trade</span></div>
          </div>
        </div>

        {/* Loading / Error Messages */}
        {isLoading && experiments.length === 0 && (
          <div className="flex flex-col items-center justify-center p-16 space-y-4 bg-neutral-900/40 border border-neutral-800/60 rounded-2xl">
            <RefreshCw className="w-8 h-8 text-amber-400 animate-spin" />
            <p className="text-sm font-mono text-neutral-400">Loading experiment matrix and walk-forward verification data...</p>
          </div>
        )}

        {errorMsg && (
          <div className="p-4 bg-rose-950/30 border border-rose-800/60 rounded-2xl text-rose-300 flex items-center gap-3 font-mono text-xs">
            <AlertOctagon className="w-5 h-5 text-rose-400 shrink-0" />
            <p>{errorMsg}</p>
          </div>
        )}

        {/* Main 2-Column Layout */}
        {experiments.length > 0 && (
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
            {/* Left Column: Experiment Selector List (4 cols) */}
            <div className="lg:col-span-4 space-y-3">
              <div className="flex items-center justify-between bg-neutral-900/80 p-3 rounded-xl border border-neutral-800">
                <span className="text-xs font-bold font-mono text-neutral-300 uppercase">
                  Experiments Registry ({experiments.length})
                </span>
                <span className="text-[10px] font-mono text-neutral-500">Single-Variable Isolation</span>
              </div>

              <div className="space-y-2">
                {experiments.map((exp) => (
                  <button
                    key={exp.experiment_id}
                    onClick={() => handleSelectExp(exp.experiment_id)}
                    className={`w-full text-left p-4 rounded-2xl border transition flex flex-col justify-between gap-2.5 ${
                      selectedExp?.experiment_id === exp.experiment_id
                        ? "bg-neutral-900 border-amber-500/80 shadow-lg shadow-amber-500/5 ring-1 ring-amber-500/30"
                        : "bg-neutral-900/50 border-neutral-800/80 hover:bg-neutral-900 hover:border-neutral-700"
                    }`}
                  >
                    <div className="flex items-center justify-between w-full">
                      <span className="text-xs font-mono font-bold text-amber-400">
                        {exp.experiment_id}
                      </span>
                      {getStatusBadge(exp.status)}
                    </div>

                    <div>
                      <h4 className="text-sm font-bold text-white font-mono leading-tight">
                        {exp.title}
                      </h4>
                      <p className="text-xs text-neutral-400 line-clamp-2 mt-1 font-sans">
                        {exp.hypothesis}
                      </p>
                    </div>

                    <div className="pt-2 border-t border-neutral-800/60 flex items-center justify-between text-[11px] font-mono text-neutral-400 w-full">
                      <span>Δ Net R (OOS):</span>
                      <span className={`font-bold ${exp.preliminary_oos_deltas?.delta_total_r >= 0 ? "text-emerald-400" : "text-rose-400"}`}>
                        {formatR(exp.preliminary_oos_deltas?.delta_total_r)}
                      </span>
                    </div>
                  </button>
                ))}
              </div>
            </div>

            {/* Right Column: Deep Dive & Audit Details (8 cols) */}
            {selectedExp && (
              <div className="lg:col-span-8 space-y-5">
                {/* Header Card */}
                <div className="bg-neutral-900/80 border border-neutral-800/80 p-5 rounded-2xl space-y-4 shadow-xl">
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                    <div className="flex items-center gap-2.5">
                      <span className="px-3 py-1 rounded-xl bg-amber-500/10 text-amber-400 border border-amber-500/30 text-sm font-mono font-bold">
                        {selectedExp.experiment_id}
                      </span>
                      <h2 className="text-lg font-bold text-white font-mono">
                        {selectedExp.title}
                      </h2>
                    </div>
                    <div>{getStatusBadge(selectedExp.status)}</div>
                  </div>

                  {/* Hypothesis & Decision Rationale */}
                  <div className="space-y-2 bg-neutral-950/70 p-4 rounded-xl border border-neutral-800/80 text-xs">
                    <div>
                      <span className="text-amber-400 font-mono font-bold uppercase block text-[10px]">
                        Controlled Hypothesis:
                      </span>
                      <p className="text-neutral-200 font-sans mt-0.5 leading-relaxed">
                        {selectedExp.hypothesis}
                      </p>
                    </div>

                    <div className="pt-2 border-t border-neutral-800/60">
                      <span className="text-neutral-400 font-mono font-bold uppercase block text-[10px]">
                        Decision Rationale:
                      </span>
                      <p className="text-neutral-300 font-sans mt-0.5">
                        {selectedExp.decision_rationale || "Evaluated against strict multi-window acceptance criteria."}
                      </p>
                    </div>
                  </div>

                  {/* Metadata Chips */}
                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 font-mono text-[11px] text-neutral-400">
                    <div className="bg-neutral-950 p-2.5 rounded-lg border border-neutral-800/60">
                      <span className="text-neutral-500 block text-[9px] uppercase">Config Hash</span>
                      <span className="text-neutral-300 font-bold">{selectedExp.configuration_hash.slice(0, 12)}</span>
                    </div>
                    <div className="bg-neutral-950 p-2.5 rounded-lg border border-neutral-800/60">
                      <span className="text-neutral-500 block text-[9px] uppercase">Dataset Hash</span>
                      <span className="text-amber-400 font-bold">{selectedExp.dataset_hash.slice(0, 12)}</span>
                    </div>
                    <div className="bg-neutral-950 p-2.5 rounded-lg border border-neutral-800/60">
                      <span className="text-neutral-500 block text-[9px] uppercase">Baseline Ref</span>
                      <span className="text-white font-bold">{selectedExp.baseline_version}</span>
                    </div>
                  </div>
                </div>

                {/* Sub-Tabs for Deep-Dive */}
                <div className="flex items-center gap-1 border-b border-neutral-800 pb-2 text-xs font-mono">
                  <button
                    onClick={() => setActiveTab("overview")}
                    className={`px-3.5 py-2 rounded-xl font-bold transition ${
                      activeTab === "overview" ? "bg-amber-500 text-neutral-950 shadow-md" : "text-neutral-400 hover:text-white bg-neutral-900/60"
                    }`}
                  >
                    Overview & Development
                  </button>
                  <button
                    onClick={() => setActiveTab("audit")}
                    className={`px-3.5 py-2 rounded-xl font-bold transition flex items-center gap-1.5 ${
                      activeTab === "audit" ? "bg-amber-500 text-neutral-950 shadow-md" : "text-neutral-400 hover:text-white bg-neutral-900/60"
                    }`}
                  >
                    <SearchCode className="w-3.5 h-3.5" />
                    <span>Independent Audit Verification</span>
                  </button>
                  <button
                    onClick={() => setActiveTab("walkforward")}
                    className={`px-3.5 py-2 rounded-xl font-bold transition ${
                      activeTab === "walkforward" ? "bg-amber-500 text-neutral-950 shadow-md" : "text-neutral-400 hover:text-white bg-neutral-900/60"
                    }`}
                  >
                    Walk-Forward OOS Matrix (9 Windows)
                  </button>
                  <button
                    onClick={() => setActiveTab("robustness")}
                    className={`px-3.5 py-2 rounded-xl font-bold transition ${
                      activeTab === "robustness" ? "bg-amber-500 text-neutral-950 shadow-md" : "text-neutral-400 hover:text-white bg-neutral-900/60"
                    }`}
                  >
                    Spread Robustness ($0.20-$0.50)
                  </button>
                </div>

                {/* TAB 1: OVERVIEW & DEVELOPMENT */}
                {activeTab === "overview" && (
                  <div className="space-y-4">
                    <div className="bg-neutral-900/80 border border-neutral-800/80 p-5 rounded-2xl space-y-4">
                      <div className="flex items-center justify-between">
                        <div>
                          <h3 className="text-base font-bold text-white font-mono">
                            Development Period (90 Days In-Sample)
                          </h3>
                          <p className="text-xs text-neutral-400">{selectedExp.development_period_label}</p>
                        </div>
                        <span className="text-xs font-mono text-neutral-400">
                          Trades Delta: <strong className="text-white">{selectedExp.development_deltas.delta_trades}</strong> ({selectedExp.development_deltas.trade_reduction_pct.toFixed(1)}% reduction)
                        </span>
                      </div>

                      <div className="overflow-x-auto">
                        <table className="w-full text-xs font-mono">
                          <thead>
                            <tr className="border-b border-neutral-800 text-neutral-400 uppercase tracking-wider text-[10px] bg-neutral-950/60">
                              <th className="py-2.5 px-3 text-left">Metric</th>
                              <th className="py-2.5 px-3 text-right">Frozen Baseline</th>
                              <th className="py-2.5 px-3 text-right">Experiment ({selectedExp.experiment_id})</th>
                              <th className="py-2.5 px-3 text-right">Delta (Δ)</th>
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-neutral-800/60">
                            <tr>
                              <td className="py-2.5 px-3 font-semibold text-neutral-300">Total Trades</td>
                              <td className="py-2.5 px-3 text-right text-white font-bold">{formatNum(selectedExp.development_baseline.trades_count)}</td>
                              <td className="py-2.5 px-3 text-right text-amber-400 font-bold">{formatNum(selectedExp.development_experiment.trades_count)}</td>
                              <td className="py-2.5 px-3 text-right text-neutral-400">{selectedExp.development_deltas.delta_trades}</td>
                            </tr>
                            <tr>
                              <td className="py-2.5 px-3 font-semibold text-neutral-300">Win Rate</td>
                              <td className="py-2.5 px-3 text-right text-neutral-200">{formatPct(selectedExp.development_baseline.win_rate)}</td>
                              <td className="py-2.5 px-3 text-right text-neutral-200">{formatPct(selectedExp.development_experiment.win_rate)}</td>
                              <td className={`py-2.5 px-3 text-right font-bold ${selectedExp.development_deltas.delta_win_rate_pct >= 0 ? "text-emerald-400" : "text-rose-400"}`}>
                                {selectedExp.development_deltas.delta_win_rate_pct > 0 ? `+${selectedExp.development_deltas.delta_win_rate_pct.toFixed(2)}%` : `${selectedExp.development_deltas.delta_win_rate_pct.toFixed(2)}%`}
                              </td>
                            </tr>
                            <tr>
                              <td className="py-2.5 px-3 font-semibold text-neutral-300">Average R (Expectancy)</td>
                              <td className="py-2.5 px-3 text-right text-rose-400">{formatR(selectedExp.development_baseline.average_r)}</td>
                              <td className="py-2.5 px-3 text-right text-rose-400">{formatR(selectedExp.development_experiment.average_r)}</td>
                              <td className={`py-2.5 px-3 text-right font-bold ${selectedExp.development_deltas.delta_average_r >= 0 ? "text-emerald-400" : "text-rose-400"}`}>
                                {formatR(selectedExp.development_deltas.delta_average_r)}
                              </td>
                            </tr>
                            <tr>
                              <td className="py-2.5 px-3 font-semibold text-neutral-300">Total Net R</td>
                              <td className="py-2.5 px-3 text-right text-rose-400 font-bold">{formatR(selectedExp.development_baseline.total_r)}</td>
                              <td className="py-2.5 px-3 text-right text-rose-400 font-bold">{formatR(selectedExp.development_experiment.total_r)}</td>
                              <td className={`py-2.5 px-3 text-right font-bold ${selectedExp.development_deltas.delta_total_r >= 0 ? "text-emerald-400" : "text-rose-400"}`}>
                                {formatR(selectedExp.development_deltas.delta_total_r)}
                              </td>
                            </tr>
                            <tr>
                              <td className="py-2.5 px-3 font-semibold text-neutral-300">Profit Factor</td>
                              <td className="py-2.5 px-3 text-right text-neutral-300">{selectedExp.development_baseline.profit_factor?.toFixed(2) || "0.00"}</td>
                              <td className="py-2.5 px-3 text-right text-neutral-300">{selectedExp.development_experiment.profit_factor?.toFixed(2) || "0.00"}</td>
                              <td className={`py-2.5 px-3 text-right font-bold ${selectedExp.development_deltas.delta_profit_factor >= 0 ? "text-emerald-400" : "text-rose-400"}`}>
                                {selectedExp.development_deltas.delta_profit_factor > 0 ? `+${selectedExp.development_deltas.delta_profit_factor.toFixed(2)}` : selectedExp.development_deltas.delta_profit_factor.toFixed(2)}
                              </td>
                            </tr>
                            <tr>
                              <td className="py-2.5 px-3 font-semibold text-neutral-300">Max Drawdown ($ / %)</td>
                              <td className="py-2.5 px-3 text-right text-rose-400">
                                ${formatNum(selectedExp.development_baseline.max_drawdown_usd)} ({formatPct(selectedExp.development_baseline.max_drawdown_pct)})
                              </td>
                              <td className="py-2.5 px-3 text-right text-rose-400">
                                ${formatNum(selectedExp.development_experiment.max_drawdown_usd)} ({formatPct(selectedExp.development_experiment.max_drawdown_pct)})
                              </td>
                              <td className="py-2.5 px-3 text-right text-emerald-400 font-bold">
                                -${formatNum(Math.abs(selectedExp.development_deltas.delta_max_drawdown_usd))}
                              </td>
                            </tr>
                          </tbody>
                        </table>
                      </div>
                    </div>
                  </div>
                )}

                {/* TAB 2: AUDIT PANEL */}
                {activeTab === "audit" && (
                  <div className="space-y-4">
                    {auditReport ? (
                      <div className="space-y-4">
                        {/* Audit Summary & Attribution Banner */}
                        <div className="bg-neutral-900/90 border border-neutral-800 p-5 rounded-2xl space-y-3">
                          <div className="flex items-center justify-between">
                            <h3 className="text-base font-bold text-white font-mono flex items-center gap-2">
                              <ShieldCheck className="w-5 h-5 text-amber-400" />
                              Phase 6A Independent Audit Verification
                            </h3>
                            <span className="text-[11px] font-mono text-neutral-400">
                              Audited at {new Date(auditReport.audit_timestamp_iso).toLocaleTimeString()}
                            </span>
                          </div>

                          <div className="bg-neutral-950 p-3 rounded-xl border border-neutral-800 text-xs font-mono">
                            <span className="text-amber-400 font-bold uppercase block text-[10px]">
                              Delta Attribution Analysis:
                            </span>
                            <p className="text-neutral-200 mt-1 font-sans">
                              {auditReport.attribution}
                            </p>
                          </div>

                          {/* 6 Audit Verification Checks */}
                          <div className="grid grid-cols-1 md:grid-cols-2 gap-2.5 pt-2">
                            {auditReport.checks.map((chk, idx) => (
                              <div
                                key={idx}
                                className="bg-neutral-950/80 p-3 rounded-xl border border-neutral-800/80 flex items-start gap-2.5 font-mono text-xs"
                              >
                                {chk.status_label === "PASS" ? (
                                  <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
                                ) : chk.status_label === "WARN" ? (
                                  <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
                                ) : (
                                  <AlertOctagon className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
                                )}
                                <div className="space-y-0.5">
                                  <div className="flex items-center gap-2">
                                    <span className="font-bold text-white">{chk.name}</span>
                                    <span className={`px-1.5 py-0.2 rounded text-[9px] font-bold ${
                                      chk.status_label === "PASS" ? "bg-emerald-950 text-emerald-400 border border-emerald-800" :
                                      chk.status_label === "WARN" ? "bg-amber-950 text-amber-400 border border-amber-800" :
                                      "bg-rose-950 text-rose-400 border border-rose-800"
                                    }`}>
                                      {chk.status_label}
                                    </span>
                                  </div>
                                  <p className="text-[11px] text-neutral-400 font-sans leading-tight">
                                    {chk.evidence}
                                  </p>
                                </div>
                              </div>
                            ))}
                          </div>
                        </div>

                        {/* Trade Reconciliation Card */}
                        <div className="bg-neutral-900/80 border border-neutral-800 p-5 rounded-2xl space-y-3">
                          <h4 className="text-sm font-bold text-white font-mono">
                            Trade Set Reconstruction & Signal Concurrency Breakdown
                          </h4>
                          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 font-mono text-xs text-center">
                            <div className="p-3 rounded-xl bg-neutral-950 border border-neutral-800">
                              <span className="text-[10px] text-neutral-500 uppercase block">Total Signals</span>
                              <span className="text-base font-bold text-white">{formatNum(auditReport.trade_reconciliation.baseline_total_signals)}</span>
                            </div>
                            <div className="p-3 rounded-xl bg-neutral-950 border border-neutral-800">
                              <span className="text-[10px] text-neutral-500 uppercase block">Concurrency Ignored</span>
                              <span className="text-base font-bold text-amber-400">{formatNum(auditReport.trade_reconciliation.baseline_ignored_signals)}</span>
                            </div>
                            <div className="p-3 rounded-xl bg-neutral-950 border border-neutral-800">
                              <span className="text-[10px] text-neutral-500 uppercase block">Removed Entries</span>
                              <span className="text-base font-bold text-rose-400">{formatNum(auditReport.trade_reconciliation.removed_trades_count)}</span>
                            </div>
                            <div className="p-3 rounded-xl bg-neutral-950 border border-neutral-800">
                              <span className="text-[10px] text-neutral-500 uppercase block">Changed Exits</span>
                              <span className="text-base font-bold text-blue-400">{formatNum(auditReport.trade_reconciliation.changed_exit_trades_count)}</span>
                            </div>
                          </div>
                        </div>
                      </div>
                    ) : (
                      <div className="p-12 text-center bg-neutral-900/40 border border-neutral-800 rounded-2xl space-y-3">
                        <SearchCode className="w-8 h-8 text-neutral-500 mx-auto" />
                        <p className="text-sm font-mono text-neutral-400">Click &ldquo;Audit Candidate&rdquo; to execute a full independent reconstruction.</p>
                      </div>
                    )}
                  </div>
                )}

                {/* TAB 3: WALK-FORWARD OOS */}
                {activeTab === "walkforward" && (
                  <div className="bg-neutral-900/80 border border-neutral-800/80 p-5 rounded-2xl space-y-4">
                    <div className="flex items-center justify-between">
                      <div>
                        <h3 className="text-base font-bold text-white font-mono">
                          Walk-Forward Out-of-Sample Matrix (Windows #1 to #9)
                        </h3>
                        <p className="text-xs text-neutral-400">
                          8 preliminary OOS windows evaluated. Final Window #9 remains locked until screening passes.
                        </p>
                      </div>
                    </div>

                    <div className="overflow-x-auto">
                      <table className="w-full text-xs font-mono">
                        <thead>
                          <tr className="border-b border-neutral-800 text-neutral-400 uppercase tracking-wider text-[10px] bg-neutral-950/60">
                            <th className="py-2.5 px-3 text-left">Window</th>
                            <th className="py-2.5 px-3 text-left">OOS Period</th>
                            <th className="py-2.5 px-3 text-right">Baseline Trades</th>
                            <th className="py-2.5 px-3 text-right">Baseline R</th>
                            <th className="py-2.5 px-3 text-right">Exp Trades</th>
                            <th className="py-2.5 px-3 text-right">Exp R</th>
                            <th className="py-2.5 px-3 text-right">Δ R</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-neutral-800/60">
                          {selectedExp.walk_forward_windows.map((w, idx) => (
                            <tr key={idx} className={`hover:bg-neutral-800/40 transition ${w.is_final_oos ? "bg-amber-950/20" : ""}`}>
                              <td className="py-2.5 px-3 font-bold text-amber-400">
                                Window #{w.window_index}
                                {w.is_final_oos && (
                                  <span className="ml-1.5 px-1.5 py-0.5 rounded bg-amber-500/20 text-amber-300 text-[9px] border border-amber-500/30">
                                    FINAL OOS LOCKED
                                  </span>
                                )}
                              </td>
                              <td className="py-2.5 px-3 text-neutral-400 text-[11px]">
                                {w.val_start_iso.slice(0, 10)} to {w.val_end_iso.slice(0, 10)}
                              </td>
                              <td className="py-2.5 px-3 text-right text-neutral-300">
                                {formatNum(w.baseline_trades)}
                              </td>
                              <td className="py-2.5 px-3 text-right text-rose-400 font-bold">
                                {formatR(w.baseline_net_r)}
                              </td>
                              <td className="py-2.5 px-3 text-right text-neutral-200 font-bold">
                                {w.is_final_oos ? "--" : formatNum(w.experiment_trades)}
                              </td>
                              <td className={`py-2.5 px-3 text-right font-bold ${w.is_final_oos ? "text-neutral-500" : (w.experiment_net_r || 0) >= 0 ? "text-emerald-400" : "text-rose-400"}`}>
                                {w.is_final_oos ? "LOCKED" : formatR(w.experiment_net_r)}
                              </td>
                              <td className={`py-2.5 px-3 text-right font-bold ${w.is_final_oos ? "text-neutral-500" : w.delta_r >= 0 ? "text-emerald-400" : "text-rose-400"}`}>
                                {w.is_final_oos ? "--" : formatR(w.delta_r)}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                )}

                {/* TAB 4: SPREAD ROBUSTNESS */}
                {activeTab === "robustness" && (
                  <div className="bg-neutral-900/80 border border-neutral-800/80 p-5 rounded-2xl space-y-4">
                    <h3 className="text-base font-bold text-white font-mono flex items-center gap-2">
                      <Scale className="w-4 h-4 text-amber-400" />
                      Spread Perturbation & Robustness Check ($0.20, $0.30, $0.50)
                    </h3>

                    <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                      {selectedExp.spread_robustness.map((s, idx) => (
                        <div key={idx} className="bg-neutral-950 p-3.5 rounded-xl border border-neutral-800/80 space-y-1.5 font-mono text-xs">
                          <div className="flex justify-between items-center">
                            <span className="font-bold text-white">${s.spread.toFixed(2)} Spread</span>
                            <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${s.is_resilient ? "bg-emerald-950/40 text-emerald-400 border border-emerald-800" : "bg-rose-950/40 text-rose-400 border border-rose-800"}`}>
                              {s.is_resilient ? "RESILIENT" : "SENSITIVE"}
                            </span>
                          </div>
                          <div className="flex justify-between text-[11px]">
                            <span className="text-neutral-500">Baseline R:</span>
                            <span className="text-rose-400">{formatR(s.baseline_total_r)}</span>
                          </div>
                          <div className="flex justify-between text-[11px]">
                            <span className="text-neutral-500">Exp R:</span>
                            <span className="text-neutral-200">{formatR(s.experiment_total_r)}</span>
                          </div>
                          <div className="flex justify-between text-[11px] pt-1 border-t border-neutral-800/60 font-bold">
                            <span className="text-neutral-400">Δ Total R:</span>
                            <span className={s.delta_total_r >= 0 ? "text-emerald-400" : "text-rose-400"}>
                              {formatR(s.delta_total_r)}
                            </span>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </main>
    </div>
  );
}

export default function ExperimentsPage() {
  return (
    <Suspense fallback={<div className="min-h-screen bg-neutral-950 text-white flex items-center justify-center font-mono text-sm">Loading Experiments...</div>}>
      <ExperimentsContent />
    </Suspense>
  );
}
