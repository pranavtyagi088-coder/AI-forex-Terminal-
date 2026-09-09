import React from 'react';
import { useCockpitStore } from '../../store/useCockpitStore';
import { Compass, Cpu, BellOff } from 'lucide-react';

export const StrategyRegimePanel: React.FC = () => {
  const { telemetry } = useCockpitStore();

  const regime = telemetry?.active_market_regime || 'DETERMINISTIC_SCAN';
  const confidence = telemetry?.regime_confidence || 85.0;
  const blackout = telemetry?.news_blackout_active || false;
  const strategies = telemetry?.active_strategies_health || {
    'trend_continuation': 'ACTIVE',
    'liquidity_sweep': 'ACTIVE',
    'mean_reversion': 'CAUTION',
  };

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-sm space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold text-slate-200 flex items-center space-x-2">
          <Compass className="w-4 h-4 text-indigo-400" />
          <span>MARKET REGIME & STRATEGY DECAY MATRIX</span>
        </h2>
        <span className="text-xs text-slate-400 font-mono">Max AI Weight: 15%</span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-xs">
        {/* Market Regime */}
        <div className="bg-slate-950/60 border border-slate-800 p-3 rounded-lg space-y-1">
          <div className="text-slate-400">Classified Regime</div>
          <div className="font-bold text-slate-100 font-mono text-sm">{regime}</div>
          <div className="text-slate-400 text-[11px]">Confidence: {confidence.toFixed(1)}%</div>
        </div>

        {/* News Blackout */}
        <div className="bg-slate-950/60 border border-slate-800 p-3 rounded-lg space-y-1">
          <div className="text-slate-400 flex items-center gap-1">
            <BellOff className="w-3.5 h-3.5 text-amber-400" /> News Blackout
          </div>
          <div className={`font-bold font-mono text-sm ${blackout ? 'text-rose-400' : 'text-emerald-400'}`}>
            {blackout ? 'BLACKOUT WINDOW ACTIVE' : 'CLEAR (TRADING PERMITTED)'}
          </div>
          <div className="text-slate-400 text-[11px]">Pre/Post 30-min Shock Guard</div>
        </div>

        {/* AI Sidecar Status */}
        <div className="bg-slate-950/60 border border-slate-800 p-3 rounded-lg space-y-1">
          <div className="text-slate-400 flex items-center gap-1">
            <Cpu className="w-3.5 h-3.5 text-indigo-400" /> AI Sidecar Posture
          </div>
          <div className="font-bold text-slate-100 font-mono text-sm">ADVISORY ONLY</div>
          <div className="text-slate-400 text-[11px]">Hallucination Guard: Fail-Closed</div>
        </div>
      </div>

      {/* Strategy Decay Badges */}
      <div className="pt-2 border-t border-slate-800 space-y-2">
        <div className="text-xs text-slate-400">Strategy Lifecycle Auto-Sync:</div>
        <div className="flex flex-wrap gap-2">
          {Object.entries(strategies).map(([stratId, status]) => (
            <div
              key={stratId}
              className={`px-3 py-1.5 rounded-lg border text-xs font-mono flex items-center space-x-2 ${
                status === 'ACTIVE'
                  ? 'bg-emerald-950/40 border-emerald-800 text-emerald-300'
                  : status === 'CAUTION'
                  ? 'bg-amber-950/40 border-amber-800 text-amber-300'
                  : 'bg-rose-950/40 border-rose-800 text-rose-300'
              }`}
            >
              <span>{stratId}</span>
              <span className="text-[10px] font-bold px-1.5 py-0.2 rounded bg-slate-900 border border-slate-800">
                {status}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
