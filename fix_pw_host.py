from pathlib import Path

ROOT = Path(r"C:\Users\PRANAV TYAGI\PycharmProjects\WelcomeScreen")

# 1. Inspect vite.config.ts
vite_cfg = ROOT / "frontend/vite.config.ts"
if vite_cfg.exists():
    text = vite_cfg.read_text(encoding="utf-8-sig", errors="replace")
    print("=== vite.config.ts ===")
    print(text)

# 2. Update playwright.config.ts with explicit host & preview/dev command
pw_cfg = ROOT / "frontend/playwright.config.ts"
clean_pw_config = '''import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './e2e',
  fullyParallel: false,
  workers: 1,
  forbidOnly: !!process.env.CI,
  retries: 0,
  timeout: 30000,
  use: {
    baseURL: 'http://127.0.0.1:5173',
    trace: 'off',
    screenshot: 'only-on-failure',
  },
  webServer: {
    command: 'npm run dev -- --host 127.0.0.1 --port 5173',
    url: 'http://127.0.0.1:5173',
    reuseExistingServer: true,
    timeout: 60000,
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
});
'''
pw_cfg.write_text(clean_pw_config, encoding="utf-8")
print("\n[SUCCESS] playwright.config.ts updated with explicit IPv4 binding command!")
