// Browser suite for the built site (roadmap S08, docs/DECISIONS.md item 27).
//
// It tests dist/ as it is, and never builds: verify.sh builds first (with
// GITHUB_REPOSITORY set, so the 404 page links under /aurelia-os/ as it does
// in CI) and then runs this. Two build.py runs at once would wipe each
// other's dist/, so the suite stays out of the build entirely, and
// tests/browser/global-setup.mjs stops with instructions if dist/ is missing
// or was built for the wrong prefix.
//
// Run: bash verify.sh   (everything), or after a build: npx playwright test
import { defineConfig, devices } from "@playwright/test";
import { BASE_PATH } from "./tests/browser/site.mjs";

const PORT = Number(process.env.BROWSER_TEST_PORT ?? 8792);

export default defineConfig({
  testDir: "tests/browser",
  globalSetup: "./tests/browser/global-setup.mjs",
  // One worker: the tests share one small static server, and the suite is
  // short enough that running in parallel saves little and costs determinism.
  workers: 1,
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: 0,
  timeout: 30_000,
  expect: { timeout: 5_000 },
  outputDir: "test-results",
  reporter: process.env.CI
    ? [["list"], ["html", { open: "never", outputFolder: "playwright-report" }]]
    : [["list"]],
  use: {
    baseURL: `http://127.0.0.1:${PORT}${BASE_PATH}`,
    // The site honours prefers-reduced-motion everywhere it animates, so this
    // turns animations off the way a visitor would.
    reducedMotion: "reduce",
    screenshot: "only-on-failure",
    trace: "retain-on-failure",
    ...devices["Desktop Chrome"],
    viewport: { width: 1440, height: 900 },
  },
  projects: [{ name: "chromium", use: { browserName: "chromium" } }],
  webServer: {
    command: `node tools/preview.mjs ${PORT} ${BASE_PATH}`,
    url: `http://127.0.0.1:${PORT}${BASE_PATH}index.html`,
    // Always our own server: a stray one on this port could serve anything.
    reuseExistingServer: false,
    timeout: 15_000,
  },
});
