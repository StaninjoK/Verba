"""Entry point: ``python -m verba.main`` or ``uvicorn verba.main:app``."""

from __future__ import annotations

import logging
import os

from .api import create_app

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
