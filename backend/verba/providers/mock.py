"""Deterministic mock provider for tests and UI development.

Its output is always flagged ``is_mock=True`` and every segment is visibly
labelled, so it can never be mistaken for a real transcription.
"""

from __future__ import annotations

import time
from pathlib import Path

from .base import (
    Cancelled,
    ProviderCapabilities,
    ProviderError,
    Segment,
    TranscriptionProvider,
    TranscriptionResult,
)

MOCK_LINES = [
    "This is placeholder text from the test engine.",
    "No speech recognition was performed on this recording.",
    "Install a local Whisper engine to get a real transcript.",
    "Each line has a timestamp so exports can be tested.",
]


class MockProvider(TranscriptionProvider):
    name = "mock"
    label = "Test engine (no real transcription)"
    kind = "mock"

    def __init__(self, step_delay: float = 0.15, fail_with: str | None = None) -> None:
        self.step_delay = step_delay
        self.fail_with = fail_with

    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            name=self.name,
            label=self.label,
            kind=self.kind,
            available=True,
            model="mock",
            language_detection=False,
            segment_timestamps=True,
            reports_progress=True,
            supports_cancel=True,
            is_mock=True,
        )

    def transcribe(self, wav_path: Path, *, language, duration_seconds, on_progress, should_cancel) -> TranscriptionResult:
        self.validate_input(wav_path)
        if self.fail_with:
            raise ProviderError(self.fail_with, "The test engine was configured to fail.")
        duration = max(float(duration_seconds or 4.0), 0.5)
        count = max(1, min(len(MOCK_LINES), int(duration // 2) or 1))
        step = duration / count
        segments: list[Segment] = []
        for i in range(count):
            if should_cancel():
                raise Cancelled()
            time.sleep(self.step_delay)
            segments.append(Segment(start=i * step, end=min(duration, (i + 1) * step), text=f"[MOCK] {MOCK_LINES[i]}"))
            on_progress((i + 1) / count)
        return TranscriptionResult(segments=segments, language=language or None, provider=self.name, model="mock", is_mock=True)
