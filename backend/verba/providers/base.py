"""The transcription provider interface.

Every engine (local Whisper, the test mock, a future cloud API) implements
``TranscriptionProvider``. The job worker only talks to this interface, so a
new engine can be added without touching the rest of the application.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Callable

ProgressCallback = Callable[[float | None], None]
CancelCheck = Callable[[], bool]


@dataclass
class Segment:
    start: float
    end: float
    text: str

    def as_dict(self, index: int) -> dict:
        return {"id": index, "start": round(self.start, 3), "end": round(self.end, 3), "text": self.text.strip()}


@dataclass
class TranscriptionResult:
    segments: list[Segment]
    language: str | None
    provider: str
    model: str | None
    is_mock: bool = False


@dataclass
class ProviderCapabilities:
    name: str
    label: str
    kind: str  # "local", "external" or "mock"
    available: bool
    reason: str | None = None
    model: str | None = None
    languages: str = "multilingual"
    language_detection: bool = False
    segment_timestamps: bool = False
    word_timestamps: bool = False
    reports_progress: bool = False
    supports_cancel: bool = False
    is_mock: bool = False
    sends_data_externally: bool = False
    details: dict = field(default_factory=dict)

    def as_dict(self) -> dict:
        return asdict(self)


class ProviderError(Exception):
    """Structured provider failure. ``code`` is stable; ``message`` is user-safe."""

    def __init__(self, code: str, message: str, retryable: bool = False) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.retryable = retryable


class Cancelled(Exception):
    pass


class TranscriptionProvider(ABC):
    name: str = "base"
    label: str = "Base"
    kind: str = "local"

    @abstractmethod
    def capabilities(self) -> ProviderCapabilities:
        """Describe availability, model and features. Must be cheap and offline."""

    def is_available(self) -> bool:
        return self.capabilities().available

    def validate_input(self, wav_path: Path) -> None:
        if not wav_path.exists() or wav_path.stat().st_size == 0:
            raise ProviderError("input_missing", "The prepared audio file is missing.")

    @abstractmethod
    def transcribe(
        self,
        wav_path: Path,
        *,
        language: str | None,
        duration_seconds: float | None,
        on_progress: ProgressCallback,
        should_cancel: CancelCheck,
    ) -> TranscriptionResult:
        """Transcribe a 16 kHz mono WAV file.

        ``on_progress`` receives a fraction in [0, 1] when real progress is
        known, or ``None`` when the engine cannot report it. Providers must not
        invent progress values. Raise ``Cancelled`` if ``should_cancel()``
        becomes true and the engine can stop early.
        """
