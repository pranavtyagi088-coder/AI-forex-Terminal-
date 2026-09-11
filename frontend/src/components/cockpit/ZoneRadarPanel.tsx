import React from 'react';
import { Layers, ShieldCheck, Flame, Clock } from 'lucide-react';
import { useCockpitStore } from '../../store/useCockpitStore';

export const ZoneRadarPanel: React.FC = () => {
  const telemetry = useCockpitStore((s) => s.telemetry);
  const zoneData = telemetry?.zone_intelligence;

  if (!zoneData || zoneData.status === 'UNAVAILABLE' || !zoneData.top_zones?.length) {
    return (
      <div className="bg-[#131722] border border-[#2A2E39] rounded-lg p-4 font-mono text-xs text-slate-400 flex flex-col justify-between">
        <div className="flex items-center justify-between border-b border-[#2A2E39] pb-2">
          <div className="flex items-center space-x-2">
            <Layers className="w-4 h-4 text-cyan-400" />
            <span className="font-semibold text-slate-200 tracking-wider">LIQUIDITY ZONE RADAR</span>
          </div>
          <span className="px-2 py-0.5 rounded text-[10px] bg-slate-800 text-slate-400 border border-slate-700">UNAVAILABLE</span>
        </div>
        <div className="py-6 text-center text-slate-500">
          No institutional-zone candidates currently identified.
        </div>
      </div>
    );
  }

  return (
    <div className="bg-[#131722] border border-[#2A2E39] rounded-lg p-4 font-mono text-xs text-slate-300 flex flex-col justify-between shadow-lg">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-[#2A2E39] pb-2">
        <div className="flex items-center space-x-2">
          <Layers className="w-4 h-4 text-cyan-400 animate-pulse" />
          <span className="font-semibold text-slate-100 tracking-wider uppercase">LIQUIDITY ZONE RADAR</span>
        </div>
        <div className="flex items-center space-x-2">
          <span className="text-[10px] text-slate-400">Weight: {(zoneData.evidence_weight * 100).toFixed(0)}%</span>
          <span className="px-2 py-0.5 rounded text-[10px] bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
            ACTIVE
          </span>
        </div>
      </div>

      {/* Top Zones List */}
      <div className="space-y-2 my-3">
        {zoneData.top_zones.slice(0, 3).map((zone, idx) => {
          const isBull = zone.zone_type.includes('BULLISH');
          const isOB = zone.zone_type.includes('ORDER_BLOCK');
          const typeLabel = isOB ? 'OB' : 'FVG';

          return (
            <div
              key={idx}
              className={`p-2 rounded border transition-colors ${
                isBull
                  ? 'bg-emerald-950/20 border-emerald-800/40 hover:border-emerald-700/60'
                  : 'bg-rose-950/20 border-rose-800/40 hover:border-rose-700/60'
              }`}
            >
              <div className="flex items-center justify-between mb-1">
                <div className="flex items-center space-x-1.5">
                  <span
                    className={`px-1.5 py-0.5 rounded text-[9px] font-bold ${
                      isBull ? 'bg-emerald-500/20 text-emerald-300' : 'bg-rose-500/20 text-rose-300'
                    }`}
                  >
                    {isBull ? 'BULL' : 'BEAR'} {typeLabel}
                  </span>
                  <span className="text-[10px] text-slate-300">
                    {zone.low.toFixed(4)} - {zone.high.toFixed(4)}
                  </span>
                </div>
                <div className="flex items-center space-x-1">
                  <Flame className="w-3 h-3 text-amber-400" />
                  <span className="text-[10px] font-bold text-amber-400">{zone.score.toFixed(0)} pts</span>
                </div>
              </div>

              <div className="flex items-center justify-between text-[10px] text-slate-400 pt-1 border-t border-slate-800/60">
                <div className="flex items-center space-x-1">
                  <ShieldCheck className="w-3 h-3 text-slate-400" />
                  <span>Touches: {zone.touches} {zone.is_mitigated ? '(Mitigated)' : '(Fresh)'}</span>
                </div>
                <div className="flex items-center space-x-1">
                  <Clock className="w-3 h-3 text-slate-500" />
                  <span>{zone.bars_since_creation} bars ago</span>
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Footer Note */}
      <div className="text-[9px] text-slate-500 text-right italic">
        Deterministic candidate ranking • Sidecar weight capped @ ≤15%
      </div>
    </div>
  );
};
