"""HTTP API (FastAPI)."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import os
import re
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any
from urllib.parse import quote, unquote

from fastapi import FastAPI, HTTPException, Query, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse
from pydantic import BaseModel, Field

from . import exports, media, storage
from .config import Settings
from .db import ACTIVE_STATUSES, Database, DuplicateJob, VersionConflict
from .jobs import JobManager
from .providers import ProviderError, ProviderRegistry

log = logging.getLogger("verba.api")

# Whisper language codes offered in the UI. "auto" means automatic detection.
LANGUAGES = [
    "auto", "en", "de", "es", "fr", "it", "pt", "nl", "pl", "tr", "ru", "uk", "ar", "zh", "ja", "ko", "hi",
    "sv", "da", "no", "fi", "cs", "el", "ro", "hu", "he", "id", "vi", "th", "ca", "hr", "sk", "bg", "sr",
]

PAGE_CSP = (
    "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; "
    "img-src 'self' data: blob:; media-src 'self' blob:; font-src 'self' data:; connect-src 'self'; "
    "frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
)
TITLE_MAX = 200
SEGMENT_TEXT_MAX = 10_000
UPLOAD_CHUNK = 1024 * 1024


class RenameBody(BaseModel):
    title: str = Field(min_length=1, max_length=TITLE_MAX)


class TranscribeBody(BaseModel):
    provider: str = Field(default="auto", max_length=40)
    language: str = Field(default="auto", max_length=10)


class SegmentEdit(BaseModel):
    id: int
    text: str = Field(max_length=SEGMENT_TEXT_MAX)


class TranscriptBody(BaseModel):
    version: int
    segments: list[SegmentEdit]


def api_error(status: int, code: str, message: str) -> HTTPException:
    return HTTPException(status_code=status, detail={"code": code, "message": message})


def create_app(settings: Settings | None = None, registry: ProviderRegistry | None = None) -> FastAPI:
    settings = settings or Settings.from_env()
    if settings.require_auth and not settings.auth_password:
        raise RuntimeError("VERBA_REQUIRE_AUTH is set but VERBA_AUTH_PASSWORD is empty – refusing to start without a password.")
    settings.ensure_dirs()
    db = Database(settings.db_path)
    registry = registry or ProviderRegistry(settings)
    jobs = JobManager(settings, db, registry)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        if settings.start_worker:
            jobs.start()
        orphans = storage.find_orphan_uploads(settings.uploads_dir, db.stored_filenames())
        if orphans:
            log.warning("%d upload file(s) have no project record; see /api/system", len(orphans))
        yield
        jobs.stop()

    app = FastAPI(title="Verba API", version="0.1.0", lifespan=lifespan, docs_url="/api/docs", openapi_url="/api/openapi.json",
                  redoc_url=None)
    app.state.settings = settings
    app.state.db = db
    app.state.jobs = jobs
    app.state.registry = registry

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        allow_headers=["Content-Type", "X-Verba-Filename"],
        expose_headers=["Content-Disposition"],
        allow_credentials=False,
    )

    @app.middleware("http")
    async def security_headers(request: Request, call_next):
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Cache-Control", "no-store")
        path = request.url.path
        if path.startswith("/api/") and not path.startswith("/api/docs"):
            response.headers.setdefault("Content-Security-Policy", "default-src 'none'; media-src 'self'; frame-ancestors 'none'")
        elif not path.startswith("/api/"):
            response.headers.setdefault("Content-Security-Policy", PAGE_CSP)
        return response

    if settings.auth_password:
        expected = f"{settings.auth_user}:{settings.auth_password}".encode()

        @app.middleware("http")
        async def basic_auth(request: Request, call_next):
            # Shared-password gate for hosted use. /api/health stays open for platform health checks.
            if request.url.path == "/api/health" or request.method == "OPTIONS":
                return await call_next(request)
            header = request.headers.get("authorization", "")
            if header.lower().startswith("basic "):
                try:
                    supplied = base64.b64decode(header[6:].strip(), validate=True)
                except ValueError:
                    supplied = b""
                if hmac.compare_digest(supplied, expected):
                    return await call_next(request)
            return Response(status_code=401, headers={"WWW-Authenticate": 'Basic realm="Verba", charset="UTF-8"'},
                            content="Authentication required")

    @app.exception_handler(HTTPException)
    async def http_error(_: Request, exc: HTTPException):
        detail = exc.detail if isinstance(exc.detail, dict) else {"code": "error", "message": str(exc.detail)}
        return JSONResponse(status_code=exc.status_code, content={"error": detail})

    # ----------------------------------------------------------- serializers
    def job_out(job: dict | None) -> dict | None:
        if not job:
            return None
        provider = registry._providers.get(job["provider"])  # noqa: SLF001 - read-only lookup
        caps = provider.capabilities() if provider else None
        return {
            "id": job["id"],
            "status": job["status"],
            "provider": job["provider"],
            "model": job["model"],
            "language_requested": job["language_requested"],
            "progress": job["progress"],
            "progress_reported": bool(caps.reports_progress) if caps else False,
            "cancel_requested": bool(job["cancel_requested"]),
            "attempts": job["attempts"],
            "error": {"code": job["error_code"], "message": job["error_message"]} if job["error_code"] else None,
            "created_at": job["created_at"],
            "updated_at": job["updated_at"],
            "started_at": job["started_at"],
            "finished_at": job["finished_at"],
        }

    def project_status(project: dict, job: dict | None) -> str:
        if job:
            return job["status"]
        return "completed" if project["segments"] else "ready"

    def project_out(project: dict, job: dict | None, full: bool = False) -> dict[str, Any]:
        segments = json.loads(project["segments"]) if project["segments"] else []
        out = {
            "id": project["id"],
            "title": project["title"],
            "original_filename": project["original_filename"],
            "media_type": project["media_type"],
            "container": project["container"],
            "size_bytes": project["size_bytes"],
            "duration_seconds": project["duration_seconds"],
            "has_video": bool(project["has_video"]),
            "media_info": json.loads(project["media_info"] or "{}"),
            "language_detected": project["language_detected"],
            "provider": project["provider"],
            "model": project["model"],
            "is_mock": bool(project["is_mock"]),
            "has_transcript": bool(segments),
            "transcript_version": project["transcript_version"],
            "transcript_edited": bool(project["transcript_edited"]),
            "word_count": sum(len(s["text"].split()) for s in segments),
            "status": project_status(project, job),
            "job": job_out(job),
            "created_at": project["created_at"],
            "updated_at": project["updated_at"],
        }
        if full:
            out["segments"] = segments
        else:
            preview = " ".join(s["text"] for s in segments[:3])
            out["preview"] = preview[:220]
        return out

    def load_project(project_id: str) -> dict:
        if not storage.is_valid_id(project_id):
            raise api_error(404, "not_found", "Project not found.")
        project = db.get_project(project_id)
        if not project:
            raise api_error(404, "not_found", "Project not found.")
        return project

    # ---------------------------------------------------------------- system
    @app.get("/api/health")
    def health():
        return {"status": "ok"}

    @app.get("/api/system")
    def system():
        used = storage.directory_size(settings.uploads_dir)
        orphans = storage.find_orphan_uploads(settings.uploads_dir, db.stored_filenames())
        providers = registry.describe()
        real_ready = any(p["available"] and p["kind"] == "local" for p in providers)
        return {
            "version": app.version,
            "ffmpeg_available": media.ffmpeg_available(),
            "providers": providers,
            "real_engine_available": real_ready,
            "default_provider": settings.default_provider,
            "external_providers_enabled": settings.external_providers_enabled,
            "processing_location": "local",
            "limits": {
                "max_upload_bytes": settings.max_upload_bytes,
                "max_storage_bytes": settings.max_storage_bytes,
                "max_concurrent_jobs": settings.max_concurrent_jobs,
                "max_media_duration_seconds": settings.max_media_duration_min * 60,
            },
            "storage": {"used_bytes": used, "data_dir": str(settings.data_dir), "orphan_files": len(orphans)},
            "allowed_extensions": sorted(media.EXTENSION_FAMILIES),
            "languages": LANGUAGES,
        }

    # -------------------------------------------------------------- projects
    @app.get("/api/projects")
    def list_projects(q: str | None = Query(default=None, max_length=200)):
        projects = db.list_projects(q.strip() if q else None)
        latest = db.latest_jobs([p["id"] for p in projects])
        return {"projects": [project_out(p, latest.get(p["id"])) for p in projects]}

    @app.post("/api/projects", status_code=201)
    async def upload(request: Request):
        raw_name = request.headers.get("x-verba-filename", "")
        filename = storage.safe_display_name(unquote(raw_name)) if raw_name else ""
        if not filename:
            raise api_error(400, "missing_filename", "The file name is missing.")
        try:
            ext = media.check_extension(filename)
        except media.MediaError as exc:
            raise api_error(415, exc.code, exc.message)

        declared = request.headers.get("content-length")
        if declared and declared.isdigit() and int(declared) > settings.max_upload_bytes:
            raise api_error(413, "file_too_large", f"The file exceeds the {settings.max_upload_mb} MB limit.")
        if db.total_upload_bytes() >= settings.max_storage_bytes:
            raise api_error(507, "storage_full", "The local storage limit has been reached. Delete projects to free space.")

        tmp_path = settings.tmp_dir / f"upload-{os.urandom(8).hex()}.part"
        digest = hashlib.sha256()
        size = 0
        try:
            with tmp_path.open("wb") as fh:
                async for chunk in request.stream():
                    size += len(chunk)
                    if size > settings.max_upload_bytes:
                        raise api_error(413, "file_too_large", f"The file exceeds the {settings.max_upload_mb} MB limit.")
                    digest.update(chunk)
                    fh.write(chunk)
            if size == 0:
                raise api_error(400, "empty_file", "The file is empty.")
            if db.total_upload_bytes() + size > settings.max_storage_bytes:
                raise api_error(507, "storage_full", "Not enough local storage left for this file.")
            try:
                info = media.probe(tmp_path, ext)
            except media.MediaError as exc:
                status = 503 if exc.code == "ffmpeg_missing" else 422
                raise api_error(status, exc.code, exc.message)
            if info.duration_seconds > settings.max_media_duration_min * 60:
                raise api_error(413, "too_long", f"Recordings longer than {settings.max_media_duration_min} minutes are not supported.")

            sha = digest.hexdigest()
            duplicate = db.find_by_sha256(sha)
            stored = storage.new_stored_filename(ext)
            dest = storage.confined_path(settings.uploads_dir, stored)
            project = db.create_project(
                title=storage.title_from_filename(filename)[:TITLE_MAX],
                original_filename=filename,
                stored_filename=stored,
                media_type=media.MEDIA_TYPES[ext],
                container=info.container,
                size_bytes=size,
                sha256=sha,
                duration_seconds=info.duration_seconds,
                has_video=int(info.has_video),
                media_info=info.as_dict(),
            )
            try:
                os.replace(tmp_path, dest)
            except OSError:
                db.delete_project(project["id"])
                raise api_error(500, "storage_error", "The file could not be saved.")
            log.info("project %s created (%d bytes)", project["id"], size)
            out = project_out(project, None)
            out["duplicate_of"] = {"id": duplicate["id"], "title": duplicate["title"]} if duplicate else None
            return out
        finally:
            tmp_path.unlink(missing_ok=True)

    @app.get("/api/projects/{project_id}")
    def get_project(project_id: str):
        project = load_project(project_id)
        return project_out(project, db.latest_job(project_id), full=True)

    @app.patch("/api/projects/{project_id}")
    def rename(project_id: str, body: RenameBody):
        load_project(project_id)
        title = " ".join(body.title.split())
        if not title:
            raise api_error(422, "invalid_title", "The title cannot be empty.")
        db.rename_project(project_id, title)
        return project_out(db.get_project(project_id), db.latest_job(project_id))  # type: ignore[arg-type]

    @app.delete("/api/projects/{project_id}", status_code=204)
    def delete(project_id: str):
        project = load_project(project_id)
        job = db.latest_job(project_id)
        if job and job["status"] in ACTIVE_STATUSES:
            jobs.cancel(job["id"])
            job = db.get_job(job["id"])
            if job and job["status"] in ("validating", "processing"):
                raise api_error(409, "job_active", "Cancel the running transcription before deleting this project.")
        path = storage.confined_path(settings.uploads_dir, project["stored_filename"])
        db.delete_project(project_id)
        path.unlink(missing_ok=True)
        log.info("project %s deleted", project_id)
        return Response(status_code=204)

    # ------------------------------------------------------------------ jobs
    @app.post("/api/projects/{project_id}/transcribe", status_code=202)
    def transcribe(project_id: str, body: TranscribeBody):
        load_project(project_id)
        language = None if body.language in ("", "auto") else body.language
        if body.language not in LANGUAGES:
            raise api_error(422, "invalid_language", "Unsupported language code.")
        try:
            provider = registry.resolve(body.provider)
        except ProviderError as exc:
            raise api_error(409 if exc.code in ("no_engine", "provider_unavailable") else 403, exc.code, exc.message)
        try:
            job = jobs.submit(project_id, provider.name, provider.capabilities().model, language)
        except DuplicateJob as exc:
            raise api_error(409, "job_already_running", f"A transcription is already in progress ({exc.job_id}).")
        return job_out(job)

    @app.get("/api/jobs/{job_id}")
    def get_job(job_id: str):
        if not storage.is_valid_id(job_id) or not (job := db.get_job(job_id)):
            raise api_error(404, "not_found", "Job not found.")
        return job_out(job)

    @app.post("/api/jobs/{job_id}/cancel")
    def cancel_job(job_id: str):
        if not storage.is_valid_id(job_id) or not db.get_job(job_id):
            raise api_error(404, "not_found", "Job not found.")
        return job_out(jobs.cancel(job_id))

    # ------------------------------------------------------------ transcript
    @app.put("/api/projects/{project_id}/transcript")
    def save_transcript(project_id: str, body: TranscriptBody):
        project = load_project(project_id)
        job = db.latest_job(project_id)
        if job and job["status"] in ACTIVE_STATUSES:
            raise api_error(409, "job_active", "The transcript cannot be edited while a transcription is running.")
        segments = json.loads(project["segments"]) if project["segments"] else []
        if not segments:
            raise api_error(409, "no_transcript", "There is no transcript to edit yet.")
        edits = {e.id: e.text for e in body.segments}
        known = {s["id"] for s in segments}
        if set(edits) - known:
            raise api_error(422, "unknown_segment", "The edit references segments that do not exist.")
        for seg in segments:  # only text changes; timestamps stay as the engine produced them
            if seg["id"] in edits:
                seg["text"] = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", edits[seg["id"]])
        try:
            version = db.update_segments(project_id, segments, body.version)
        except VersionConflict:
            raise api_error(409, "version_conflict", "The transcript was changed elsewhere. Reload to continue.")
        return {"version": version, "saved_at": db.get_project(project_id)["updated_at"]}  # type: ignore[index]

    @app.get("/api/projects/{project_id}/export")
    def export(project_id: str, format: str = Query(pattern="^(txt|srt|vtt|docx|json)$"), timestamps: bool = False):
        project = load_project(project_id)
        segments = json.loads(project["segments"]) if project["segments"] else []
        if not segments:
            raise api_error(409, "no_transcript", "There is no transcript to export yet.")
        name = storage.download_filename(project["title"], format)
        disposition = f"attachment; filename=\"{name}\"; filename*=UTF-8''{quote(name)}"
        headers = {"Content-Disposition": disposition}
        if format == "txt":
            return PlainTextResponse(exports.to_txt(segments, timestamps), headers=headers, media_type="text/plain; charset=utf-8")
        if format == "srt":
            return PlainTextResponse(exports.to_srt(segments), headers=headers, media_type="application/x-subrip; charset=utf-8")
        if format == "vtt":
            return PlainTextResponse(exports.to_vtt(segments), headers=headers, media_type="text/vtt; charset=utf-8")
        if format == "json":
            payload = {"title": project["title"], "language": project["language_detected"], "provider": project["provider"],
                       "model": project["model"], "is_mock": bool(project["is_mock"]), "segments": segments}
            return JSONResponse(payload, headers=headers)
        return Response(exports.to_docx(project["title"], segments, timestamps), headers=headers,
                        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document")

    @app.get("/api/projects/{project_id}/media")
    def get_media(project_id: str):
        project = load_project(project_id)
        try:
            path = storage.confined_path(settings.uploads_dir, project["stored_filename"])
        except storage.UnsafePath:
            raise api_error(404, "not_found", "Media not found.")
        if not path.exists():
            raise api_error(404, "file_missing", "The media file is missing from local storage.")
        response = FileResponse(path, media_type=project["media_type"], content_disposition_type="inline",
                                filename=f"media{Path(project['stored_filename']).suffix}")
        response.headers["Cache-Control"] = "private, max-age=0, no-store"
        return response

    @app.get("/api/languages")
    def languages():
        return {"languages": LANGUAGES}

    if settings.static_dir:
        static_root = settings.static_dir

        @app.get("/{full_path:path}", include_in_schema=False)
        def static_files(full_path: str):
            # Serves the exported frontend (VERBA_STATIC_EXPORT=1 build). Never escapes static_root.
            if full_path.startswith("api/"):
                raise api_error(404, "not_found", "Not found.")
            clean = full_path.strip("/")
            candidates = [clean, f"{clean}.html", f"{clean}/index.html"] if clean else ["index.html"]
            for name in candidates:
                target = (static_root / name).resolve()
                if target.is_relative_to(static_root) and target.is_file():
                    response = FileResponse(target)
                    if clean.startswith("_next/static/"):
                        response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
                    else:
                        response.headers["Cache-Control"] = "no-cache"
                    return response
            not_found = static_root / "404.html"
            if not_found.is_file():
                return FileResponse(not_found, status_code=404)
            raise api_error(404, "not_found", "Not found.")

    return app
