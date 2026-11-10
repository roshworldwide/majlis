import { defineConfig, devices } from '@playwright/test';

/**
 * MAJLIS Experience e2e.
 *   npm run e2e                      # builds dist/ if stale, serves it, runs all projects
 *   npx playwright test --project=chromium --project=chromium-nogl
 * Projects:
 *   chromium       headless Chromium with GPU flags (WebGL2; may be software GL headless)
 *   chromium-nogl  WebGL disabled (--disable-webgl --disable-3d-apis) → must auto-select the 2D Experience
 *   webkit
 *   firefox        only with E2E_FIREFOX=1 (hangs at launch in the sandboxed agent shell)
 */
const PORT = Number(process.env.E2E_PORT || 4173);
const GPU_ARGS = ['--use-angle=metal', '--enable-gpu', '--ignore-gpu-blocklist', '--enable-unsafe-swiftshader'];

export default defineConfig({
  testDir: './e2e',
  globalSetup: './e2e/global-setup.ts',
  outputDir: './test-results',
  timeout: 300_000,
  expect: { timeout: 20_000 },
  fullyParallel: true,
  workers: process.env.E2E_WORKERS ? Number(process.env.E2E_WORKERS) : 3,
  retries: 0,
  reporter: [['list'], ['html', { open: 'never', outputFolder: 'playwright-report' }]],
  use: {
    baseURL: `http://127.0.0.1:${PORT}/`,
    viewport: { width: 1440, height: 900 },
    // traces add screencast overhead to WebGL pages and stall on the 1 MB single-file page; opt in with E2E_TRACE=1
    trace: process.env.E2E_TRACE ? 'retain-on-failure' : 'off',
    screenshot: 'only-on-failure',
    video: 'off',
  },
  webServer: {
    command: 'node scripts/e2e-server.mjs',
    url: `http://127.0.0.1:${PORT}/`,
    reuseExistingServer: true,
    timeout: 240_000,
    stdout: 'pipe',
    stderr: 'pipe',
    env: { E2E_PORT: String(PORT) },
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'], viewport: { width: 1440, height: 900 }, launchOptions: { args: GPU_ARGS } },
    },
    {
      name: 'chromium-nogl',
      use: {
        ...devices['Desktop Chrome'],
        viewport: { width: 1440, height: 900 },
        launchOptions: { args: ['--disable-webgl', '--disable-3d-apis'] },
      },
    },
    { name: 'webkit', use: { ...devices['Desktop Safari'], viewport: { width: 1440, height: 900 } } },
    // Firefox (Playwright build 1466) hangs at launch inside the sandboxed agent shell on this Mac;
    // enable it from a normal terminal with E2E_FIREFOX=1.
    ...(process.env.E2E_FIREFOX
      ? [{ name: 'firefox', use: { ...devices['Desktop Firefox'], viewport: { width: 1440, height: 900 } } }]
      : []),
  ],
});
