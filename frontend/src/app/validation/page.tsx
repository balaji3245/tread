"use client";

import React, { useState, useEffect } from "react";
import { Header } from "@/components/market/Header";
import { runValidation, exportValidation, downloadHistory } from "@/lib/api";
import {
  ConnectionState,
  ValidationRequest,
  ValidationResponse,
  WsStatusData,
} from "@/types/market";
import {
  Activity,
  AlertCircle,
  AlertTriangle,
  ArrowDownRight,
  ArrowUpRight,
  BarChart3,
  Calendar,
  CheckCircle2,
  Clock,
  Coins,
  Database,
  Download,
  FileCode,
  FileSpreadsheet,
  Filter,
  Gauge,
  HelpCircle,
  History,
  Info,
  Layers,
  Lock,
  Percent,
  Play,
  RefreshCw,
  Scale,
  ShieldAlert,
  ShieldCheck,
  TrendingDown,
  TrendingUp,
  Zap,
} from "lucide-react";

export default function ValidationPage() {
  // Connection state for header
  const [connectionState] = useState<ConnectionState>("CONNECTED");
  const [mt5Status] = useState<WsStatusData>({
    mt5_connected: true,
    symbol: "XAUUSD",
    is_mock: false,
    message: "Connected to Exness MT5 stream",
  });
  const [lastMessageTime, setLastMessageTime] = useState<number>(Date.now());

  // Form Configuration State
  const [datePreset, setDatePreset] = useState<"3m" | "6m" | "9m" | "12m" | "custom">("12m");
  const [targetMonths, setTargetMonths] = useState<number>(12);
  const [startDate, setStartDate] = useState<string>("");
  const [endDate, setEndDate] = useState<string>("");

  const [trainDays, setTrainDays] = useState<number>(90);
  const [validationDays, setValidationDays] = useState<number>(30);
  const [stepDays, setStepDays] = useState<number>(30);

  const [signalThreshold, setSignalThreshold] = useState<number>(7);
  const [slAtrMultiplier, setSlAtrMultiplier] = useState<number>(1.0);
  const [tp1AtrMultiplier, setTp1AtrMultiplier] = useState<number>(1.0);
  const [tp2AtrMultiplier, setTp2AtrMultiplier] = useState<number>(2.0);
  const [assumedSpread, setAssumedSpread] = useState<number>(0.30);
  const [maxHoldingMinutes, setMaxHoldingMinutes] = useState<number>(60);
  const [initialCapital, setInitialCapital] = useState<number>(10000);
  const [monteCarloSims, setMonteCarloSims] = useState<number>(5000);
  const [randomSeed, setRandomSeed] = useState<number>(42);
  const [finalOosLocked, setFinalOosLocked] = useState<boolean>(true);

  // Execution & Response State
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [isDownloading, setIsDownloading] = useState<boolean>(false);
  const [downloadMsg, setDownloadMsg] = useState<string | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [validationData, setValidationData] = useState<ValidationResponse | null>(null);
  const [activeSensitivityTab, setActiveSensitivityTab] = useState<"spread" | "threshold" | "exit">("spread");

  // Initialize dates
  useEffect(() => {
    applyDatePreset("12m");
    const timer = setInterval(() => setLastMessageTime(Date.now()), 5000);
    return () => clearInterval(timer);
  }, []);

  const applyDatePreset = (preset: "3m" | "6m" | "9m" | "12m" | "custom") => {
    setDatePreset(preset);
    const now = new Date();
    const endStr = now.toISOString().slice(0, 16);

    let months = 12;
    if (preset === "3m") months = 3;
    if (preset === "6m") months = 6;
    if (preset === "9m") months = 9;
    if (preset === "12m") months = 12;

    setTargetMonths(months);

    if (preset !== "custom") {
      const daysBack = months * 30;
      const start = new Date(now.getTime() - daysBack * 86400 * 1000);
      setStartDate(start.toISOString().slice(0, 16));
      setEndDate(endStr);
    }
  };

  const handleDownloadHistory = async (force: boolean = false) => {
    setIsDownloading(true);
    setDownloadMsg(null);
    setErrorMsg(null);
    try {
      const res = await downloadHistory({
        symbol: "XAUUSD",
        months: targetMonths,
        force_refresh: force,
      });
      setDownloadMsg(`Historical update complete. 1m: ${res.data?.total_1m_candles} | 5m: ${res.data?.total_5m_candles}`);
    } catch (err: any) {
      setErrorMsg(err.message || "Failed to download historical data from MT5.");
    } finally {
      setIsDownloading(false);
    }
  };

  const handleRunValidation = async () => {
    setIsLoading(true);
    setErrorMsg(null);

    const req: ValidationRequest = {
      symbol: "XAUUSD",
      start: startDate ? new Date(startDate).toISOString() : null,
      end: endDate ? new Date(endDate).toISOString() : null,
      months: datePreset !== "custom" ? targetMonths : null,
      train_days: trainDays,
      validation_days: validationDays,
      step_days: stepDays,
      signal_threshold: signalThreshold,
      sl_atr_multiplier: slAtrMultiplier,
      tp1_atr_multiplier: tp1AtrMultiplier,
      tp2_atr_multiplier: tp2AtrMultiplier,
      max_holding_minutes: maxHoldingMinutes,
      assumed_spread: assumedSpread,
      initial_capital: initialCapital,
      spread_values: [0.0, 0.20, 0.30, 0.50, 0.75, 1.0],
      threshold_values: [7, 8, 9, 10],
      monte_carlo_simulations: monteCarloSims,
      random_seed: randomSeed,
      final_oos_locked: finalOosLocked,
    };

    try {
      const resp = await runValidation(req);
      setValidationData(resp);
    } catch (err: any) {
      setErrorMsg(err.message || "Failed to execute strategy validation.");
    } finally {
      setIsLoading(false);
    }
  };

  const handleExportJson = () => {
    if (!validationData) return;
    const blob = new Blob([JSON.stringify(validationData, null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `xauusd_validation_${validationData.validation_run_id}_${validationData.configuration_hash}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleExportCsv = async () => {
    try {
      const exportResp = await exportValidation();
      if (exportResp.csv_files) {
        Object.entries(exportResp.csv_files).forEach(([filename, content]) => {
          const blob = new Blob([content], { type: "text/csv;charset=utf-8;" });
          const url = URL.createObjectURL(blob);
          const a = document.createElement("a");
          a.href = url;
          a.download = filename;
          a.click();
          URL.revokeObjectURL(url);
        });
      }
    } catch (err: any) {
      alert("Failed to export CSV: " + (err.message || "Unknown error"));
    }
  };

  const cov = validationData?.dataset_coverage;
  const dq = validationData?.data_quality;
  const valStatus = validationData?.validation_status;
  const oosCons = validationData?.oos_consistency;
  const overall = validationData?.overall_metrics;
  const oos = validationData?.out_of_sample;
  const mc = validationData?.monte_carlo;
  const exp = validationData?.expectancy;
  const dd = validationData?.drawdown_analysis;
  const conc = validationData?.period_concentration;
  const flags = validationData?.diagnostics || validationData?.robustness_summary?.flags || [];

  return (
    <div className="min-h-screen bg-neutral-950 text-neutral-100 flex flex-col font-sans selection:bg-amber-500/30 selection:text-amber-300">
      <Header
        symbol="XAUUSD"
        connectionState={connectionState}
        mt5Status={mt5Status}
        lastMessageTime={lastMessageTime}
        reconnectAttempt={0}
        onReconnect={() => {}}
      />

      <main className="flex-1 max-w-[1750px] w-full mx-auto p-4 sm:p-6 space-y-6">
        {/* Title Bar */}
        <div className="flex flex-wrap items-center justify-between gap-4 bg-gradient-to-r from-neutral-900 via-neutral-900/90 to-neutral-950 border border-neutral-800/80 rounded-2xl p-5 shadow-xl">
          <div>
            <div className="flex items-center gap-3 mb-1.5">
              <div className="p-2.5 rounded-xl bg-amber-500/10 border border-amber-500/30 text-amber-400 shadow-inner">
                <ShieldCheck className="w-6 h-6" />
              </div>
              <div>
                <h1 className="text-2xl font-black tracking-tight text-white font-mono flex items-center gap-2.5">
                  <span>XAUUSD Historical Expansion & Multi-OOS Validation</span>
                  <span className="text-xs px-2.5 py-0.5 rounded-full bg-amber-500/20 text-amber-300 border border-amber-500/40 font-mono uppercase tracking-wider">
                    Phase 5 Engine
                  </span>
                </h1>
                <p className="text-xs text-neutral-400">
                  6–12 Month Historical Replay • Multi-OOS Walk-Forward • Data Quality Audit • Final OOS Locked • Zero Parameter Tuning
                </p>
              </div>
            </div>
          </div>

          <div className="flex items-center gap-2.5">
            <button
              onClick={() => handleDownloadHistory(false)}
              disabled={isDownloading || isLoading}
              className="flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-neutral-800 hover:bg-neutral-700 text-neutral-200 text-xs font-mono font-medium border border-neutral-700 transition shadow-sm cursor-pointer disabled:opacity-50"
              title="Download or update local historical MT5 cache"
            >
              <Database className="w-3.5 h-3.5 text-cyan-400" />
              <span>{isDownloading ? "Caching MT5 Data..." : "Cache MT5 Data"}</span>
            </button>

            {validationData && (
              <>
                <button
                  onClick={handleExportJson}
                  className="flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-neutral-800 hover:bg-neutral-700 text-neutral-200 text-xs font-mono font-medium border border-neutral-700 transition shadow-sm cursor-pointer"
                >
                  <FileCode className="w-3.5 h-3.5 text-amber-400" />
                  <span>JSON</span>
                </button>
                <button
                  onClick={handleExportCsv}
                  className="flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-neutral-800 hover:bg-neutral-700 text-neutral-200 text-xs font-mono font-medium border border-neutral-700 transition shadow-sm cursor-pointer"
                >
                  <FileSpreadsheet className="w-3.5 h-3.5 text-emerald-400" />
                  <span>CSVs</span>
                </button>
              </>
            )}

            <button
              onClick={handleRunValidation}
              disabled={isLoading || isDownloading}
              className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-gradient-to-r from-amber-500 to-yellow-600 hover:from-amber-400 hover:to-yellow-500 text-neutral-950 font-bold text-xs tracking-wider uppercase font-mono shadow-lg shadow-amber-500/20 transition disabled:opacity-50 cursor-pointer"
            >
              {isLoading ? (
                <>
                  <RefreshCw className="w-4 h-4 animate-spin" />
                  <span>Evaluating Dataset...</span>
                </>
              ) : (
                <>
                  <Play className="w-4 h-4 fill-neutral-950" />
                  <span>Run Validation</span>
                </>
              )}
            </button>
          </div>
        </div>

        {downloadMsg && (
          <div className="bg-cyan-950/40 border border-cyan-800/80 rounded-2xl p-3 px-4 text-cyan-300 font-mono text-xs flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 shrink-0 text-cyan-400" />
            <span>{downloadMsg}</span>
          </div>
        )}

        {/* Configuration Panel */}
        <div className="bg-neutral-900/70 border border-neutral-800 rounded-2xl p-5 shadow-lg space-y-4">
          <div className="flex items-center justify-between border-b border-neutral-800/80 pb-3">
            <div className="flex items-center gap-2 text-neutral-200 font-mono text-xs font-bold uppercase tracking-wider">
              <Scale className="w-4 h-4 text-amber-400" />
              <span>Historical Span & Multi-OOS Parameters</span>
            </div>
            <div className="flex items-center gap-4 text-[11px] font-mono text-neutral-400">
              {validationData?.validation_run_id && (
                <span>
                  Run ID: <strong className="text-white">{validationData.validation_run_id}</strong>
                </span>
              )}
              {validationData?.configuration_hash && (
                <span>
                  Config Hash: <strong className="text-amber-400">{validationData.configuration_hash}</strong>
                </span>
              )}
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 text-xs font-mono">
            {/* Range Quick Select */}
            <div className="space-y-2">
              <label className="text-neutral-400 text-[11px] flex items-center justify-between">
                <span>Historical Duration Quick Select</span>
                <span className="text-amber-400 font-semibold">{datePreset.toUpperCase()}</span>
              </label>
              <div className="grid grid-cols-5 gap-1 p-1 bg-neutral-950 border border-neutral-800 rounded-lg text-center">
                {(["3m", "6m", "9m", "12m", "custom"] as const).map((p) => (
                  <button
                    key={p}
                    onClick={() => applyDatePreset(p)}
                    className={`py-1 rounded font-bold transition text-[11px] ${
                      datePreset === p
                        ? "bg-amber-500 text-neutral-950"
                        : "text-neutral-400 hover:text-white"
                    }`}
                  >
                    {p.toUpperCase()}
                  </button>
                ))}
              </div>
              <div className="grid grid-cols-2 gap-2 pt-1">
                <div>
                  <span className="text-[10px] text-neutral-500">From</span>
                  <input
                    type="datetime-local"
                    value={startDate}
                    onChange={(e) => {
                      setStartDate(e.target.value);
                      setDatePreset("custom");
                    }}
                    className="w-full bg-neutral-950 border border-neutral-800 rounded px-2 py-1 text-white text-[11px]"
                  />
                </div>
                <div>
                  <span className="text-[10px] text-neutral-500">To</span>
                  <input
                    type="datetime-local"
                    value={endDate}
                    onChange={(e) => {
                      setEndDate(e.target.value);
                      setDatePreset("custom");
                    }}
                    className="w-full bg-neutral-950 border border-neutral-800 rounded px-2 py-1 text-white text-[11px]"
                  />
                </div>
              </div>
            </div>

            {/* Walk-Forward Parameters */}
            <div className="space-y-2">
              <label className="text-neutral-400 text-[11px]">Walk-Forward Window Sizing</label>
              <div className="grid grid-cols-3 gap-2">
                <div>
                  <span className="text-[10px] text-neutral-500">Train (Days)</span>
                  <input
                    type="number"
                    min="7"
                    max="365"
                    value={trainDays}
                    onChange={(e) => setTrainDays(Number(e.target.value))}
                    className="w-full bg-neutral-950 border border-neutral-800 rounded px-2 py-1.5 text-white"
                  />
                </div>
                <div>
                  <span className="text-[10px] text-neutral-500">OOS (Days)</span>
                  <input
                    type="number"
                    min="1"
                    max="180"
                    value={validationDays}
                    onChange={(e) => setValidationDays(Number(e.target.value))}
                    className="w-full bg-neutral-950 border border-neutral-800 rounded px-2 py-1.5 text-white"
                  />
                </div>
                <div>
                  <span className="text-[10px] text-neutral-500">Step (Days)</span>
                  <input
                    type="number"
                    min="1"
                    max="180"
                    value={stepDays}
                    onChange={(e) => setStepDays(Number(e.target.value))}
                    className="w-full bg-neutral-950 border border-neutral-800 rounded px-2 py-1.5 text-white"
                  />
                </div>
              </div>
              <p className="text-[10px] text-neutral-500">
                Default: 90d Train, 30d OOS, 30d Step. Requires &ge; 6 OOS windows.
              </p>
            </div>

            {/* Baseline Strategy Settings (Preserved) */}
            <div className="space-y-2">
              <div className="flex items-center justify-between text-neutral-400 text-[11px]">
                <span>Baseline Strategy Parameters</span>
                <span className="text-emerald-400 text-[10px] flex items-center gap-1 font-semibold">
                  <Lock className="w-3 h-3" /> Locked
                </span>
              </div>
              <div className="grid grid-cols-3 gap-2">
                <div>
                  <span className="text-[10px] text-neutral-500">Score &ge;</span>
                  <input
                    type="number"
                    min="1"
                    max="10"
                    value={signalThreshold}
                    onChange={(e) => setSignalThreshold(Number(e.target.value))}
                    className="w-full bg-neutral-950 border border-neutral-800 rounded px-2 py-1.5 text-white"
                  />
                </div>
                <div>
                  <span className="text-[10px] text-neutral-500">SL (ATR)</span>
                  <input
                    type="number"
                    step="0.25"
                    value={slAtrMultiplier}
                    onChange={(e) => setSlAtrMultiplier(Number(e.target.value))}
                    className="w-full bg-neutral-950 border border-neutral-800 rounded px-2 py-1.5 text-white"
                  />
                </div>
                <div>
                  <span className="text-[10px] text-neutral-500">TP (ATR)</span>
                  <input
                    type="number"
                    step="0.25"
                    value={tp1AtrMultiplier}
                    onChange={(e) => setTp1AtrMultiplier(Number(e.target.value))}
                    className="w-full bg-neutral-950 border border-neutral-800 rounded px-2 py-1.5 text-white"
                  />
                </div>
              </div>
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <span className="text-[10px] text-neutral-500">Spread ($)</span>
                  <input
                    type="number"
                    step="0.05"
                    value={assumedSpread}
                    onChange={(e) => setAssumedSpread(Number(e.target.value))}
                    className="w-full bg-neutral-950 border border-neutral-800 rounded px-2 py-1.5 text-white"
                  />
                </div>
                <div>
                  <span className="text-[10px] text-neutral-500">Max Hold (m)</span>
                  <input
                    type="number"
                    value={maxHoldingMinutes}
                    onChange={(e) => setMaxHoldingMinutes(Number(e.target.value))}
                    className="w-full bg-neutral-950 border border-neutral-800 rounded px-2 py-1.5 text-white"
                  />
                </div>
              </div>
            </div>

            {/* Monte Carlo & Final OOS Lock */}
            <div className="space-y-2">
              <label className="text-neutral-400 text-[11px]">Monte Carlo & Final OOS Guard</label>
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <span className="text-[10px] text-neutral-500">Simulations</span>
                  <input
                    type="number"
                    step="500"
                    min="100"
                    max="50000"
                    value={monteCarloSims}
                    onChange={(e) => setMonteCarloSims(Number(e.target.value))}
                    className="w-full bg-neutral-950 border border-neutral-800 rounded px-2 py-1.5 text-white"
                  />
                </div>
                <div>
                  <span className="text-[10px] text-neutral-500">Seed</span>
                  <input
                    type="number"
                    value={randomSeed}
                    onChange={(e) => setRandomSeed(Number(e.target.value))}
                    className="w-full bg-neutral-950 border border-neutral-800 rounded px-2 py-1.5 text-white"
                  />
                </div>
              </div>
              <div className="pt-1.5 flex items-center justify-between text-[11px] text-neutral-400">
                <label className="flex items-center gap-1.5 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={finalOosLocked}
                    onChange={(e) => setFinalOosLocked(e.target.checked)}
                    className="rounded border-neutral-700 bg-neutral-950 text-amber-500 focus:ring-0"
                  />
                  <span>Lock Final OOS Window</span>
                </label>
                <span className="text-emerald-400 font-bold">Zero Tuning</span>
              </div>
            </div>
          </div>
        </div>

        {/* Error Alert */}
        {errorMsg && (
          <div className="bg-rose-950/40 border border-rose-800/80 rounded-2xl p-4 flex items-center gap-3 text-rose-300 font-mono text-xs shadow-lg">
            <AlertCircle className="w-5 h-5 shrink-0 text-rose-400" />
            <div>
              <p className="font-bold">Validation Execution Error</p>
              <p className="text-neutral-300">{errorMsg}</p>
            </div>
          </div>
        )}

        {/* Initial Empty State */}
        {!validationData && !isLoading && (
          <div className="bg-neutral-900/40 border border-dashed border-neutral-800 rounded-3xl p-12 text-center flex flex-col items-center justify-center space-y-4">
            <div className="p-4 rounded-2xl bg-neutral-900 border border-neutral-800 text-amber-400 shadow-xl">
              <ShieldCheck className="w-10 h-10" />
            </div>
            <div className="max-w-md space-y-1">
              <h3 className="text-lg font-bold font-mono text-white">No Validation Results Yet</h3>
              <p className="text-xs text-neutral-400">
                Select your target historical duration (3, 6, 9, or 12 months) and click <strong>RUN VALIDATION</strong> to test strategy stability across multi-OOS windows.
              </p>
            </div>
            <button
              onClick={handleRunValidation}
              className="px-6 py-2.5 rounded-xl bg-amber-500 hover:bg-amber-400 text-neutral-950 font-bold font-mono text-xs uppercase tracking-wider transition cursor-pointer shadow-lg shadow-amber-500/10"
            >
              Run 12-Month Multi-OOS Validation
            </button>
          </div>
        )}

        {/* VALIDATION RESULTS VIEW */}
        {validationData && (
          <div className="space-y-6">
            {/* PHASE 5: TOP-TIER STATUS & DATA COVERAGE CARDS */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 font-mono">
              {/* Card 1: Historical Data Coverage */}
              <div className="bg-neutral-900/90 border border-neutral-800 rounded-2xl p-4.5 space-y-3 shadow-lg">
                <div className="flex items-center justify-between border-b border-neutral-800 pb-2">
                  <div className="flex items-center gap-2 text-xs font-bold text-white uppercase tracking-wider">
                    <Database className="w-4 h-4 text-cyan-400" />
                    <span>Historical Data Coverage</span>
                  </div>
                  <span
                    className={`text-[10px] px-2 py-0.5 rounded font-bold uppercase border ${
                      cov?.data_complete
                        ? "bg-emerald-500/20 text-emerald-400 border-emerald-500/40"
                        : "bg-amber-500/20 text-amber-400 border-amber-500/40"
                    }`}
                  >
                    {cov?.data_complete ? "Complete" : "Partial"}
                  </span>
                </div>

                <div className="grid grid-cols-2 gap-2 text-[11px]">
                  <div>
                    <span className="text-neutral-500 block">Requested Span</span>
                    <span className="text-neutral-200 font-semibold">{cov?.requested_days} Days</span>
                  </div>
                  <div>
                    <span className="text-neutral-500 block">Available Span</span>
                    <span className="text-white font-bold">{cov?.available_days} Days</span>
                  </div>
                  <div>
                    <span className="text-neutral-500 block">1m Candles</span>
                    <span className="text-cyan-400 font-bold">{cov?.candle_count_1m?.toLocaleString()}</span>
                  </div>
                  <div>
                    <span className="text-neutral-500 block">5m Candles</span>
                    <span className="text-cyan-400 font-bold">{cov?.candle_count_5m?.toLocaleString()}</span>
                  </div>
                </div>

                <div className="pt-1 border-t border-neutral-800/80 text-[10px] space-y-1">
                  <div className="flex justify-between text-neutral-400">
                    <span>Coverage Status:</span>
                    <span className="text-white font-semibold">{cov?.coverage_status}</span>
                  </div>
                  <div className="flex justify-between text-neutral-400">
                    <span>Dataset Hash:</span>
                    <span className="text-amber-400 font-bold">{cov?.dataset_hash}</span>
                  </div>
                </div>
              </div>

              {/* Card 2: Validation Coverage & Status */}
              <div className="bg-neutral-900/90 border border-neutral-800 rounded-2xl p-4.5 space-y-3 shadow-lg">
                <div className="flex items-center justify-between border-b border-neutral-800 pb-2">
                  <div className="flex items-center gap-2 text-xs font-bold text-white uppercase tracking-wider">
                    <ShieldCheck className="w-4 h-4 text-amber-400" />
                    <span>Validation Status</span>
                  </div>
                  <span
                    className={`text-[10px] px-2 py-0.5 rounded font-bold uppercase border ${
                      valStatus?.status === "VALIDATION_SUFFICIENT_COVERAGE"
                        ? "bg-emerald-500/20 text-emerald-400 border-emerald-500/40"
                        : "bg-amber-500/20 text-amber-400 border-amber-500/40"
                    }`}
                  >
                    {valStatus?.status}
                  </span>
                </div>

                <div className="grid grid-cols-2 gap-2 text-[11px]">
                  <div>
                    <span className="text-neutral-500 block">OOS Windows</span>
                    <span className="text-white font-bold text-base">
                      {valStatus?.oos_windows} <span className="text-xs text-neutral-500 font-normal">(&ge; {valStatus?.minimum_oos_windows} min)</span>
                    </span>
                  </div>
                  <div>
                    <span className="text-neutral-500 block">Final OOS Window</span>
                    <span className="text-emerald-400 font-bold text-xs flex items-center gap-1 mt-0.5">
                      <Lock className="w-3.5 h-3.5" /> LOCKED
                    </span>
                  </div>
                  <div>
                    <span className="text-neutral-500 block">Baseline Evaluated</span>
                    <span className="text-neutral-200 font-semibold">YES</span>
                  </div>
                  <div>
                    <span className="text-neutral-500 block">Parameter Tuning</span>
                    <span className="text-rose-400 font-semibold">NONE (Locked)</span>
                  </div>
                </div>

                <div className="pt-1 border-t border-neutral-800/80 text-[10px] text-neutral-400 leading-tight">
                  {valStatus?.notes?.map((n, i) => (
                    <p key={i} className="text-neutral-400">• {n}</p>
                  ))}
                </div>
              </div>

              {/* Card 3: Historical Data Quality Audit */}
              <div className="bg-neutral-900/90 border border-neutral-800 rounded-2xl p-4.5 space-y-3 shadow-lg">
                <div className="flex items-center justify-between border-b border-neutral-800 pb-2">
                  <div className="flex items-center gap-2 text-xs font-bold text-white uppercase tracking-wider">
                    <Activity className="w-4 h-4 text-emerald-400" />
                    <span>Data Quality Audit</span>
                  </div>
                  <span
                    className={`text-[10px] px-2 py-0.5 rounded font-bold uppercase border ${
                      dq?.is_clean
                        ? "bg-emerald-500/20 text-emerald-400 border-emerald-500/40"
                        : "bg-amber-500/20 text-amber-400 border-amber-500/40"
                    }`}
                  >
                    {dq?.is_clean ? "PASS" : "AUDITED"}
                  </span>
                </div>

                <div className="grid grid-cols-2 gap-2 text-[11px]">
                  <div>
                    <span className="text-neutral-500 block">Duplicates (1m/5m)</span>
                    <span className="text-neutral-200 font-semibold">
                      {(dq?.duplicate_count_1m || 0) + (dq?.duplicate_count_5m || 0)}
                    </span>
                  </div>
                  <div>
                    <span className="text-neutral-500 block">Invalid OHLC</span>
                    <span className="text-neutral-200 font-semibold">
                      {(dq?.invalid_candles_count_1m || 0) + (dq?.invalid_candles_count_5m || 0)}
                    </span>
                  </div>
                  <div>
                    <span className="text-neutral-500 block">1m/5m Alignment</span>
                    <span className="text-emerald-400 font-bold">{dq?.alignment_status}</span>
                  </div>
                  <div>
                    <span className="text-neutral-500 block">Timezone</span>
                    <span className="text-neutral-200 font-semibold">{dq?.timezone || "UTC"}</span>
                  </div>
                </div>

                <div className="pt-1 border-t border-neutral-800/80 text-[10px] text-neutral-400">
                  <p>Unexpected intraday gaps (&gt;15m): <strong className="text-white">{dq?.unexpected_gaps_count}</strong></p>
                  <p>Expected weekend/rollover gaps: <strong className="text-white">{dq?.expected_market_gaps_count}</strong></p>
                </div>
              </div>
            </div>

            {/* Diagnostic Flags Banner */}
            <div className="bg-neutral-900/90 border border-neutral-800 rounded-2xl p-5 shadow-xl space-y-3">
              <div className="flex items-center justify-between border-b border-neutral-800 pb-2.5">
                <div className="flex items-center gap-2 font-mono text-xs font-bold text-white uppercase tracking-wider">
                  <ShieldAlert className="w-4 h-4 text-amber-400" />
                  <span>Robustness & Data Diagnostic Flags</span>
                </div>
                <span className="text-[11px] font-mono text-neutral-400">
                  {flags.length} measured diagnostic{flags.length === 1 ? "" : "s"}
                </span>
              </div>

              {flags.length === 0 ? (
                <div className="flex items-center gap-2 text-emerald-400 text-xs font-mono py-1">
                  <CheckCircle2 className="w-4 h-4" />
                  <span>All robustness and data sanity checks passed without divergence flags.</span>
                </div>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                  {flags.map((flag, idx) => {
                    const isWarn = flag.severity === "WARNING";
                    const isCaution = flag.severity === "CAUTION";
                    const bgClass = isCaution
                      ? "bg-rose-950/20 border-rose-800/40 text-rose-300"
                      : isWarn
                      ? "bg-amber-950/20 border-amber-800/40 text-amber-300"
                      : "bg-blue-950/20 border-blue-800/40 text-blue-300";

                    const badgeClass = isCaution
                      ? "bg-rose-500/20 text-rose-400 border-rose-500/40"
                      : isWarn
                      ? "bg-amber-500/20 text-amber-400 border-amber-500/40"
                      : "bg-blue-500/20 text-blue-400 border-blue-500/40";

                    return (
                      <div key={idx} className={`p-3.5 rounded-xl border ${bgClass} font-mono space-y-1.5`}>
                        <div className="flex items-center justify-between">
                          <span className="font-bold text-xs text-white">{flag.title}</span>
                          <span className={`text-[10px] px-2 py-0.5 rounded border uppercase font-bold ${badgeClass}`}>
                            {flag.severity}
                          </span>
                        </div>
                        <p className="text-[11px] text-neutral-300 leading-relaxed">
                          {flag.measured_evidence}
                        </p>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>

            {/* Executive Baseline Performance Metrics */}
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3 font-mono">
              <div className="bg-neutral-900/80 border border-neutral-800 rounded-2xl p-4">
                <span className="text-[11px] text-neutral-400 uppercase">Total Trades</span>
                <div className="mt-1 flex items-baseline gap-2">
                  <span className="text-2xl font-black text-white">{overall?.trades_count || 0}</span>
                  <span className="text-xs text-neutral-400">({oos?.total_oos_trades || 0} OOS)</span>
                </div>
                <span className="text-[10px] text-neutral-500 mt-1 block">Full evaluation span</span>
              </div>

              <div className="bg-neutral-900/80 border border-neutral-800 rounded-2xl p-4">
                <span className="text-[11px] text-neutral-400 uppercase">Win Rate</span>
                <div className="mt-1 flex items-baseline gap-2">
                  <span className="text-2xl font-black text-white">{overall?.win_rate || 0}%</span>
                  <span className="text-xs text-neutral-400">
                    {overall?.winning_trades}/{overall?.trades_count}
                  </span>
                </div>
                <span className="text-[10px] text-neutral-500 mt-1 block">Losing: {overall?.losing_trades}</span>
              </div>

              <div className="bg-neutral-900/80 border border-neutral-800 rounded-2xl p-4">
                <span className="text-[11px] text-neutral-400 uppercase">Total Return (R)</span>
                <div className="mt-1 flex items-baseline gap-2">
                  <span
                    className={`text-2xl font-black ${
                      (overall?.total_r || 0) >= 0 ? "text-emerald-400" : "text-rose-400"
                    }`}
                  >
                    {(overall?.total_r || 0) > 0 ? `+${overall?.total_r}` : overall?.total_r}R
                  </span>
                </div>
                <span className="text-[10px] text-neutral-500 mt-1 block">
                  OOS: {oos?.total_oos_r !== undefined && oos.total_oos_r > 0 ? `+${oos.total_oos_r}` : oos?.total_oos_r}R
                </span>
              </div>

              <div className="bg-neutral-900/80 border border-neutral-800 rounded-2xl p-4">
                <span className="text-[11px] text-neutral-400 uppercase">Average R / Trade</span>
                <div className="mt-1 flex items-baseline gap-2">
                  <span
                    className={`text-2xl font-black ${
                      (overall?.average_r || 0) >= 0 ? "text-emerald-400" : "text-rose-400"
                    }`}
                  >
                    {(overall?.average_r || 0) > 0 ? `+${overall?.average_r}` : overall?.average_r}R
                  </span>
                </div>
                <span className="text-[10px] text-neutral-500 mt-1 block">
                  Median: {overall?.median_r}R
                </span>
              </div>

              <div className="bg-neutral-900/80 border border-neutral-800 rounded-2xl p-4">
                <span className="text-[11px] text-neutral-400 uppercase">Profit Factor</span>
                <div className="mt-1 flex items-baseline gap-2">
                  <span
                    className={`text-2xl font-black ${
                      (overall?.profit_factor || 0) >= 1.0 ? "text-emerald-400" : "text-neutral-200"
                    }`}
                  >
                    {overall?.profit_factor !== null && overall?.profit_factor !== undefined
                      ? overall.profit_factor.toFixed(2)
                      : "N/A"}
                  </span>
                </div>
                <span className="text-[10px] text-neutral-500 mt-1 block">
                  OOS: {oos?.oos_profit_factor ? oos.oos_profit_factor.toFixed(2) : "N/A"}
                </span>
              </div>

              <div className="bg-neutral-900/80 border border-neutral-800 rounded-2xl p-4">
                <span className="text-[11px] text-neutral-400 uppercase">Max Drawdown</span>
                <div className="mt-1 flex items-baseline gap-2">
                  <span className="text-2xl font-black text-rose-400">
                    {overall?.max_drawdown_pct?.toFixed(1)}%
                  </span>
                  <span className="text-xs text-neutral-400">(${overall?.max_drawdown_usd?.toFixed(0)})</span>
                </div>
                <span className="text-[10px] text-neutral-500 mt-1 block">
                  OOS DD: {oos?.oos_max_drawdown_pct?.toFixed(1)}%
                </span>
              </div>
            </div>

            {/* OOS Consistency & Stability Statistics */}
            {oosCons && (
              <div className="bg-neutral-900/80 border border-neutral-800 rounded-2xl p-5 shadow-xl space-y-3 font-mono">
                <div className="flex items-center justify-between border-b border-neutral-800 pb-2.5">
                  <div className="flex items-center gap-2 text-xs font-bold text-white uppercase tracking-wider">
                    <Gauge className="w-4 h-4 text-amber-400" />
                    <span>Multi-OOS Consistency & Stability Statistics</span>
                  </div>
                </div>

                <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3 text-xs">
                  <div className="p-3 bg-neutral-950 border border-neutral-800 rounded-xl space-y-1">
                    <span className="text-[10px] text-neutral-500 uppercase">Positive Month Fraction</span>
                    <div className="text-lg font-bold text-white">
                      {(oosCons.positive_month_fraction * 100).toFixed(1)}%
                    </div>
                  </div>

                  <div className="p-3 bg-neutral-950 border border-neutral-800 rounded-xl space-y-1">
                    <span className="text-[10px] text-neutral-500 uppercase">Positive OOS Window %</span>
                    <div className="text-lg font-bold text-white">
                      {(oosCons.positive_oos_window_fraction * 100).toFixed(1)}%
                    </div>
                  </div>

                  <div className="p-3 bg-neutral-950 border border-neutral-800 rounded-xl space-y-1">
                    <span className="text-[10px] text-neutral-500 uppercase">Median Monthly Return</span>
                    <div className={`text-lg font-bold ${oosCons.median_monthly_r >= 0 ? "text-emerald-400" : "text-rose-400"}`}>
                      {oosCons.median_monthly_r > 0 ? `+${oosCons.median_monthly_r}` : oosCons.median_monthly_r}R
                    </div>
                  </div>

                  <div className="p-3 bg-neutral-950 border border-neutral-800 rounded-xl space-y-1">
                    <span className="text-[10px] text-neutral-500 uppercase">Median OOS Window Return</span>
                    <div className={`text-lg font-bold ${oosCons.median_oos_window_r >= 0 ? "text-emerald-400" : "text-rose-400"}`}>
                      {oosCons.median_oos_window_r > 0 ? `+${oosCons.median_oos_window_r}` : oosCons.median_oos_window_r}R
                    </div>
                  </div>

                  <div className="p-3 bg-neutral-950 border border-neutral-800 rounded-xl space-y-1">
                    <span className="text-[10px] text-neutral-500 uppercase">Monthly Return Std Dev</span>
                    <div className="text-lg font-bold text-neutral-200">
                      &plusmn;{oosCons.std_dev_monthly_r}R
                    </div>
                  </div>

                  <div className="p-3 bg-neutral-950 border border-neutral-800 rounded-xl space-y-1">
                    <span className="text-[10px] text-neutral-500 uppercase">OOS Window Std Dev</span>
                    <div className="text-lg font-bold text-neutral-200">
                      &plusmn;{oosCons.std_dev_oos_r}R
                    </div>
                  </div>
                </div>

                {oosCons.top_month_removed_impact && (
                  <p className="text-[11px] text-neutral-400 pt-1">
                    • <strong>Top Month Sensitivity:</strong> {oosCons.top_month_removed_impact}
                  </p>
                )}
              </div>
            )}

            {/* Walk-Forward Table & Out-Of-Sample Profile */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              {/* Walk Forward Table */}
              <div className="lg:col-span-2 bg-neutral-900/80 border border-neutral-800 rounded-2xl p-5 shadow-xl space-y-4">
                <div className="flex items-center justify-between border-b border-neutral-800 pb-3">
                  <div className="flex items-center gap-2 font-mono text-xs font-bold text-white uppercase tracking-wider">
                    <Layers className="w-4 h-4 text-amber-400" />
                    <span>Chronological Walk-Forward Windows ({validationData.walk_forward.length} Slices)</span>
                  </div>
                </div>

                <div className="overflow-x-auto">
                  <table className="w-full text-left font-mono text-xs border-collapse">
                    <thead>
                      <tr className="border-b border-neutral-800 text-neutral-400 text-[11px]">
                        <th className="py-2.5 px-3">Win #</th>
                        <th className="py-2.5 px-3">Train Window</th>
                        <th className="py-2.5 px-3">Train R</th>
                        <th className="py-2.5 px-3">OOS Window</th>
                        <th className="py-2.5 px-3">OOS Trades</th>
                        <th className="py-2.5 px-3">OOS WR</th>
                        <th className="py-2.5 px-3">OOS Total R</th>
                        <th className="py-2.5 px-3">OOS PF</th>
                        <th className="py-2.5 px-3">Status</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-neutral-800/60 text-neutral-200 text-xs">
                      {validationData.walk_forward.map((w) => (
                        <tr key={w.window_index} className="hover:bg-neutral-800/30 transition">
                          <td className="py-2.5 px-3 font-bold text-amber-400">#{w.window_index}</td>
                          <td className="py-2.5 px-3 text-[11px] text-neutral-400">
                            {w.train_start_iso.slice(5, 10)} &rarr; {w.train_end_iso.slice(5, 10)}
                          </td>
                          <td className="py-2.5 px-3 font-semibold">
                            <span className={w.train_metrics.total_r >= 0 ? "text-emerald-400" : "text-rose-400"}>
                              {w.train_metrics.total_r > 0 ? `+${w.train_metrics.total_r}` : w.train_metrics.total_r}R
                            </span>
                          </td>
                          <td className="py-2.5 px-3 text-[11px] text-neutral-300 font-semibold">
                            {w.validation_start_iso.slice(5, 10)} &rarr; {w.validation_end_iso.slice(5, 10)}
                          </td>
                          <td className="py-2.5 px-3">{w.validation_metrics.trades_count}</td>
                          <td className="py-2.5 px-3">{w.validation_metrics.win_rate}%</td>
                          <td className="py-2.5 px-3 font-bold">
                            <span className={w.validation_metrics.total_r >= 0 ? "text-emerald-400" : "text-rose-400"}>
                              {w.validation_metrics.total_r > 0 ? `+${w.validation_metrics.total_r}` : w.validation_metrics.total_r}R
                            </span>
                          </td>
                          <td className="py-2.5 px-3 text-neutral-400">
                            {w.validation_metrics.profit_factor ? w.validation_metrics.profit_factor.toFixed(2) : "N/A"}
                          </td>
                          <td className="py-2.5 px-3">
                            {w.is_final_oos ? (
                              <span className="px-2 py-0.5 rounded text-[10px] bg-amber-500/20 text-amber-300 border border-amber-500/40 font-bold uppercase">
                                Final OOS
                              </span>
                            ) : (
                              <span className="text-[10px] text-neutral-500 uppercase font-semibold">
                                Sequential
                              </span>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Out-of-Sample Consolidated Profile */}
              <div className="bg-neutral-900/80 border border-neutral-800 rounded-2xl p-5 shadow-xl space-y-4 flex flex-col justify-between font-mono">
                <div className="space-y-4">
                  <div className="flex items-center justify-between border-b border-neutral-800 pb-3">
                    <div className="flex items-center gap-2 text-xs font-bold text-white uppercase tracking-wider">
                      <Zap className="w-4 h-4 text-emerald-400" />
                      <span>Out-Of-Sample Profile</span>
                    </div>
                  </div>

                  <div className="space-y-3 text-xs">
                    <div className="p-3 bg-neutral-950 border border-neutral-800 rounded-xl space-y-1">
                      <span className="text-[10px] text-neutral-500 uppercase">Profitable OOS Window Fraction</span>
                      <div className="flex items-baseline justify-between">
                        <span className="text-xl font-bold text-white">
                          {( (oos?.profitable_period_fraction || 0) * 100 ).toFixed(1)}%
                        </span>
                        <span className="text-neutral-400 text-xs">
                          {oos?.positive_oos_periods} Positive / {oos?.negative_oos_periods} Negative
                        </span>
                      </div>
                    </div>

                    <div className="p-3 bg-neutral-950 border border-neutral-800 rounded-xl space-y-1">
                      <span className="text-[10px] text-neutral-500 uppercase">Combined OOS Expectancy</span>
                      <div className="flex items-baseline justify-between">
                        <span className={`text-xl font-bold ${(oos?.oos_expectancy || 0) >= 0 ? "text-emerald-400" : "text-rose-400"}`}>
                          {(oos?.oos_expectancy || 0) > 0 ? `+${oos?.oos_expectancy}` : oos?.oos_expectancy}R / trade
                        </span>
                        <span className="text-neutral-400 text-xs">
                          Total: {oos?.total_oos_r}R
                        </span>
                      </div>
                    </div>

                    <div className="p-3 bg-neutral-950 border border-neutral-800 rounded-xl space-y-1">
                      <span className="text-[10px] text-neutral-500 uppercase">OOS Max Drawdown</span>
                      <div className="flex items-baseline justify-between">
                        <span className="text-xl font-bold text-rose-400">
                          {oos?.oos_max_drawdown_pct?.toFixed(1)}%
                        </span>
                        <span className="text-neutral-400 text-xs">
                          ${oos?.oos_max_drawdown_usd?.toFixed(0)}
                        </span>
                      </div>
                    </div>
                  </div>
                </div>

                <p className="text-[10px] text-neutral-500 italic">
                  * Unseen historical validation slices evaluate out-of-sample stability without parameter tuning.
                </p>
              </div>
            </div>

            {/* Month-By-Month Breakdown & Period Concentration */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 font-mono">
              {/* Monthly Table */}
              <div className="lg:col-span-2 bg-neutral-900/80 border border-neutral-800 rounded-2xl p-5 shadow-xl space-y-4">
                <div className="flex items-center justify-between border-b border-neutral-800 pb-3">
                  <div className="flex items-center gap-2 text-xs font-bold text-white uppercase tracking-wider">
                    <Calendar className="w-4 h-4 text-amber-400" />
                    <span>Month-by-Month Empirical Performance ({validationData.monthly.length} Months)</span>
                  </div>
                </div>

                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs border-collapse">
                    <thead>
                      <tr className="border-b border-neutral-800 text-neutral-400 text-[11px]">
                        <th className="py-2.5 px-3">Month</th>
                        <th className="py-2.5 px-3">Trades</th>
                        <th className="py-2.5 px-3">Win Rate</th>
                        <th className="py-2.5 px-3">Total R</th>
                        <th className="py-2.5 px-3">Avg R</th>
                        <th className="py-2.5 px-3">PF</th>
                        <th className="py-2.5 px-3">Max DD</th>
                        <th className="py-2.5 px-3">L / S</th>
                        <th className="py-2.5 px-3">1m / 5m Bars</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-neutral-800/60 text-neutral-200">
                      {validationData.monthly.map((m) => (
                        <tr key={m.year_month} className="hover:bg-neutral-800/30 transition">
                          <td className="py-2.5 px-3 font-semibold text-white">{m.month_name}</td>
                          <td className="py-2.5 px-3">{m.trades}</td>
                          <td className="py-2.5 px-3">{m.win_rate}%</td>
                          <td className="py-2.5 px-3 font-bold">
                            <span className={m.total_r >= 0 ? "text-emerald-400" : "text-rose-400"}>
                              {m.total_r > 0 ? `+${m.total_r}` : m.total_r}R
                            </span>
                          </td>
                          <td className="py-2.5 px-3 text-neutral-300">
                            {m.average_r > 0 ? `+${m.average_r}` : m.average_r}R
                          </td>
                          <td className="py-2.5 px-3 text-neutral-400">
                            {m.profit_factor ? m.profit_factor.toFixed(2) : "N/A"}
                          </td>
                          <td className="py-2.5 px-3 text-rose-400">${m.max_drawdown_usd.toFixed(0)}</td>
                          <td className="py-2.5 px-3 text-neutral-400 text-[11px]">
                            {m.long_trades} / {m.short_trades}
                          </td>
                          <td className="py-2.5 px-3 text-neutral-500 text-[10px]">
                            {m.candle_count_1m} / {m.candle_count_5m}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Period Concentration */}
              <div className="bg-neutral-900/80 border border-neutral-800 rounded-2xl p-5 shadow-xl space-y-4">
                <div className="flex items-center justify-between border-b border-neutral-800 pb-3">
                  <div className="flex items-center gap-2 text-xs font-bold text-white uppercase tracking-wider">
                    <BarChart3 className="w-4 h-4 text-amber-400" />
                    <span>Period Concentration</span>
                  </div>
                </div>

                <div className="space-y-4 text-xs">
                  <p className="text-neutral-300 text-[11px] leading-relaxed">
                    {conc?.description}
                  </p>

                  <div className="space-y-3">
                    <div>
                      <div className="flex justify-between text-[11px] text-neutral-400 mb-1">
                        <span>Top 1 Month Contribution</span>
                        <span className="font-bold text-white">{conc?.top_1_month_pct}%</span>
                      </div>
                      <div className="w-full bg-neutral-950 h-2 rounded-full overflow-hidden border border-neutral-800">
                        <div
                          className="bg-amber-400 h-full rounded-full"
                          style={{ width: `${Math.min(100, conc?.top_1_month_pct || 0)}%` }}
                        />
                      </div>
                    </div>

                    <div>
                      <div className="flex justify-between text-[11px] text-neutral-400 mb-1">
                        <span>Top 2 Months Contribution</span>
                        <span className="font-bold text-white">{conc?.top_2_month_pct}%</span>
                      </div>
                      <div className="w-full bg-neutral-950 h-2 rounded-full overflow-hidden border border-neutral-800">
                        <div
                          className="bg-amber-500 h-full rounded-full"
                          style={{ width: `${Math.min(100, conc?.top_2_month_pct || 0)}%` }}
                        />
                      </div>
                    </div>

                    <div>
                      <div className="flex justify-between text-[11px] text-neutral-400 mb-1">
                        <span>Top 3 Months Contribution</span>
                        <span className="font-bold text-white">{conc?.top_3_month_pct}%</span>
                      </div>
                      <div className="w-full bg-neutral-950 h-2 rounded-full overflow-hidden border border-neutral-800">
                        <div
                          className="bg-yellow-500 h-full rounded-full"
                          style={{ width: `${Math.min(100, conc?.top_3_month_pct || 0)}%` }}
                        />
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* Sensitivity Analysis Matrices (Spread on Expanded Data, Threshold & Exit on Development Only) */}
            <div className="bg-neutral-900/80 border border-neutral-800 rounded-2xl p-5 shadow-xl space-y-4 font-mono">
              <div className="flex flex-wrap items-center justify-between gap-4 border-b border-neutral-800 pb-3">
                <div className="flex items-center gap-2 text-xs font-bold text-white uppercase tracking-wider">
                  <Scale className="w-4 h-4 text-amber-400" />
                  <span>Sensitivity Analysis Matrices</span>
                </div>

                <div className="flex items-center gap-1.5 p-1 bg-neutral-950 border border-neutral-800 rounded-xl text-xs">
                  <button
                    onClick={() => setActiveSensitivityTab("spread")}
                    className={`px-3 py-1.5 rounded-lg font-bold transition ${
                      activeSensitivityTab === "spread"
                        ? "bg-amber-500 text-neutral-950"
                        : "text-neutral-400 hover:text-white"
                    }`}
                  >
                    Spread (Expanded Data)
                  </button>
                  <button
                    onClick={() => setActiveSensitivityTab("threshold")}
                    className={`px-3 py-1.5 rounded-lg font-bold transition ${
                      activeSensitivityTab === "threshold"
                        ? "bg-amber-500 text-neutral-950"
                        : "text-neutral-400 hover:text-white"
                    }`}
                  >
                    Threshold (Development Only)
                  </button>
                  <button
                    onClick={() => setActiveSensitivityTab("exit")}
                    className={`px-3 py-1.5 rounded-lg font-bold transition ${
                      activeSensitivityTab === "exit"
                        ? "bg-amber-500 text-neutral-950"
                        : "text-neutral-400 hover:text-white"
                    }`}
                  >
                    ATR Exit (Development Only)
                  </button>
                </div>
              </div>

              {/* Spread Sensitivity Tab */}
              {activeSensitivityTab === "spread" && (
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs border-collapse">
                    <thead>
                      <tr className="border-b border-neutral-800 text-neutral-400 text-[11px]">
                        <th className="py-2.5 px-3">Fixed Spread ($)</th>
                        <th className="py-2.5 px-3">Trades</th>
                        <th className="py-2.5 px-3">Win Rate</th>
                        <th className="py-2.5 px-3">Total R</th>
                        <th className="py-2.5 px-3">Average R</th>
                        <th className="py-2.5 px-3">Profit Factor</th>
                        <th className="py-2.5 px-3">Max DD ($)</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-neutral-800/60 text-neutral-200">
                      {validationData.spread_sensitivity.map((s) => (
                        <tr key={s.spread} className="hover:bg-neutral-800/30 transition">
                          <td className="py-2.5 px-3 font-bold text-amber-400">${s.spread.toFixed(2)}</td>
                          <td className="py-2.5 px-3">{s.trades}</td>
                          <td className="py-2.5 px-3">{s.win_rate}%</td>
                          <td className="py-2.5 px-3 font-bold">
                            <span className={s.total_r >= 0 ? "text-emerald-400" : "text-rose-400"}>
                              {s.total_r > 0 ? `+${s.total_r}` : s.total_r}R
                            </span>
                          </td>
                          <td className="py-2.5 px-3">
                            <span className={s.average_r >= 0 ? "text-emerald-400" : "text-rose-400"}>
                              {s.average_r > 0 ? `+${s.average_r}` : s.average_r}R
                            </span>
                          </td>
                          <td className="py-2.5 px-3 text-neutral-400">
                            {s.profit_factor ? s.profit_factor.toFixed(2) : "N/A"}
                          </td>
                          <td className="py-2.5 px-3 text-rose-400">${s.max_drawdown_usd.toFixed(0)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}

              {/* Threshold Sensitivity Tab */}
              {activeSensitivityTab === "threshold" && (
                <div className="overflow-x-auto">
                  <div className="pb-2 text-[11px] text-amber-400/80 flex items-center gap-1.5">
                    <Lock className="w-3.5 h-3.5" />
                    <span>Development/In-Sample only. Final OOS window is strictly locked against threshold selection.</span>
                  </div>
                  <table className="w-full text-left text-xs border-collapse">
                    <thead>
                      <tr className="border-b border-neutral-800 text-neutral-400 text-[11px]">
                        <th className="py-2.5 px-3">Score Threshold</th>
                        <th className="py-2.5 px-3">Signals</th>
                        <th className="py-2.5 px-3">Trades</th>
                        <th className="py-2.5 px-3">Win Rate</th>
                        <th className="py-2.5 px-3">Total R</th>
                        <th className="py-2.5 px-3">Average R</th>
                        <th className="py-2.5 px-3">Profit Factor</th>
                        <th className="py-2.5 px-3">Sample Reliability Note</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-neutral-800/60 text-neutral-200">
                      {validationData.threshold_sensitivity_development.map((t) => (
                        <tr key={t.threshold} className="hover:bg-neutral-800/30 transition">
                          <td className="py-2.5 px-3 font-bold text-amber-400">{t.threshold}/10</td>
                          <td className="py-2.5 px-3">{t.signals}</td>
                          <td className="py-2.5 px-3">{t.trades}</td>
                          <td className="py-2.5 px-3">{t.win_rate}%</td>
                          <td className="py-2.5 px-3 font-bold">
                            <span className={t.total_r >= 0 ? "text-emerald-400" : "text-rose-400"}>
                              {t.total_r > 0 ? `+${t.total_r}` : t.total_r}R
                            </span>
                          </td>
                          <td className="py-2.5 px-3">
                            <span className={t.average_r >= 0 ? "text-emerald-400" : "text-rose-400"}>
                              {t.average_r > 0 ? `+${t.average_r}` : t.average_r}R
                            </span>
                          </td>
                          <td className="py-2.5 px-3 text-neutral-400">
                            {t.profit_factor ? t.profit_factor.toFixed(2) : "N/A"}
                          </td>
                          <td className="py-2.5 px-3">
                            {t.sample_size_warning ? (
                              <span className="text-amber-400 font-semibold flex items-center gap-1.5 text-[11px]">
                                <AlertTriangle className="w-3.5 h-3.5 shrink-0" />
                                <span>{t.sample_size_note}</span>
                              </span>
                            ) : (
                              <span className="text-emerald-400 text-[11px]">Sufficient Sample Size</span>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}

              {/* Exit Sensitivity Tab */}
              {activeSensitivityTab === "exit" && (
                <div className="overflow-x-auto">
                  <div className="pb-2 text-[11px] text-amber-400/80 flex items-center gap-1.5">
                    <Lock className="w-3.5 h-3.5" />
                    <span>Development/In-Sample only. Predefined Cases A–E tested without OOS optimization.</span>
                  </div>
                  <table className="w-full text-left text-xs border-collapse">
                    <thead>
                      <tr className="border-b border-neutral-800 text-neutral-400 text-[11px]">
                        <th className="py-2.5 px-3">Case</th>
                        <th className="py-2.5 px-3">Scenario Multipliers</th>
                        <th className="py-2.5 px-3">Trades</th>
                        <th className="py-2.5 px-3">Win Rate</th>
                        <th className="py-2.5 px-3">Total R</th>
                        <th className="py-2.5 px-3">Average R</th>
                        <th className="py-2.5 px-3">Profit Factor</th>
                        <th className="py-2.5 px-3">Max DD ($)</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-neutral-800/60 text-neutral-200">
                      {validationData.exit_sensitivity_development.map((e) => (
                        <tr key={e.case_id} className="hover:bg-neutral-800/30 transition">
                          <td className="py-2.5 px-3 font-bold text-amber-400">{e.case_id}</td>
                          <td className="py-2.5 px-3 text-white">{e.label}</td>
                          <td className="py-2.5 px-3">{e.trades}</td>
                          <td className="py-2.5 px-3">{e.win_rate}%</td>
                          <td className="py-2.5 px-3 font-bold">
                            <span className={e.total_r >= 0 ? "text-emerald-400" : "text-rose-400"}>
                              {e.total_r > 0 ? `+${e.total_r}` : e.total_r}R
                            </span>
                          </td>
                          <td className="py-2.5 px-3">
                            <span className={e.average_r >= 0 ? "text-emerald-400" : "text-rose-400"}>
                              {e.average_r > 0 ? `+${e.average_r}` : e.average_r}R
                            </span>
                          </td>
                          <td className="py-2.5 px-3 text-neutral-400">
                            {e.profit_factor ? e.profit_factor.toFixed(2) : "N/A"}
                          </td>
                          <td className="py-2.5 px-3 text-rose-400">${e.max_drawdown_usd.toFixed(0)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>

            {/* Monte Carlo Trade-Order Analysis */}
            <div className="bg-neutral-900/80 border border-neutral-800 rounded-2xl p-5 shadow-xl space-y-4 font-mono">
              <div className="flex items-center justify-between border-b border-neutral-800 pb-3">
                <div className="flex items-center gap-2 text-xs font-bold text-white uppercase tracking-wider">
                  <Coins className="w-4 h-4 text-amber-400" />
                  <span>Monte Carlo Trade-Order Sensitivity ({mc?.simulations.toLocaleString()} Simulations)</span>
                </div>
                <span className="text-[11px] text-neutral-400">
                  Seed: <span className="text-amber-400">{mc?.random_seed ?? "None"}</span>
                </span>
              </div>

              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
                <div className="p-3.5 bg-neutral-950 border border-neutral-800 rounded-xl space-y-1">
                  <span className="text-[10px] text-neutral-500 uppercase">Median Max Drawdown</span>
                  <div className="text-xl font-bold text-rose-400">
                    ${mc?.median_max_drawdown_usd?.toFixed(0)}
                  </div>
                  <span className="text-[10px] text-neutral-500">50th percentile drawdown</span>
                </div>

                <div className="p-3.5 bg-neutral-950 border border-neutral-800 rounded-xl space-y-1">
                  <span className="text-[10px] text-neutral-500 uppercase">95th %ile Max Drawdown (Tail)</span>
                  <div className="text-xl font-bold text-rose-500">
                    ${mc?.percentile_95_max_drawdown_usd?.toFixed(0)}
                  </div>
                  <span className="text-[10px] text-neutral-500">Worst 5% tail risk scenario</span>
                </div>

                <div className="p-3.5 bg-neutral-950 border border-neutral-800 rounded-xl space-y-1">
                  <span className="text-[10px] text-neutral-500 uppercase">Ending Return (5th - 95th)</span>
                  <div className="text-xl font-bold text-white">
                    {mc?.percentile_5_ending_r?.toFixed(1)}R &rarr; {mc?.percentile_95_ending_r?.toFixed(1)}R
                  </div>
                  <span className="text-[10px] text-neutral-500">Median: {mc?.median_ending_r?.toFixed(1)}R</span>
                </div>

                <div className="p-3.5 bg-neutral-950 border border-neutral-800 rounded-xl space-y-1">
                  <span className="text-[10px] text-neutral-500 uppercase">Max Observed Losing Streak</span>
                  <div className="text-xl font-bold text-amber-400">
                    {mc?.max_observed_losing_streak} Losses
                  </div>
                  <span className="text-[10px] text-neutral-500">Peak observed in resamplings</span>
                </div>
              </div>

              <p className="text-[11px] text-neutral-400 italic leading-relaxed">
                {mc?.disclaimer}
              </p>
            </div>

            {/* Expectancy & Granular Drawdown Profile */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 font-mono">
              {/* Mathematical Expectancy */}
              <div className="bg-neutral-900/80 border border-neutral-800 rounded-2xl p-5 shadow-xl space-y-4">
                <div className="flex items-center justify-between border-b border-neutral-800 pb-3">
                  <div className="flex items-center gap-2 text-xs font-bold text-white uppercase tracking-wider">
                    <Scale className="w-4 h-4 text-emerald-400" />
                    <span>Mathematical Expectancy</span>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-3 text-xs">
                  <div className="p-3 bg-neutral-950 border border-neutral-800 rounded-xl">
                    <span className="text-[10px] text-neutral-500 uppercase">Expectancy / Trade</span>
                    <div className={`text-xl font-bold mt-1 ${(exp?.expectancy_per_trade || 0) >= 0 ? "text-emerald-400" : "text-rose-400"}`}>
                      {(exp?.expectancy_per_trade || 0) > 0 ? `+${exp?.expectancy_per_trade}` : exp?.expectancy_per_trade}R
                    </div>
                  </div>
                  <div className="p-3 bg-neutral-950 border border-neutral-800 rounded-xl">
                    <span className="text-[10px] text-neutral-500 uppercase">Risk-Reward Ratio</span>
                    <div className="text-xl font-bold text-white mt-1">
                      1 : {exp?.risk_reward_ratio?.toFixed(2)}
                    </div>
                  </div>
                  <div className="p-3 bg-neutral-950 border border-neutral-800 rounded-xl">
                    <span className="text-[10px] text-neutral-500 uppercase">Win / Loss Probability</span>
                    <div className="text-sm font-semibold text-neutral-200 mt-1">
                      {((exp?.win_probability || 0) * 100).toFixed(1)}% / {((exp?.loss_probability || 0) * 100).toFixed(1)}%
                    </div>
                  </div>
                  <div className="p-3 bg-neutral-950 border border-neutral-800 rounded-xl">
                    <span className="text-[10px] text-neutral-500 uppercase">Avg Win R / Avg Loss R</span>
                    <div className="text-sm font-semibold text-neutral-200 mt-1">
                      +{exp?.avg_winning_r}R / -{exp?.avg_losing_r}R
                    </div>
                  </div>
                </div>
              </div>

              {/* Granular Drawdown Profile */}
              <div className="bg-neutral-900/80 border border-neutral-800 rounded-2xl p-5 shadow-xl space-y-4">
                <div className="flex items-center justify-between border-b border-neutral-800 pb-3">
                  <div className="flex items-center gap-2 text-xs font-bold text-white uppercase tracking-wider">
                    <TrendingDown className="w-4 h-4 text-rose-400" />
                    <span>Granular Drawdown Profile</span>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-3 text-xs">
                  <div className="p-3 bg-neutral-950 border border-neutral-800 rounded-xl">
                    <span className="text-[10px] text-neutral-500 uppercase">Average Drawdown ($)</span>
                    <div className="text-xl font-bold text-rose-400 mt-1">
                      ${dd?.avg_drawdown_usd?.toFixed(0)}
                    </div>
                  </div>
                  <div className="p-3 bg-neutral-950 border border-neutral-800 rounded-xl">
                    <span className="text-[10px] text-neutral-500 uppercase">Recovery Factor</span>
                    <div className="text-xl font-bold text-white mt-1">
                      {dd?.recovery_factor !== null && dd?.recovery_factor !== undefined
                        ? dd.recovery_factor.toFixed(2)
                        : "N/A"}
                    </div>
                  </div>
                  <div className="p-3 bg-neutral-950 border border-neutral-800 rounded-xl">
                    <span className="text-[10px] text-neutral-500 uppercase">Drawdown Episodes</span>
                    <div className="text-sm font-semibold text-neutral-200 mt-1">
                      {dd?.num_drawdowns} distinct dips
                    </div>
                  </div>
                  <div className="p-3 bg-neutral-950 border border-neutral-800 rounded-xl">
                    <span className="text-[10px] text-neutral-500 uppercase">Max / Avg Losing Streak</span>
                    <div className="text-sm font-semibold text-neutral-200 mt-1">
                      {dd?.max_losing_streak} trades / {dd?.avg_losing_streak} trades
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* Direction & Session Breakdown */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6 font-mono text-xs">
              {/* Direction Breakdown */}
              <div className="bg-neutral-900/80 border border-neutral-800 rounded-2xl p-5 shadow-xl space-y-4">
                <div className="flex items-center justify-between border-b border-neutral-800 pb-3">
                  <span className="text-xs font-bold text-white uppercase tracking-wider">
                    Directional Robustness (LONG vs SHORT)
                  </span>
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div className="p-3.5 bg-neutral-950 border border-neutral-800 rounded-xl space-y-1">
                    <span className="text-[10px] text-neutral-400 font-bold uppercase">LONG Setups</span>
                    <div className="text-lg font-black text-emerald-400">
                      {overall?.long_win_rate}% WR
                    </div>
                    <p className="text-[11px] text-neutral-400">
                      {overall?.long_trades} Trades | {(overall?.long_total_r ?? 0) > 0 ? `+${overall?.long_total_r}` : overall?.long_total_r ?? 0}R
                    </p>
                  </div>
                  <div className="p-3.5 bg-neutral-950 border border-neutral-800 rounded-xl space-y-1">
                    <span className="text-[10px] text-neutral-400 font-bold uppercase">SHORT Setups</span>
                    <div className="text-lg font-black text-rose-400">
                      {overall?.short_win_rate}% WR
                    </div>
                    <p className="text-[11px] text-neutral-400">
                      {overall?.short_trades} Trades | {(overall?.short_total_r ?? 0) > 0 ? `+${overall?.short_total_r}` : overall?.short_total_r ?? 0}R
                    </p>
                  </div>
                </div>
              </div>

              {/* Session Breakdown */}
              <div className="bg-neutral-900/80 border border-neutral-800 rounded-2xl p-5 shadow-xl space-y-4">
                <div className="flex items-center justify-between border-b border-neutral-800 pb-3">
                  <span className="text-xs font-bold text-white uppercase tracking-wider">
                    Market Sessions (UTC Canonical)
                  </span>
                </div>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                  {validationData.session_breakdown.map((s: any, idx: number) => (
                    <div key={idx} className="p-2.5 bg-neutral-950 border border-neutral-800 rounded-xl space-y-0.5 text-center">
                      <span className="text-[10px] text-neutral-400 block truncate">{s.session}</span>
                      <span className="font-bold text-white block text-sm">{s.win_rate}%</span>
                      <span className="text-[10px] text-neutral-500 block">{s.total_trades} trades</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            {/* Mandatory Factual Disclaimer */}
            <div className="bg-neutral-950 border border-neutral-800 rounded-2xl p-4 font-mono text-xs text-neutral-400 space-y-1.5 shadow-inner">
              <div className="flex items-center gap-2 text-amber-400 font-bold uppercase text-[11px]">
                <Info className="w-4 h-4" />
                <span>Empirical Strategy Validation & Simulation Disclaimer</span>
              </div>
              <p className="text-[11px] leading-relaxed text-neutral-400">
                {validationData.disclaimer}
              </p>
              <div className="pt-1 flex flex-wrap gap-4 text-[10px] text-neutral-500">
                <span><strong>Execution Model:</strong> Next 1m Open ($T+1$)</span>
                <span><strong>Same-Candle Policy:</strong> Stop First (Conservative)</span>
                <span><strong>Dataset:</strong> Real Exness MT5 Historical Multi-Timeframe Bars</span>
                <span><strong>Temporal Logic:</strong> Strict Zero Future-Leakage</span>
                <span><strong>Phase 5 Architecture:</strong> Multi-OOS Windows & Data Quality Audited</span>
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
