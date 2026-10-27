"""SQLite persistence for projects and transcription jobs.

All access goes through a single connection guarded by a lock. SQLite is more
than fast enough for a single-user local app, and the lock keeps the worker
threads and request handlers from interleaving writes.
"""

from __future__ import annotations

import json
import sqlite3
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA = """
CREATE TABLE IF NOT EXISTS projects (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    original_filename TEXT NOT NULL,
    stored_filename TEXT NOT NULL,
    media_type TEXT NOT NULL,
    container TEXT NOT NULL,
    size_bytes INTEGER NOT NULL,
    sha256 TEXT NOT NULL,
    duration_seconds REAL,
    has_video INTEGER NOT NULL DEFAULT 0,
    media_info TEXT NOT NULL DEFAULT '{}',
    language_detected TEXT,
    provider TEXT,
    model TEXT,
    is_mock INTEGER NOT NULL DEFAULT 0,
    segments TEXT,
    transcript_version INTEGER NOT NULL DEFAULT 0,
    transcript_edited INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS jobs (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    status TEXT NOT NULL,
    provider TEXT NOT NULL,
    model TEXT,
    language_requested TEXT,
    progress REAL,
    attempts INTEGER NOT NULL DEFAULT 0,
    cancel_requested INTEGER NOT NULL DEFAULT 0,
    error_code TEXT,
    error_message TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    started_at TEXT,
    finished_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_jobs_project ON jobs(project_id, created_at);
CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status, created_at);
CREATE INDEX IF NOT EXISTS idx_projects_sha ON projects(sha256);
"""

ACTIVE_STATUSES = ("pending", "validating", "processing")
TERMINAL_STATUSES = ("completed", "failed", "cancelled")

# Allowed job state transitions. Anything else is a programming error.
TRANSITIONS: dict[str, set[str]] = {
    "pending": {"validating", "cancelled", "failed"},
    "validating": {"processing", "failed", "cancelled", "pending"},
    "processing": {"completed", "failed", "cancelled", "pending"},
    "completed": set(),
    "failed": set(),
    "cancelled": set(),
}


class InvalidTransition(Exception):
    pass


class VersionConflict(Exception):
    pass


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def new_id() -> str:
    return uuid.uuid4().hex


class Database:
    def __init__(self, path: Path) -> None:
        self.path = path
        self._lock = threading.RLock()
        self._conn = sqlite3.connect(str(path), check_same_thread=False, isolation_level=None)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA foreign_keys = ON")
        self._conn.execute("PRAGMA journal_mode = WAL")
        self._conn.executescript(SCHEMA)

    def close(self) -> None:
        with self._lock:
            self._conn.close()

    # ------------------------------------------------------------------ helpers
    def _one(self, sql: str, params: tuple = ()) -> dict[str, Any] | None:
        with self._lock:
            row = self._conn.execute(sql, params).fetchone()
        return dict(row) if row else None

    def _all(self, sql: str, params: tuple = ()) -> list[dict[str, Any]]:
        with self._lock:
            rows = self._conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]

    def _exec(self, sql: str, params: tuple = ()) -> int:
        with self._lock:
            cur = self._conn.execute(sql, params)
            return cur.rowcount

    # ----------------------------------------------------------------- projects
    def create_project(self, **fields: Any) -> dict[str, Any]:
        project_id = fields.pop("id", None) or new_id()
        ts = now_iso()
        record = {
            "id": project_id,
            "media_info": json.dumps(fields.pop("media_info", {})),
            "created_at": ts,
            "updated_at": ts,
            **fields,
        }
        cols = ", ".join(record)
        marks = ", ".join("?" for _ in record)
        self._exec(f"INSERT INTO projects ({cols}) VALUES ({marks})", tuple(record.values()))
        return self.get_project(project_id)  # type: ignore[return-value]

    def get_project(self, project_id: str) -> dict[str, Any] | None:
        return self._one("SELECT * FROM projects WHERE id = ?", (project_id,))

    def list_projects(self, query: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
        if query:
            like = "%" + query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"
            return self._all(
                "SELECT * FROM projects WHERE title LIKE ? ESCAPE '\\' OR original_filename LIKE ? ESCAPE '\\' "
                "OR segments LIKE ? ESCAPE '\\' ORDER BY updated_at DESC LIMIT ?",
                (like, like, like, limit),
            )
        return self._all("SELECT * FROM projects ORDER BY updated_at DESC LIMIT ?", (limit,))

    def rename_project(self, project_id: str, title: str) -> bool:
        return self._exec(
            "UPDATE projects SET title = ?, updated_at = ? WHERE id = ?", (title, now_iso(), project_id)
        ) > 0

    def delete_project(self, project_id: str) -> bool:
        return self._exec("DELETE FROM projects WHERE id = ?", (project_id,)) > 0

    def find_by_sha256(self, sha256: str) -> dict[str, Any] | None:
        return self._one("SELECT * FROM projects WHERE sha256 = ? ORDER BY created_at DESC LIMIT 1", (sha256,))

    def total_upload_bytes(self) -> int:
        row = self._one("SELECT COALESCE(SUM(size_bytes), 0) AS total FROM projects")
        return int(row["total"]) if row else 0

    def stored_filenames(self) -> set[str]:
        return {r["stored_filename"] for r in self._all("SELECT stored_filename FROM projects")}

    def save_transcript_result(
        self,
        project_id: str,
        *,
        segments: list[dict[str, Any]],
        language: str | None,
        provider: str,
        model: str | None,
        is_mock: bool,
    ) -> None:
        with self._lock:
            self._conn.execute(
                "UPDATE projects SET segments = ?, language_detected = ?, provider = ?, model = ?, is_mock = ?, "
                "transcript_version = transcript_version + 1, transcript_edited = 0, updated_at = ? WHERE id = ?",
                (json.dumps(segments, ensure_ascii=False), language, provider, model, int(is_mock), now_iso(), project_id),
            )

    def update_segments(self, project_id: str, segments: list[dict[str, Any]], expected_version: int) -> int:
        """Persist edited segments using optimistic concurrency. Returns the new version."""
        with self._lock:
            cur = self._conn.execute(
                "UPDATE projects SET segments = ?, transcript_version = transcript_version + 1, "
                "transcript_edited = 1, updated_at = ? WHERE id = ? AND transcript_version = ?",
                (json.dumps(segments, ensure_ascii=False), now_iso(), project_id, expected_version),
            )
            if cur.rowcount == 0:
                raise VersionConflict()
            row = self._conn.execute("SELECT transcript_version FROM projects WHERE id = ?", (project_id,)).fetchone()
            return int(row["transcript_version"])

    # --------------------------------------------------------------------- jobs
    def create_job(self, project_id: str, provider: str, model: str | None, language: str | None) -> dict[str, Any]:
        """Create a pending job unless the project already has an active one."""
        ts = now_iso()
        job_id = new_id()
        with self._lock:
            self._conn.execute("BEGIN IMMEDIATE")
            try:
                active = self._conn.execute(
                    f"SELECT id FROM jobs WHERE project_id = ? AND status IN ({','.join('?' * len(ACTIVE_STATUSES))})",
                    (project_id, *ACTIVE_STATUSES),
                ).fetchone()
                if active:
                    self._conn.execute("ROLLBACK")
                    raise DuplicateJob(active["id"])
                self._conn.execute(
                    "INSERT INTO jobs (id, project_id, status, provider, model, language_requested, created_at, updated_at) "
                    "VALUES (?, ?, 'pending', ?, ?, ?, ?, ?)",
                    (job_id, project_id, provider, model, language, ts, ts),
                )
                self._conn.execute("UPDATE projects SET updated_at = ? WHERE id = ?", (ts, project_id))
                self._conn.execute("COMMIT")
            except DuplicateJob:
                raise
            except Exception:
                self._conn.execute("ROLLBACK")
                raise
        return self.get_job(job_id)  # type: ignore[return-value]

    def get_job(self, job_id: str) -> dict[str, Any] | None:
        return self._one("SELECT * FROM jobs WHERE id = ?", (job_id,))

    def latest_job(self, project_id: str) -> dict[str, Any] | None:
        return self._one(
            "SELECT * FROM jobs WHERE project_id = ? ORDER BY created_at DESC, rowid DESC LIMIT 1", (project_id,)
        )

    def latest_jobs(self, project_ids: list[str]) -> dict[str, dict[str, Any]]:
        if not project_ids:
            return {}
        marks = ",".join("?" * len(project_ids))
        rows = self._all(
            f"SELECT * FROM jobs WHERE project_id IN ({marks}) ORDER BY created_at ASC, rowid ASC", tuple(project_ids)
        )
        return {r["project_id"]: r for r in rows}  # later rows overwrite earlier ones

    def next_pending_job(self) -> dict[str, Any] | None:
        return self._one("SELECT * FROM jobs WHERE status = 'pending' ORDER BY created_at ASC LIMIT 1")

    def active_jobs(self) -> list[dict[str, Any]]:
        marks = ",".join("?" * len(ACTIVE_STATUSES))
        return self._all(f"SELECT * FROM jobs WHERE status IN ({marks})", ACTIVE_STATUSES)

    def transition_job(self, job_id: str, new_status: str, expected_from: str | None = None, **fields: Any) -> dict[str, Any]:
        with self._lock:
            row = self._conn.execute("SELECT status FROM jobs WHERE id = ?", (job_id,)).fetchone()
            if row is None:
                raise KeyError(job_id)
            current = row["status"]
            if expected_from is not None and current != expected_from:
                raise InvalidTransition(f"expected {expected_from}, found {current}")
            if new_status not in TRANSITIONS[current]:
                raise InvalidTransition(f"{current} -> {new_status}")
            ts = now_iso()
            updates = {"status": new_status, "updated_at": ts, **fields}
            if new_status == "validating" and "started_at" not in fields:
                updates["started_at"] = ts
            if new_status in TERMINAL_STATUSES:
                updates["finished_at"] = ts
            assignments = ", ".join(f"{k} = ?" for k in updates)
            self._conn.execute(
                f"UPDATE jobs SET {assignments} WHERE id = ? AND status = ?", (*updates.values(), job_id, current)
            )
        return self.get_job(job_id)  # type: ignore[return-value]

    def set_job_progress(self, job_id: str, progress: float | None) -> None:
        self._exec("UPDATE jobs SET progress = ?, updated_at = ? WHERE id = ?", (progress, now_iso(), job_id))

    def increment_attempts(self, job_id: str) -> int:
        with self._lock:
            self._conn.execute("UPDATE jobs SET attempts = attempts + 1 WHERE id = ?", (job_id,))
            row = self._conn.execute("SELECT attempts FROM jobs WHERE id = ?", (job_id,)).fetchone()
            return int(row["attempts"])

    def request_cancel(self, job_id: str) -> None:
        self._exec("UPDATE jobs SET cancel_requested = 1, updated_at = ? WHERE id = ?", (now_iso(), job_id))

    def is_cancel_requested(self, job_id: str) -> bool:
        row = self._one("SELECT cancel_requested FROM jobs WHERE id = ?", (job_id,))
        return bool(row and row["cancel_requested"])


class DuplicateJob(Exception):
    def __init__(self, job_id: str) -> None:
        super().__init__(job_id)
        self.job_id = job_id
