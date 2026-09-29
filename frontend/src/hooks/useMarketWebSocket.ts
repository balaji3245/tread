"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import { WS_URL } from "@/lib/config";
import { ConnectionState, MarketTick, Candle, Timeframe, WsStatusData, WsMessage, MarketSignal } from "@/types/market";

interface UseMarketWebSocketOptions {
  onTick?: (tick: MarketTick) => void;
  onCandle?: (timeframe: Timeframe, candle: Candle) => void;
  onStatus?: (status: WsStatusData) => void;
  onAnalysis?: (signal: MarketSignal) => void;
}

export function useMarketWebSocket(options: UseMarketWebSocketOptions = {}) {
  const [connectionState, setConnectionState] = useState<ConnectionState>("CONNECTING");
  const [mt5Status, setMt5Status] = useState<WsStatusData>({
    mt5_connected: false,
    symbol: null,
    is_mock: false,
    message: "Initializing MT5 connection...",
  });
  const [lastMessageTime, setLastMessageTime] = useState<number>(0);
  const [reconnectAttempt, setReconnectAttempt] = useState<number>(0);

  const optionsRef = useRef(options);
  optionsRef.current = options;

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const backoffRef = useRef<number>(1000); // starts at 1s
  const isManuallyClosedRef = useRef<boolean>(false);

  const connect = useCallback(() => {
    if (wsRef.current && (wsRef.current.readyState === WebSocket.OPEN || wsRef.current.readyState === WebSocket.CONNECTING)) {
      return;
    }

    try {
      setConnectionState((prev) => (prev === "DISCONNECTED" ? "RECONNECTING" : "CONNECTING"));
      const ws = new WebSocket(WS_URL);
      wsRef.current = ws;

      ws.onopen = () => {
        setConnectionState("CONNECTED");
        backoffRef.current = 1000; // Reset backoff on success
        setReconnectAttempt(0);
      };

      ws.onmessage = (event) => {
        try {
          const now = Date.now();
          setLastMessageTime(now);

          const msg: WsMessage = JSON.parse(event.data);
          if (msg.type === "tick") {
            optionsRef.current.onTick?.(msg.data);
          } else if (msg.type === "candle") {
            optionsRef.current.onCandle?.(msg.timeframe, msg.data);
          } else if (msg.type === "status") {
            setMt5Status(msg.data);
            optionsRef.current.onStatus?.(msg.data);
          } else if (msg.type === "analysis") {
            optionsRef.current.onAnalysis?.(msg.data.signal);
          }
        } catch (err) {
          console.error("Error parsing WebSocket message:", err);
        }
      };

      ws.onerror = (event) => {
        console.warn("WebSocket encountered an error:", event);
      };

      ws.onclose = () => {
        if (isManuallyClosedRef.current) return;

        setConnectionState("DISCONNECTED");
        const nextDelay = Math.min(backoffRef.current * 2, 30000);
        const currentDelay = backoffRef.current;
        backoffRef.current = nextDelay;

        setReconnectAttempt((prev) => prev + 1);

        if (reconnectTimeoutRef.current) {
          clearTimeout(reconnectTimeoutRef.current);
        }

        reconnectTimeoutRef.current = setTimeout(() => {
          connect();
        }, currentDelay);
      };
    } catch (err) {
      console.error("WebSocket connection failure:", err);
      setConnectionState("DISCONNECTED");
    }
  }, []);

  const manualReconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
    }
    if (wsRef.current) {
      wsRef.current.close();
    }
    backoffRef.current = 1000;
    connect();
  }, [connect]);

  useEffect(() => {
    isManuallyClosedRef.current = false;
    connect();

    return () => {
      isManuallyClosedRef.current = true;
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [connect]);

  return {
    connectionState,
    mt5Status,
    lastMessageTime,
    reconnectAttempt,
    manualReconnect,
  };
}
