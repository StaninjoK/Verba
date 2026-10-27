"""Entry point: ``python -m verba.main`` or ``uvicorn verba.main:app``."""

from __future__ import annotations

import logging
import os
from pathlib import Path

from .api import create_app


def load_dotenv(path: Path) -> None:
    """Minimal .env reader (KEY=VALUE lines). Real environment variables take precedence."""
    if not path.is_file():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key, value = key.strip(), value.strip().strip('"').strip("'")
        if key.startswith("VERBA_"):
            os.environ.setdefault(key, value)


load_dotenv(Path(__file__).resolve().parents[2] / ".env")

logging.basicConfig(level=os.environ.get("VERBA_LOG_LEVEL", "INFO"), format="%(asctime)s %(levelname)s %(name)s: %(message)s")

app = create_app()

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host=os.environ.get("VERBA_HOST", "127.0.0.1"),
        port=int(os.environ.get("VERBA_PORT", "8000")),
        log_level=os.environ.get("VERBA_LOG_LEVEL", "info").lower(),
        access_log=False,
    )
