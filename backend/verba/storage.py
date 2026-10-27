"""Filesystem helpers: safe names, confined paths, usage accounting and cleanup."""

from __future__ import annotations

import logging
import re
import time
import unicodedata
import uuid
from pathlib import Path

log = logging.getLogger("verba.storage")

_ID_RE = re.compile(r"^[0-9a-f]{32}$")
_STORED_RE = re.compile(r"^[0-9a-f]{32}\.[a-z0-9]{1,5}$")


class UnsafePath(Exception):
    pass


def is_valid_id(value: str) -> bool:
    return bool(_ID_RE.match(value or ""))


def safe_display_name(filename: str, max_length: int = 120) -> str:
    """Return a printable, single-line version of a user-supplied filename.

    It is only ever used for display and as a default title. It is never used
    to build a filesystem path.
    """
    name = unicodedata.normalize("NFKC", filename or "")
    name = name.replace("\\", "/").split("/")[-1]
    name = "".join(ch for ch in name if unicodedata.category(ch)[0] != "C")
    name = re.sub(r"\s+", " ", name).strip().strip(".")
    if not name:
        name = "Untitled"
    return name[:max_length]


def title_from_filename(filename: str) -> str:
    name = safe_display_name(filename)
    stem = name.rsplit(".", 1)[0] if "." in name else name
    return stem.strip() or "Untitled"


def download_filename(title: str, extension: str) -> str:
    """ASCII-only filename for Content-Disposition headers."""
    ascii_title = unicodedata.normalize("NFKD", title).encode("ascii", "ignore").decode("ascii")
    ascii_title = re.sub(r"[^A-Za-z0-9._ -]+", "", ascii_title).strip(" .") or "transcript"
    ascii_title = re.sub(r"\s+", "_", ascii_title)[:80]
    return f"{ascii_title}.{extension}"


def new_stored_filename(extension: str) -> str:
    ext = extension.lower().lstrip(".")
    if not re.fullmatch(r"[a-z0-9]{1,5}", ext):
        raise UnsafePath("invalid extension")
    return f"{uuid.uuid4().hex}.{ext}"


def confined_path(base: Path, name: str) -> Path:
    """Resolve ``name`` inside ``base`` and refuse anything that escapes it."""
    if not _STORED_RE.match(name or ""):
        raise UnsafePath("invalid stored filename")
    base_resolved = base.resolve()
    candidate = (base_resolved / name).resolve()
    if candidate.parent != base_resolved:
        raise UnsafePath("path escapes storage directory")
    return candidate


def directory_size(path: Path) -> int:
    total = 0
    if not path.exists():
        return 0
    for item in path.rglob("*"):
        try:
            if item.is_file() and not item.is_symlink():
                total += item.stat().st_size
        except OSError:
            continue
    return total


def cleanup_temp(tmp_dir: Path, max_age_seconds: int) -> int:
    """Delete abandoned temporary files older than ``max_age_seconds``."""
    removed = 0
    if not tmp_dir.exists():
        return 0
    cutoff = time.time() - max_age_seconds
    for item in tmp_dir.iterdir():
        try:
            if item.is_file() and item.stat().st_mtime < cutoff:
                item.unlink()
                removed += 1
        except OSError:
            log.warning("could not remove temp file %s", item.name)
    if removed:
        log.info("removed %d abandoned temp files", removed)
    return removed


def find_orphan_uploads(uploads_dir: Path, known: set[str]) -> list[Path]:
    """Upload files with no project record (e.g. after a crash mid-upload).

    These are reported, not deleted automatically, so no user data is removed
    silently.
    """
    if not uploads_dir.exists():
        return []
    return [p for p in uploads_dir.iterdir() if p.is_file() and p.name not in known]
