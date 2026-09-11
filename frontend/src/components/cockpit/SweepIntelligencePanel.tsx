import React from 'react';
import { ShieldAlert, Crosshair, TrendingUp, TrendingDown, Activity } from 'lucide-react';
import { useCockpitStore } from '../../store/useCockpitStore';

export const SweepIntelligencePanel: React.FC = () => {
  const telemetry = useCockpitStore((state) => state.telemetry);
  const sweep = telemetry?.sweep_intelligence;

  const isSweepActive = sweep?.sweep_detected ?? false;
  const bias = sweep?.bias ?? 'NEUTRAL';
  const confidence = sweep?.confidence ? (sweep.confidence * 100).toFixed(0) : '0';
  const depth = sweep?.sweep_depth_pips?.toFixed(1) ?? '0.0';
  const wickRatio = sweep?.wick_ratio ? (sweep.wick_ratio * 100).toFixed(0) : '0';
  const volSpike = sweep?.volume_spike?.toFixed(1) ?? '1.0';
  const evidenceWeight = sweep?.evidence_weight ? (sweep.evidence_weight * 100).toFixed(0) : '0';

  return (
    <div className="bg-[#131722] border border-[#2a2e39] rounded-xl p-5 text-gray-200 shadow-lg">
      {/* Header */}
      <div className="flex items-center justify-between pb-3 border-b border-[#2a2e39]">
        <div className="flex items-center space-x-2">
          <Crosshair className="w-5 h-5 text-cyan-400" />
          <h3 className="font-semibold tracking-wide text-sm uppercase text-gray-100">
            Liquidity Sweep Radar
          </h3>
        </div>
        <div className="flex items-center space-x-2">
          <span className="text-xs px-2.5 py-0.5 rounded-full font-mono bg-cyan-950/80 text-cyan-400 border border-cyan-800/60">
            {sweep?.active_symbol || 'EURUSD'}
          </span>
          {isSweepActive ? (
            <span className="flex items-center text-xs px-2.5 py-0.5 rounded-full font-bold bg-amber-950/80 text-amber-400 border border-amber-700/60 animate-pulse">
              <ShieldAlert className="w-3.5 h-3.5 mr-1" />
              SWEEP ACTIVE
            </span>
          ) : (
            <span className="text-xs px-2.5 py-0.5 rounded-full font-medium bg-gray-800 text-gray-400">
              STABLE
            </span>
          )}
        </div>
      </div>

      {/* Main Metrics Grid */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 my-4">
        <div className="bg-[#1e222d] p-3 rounded-lg border border-[#2a2e39]/60">
          <div className="text-[11px] text-gray-400 font-medium">Bias / Direction</div>
          <div className="flex items-center mt-1">
            {bias === 'FADE_BUY' ? (
              <span className="text-emerald-400 font-bold text-sm flex items-center">
                <TrendingUp className="w-4 h-4 mr-1" /> FADE BUY
              </span>
            ) : bias === 'FADE_SELL' ? (
              <span className="text-rose-400 font-bold text-sm flex items-center">
                <TrendingDown className="w-4 h-4 mr-1" /> FADE SELL
              </span>
            ) : (
              <span className="text-gray-400 font-bold text-sm">NEUTRAL</span>
            )}
          </div>
        </div>

        <div className="bg-[#1e222d] p-3 rounded-lg border border-[#2a2e39]/60">
          <div className="text-[11px] text-gray-400 font-medium">Sweep Depth</div>
          <div className="text-sm font-mono font-bold text-cyan-300 mt-1">
            {depth} <span className="text-xs font-normal text-gray-400">pips</span>
          </div>
        </div>

        <div className="bg-[#1e222d] p-3 rounded-lg border border-[#2a2e39]/60">
          <div className="text-[11px] text-gray-400 font-medium">Wick Rejection</div>
          <div className="text-sm font-mono font-bold text-purple-300 mt-1">
            {wickRatio}%
          </div>
        </div>

        <div className="bg-[#1e222d] p-3 rounded-lg border border-[#2a2e39]/60">
          <div className="text-[11px] text-gray-400 font-medium">Volume Spike</div>
          <div className="text-sm font-mono font-bold text-amber-300 mt-1">
            {volSpike}x <span className="text-xs font-normal text-gray-400">avg</span>
          </div>
        </div>
      </div>

      {/* Evidence & Confidence Footer */}
      <div className="flex items-center justify-between pt-3 border-t border-[#2a2e39]/60 text-xs">
        <div className="flex items-center space-x-2 text-gray-400">
          <Activity className="w-3.5 h-3.5 text-cyan-400" />
          <span>Confidence: <strong className="text-gray-200">{confidence}%</strong></span>
        </div>
        <div className="text-gray-400">
          Evidence Weight: <strong className="text-cyan-400">{evidenceWeight}%</strong> <span className="text-[10px] text-gray-500">(max 15% cap)</span>
        </div>
      </div>
    </div>
  );
};
