
export interface PropFirmPreset {
  id: string;
  name: string;
  daily_drawdown_pct: number;
  max_drawdown_pct: number;
  drawdown_type: string;
  max_loss_basis: string;
  profit_target_pct: number;
  allow_weekend_holding: boolean;
  allow_news_trading: boolean;
  news_blackout_minutes: number;
  max_open_risk_pct: number;
}

export interface RadarSignal {
  id: string;
  symbol: string;
  timeframe: string;
  direction: string;
  strategy_name: string;
  strategy_id: string;
  score: number;
  rr_ratio: number;
  entry_price: number;
  stop_loss: number;
  take_profit: number;
  regime: string;
  session: string;
  detected_at: string;
  status: string;
}

export interface ScannerStatus {
  status: string;
  watchlist: string[];
  total_active_signals: number;
  last_scan_at: string | null;
}

export interface WebhookAlertItem {
  id: string;
  symbol: string;
  timeframe: string;
  event: string;
  price: number;
  atr: number;
  suggested_direction: string;
  regime: string;
  session: string;
  received_at: string;
  status: string;
}
export interface BacktestMetrics {
  total_trades: number;
  winning_trades: number;
  losing_trades: number;
  win_rate: number;
  profit_factor: number;
  expectancy_r: number;
  expectancy_usd: number;
  max_drawdown: number;
  max_drawdown_pct: number;
  net_profit: number;
  net_profit_pct: number;
  sharpe_ratio: number;
  avg_rr: number;
  consecutive_losses: number;
  total_bars: number;
}

export interface TradeLogItem {
  entry_bar: number;
  exit_bar: number;
  direction: string;
  entry_price: number;
  exit_price: number;
  pnl: number;
  pnl_pct: number;
  r_multiple: number;
  exit_reason: string;
}

export interface BacktestResponse {
  status: string;
  symbol: string;
  timeframe: string;
  strategy: string;
  metrics: BacktestMetrics;
  trade_log: TradeLogItem[];
  equity_curve: number[];
  drawdown_curve: number[];
  is_metrics?: BacktestMetrics | null;
  oos_metrics?: BacktestMetrics | null;
  data_source: string;
  data_quality?: Record<string, any> | null;
  slippage_pips_used: number;
  commission_per_lot_used: number;
}

export interface StrategyComparisonItem {
  strategy: string;
  metrics: BacktestMetrics;
  equity_curve: number[];
  drawdown_curve: number[];
}

export interface StrategyComparisonResponse {
  status: string;
  symbol: string;
  timeframe: string;
  data_source: string;
  total_bars: number;
  comparisons: StrategyComparisonItem[];
}

const API_BASE = "http://localhost:8000";

export async function runAnalysis(formData: FormData) {
  const res = await fetch(`${API_BASE}/api/analysis/run`, {
    method: "POST",
    body: formData,
  });
  if (!res.ok) throw new Error(`Analysis failed: ${res.status}`);
  return res.json();
}

export const api = {
  runAnalysis,

  getTrades: async () => {
    const res = await fetch(`${API_BASE}/api/journal/trades`);
    if (!res.ok) throw new Error(`Fetch trades failed: ${res.status}`);
    return res.json();
  },

  createTrade: async (tradeData: any) => {
    const res = await fetch(`${API_BASE}/api/journal/trades`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(tradeData),
    });
    if (!res.ok) throw new Error(`Create trade failed: ${res.status}`);
    return res.json();
  },

  deleteTrade: async (id: number) => {
    const res = await fetch(`${API_BASE}/api/journal/trades/${id}`, {
      method: "DELETE",
    });
    if (!res.ok) throw new Error(`Delete trade failed: ${res.status}`);
    return res.json();
  },

  runBacktest: async (req: any): Promise<BacktestResponse> => {
    const res = await fetch(`${API_BASE}/api/backtest/run`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(req),
    });
    if (!res.ok) throw new Error(`Backtest failed: ${res.status}`);
    return res.json();
  },

  runBacktestWithCsv: async (formData: FormData): Promise<BacktestResponse> => {
    const res = await fetch(`${API_BASE}/api/backtest/run-csv`, {
      method: "POST",
      body: formData,
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: "CSV Backtest failed" }));
      throw new Error(err.detail || `Backtest failed with status ${res.status}`);
    }
    return res.json();
  },

  compareStrategies: async (req: any): Promise<StrategyComparisonResponse> => {
    const res = await fetch(`${API_BASE}/api/backtest/compare`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(req),
    });
    if (!res.ok) throw new Error(`Comparison failed: ${res.status}`);
    return res.json();
  },

  getPropPresets: async (): Promise<PropFirmPreset[]> => {
    const res = await fetch(`${API_BASE}/api/prop-firm/presets`);
    if (!res.ok) return [];
    return res.json();
  },

  getPropAccount: async () => {
    const res = await fetch(`${API_BASE}/api/prop-firm/account`);
    if (!res.ok) throw new Error("Failed to fetch prop account");
    return res.json();
  },

  getWebhookAlerts: async (): Promise<WebhookAlertItem[]> => {
    const res = await fetch(`${API_BASE}/api/webhooks/alerts`);
    if (!res.ok) return [];
    return res.json();
  },

  clearWebhookAlerts: async () => {
    const res = await fetch(`${API_BASE}/api/webhooks/alerts/clear`, { method: "POST" });
    return res.json();
  },

  getRadarSignals: async (): Promise<RadarSignal[]> => {
    const res = await fetch(`${API_BASE}/api/scanner/signals`);
    if (!res.ok) return [];
    return res.json();
  },

  triggerScanNow: async () => {
    const res = await fetch(`${API_BASE}/api/scanner/scan-now`, { method: "POST" });
    if (!res.ok) throw new Error("Scan trigger failed");
    return res.json();
  },

  dismissRadarSignal: async (signalId: string) => {
    const res = await fetch(`${API_BASE}/api/scanner/signals/dismiss/${signalId}`, { method: "POST" });
    return res.json();
  },

  checkPropCompliance: async (tradeReq: any) => {
    const res = await fetch(`${API_BASE}/api/prop-firm/check-compliance`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(tradeReq),
    });
    if (!res.ok) throw new Error("Compliance check failed");
    return res.json();
  },
};
