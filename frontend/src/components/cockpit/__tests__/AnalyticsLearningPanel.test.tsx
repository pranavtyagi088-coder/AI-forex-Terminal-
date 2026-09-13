import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import React from 'react';
import { AnalyticsLearningPanel } from '../AnalyticsLearningPanel';
import { api } from '../../../lib/api';

function renderWithClient(ui: React.ReactElement) {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false, refetchOnWindowFocus: false } },
  });
  return render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>);
}

describe('AnalyticsLearningPanel', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('renders header, metrics cards, and fallback state gracefully', async () => {
    vi.spyOn(api, 'getRollingMetrics').mockResolvedValue({
      total_trades: 0,
      winning_trades: 0,
      losing_trades: 0,
      win_rate_pct: 0.0,
      profit_factor: 0.0,
      expectancy_usd: 0.0,
      average_r_multiple: 0.0,
      sharpe_ratio: 0.0,
      sortino_ratio: 0.0,
      calmar_ratio: 0.0,
      max_drawdown_pct: 0.0,
      max_drawdown_usd: 0.0,
      consecutive_losses_max: 0,
      total_pnl_usd: 0.0,
      is_statistically_significant: false,
    });
    vi.spyOn(api, 'getSlippageReport').mockResolvedValue({
      total_analyzed_trades: 0,
      average_slippage_pips: 0.0,
      max_adverse_slippage_pips: 0.0,
      adverse_execution_rate_pct: 0.0,
      favorable_execution_rate_pct: 0.0,
      zero_slippage_rate_pct: 0.0,
      total_slippage_cost_usd: 0.0,
      execution_quality_score: 100.0,
    });
    vi.spyOn(api, 'getStrategyWeights').mockResolvedValue([]);

    renderWithClient(<AnalyticsLearningPanel />);

    expect(screen.getByText(/CLOSED-LOOP QUANTITATIVE POST-MORTEM/i)).toBeInTheDocument();
    expect(screen.getByText(/SAMPLE SIZE < 15/i)).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText(/ANNUALIZED SHARPE/i)).toBeInTheDocument();
      expect(screen.getByText(/FILL QUALITY SCORE/i)).toBeInTheDocument();
    });
  });

  it('displays calculated ratios and dynamic strategy weights when data is present', async () => {
    vi.spyOn(api, 'getRollingMetrics').mockResolvedValue({
      total_trades: 25,
      winning_trades: 18,
      losing_trades: 7,
      win_rate_pct: 72.0,
      profit_factor: 2.45,
      expectancy_usd: 350.0,
      average_r_multiple: 1.6,
      sharpe_ratio: 1.85,
      sortino_ratio: 2.40,
      calmar_ratio: 3.10,
      max_drawdown_pct: 2.15,
      max_drawdown_usd: 2150.0,
      consecutive_losses_max: 2,
      total_pnl_usd: 8750.0,
      is_statistically_significant: true,
    });
    vi.spyOn(api, 'getSlippageReport').mockResolvedValue({
      total_analyzed_trades: 25,
      average_slippage_pips: 0.12,
      max_adverse_slippage_pips: 0.40,
      adverse_execution_rate_pct: 12.0,
      favorable_execution_rate_pct: 24.0,
      zero_slippage_rate_pct: 64.0,
      total_slippage_cost_usd: 30.0,
      execution_quality_score: 93.0,
    });
    vi.spyOn(api, 'getStrategyWeights').mockResolvedValue([
      {
        strategy_id: '1',
        strategy_name: 'Liquidity Sweep Momentum',
        current_status: 'ACTIVE',
        recommended_status: 'ACTIVE',
        risk_multiplier: 1.0,
        rebalance_reason: 'Optimal risk-adjusted performance',
        is_throttled: false,
      },
      {
        strategy_id: '2',
        strategy_name: 'Asian Range Fade',
        current_status: 'ACTIVE',
        recommended_status: 'CAUTION',
        risk_multiplier: 0.5,
        rebalance_reason: 'Caution: Sub-optimal Sortino',
        is_throttled: true,
      },
    ]);

    renderWithClient(<AnalyticsLearningPanel />);

    await waitFor(() => {
      expect(screen.getByText(/STATISTICALLY RELIABLE/i)).toBeInTheDocument();
      expect(screen.getByText('1.85')).toBeInTheDocument();
      expect(screen.getByText('2.40')).toBeInTheDocument();
      expect(screen.getByText('93/100')).toBeInTheDocument();
      expect(screen.getByText(/Liquidity Sweep Momentum/i)).toBeInTheDocument();
      expect(screen.getByText(/Asian Range Fade/i)).toBeInTheDocument();
      expect(screen.getByText('0.50x')).toBeInTheDocument();
    });
  });
});
