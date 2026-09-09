import React from 'react';
import { useCockpitStore } from '../../store/useCockpitStore';
import { AlertCircle, TrendingDown, Layers, DollarSign } from 'lucide-react';

export const RiskRadarGauges: React.FC = () => {
  const { telemetry } = useCockpitStore();

  const dailyDd = telemetry?.current_daily_drawdown_pct;
  const maxDailyDd = telemetry?.max_daily_drawdown_pct ?? 4.0;
  const totalDd = telemetry?.current_total_drawdown_pct;
  const maxTotalDd = telemetry?.max_total_drawdown_pct ?? 8.0;
  const balance = telemetry?.account_balance;

  const hasDailyDd = dailyDd !== undefined && dailyDd !== null;
  const hasTotalDd = totalDd !== undefined && totalDd !== null;
  const hasBalance = balance !== undefined && balance !== null;

  const dailyRatio = hasDailyDd ? Math.min((dailyDd / maxDailyDd) * 100, 100) : 0;
  const totalRatio = hasTotalDd ? Math.min((totalDd / maxTotalDd) * 100, 100) : 0;

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-sm space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold text-slate-200 flex items-center space-x-2">
          <Layers className="w-4 h-4 text-indigo-400" />
          <span>INSTITUTIONAL RISK RADAR</span>
        </h2>
        <span className="text-xs text-slate-400 font-mono">Fail-Closed Limits</span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Account Balance */}
        <div className="bg-slate-950/60 border border-slate-800/80 p-4 rounded-lg space-y-1">
          <div className="text-xs text-slate-400 flex items-center gap-1">
            <DollarSign className="w-3.5 h-3.5 text-emerald-400" /> Account Balance
          </div>
          <div className="text-base font-bold font-mono text-slate-100">
            {hasBalance ? `$${balance.toLocaleString(undefined, { minimumFractionDigits: 2 })}` : 'UNAVAILABLE'}
          </div>
        </div>

        {/* Daily Drawdown Gauge */}
        <div className="bg-slate-950/60 border border-slate-800/80 p-4 rounded-lg space-y-2">
          <div className="flex justify-between items-center text-xs">
            <span className="text-slate-400 flex items-center gap-1">
              <TrendingDown className="w-3.5 h-3.5 text-amber-400" /> Daily Drawdown
            </span>
            <span className="font-mono font-bold text-slate-200">
              {hasDailyDd ? `${dailyDd.toFixed(2)}% / ${maxDailyDd.toFixed(2)}%` : 'UNAVAILABLE'}
            </span>
          </div>
          <div className="w-full bg-slate-800 rounded-full h-2 overflow-hidden">
            <div
              className={`h-full transition-all duration-500 ${
                dailyRatio > 75 ? 'bg-rose-500' : dailyRatio > 50 ? 'bg-amber-500' : 'bg-emerald-500'
              }`}
              style={{ width: `${hasDailyDd ? dailyRatio : 0}%` }}
            />
          </div>
        </div>

        {/* Total Trailing Drawdown Gauge */}
        <div className="bg-slate-950/60 border border-slate-800/80 p-4 rounded-lg space-y-2">
          <div className="flex justify-between items-center text-xs">
            <span className="text-slate-400 flex items-center gap-1">
              <AlertCircle className="w-3.5 h-3.5 text-rose-400" /> Maximum Trailing DD
            </span>
            <span className="font-mono font-bold text-slate-200">
              {hasTotalDd ? `${totalDd.toFixed(2)}% / ${maxTotalDd.toFixed(2)}%` : 'UNAVAILABLE'}
            </span>
          </div>
          <div className="w-full bg-slate-800 rounded-full h-2 overflow-hidden">
            <div
              className={`h-full transition-all duration-500 ${
                totalRatio > 75 ? 'bg-rose-500' : totalRatio > 50 ? 'bg-amber-500' : 'bg-emerald-500'
              }`}
              style={{ width: `${hasTotalDd ? totalRatio : 0}%` }}
            />
          </div>
        </div>
      </div>

      {/* Currency Cluster Exposure */}
      {telemetry?.total_cluster_exposure_pct && Object.keys(telemetry.total_cluster_exposure_pct).length > 0 && (
        <div className="pt-2 border-t border-slate-800">
          <div className="text-xs text-slate-400 mb-2">Currency Cluster Exposure (Limit: 3.0% / currency):</div>
          <div className="flex flex-wrap gap-2">
            {Object.entries(telemetry.total_cluster_exposure_pct).map(([ccy, exp]) => (
              <span
                key={ccy}
                className={`text-xs font-mono px-2.5 py-1 rounded border ${
                  exp > 2.5
                    ? 'bg-rose-950/80 border-rose-700 text-rose-300'
                    : 'bg-slate-800 border-slate-700 text-slate-300'
                }`}
              >
                {ccy}: {exp.toFixed(2)}%
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
