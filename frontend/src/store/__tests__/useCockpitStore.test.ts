import { describe, it, expect, beforeEach, vi } from 'vitest';
import { useCockpitStore } from '../useCockpitStore';
import { TerminalEvent, CockpitTelemetrySnapshot } from '../../types/telemetry';
import { api } from '../../lib/api';

describe('useCockpitStore', () => {
  beforeEach(() => {
    // Reset store state before each test
    useCockpitStore.setState({
      wsConnected: false,
      clientId: null,
      lastPingTimestamp: null,
      telemetry: null,
      telemetryLoading: false,
      telemetryError: null,
      events: [],
      circuitBreakerTripped: false,
      circuitBreakerReason: null,
    });
  });

  it('adds events and caps ring buffer at 200 items', () => {
    const store = useCockpitStore.getState();

    // Add 250 distinct events
    for (let i = 0; i < 250; i++) {
      store.addEvent({
        event_id: `EVT-${i}`,
        type: 'TEST_EVENT',
        severity: 'INFO',
        source: 'test_engine',
        message: `Event number ${i}`,
        symbol: 'EURUSD',
        payload: { index: i },
        timestamp: Date.now() / 1000,
      });
    }

    const state = useCockpitStore.getState();
    expect(state.events.length).toBe(200);
    // Most recent event should be first
    expect(state.events[0].event_id).toBe('EVT-249');
  });

  it('deduplicates events with identical event_id', () => {
    const store = useCockpitStore.getState();
    const duplicateEvent: TerminalEvent = {
      event_id: 'EVT-DUP-001',
      type: 'ORDER_REJECTED',
      severity: 'HIGH',
      source: 'gatekeeper',
      message: 'Spread too wide',
      symbol: 'XAUUSD',
      payload: {},
      timestamp: 1700000000,
    };

    store.addEvent(duplicateEvent);
    store.addEvent(duplicateEvent); // Add again

    const state = useCockpitStore.getState();
    expect(state.events.length).toBe(1);
    expect(state.events[0].event_id).toBe('EVT-DUP-001');
  });

  it('trips and resets circuit breaker based on event type', () => {
    const store = useCockpitStore.getState();
    expect(useCockpitStore.getState().circuitBreakerTripped).toBe(false);

    // Trip event
    store.addEvent({
      event_id: 'EVT-CB-1',
      type: 'CIRCUIT_BREAKER_TRIPPED',
      severity: 'CRITICAL',
      source: 'circuit_breaker',
      message: 'Daily drawdown limit reached (5.2%)',
      symbol: null,
      payload: {},
      timestamp: Date.now() / 1000,
    });

    expect(useCockpitStore.getState().circuitBreakerTripped).toBe(true);
    expect(useCockpitStore.getState().circuitBreakerReason).toBe('Daily drawdown limit reached (5.2%)');

    // Reset event
    store.addEvent({
      event_id: 'EVT-CB-2',
      type: 'CIRCUIT_BREAKER_RESET',
      severity: 'INFO',
      source: 'admin',
      message: 'Admin manual reset',
      symbol: null,
      payload: {},
      timestamp: Date.now() / 1000,
    });

    expect(useCockpitStore.getState().circuitBreakerTripped).toBe(false);
  });

  it('hydrates state on successful fetchSnapshot', async () => {
    const mockSnapshot: CockpitTelemetrySnapshot = {
      circuit_breaker_active: true,
      circuit_breaker_reason: 'Spread spike detected',
      daily_drawdown_pct: 1.45,
      max_daily_drawdown_pct: 4.0,
      total_drawdown_pct: 3.2,
      max_total_drawdown_pct: 8.0,
      cluster_exposures: { USD: 1.8, EUR: 1.0 },
      current_regime: 'TRENDING_BULLISH',
      news_blackout_active: false,
      ai_uncertainty_active: false,
      ai_confidence_score: 0.85,
      active_strategies_count: 3,
      degraded_strategies_count: 0,
      system_uptime_seconds: 12000,
      timestamp: Date.now() / 1000,
    };

    vi.spyOn(api, 'getTelemetrySnapshot').mockResolvedValue(mockSnapshot);
    vi.spyOn(api, 'getRecentEvents').mockResolvedValue([]);

    await useCockpitStore.getState().fetchSnapshot();

    const state = useCockpitStore.getState();
    expect(state.telemetry).toEqual(mockSnapshot);
    expect(state.circuitBreakerTripped).toBe(true);
    expect(state.circuitBreakerReason).toBe('Spread spike detected');
    expect(state.telemetryLoading).toBe(false);
    expect(state.telemetryError).toBeNull();
  });

  it('fails closed when fetchSnapshot fails (does NOT fabricate healthy data)', async () => {
    vi.spyOn(api, 'getTelemetrySnapshot').mockRejectedValue(new Error('500 Internal Server Error'));

    await useCockpitStore.getState().fetchSnapshot();

    const state = useCockpitStore.getState();
    expect(state.telemetry).toBeNull();
    expect(state.telemetryError).toBe('500 Internal Server Error');
    expect(state.telemetryLoading).toBe(false);
  });
});
