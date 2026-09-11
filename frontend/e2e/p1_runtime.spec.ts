import { test, expect } from '@playwright/test';

test.describe('Phase P1 Live Runtime & Risk Cockpit Verification', () => {

  test.beforeEach(async ({ page }) => {
    await page.goto('http://127.0.0.1:5173');
    await page.waitForLoadState('domcontentloaded');
  });

  test('P1-01: Terminal Cockpit Hydration & Live WS Stream Verification', async ({ page }) => {
    await expect(page.locator('body')).toBeVisible();

    const wsBadge = page.locator('text=/LIVE WS|CONNECTED|WS STREAM|TELEMETRY|NORMAL/i').first();
    await expect(wsBadge).toBeVisible({ timeout: 15000 });

    const riskSection = page.locator('text=/RISK|DRAWDOWN|CIRCUIT|EQUITY|MONTE CARLO|HERMES/i').first();
    await expect(riskSection).toBeVisible({ timeout: 10000 });
  });

  test('P1-02: Pre-Flight Trade Gate Evaluation (9/9 Gates Approved)', async ({ page }) => {
    const response = await page.request.post('http://127.0.0.1:8000/api/trades/pre-flight-check', {
      headers: {
        'Authorization': 'Bearer dev-secret-token',
        'Content-Type': 'application/json'
      },
      data: {
        symbol: 'EURUSD',
        direction: 'BUY',
        entry_price: 1.0850,
        stop_loss: 1.0800,
        take_profit: 1.0950,
        account_balance: 100000.0,
        account_equity: 100000.0,
        risk_per_trade_pct: 1.0,
        current_spread_pips: 1.2
      }
    });

    expect(response.status()).toBe(200);
    const json = await response.json();
    expect(json.allowed).toBe(true);
    expect(json.canonical_symbol).toBe('EURUSD');
    expect(json.approved_lot_size).toBeGreaterThan(0);
    expect(json.integrity_hash).toBeTruthy();
    expect(json.decision_id).toBeTruthy();
  });

  test('P1-03: Excessive Spread Rejection (Gate 3 Veto)', async ({ page }) => {
    const response = await page.request.post('http://127.0.0.1:8000/api/trades/pre-flight-check', {
      headers: {
        'Authorization': 'Bearer dev-secret-token',
        'Content-Type': 'application/json'
      },
      data: {
        symbol: 'EURUSD',
        direction: 'BUY',
        entry_price: 1.0850,
        stop_loss: 1.0800,
        account_balance: 100000.0,
        account_equity: 100000.0,
        risk_per_trade_pct: 1.0,
        current_spread_pips: 5.0
      }
    });

    expect(response.status()).toBe(200);
    const json = await response.json();
    expect(json.allowed).toBe(false);
    expect(json.rejection_reasons.length).toBeGreaterThan(0);
    const hasSpreadReason = json.rejection_reasons.some((r: string) => /spread/i.test(r));
    expect(hasSpreadReason).toBe(true);
  });

  test('P1-04: Circuit Breaker Intercept & Kill Switch Gate Intercept', async ({ page }) => {
    // 1. Check cockpit telemetry initially
    const telRes = await page.request.get('http://127.0.0.1:8000/api/telemetry/cockpit', {
      headers: { 'Authorization': 'Bearer dev-secret-token' }
    });
    expect(telRes.status()).toBe(200);
    const telData = await telRes.json();
    expect(telData.circuit_breaker_active).toBe(false);

    // 2. Toggle Circuit Breaker to ON (Trip Kill Switch) with exact schema { enable: true }
    const toggleOn = await page.request.post('http://127.0.0.1:8000/api/admin/circuit-breaker/toggle', {
      headers: {
        'Authorization': 'Bearer dev-secret-token',
        'Content-Type': 'application/json'
      },
      data: {
        enable: true,
        reason: 'E2E Automated Kill Switch Test'
      }
    });
    expect(toggleOn.status()).toBe(200);
    const toggleOnData = await toggleOn.json();
    expect(toggleOnData.circuit_breaker_active).toBe(true);

    // 3. Verify Trade is VETOED due to active circuit breaker
    const tradeRes = await page.request.post('http://127.0.0.1:8000/api/trades/pre-flight-check', {
      headers: {
        'Authorization': 'Bearer dev-secret-token',
        'Content-Type': 'application/json'
      },
      data: {
        symbol: 'EURUSD',
        direction: 'BUY',
        entry_price: 1.0850,
        stop_loss: 1.0800,
        account_balance: 100000.0,
        account_equity: 100000.0,
        risk_per_trade_pct: 1.0,
        current_spread_pips: 1.2
      }
    });
    expect(tradeRes.status()).toBe(200);
    const tradeJson = await tradeRes.json();
    expect(tradeJson.allowed).toBe(false);
    const hasBreakerReason = tradeJson.rejection_reasons.some((r: string) => /CIRCUIT_BREAKER|KILL/i.test(r));
    expect(hasBreakerReason).toBe(true);

    // 4. Reset Circuit Breaker back to NORMAL with exact schema { enable: false }
    const toggleOff = await page.request.post('http://127.0.0.1:8000/api/admin/circuit-breaker/toggle', {
      headers: {
        'Authorization': 'Bearer dev-secret-token',
        'Content-Type': 'application/json'
      },
      data: {
        enable: false,
        reason: 'Reset to Normal State'
      }
    });
    expect(toggleOff.status()).toBe(200);
    const toggleOffData = await toggleOff.json();
    expect(toggleOffData.circuit_breaker_active).toBe(false);
  });

});
