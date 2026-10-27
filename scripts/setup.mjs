#!/usr/bin/env node
// One-time local setup: Python virtualenv + backend deps, frontend deps. Downloads only free packages
// (~25 MB Python, ~450 MB node_modules). Does NOT install Whisper or download any model.
import { execSync } from "node:child_process";
import { existsSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const backend = path.join(root, "backend");
const win = process.platform === "win32";
const py = win ? "python" : "python3";
const venvPy = win ? path.join(backend, ".venv", "Scripts", "python.exe") : path.join(backend, ".venv", "bin", "python");
const sh = (cmd, cwd = root) => {
  console.log(`\n$ ${cmd}`);
  execSync(cmd, { cwd, stdio: "inherit" });
};

try {
  execSync("ffmpeg -version", { stdio: "ignore" });
} catch {
  console.warn("\n⚠  FFmpeg was not found. Install it before uploading files (see README.md).\n");
}
if (!existsSync(venvPy)) sh(`${py} -m venv .venv`, backend);
sh(`"${venvPy}" -m pip install -r requirements-dev.txt`, backend);
sh("npm install", path.join(root, "frontend"));
console.log("\n✓ Setup complete. Start Verba with: npm run dev\n");
