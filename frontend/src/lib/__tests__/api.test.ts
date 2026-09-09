import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { NormalizedApiError, parseFastApiError, api } from '../api';

describe('NormalizedApiError & parseFastApiError', () => {
  it('correctly constructs NormalizedApiError with status, endpoint, and details', () => {
    const err = new NormalizedApiError('Test error message', 400, 'testEndpoint', { field: 'symbol' });
    expect(err.name).toBe('NormalizedApiError');
    expect(err.message).toBe('Test error message');
    expect(err.status).toBe(400);
    expect(err.endpoint).toBe('testEndpoint');
    expect(err.details).toEqual({ field: 'symbol' });
  });

  it('parses FastAPI 422 array validation errors into clean readable string', () => {
    const fastApi422 = {
      detail: [
        { loc: ['body', 'entry_price'], msg: 'Input should be greater than 0', type: 'greater_than' },
        { loc: ['body', 'symbol'], msg: 'Field required', type: 'missing' },
      ],
    };

    const err = parseFastApiError(fastApi422, 422, 'evaluatePreFlight');
    expect(err.status).toBe(422);
    expect(err.endpoint).toBe('evaluatePreFlight');
    expect(err.message).toContain('Validation Error:');
    expect(err.message).toContain('entry_price: Input should be greater than 0');
    expect(err.message).toContain('symbol: Field required');
  });

  it('parses 400 error with string detail', () => {
    const fastApi400 = { detail: 'CIRCUIT_BREAKER_ACTIVE: Trading halted by Risk Officer' };
    const err = parseFastApiError(fastApi400, 400, 'evaluatePreFlight');
    expect(err.status).toBe(400);
    expect(err.message).toBe('CIRCUIT_BREAKER_ACTIVE: Trading halted by Risk Officer');
  });

  it('parses 500 error with object detail', () => {
    const fastApi500 = { detail: { error: 'Database locked', code: 'DB_BUSY' } };
    const err = parseFastApiError(fastApi500, 500, 'getTelemetrySnapshot');
    expect(err.status).toBe(500);
    expect(err.message).toBe(JSON.stringify({ error: 'Database locked', code: 'DB_BUSY' }));
  });

  it('handles null or undefined error payload gracefully', () => {
    const err = parseFastApiError(null, 502, 'gateway');
    expect(err.status).toBe(502);
    expect(err.message).toBe('HTTP 502 Response Error');
  });
});

describe('api.evaluatePreFlight Network Failure', () => {
  const originalFetch = global.fetch;

  beforeEach(() => {
    global.fetch = vi.fn();
  });

  afterEach(() => {
    global.fetch = originalFetch;
  });

  it('throws NormalizedApiError on network failure without crashing', async () => {
    (global.fetch as any).mockRejectedValue(new Error('Failed to fetch'));

    await expect(
      api.evaluatePreFlight({
        canonical_symbol: 'EURUSD',
        direction: 'BUY',
        entry_price: 1.085,
        stop_loss: 1.08,
        account_balance: 100000,
        risk_per_trade_pct: 1.0,
      } as any)
    ).rejects.toThrow(/Network Connection Failure/);
  });
});
