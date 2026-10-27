"""Runtime configuration, read from environment variables (see .env.example)."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parent.parent


def _bool(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None or raw.strip() == "":
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _int(name: str, default: int, minimum: int = 0) -> int:
    raw = os.environ.get(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        value = int(raw)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer") from exc
    if value < minimum:
        raise ValueError(f"{name} must be >= {minimum}")
    return value


def _list(name: str, default: list[str]) -> list[str]:
    raw = os.environ.get(name)
    if raw is None or raw.strip() == "":
        return list(default)
    return [item.strip() for item in raw.split(",") if item.strip()]


ALLOWED_EXTENSIONS = (".mp3", ".wav", ".m4a", ".mp4", ".ogg", ".oga", ".opus", ".flac", ".webm", ".mov")


@dataclass
class Settings:
    data_dir: Path
    max_upload_mb: int = 500
    max_storage_mb: int = 10_000
    max_concurrent_jobs: int = 1
    max_media_duration_min: int = 240
    job_timeout_factor: float = 6.0
    job_timeout_min_seconds: int = 300
    max_job_attempts: int = 2
    allowed_providers: list[str] = field(default_factory=lambda: ["faster-whisper", "openai-whisper", "mock"])
    default_provider: str = "auto"
    external_providers_enabled: bool = False
    external_api_key: str = ""
    whisper_model: str = "base"
    whisper_model_dir: Path | None = None
    whisper_device: str = "cpu"
    whisper_compute_type: str = "int8"
    allow_model_download: bool = False
    cors_origins: list[str] = field(default_factory=lambda: ["http://localhost:3000", "http://127.0.0.1:3000"])
    temp_max_age_seconds: int = 3600
    start_worker: bool = True

    @property
    def uploads_dir(self) -> Path:
        return self.data_dir / "uploads"

    @property
    def tmp_dir(self) -> Path:
        return self.data_dir / "tmp"

    @property
    def db_path(self) -> Path:
        return self.data_dir / "verba.sqlite3"

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_mb * 1024 * 1024

    @property
    def max_storage_bytes(self) -> int:
        return self.max_storage_mb * 1024 * 1024

    def ensure_dirs(self) -> None:
        for path in (self.data_dir, self.uploads_dir, self.tmp_dir):
            path.mkdir(parents=True, exist_ok=True)

    @classmethod
    def from_env(cls) -> "Settings":
        data_dir = Path(os.environ.get("VERBA_DATA_DIR") or (BACKEND_ROOT / "data")).resolve()
        model_dir = os.environ.get("VERBA_WHISPER_MODEL_DIR")
        return cls(
            data_dir=data_dir,
            max_upload_mb=_int("VERBA_MAX_UPLOAD_MB", 500, 1),
            max_storage_mb=_int("VERBA_MAX_STORAGE_MB", 10_000, 1),
            max_concurrent_jobs=_int("VERBA_MAX_CONCURRENT_JOBS", 1, 1),
            max_media_duration_min=_int("VERBA_MAX_MEDIA_DURATION_MIN", 240, 1),
            max_job_attempts=_int("VERBA_MAX_JOB_ATTEMPTS", 2, 1),
            allowed_providers=_list("VERBA_ALLOWED_PROVIDERS", ["faster-whisper", "openai-whisper", "mock"]),
            default_provider=os.environ.get("VERBA_DEFAULT_PROVIDER", "auto").strip() or "auto",
            external_providers_enabled=_bool("VERBA_EXTERNAL_PROVIDERS_ENABLED", False),
            external_api_key=os.environ.get("VERBA_EXTERNAL_API_KEY", ""),
            whisper_model=os.environ.get("VERBA_WHISPER_MODEL", "base").strip() or "base",
            whisper_model_dir=Path(model_dir).resolve() if model_dir else None,
            whisper_device=os.environ.get("VERBA_WHISPER_DEVICE", "cpu").strip() or "cpu",
            whisper_compute_type=os.environ.get("VERBA_WHISPER_COMPUTE_TYPE", "int8").strip() or "int8",
            allow_model_download=_bool("VERBA_ALLOW_MODEL_DOWNLOAD", False),
            cors_origins=_list("VERBA_CORS_ORIGINS", ["http://localhost:3000", "http://127.0.0.1:3000"]),
            start_worker=_bool("VERBA_START_WORKER", True),
        )
