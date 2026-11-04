"""Small HTTP client for the Verba API (standard library only). Used by the CLI and the MCP server."""

from __future__ import annotations

import base64
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
REPO_DIR = BACKEND_DIR.parent


class VerbaError(Exception):
    def __init__(self, code: str, message: str, status: int = 0) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status = status


def _load_dotenv() -> None:
    env = REPO_DIR / ".env"
    if not env.is_file():
        return
    for raw in env.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            if key.strip().startswith("VERBA_"):
                os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


class VerbaClient:
    def __init__(self, base_url: str | None = None, autostart: bool | None = None) -> None:
        _load_dotenv()
        port = os.environ.get("VERBA_PORT", "8000")
        self.base_url = (base_url or os.environ.get("VERBA_API_URL") or f"http://127.0.0.1:{port}").rstrip("/")
        user = os.environ.get("VERBA_AUTH_USER", "verba")
        password = os.environ.get("VERBA_AUTH_PASSWORD", "")
        self._auth = "Basic " + base64.b64encode(f"{user}:{password}".encode()).decode() if password else None
        self.autostart = autostart if autostart is not None else os.environ.get("VERBA_MCP_AUTOSTART", "1") != "0"
        self._started: subprocess.Popen | None = None

    # ------------------------------------------------------------------ transport
    def _request(self, method: str, path: str, *, body: bytes | None = None, json_body: dict | None = None,
                 headers: dict | None = None, timeout: float = 120.0) -> tuple[bytes, dict]:
        hdrs = dict(headers or {})
        if json_body is not None:
            body = json.dumps(json_body).encode()
            hdrs["Content-Type"] = "application/json"
        if self._auth:
            hdrs["Authorization"] = self._auth
        req = urllib.request.Request(self.base_url + path, data=body, method=method, headers=hdrs)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as res:
                return res.read(), {k.lower(): v for k, v in res.headers.items()}
        except urllib.error.HTTPError as exc:
            try:
                err = json.loads(exc.read() or b"{}").get("error") or {}
            except json.JSONDecodeError:
                err = {}
            raise VerbaError(err.get("code", "http_error"), err.get("message", f"HTTP {exc.code}"), exc.code) from exc
        except (urllib.error.URLError, ConnectionError, TimeoutError) as exc:
            raise VerbaError("backend_unreachable", f"Verba is not reachable at {self.base_url}.") from exc

    def get_json(self, path: str, **kw) -> dict:
        data, _ = self._request("GET", path, **kw)
        return json.loads(data)

    def send_json(self, method: str, path: str, payload: dict | None = None) -> dict:
        data, _ = self._request(method, path, json_body=payload or {})
        return json.loads(data) if data else {}

    def get_bytes(self, path: str) -> tuple[bytes, str]:
        data, headers = self._request("GET", path)
        return data, headers.get("content-type", "application/octet-stream")

    # ------------------------------------------------------------------ backend
    def ensure_running(self, wait_seconds: float = 45.0) -> None:
        try:
            self.get_json("/api/health", timeout=3)
            return
        except VerbaError:
            local = urllib.parse.urlparse(self.base_url).hostname in ("127.0.0.1", "localhost")
            if not (self.autostart and local):
                raise
        log_path = BACKEND_DIR / "data" / "verba-backend.log"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        with log_path.open("ab") as log:
            self._started = subprocess.Popen([sys.executable, "-m", "verba.main"], cwd=BACKEND_DIR, stdout=log, stderr=log,
                                             stdin=subprocess.DEVNULL, creationflags=flags)
        deadline = time.time() + wait_seconds
        while time.time() < deadline:
            time.sleep(1)
            try:
                self.get_json("/api/health", timeout=3)
                return
            except VerbaError:
                if self._started.poll() is not None:
                    break
        raise VerbaError("backend_unreachable", f"Verba could not be started. See {log_path}.")

    # ------------------------------------------------------------------ uploads
    def upload(self, path: Path, endpoint: str, params: dict | None = None) -> dict:
        path = Path(path).expanduser()
        if not path.is_file():
            raise VerbaError("file_not_found", f"File not found: {path}")
        query = f"?{urllib.parse.urlencode(params)}" if params else ""
        data, _ = self._request("POST", endpoint + query, body=path.read_bytes(), timeout=600,
                                headers={"X-Verba-Filename": urllib.parse.quote(path.name),
                                         "Content-Type": "application/octet-stream"})
        return json.loads(data)

    def import_chat(self, path: Path, language: str = "auto", provider: str = "auto") -> dict:
        return self.upload(path, "/api/chats", {"provider": provider, "language": language})

    def wait_for_chat(self, chat_id: str, timeout: float, on_progress=None) -> dict:
        deadline = time.time() + timeout
        while True:
            chat = self.get_json(f"/api/chats/{chat_id}")
            if on_progress:
                on_progress(chat)
            if chat["status"] not in ("pending", "processing") or time.time() >= deadline:
                return chat
            time.sleep(2)

    def export_chat(self, chat_id: str, fmt: str = "txt", lang: str = "de") -> bytes:
        data, _ = self._request("GET", f"/api/chats/{chat_id}/export?format={fmt}&lang={lang}")
        return data

    def transcribe_file(self, path: Path, language: str = "auto", provider: str = "auto", timeout: float = 900,
                        on_progress=None) -> dict:
        project = self.upload(path, "/api/projects")
        self.send_json("POST", f"/api/projects/{project['id']}/transcribe", {"provider": provider, "language": language})
        deadline = time.time() + timeout
        while True:
            project = self.get_json(f"/api/projects/{project['id']}")
            if on_progress:
                on_progress(project)
            if project["status"] not in ("pending", "validating", "processing") or time.time() >= deadline:
                return project
            time.sleep(2)
