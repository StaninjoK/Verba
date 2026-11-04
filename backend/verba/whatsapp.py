"""Parsing of WhatsApp chat exports ("Export chat" → with or without media).

Supports the Android format (``04.11.26, 14:32 - Name: text``) and the iOS format
(``[04.11.26, 14:32:10] Name: text``) in the common date orders and in German,
English, Spanish, French, Italian and Portuguese wording for attachments.

Archives are untrusted input: members are never extracted under their own
names, only regular files of known media types are copied, and the total size
and file count are capped.
"""

from __future__ import annotations

import re
import shutil
import unicodedata
import uuid
import zipfile
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path, PurePosixPath

AUDIO_EXT = {".opus", ".ogg", ".oga", ".m4a", ".mp3", ".aac", ".amr", ".wav", ".flac", ".3ga"}
VIDEO_EXT = {".mp4", ".mov", ".3gp", ".mkv", ".webm", ".avi"}
IMAGE_EXT = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".heic", ".heif"}
DOC_EXT = {".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".txt", ".vcf", ".csv", ".zip"}
MEDIA_EXT = AUDIO_EXT | VIDEO_EXT | IMAGE_EXT | DOC_EXT

# Invisible marks WhatsApp sprinkles into exports (LRM, RLM, BOM, narrow no-break space …).
_INVISIBLE = dict.fromkeys(map(ord, "‎‏﻿‪‫‬‭‮⁦⁧⁨⁩"), None)

_DATE = r"(\d{1,4})[./-](\d{1,2})[./-](\d{1,4})"
_TIME = r"(\d{1,2})[:.](\d{2})(?:[:.](\d{2}))?(?:\s*([AaPp])\.?\s*[Mm]\.?)?"
IOS_RE = re.compile(rf"^\[{_DATE},?\s+{_TIME}\]\s(.*)$")
ANDROID_RE = re.compile(rf"^{_DATE},?\s+{_TIME}\s[-–]\s(.*)$")

ATTACH_PATTERNS = [
    re.compile(r"^<(?:attached|anhang|adjunto|adjuntos|pièce jointe|allegato|anexado|anexo|ek|прикреплено):\s*(.+?)>$", re.I),
    re.compile(r"^(.+?\.\w{2,5})\s*\((?:file attached|datei angehängt|archivo adjunto|fichier joint|file allegato|"
               r"arquivo anexado|ficheiro anexado|bestand bijgevoegd|dosya ekli)\)$", re.I),
]
OMITTED_RE = re.compile(
    r"^<?(?:media omitted|medien ausgeschlossen|multimedia omitido|archivo omitido|médias omis|media omessi|"
    r"mídia oculta|arquivo de mídia oculto|image omitted|audio omitted|video omitted|sticker omitted|"
    r"bild weggelassen|audio weggelassen|video weggelassen|sticker weggelassen|imagen omitida|audio omitido|"
    r"video omitido|sticker omitido|gif omitted|document omitted|dokument weggelassen|documento omitido)>?$",
    re.I,
)
CHAT_TXT_RE = re.compile(r"(^|/)(_chat\.txt|whatsapp[^/]*\.txt|chat[^/]*\.txt)$", re.I)


class ChatImportError(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass
class RawMessage:
    date_parts: tuple[int, int, int]
    time_parts: tuple[int, int, int]
    ampm: str | None
    body: str


@dataclass
class ChatMessage:
    index: int
    timestamp: str  # ISO 8601, local time as written in the export (no time zone)
    sender: str | None
    kind: str  # text | voice | audio | video | image | sticker | document | omitted | system | deleted
    text: str = ""
    attachment: str | None = None  # original file name inside the export
    stored_name: str | None = None  # file name under the chat's media directory


@dataclass
class ParsedChat:
    messages: list[ChatMessage]
    participants: list[str]
    date_order: str
    media: dict[str, str] = field(default_factory=dict)  # original name -> stored name


def _clean(line: str) -> str:
    return unicodedata.normalize("NFC", line.translate(_INVISIBLE)).replace(" ", " ").replace(" ", " ")


def split_raw(text: str) -> list[RawMessage]:
    """Split the export into messages; lines without a timestamp continue the previous message."""
    messages: list[RawMessage] = []
    for raw in text.splitlines():
        line = _clean(raw).rstrip()
        m = IOS_RE.match(line) or ANDROID_RE.match(line)
        if m:
            d1, d2, d3, hh, mm, ss, ampm, body = m.groups()
            messages.append(RawMessage((int(d1), int(d2), int(d3)), (int(hh), int(mm), int(ss or 0)),
                                       ampm.lower() if ampm else None, body))
        elif messages:
            messages[-1].body += "\n" + line
        # text before the first timestamp is ignored (should not happen in a real export)
    return messages


def detect_date_order(raws: list[RawMessage]) -> str:
    """Return 'ymd', 'dmy' or 'mdy' by looking at all dates of the export."""
    if raws and all(r.date_parts[0] > 31 for r in raws[:20]):
        return "ymd"
    first_gt12 = any(r.date_parts[0] > 12 for r in raws)
    second_gt12 = any(r.date_parts[1] > 12 for r in raws)
    if second_gt12 and not first_gt12:
        return "mdy"
    return "dmy"  # also the default when ambiguous (most WhatsApp locales outside the US)


def _to_datetime(r: RawMessage, order: str) -> datetime:
    a, b, c = r.date_parts
    if order == "ymd":
        year, month, day = a, b, c
    elif order == "mdy":
        month, day, year = a, b, c
    else:
        day, month, year = a, b, c
    if year < 100:
        year += 2000
    hour, minute, second = r.time_parts
    if r.ampm == "p" and hour < 12:
        hour += 12
    elif r.ampm == "a" and hour == 12:
        hour = 0
    return datetime(year, month, day, hour, minute, second)


def classify(name: str) -> str:
    ext = PurePosixPath(name).suffix.lower()
    upper = PurePosixPath(name).name.upper()
    if ext in AUDIO_EXT:
        return "voice" if (upper.startswith("PTT-") or "-AUDIO-" in upper or "AUDIO" in upper and ext == ".opus") else "audio"
    if ext in VIDEO_EXT:
        return "video"
    if ext in IMAGE_EXT:
        return "sticker" if upper.startswith("STK-") or "-STICKER-" in upper else "image"
    return "document"


def _attachment_name(body: str, available: set[str]) -> tuple[str | None, str]:
    """Return (attachment file name, remaining caption) if the message carries a file."""
    first, _, rest = body.partition("\n")
    candidate = first.strip()
    for pattern in ATTACH_PATTERNS:
        m = pattern.match(candidate)
        if m:
            return PurePosixPath(m.group(1).strip()).name, rest.strip()
    if candidate in available:
        return candidate, rest.strip()
    return None, body


DELETED_RE = re.compile(r"^(this message was deleted|you deleted this message|diese nachricht wurde gelöscht|"
                        r"du hast diese nachricht gelöscht|se eliminó este mensaje|eliminaste este mensaje|"
                        r"ce message a été supprimé|questo messaggio è stato eliminato|mensagem apagada)\.?$", re.I)


def parse_chat_text(text: str, available_media: set[str] | None = None) -> ParsedChat:
    available = available_media or set()
    raws = split_raw(text)
    if not raws:
        raise ChatImportError("not_a_chat", "No WhatsApp messages were found in this file.")
    order = detect_date_order(raws)
    messages: list[ChatMessage] = []
    participants: list[str] = []
    for raw in raws:
        try:
            ts = _to_datetime(raw, order).isoformat(timespec="seconds")
        except ValueError:
            continue  # impossible date: skip the line rather than guess
        sender, sep, body = raw.body.partition(": ")
        if not sep or len(sender) > 80 or "\n" in sender:
            messages.append(ChatMessage(len(messages), ts, None, "system", raw.body.strip()))
            continue
        sender = sender.strip()
        if sender not in participants:
            participants.append(sender)
        body = body.strip()
        attachment, caption = _attachment_name(body, available)
        if attachment:
            kind = classify(attachment)
            messages.append(ChatMessage(len(messages), ts, sender, kind, caption, attachment))
        elif OMITTED_RE.match(body.split("\n", 1)[0].strip()):
            messages.append(ChatMessage(len(messages), ts, sender, "omitted", ""))
        elif DELETED_RE.match(body):
            messages.append(ChatMessage(len(messages), ts, sender, "deleted", ""))
        else:
            messages.append(ChatMessage(len(messages), ts, sender, "text", body))
    if not messages:
        raise ChatImportError("not_a_chat", "No WhatsApp messages were found in this file.")
    return ParsedChat(messages=messages, participants=participants, date_order=order)


def _decode(data: bytes) -> str:
    for enc in ("utf-8-sig", "utf-16", "cp1252"):
        try:
            return data.decode(enc)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace")


def import_export(source: Path, media_dir: Path, *, max_total_bytes: int, max_files: int = 20_000) -> ParsedChat:
    """Read a WhatsApp export (.zip or plain .txt) and copy its media into ``media_dir`` under random names."""
    media_dir.mkdir(parents=True, exist_ok=True)
    with source.open("rb") as fh:
        is_zip = fh.read(4) == b"PK\x03\x04"

    if not is_zip:
        if source.stat().st_size > 50 * 1024 * 1024:
            raise ChatImportError("chat_too_large", "The chat text file is too large.")
        return parse_chat_text(_decode(source.read_bytes()))

    try:
        zf = zipfile.ZipFile(source)
    except zipfile.BadZipFile as exc:
        raise ChatImportError("bad_archive", "The ZIP archive could not be read.") from exc
    with zf:
        infos = [i for i in zf.infolist() if not i.is_dir()]
        if len(infos) > max_files:
            raise ChatImportError("too_many_files", "The archive contains too many files.")
        total = sum(i.file_size for i in infos)
        if total > max_total_bytes:
            raise ChatImportError("chat_too_large", "The unpacked chat export is larger than the configured limit.")
        for info in infos:  # zip-bomb guard: refuse absurd compression ratios
            if info.compress_size and info.file_size / info.compress_size > 200 and info.file_size > 10 * 1024 * 1024:
                raise ChatImportError("bad_archive", "The archive looks unsafe (extreme compression).")

        chat_candidates = [i for i in infos if CHAT_TXT_RE.search(i.filename.replace("\\", "/"))]
        if not chat_candidates:
            chat_candidates = [i for i in infos if i.filename.lower().endswith(".txt")]
        if not chat_candidates:
            raise ChatImportError("no_chat_file", "No chat text file (_chat.txt) was found in the archive.")
        chat_info = max(chat_candidates, key=lambda i: i.file_size)
        if chat_info.file_size > 50 * 1024 * 1024:
            raise ChatImportError("chat_too_large", "The chat text file is too large.")

        by_name: dict[str, zipfile.ZipInfo] = {}
        for info in infos:
            if info is chat_info:
                continue
            # symlinks are stored with Unix mode S_IFLNK in the high bits – skip them
            if (info.external_attr >> 16) & 0o170000 == 0o120000:
                continue
            name = PurePosixPath(info.filename.replace("\\", "/")).name
            if name and PurePosixPath(name).suffix.lower() in MEDIA_EXT:
                by_name.setdefault(name, info)

        parsed = parse_chat_text(_decode(zf.read(chat_info)), set(by_name))
        for msg in parsed.messages:
            if not msg.attachment or msg.attachment not in by_name:
                continue
            if msg.attachment not in parsed.media:
                ext = PurePosixPath(msg.attachment).suffix.lower()
                stored = f"{uuid.uuid4().hex}{ext}"
                with zf.open(by_name[msg.attachment]) as src, (media_dir / stored).open("wb") as dst:
                    shutil.copyfileobj(src, dst, 1024 * 1024)
                parsed.media[msg.attachment] = stored
            msg.stored_name = parsed.media[msg.attachment]
    return parsed


def chat_title(filename: str, participants: list[str]) -> str:
    stem = PurePosixPath(filename.replace("\\", "/")).stem
    for prefix in ("WhatsApp Chat with ", "WhatsApp Chat mit ", "Chat de WhatsApp con ", "WhatsApp Chat - ",
                   "WhatsApp-Chat mit ", "Chat WhatsApp avec "):
        if stem.lower().startswith(prefix.lower()):
            return stem[len(prefix):].strip() or stem
    if stem.lower() in {"_chat", "chat", "whatsapp chat"} and participants:
        return ", ".join(participants[:3])
    return stem or "WhatsApp-Chat"
