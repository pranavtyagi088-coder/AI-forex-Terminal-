import React, { useState } from 'react';
import { Play, CheckCircle2, XCircle, AlertTriangle, ShieldCheck } from 'lucide-react';
import { api } from '../../lib/api';
import { PreFlightResponse } from '../../types/telemetry';

const CANONICAL_GATES = [
  { key: 'account_freshness', name: '1. Account Freshness' },
  { key: 'instrument_registry', name: '2. Instrument Registry' },
  { key: 'spread_guard', name: '3. Spread Guard' },
  { key: 'circuit_breaker', name: '4. Circuit Breaker' },
  { key: 'drawdown_guard', name: '5. Drawdown Guard' },
  { key: 'news_blackout', name: '6. News Blackout' },
  { key: 'strategy_health', name: '7. Strategy Health' },
  { key: 'stop_loss_geometry', name: '8. Stop Loss Geometry' },
  { key: 'correlation_exposure', name: '9. Currency Correlation' },
];

const GATE_KEY_ALIASES: Record<string, string[]> = {
  account_freshness: ['account_freshness'],
  instrument_registry: ['instrument_supported', 'instrument_registry'],
  spread_guard: ['spread_guard'],
  circuit_breaker: ['circuit_breaker'],
  drawdown_guard: ['prop_firm_drawdown', 'drawdown_guard'],
  news_blackout: ['news_and_calendar', 'news_blackout'],
  strategy_health: ['strategy_health'],
  stop_loss_geometry: ['stop_loss_geometry'],
  correlation_exposure: ['portfolio_correlation', 'correlation_exposure'],
};

export const PreFlightTerminal: React.FC = () => {
  const [symbol, setSymbol] = useState('EURUSD');
  const [direction, setDirection] = useState<'BUY' | 'SELL'>('BUY');
  const [entryPrice, setEntryPrice] = useState(1.085);
  const [stopLoss, setStopLoss] = useState(1.082);
  const [accountBalance, setAccountBalance] = useState(100000);
  const [riskPct, setRiskPct] = useState(1.0);
  const [spreadPips, setSpreadPips] = useState(1.2);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<PreFlightResponse | null>(null);

  const handleEvaluate = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      const res = await api.evaluatePreFlight({
        symbol,
        direction,
        entry_price: Number(entryPrice),
        stop_loss: Number(stopLoss),
        account_balance: Number(accountBalance),
        risk_per_trade_pct: Number(riskPct),
        current_spread_pips: Number(spreadPips),
      });
      setResult(res);
    } catch (err: any) {
      setError(err?.message || 'Pre-flight evaluation failed.');
    } finally {
      setLoading(false);
    }
  };

  const getGateStatus = (gateKey: string): { exists: boolean; passed: boolean } => {
    if (!result || !result.gate_checks) return { exists: false, passed: false };
    
    const possibleKeys = GATE_KEY_ALIASES[gateKey] || [gateKey];
    for (const k of possibleKeys) {
      if (k in result.gate_checks) {
        return { exists: true, passed: Boolean(result.gate_checks[k]) };
      }
    }
    return { exists: false, passed: false };
  };

  return (
    <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-5 shadow-xl backdrop-blur-md">
      <div className="flex items-center justify-between mb-4 border-b border-slate-800 pb-3">
        <div className="flex items-center gap-2">
          <ShieldCheck className="w-5 h-5 text-indigo-400" />
          <h2 className="text-sm font-semibold tracking-wider text-slate-200 uppercase">
            9-Gate Pre-Flight Evaluator
          </h2>
        </div>
        <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
          Deterministic Sizing
        </span>
      </div>

      <form onSubmit={handleEvaluate} className="space-y-4">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-xs font-mono">
          <div>
            <label className="block text-slate-400 text-[10px] uppercase mb-1">Symbol</label>
            <select
              value={symbol}
              onChange={(e) => setSymbol(e.target.value)}
              className="w-full bg-slate-950 border border-slate-800 rounded px-2.5 py-1.5 text-slate-200 focus:outline-none focus:border-indigo-500"
            >
              <option value="EURUSD">EURUSD</option>

              <option value="GBPUSD">GBPUSD</option>
              <option value="USDJPY">USDJPY</option>
              <option value="AUDUSD">AUDUSD</option>
              <option value="XAUUSD">XAUUSD</option>
            </select>
          </div>

          <div>
            <label className="block text-slate-400 text-[10px] uppercase mb-1">Direction</label>
            <select
              value={direction}
              onChange={(e) => setDirection(e.target.value as 'BUY' | 'SELL')}
              className="w-full bg-slate-950 border border-slate-800 rounded px-2.5 py-1.5 text-slate-200 focus:outline-none focus:border-indigo-500"
            >
              <option value="BUY">BUY (LONG)</option>
              <option value="SELL">SELL (SHORT)</option>
            </select>
          </div>

          <div>
            <label className="block text-slate-400 text-[10px] uppercase mb-1">Entry Price</label>
            <input
              type="number"
              step="0.00001"
              value={entryPrice}
              onChange={(e) => setEntryPrice(Number(e.target.value))}
              className="w-full bg-slate-950 border border-slate-800 rounded px-2.5 py-1.5 text-slate-200 focus:outline-none focus:border-indigo-500"
            />
          </div>

          <div>
            <label className="block text-slate-400 text-[10px] uppercase mb-1">Stop Loss</label>
            <input
              type="number"
              step="0.00001"
              value={stopLoss}
              onChange={(e) => setStopLoss(Number(e.target.value))}
              className="w-full bg-slate-950 border border-slate-800 rounded px-2.5 py-1.5 text-slate-200 focus:outline-none focus:border-indigo-500"
            />
          </div>

          <div>
            <label className="block text-slate-400 text-[10px] uppercase mb-1">Account Balance ($)</label>
            <input
              type="number"
              value={accountBalance}
              onChange={(e) => setAccountBalance(Number(e.target.value))}
              className="w-full bg-slate-950 border border-slate-800 rounded px-2.5 py-1.5 text-slate-200 focus:outline-none focus:border-indigo-500"
            />
          </div>

          <div>
            <label className="block text-slate-400 text-[10px] uppercase mb-1">Risk Per Trade (%)</label>
            <input
              type="number"
              step="0.1"
              value={riskPct}
              onChange={(e) => setRiskPct(Number(e.target.value))}
              className="w-full bg-slate-950 border border-slate-800 rounded px-2.5 py-1.5 text-slate-200 focus:outline-none focus:border-indigo-500"
            />
          </div>

          <div>
            <label className="block text-slate-400 text-[10px] uppercase mb-1">Current Spread (pips)</label>
            <input
              type="number"
              step="0.1"
              value={spreadPips}
              onChange={(e) => setSpreadPips(Number(e.target.value))}
              className="w-full bg-slate-950 border border-slate-800 rounded px-2.5 py-1.5 text-slate-200 focus:outline-none focus:border-indigo-500"
            />
          </div>

          <div className="flex items-end">
            <button
              type="submit"
              disabled={loading}
              className="w-full bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white font-semibold py-1.5 px-3 rounded text-xs transition flex items-center justify-center gap-1.5 shadow-lg shadow-indigo-600/20"
            >
              <Play className="w-3.5 h-3.5 fill-current" />
              <span>{loading ? 'EVALUATING...' : 'RUN 9-GATE EVAL'}</span>
            </button>
          </div>
        </div>
      </form>

      {error && (
        <div className="mt-4 p-3 bg-rose-500/10 border border-rose-500/30 rounded-lg text-rose-400 text-xs flex items-center gap-2">
          <AlertTriangle className="w-4 h-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {result && (
        <div className="mt-5 space-y-4 font-mono">
          <div
            className={`p-4 rounded-xl border ${
              result.allowed
                ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-300'
                : 'bg-rose-500/10 border-rose-500/30 text-rose-300'
            }`}
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                {result.allowed ? (
                  <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0" />
                ) : (
                  <XCircle className="w-5 h-5 text-rose-400 shrink-0" />
                )}
                <div>
                  <div className="text-xs font-bold tracking-wide uppercase">
                    {result.allowed
                      ? 'TRADE APPROVED BY PRE-FLIGHT GATEKEEPER'
                      : 'TRADE VETOED / BLOCKED (NO_TRADE DECISION)'}
                  </div>
                  {result.rejection_reasons && result.rejection_reasons.length > 0 && (
                    <div className="text-[11px] text-rose-400 mt-1 font-sans">
                      Reason: {result.rejection_reasons.join(', ')}
                    </div>
                  )}
                </div>
              </div>

              {result.decision_id && (
                <div className="text-[10px] text-slate-400 font-mono text-right">
                  <span># SHA-256: </span>
                  <span className="text-slate-200">{result.decision_id}</span>
                </div>
              )}
            </div>

            <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mt-3 pt-3 border-t border-slate-800/80 text-xs">
              <div>
                <span className="text-slate-400 text-[10px] block uppercase">Approved Lot Size</span>
                <span className="font-bold text-slate-100">{result.approved_lot_size ?? 0}</span>
              </div>
              <div>
                <span className="text-slate-400 text-[10px] block uppercase">Risk USD</span>
                <span className="font-bold text-slate-100">${result.risk_amount_usd?.toFixed(2) ?? '0.00'}</span>
              </div>
              <div>
                <span className="text-slate-400 text-[10px] block uppercase">Risk/Reward</span>
                <span className="font-bold text-slate-100">{result.reward_risk_ratio ? `${result.reward_risk_ratio}:1` : 'N/A'}</span>
              </div>
              <div>
                <span className="text-slate-400 text-[10px] block uppercase">Data Status</span>
                <span className="font-bold text-indigo-400">{result.account_data_status || 'DETERMINISTIC'}</span>
              </div>
            </div>
          </div>

          <div>
            <div className="text-xs font-semibold text-slate-300 mb-2 uppercase tracking-wider text-[10px]">
              Individual Gate Breakdown (Authoritative Checks):
            </div>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-2 text-xs">
              {CANONICAL_GATES.map((g) => {
                const { exists, passed } = getGateStatus(g.key);
                return (
                  <div
                    key={g.key}
                    className={`p-2.5 rounded-lg border flex items-center justify-between ${
                      !exists
                        ? 'bg-slate-950/40 border-slate-800 text-slate-500'
                        : passed
                        ? 'bg-emerald-950/30 border-emerald-800/50 text-emerald-300'
                        : 'bg-rose-950/30 border-rose-800/50 text-rose-300'
                    }`}
                  >
                    <span className="truncate pr-2 font-sans font-medium text-[11px]">{g.name}</span>
                    <span
                      className={`text-[10px] font-mono font-bold px-1.5 py-0.5 rounded ${
                        !exists
                          ? 'bg-slate-800 text-slate-400'
                          : passed
                          ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                          : 'bg-rose-500/20 text-rose-400 border border-rose-500/30'
                      }`}
                    >
                      {!exists ? 'UNAVAILABLE' : passed ? 'PASS' : 'FAIL'}
                    </span>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};