import React, { useState } from 'react';
import { api, NormalizedApiError } from '../../lib/api';
import { PreFlightRequest, PreFlightResponse } from '../../types/telemetry';
import { CheckCircle2, XCircle, AlertTriangle, Play, Shield, Hash, RefreshCw } from 'lucide-react';

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

export const PreFlightTerminal: React.FC = () => {
  const [form, setForm] = useState<PreFlightRequest>({
    symbol: 'EURUSD',
    direction: 'BUY',
    entry_price: 1.0850,
    stop_loss: 1.0820,
    take_profit: 1.0910,
    account_balance: 100000,
    risk_per_trade_pct: 1.0,
    current_spread_pips: 1.2,
    current_daily_drawdown_pct: 0.0,
    current_total_drawdown_pct: 0.0,
    open_positions: [],
  });

  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<PreFlightResponse | null>(null);
  const [error, setError] = useState<NormalizedApiError | null>(null);

  const handleEvaluate = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    const payload: PreFlightRequest = {
      ...form,
      entry_price: Number(form.entry_price),
      stop_loss: Number(form.stop_loss),
      take_profit: form.take_profit ? Number(form.take_profit) : undefined,
      account_balance: Number(form.account_balance),
      risk_per_trade_pct: Number(form.risk_per_trade_pct),
      current_spread_pips: Number(form.current_spread_pips),
    };

    try {
      const res = await api.evaluatePreFlight(payload);
      setResult(res);
    } catch (err: any) {
      if (err instanceof NormalizedApiError) {
        setError(err);
      } else {
        setError(new NormalizedApiError(err.message || 'Unhandled Evaluation Error', 500, 'evaluatePreFlight'));
      }
      setResult(null);
    } finally {
      setLoading(false);
    }
  };

  const getGateStatus = (gateKey: string): { exists: boolean; passed: boolean } => {
    if (!result || !result.gate_checks) return { exists: false, passed: false };
    if (gateKey in result.gate_checks) {
      const val = result.gate_checks[gateKey];
      const isPassed = typeof val === 'boolean' ? val : (val as any)?.passed ?? false;
      return { exists: true, passed: isPassed };
    }
    return { exists: false, passed: false };
  };

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-sm space-y-5">
      <div className="flex items-center justify-between border-b border-slate-800 pb-3">
        <h2 className="text-sm font-semibold text-slate-200 flex items-center space-x-2">
          <Shield className="w-4 h-4 text-indigo-400" />
          <span>9-GATE PRE-FLIGHT EVALUATOR</span>
        </h2>
        <span className="text-xs px-2.5 py-0.5 rounded bg-slate-800 text-slate-300 font-mono">
          Deterministic Sizing
        </span>
      </div>

      <form onSubmit={handleEvaluate} className="grid grid-cols-2 md:grid-cols-4 gap-3 text-xs">
        <div>
          <label className="text-slate-400 mb-1 block">Symbol</label>
          <select
            value={form.symbol}
            onChange={(e) => setForm({ ...form, symbol: e.target.value })}
            className="w-full bg-slate-950 border border-slate-800 rounded px-2.5 py-1.5 text-slate-200 font-mono"
          >
            <option value="EURUSD">EURUSD</option>
            <option value="GBPUSD">GBPUSD</option>
            <option value="USDJPY">USDJPY</option>
            <option value="XAUUSD">XAUUSD</option>
            <option value="NAS100">NAS100</option>
          </select>
        </div>

        <div>
          <label className="text-slate-400 mb-1 block">Direction</label>
          <select
            value={form.direction}
            onChange={(e) => setForm({ ...form, direction: e.target.value as 'BUY' | 'SELL' })}
            className="w-full bg-slate-950 border border-slate-800 rounded px-2.5 py-1.5 text-slate-200 font-bold"
          >
            <option value="BUY">BUY (LONG)</option>
            <option value="SELL">SELL (SHORT)</option>
          </select>
        </div>

        <div>
          <label className="text-slate-400 mb-1 block">Entry Price</label>
          <input
            type="number"
            step="any"
            value={form.entry_price}
            onChange={(e) => setForm({ ...form, entry_price: parseFloat(e.target.value) || 0 })}
            className="w-full bg-slate-950 border border-slate-800 rounded px-2.5 py-1.5 text-slate-200 font-mono"
          />
        </div>

        <div>
          <label className="text-slate-400 mb-1 block">Stop Loss</label>
          <input
            type="number"
            step="any"
            value={form.stop_loss}
            onChange={(e) => setForm({ ...form, stop_loss: parseFloat(e.target.value) || 0 })}
            className="w-full bg-slate-950 border border-slate-800 rounded px-2.5 py-1.5 text-slate-200 font-mono"
          />
        </div>

        <div>
          <label className="text-slate-400 mb-1 block">Account Balance ($)</label>
          <input
            type="number"
            value={form.account_balance}
            onChange={(e) => setForm({ ...form, account_balance: parseFloat(e.target.value) || 0 })}
            className="w-full bg-slate-950 border border-slate-800 rounded px-2.5 py-1.5 text-slate-200 font-mono"
          />
        </div>

        <div>
          <label className="text-slate-400 mb-1 block">Risk Per Trade (%)</label>
          <input
            type="number"
            step="0.1"
            value={form.risk_per_trade_pct}
            onChange={(e) => setForm({ ...form, risk_per_trade_pct: parseFloat(e.target.value) || 0 })}
            className="w-full bg-slate-950 border border-slate-800 rounded px-2.5 py-1.5 text-slate-200 font-mono"
          />
        </div>

        <div>
          <label className="text-slate-400 mb-1 block">Current Spread (pips)</label>
          <input
            type="number"
            step="0.1"
            value={form.current_spread_pips}
            onChange={(e) => setForm({ ...form, current_spread_pips: parseFloat(e.target.value) || 0 })}
            className="w-full bg-slate-950 border border-slate-800 rounded px-2.5 py-1.5 text-slate-200 font-mono"
          />
        </div>

        <div className="flex items-end">
          <button
            type="submit"
            disabled={loading}
            className="w-full bg-indigo-600 hover:bg-indigo-700 text-white font-semibold py-1.5 px-3 rounded flex items-center justify-center space-x-1.5 shadow transition-colors"
          >
            {loading ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <Play className="w-3.5 h-3.5" />}
            <span>{loading ? 'EVALUATING...' : 'RUN 9-GATE EVAL'}</span>
          </button>
        </div>
      </form>

      {/* TYPED API ERROR CARD (No [object Object]) */}
      {error && (
        <div className="p-4 bg-rose-950/80 border border-rose-700 text-rose-200 rounded-lg text-xs space-y-1 font-mono">
          <div className="flex items-center space-x-2 font-bold text-rose-300">
            <AlertTriangle className="w-4 h-4 shrink-0 text-rose-400" />
            <span>PRE-FLIGHT EVALUATION ERROR (HTTP {error.status || 500})</span>
          </div>
          <div className="text-slate-300 pl-6">{error.message}</div>
          {error.endpoint && <div className="text-slate-500 text-[10px] pl-6">Endpoint: {error.endpoint}</div>}
        </div>
      )}

      {/* AUTHORITATIVE 9-GATE RESULTS & MATRIX */}
      {result && (
        <div className="space-y-4 pt-2">
          <div className={`p-4 rounded-lg border text-xs space-y-3 ${
            result.allowed 
              ? 'bg-emerald-950/40 border-emerald-800/80 text-emerald-200' 
              : 'bg-rose-950/40 border-rose-800/80 text-rose-200'
          }`}>
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-2">
                {result.allowed ? (
                  <CheckCircle2 className="w-5 h-5 text-emerald-400" />
                ) : (
                  <XCircle className="w-5 h-5 text-rose-400" />
                )}
                <span className="font-bold text-sm">
                  {result.allowed ? 'TRADE APPROVED BY PRE-FLIGHT GATEKEEPER' : 'TRADE VETOED / BLOCKED (NO_TRADE DECISION)'}
                </span>
              </div>
              <div className="font-mono text-slate-400 flex items-center gap-1 text-[11px]">
                <Hash className="w-3.5 h-3.5" /> SHA-256: {result.decision_id?.slice(0, 14)}...
              </div>
            </div>

            <div className="grid grid-cols-2 md:grid-cols-4 gap-2 pt-2 border-t border-slate-800/80 font-mono">
              <div>Approved Lot Size: <span className="font-bold text-slate-100">{result.approved_lot_size}</span></div>
              <div>Risk USD: <span className="font-bold text-slate-100">${result.risk_amount_usd?.toFixed(2)}</span></div>
              <div>Risk/Reward: <span className="font-bold text-slate-100">{result.risk_reward_ratio ? result.risk_reward_ratio.toFixed(2) : 'N/A'}</span></div>
              <div>Data Status: <span className="font-bold text-slate-100">{result.account_data_status || 'FRESH'}</span></div>
            </div>

            {result.rejection_reasons?.length > 0 && (
              <div className="text-rose-300 space-y-1 pt-2 border-t border-slate-800/60">
                <div className="font-semibold">Rejection Violations:</div>
                <ul className="list-disc list-inside space-y-0.5">
                  {result.rejection_reasons.map((r, idx) => (
                    <li key={idx}>{r}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>

          {/* INDIVIDUAL 9-GATE MATRIX */}
          <div className="space-y-2">
            <div className="text-xs font-semibold text-slate-300">INDIVIDUAL GATE BREAKDOWN (AUTHORITATIVE CHECKS):</div>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-2">
              {CANONICAL_GATES.map((g) => {
                const { exists, passed } = getGateStatus(g.key);

                return (
                  <div
                    key={g.key}
                    className={`p-2.5 rounded-lg border font-mono text-xs flex items-center justify-between ${
                      !exists
                        ? 'bg-slate-950 border-slate-800 text-slate-500'
                        : passed
                        ? 'bg-emerald-950/20 border-emerald-800/60 text-emerald-300'
                        : 'bg-rose-950/30 border-rose-800/80 text-rose-300'
                    }`}
                  >
                    <span className="font-bold">{g.name}</span>
                    <span className={`px-2 py-0.5 text-[10px] font-bold rounded border ${
                      !exists
                        ? 'bg-slate-900 border-slate-700 text-slate-400'
                        : passed
                        ? 'bg-emerald-900/60 border-emerald-700 text-emerald-200'
                        : 'bg-rose-900/60 border-rose-700 text-rose-200'
                    }`}>
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
