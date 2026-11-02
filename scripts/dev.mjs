#!/usr/bin/env node
// Starts the Verba backend (FastAPI on 127.0.0.1:8000) and frontend (Next.js on :3000) together.
// Usage: npm run dev   (from the repository root)
import { spawn } from "node:child_process";
import { existsSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const venvPython = process.platform === "win32"
  ? path.join(root, "backend", ".venv", "Scripts", "python.exe")
  : path.join(root, "backend", ".venv", "bin", "python");

if (!existsSync(venvPython)) {
  console.error("Backend virtualenv not found. Run `npm run setup` first (see README.md).");
  process.exit(1);
}

const procs = [];
function run(name, cmd, args, cwd, color) {
  const child = spawn(cmd, args, { cwd, env: process.env, stdio: ["ignore", "pipe", "pipe"], shell: process.platform === "win32" });
  const prefix = `\x1b[${color}m[${name}]\x1b[0m `;
  const pipe = (stream, out) => {
    let buf = "";
    stream.on("data", (chunk) => {
      buf += chunk;
      const lines = buf.split("\n");
      buf = lines.pop();
      for (const line of lines) out.write(prefix + line + "\n");
    });
  };
  pipe(child.stdout, process.stdout);
  pipe(child.stderr, process.stderr);
  child.on("exit", (code) => {
    console.log(`${prefix}exited with code ${code}`);
    shutdown(code ?? 0);
  });
  procs.push(child);
}

let stopping = false;
function shutdown(code) {
  if (stopping) return;
  stopping = true;
  for (const p of procs) p.kill("SIGTERM");
  setTimeout(() => process.exit(code), 500);
}
process.on("SIGINT", () => shutdown(0));
process.on("SIGTERM", () => shutdown(0));

run("api", venvPython, ["-m", "verba.main"], path.join(root, "backend"), "35");
run("web", "npm", ["run", process.argv.includes("--prod") ? "start" : "dev"], path.join(root, "frontend"), "36");
console.log("\n  Verba is starting…  App: http://localhost:3000   API: http://127.0.0.1:8000/api/health\n");

// --open: open the library in the default browser once the web server answers.
if (process.argv.includes("--open")) {
  const url = "http://localhost:3000/app";
  const started = Date.now();
  const tryOpen = async () => {
    try {
      const res = await fetch(url);
      if (res.ok) {
        const opener = process.platform === "win32" ? ["cmd", ["/c", "start", "", url]] : process.platform === "darwin" ? ["open", [url]] : ["xdg-open", [url]];
        spawn(opener[0], opener[1], { stdio: "ignore", detached: true }).unref();
        return;
      }
    } catch {
      // not up yet
    }
    if (Date.now() - started < 180_000) setTimeout(tryOpen, 1500);
  };
  setTimeout(tryOpen, 2000);
}
