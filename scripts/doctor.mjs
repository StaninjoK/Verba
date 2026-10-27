#!/usr/bin/env node
// Checks what Verba needs on this computer and which Whisper engines/models are already present.
// Read-only: installs and downloads nothing. Usage: npm run doctor
import { execFileSync } from "node:child_process";
import { existsSync, readdirSync, statSync } from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const win = process.platform === "win32";
const venvPy = win ? path.join(root, "backend", ".venv", "Scripts", "python.exe") : path.join(root, "backend", ".venv", "bin", "python");

const ok = (msg) => console.log(`  \x1b[32m✓\x1b[0m ${msg}`);
const bad = (msg) => console.log(`  \x1b[31m✗\x1b[0m ${msg}`);
const info = (msg) => console.log(`    ${msg}`);

function run(cmd, args) {
  try {
    return execFileSync(cmd, args, { encoding: "utf8", stdio: ["ignore", "pipe", "pipe"] }).trim();
  } catch {
    return null;
  }
}

const probe = `
import importlib.util, json
def v(m):
    if importlib.util.find_spec(m) is None: return None
    try:
        import importlib.metadata as md
        return md.version({"faster_whisper":"faster-whisper","whisper":"openai-whisper"}.get(m,m))
    except Exception: return "installed"
print(json.dumps({"faster_whisper": v("faster_whisper"), "whisper": v("whisper"), "torch": v("torch")}))
`;

function engines(python) {
  const out = run(python, ["-c", probe]);
  try {
    return out ? JSON.parse(out.split("\n").pop()) : null;
  } catch {
    return null;
  }
}

const mb = (p) => {
  let total = 0;
  const walk = (d) => {
    for (const e of readdirSync(d, { withFileTypes: true })) {
      const full = path.join(d, e.name);
      if (e.isDirectory()) walk(full);
      else if (e.isFile()) total += statSync(full).size;
    }
  };
  try {
    statSync(p).isDirectory() ? walk(p) : (total = statSync(p).size);
  } catch {
    return "?";
  }
  return `${Math.round(total / 1024 / 1024)} MB`;
};

console.log("\nVerba – Systemprüfung\n");

console.log("Grundlagen");
ok(`Node.js ${process.version}`);
const ff = run("ffmpeg", ["-version"]);
ff ? ok(ff.split("\n")[0]) : bad("FFmpeg nicht gefunden – siehe README.md");
existsSync(venvPy) ? ok("Backend-Umgebung backend/.venv vorhanden") : bad("backend/.venv fehlt – zuerst `npm run setup`");

console.log("\nWhisper-Engines");
const venv = existsSync(venvPy) ? engines(venvPy) : null;
if (venv) {
  venv.faster_whisper ? ok(`faster-whisper ${venv.faster_whisper} in backend/.venv (wird von Verba genutzt)`) : bad("faster-whisper nicht in backend/.venv");
  venv.whisper ? ok(`openai-whisper ${venv.whisper} in backend/.venv (wird von Verba genutzt)`) : info("openai-whisper nicht in backend/.venv");
}
const systemPythons = win ? ["python", "py"] : ["python3", "python"];
let systemFound = null;
for (const py of systemPythons) {
  const e = engines(py);
  if (e && (e.faster_whisper || e.whisper)) {
    systemFound = { py, ...e };
    break;
  }
}
if (systemFound) {
  const names = [systemFound.faster_whisper && `faster-whisper ${systemFound.faster_whisper}`, systemFound.whisper && `openai-whisper ${systemFound.whisper}`]
    .filter(Boolean)
    .join(", ");
  info(`System-Python (${systemFound.py}) hat: ${names} – Verba sieht das NICHT, weil es eine eigene Umgebung nutzt.`);
}
const whisperCli = run(win ? "where" : "which", ["whisper"]);
if (whisperCli) info(`Kommandozeilen-Programm "whisper" gefunden: ${whisperCli.split("\n")[0]}`);

console.log("\nBereits heruntergeladene Modelle");
const home = os.homedir();
const found = [];
const owDir = process.env.XDG_CACHE_HOME ? path.join(process.env.XDG_CACHE_HOME, "whisper") : path.join(home, ".cache", "whisper");
if (existsSync(owDir)) {
  for (const f of readdirSync(owDir).filter((f) => f.endsWith(".pt"))) found.push(["openai-whisper", f.replace(/\.pt$/, ""), path.join(owDir, f)]);
}
const hfHub = process.env.HF_HOME ? path.join(process.env.HF_HOME, "hub") : path.join(home, ".cache", "huggingface", "hub");
if (existsSync(hfHub)) {
  for (const d of readdirSync(hfHub).filter((d) => /faster-whisper/.test(d))) {
    found.push(["faster-whisper", d.replace(/^models--[^-]+(?:-[^-]+)*?--faster-whisper-/, ""), path.join(hfHub, d)]);
  }
}
const localModels = path.join(root, "backend", "models");
if (existsSync(localModels)) {
  for (const d of readdirSync(localModels)) {
    if (existsSync(path.join(localModels, d, "model.bin"))) found.push(["faster-whisper", d.replace(/^faster-whisper-/, ""), path.join(localModels, d)]);
  }
}
if (found.length) for (const [engine, name, p] of found) ok(`${engine}: ${name}  (${mb(p)})  ${p}`);
else bad("Keine Whisper-Modelle gefunden");

console.log("\nEmpfehlung");
const hasFw = venv?.faster_whisper;
const hasOw = venv?.whisper;
const fwModel = found.find((f) => f[0] === "faster-whisper");
const owModel = found.find((f) => f[0] === "openai-whisper");
if (hasFw && fwModel) {
  info(`Alles bereit. In .env: VERBA_WHISPER_MODEL=${fwModel[1]}${fwModel[2].startsWith(localModels) ? `\n    VERBA_WHISPER_MODEL_DIR=${localModels}` : ""}`);
} else if (hasOw && owModel) {
  info(`Alles bereit (openai-whisper). In .env: VERBA_WHISPER_MODEL=${owModel[1]}`);
} else if (!hasFw && !hasOw && systemFound?.whisper && owModel) {
  info("openai-whisper und ein Modell sind schon auf dem System. Ohne neuen Modell-Download nutzbar mit:");
  info(`  ${path.relative(process.cwd(), venvPy) || venvPy} -m pip install openai-whisper`);
  info(`  und in .env: VERBA_WHISPER_MODEL=${owModel[1]}`);
  info("  (Achtung: installiert PyTorch in backend/.venv, je nach System mehrere hundert MB bis über 2 GB.)");
  info("Leichter und schneller auf CPUs ist faster-whisper (siehe docs/WHISPER_SETUP.md).");
} else {
  info("Empfohlen: faster-whisper + Modell base installieren – Anleitung in docs/WHISPER_SETUP.md.");
}
console.log("");
