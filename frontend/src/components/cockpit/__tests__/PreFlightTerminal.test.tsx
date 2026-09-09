import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import React from 'react';
import { PreFlightTerminal } from '../PreFlightTerminal';
import { api } from '../../../lib/api';

describe('PreFlightTerminal Component', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('renders pre-flight input fields and header', () => {
    render(<PreFlightTerminal />);

    // Verify presence of core UI titles & buttons
    expect(screen.getByText(/9-GATE PRE-FLIGHT EVALUATOR/i)).toBeInTheDocument();
    expect(screen.getByText(/Symbol/i)).toBeInTheDocument();
    expect(screen.getByText(/Entry Price/i)).toBeInTheDocument();
    expect(screen.getByText(/Stop Loss/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /RUN 9-GATE EVAL/i })).toBeInTheDocument();
  });

  it('displays APPROVED verdict and 9-gate checks when all gates pass', async () => {
    const approvedResponse = {
      allowed: true,
      canonical_symbol: 'EURUSD',
      approved_lot_size: 1.5,
      risk_amount_usd: 500,
      decision_id: 'a1b2c3d4e5f67890abcdef1234567890abcdef1234567890abcdef1234567890',
      rejection_reasons: [],
      gate_checks: {
        account_freshness: { passed: true, detail: 'Fresh account metrics within 10s' },
        instrument_registry: { passed: true, detail: 'EURUSD specs validated' },
        spread_guard: { passed: true, detail: 'Spread 0.8 pips <= max 2.5' },
        circuit_breaker: { passed: true, detail: 'Circuit breaker normal' },
        drawdown_guard: { passed: true, detail: 'Daily DD 0.5% within 4% limit' },
        news_blackout: { passed: true, detail: 'No high-impact news in window' },
        strategy_health: { passed: true, detail: 'Strategy active and healthy' },
        stop_loss_geometry: { passed: true, detail: 'SL geometry valid 15 pips' },
        correlation_exposure: { passed: true, detail: 'USD cluster at 1.5% <= 3.0%' },
      },
      timestamp: Date.now() / 1000,
    };

    vi.spyOn(api, 'evaluatePreFlight').mockResolvedValue(approvedResponse as any);

    render(<PreFlightTerminal />);

    const evalButton = screen.getByRole('button', { name: /RUN 9-GATE EVAL/i });
    fireEvent.click(evalButton);

    await waitFor(() => {
      expect(screen.getByText(/TRADE APPROVED BY PRE-FLIGHT GATEKEEPER/i)).toBeInTheDocument();
      expect(screen.getByText(/a1b2c3d4e5f6/i)).toBeInTheDocument();
      // Individual gate matrix rendered
      expect(screen.getByText(/1. Account Freshness/i)).toBeInTheDocument();
      expect(screen.getByText(/3. Spread Guard/i)).toBeInTheDocument();
    });
  });

  it('displays REJECTED verdict and failure reasons when gate rejects', async () => {
    const rejectedResponse = {
      allowed: false,
      canonical_symbol: 'EURUSD',
      approved_lot_size: 0,
      risk_amount_usd: 0,
      decision_id: '9999c3d4e5f67890abcdef1234567890abcdef1234567890abcdef1234567890',
      rejection_reasons: ['Spread Guard: Spread 4.5 pips exceeds max 2.5 pips limit'],
      gate_checks: {
        account_freshness: { passed: true, detail: 'Fresh account metrics' },
        instrument_registry: { passed: true, detail: 'EURUSD specs validated' },
        spread_guard: { passed: false, detail: 'Spread 4.5 pips exceeds limit 2.5' },
        circuit_breaker: { passed: true, detail: 'Circuit breaker normal' },
        drawdown_guard: { passed: true, detail: 'Daily DD within limit' },
        news_blackout: { passed: true, detail: 'Clear' },
        strategy_health: { passed: true, detail: 'Healthy' },
        stop_loss_geometry: { passed: true, detail: 'SL valid' },
        correlation_exposure: { passed: true, detail: 'Exposure normal' },
      },
      timestamp: Date.now() / 1000,
    };

    vi.spyOn(api, 'evaluatePreFlight').mockResolvedValue(rejectedResponse as any);

    render(<PreFlightTerminal />);

    const evalButton = screen.getByRole('button', { name: /RUN 9-GATE EVAL/i });
    fireEvent.click(evalButton);

    await waitFor(() => {
      expect(screen.getByText(/TRADE VETOED \/ BLOCKED \(NO_TRADE DECISION\)/i)).toBeInTheDocument();
      expect(screen.getByText(/Spread Guard: Spread 4.5 pips exceeds max 2.5 pips limit/i)).toBeInTheDocument();
    });
  });
});
