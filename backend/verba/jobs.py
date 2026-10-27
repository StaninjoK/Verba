"""Background job processing.

A dispatcher thread pulls pending jobs from SQLite and runs up to
``max_concurrent_jobs`` of them in worker threads. Because job state lives in
the database, a backend restart can pick up where it left off: interrupted
jobs are re-queued (up to the attempt limit) or marked failed.

Logs contain job/project ids and states only, never transcript text or
original filenames.
"""

from __future__ import annotations

import logging
import threading
import time
from pathlib import Path

from . import media, storage
from .config import Settings
from .db import Database, InvalidTransition
from .providers import Cancelled, ProviderError, ProviderRegistry

log = logging.getLogger("verba.jobs")

CLEANUP_INTERVAL_SECONDS = 600


class JobTimeout(Exception):
    pass


class JobManager:
    def __init__(self, settings: Settings, db: Database, registry: ProviderRegistry) -> None:
        self.settings = settings
        self.db = db
        self.registry = registry
        self._wake = threading.Condition()
        self._running: dict[str, threading.Thread] = {}
        self._stop = threading.Event()
        self._dispatcher: threading.Thread | None = None
        self._last_cleanup = 0.0

    # --------------------------------------------------------------- lifecycle
    def start(self) -> None:
        self.recover()
        self._stop.clear()
        self._dispatcher = threading.Thread(target=self._dispatch_loop, name="verba-dispatcher", daemon=True)
        self._dispatcher.start()

    def stop(self, timeout: float = 5.0) -> None:
        self._stop.set()
        self.wake()
        if self._dispatcher:
            self._dispatcher.join(timeout)
        for thread in list(self._running.values()):
            thread.join(timeout)

    def wake(self) -> None:
        with self._wake:
            self._wake.notify_all()

    def recover(self) -> None:
        """Re-queue or fail jobs that were active when the backend stopped."""
        for job in self.db.active_jobs():
            if job["status"] == "pending":
                continue
            try:
                if job["cancel_requested"]:
                    self.db.transition_job(job["id"], "cancelled")
                elif job["attempts"] < self.settings.max_job_attempts:
                    self.db.transition_job(job["id"], "pending", progress=None)
                    log.info("job %s re-queued after restart", job["id"])
                else:
                    self.db.transition_job(job["id"], "failed", error_code="interrupted",
                                           error_message="Processing was interrupted and the retry limit was reached.")
            except InvalidTransition:
                continue
        storage.cleanup_temp(self.settings.tmp_dir, 0)  # nothing is running yet, so all temp files are stale

    # ------------------------------------------------------------- public API
    def submit(self, project_id: str, provider_name: str, model: str | None, language: str | None) -> dict:
        job = self.db.create_job(project_id, provider_name, model, language)  # raises DuplicateJob
        log.info("job %s queued for project %s (provider=%s)", job["id"], project_id, provider_name)
        self.wake()
        return job

    def cancel(self, job_id: str) -> dict:
        job = self.db.get_job(job_id)
        if job is None:
            raise KeyError(job_id)
        if job["status"] == "pending":
            try:
                return self.db.transition_job(job_id, "cancelled", expected_from="pending")
            except InvalidTransition:
                job = self.db.get_job(job_id)  # picked up meanwhile; fall through
        if job and job["status"] in ("validating", "processing"):
            self.db.request_cancel(job_id)
            log.info("cancel requested for job %s", job_id)
        return self.db.get_job(job_id)  # type: ignore[return-value]

    def run_pending_once(self) -> bool:
        """Synchronously run the oldest pending job. Used by tests."""
        job = self.db.next_pending_job()
        if not job:
            return False
        self._run(job["id"])
        return True

    # --------------------------------------------------------------- internals
    def _dispatch_loop(self) -> None:
        while not self._stop.is_set():
            try:
                self._reap()
                while len(self._running) < self.settings.max_concurrent_jobs:
                    job = self.db.next_pending_job()
                    if not job or job["id"] in self._running:
                        break
                    thread = threading.Thread(target=self._run, args=(job["id"],), name=f"verba-job-{job['id'][:8]}",
                                              daemon=True)
                    self._running[job["id"]] = thread
                    thread.start()
                    time.sleep(0.01)  # let the thread move the job out of 'pending'
                if time.time() - self._last_cleanup > CLEANUP_INTERVAL_SECONDS:
                    self._last_cleanup = time.time()
                    self._cleanup_temp()
            except Exception:  # never let the dispatcher die
                log.exception("dispatcher error")
            with self._wake:
                self._wake.wait(timeout=1.0)

    def _reap(self) -> None:
        for job_id, thread in list(self._running.items()):
            if not thread.is_alive():
                self._running.pop(job_id, None)

    def _cleanup_temp(self) -> None:
        active = set(self._running)
        tmp = self.settings.tmp_dir
        cutoff = time.time() - self.settings.temp_max_age_seconds
        for item in tmp.iterdir() if tmp.exists() else []:
            if item.stem in active:
                continue
            try:
                if item.is_file() and item.stat().st_mtime < cutoff:
                    item.unlink()
            except OSError:
                pass

    def _timeout_for(self, duration: float | None) -> float:
        return max(float(self.settings.job_timeout_min_seconds), float(duration or 0) * self.settings.job_timeout_factor)

    def _run(self, job_id: str) -> None:
        wav_path: Path | None = None
        try:
            job = self.db.transition_job(job_id, "validating", expected_from="pending")
        except InvalidTransition:
            return  # cancelled or picked up elsewhere
        attempts = self.db.increment_attempts(job_id)
        try:
            project = self.db.get_project(job["project_id"])
            if project is None:
                raise ProviderError("project_missing", "The project no longer exists.")
            source = storage.confined_path(self.settings.uploads_dir, project["stored_filename"])
            if not source.exists():
                raise ProviderError("file_missing", "The uploaded file is missing from local storage.")
            ext = "." + project["stored_filename"].rsplit(".", 1)[1]
            info = media.probe(source, ext)

            wav_path = self.settings.tmp_dir / f"{job_id}.wav"
            media.convert_to_wav(source, wav_path)
            if self.db.is_cancel_requested(job_id):
                raise Cancelled()

            provider = self.registry.get(job["provider"])
            if not self.registry.allowed(provider.name):
                raise ProviderError("provider_disabled", "This transcription engine is disabled in the configuration.")
            self.db.transition_job(job_id, "processing", expected_from="validating", progress=None)

            deadline = time.monotonic() + self._timeout_for(info.duration_seconds)
            state = {"timed_out": False}

            def should_cancel() -> bool:
                if time.monotonic() > deadline:
                    state["timed_out"] = True
                    return True
                return self.db.is_cancel_requested(job_id)

            def on_progress(value: float | None) -> None:
                self.db.set_job_progress(job_id, None if value is None else max(0.0, min(1.0, float(value))))

            try:
                result = provider.transcribe(wav_path, language=job["language_requested"],
                                             duration_seconds=info.duration_seconds,
                                             on_progress=on_progress, should_cancel=should_cancel)
            except Cancelled:
                if state["timed_out"]:
                    raise JobTimeout()
                raise

            if self.db.is_cancel_requested(job_id):
                raise Cancelled()  # engine could not stop early; discard its result
            if time.monotonic() > deadline:
                raise JobTimeout()

            segments = [s.as_dict(i) for i, s in enumerate(result.segments) if s.text and s.text.strip()]
            if not segments:
                raise ProviderError("no_speech", "No speech was detected in this recording.")

            self.db.save_transcript_result(project["id"], segments=segments, language=result.language,
                                           provider=result.provider, model=result.model, is_mock=result.is_mock)
            self.db.transition_job(job_id, "completed", expected_from="processing", progress=1.0,
                                   error_code=None, error_message=None)
            log.info("job %s completed (%d segments)", job_id, len(segments))

        except Cancelled:
            self._finish(job_id, "cancelled")
            log.info("job %s cancelled", job_id)
        except JobTimeout:
            self._finish(job_id, "failed", "timeout", "Processing took longer than the configured limit.")
            log.warning("job %s timed out", job_id)
        except media.MediaError as exc:
            self._finish(job_id, "failed", exc.code, exc.message)
            log.info("job %s failed: %s", job_id, exc.code)
        except ProviderError as exc:
            if exc.retryable and attempts < self.settings.max_job_attempts and not self.db.is_cancel_requested(job_id):
                self._finish(job_id, "pending", exc.code, exc.message)
                log.warning("job %s failed with %s, retrying (attempt %d)", job_id, exc.code, attempts)
                self.wake()
            else:
                self._finish(job_id, "failed", exc.code, exc.message)
                log.info("job %s failed: %s", job_id, exc.code)
        except storage.UnsafePath:
            self._finish(job_id, "failed", "storage_error", "The stored file reference is invalid.")
            log.error("job %s refused an unsafe storage path", job_id)
        except Exception:
            self._finish(job_id, "failed", "internal_error", "An unexpected error occurred while processing.")
            log.exception("job %s crashed", job_id)
        finally:
            if wav_path is not None:
                wav_path.unlink(missing_ok=True)

    def _finish(self, job_id: str, status: str, code: str | None = None, message: str | None = None) -> None:
        try:
            fields = {"error_code": code, "error_message": message}
            if status == "pending":
                fields["progress"] = None
            self.db.transition_job(job_id, status, **fields)
        except InvalidTransition:
            log.warning("job %s could not move to %s", job_id, status)
