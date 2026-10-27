import { defineConfig, devices } from "@playwright/test";
import path from "node:path";

// Tests the single-process hosting setup used by the Docker image: the backend serves the static
// frontend export on :8080 behind the shared-password gate. Requires `VERBA_STATIC_EXPORT=1 NEXT_PUBLIC_API_URL="" next build` first.
const backendPython = path.join(__dirname, "..", "backend", ".venv", "bin", "python");

export default defineConfig({
  testDir: "./e2e",
  testIgnore: /responsive/,
  timeout: 60_000,
  workers: 1,
  reporter: [["list"]],
  globalSetup: "./e2e/global-setup.ts",
  use: {
    ...devices["Desktop Chrome"],
    baseURL: "http://127.0.0.1:8080",
    locale: "de-DE",
    acceptDownloads: true,
    httpCredentials: { username: "verba", password: "e2e-test-password" },
  },
  webServer: {
    command: `${backendPython} -m verba.main`,
    cwd: path.join(__dirname, "..", "backend"),
    url: "http://127.0.0.1:8080/api/health",
    reuseExistingServer: false,
    env: {
      VERBA_PORT: "8080",
      VERBA_STATIC_DIR: path.join(__dirname, "out"),
      VERBA_DATA_DIR: path.join(__dirname, "e2e", ".data-hosted"),
      VERBA_REQUIRE_AUTH: "true",
      VERBA_AUTH_PASSWORD: "e2e-test-password",
      VERBA_CORS_ORIGINS: "",
    },
  },
});
