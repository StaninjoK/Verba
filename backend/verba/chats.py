"""WhatsApp chat imports: storage, background transcription and the combined text export.

A chat is processed item by item (voice notes, audio files, videos, images).
Progress is the real number of finished items. Every item's result is saved
as soon as it is ready, so a restart resumes where it stopped and a broken
voice note never sinks the whole chat.
"""

from __future__ import annotations

import json
import logging
import shutil
import threading
import time
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

from . import exports, media
from .config import Settings
from .db import Database, new_id, now_iso
from .providers import Cancelled, ProviderError, ProviderRegistry
from .whatsapp import ParsedChat

log = logging.getLogger("verba.chats")

AUDIO_KINDS = ("voice", "audio", "video")
FATAL_PROVIDER_CODES = {"provider_unavailable", "provider_disabled", "model_load_failed", "out_of_memory", "no_engine"}
# Below this confidence an auto-detected language on a short note is replaced by the chat's main language.
MIN_LANGUAGE_CONFIDENCE = 0.6
ACTIVE = ("pending", "processing")


class ChatStore:
    """Chat tables. Shares the connection and lock of ``Database``."""

    def __init__(self, db: Database) -> None:
        self.db = db

    def _exec(self, sql: str, params: tuple = ()) -> int:
        with self.db._lock:  # noqa: SLF001 - same module family, shared connection
            return self.db._conn.execute(sql, params).rowcount  # noqa: SLF001

    def create(self, *, title: str, original_filename: str, size_bytes: int, parsed: ParsedChat, provider: str,
               model: str | None, language: str | None, is_mock: bool) -> str:
        chat_id = new_id()
        ts = now_iso()
        items = sum(1 for m in parsed.messages if m.stored_name and m.kind in AUDIO_KINDS)
        with self.db._lock:  # noqa: SLF001
            conn = self.db._conn  # noqa: SLF001
            conn.execute("BEGIN")
            try:
                conn.execute(
                    "INSERT INTO chats (id, title, original_filename, size_bytes, participants, date_order, status, provider,"
                    " model, language_requested, is_mock, total_items, created_at, updated_at)"
                    " VALUES (?, ?, ?, ?, ?, ?, 'pending', ?, ?, ?, ?, ?, ?, ?)",
                    (chat_id, title, original_filename, size_bytes, json.dumps(parsed.participants, ensure_ascii=False),
                     parsed.date_order, provider, model, language, int(is_mock), items, ts, ts),
                )
                conn.executemany(
                    "INSERT INTO chat_messages (chat_id, idx, ts, sender, kind, text, attachment, stored_name, item_status)"
                    " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    [(chat_id, m.index, m.timestamp, m.sender, m.kind, m.text, m.attachment, m.stored_name,
                      "pending" if m.stored_name and m.kind in AUDIO_KINDS + ("image",) else None)
                     for m in parsed.messages],
                )
                conn.execute("COMMIT")
            except Exception:
                conn.execute("ROLLBACK")
                raise
        return chat_id

    def get(self, chat_id: str) -> dict | None:
        return self.db._one("SELECT * FROM chats WHERE id = ?", (chat_id,))  # noqa: SLF001

    def list(self, query: str | None = None) -> list[dict]:
        if query:
            like = "%" + query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"
            return self.db._all(  # noqa: SLF001
                "SELECT * FROM chats WHERE title LIKE ? ESCAPE '\\' OR id IN (SELECT chat_id FROM chat_messages WHERE"
                " text LIKE ? ESCAPE '\\' OR transcript LIKE ? ESCAPE '\\') ORDER BY updated_at DESC LIMIT 100",
                (like, like, like))
        return self.db._all("SELECT * FROM chats ORDER BY updated_at DESC LIMIT 100")  # noqa: SLF001

    def messages(self, chat_id: str) -> list[dict]:
        return self.db._all("SELECT * FROM chat_messages WHERE chat_id = ? ORDER BY idx", (chat_id,))  # noqa: SLF001

    def message(self, chat_id: str, idx: int) -> dict | None:
        return self.db._one("SELECT * FROM chat_messages WHERE chat_id = ? AND idx = ?", (chat_id, idx))  # noqa: SLF001

    def update(self, chat_id: str, **fields: Any) -> None:
        fields["updated_at"] = now_iso()
        cols = ", ".join(f"{k} = ?" for k in fields)
        self._exec(f"UPDATE chats SET {cols} WHERE id = ?", (*fields.values(), chat_id))

    def update_message(self, chat_id: str, idx: int, **fields: Any) -> None:
        cols = ", ".join(f"{k} = ?" for k in fields)
        self._exec(f"UPDATE chat_messages SET {cols} WHERE chat_id = ? AND idx = ?", (*fields.values(), chat_id, idx))
        self._exec("UPDATE chats SET updated_at = ? WHERE id = ?", (now_iso(), chat_id))

    def claim_next_pending(self) -> dict | None:
        """Atomically move the oldest pending chat to 'processing'."""
        with self.db._lock:  # noqa: SLF001
            row = self.db._conn.execute(  # noqa: SLF001
                "SELECT id FROM chats WHERE status = 'pending' ORDER BY created_at LIMIT 1").fetchone()
            if not row:
                return None
            ts = now_iso()
            self.db._conn.execute(  # noqa: SLF001
                "UPDATE chats SET status = 'processing', attempts = attempts + 1, started_at = COALESCE(started_at, ?),"
                " updated_at = ?, error_code = NULL, error_message = NULL WHERE id = ? AND status = 'pending'",
                (ts, ts, row["id"]))
        return self.get(row["id"])

    def delete(self, chat_id: str) -> None:
        self._exec("DELETE FROM chats WHERE id = ?", (chat_id,))

    def count_done(self, chat_id: str) -> int:
        row = self.db._one(  # noqa: SLF001
            "SELECT COUNT(*) AS n FROM chat_messages WHERE chat_id = ? AND kind IN ('voice','audio','video')"
            " AND stored_name IS NOT NULL AND item_status IN ('done','failed','skipped')", (chat_id,))
        return int(row["n"]) if row else 0

    def total_bytes(self) -> int:
        row = self.db._one("SELECT COALESCE(SUM(size_bytes), 0) AS n FROM chats")  # noqa: SLF001
        return int(row["n"]) if row else 0


class ChatManager:
    def __init__(self, settings: Settings, db: Database, registry: ProviderRegistry) -> None:
        self.settings = settings
        self.store = ChatStore(db)
        self.registry = registry
        self._wake = threading.Event()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def media_dir(self, chat_id: str) -> Path:
        return self.settings.data_dir / "chats" / chat_id

    # ------------------------------------------------------------------ lifecycle
    def start(self) -> None:
        self.recover()
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, name="verba-chats", daemon=True)
        self._thread.start()

    def stop(self, timeout: float = 5.0) -> None:
        self._stop.set()
        self._wake.set()
        if self._thread:
            self._thread.join(timeout)

    def recover(self) -> None:
        for chat in self.store.list():
            if chat["status"] == "processing":
                status = "cancelled" if chat["cancel_requested"] else "pending"
                self.store.update(chat["id"], status=status)
                log.info("chat %s %s after restart", chat["id"], "cancelled" if status == "cancelled" else "re-queued")

    def wake(self) -> None:
        self._wake.set()

    def _loop(self) -> None:
        while not self._stop.is_set():
            try:
                while not self._stop.is_set() and self.run_pending_once():
                    pass
            except Exception:
                log.exception("chat worker error")
            self._wake.wait(timeout=2.0)
            self._wake.clear()

    # --------------------------------------------------------------- public API
    def cancel(self, chat_id: str) -> None:
        chat = self.store.get(chat_id)
        if not chat:
            return
        if chat["status"] == "pending":
            self.store.update(chat_id, status="cancelled", finished_at=now_iso())
        elif chat["status"] == "processing":
            self.store.update(chat_id, cancel_requested=1)

    def restart(self, chat_id: str, *, provider: str, model: str | None, language: str | None, is_mock: bool,
                redo_all: bool = False) -> None:
        """Queue failed/remaining items again (or every item with ``redo_all``)."""
        states = ("pending", "failed", "done", "skipped") if redo_all else ("pending", "failed")
        marks = ",".join("?" * len(states))
        self.store._exec(  # noqa: SLF001
            f"UPDATE chat_messages SET item_status = 'pending', item_error = NULL WHERE chat_id = ? AND stored_name IS NOT NULL"
            f" AND kind IN ('voice','audio','video','image') AND item_status IN ({marks})", (chat_id, *states))
        self.store.update(chat_id, status="pending", provider=provider, model=model, language_requested=language,
                          is_mock=int(is_mock), cancel_requested=0, finished_at=None,
                          done_items=self.store.count_done(chat_id))
        self.wake()

    def delete(self, chat_id: str) -> None:
        self.store.delete(chat_id)
        shutil.rmtree(self.media_dir(chat_id), ignore_errors=True)

    def run_pending_once(self) -> bool:
        chat = self.store.claim_next_pending()
        if not chat:
            return False
        self._process(chat)
        return True

    # --------------------------------------------------------------- processing
    def _process(self, chat: dict) -> None:
        chat_id = chat["id"]
        log.info("chat %s processing started", chat_id)
        try:
            provider = self.registry.get(chat["provider"])
        except KeyError:
            self._fail(chat_id, "unknown_provider", "Unknown transcription engine.")
            return
        if not self.registry.allowed(provider.name) or not provider.is_available():
            self._fail(chat_id, "provider_unavailable", provider.capabilities().reason or "This engine is not available.")
            return

        forced = chat["language_requested"]
        languages: Counter[str] = Counter(m["transcript_language"] for m in self.store.messages(chat_id)
                                          if m["item_status"] == "done" and m["transcript_language"])
        failed = 0
        for msg in self.store.messages(chat_id):
            if msg["item_status"] != "pending" or not msg["stored_name"]:
                continue
            if self.store.get(chat_id)["cancel_requested"]:
                self.store.update(chat_id, status="cancelled", cancel_requested=0, finished_at=now_iso())
                log.info("chat %s cancelled", chat_id)
                return
            path = self.media_dir(chat_id) / msg["stored_name"]
            if msg["kind"] == "image":
                self._process_image(chat_id, msg, path)
                continue
            try:
                self._transcribe_item(chat_id, msg, path, provider, forced, languages)
            except Cancelled:
                self.store.update(chat_id, status="cancelled", cancel_requested=0, finished_at=now_iso())
                log.info("chat %s cancelled", chat_id)
                return
            except ProviderError as exc:
                if exc.code in FATAL_PROVIDER_CODES:
                    self._fail(chat_id, exc.code, exc.message)
                    return
                failed += 1
                self.store.update_message(chat_id, msg["idx"], item_status="failed", item_error=exc.code)
            except media.MediaError as exc:
                if exc.code == "ffmpeg_missing":
                    self._fail(chat_id, exc.code, exc.message)
                    return
                status = "skipped" if exc.code == "no_audio" else "failed"
                failed += status == "failed"
                self.store.update_message(chat_id, msg["idx"], item_status=status, item_error=exc.code)
            except Exception:
                failed += 1
                log.exception("chat %s item %s crashed", chat_id, msg["idx"])
                self.store.update_message(chat_id, msg["idx"], item_status="failed", item_error="internal_error")
            self.store.update(chat_id, done_items=self.store.count_done(chat_id))

        chat = self.store.get(chat_id)
        done = sum(1 for m in self.store.messages(chat_id) if m["kind"] in AUDIO_KINDS and m["item_status"] == "done")
        if chat["total_items"] and done == 0 and failed and failed == chat["total_items"]:
            self._fail(chat_id, "all_items_failed", "None of the voice notes could be transcribed.")
            return
        self.store.update(chat_id, status="completed", done_items=self.store.count_done(chat_id), finished_at=now_iso())
        log.info("chat %s completed (%d transcribed, %d failed)", chat_id, done, failed)

    def _transcribe_item(self, chat_id: str, msg: dict, path: Path, provider, forced: str | None,
                         languages: Counter) -> None:
        duration = media.probe_chat_audio(path)
        self.store.update_message(chat_id, msg["idx"], duration_seconds=duration)
        wav = self.settings.tmp_dir / f"chat-{chat_id}-{msg['idx']}.wav"
        deadline = time.monotonic() + max(120.0, duration * self.settings.job_timeout_factor)

        def should_cancel() -> bool:
            return time.monotonic() > deadline or bool(self.store.get(chat_id)["cancel_requested"])

        def run(language: str | None):
            with self.registry.engine_slots:
                return provider.transcribe(wav, language=language, duration_seconds=duration,
                                           on_progress=lambda _p: None, should_cancel=should_cancel)

        try:
            media.convert_to_wav(path, wav)
            result = run(forced)
            # Short notes are sometimes misdetected; fall back to the chat's main language when unsure.
            main = languages.most_common(1)[0][0] if languages else None
            if (not forced and main and result.language and result.language != main
                    and result.language_probability is not None and result.language_probability < MIN_LANGUAGE_CONFIDENCE):
                result = run(main)
        except Cancelled:
            if time.monotonic() > deadline:
                raise ProviderError("timeout", "Processing took longer than the configured limit.")
            raise
        finally:
            wav.unlink(missing_ok=True)

        text = " ".join(s.text.strip() for s in result.segments if s.text and s.text.strip())
        language = result.language or forced
        if language:
            languages[language] += 1
        self.store.update_message(chat_id, msg["idx"], transcript=text, transcript_language=language,
                                  item_status="done" if text else "failed", item_error=None if text else "no_speech")

    def _process_image(self, chat_id: str, msg: dict, path: Path) -> None:
        text = media.ocr_image(path) if path.exists() else None
        self.store.update_message(chat_id, msg["idx"], image_text=text, item_status="done")

    def _fail(self, chat_id: str, code: str, message: str) -> None:
        self.store.update(chat_id, status="failed", error_code=code, error_message=message, finished_at=now_iso())
        log.info("chat %s failed: %s", chat_id, code)


# ---------------------------------------------------------------------- export
LABELS = {
    "de": {"chat": "WhatsApp-Chat", "participants": "Teilnehmer", "period": "Zeitraum", "messages": "Nachrichten",
           "voice_notes": "Sprachnachrichten", "transcribed": "transkribiert", "images": "Bilder",
           "engine": "Transkribiert mit Verba", "mock": "ACHTUNG: Testdaten – keine echte Transkription",
           "voice": "Sprachnachricht", "audio": "Audiodatei", "video": "Video", "image": "Bild", "sticker": "Sticker",
           "document": "Dokument", "omitted": "Medien nicht im Export enthalten", "deleted": "Nachricht gelöscht",
           "system": "System", "language": "Sprache", "description": "Beschreibung", "image_text": "Text im Bild",
           "no_description": "ohne Beschreibung", "pending": "noch nicht transkribiert", "failed": "Transkription fehlgeschlagen",
           "skipped": "keine Tonspur", "caption": "Bildunterschrift", "missing": "Datei fehlt im Export",
           "generated": "Erstellt"},
    "en": {"chat": "WhatsApp chat", "participants": "Participants", "period": "Period", "messages": "Messages",
           "voice_notes": "Voice notes", "transcribed": "transcribed", "images": "Images",
           "engine": "Transcribed with Verba", "mock": "WARNING: test data – not a real transcription",
           "voice": "Voice note", "audio": "Audio file", "video": "Video", "image": "Image", "sticker": "Sticker",
           "document": "Document", "omitted": "Media not included in export", "deleted": "Message deleted",
           "system": "System", "language": "language", "description": "Description", "image_text": "Text in image",
           "no_description": "no description", "pending": "not transcribed yet", "failed": "transcription failed",
           "skipped": "no audio track", "caption": "Caption", "missing": "file missing from export",
           "generated": "Generated"},
    "es": {"chat": "Chat de WhatsApp", "participants": "Participantes", "period": "Periodo", "messages": "Mensajes",
           "voice_notes": "Notas de voz", "transcribed": "transcritas", "images": "Imágenes",
           "engine": "Transcrito con Verba", "mock": "ATENCIÓN: datos de prueba – no es una transcripción real",
           "voice": "Nota de voz", "audio": "Archivo de audio", "video": "Vídeo", "image": "Imagen", "sticker": "Sticker",
           "document": "Documento", "omitted": "Archivo no incluido en la exportación", "deleted": "Mensaje eliminado",
           "system": "Sistema", "language": "idioma", "description": "Descripción", "image_text": "Texto en la imagen",
           "no_description": "sin descripción", "pending": "aún sin transcribir", "failed": "la transcripción falló",
           "skipped": "sin pista de audio", "caption": "Pie de foto", "missing": "falta el archivo en la exportación",
           "generated": "Generado"},
}
ICONS = {"voice": "🎤", "audio": "🎵", "video": "🎬", "image": "🖼", "sticker": "🏷", "document": "📄"}


def _fmt_date(ts: str, lang: str) -> str:
    d = datetime.fromisoformat(ts)
    return d.strftime("%Y-%m-%d") if lang == "en" else d.strftime("%d.%m.%Y")


def _fmt_dur(seconds: float | None) -> str:
    if not seconds:
        return ""
    s = int(round(seconds))
    return f"{s // 60}:{s % 60:02d}"


def chat_stats(messages: list[dict]) -> dict:
    audio = [m for m in messages if m["kind"] in AUDIO_KINDS]
    langs = Counter(m["transcript_language"] for m in audio if m["transcript_language"])
    return {
        "messages": sum(1 for m in messages if m["kind"] != "system"),
        "voice_notes": sum(1 for m in audio if m["kind"] == "voice"),
        "audio_items": len(audio),
        "transcribed": sum(1 for m in audio if m["item_status"] == "done"),
        "failed": sum(1 for m in audio if m["item_status"] == "failed"),
        "images": sum(1 for m in messages if m["kind"] in ("image", "sticker")),
        "images_described": sum(1 for m in messages if m["kind"] in ("image", "sticker") and m["image_description"]),
        "main_language": langs.most_common(1)[0][0] if langs else None,
        "languages": dict(langs),
        "first": messages[0]["ts"] if messages else None,
        "last": messages[-1]["ts"] if messages else None,
    }


def message_line(m: dict, lang: str, main_language: str | None) -> str:
    """One message as a single line of plain text (multi-line texts keep their line breaks)."""
    L = LABELS.get(lang, LABELS["de"])
    time_s = datetime.fromisoformat(m["ts"]).strftime("%H:%M")
    if m["kind"] == "system" or not m["sender"]:
        return f"[{time_s}] — {m['text']}"
    head = f"[{time_s}] {m['sender']}"
    kind = m["kind"]
    if kind == "text":
        return f"{head}: {m['text']}"
    if kind == "deleted":
        return f"{head}: ({L['deleted']})"
    if kind == "omitted":
        return f"{head}: ({L['omitted']})"
    label = f"{ICONS.get(kind, '')} {L.get(kind, kind)}".strip()
    if kind in AUDIO_KINDS:
        details = [d for d in (_fmt_dur(m["duration_seconds"]),) if d]
        if m["transcript_language"] and m["transcript_language"] != main_language:
            details.append(f"{L['language']}: {m['transcript_language']}")
        label += f" ({', '.join(details)})" if details else ""
        if not m["stored_name"]:
            body = f"[{m['attachment']} – {L['missing']}]"
        elif m["item_status"] == "done":
            body = m["transcript"] or ""
        else:
            body = f"[{L.get(m['item_status'] or 'pending', L['pending'])}]"
    elif kind in ("image", "sticker"):
        parts = []
        if m["image_description"]:
            parts.append(f"{L['description']}: {m['image_description']}")
        if m["image_text"]:
            parts.append(f"{L['image_text']}: „{m['image_text']}“" if lang == "de" else f"{L['image_text']}: \"{m['image_text']}\"")
        if not m["stored_name"]:
            parts.append(f"[{m['attachment']} – {L['missing']}]")
        body = " | ".join(parts) if parts else f"({L['no_description']})"
    else:
        body = m["attachment"] or ""
    line = f"{head} – {label}: {body}"
    if m["text"]:
        line += f" | {L['caption']}: {m['text']}"
    return line


def render_chat(chat: dict, messages: list[dict], fmt: str, lang: str = "de") -> str | bytes:
    L = LABELS.get(lang, LABELS["de"])
    stats = chat_stats(messages)
    participants = json.loads(chat["participants"] or "[]")
    header = [f"{L['chat']}: {chat['title']}"]
    if participants:
        header.append(f"{L['participants']}: {', '.join(participants)}")
    if stats["first"]:
        header.append(f"{L['period']}: {_fmt_date(stats['first'], lang)} – {_fmt_date(stats['last'], lang)}")
    header.append(f"{L['messages']}: {stats['messages']} · {L['voice_notes']}: {stats['voice_notes']} "
                  f"({stats['transcribed']} {L['transcribed']}) · {L['images']}: {stats['images']}")
    engine = f"{L['engine']} ({chat['provider']}{' · ' + chat['model'] if chat['model'] and not chat['is_mock'] else ''})"
    header.append(engine)
    if chat["is_mock"]:
        header.append(L["mock"])

    if fmt == "json":
        payload = {"chat": {k: chat[k] for k in ("id", "title", "original_filename", "status", "provider", "model",
                                                  "language_requested", "is_mock")},
                   "participants": participants, "stats": stats,
                   "messages": [{k: m[k] for k in ("idx", "ts", "sender", "kind", "text", "attachment", "duration_seconds",
                                                   "transcript", "transcript_language", "item_status", "image_text",
                                                   "image_description")} for m in messages]}
        return json.dumps(payload, ensure_ascii=False, indent=2)

    blocks: list[tuple[str, bool]] = []  # (line, is_heading)
    day = None
    for m in messages:
        d = _fmt_date(m["ts"], lang)
        if d != day:
            day = d
            blocks.append((d, True))
        blocks.append((message_line(m, lang, stats["main_language"]), False))

    if fmt == "md":
        out = [f"# {header[0]}", "", *[f"- {h}" for h in header[1:]], ""]
        for text, heading in blocks:
            out.extend(["", f"## {text}", ""] if heading else [text.replace("\n", "  \n") + "  "])
        return "\n".join(out).strip() + "\n"
    if fmt == "docx":
        lines = [(h, False) for h in header[1:]] + [("", False)] + blocks
        return exports.docx_from_lines(header[0], lines)
    out = [*header]
    for text, heading in blocks:
        out.extend(["", f"── {text} ──"] if heading else [text])
    return "\n".join(out).strip() + "\n"
