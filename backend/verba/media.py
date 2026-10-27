"""Media validation and conversion using FFmpeg/ffprobe.

Uploaded files are never executed. They are only read by ffprobe/ffmpeg with
the protocol whitelist restricted to local files, so a crafted playlist or
container cannot make FFmpeg open network resources or other local paths.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

PROBE_TIMEOUT_SECONDS = 60
CONVERT_TIMEOUT_SECONDS = 1800

# Container families we accept, keyed by what the file's leading bytes look like.
# The extension must agree with the sniffed family and ffprobe must agree too.
EXTENSION_FAMILIES: dict[str, set[str]] = {
    ".mp3": {"mp3"},
    ".wav": {"wav"},
    ".m4a": {"mp4"},
    ".mp4": {"mp4"},
    ".mov": {"mp4"},
    ".ogg": {"ogg"},
    ".oga": {"ogg"},
    ".opus": {"ogg"},
    ".flac": {"flac"},
    ".webm": {"webm"},
}

FFPROBE_FORMATS: dict[str, set[str]] = {
    "mp3": {"mp3"},
    "wav": {"wav"},
    "mp4": {"mov", "mp4", "m4a", "3gp", "3g2", "mj2"},
    "ogg": {"ogg"},
    "flac": {"flac"},
    "webm": {"matroska", "webm"},
}

MEDIA_TYPES: dict[str, str] = {
    ".mp3": "audio/mpeg",
    ".wav": "audio/wav",
    ".m4a": "audio/mp4",
    ".mp4": "video/mp4",
    ".mov": "video/quicktime",
    ".ogg": "audio/ogg",
    ".oga": "audio/ogg",
    ".opus": "audio/ogg",
    ".flac": "audio/flac",
    ".webm": "video/webm",
}


class MediaError(Exception):
    """A user-facing media problem. ``code`` is stable and safe to show."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass
class MediaInfo:
    family: str
    container: str
    duration_seconds: float
    has_video: bool
    audio_codec: str | None
    sample_rate: int | None
    channels: int | None
    bit_rate: int | None
    extra: dict = field(default_factory=dict)

    def as_dict(self) -> dict:
        return {
            "family": self.family,
            "container": self.container,
            "duration_seconds": self.duration_seconds,
            "has_video": self.has_video,
            "audio_codec": self.audio_codec,
            "sample_rate": self.sample_rate,
            "channels": self.channels,
            "bit_rate": self.bit_rate,
        }


def ffmpeg_available() -> bool:
    return shutil.which("ffmpeg") is not None and shutil.which("ffprobe") is not None


def sniff_family(head: bytes) -> str | None:
    """Identify the container from the first bytes of the file."""
    if len(head) < 12:
        return None
    if head[:4] == b"RIFF" and head[8:12] == b"WAVE":
        return "wav"
    if head[:3] == b"ID3":
        return "mp3"
    if head[0] == 0xFF and (head[1] & 0xE0) == 0xE0 and (head[1] & 0x06) != 0:
        return "mp3"  # MPEG audio frame sync without an ID3 tag
    if head[4:8] == b"ftyp":
        return "mp4"
    if head[:4] == b"OggS":
        return "ogg"
    if head[:4] == b"fLaC":
        return "flac"
    if head[:4] == b"\x1a\x45\xdf\xa3":
        return "webm"
    return None


def check_extension(filename: str) -> str:
    ext = Path(filename).suffix.lower()
    if ext not in EXTENSION_FAMILIES:
        raise MediaError("unsupported_format", "This file type is not supported.")
    return ext


def _run(cmd: list[str], timeout: int) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, timeout=timeout, check=False, stdin=subprocess.DEVNULL)


def probe(path: Path, extension: str) -> MediaInfo:
    """Validate a stored file's content and return its metadata."""
    if not ffmpeg_available():
        raise MediaError("ffmpeg_missing", "FFmpeg is not installed on this machine.")

    with path.open("rb") as fh:
        head = fh.read(64)
    family = sniff_family(head)
    if family is None or family not in EXTENSION_FAMILIES.get(extension, set()):
        raise MediaError("content_mismatch", "The file content does not match its extension or is not a supported media file.")

    cmd = [
        "ffprobe", "-v", "error", "-protocol_whitelist", "file",
        "-print_format", "json", "-show_format", "-show_streams",
        f"file:{path}",
    ]
    try:
        result = _run(cmd, PROBE_TIMEOUT_SECONDS)
    except subprocess.TimeoutExpired as exc:
        raise MediaError("probe_timeout", "Analysing the file took too long.") from exc
    if result.returncode != 0:
        raise MediaError("corrupt_file", "The file could not be read. It may be damaged or incomplete.")
    try:
        data = json.loads(result.stdout or b"{}")
    except json.JSONDecodeError as exc:
        raise MediaError("corrupt_file", "The file could not be read.") from exc

    fmt = data.get("format") or {}
    format_names = set((fmt.get("format_name") or "").split(","))
    if not format_names & FFPROBE_FORMATS[family]:
        raise MediaError("content_mismatch", "The file content does not match its extension.")

    streams = data.get("streams") or []
    audio = [s for s in streams if s.get("codec_type") == "audio"]
    video = [s for s in streams if s.get("codec_type") == "video" and not (s.get("disposition") or {}).get("attached_pic")]
    if not audio:
        raise MediaError("no_audio", "The file does not contain an audio track.")

    duration = _float(fmt.get("duration")) or _float(audio[0].get("duration"))
    if not duration or duration <= 0:
        raise MediaError("no_duration", "The recording length could not be determined, or the file is empty.")

    a = audio[0]
    return MediaInfo(
        family=family,
        container=sorted(format_names)[0] if format_names else family,
        duration_seconds=round(duration, 3),
        has_video=bool(video),
        audio_codec=a.get("codec_name"),
        sample_rate=_int(a.get("sample_rate")),
        channels=_int(a.get("channels")),
        bit_rate=_int(fmt.get("bit_rate")),
    )


def convert_to_wav(source: Path, target: Path, timeout: int = CONVERT_TIMEOUT_SECONDS) -> None:
    """Decode to 16 kHz mono PCM WAV, the input format Whisper expects."""
    cmd = [
        "ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error", "-y",
        "-protocol_whitelist", "file",
        "-i", f"file:{source}",
        "-vn", "-sn", "-dn", "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le",
        f"file:{target}",
    ]
    try:
        result = _run(cmd, timeout)
    except subprocess.TimeoutExpired as exc:
        target.unlink(missing_ok=True)
        raise MediaError("convert_timeout", "Converting the audio took too long.") from exc
    if result.returncode != 0 or not target.exists() or target.stat().st_size <= 44:
        target.unlink(missing_ok=True)
        raise MediaError("convert_failed", "The audio could not be decoded.")


def _float(value) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _int(value) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
