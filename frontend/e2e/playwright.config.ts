import { defineConfig, devices } from '@playwright/test'

/**
 * 独立 E2E 基线配置。
 *
 * - 不依赖后端服务: 前端 `src/api/request.ts` 具备 Mock 兜底, 后端不可达时
 *   页面仍可渲染, 因此本套用例可在纯前端 dev server 下运行。
 * - webServer 从 frontend/ 目录启动 Vite; CI 中不复用已有服务。
 * - 目录独立于 frontend/ 主工程, 不修改 package-lock.json / npm ci。
 */
export default defineConfig({
  testDir: './specs',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  workers: process.env.CI ? 2 : undefined,
  reporter: [['list'], ['html', { outputFolder: 'playwright-report', open: 'never' }]],
  use: {
    baseURL: 'http://127.0.0.1:5173',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    ...devices['Desktop Chrome'],
  },
  webServer: {
    command: 'npm run dev -- --host 127.0.0.1 --port 5173',
    cwd: '..',
    url: 'http://127.0.0.1:5173',
    reuseExistingServer: !process.env.CI,
    timeout: 120_000,
  },
})
