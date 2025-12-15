import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: '.',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: 'html',
  use: {
    baseURL: 'http://localhost:3001',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
  webServer: [
    {
      command: 'cd ../backend && python -m uvicorn main:app --port 8888',
      url: 'http://localhost:8888/api/stats',
      reuseExistingServer: !process.env.CI,
      timeout: 30000,
    },
    {
      command: 'cd ../frontend && bun run dev',
      url: 'http://localhost:3001',
      reuseExistingServer: !process.env.CI,
      timeout: 30000,
    },
  ],
});
