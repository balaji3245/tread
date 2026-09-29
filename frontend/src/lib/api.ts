import { BACKEND_URL } from "./config";
import { AnalysisResponse, Candle, HealthStatus, SymbolInfo, Timeframe } from "@/types/market";

export async function fetchHealth(): Promise<HealthStatus> {
  const res = await fetch(`${BACKEND_URL}/health`, { cache: "no-store" });
  if (!res.ok) {
    throw new Error(`Failed to fetch health status: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchCandles(timeframe: Timeframe, count: number = 300): Promise<Candle[]> {
  const res = await fetch(
    `${BACKEND_URL}/api/market/xauusd/candles?timeframe=${timeframe}&count=${count}`,
    { cache: "no-store" }
  );
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    const message = errorData.detail?.message || `Failed to fetch candles (${res.statusText})`;
    throw new Error(message);
  }
  const data = await res.json();
  return data.candles || [];
}

export async function fetchSymbolInfo(): Promise<SymbolInfo> {
  const res = await fetch(`${BACKEND_URL}/api/market/xauusd/info`, {
    cache: "no-store",
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    const message = errorData.detail?.message || `Failed to fetch symbol info (${res.statusText})`;
    throw new Error(message);
  }
  return res.json();
}

export async function fetchAnalysis(): Promise<AnalysisResponse> {
  const res = await fetch(`${BACKEND_URL}/api/market/xauusd/analysis`, {
    cache: "no-store",
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    const message = errorData.detail?.message || `Failed to fetch market analysis (${res.statusText})`;
    throw new Error(message);
  }
  return res.json();
}

export async function runBacktest(config: import("@/types/market").BacktestConfig): Promise<import("@/types/market").BacktestResponse> {
  const res = await fetch(`${BACKEND_URL}/api/backtest/xauusd`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(config),
    cache: "no-store",
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    const message = errorData.detail?.message || `Backtest failed (${res.statusText})`;
    throw new Error(message);
  }
  return res.json();
}

export async function runValidation(
  config: import("@/types/market").ValidationRequest
): Promise<import("@/types/market").ValidationResponse> {
  const res = await fetch(`${BACKEND_URL}/api/validation/xauusd`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(config),
    cache: "no-store",
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    const message = errorData.detail?.message || `Strategy validation failed (${res.statusText})`;
    throw new Error(message);
  }
  return res.json();
}

export async function exportValidation(
  config?: import("@/types/market").ValidationRequest
): Promise<import("@/types/market").ValidationExportResponse> {
  const res = await fetch(`${BACKEND_URL}/api/validation/xauusd/export`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: config ? JSON.stringify(config) : undefined,
    cache: "no-store",
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    const message = errorData.detail?.message || `Validation export failed (${res.statusText})`;
    throw new Error(message);
  }
  return res.json();
}

export async function fetchHistoryStatus(): Promise<import("@/types/market").HistoryStatusResponse> {
  const res = await fetch(`${BACKEND_URL}/api/history/xauusd/status`, {
    cache: "no-store",
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    const message = errorData.detail?.message || `Failed to fetch history status (${res.statusText})`;
    throw new Error(message);
  }
  return res.json();
}

export async function downloadHistory(params: {
  symbol?: string;
  months?: number;
  start?: string;
  end?: string;
  force_refresh?: boolean;
}): Promise<any> {
  const res = await fetch(`${BACKEND_URL}/api/history/xauusd/download`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(params),
    cache: "no-store",
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    const message = errorData.detail?.message || `Failed to download history (${res.statusText})`;
    throw new Error(message);
  }
  return res.json();
}

export async function fetchForensicsSummary(): Promise<{ success: boolean; report: import("@/types/market").ForensicsReport }> {
  const res = await fetch(`${BACKEND_URL}/api/forensics/summary`, {
    cache: "no-store",
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    const message = errorData.detail?.message || `Failed to fetch forensics report (${res.statusText})`;
    throw new Error(message);
  }
  const data = await res.json();
  if (data.report_id) {
    return { success: true, report: data };
  }
  return data;
}

export async function fetchForensicsFailures(): Promise<{ success: boolean; count: number; categories: import("@/types/market").FailureCategorySummary[] }> {
  const res = await fetch(`${BACKEND_URL}/api/forensics/failures`, {
    cache: "no-store",
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    const message = errorData.detail?.message || `Failed to fetch failure categories (${res.statusText})`;
    throw new Error(message);
  }
  const data = await res.json();
  if (Array.isArray(data)) {
    return { success: true, count: data.length, categories: data };
  }
  return data;
}

export async function fetchForensicsHypotheses(): Promise<{ success: boolean; count: number; hypotheses: import("@/types/market").CandidateHypothesisItem[] }> {
  const res = await fetch(`${BACKEND_URL}/api/forensics/hypotheses`, {
    cache: "no-store",
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    const message = errorData.detail?.message || `Failed to fetch candidate hypotheses (${res.statusText})`;
    throw new Error(message);
  }
  const data = await res.json();
  if (Array.isArray(data)) {
    return { success: true, count: data.length, hypotheses: data };
  }
  return data;
}

export async function fetchExperimentsList(): Promise<{ success: boolean; count: number; experiments: import("@/types/market").ExperimentResult[] }> {
  const res = await fetch(`${BACKEND_URL}/api/experiments/list`, {
    cache: "no-store",
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    const message = errorData.detail?.message || `Failed to fetch experiments list (${res.statusText})`;
    throw new Error(message);
  }
  const data = await res.json();
  if (Array.isArray(data)) {
    return { success: true, count: data.length, experiments: data };
  }
  return data;
}

export async function fetchExperimentDetail(id: string): Promise<{ success: boolean; experiment: import("@/types/market").ExperimentResult }> {
  const res = await fetch(`${BACKEND_URL}/api/experiments/${id}`, {
    cache: "no-store",
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    const message = errorData.detail?.message || `Failed to fetch experiment ${id} (${res.statusText})`;
    throw new Error(message);
  }
  const data = await res.json();
  if (data.experiment_id) {
    return { success: true, experiment: data };
  }
  return data;
}

export async function runExperiments(experimentId?: string): Promise<{ success: boolean; results: import("@/types/market").ExperimentResult[] }> {
  const url = experimentId ? `${BACKEND_URL}/api/experiments/run?experiment_id=${encodeURIComponent(experimentId)}` : `${BACKEND_URL}/api/experiments/run`;
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    cache: "no-store",
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    const message = errorData.detail?.message || `Failed to run experiments (${res.statusText})`;
    throw new Error(message);
  }
  const data = await res.json();
  if (Array.isArray(data)) {
    return { success: true, results: data };
  }
  return data;
}

export async function fetchExperimentAudit(id: string): Promise<{ success: boolean; audit: import("@/types/market").ExperimentAuditReport }> {
  const res = await fetch(`${BACKEND_URL}/api/experiments/audit/${encodeURIComponent(id)}`, {
    cache: "no-store",
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    const message = errorData.detail?.message || `Failed to fetch audit for experiment ${id} (${res.statusText})`;
    throw new Error(message);
  }
  const data = await res.json();
  if (data.experiment_id) {
    return { success: true, audit: data };
  }
  return data;
}

export async function triggerExperimentAudit(id: string): Promise<{ success: boolean; audit: import("@/types/market").ExperimentAuditReport }> {
  const res = await fetch(`${BACKEND_URL}/api/experiments/audit/${encodeURIComponent(id)}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    cache: "no-store",
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    const message = errorData.detail?.message || `Failed to run audit for experiment ${id} (${res.statusText})`;
    throw new Error(message);
  }
  const data = await res.json();
  if (data.experiment_id) {
    return { success: true, audit: data };
  }
  return data;
}

export async function fetchExcursionsForensics(): Promise<import("@/types/market").ExcursionsForensicReport> {
  const res = await fetch(`${BACKEND_URL}/api/forensics/excursions`, {
    cache: "no-store",
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    const message = errorData.detail?.message || `Failed to fetch excursions report (${res.statusText})`;
    throw new Error(message);
  }
  return res.json();
}

export async function fetchEntryQualityForensics(): Promise<any> {
  const res = await fetch(`${BACKEND_URL}/api/forensics/entry-quality`, {
    cache: "no-store",
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    const message = errorData.detail?.message || `Failed to fetch entry quality report (${res.statusText})`;
    throw new Error(message);
  }
  return res.json();
}

export async function fetchHoldingTimeForensics(): Promise<any> {
  const res = await fetch(`${BACKEND_URL}/api/forensics/holding-time`, {
    cache: "no-store",
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    const message = errorData.detail?.message || `Failed to fetch holding time report (${res.statusText})`;
    throw new Error(message);
  }
  return res.json();
}

export async function fetchExitPaths(count: number = 20): Promise<{ count: number; samples: import("@/types/market").ExitPathSample[] }> {
  const res = await fetch(`${BACKEND_URL}/api/forensics/exit-paths?count=${count}`, {
    cache: "no-store",
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    const message = errorData.detail?.message || `Failed to fetch exit paths (${res.statusText})`;
    throw new Error(message);
  }
  return res.json();
}

export async function fetchShadowStatus(): Promise<any> {
  const res = await fetch(`${BACKEND_URL}/api/shadow/status`, { cache: "no-store" });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    const message = errorData.detail?.message || `Failed to fetch shadow status (${res.statusText})`;
    throw new Error(message);
  }
  return res.json();
}

export async function fetchShadowJournal(limit: number = 50): Promise<any[]> {
  const res = await fetch(`${BACKEND_URL}/api/shadow/journal?limit=${limit}`, { cache: "no-store" });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    const message = errorData.detail?.message || `Failed to fetch shadow journal (${res.statusText})`;
    throw new Error(message);
  }
  return res.json();
}

export async function fetchShadowSummary(): Promise<any> {
  const res = await fetch(`${BACKEND_URL}/api/shadow/summary`, { cache: "no-store" });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    const message = errorData.detail?.message || `Failed to fetch shadow summary (${res.statusText})`;
    throw new Error(message);
  }
  return res.json();
}

