export type EventSeverity = 'INFO' | 'WARN' | 'WARNING' | 'ERROR' | 'CRITICAL' | 'EMERGENCY' | 'DEBUG';

export interface TerminalEvent {
  event_id: string;
  type: string;
  severity: EventSeverity;
  source: string;
  source_module?: string;
  message: string;
  symbol?: string | null;
  payload: Record<string, any>;
  timestamp: number;
}

export interface GateCheckResult {
  passed: boolean;
  reason?: string;
  metadata?: Record<string, any>;
}

export interface PreFlightRequest {
  symbol: string;
  direction: 'BUY' | 'SELL';
  entry_price: number;
  stop_loss: number;
  take_profit?: number;
  account_balance: number;
  risk_per_trade_pct?: number;
  open_positions?: Array<{ symbol: string; direction: string; lot_size: number; unrealized_pnl?: number }>;
  current_daily_drawdown_pct?: number;
  current_total_drawdown_pct?: number;
  current_spread_pips?: number;
  account_data_status?: string;
  strategy_id?: string;
  ai_confidence?: number;
}

export interface PreFlightResponse {
  allowed: boolean;
  canonical_symbol: string;
  approved_lot_size: number;
  risk_amount_usd: number;
  potential_reward_usd?: number;
  risk_reward_ratio?: number;
  decision_id: string;
  integrity_hash: string;
  gate_checks: Record<string, GateCheckResult>;
  rejection_reasons: string[];
  warnings: string[];
  account_data_status: string;
}

export interface CockpitTelemetrySnapshot {
  account_balance?: number;
  daily_pnl?: number;
  current_daily_drawdown_pct?: number;
  current_total_drawdown_pct?: number;
  max_daily_drawdown_pct?: number;
  max_total_drawdown_pct?: number;
  circuit_breaker_active: boolean;
  circuit_breaker_reason?: string;
  active_market_regime?: string;
  regime_confidence?: number;
  news_blackout_active?: boolean;
  active_open_trades_count?: number;
  total_cluster_exposure_pct?: Record<string, number>;
  active_strategies_health?: Record<string, 'ACTIVE' | 'CAUTION' | 'DEGRADED' | 'RETIRED' | 'SUSPENDED'>;
  sweep_intelligence?: SweepIntelligenceData;
  recent_events?: TerminalEvent[];
  last_updated?: number;
}

export interface SweepIntelligenceData {
  sweep_detected: boolean;
  active_symbol?: string;
  bias?: 'FADE_BUY' | 'FADE_SELL' | 'NEUTRAL';
  sweep_depth_pips?: number;
  wick_ratio?: number;
  volume_spike?: number;
  confidence?: number;
  evidence_weight?: number;
}
