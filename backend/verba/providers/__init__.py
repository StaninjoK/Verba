"""Provider registry: builds the configured engines and resolves a user's choice."""

from __future__ import annotations

from ..config import Settings
from .base import (  # noqa: F401
    Cancelled,
    ProviderCapabilities,
    ProviderError,
    Segment,
    TranscriptionProvider,
    TranscriptionResult,
)
from .external_api import ExternalAPIProvider
from .faster_whisper_provider import FasterWhisperProvider
from .mock import MockProvider
from .openai_whisper_provider import OpenAIWhisperProvider

# Order matters for "auto": real local engines first, the mock never.
LOCAL_PREFERENCE = ("faster-whisper", "openai-whisper")


class ProviderRegistry:
    def __init__(self, settings: Settings, providers: list[TranscriptionProvider] | None = None) -> None:
        self.settings = settings
        if providers is None:
            providers = [
                FasterWhisperProvider(settings),
                OpenAIWhisperProvider(settings),
                MockProvider(),
                ExternalAPIProvider(settings),
            ]
        self._providers = {p.name: p for p in providers}

    def allowed(self, name: str) -> bool:
        provider = self._providers.get(name)
        if provider is None:
            return False
        if provider.kind == "external" and not self.settings.external_providers_enabled:
            return False
        return name in self.settings.allowed_providers

    def get(self, name: str) -> TranscriptionProvider:
        return self._providers[name]

    def describe(self) -> list[dict]:
        out = []
        for name, provider in self._providers.items():
            caps = provider.capabilities().as_dict()
            caps["allowed"] = self.allowed(name)
            if not caps["allowed"]:
                caps["available"] = False
                caps["reason"] = caps.get("reason") or "Disabled in configuration."
            out.append(caps)
        return out

    def resolve(self, requested: str | None) -> TranscriptionProvider:
        """Pick the engine for a new job. Never falls back to a different engine silently."""
        choice = (requested or self.settings.default_provider or "auto").strip()
        if choice == "auto":
            for name in LOCAL_PREFERENCE:
                if self.allowed(name) and self._providers[name].is_available():
                    return self._providers[name]
            raise ProviderError(
                "no_engine",
                "No local transcription engine is installed. Install Whisper (docs/WHISPER_SETUP.md) "
                "or choose the test engine explicitly.",
            )
        if choice not in self._providers:
            raise ProviderError("unknown_provider", "Unknown transcription engine.")
        if not self.allowed(choice):
            raise ProviderError("provider_disabled", "This transcription engine is disabled in the configuration.")
        provider = self._providers[choice]
        caps = provider.capabilities()
        if not caps.available:
            raise ProviderError("provider_unavailable", caps.reason or "This engine is not available.")
        return provider
