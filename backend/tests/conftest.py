"""Shared fixtures. All media is synthesised locally with FFmpeg (no downloads)."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from verba.api import create_app
from verba.config import Settings
from verba.providers import ProviderRegistry
from verba.providers.external_api import ExternalAPIProvider
from verba.providers.mock import MockProvider


def _ffmpeg(*args: str) -> None:
    subprocess.run(["ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error", "-y", *args], check=True)


@pytest.fixture(scope="session")
def media_dir(tmp_path_factory) -> Path:
    d = tmp_path_factory.mktemp("media")
    tone = ["-f", "lavfi", "-i", "sine=frequency=440:duration=6"]
    _ffmpeg(*tone, str(d / "tone.wav"))
    _ffmpeg(*tone, "-c:a", "libmp3lame", str(d / "tone.mp3"))
    _ffmpeg(*tone, "-c:a", "aac", str(d / "tone.m4a"))
    _ffmpeg("-f", "lavfi", "-i", "testsrc=size=160x120:rate=10:duration=3", *tone[:4],
            "-shortest", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", str(d / "clip.mp4"))
    _ffmpeg("-f", "lavfi", "-i", "testsrc=size=160x120:rate=10:duration=2", "-c:v", "libx264", "-pix_fmt", "yuv420p",
            str(d / "silent_video.mp4"))
    (d / "fake.mp3").write_text("this is not audio at all, just text pretending" * 10)
    wav = (d / "tone.wav").read_bytes()
    (d / "truncated.wav").write_bytes(wav[:60])
    (d / "renamed.mp3").write_bytes(wav)  # real WAV content with an .mp3 extension
    return d


def make_settings(tmp_path: Path, **overrides) -> Settings:
    overrides.setdefault("start_worker", False)
    settings = Settings(data_dir=tmp_path / "data", cors_origins=["http://localhost:3000"], **overrides)
    settings.ensure_dirs()
    return settings


class FlakyProvider(MockProvider):
    """Fails with a retryable error the first ``failures`` times."""

    name = "flaky"

    def __init__(self, failures: int = 1) -> None:
        super().__init__(step_delay=0)
        self.failures = failures
        self.calls = 0

    def transcribe(self, *args, **kwargs):
        from verba.providers import ProviderError

        self.calls += 1
        if self.calls <= self.failures:
            raise ProviderError("engine_error", "temporary failure", retryable=True)
        return super().transcribe(*args, **kwargs)


class BrokenProvider(MockProvider):
    name = "broken"

    def __init__(self) -> None:
        super().__init__(step_delay=0, fail_with="engine_error")


class EmptyProvider(MockProvider):
    name = "empty"

    def transcribe(self, wav_path, **kwargs):
        from verba.providers import TranscriptionResult

        return TranscriptionResult(segments=[], language="en", provider=self.name, model="none")


@pytest.fixture
def build_client(tmp_path):
    clients = []

    def _build(providers=None, **overrides):
        settings = make_settings(tmp_path, allowed_providers=overrides.pop(
            "allowed_providers", ["faster-whisper", "openai-whisper", "mock", "flaky", "broken", "empty"]), **overrides)
        if providers is None:
            providers = [MockProvider(step_delay=0), FlakyProvider(), BrokenProvider(), EmptyProvider(),
                         ExternalAPIProvider(settings)]
        registry = ProviderRegistry(settings, providers)
        app = create_app(settings, registry)
        client = TestClient(app)
        client.__enter__()
        clients.append(client)
        return client

    yield _build
    for c in clients:
        c.__exit__(None, None, None)
        c.app.state.db.close()


@pytest.fixture
def client(build_client):
    return build_client()


def upload(client: TestClient, path: Path, name: str | None = None):
    from urllib.parse import quote

    return client.post("/api/projects", content=path.read_bytes(),
                       headers={"X-Verba-Filename": quote(name or path.name), "Content-Type": "application/octet-stream"})


def run_jobs(client: TestClient) -> None:
    while client.app.state.jobs.run_pending_once():
        pass
