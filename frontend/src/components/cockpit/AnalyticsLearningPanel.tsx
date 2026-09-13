import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { api } from '../../lib/api';
import {
  TrendingUp,
  Activity,
  Gauge,
  Sliders,
  AlertTriangle,
  CheckCircle2,
  Percent,
} from 'lucide-react';
import {
  RollingPerformanceMetrics,
  SlippagePostMortem,
  StrategyWeightAllocation,
} from '../../types/telemetry';

export const AnalyticsLearningPanel: React.FC = () => {
  const { data: metrics, isLoading: loadingMetrics } = useQuery<RollingPerformanceMetrics>({
    queryKey: ['rolling-metrics'],
    queryFn: () => api.getRollingMetrics(),
    refetchInterval: 10000,
  });

  const { data: slippage, isLoading: loadingSlippage } = useQuery<SlippagePostMortem>({
    queryKey: ['slippage-report'],
    queryFn: () => api.getSlippageReport(),
    refetchInterval: 10000,
  });

  const { data: weights, isLoading: loadingWeights } = useQuery<StrategyWeightAllocation[]>({
    queryKey: ['strategy-weights'],
    queryFn: () => api.getStrategyWeights(),
    refetchInterval: 10000,
  });

  return (
    <div className="bg-[#161b22] border border-[#30363d] rounded-xl p-5 shadow-lg space-y-5">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-[#30363d]/80 pb-4">
        <div className="flex items-center space-x-3">
          <div className="p-2 bg-indigo-950/60 border border-indigo-700/50 rounded-lg text-indigo-400">
            <Activity className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <h3 className="font-bold text-sm text-gray-100 tracking-wide uppercase">
                Closed-Loop Quantitative Post-Mortem & Adaptive Rebalancer
              </h3>
              <span className="px-2 py-0.5 text-[10px] font-mono rounded bg-cyan-950 text-cyan-400 border border-cyan-800/60">
                P3 FEEDBACK
              </span>
            </div>
            <p className="text-xs text-gray-400 font-mono">
              Deterministic rolling risk metrics, downside volatility Sortino, and automated risk allocation throttling.
            </p>
          </div>
        </div>

        {/* Statistical Significance Badge */}
        <div className="flex items-center space-x-2 font-mono text-xs">
          {metrics?.is_statistically_significant ? (
            <span className="flex items-center space-x-1 px-2.5 py-1 rounded bg-emerald-950/80 border border-emerald-700/50 text-emerald-400 text-[11px]">
              <CheckCircle2 className="w-3.5 h-3.5" />
              <span>STATISTICALLY RELIABLE (N &ge; 15)</span>
            </span>
          ) : (
            <span className="flex items-center space-x-1 px-2.5 py-1 rounded bg-amber-950/50 border border-amber-700/40 text-amber-300 text-[11px]">
              <AlertTriangle className="w-3.5 h-3.5" />
              <span>SAMPLE SIZE &lt; 15 (OBSERVATION)</span>
            </span>
          )}
        </div>
      </div>

      {/* Metrics 4-Card Grid */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 font-mono">
        {/* Sharpe & Sortino */}
        <div className="bg-[#0d1117] border border-[#30363d] rounded-lg p-3 space-y-1">
          <div className="text-[11px] text-gray-400 flex items-center justify-between">
            <span>ANNUALIZED SHARPE</span>
            <TrendingUp className="w-3.5 h-3.5 text-cyan-400" />
          </div>
          <div className="text-xl font-bold text-gray-100">
            {loadingMetrics ? '...' : (metrics?.sharpe_ratio ?? 0.0).toFixed(2)}
          </div>
          <div className="text-[10px] text-gray-400 flex justify-between pt-1 border-t border-[#21262d]">
            <span>SORTINO (DOWNSIDE):</span>
            <span className="font-semibold text-emerald-400">
              {loadingMetrics ? '...' : (metrics?.sortino_ratio ?? 0.0).toFixed(2)}
            </span>
          </div>
        </div>

        {/* Win Rate & Profit Factor */}
        <div className="bg-[#0d1117] border border-[#30363d] rounded-lg p-3 space-y-1">
          <div className="text-[11px] text-gray-400 flex items-center justify-between">
            <span>WIN RATE</span>
            <Percent className="w-3.5 h-3.5 text-emerald-400" />
          </div>
          <div className="text-xl font-bold text-gray-100">
            {loadingMetrics ? '...' : `${(metrics?.win_rate_pct ?? 0.0).toFixed(1)}%`}
          </div>
          <div className="text-[10px] text-gray-400 flex justify-between pt-1 border-t border-[#21262d]">
            <span>PROFIT FACTOR:</span>
            <span className="font-semibold text-cyan-400">
              {loadingMetrics ? '...' : (metrics?.profit_factor ?? 0.0).toFixed(2)}
            </span>
          </div>
        </div>

        {/* Slippage & Execution Quality */}
        <div className="bg-[#0d1117] border border-[#30363d] rounded-lg p-3 space-y-1">
          <div className="text-[11px] text-gray-400 flex items-center justify-between">
            <span>FILL QUALITY SCORE</span>
            <Gauge className="w-3.5 h-3.5 text-indigo-400" />
          </div>
          <div className="text-xl font-bold text-indigo-300">
            {loadingSlippage ? '...' : `${(slippage?.execution_quality_score ?? 100).toFixed(0)}/100`}
          </div>
          <div className="text-[10px] text-gray-400 flex justify-between pt-1 border-t border-[#21262d]">
            <span>AVG SLIPPAGE:</span>
            <span className="font-semibold text-gray-300">
              {loadingSlippage ? '...' : `${(slippage?.average_slippage_pips ?? 0.0).toFixed(2)} pips`}
            </span>
          </div>
        </div>

        {/* Drawdown & Expectancy */}
        <div className="bg-[#0d1117] border border-[#30363d] rounded-lg p-3 space-y-1">
          <div className="text-[11px] text-gray-400 flex items-center justify-between">
            <span>MAX DRAWDOWN</span>
            <AlertTriangle className="w-3.5 h-3.5 text-rose-400" />
          </div>
          <div className="text-xl font-bold text-rose-400">
            {loadingMetrics ? '...' : `${(metrics?.max_drawdown_pct ?? 0.0).toFixed(2)}%`}
          </div>
          <div className="text-[10px] text-gray-400 flex justify-between pt-1 border-t border-[#21262d]">
            <span>CALMAR RATIO:</span>
            <span className="font-semibold text-gray-300">
              {loadingMetrics ? '...' : (metrics?.calmar_ratio ?? 0.0).toFixed(2)}
            </span>
          </div>
        </div>
      </div>

      {/* Adaptive Rebalancer Strategy Weights */}
      <div className="space-y-2">
        <div className="flex items-center space-x-2 text-xs font-bold text-gray-300 uppercase tracking-wider">
          <Sliders className="w-3.5 h-3.5 text-cyan-400" />
          <span>Dynamic Risk Weight Allocations</span>
        </div>

        <div className="bg-[#0d1117] border border-[#30363d] rounded-lg overflow-hidden">
          {loadingWeights ? (
            <div className="p-4 text-xs font-mono text-gray-400 text-center">Loading adaptive weights...</div>
          ) : !weights || weights.length === 0 ? (
            <div className="p-4 text-xs font-mono text-gray-500 text-center">
              No registered strategies currently undergoing live feedback loop.
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left font-mono text-xs">
                <thead>
                  <tr className="bg-[#161b22] border-b border-[#30363d] text-gray-400">
                    <th className="py-2 px-3">Strategy</th>
                    <th className="py-2 px-3">Status</th>
                    <th className="py-2 px-3">Risk Multiplier</th>
                    <th className="py-2 px-3">Degradation Reason</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#21262d]">
                  {weights.map((w) => (
                    <tr key={w.strategy_id} className="hover:bg-[#161b22]/50 transition-colors">
                      <td className="py-2.5 px-3 font-semibold text-gray-200">{w.strategy_name}</td>
                      <td className="py-2.5 px-3">
                        <span
                          className={`px-2 py-0.5 text-[10px] font-bold rounded ${
                            w.recommended_status === 'ACTIVE'
                              ? 'bg-emerald-950 text-emerald-400 border border-emerald-800'
                              : w.recommended_status === 'CAUTION'
                              ? 'bg-amber-950 text-amber-400 border border-amber-800'
                              : w.recommended_status === 'DEGRADED'
                              ? 'bg-orange-950 text-orange-400 border border-orange-800'
                              : 'bg-rose-950 text-rose-400 border border-rose-800'
                          }`}
                        >
                          {w.recommended_status}
                        </span>
                      </td>
                      <td className="py-2.5 px-3 font-bold text-cyan-400">
                        {w.risk_multiplier.toFixed(2)}x
                      </td>
                      <td className="py-2.5 px-3 text-gray-400 text-[11px] truncate max-w-xs">
                        {w.rebalance_reason}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
