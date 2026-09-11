# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: p1_runtime.spec.ts >> Phase P1 Live Runtime & Risk Cockpit Verification >> P1-04: Circuit Breaker Intercept & Kill Switch Gate Intercept
- Location: e2e\p1_runtime.spec.ts:74:3

# Error details

```
Error: page.goto: net::ERR_CONNECTION_REFUSED at http://127.0.0.1:5173/
Call log:
  - navigating to "http://127.0.0.1:5173/", waiting until "load"

```

# Test source

```ts
  1   | import { test, expect } from '@playwright/test';
  2   | 
  3   | test.describe('Phase P1 Live Runtime & Risk Cockpit Verification', () => {
  4   | 
  5   |   test.beforeEach(async ({ page }) => {
> 6   |     await page.goto('http://127.0.0.1:5173');
      |                ^ Error: page.goto: net::ERR_CONNECTION_REFUSED at http://127.0.0.1:5173/
  7   |     await page.waitForLoadState('domcontentloaded');
  8   |   });
  9   | 
  10  |   test('P1-01: Terminal Cockpit Hydration & Live WS Stream Verification', async ({ page }) => {
  11  |     await expect(page.locator('body')).toBeVisible();
  12  | 
  13  |     const wsBadge = page.locator('text=/LIVE WS|CONNECTED|WS STREAM|TELEMETRY|NORMAL/i').first();
  14  |     await expect(wsBadge).toBeVisible({ timeout: 15000 });
  15  | 
  16  |     const riskSection = page.locator('text=/RISK|DRAWDOWN|CIRCUIT|EQUITY|MONTE CARLO|HERMES/i').first();
  17  |     await expect(riskSection).toBeVisible({ timeout: 10000 });
  18  |   });
  19  | 
  20  |   test('P1-02: Pre-Flight Trade Gate Evaluation (9/9 Gates Approved)', async ({ page }) => {
  21  |     const response = await page.request.post('http://127.0.0.1:8000/api/trades/pre-flight-check', {
  22  |       headers: {
  23  |         'Authorization': 'Bearer dev-secret-token',
  24  |         'Content-Type': 'application/json'
  25  |       },
  26  |       data: {
  27  |         symbol: 'EURUSD',
  28  |         direction: 'BUY',
  29  |         entry_price: 1.0850,
  30  |         stop_loss: 1.0800,
  31  |         take_profit: 1.0950,
  32  |         account_balance: 100000.0,
  33  |         account_equity: 100000.0,
  34  |         risk_per_trade_pct: 1.0,
  35  |         current_spread_pips: 1.2
  36  |       }
  37  |     });
  38  | 
  39  |     expect(response.status()).toBe(200);
  40  |     const json = await response.json();
  41  |     expect(json.allowed).toBe(true);
  42  |     expect(json.canonical_symbol).toBe('EURUSD');
  43  |     expect(json.approved_lot_size).toBeGreaterThan(0);
  44  |     expect(json.integrity_hash).toBeTruthy();
  45  |     expect(json.decision_id).toBeTruthy();
  46  |   });
  47  | 
  48  |   test('P1-03: Excessive Spread Rejection (Gate 3 Veto)', async ({ page }) => {
  49  |     const response = await page.request.post('http://127.0.0.1:8000/api/trades/pre-flight-check', {
  50  |       headers: {
  51  |         'Authorization': 'Bearer dev-secret-token',
  52  |         'Content-Type': 'application/json'
  53  |       },
  54  |       data: {
  55  |         symbol: 'EURUSD',
  56  |         direction: 'BUY',
  57  |         entry_price: 1.0850,
  58  |         stop_loss: 1.0800,
  59  |         account_balance: 100000.0,
  60  |         account_equity: 100000.0,
  61  |         risk_per_trade_pct: 1.0,
  62  |         current_spread_pips: 5.0
  63  |       }
  64  |     });
  65  | 
  66  |     expect(response.status()).toBe(200);
  67  |     const json = await response.json();
  68  |     expect(json.allowed).toBe(false);
  69  |     expect(json.rejection_reasons.length).toBeGreaterThan(0);
  70  |     const hasSpreadReason = json.rejection_reasons.some((r: string) => /spread/i.test(r));
  71  |     expect(hasSpreadReason).toBe(true);
  72  |   });
  73  | 
  74  |   test('P1-04: Circuit Breaker Intercept & Kill Switch Gate Intercept', async ({ page }) => {
  75  |     // 1. Check cockpit telemetry initially
  76  |     const telRes = await page.request.get('http://127.0.0.1:8000/api/telemetry/cockpit', {
  77  |       headers: { 'Authorization': 'Bearer dev-secret-token' }
  78  |     });
  79  |     expect(telRes.status()).toBe(200);
  80  |     const telData = await telRes.json();
  81  |     expect(telData.circuit_breaker_active).toBe(false);
  82  | 
  83  |     // 2. Toggle Circuit Breaker to ON (Trip Kill Switch) with exact schema { enable: true }
  84  |     const toggleOn = await page.request.post('http://127.0.0.1:8000/api/admin/circuit-breaker/toggle', {
  85  |       headers: {
  86  |         'Authorization': 'Bearer dev-secret-token',
  87  |         'Content-Type': 'application/json'
  88  |       },
  89  |       data: {
  90  |         enable: true,
  91  |         reason: 'E2E Automated Kill Switch Test'
  92  |       }
  93  |     });
  94  |     expect(toggleOn.status()).toBe(200);
  95  |     const toggleOnData = await toggleOn.json();
  96  |     expect(toggleOnData.circuit_breaker_active).toBe(true);
  97  | 
  98  |     // 3. Verify Trade is VETOED due to active circuit breaker
  99  |     const tradeRes = await page.request.post('http://127.0.0.1:8000/api/trades/pre-flight-check', {
  100 |       headers: {
  101 |         'Authorization': 'Bearer dev-secret-token',
  102 |         'Content-Type': 'application/json'
  103 |       },
  104 |       data: {
  105 |         symbol: 'EURUSD',
  106 |         direction: 'BUY',
```