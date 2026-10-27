"""Local Whisper via the original ``openai-whisper`` package (runs offline, no API).

Slower than faster-whisper on CPU and cannot report progress or stop early,
so the UI shows an indeterminate indicator for jobs using this engine.
"""

from __future__ import annotations

import importlib.util
import os
import threading
from pathlib import Path

from ..config import Settings
from .base import ProviderCapabilities, ProviderError, Segment, TranscriptionProvider, TranscriptionResult


def _weights_path(settings: Settings) -> Path:
    root = settings.whisper_model_dir or Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache")) / "whisper"
    return root / f"{settings.whisper_model}.pt"


class OpenAIWhisperProvider(TranscriptionProvider):
    name = "openai-whisper"
    label = "Whisper (local, reference implementation)"
    kind = "local"

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._model = None
        self._lock = threading.Lock()

    def capabilities(self) -> ProviderCapabilities:
        installed = importlib.util.find_spec("whisper") is not None and importlib.util.find_spec("torch") is not None
        weights = _weights_path(self.settings)
        present = weights.exists()
        reason = None
        if not installed:
            reason = "openai-whisper is not installed. See docs/WHISPER_SETUP.md."
        elif not present and not self.settings.allow_model_download:
            reason = f"Model file {weights.name} is not downloaded yet. See docs/WHISPER_SETUP.md."
        return ProviderCapabilities(
            name=self.name,
            label=self.label,
            kind=self.kind,
            available=installed and (present or self.settings.allow_model_download),
            reason=reason,
            model=self.settings.whisper_model,
            language_detection=True,
            segment_timestamps=True,
            reports_progress=False,
            supports_cancel=False,
            details={"weights_path": str(weights)},
        )

    def transcribe(self, wav_path: Path, *, language, duration_seconds, on_progress, should_cancel) -> TranscriptionResult:
        self.validate_input(wav_path)
        caps = self.capabilities()
        if not caps.available:
            raise ProviderError("provider_unavailable", caps.reason or "Engine unavailable.")
        on_progress(None)  # this engine cannot report real progress
        try:
            import whisper  # type: ignore

            with self._lock:
                if self._model is None:
                    root = str(self.settings.whisper_model_dir) if self.settings.whisper_model_dir else None
                    self._model = whisper.load_model(self.settings.whisper_model, device=self.settings.whisper_device,
                                                     download_root=root)
            result = self._model.transcribe(str(wav_path), language=language or None, fp16=False, verbose=None)
        except MemoryError as exc:
            raise ProviderError("out_of_memory", "Not enough memory for this model.") from exc
        except Exception as exc:
            raise ProviderError("engine_error", "The Whisper engine failed while transcribing.", retryable=True) from exc

        segments = [Segment(start=float(s["start"]), end=float(s["end"]), text=s["text"]) for s in result.get("segments", [])]
        return TranscriptionResult(segments=segments, language=result.get("language") or language,
                                   provider=self.name, model=self.settings.whisper_model)
