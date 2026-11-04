"""HTTP routes for WhatsApp chat imports."""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from urllib.parse import quote, unquote

from fastapi import FastAPI, HTTPException, Query, Request, Response
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse
from pydantic import BaseModel, Field

from . import storage
from .chats import ACTIVE, AUDIO_KINDS, ChatManager, chat_stats, render_chat
from .config import Settings
from .db import Database
from .providers import ProviderError, ProviderRegistry
from .whatsapp import ChatImportError, chat_title, import_export

log = logging.getLogger("verba.chats")

MEDIA_TYPES = {
    ".opus": "audio/ogg", ".ogg": "audio/ogg", ".oga": "audio/ogg", ".m4a": "audio/mp4", ".mp3": "audio/mpeg",
    ".aac": "audio/aac", ".wav": "audio/wav", ".flac": "audio/flac", ".amr": "audio/amr", ".3ga": "audio/3gpp",
    ".mp4": "video/mp4", ".mov": "video/quicktime", ".3gp": "video/3gpp", ".webm": "video/webm", ".mkv": "video/x-matroska",
    ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp", ".gif": "image/gif",
    ".heic": "image/heic", ".heif": "image/heif",
}


def _err(status: int, code: str, message: str) -> HTTPException:
    return HTTPException(status_code=status, detail={"code": code, "message": message})


class ChatRename(BaseModel):
    title: str = Field(min_length=1, max_length=200)


class ChatRetry(BaseModel):
    provider: str = Field(default="auto", max_length=40)
    language: str = Field(default="auto", max_length=10)
    redo_all: bool = False


class MessageEdit(BaseModel):
    transcript: str | None = Field(default=None, max_length=100_000)
    image_description: str | None = Field(default=None, max_length=20_000)


def register_chat_routes(app: FastAPI, settings: Settings, db: Database, registry: ProviderRegistry,
                         manager: ChatManager, languages: list[str]) -> None:
    store = manager.store

    def load(chat_id: str) -> dict:
        if not storage.is_valid_id(chat_id) or not (chat := store.get(chat_id)):
            raise _err(404, "not_found", "Chat not found.")
        return chat

    def resolve(provider_name: str, language: str):
        if language not in languages:
            raise _err(422, "invalid_language", "Unsupported language code.")
        try:
            provider = registry.resolve(provider_name)
        except ProviderError as exc:
            raise _err(409 if exc.code in ("no_engine", "provider_unavailable") else 403, exc.code, exc.message)
        caps = provider.capabilities()
        return provider, caps, (None if language == "auto" else language)

    def chat_out(chat: dict, messages: list[dict] | None = None) -> dict:
        msgs = messages if messages is not None else store.messages(chat["id"])
        out = {
            "id": chat["id"], "title": chat["title"], "original_filename": chat["original_filename"],
            "size_bytes": chat["size_bytes"], "participants": json.loads(chat["participants"] or "[]"),
            "status": chat["status"], "provider": chat["provider"], "model": chat["model"],
            "language_requested": chat["language_requested"], "is_mock": bool(chat["is_mock"]),
            "total_items": chat["total_items"], "done_items": chat["done_items"],
            "cancel_requested": bool(chat["cancel_requested"]), "attempts": chat["attempts"],
            "error": {"code": chat["error_code"], "message": chat["error_message"]} if chat["error_code"] else None,
            "created_at": chat["created_at"], "updated_at": chat["updated_at"], "started_at": chat["started_at"],
            "finished_at": chat["finished_at"], "stats": chat_stats(msgs) if msgs else None,
        }
        return out

    def message_out(m: dict) -> dict:
        return {k: m[k] for k in ("idx", "ts", "sender", "kind", "text", "attachment", "duration_seconds", "transcript",
                                  "transcript_language", "item_status", "item_error", "image_text", "image_description")} | {
            "has_media": bool(m["stored_name"])}

    @app.post("/api/chats", status_code=201)
    async def import_chat(request: Request, provider: str = Query("auto", max_length=40),
                          language: str = Query("auto", max_length=10)):
        raw_name = request.headers.get("x-verba-filename", "")
        filename = storage.safe_display_name(unquote(raw_name)) if raw_name else ""
        if not filename or Path(filename).suffix.lower() not in (".zip", ".txt"):
            raise _err(415, "unsupported_chat_file", "Upload the WhatsApp export as .zip (with media) or .txt.")
        prov, caps, lang = resolve(provider, language)
        limit = settings.max_chat_import_mb * 1024 * 1024
        declared = request.headers.get("content-length")
        if declared and declared.isdigit() and int(declared) > limit:
            raise _err(413, "file_too_large", f"The export exceeds the {settings.max_chat_import_mb} MB limit.")
        if db.total_upload_bytes() + store.total_bytes() >= settings.max_storage_bytes:
            raise _err(507, "storage_full", "The local storage limit has been reached. Delete projects to free space.")

        tmp = settings.tmp_dir / f"upload-{os.urandom(8).hex()}.part"
        size = 0
        chat_id = None
        staging = settings.data_dir / "chats" / f"staging-{os.urandom(8).hex()}"
        try:
            with tmp.open("wb") as fh:
                async for chunk in request.stream():
                    size += len(chunk)
                    if size > limit:
                        raise _err(413, "file_too_large", f"The export exceeds the {settings.max_chat_import_mb} MB limit.")
                    fh.write(chunk)
            if size == 0:
                raise _err(400, "empty_file", "The file is empty.")
            try:
                parsed = import_export(tmp, staging, max_total_bytes=limit * 3)
            except ChatImportError as exc:
                raise _err(422, exc.code, exc.message)
            chat_id = store.create(title=chat_title(filename, parsed.participants)[:200], original_filename=filename,
                                   size_bytes=size, parsed=parsed, provider=prov.name, model=caps.model, language=lang,
                                   is_mock=caps.is_mock)
            staging.rename(manager.media_dir(chat_id))
        finally:
            tmp.unlink(missing_ok=True)
            if staging.exists():
                import shutil

                shutil.rmtree(staging, ignore_errors=True)
        manager.wake()
        log.info("chat %s imported (%d bytes)", chat_id, size)
        return chat_out(store.get(chat_id))  # type: ignore[arg-type]

    @app.get("/api/chats")
    def list_chats(q: str | None = Query(default=None, max_length=200)):
        return {"chats": [chat_out(c, []) for c in store.list(q.strip() if q else None)]}

    @app.get("/api/chats/{chat_id}")
    def get_chat(chat_id: str):
        chat = load(chat_id)
        msgs = store.messages(chat_id)
        return chat_out(chat, msgs) | {"messages": [message_out(m) for m in msgs]}

    @app.patch("/api/chats/{chat_id}")
    def rename_chat(chat_id: str, body: ChatRename):
        load(chat_id)
        title = " ".join(body.title.split())
        if not title:
            raise _err(422, "invalid_title", "The title cannot be empty.")
        store.update(chat_id, title=title)
        return chat_out(store.get(chat_id), [])  # type: ignore[arg-type]

    @app.delete("/api/chats/{chat_id}", status_code=204)
    def delete_chat(chat_id: str):
        chat = load(chat_id)
        if chat["status"] == "processing":
            raise _err(409, "job_active", "Cancel the running transcription before deleting this chat.")
        manager.delete(chat_id)
        log.info("chat %s deleted", chat_id)
        return Response(status_code=204)

    @app.post("/api/chats/{chat_id}/cancel")
    def cancel_chat(chat_id: str):
        load(chat_id)
        manager.cancel(chat_id)
        return chat_out(store.get(chat_id), [])  # type: ignore[arg-type]

    @app.post("/api/chats/{chat_id}/retry", status_code=202)
    def retry_chat(chat_id: str, body: ChatRetry):
        chat = load(chat_id)
        if chat["status"] in ACTIVE:
            raise _err(409, "job_already_running", "This chat is already being processed.")
        prov, caps, lang = resolve(body.provider, body.language)
        manager.restart(chat_id, provider=prov.name, model=caps.model, language=lang, is_mock=caps.is_mock,
                        redo_all=body.redo_all)
        return chat_out(store.get(chat_id), [])  # type: ignore[arg-type]

    @app.patch("/api/chats/{chat_id}/messages/{idx}")
    def edit_message(chat_id: str, idx: int, body: MessageEdit):
        load(chat_id)
        msg = store.message(chat_id, idx)
        if not msg:
            raise _err(404, "not_found", "Message not found.")
        fields = {}
        if body.transcript is not None:
            if msg["kind"] not in AUDIO_KINDS:
                raise _err(422, "not_audio", "Only voice notes, audio and video have a transcript.")
            fields.update(transcript=body.transcript.strip(), item_status="done", item_error=None)
        if body.image_description is not None:
            if msg["kind"] not in ("image", "sticker"):
                raise _err(422, "not_image", "Only images have a description.")
            fields["image_description"] = body.image_description.strip() or None
        if fields:
            store.update_message(chat_id, idx, **fields)
        return message_out(store.message(chat_id, idx))  # type: ignore[arg-type]

    @app.get("/api/chats/{chat_id}/export")
    def export_chat(chat_id: str, format: str = Query("txt", pattern="^(txt|md|docx|json)$"),
                    lang: str = Query("de", pattern="^(de|en|es)$")):
        chat = load(chat_id)
        content = render_chat(chat, store.messages(chat_id), format, lang)
        name = storage.download_filename(f"WhatsApp {chat['title']}", format)
        headers = {"Content-Disposition": f"attachment; filename=\"{name}\"; filename*=UTF-8''{quote(name)}"}
        if format == "docx":
            return Response(content, headers=headers,
                            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
        if format == "json":
            return JSONResponse(json.loads(content), headers=headers)
        media_type = "text/markdown; charset=utf-8" if format == "md" else "text/plain; charset=utf-8"
        return PlainTextResponse(content, headers=headers, media_type=media_type)

    @app.get("/api/chats/{chat_id}/media/{idx}")
    def chat_media(chat_id: str, idx: int):
        load(chat_id)
        msg = store.message(chat_id, idx)
        if not msg or not msg["stored_name"]:
            raise _err(404, "not_found", "Media not found.")
        ext = Path(msg["stored_name"]).suffix.lower()
        if ext not in MEDIA_TYPES:  # documents are not served back; avoids rendering arbitrary content
            raise _err(404, "not_found", "Media not found.")
        try:
            path = storage.confined_path(manager.media_dir(chat_id), msg["stored_name"])
        except storage.UnsafePath:
            raise _err(404, "not_found", "Media not found.")
        if not path.exists():
            raise _err(404, "file_missing", "The media file is missing from local storage.")
        response = FileResponse(path, media_type=MEDIA_TYPES[ext], content_disposition_type="inline", filename=f"media{ext}")
        response.headers["Cache-Control"] = "private, max-age=0, no-store"
        return response
