"""Placeholder for a future cloud transcription API. Disabled; makes no network calls.

This adapter exists so the rest of the system (configuration, UI labelling,
fail-closed checks) is ready for an external engine. It deliberately has no
HTTP client. Before implementing it, the owner must approve a provider after
reviewing pricing, data handling and terms (see COSTS.md).
"""

from __future__ import annotations

from ..config import Settings
from .base import ProviderCapabilities, ProviderError, TranscriptionProvider


class ExternalAPIProvider(TranscriptionProvider):
    name = "external-api"
    label = "Cloud API (not configured)"
    kind = "external"

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def _blocked_reason(self) -> str | None:
        if not self.settings.external_providers_enabled:
            return "External providers are disabled (VERBA_EXTERNAL_PROVIDERS_ENABLED=false)."
        if self.name not in self.settings.allowed_providers:
            return "The external provider is not in VERBA_ALLOWED_PROVIDERS."
        if not self.settings.external_api_key.strip():
            return "No API credentials are configured."
        return "The external adapter is not implemented in this version."

    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            name=self.name,
            label=self.label,
            kind=self.kind,
            available=False,
            reason=self._blocked_reason(),
            sends_data_externally=True,
        )

    def transcribe(self, wav_path, *, language, duration_seconds, on_progress, should_cancel):
        # Fail closed: never send data anywhere.
        raise ProviderError("provider_disabled", self._blocked_reason() or "External provider unavailable.")
