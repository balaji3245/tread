export const getBackendUrl = (): string => {
  if (process.env.NEXT_PUBLIC_BACKEND_URL) {
    return process.env.NEXT_PUBLIC_BACKEND_URL;
  }
  if (typeof window !== "undefined") {
    // In browser: use current origin (makes all API calls relative/same-origin)
    return window.location.origin;
  }
  return "http://127.0.0.1:8000";
};

export const getWsUrl = (): string => {
  if (process.env.NEXT_PUBLIC_WS_URL) {
    return process.env.NEXT_PUBLIC_WS_URL;
  }
  if (typeof window !== "undefined") {
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    return `${protocol}//${window.location.host}/ws/market/xauusd`;
  }
  return "ws://127.0.0.1:8000/ws/market/xauusd";
};

export const BACKEND_URL = getBackendUrl();
export const WS_URL = getWsUrl();

export const STALE_DATA_THRESHOLD_SECONDS = 5.0;

