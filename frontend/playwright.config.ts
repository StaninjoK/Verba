import { defineConfig, devices } from "@playwright/test";
import path from "node:path";

// Starts (or reuses) the backend on :8000 and the frontend dev server on :3000.
// A dedicated data directory keeps e2e projects out of your normal library when the servers are started here.
const backendPython = path.join(__dirname, "..", "backend", ".venv", "bin", "python");

export default defineConfig({
  testDir: "./e2e",
  timeout: 60_000,
  fullyParallel: false,
  workers: 1,
  reporter: [["list"]],
  globalSetup: "./e2e/global-setup.ts",
  use: {
    baseURL: "http://localhost:3000",
    locale: "de-DE",
    trace: "retain-on-failure",
    acceptDownloads: true,
  },
  projects: [
    { name: "desktop", use: { ...devices["Desktop Chrome"] }, testIgnore: /responsive/ },
    { name: "mobile", use: { ...devices["Pixel 7"] }, testMatch: /responsive/ },
  ],
  webServer: [
    {
      command: `${backendPython} -m verba.main`,
      cwd: path.join(__dirname, "..", "backend"),
      url: "http://127.0.0.1:8000/api/health",
      reuseExistingServer: true,
      env: { VERBA_DATA_DIR: path.join(__dirname, "e2e", ".data") },
    },
    {
      command: "npx next dev -p 3000",
      url: "http://localhost:3000",
      reuseExistingServer: true,
      timeout: 120_000,
    },
  ],
});
