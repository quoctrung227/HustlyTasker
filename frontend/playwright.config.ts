import { defineConfig, devices } from '@playwright/test'

const channel = process.env.PLAYWRIGHT_CHANNEL
if (channel && !['chrome', 'msedge', 'chromium'].includes(channel)) throw new Error('Unsupported integration browser channel.')

export default defineConfig({
  testDir: './e2e',
  fullyParallel: false,
  workers: 1,
  retries: 0,
  timeout: 30_000,
  reporter: 'list',
  use: {
    baseURL: 'http://127.0.0.1:5173',
    trace: 'off',
    screenshot: 'off',
    video: 'off',
  },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'], ...(channel ? { channel } : {}) } }],
  webServer: {
    command: 'npm run dev -- --host 127.0.0.1 --port 5173 --strictPort',
    url: 'http://127.0.0.1:5173/login',
    reuseExistingServer: false,
    timeout: 30_000,
    env: { DJANGO_API_TARGET: process.env.DJANGO_API_TARGET ?? 'http://127.0.0.1:8001' },
  },
})
