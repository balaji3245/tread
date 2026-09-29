"use client";

import React, { useCallback, useEffect, useState } from "react";
import { Header } from "@/components/market/Header";
import { PriceDisplay } from "@/components/market/PriceDisplay";
import { MarketAnalysis } from "@/components/market/MarketAnalysis";
import { ShadowMonitoring } from "@/components/market/ShadowMonitoring";
import { CandlestickChart } from "@/components/charts/CandlestickChart";
import { ConnectionBanner } from "@/components/ui/ConnectionBanner";
import { useMarketWebSocket } from "@/hooks/useMarketWebSocket";
import { fetchAnalysis, fetchCandles, fetchSymbolInfo } from "@/lib/api";
import { Candle, MarketSignal, MarketTick, SymbolInfo, Timeframe } from "@/types/market";

export default function DashboardPage() {
  const [activeTimeframe, setActiveTimeframe] = useState<Timeframe>("1m");
  const [candles, setCandles] = useState<Candle[]>([]);
  const [liveCandle, setLiveCandle] = useState<Candle | null>(null);
  const [latestTick, setLatestTick] = useState<MarketTick | null>(null);
  const [marketSignal, setMarketSignal] = useState<MarketSignal | null>(null);
  const [symbolInfo, setSymbolInfo] = useState<SymbolInfo | null>(null);
  const [isLoadingCandles, setIsLoadingCandles] = useState<boolean>(true);
  const [loadError, setLoadError] = useState<string | null>(null);

  // Load historical candles
  const loadHistoricalCandles = useCallback(async (tf: Timeframe) => {
    try {
      setIsLoadingCandles(true);
      setLoadError(null);
      const data = await fetchCandles(tf, 300);
      setCandles(data);
      if (data.length > 0) {
        setLiveCandle(data[data.length - 1]);
      }
    } catch (err: any) {
      console.warn(`Could not load ${tf} historical candles:`, err.message);
      setLoadError(err.message || "Failed to load historical candles.");
    } finally {
      setIsLoadingCandles(false);
    }
  }, []);

  // Load symbol specs
  const loadSpecs = useCallback(async () => {
    try {
      const info = await fetchSymbolInfo();
      setSymbolInfo(info);
    } catch (err) {
      console.debug("Symbol specs fetch deferred until MT5 connected:", err);
    }
  }, []);

  // Load initial analysis
  const loadInitialAnalysis = useCallback(async () => {
    try {
      const res = await fetchAnalysis();
      if (res && res.signal) {
        setMarketSignal(res.signal);
      }
    } catch (err) {
      console.debug("Analysis fetch deferred until stream active:", err);
    }
  }, []);

  // Handle live WebSocket callbacks
  const handleTick = useCallback((tick: MarketTick) => {
    setLatestTick(tick);
  }, []);

  const handleCandle = useCallback(
    (timeframe: Timeframe, candle: Candle) => {
      if (timeframe === activeTimeframe) {
        setLiveCandle(candle);
      }
    },
    [activeTimeframe]
  );

  const handleAnalysis = useCallback((signal: MarketSignal) => {
    setMarketSignal(signal);
  }, []);

  const {
    connectionState,
    mt5Status,
    lastMessageTime,
    reconnectAttempt,
    manualReconnect,
  } = useMarketWebSocket({
    onTick: handleTick,
    onCandle: handleCandle,
    onAnalysis: handleAnalysis,
    onStatus: (status) => {
      if (status.mt5_connected) {
        loadSpecs();
        loadInitialAnalysis();
      }
    },
  });

  // Initial load
  useEffect(() => {
    loadHistoricalCandles(activeTimeframe);
    loadSpecs();
    loadInitialAnalysis();
  }, [activeTimeframe, loadHistoricalCandles, loadSpecs, loadInitialAnalysis]);

  // Calculate day stats from candles
  const dayOpen = candles.length > 0 ? candles[0].open : undefined;
  const dayHigh = candles.length > 0 ? Math.max(...candles.map((c) => c.high)) : undefined;
  const dayLow = candles.length > 0 ? Math.min(...candles.map((c) => c.low)) : undefined;

  const currentSymbol = symbolInfo?.symbol || mt5Status.symbol || "XAUUSD";

  return (
    <div className="min-h-screen bg-neutral-950 text-neutral-100 flex flex-col font-sans selection:bg-amber-500/30 selection:text-amber-200">
      {/* Sticky Header */}
      <Header
        symbol={currentSymbol}
        connectionState={connectionState}
        mt5Status={mt5Status}
        lastMessageTime={lastMessageTime}
        reconnectAttempt={reconnectAttempt}
        onReconnect={manualReconnect}
      />

      {/* Disconnection or MT5 issue notification banner */}
      <ConnectionBanner
        connectionState={connectionState}
        mt5Status={mt5Status}
        onRetry={() => {
          manualReconnect();
          loadHistoricalCandles(activeTimeframe);
          loadInitialAnalysis();
        }}
      />

      {/* Main Content Area */}
      <main className="flex-1 p-3 sm:p-5 max-w-[1700px] w-full mx-auto flex flex-col gap-4">
        {/* Main Grid: Candlestick Chart (Left 9 cols) + Compact Price/BID/ASK Panel (Right 3 cols) */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 items-start">
          {/* Main Candlestick Chart (9 cols on large screens) */}
          <div className="lg:col-span-9 flex flex-col min-h-[580px] lg:min-h-[640px]">
            <CandlestickChart
              candles={candles}
              timeframe={activeTimeframe}
              onTimeframeChange={(tf) => {
                setActiveTimeframe(tf);
                loadHistoricalCandles(tf);
              }}
              liveCandle={liveCandle}
              isLoading={isLoadingCandles}
              onReload={() => loadHistoricalCandles(activeTimeframe)}
            />
          </div>

          {/* Right Column: Compact BID (SELL), SPREAD, ASK (BUY) & Session Metrics (3 cols) */}
          <div className="lg:col-span-3 flex flex-col">
            <PriceDisplay
              tick={latestTick}
              dayOpenPrice={dayOpen}
              dayHighPrice={dayHigh}
              dayLowPrice={dayLow}
            />
          </div>
        </div>

        {/* Real-Time Market Analysis & Signal Engine Panel */}
        <MarketAnalysis signal={marketSignal} />

        {/* Phase 6I: Live Read-Only Shadow Engine Monitoring Panel */}
        <ShadowMonitoring />
      </main>

      {/* Bottom Footer */}
      <footer className="w-full bg-neutral-950 border-t border-neutral-900 px-4 py-3 text-center text-xs font-mono text-neutral-400">
        <div className="max-w-7xl mx-auto flex flex-wrap items-center justify-between gap-2">
          <div>
            Exness MT5 <span className="text-amber-400 font-bold">XAUUSD</span> Live Market Feed (Local-Only)
          </div>
          <div className="flex items-center gap-2">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
            <span>Read-Only Mode Active • Trading Disabled • Deterministic Analysis Engine</span>
          </div>
        </div>
      </footer>
    </div>
  );
}

