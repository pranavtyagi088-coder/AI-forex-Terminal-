import { test, expect } from '@playwright/test';

test.describe('Institutional Broker Cockpit E2E Suite', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('domcontentloaded');
  });

  test('E2E-01: Broker Bridge Panel is visible with header and account cards', async ({ page }) => {
    const brokerPanel = page.locator('[data-testid="broker-bridge-panel"]');
    await expect(brokerPanel).toBeVisible({ timeout: 15000 });
    await expect(brokerPanel.getByText('INSTITUTIONAL BROKER BRIDGE')).toBeVisible();
    await expect(brokerPanel.getByText(/Account/i)).toBeVisible();
    await expect(brokerPanel.getByText(/Balance/i)).toBeVisible();
  });

  test('E2E-02: Emergency Liquidation button reveals 2-step confirmation modal and cancel works', async ({ page }) => {
    const brokerPanel = page.locator('[data-testid="broker-bridge-panel"]');
    await expect(brokerPanel).toBeVisible({ timeout: 15000 });

    const emergencyBtn = brokerPanel.locator('[data-testid="emergency-close-btn"]');
    await expect(emergencyBtn).toBeVisible();

    if (await emergencyBtn.isEnabled()) {
      await emergencyBtn.click();
      const confirmBtn = brokerPanel.locator('[data-testid="emergency-confirm-btn"]');
      const cancelBtn = brokerPanel.locator('[data-testid="emergency-cancel-btn"]');
      await expect(confirmBtn).toBeVisible();
      await expect(cancelBtn).toBeVisible();
      await cancelBtn.click();
      await expect(confirmBtn).not.toBeVisible();
    }
  });

  test('E2E-03: Approval Queue and Positions sections are present', async ({ page }) => {
    const brokerPanel = page.locator('[data-testid="broker-bridge-panel"]');
    await expect(brokerPanel).toBeVisible({ timeout: 15000 });
    await expect(brokerPanel.getByText(/Approval Queue/i)).toBeVisible();
    await expect(brokerPanel.getByText(/Live Broker Positions/i)).toBeVisible();
  });
});
