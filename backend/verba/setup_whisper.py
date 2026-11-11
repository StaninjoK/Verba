"""One-click installation of the local speech recognition (faster-whisper + model) from inside the app.

Runs in the background: installs the pinned packages from requirements-whisper.txt into the
backend's own Python environment, downloads the chosen model once (free, from Hugging Face)
into backend/models, and saves the choice in the repository's .env so it survives restarts.
Only the model name is user input, and it must be one of MODELS.
"""

from __future__ import annotations

import importlib
import importlib.util
import logging
import os
import re
import subprocess
import sys
import threading
from pathlib import Path

from .config import BACKEND_ROOT, Settings

log = logging.getLogger("verba.setup")

MODELS = {"base": 145, "small": 465, "medium": 1500}  # approximate download size in MB
PACKAGES_MB = 450
REQUIREMENTS = BACKEND_ROOT / "requirements-whisper.txt"
MODELS_DIR = BACKEND_ROOT / "models"
ENV_FILE = BACKEND_ROOT.parent / ".env"


def _run(cmd: list[str], timeout: int) -> subprocess.CompletedProcess:
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, check=False,
                          stdin=subprocess.DEVNULL, creationflags=flags)


def update_env_file(path: Path, values: dict[str, str]) -> None:
    """Set KEY=VALUE lines in a .env file, keeping all other lines."""
    lines = path.read_text(encoding="utf-8").splitlines() if path.exists() else []
    seen = set()
    out = []
    for line in lines:
        key = line.split("=", 1)[0].strip()
        if key in values:
            out.append(f"{key}={values[key]}")
            seen.add(key)
        else:
            out.append(line)
    out.extend(f"{k}={v}" for k, v in values.items() if k not in seen)
    path.write_text("\n".join(out) + "\n", encoding="utf-8")


class WhisperSetup:
    def __init__(self, settings: Settings, runner=_run) -> None:
        self.settings = settings
        self.runner = runner
        self._lock = threading.Lock()
        self.state = {"status": "idle", "step": None, "model": None, "error": None}

    def status(self) -> dict:
        with self._lock:
            return dict(self.state) | {"models": MODELS, "packages_mb": PACKAGES_MB,
                                       "installed": importlib.util.find_spec("faster_whisper") is not None}

    def _set(self, **kw) -> None:
        with self._lock:
            self.state.update(kw)

    def start(self, model: str) -> dict:
        if model not in MODELS:
            raise ValueError("unknown model")
        with self._lock:
            if self.state["status"] == "running":
                return dict(self.state)
            self.state = {"status": "running", "step": "packages", "model": model, "error": None}
        threading.Thread(target=self._run, args=(model,), name="verba-setup", daemon=True).start()
        return self.status()

    def _run(self, model: str) -> None:
        try:
            if importlib.util.find_spec("faster_whisper") is None:
                log.info("installing faster-whisper")
                res = self.runner([sys.executable, "-m", "pip", "install", "--disable-pip-version-check",
                                   "-r", str(REQUIREMENTS)], 3600)
                if res.returncode != 0:
                    raise RuntimeError("pip: " + _tail(res.stderr or res.stdout))
                importlib.invalidate_caches()

            self._set(step="model")
            target = MODELS_DIR / f"faster-whisper-{model}"
            if not (target / "model.bin").exists():
                log.info("downloading whisper model %s", model)
                code = ("import sys\nfrom faster_whisper import download_model\n"
                        "download_model(sys.argv[1], output_dir=sys.argv[2])")
                res = self.runner([sys.executable, "-c", code, model, str(target)], 3600)
                if res.returncode != 0 or not (target / "model.bin").exists():
                    raise RuntimeError("download: " + _tail(res.stderr or res.stdout))

            self._set(step="config")
            self.settings.whisper_model = model
            self.settings.whisper_model_dir = MODELS_DIR.resolve()
            for name in ("faster-whisper",):
                if name not in self.settings.allowed_providers:
                    self.settings.allowed_providers.insert(0, name)
            os.environ["VERBA_WHISPER_MODEL"] = model
            os.environ["VERBA_WHISPER_MODEL_DIR"] = str(MODELS_DIR.resolve())
            try:
                update_env_file(ENV_FILE, {"VERBA_WHISPER_MODEL": model,
                                           "VERBA_WHISPER_MODEL_DIR": str(MODELS_DIR.resolve())})
            except OSError:
                log.warning("could not write .env; the setting applies until the next restart")
            self._set(status="done", step=None)
            log.info("speech recognition ready (model %s)", model)
        except Exception as exc:  # report, never crash the backend
            log.warning("whisper setup failed: %s", type(exc).__name__)
            self._set(status="failed", error=str(exc)[-600:])


def _tail(text: str | None, lines: int = 6) -> str:
    text = re.sub(r"\s+\n", "\n", text or "").strip()
    return "\n".join(text.splitlines()[-lines:])
