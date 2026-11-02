import { defineConfig } from "@playwright/test";
import { mkdtempSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

const dataDir = mkdtempSync(join(tmpdir(), "harness-e2e-"));
export default defineConfig({
  testDir: ".",
  testMatch: "harness.spec.ts",
  workers: 1,
  timeout: 30_000,
  use: {
    baseURL: "http://127.0.0.1:18010",
    launchOptions: { executablePath: process.env.HARNESS_CHROMIUM_PATH || undefined },
    screenshot: "only-on-failure",
  },
  webServer: {
    command: ".venv/bin/analytics-agent bootstrap && .venv/bin/uvicorn analytics_agent.main:app --host 127.0.0.1 --port 18010",
    cwd: join(__dirname, "../.."),
    url: "http://127.0.0.1:18010/health",
    env: {
      DATABASE_URL: `sqlite+aiosqlite:///${join(dataDir, "test.db")}`,
      ANALYTICS_AGENT_CONFIG_DIR: dataDir,
      DATAHUB_TELEMETRY_ENABLED: "false",
    },
  },
});
