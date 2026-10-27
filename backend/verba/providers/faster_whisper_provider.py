"""Local Whisper via faster-whisper (CTranslate2). Recommended for CPU-only machines.

Model weights are never downloaded implicitly: unless
VERBA_ALLOW_MODEL_DOWNLOAD=true, the model must already be present locally
(see docs/WHISPER_SETUP.md).
"""

from __future__ import annotations

import importlib.util
import threading
from pathlib import Path

from ..config import Settings
from .base import (
    Cancelled,
    ProviderCapabilities,
    ProviderError,
    Segment,
    TranscriptionProvider,
    TranscriptionResult,
)


def _model_locally_present(settings: Settings) -> tuple[bool, str | None]:
    """Check for model weights without touching the network."""
    model = settings.whisper_model
    if Path(model).is_dir():
        return (Path(model) / "model.bin").exists(), str(Path(model))
    if settings.whisper_model_dir:
        candidate = settings.whisper_model_dir / f"faster-whisper-{model}"
        if (candidate / "model.bin").exists():
            return True, str(candidate)
        if (settings.whisper_model_dir / model / "model.bin").exists():
            return True, str(settings.whisper_model_dir / model)
    # Hugging Face cache layout used by faster-whisper's own download helper.
    try:
        from huggingface_hub import try_to_load_from_cache  # type: ignore

        for repo in (f"Systran/faster-whisper-{model}", f"mobiuslabsgmbh/faster-whisper-{model}"):
            hit = try_to_load_from_cache(repo, "model.bin")
            if isinstance(hit, str):
                return True, str(Path(hit).parent)
    except Exception:
        pass
    return False, None


class FasterWhisperProvider(TranscriptionProvider):
    name = "faster-whisper"
    label = "Whisper (local, faster-whisper)"
    kind = "local"

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._model = None
        self._model_lock = threading.Lock()

    def capabilities(self) -> ProviderCapabilities:
        installed = importlib.util.find_spec("faster_whisper") is not None
        present, location = _model_locally_present(self.settings) if installed else (False, None)
        reason = None
        if not installed:
            reason = "faster-whisper is not installed. See docs/WHISPER_SETUP.md."
        elif not present and not self.settings.allow_model_download:
            reason = f"Model '{self.settings.whisper_model}' is not downloaded yet. See docs/WHISPER_SETUP.md."
        return ProviderCapabilities(
            name=self.name,
            label=self.label,
            kind=self.kind,
            available=installed and (present or self.settings.allow_model_download),
            reason=reason,
            model=self.settings.whisper_model,
            language_detection=True,
            segment_timestamps=True,
            word_timestamps=False,
            reports_progress=True,
            supports_cancel=True,
            details={"device": self.settings.whisper_device, "compute_type": self.settings.whisper_compute_type,
                     "model_path": location},
        )

    def _load(self):
        with self._model_lock:
            if self._model is None:
                caps = self.capabilities()
                if not caps.available:
                    raise ProviderError("provider_unavailable", caps.reason or "Engine unavailable.")
                from faster_whisper import WhisperModel  # type: ignore

                _, location = _model_locally_present(self.settings)
                self._model = WhisperModel(
                    location or self.settings.whisper_model,
                    device=self.settings.whisper_device,
                    compute_type=self.settings.whisper_compute_type,
                    download_root=str(self.settings.whisper_model_dir) if self.settings.whisper_model_dir else None,
                    local_files_only=not self.settings.allow_model_download,
                )
            return self._model

    def transcribe(self, wav_path: Path, *, language, duration_seconds, on_progress, should_cancel) -> TranscriptionResult:
        self.validate_input(wav_path)
        try:
            model = self._load()
        except ProviderError:
            raise
        except Exception as exc:  # model files corrupt, out of memory, ...
            raise ProviderError("model_load_failed", "The Whisper model could not be loaded.") from exc

        try:
            segments_iter, info = model.transcribe(
                str(wav_path), language=language or None, beam_size=5, vad_filter=True, condition_on_previous_text=True
            )
            total = float(duration_seconds or getattr(info, "duration", 0) or 0)
            on_progress(0.0 if total else None)
            segments: list[Segment] = []
            for seg in segments_iter:  # decoding happens lazily while iterating
                if should_cancel():
                    raise Cancelled()
                segments.append(Segment(start=float(seg.start), end=float(seg.end), text=seg.text))
                if total:
                    on_progress(min(0.99, float(seg.end) / total))
        except (Cancelled, ProviderError):
            raise
        except MemoryError as exc:
            raise ProviderError("out_of_memory", "Not enough memory for this model. Try a smaller model.") from exc
        except Exception as exc:
            raise ProviderError("engine_error", "The Whisper engine failed while transcribing.", retryable=True) from exc

        return TranscriptionResult(
            segments=segments,
            language=getattr(info, "language", None) or language,
            provider=self.name,
            model=self.settings.whisper_model,
        )
