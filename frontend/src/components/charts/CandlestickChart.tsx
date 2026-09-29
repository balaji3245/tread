"use client";

import React, { useEffect, useRef, useState, useCallback } from "react";
import {
  createChart,
  IChartApi,
  ISeriesApi,
  CandlestickSeries,
  ColorType,
  UTCTimestamp,
  CandlestickData,
  CrosshairMode,
  LineStyle,
} from "lightweight-charts";
import { Candle, Timeframe } from "@/types/market";
import { BarChart3, Maximize2, RefreshCw } from "lucide-react";

interface CandlestickChartProps {
  candles: Candle[];
  timeframe: Timeframe;
  onTimeframeChange: (tf: Timeframe) => void;
  liveCandle: Candle | null;
  isLoading: boolean;
  onReload: () => void;
}

export const CandlestickChart: React.FC<CandlestickChartProps> = ({
  candles,
  timeframe,
  onTimeframeChange,
  liveCandle,
  isLoading,
  onReload,
}) => {
  const chartContainerRef = useRef<HTMLDivElement | null>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const seriesRef = useRef<ISeriesApi<"Candlestick"> | null>(null);

  const [hoveredCandle, setHoveredCandle] = useState<Candle | null>(null);

  // Initialize and configure Lightweight Charts
  useEffect(() => {
    if (!chartContainerRef.current) return;

    // Create chart
    const chart = createChart(chartContainerRef.current, {
      autoSize: true,
      layout: {
        background: { type: ColorType.Solid, color: "#09090b" },
        textColor: "#a1a1aa",
        fontSize: 12,
        fontFamily: "'Geist Mono', monospace, -apple-system, BlinkMacSystemFont",
      },
      grid: {
        vertLines: { color: "rgba(39, 39, 42, 0.4)", style: LineStyle.Dotted },
        horzLines: { color: "rgba(39, 39, 42, 0.4)", style: LineStyle.Dotted },
      },
      crosshair: {
        mode: CrosshairMode.Normal,
        vertLine: {
          color: "rgba(245, 158, 11, 0.6)",
          width: 1,
          style: LineStyle.Dashed,
          labelBackgroundColor: "#f59e0b",
        },
        horzLine: {
          color: "rgba(245, 158, 11, 0.6)",
          width: 1,
          style: LineStyle.Dashed,
          labelBackgroundColor: "#f59e0b",
        },
      },
      rightPriceScale: {
        borderColor: "rgba(39, 39, 42, 0.8)",
        scaleMargins: {
          top: 0.1,
          bottom: 0.15,
        },
      },
      timeScale: {
        borderColor: "rgba(39, 39, 42, 0.8)",
        timeVisible: true,
        secondsVisible: timeframe === "1m",
        rightOffset: 12,
        barSpacing: 8,
      },
      handleScroll: {
        mouseWheel: true,
        pressedMouseMove: true,
        horzTouchDrag: true,
        vertTouchDrag: true,
      },
      handleScale: {
        axisPressedMouseMove: true,
        mouseWheel: true,
        pinch: true,
      },
    });

    const candlestickSeries = chart.addSeries(CandlestickSeries, {
      upColor: "#10b981", // Emerald
      downColor: "#f43f5e", // Crimson
      borderVisible: false,
      wickUpColor: "#10b981",
      wickDownColor: "#f43f5e",
      priceFormat: {
        type: "price",
        precision: 2,
        minMove: 0.01,
      },
    });

    chartRef.current = chart;
    seriesRef.current = candlestickSeries;

    // Load initial candle data if already available
    if (candles && candles.length > 0) {
      const formattedData: CandlestickData<UTCTimestamp>[] = candles.map((c) => ({
        time: c.time as UTCTimestamp,
        open: c.open,
        high: c.high,
        low: c.low,
        close: c.close,
      }));
      formattedData.sort((a, b) => Number(a.time) - Number(b.time));
      const deduplicated: CandlestickData<UTCTimestamp>[] = [];
      let lastTime = 0;
      for (const item of formattedData) {
        if (Number(item.time) !== lastTime) {
          deduplicated.push(item);
          lastTime = Number(item.time);
        }
      }
      candlestickSeries.setData(deduplicated);
      chart.timeScale().fitContent();
    }

    // Crosshair move handler
    chart.subscribeCrosshairMove((param) => {
      if (
        param.point === undefined ||
        !param.time ||
        !chartContainerRef.current ||
        param.point.x < 0 ||
        param.point.x > chartContainerRef.current.clientWidth ||
        param.point.y < 0 ||
        param.point.y > chartContainerRef.current.clientHeight
      ) {
        setHoveredCandle(null);
      } else {
        const data = param.seriesData.get(candlestickSeries) as CandlestickData<UTCTimestamp> | undefined;
        if (data) {
          setHoveredCandle({
            time: Number(data.time),
            open: data.open,
            high: data.high,
            low: data.low,
            close: data.close,
          });
        }
      }
    });

    return () => {
      chart.remove();
      chartRef.current = null;
      seriesRef.current = null;
    };
  }, [timeframe]);

  // Set historical data when candles changes
  useEffect(() => {
    if (!seriesRef.current || candles.length === 0) return;

    const formattedData: CandlestickData<UTCTimestamp>[] = candles.map((c) => ({
      time: c.time as UTCTimestamp,
      open: c.open,
      high: c.high,
      low: c.low,
      close: c.close,
    }));

    // Ensure sorted by time
    formattedData.sort((a, b) => Number(a.time) - Number(b.time));

    // Deduplicate timestamps if any
    const deduplicated: CandlestickData<UTCTimestamp>[] = [];
    let lastTime = 0;
    for (const item of formattedData) {
      if (Number(item.time) !== lastTime) {
        deduplicated.push(item);
        lastTime = Number(item.time);
      }
    }

    seriesRef.current.setData(deduplicated);
    chartRef.current?.timeScale().fitContent();
  }, [candles]);

  // Real-time update for forming candle
  useEffect(() => {
    if (!seriesRef.current || !liveCandle) return;

    try {
      seriesRef.current.update({
        time: liveCandle.time as UTCTimestamp,
        open: liveCandle.open,
        high: liveCandle.high,
        low: liveCandle.low,
        close: liveCandle.close,
      });
    } catch (err) {
      console.debug("Live candle update exception (safe skip):", err);
    }
  }, [liveCandle]);

  const fitContent = useCallback(() => {
    chartRef.current?.timeScale().fitContent();
  }, []);

  // Display candle in info bar (either hovered or latest)
  const displayCandle = hoveredCandle || liveCandle || (candles.length > 0 ? candles[candles.length - 1] : null);
  const candleChange = displayCandle ? displayCandle.close - displayCandle.open : 0;
  const candleChangePct = displayCandle && displayCandle.open > 0 ? (candleChange / displayCandle.open) * 100 : 0;
  const isUp = candleChange >= 0;

  return (
    <div className="flex flex-col h-full w-full bg-neutral-950 border border-neutral-800/80 rounded-2xl overflow-hidden shadow-2xl">
      {/* Chart Toolbar */}
      <div className="flex items-center justify-between px-4 py-2.5 bg-neutral-900/80 border-b border-neutral-800 flex-wrap gap-2 text-xs">
        {/* Left: Timeframe Switcher & Title */}
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1.5 font-bold font-mono text-neutral-300">
            <BarChart3 className="w-4 h-4 text-amber-400" />
            <span>XAUUSD Chart</span>
          </div>

          <div className="flex items-center bg-neutral-950 border border-neutral-800 rounded-lg p-0.5 font-mono">
            <button
              onClick={() => onTimeframeChange("1m")}
              className={`px-3 py-1 rounded text-xs font-semibold transition cursor-pointer ${
                timeframe === "1m"
                  ? "bg-amber-500 text-neutral-950 shadow"
                  : "text-neutral-400 hover:text-white"
              }`}
            >
              1m
            </button>
            <button
              onClick={() => onTimeframeChange("5m")}
              className={`px-3 py-1 rounded text-xs font-semibold transition cursor-pointer ${
                timeframe === "5m"
                  ? "bg-amber-500 text-neutral-950 shadow"
                  : "text-neutral-400 hover:text-white"
              }`}
            >
              5m
            </button>
          </div>
        </div>

        {/* Center: Live Candle OHLC Inspector */}
        {displayCandle && (
          <div className="hidden lg:flex items-center gap-3 font-mono text-[11px] bg-neutral-950/60 px-3 py-1 rounded-md border border-neutral-800/60">
            <span className="text-neutral-400">
              O: <strong className="text-white">${displayCandle.open.toFixed(2)}</strong>
            </span>
            <span className="text-neutral-400">
              H: <strong className="text-emerald-400">${displayCandle.high.toFixed(2)}</strong>
            </span>
            <span className="text-neutral-400">
              L: <strong className="text-rose-400">${displayCandle.low.toFixed(2)}</strong>
            </span>
            <span className="text-neutral-400">
              C: <strong className="text-white">${displayCandle.close.toFixed(2)}</strong>
            </span>
            <span className={`font-bold ${isUp ? "text-emerald-400" : "text-rose-400"}`}>
              {isUp ? "+" : ""}
              {candleChange.toFixed(2)} ({isUp ? "+" : ""}
              {candleChangePct.toFixed(2)}%)
            </span>
          </div>
        )}

        {/* Right: Chart Controls */}
        <div className="flex items-center gap-1.5">
          <button
            onClick={fitContent}
            className="flex items-center gap-1 px-2.5 py-1 rounded bg-neutral-800/80 hover:bg-neutral-700 text-neutral-300 font-medium transition cursor-pointer border border-neutral-700/60"
            title="Fit content"
          >
            <Maximize2 className="w-3 h-3" />
            <span>Fit</span>
          </button>
          <button
            onClick={onReload}
            disabled={isLoading}
            className="flex items-center gap-1 px-2.5 py-1 rounded bg-neutral-800/80 hover:bg-neutral-700 text-neutral-300 font-medium transition cursor-pointer border border-neutral-700/60 disabled:opacity-50"
            title="Reload candles"
          >
            <RefreshCw className={`w-3 h-3 ${isLoading ? "animate-spin" : ""}`} />
            <span>Refresh</span>
          </button>
        </div>
      </div>

      {/* Chart Canvas Area */}
      <div className="relative flex-1 min-h-[500px] h-[560px] lg:h-[620px] w-full">
        {isLoading && (
          <div className="absolute inset-0 bg-neutral-950/70 z-10 flex items-center justify-center backdrop-blur-xs">
            <div className="flex items-center gap-2.5 bg-neutral-900 border border-neutral-800 px-4 py-2 rounded-xl text-neutral-300 font-mono text-xs shadow-xl">
              <RefreshCw className="w-4 h-4 animate-spin text-amber-400" />
              <span>Loading {timeframe} historical candles...</span>
            </div>
          </div>
        )}
        <div ref={chartContainerRef} className="absolute inset-0 w-full h-full" />
      </div>
    </div>
  );
};
