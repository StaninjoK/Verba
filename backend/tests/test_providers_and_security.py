from pathlib import Path

import pytest

from verba import storage
from verba.media import sniff_family
from verba.providers import ProviderError, ProviderRegistry
from verba.providers.external_api import ExternalAPIProvider
from verba.providers.mock import MockProvider

from .conftest import make_settings, upload


# ------------------------------------------------------- external providers
def test_external_provider_disabled_by_default(tmp_path):
    settings = make_settings(tmp_path)
    registry = ProviderRegistry(settings, [ExternalAPIProvider(settings), MockProvider()])
    assert settings.external_providers_enabled is False
    assert not registry.allowed("external-api")
    with pytest.raises(ProviderError) as exc:
        registry.resolve("external-api")
    assert exc.value.code == "provider_disabled"
    described = {p["name"]: p for p in registry.describe()}
    assert described["external-api"]["available"] is False
    assert described["external-api"]["sends_data_externally"] is True


def test_external_provider_missing_credentials_fails_closed(tmp_path):
    settings = make_settings(tmp_path, external_providers_enabled=True,
                             allowed_providers=["external-api"], external_api_key="")
    provider = ExternalAPIProvider(settings)
    caps = provider.capabilities()
    assert caps.available is False and "credentials" in caps.reason
    registry = ProviderRegistry(settings, [provider])
    with pytest.raises(ProviderError) as exc:
        registry.resolve("external-api")
    assert exc.value.code == "provider_unavailable"
    with pytest.raises(ProviderError):
        provider.transcribe(Path("/nonexistent"), language=None, duration_seconds=1,
                            on_progress=lambda _: None, should_cancel=lambda: False)


def test_external_provider_with_credentials_still_never_sends(tmp_path):
    settings = make_settings(tmp_path, external_providers_enabled=True,
                             allowed_providers=["external-api"], external_api_key="placeholder")
    provider = ExternalAPIProvider(settings)
    assert provider.capabilities().available is False
    with pytest.raises(ProviderError) as exc:
        provider.transcribe(Path("/x"), language=None, duration_seconds=1,
                            on_progress=lambda _: None, should_cancel=lambda: False)
    assert exc.value.code == "provider_disabled"


def test_api_refuses_external_provider(client, media_dir):
    pid = upload(client, media_dir / "tone.wav").json()["id"]
    res = client.post(f"/api/projects/{pid}/transcribe", json={"provider": "external-api"})
    assert res.status_code == 403


def test_disallowed_provider_is_refused(build_client, media_dir):
    client = build_client(allowed_providers=["faster-whisper"])
    pid = upload(client, media_dir / "tone.wav").json()["id"]
    res = client.post(f"/api/projects/{pid}/transcribe", json={"provider": "mock"})
    assert res.status_code == 403
    assert res.json()["error"]["code"] == "provider_disabled"


def test_auto_never_selects_mock(tmp_path):
    settings = make_settings(tmp_path)
    registry = ProviderRegistry(settings, [MockProvider()])
    with pytest.raises(ProviderError) as exc:
        registry.resolve("auto")
    assert exc.value.code == "no_engine"


def test_whisper_providers_report_unavailable_without_install(tmp_path):
    settings = make_settings(tmp_path)
    registry = ProviderRegistry(settings)
    described = {p["name"]: p for p in registry.describe()}
    for name in ("faster-whisper", "openai-whisper"):
        assert name in described
        if not described[name]["available"]:
            assert described[name]["reason"]


def test_system_endpoint(client):
    body = client.get("/api/system").json()
    assert body["external_providers_enabled"] is False
    assert body["processing_location"] == "local"
    assert body["ffmpeg_available"] is True
    names = {p["name"] for p in body["providers"]}
    assert {"mock", "external-api"} <= names
    mock = next(p for p in body["providers"] if p["name"] == "mock")
    assert mock["is_mock"] is True


# ---------------------------------------------------------- storage safety
def test_confined_path_blocks_traversal(tmp_path):
    base = tmp_path / "uploads"
    base.mkdir()
    good = storage.new_stored_filename("wav")
    assert storage.confined_path(base, good).parent == base.resolve()
    for bad in ["../x.wav", "/etc/passwd", "a/b.wav", "..", "", "x" * 32 + ".wav/../../y", "ABC.wav"]:
        with pytest.raises(storage.UnsafePath):
            storage.confined_path(base, bad)


def test_new_stored_filename_rejects_bad_extension():
    with pytest.raises(storage.UnsafePath):
        storage.new_stored_filename("../sh")


def test_safe_display_name():
    assert storage.safe_display_name("..\\..\\windows\\evil.mp3") == "evil.mp3"
    assert storage.safe_display_name("") == "Untitled"
    assert storage.safe_display_name("a‮b.mp3") == "ab.mp3"  # bidi override stripped
    assert len(storage.safe_display_name("x" * 500)) == 120
    assert storage.title_from_filename("interview.final.mp3") == "interview.final"


def test_download_filename():
    assert storage.download_filename("Ünïcode / test", "txt") == "Unicode_test.txt"
    assert storage.download_filename("///", "srt") == "transcript.srt"


def test_sniffing():
    assert sniff_family(b"RIFF\x00\x00\x00\x00WAVEfmt ") == "wav"
    assert sniff_family(b"ID3\x04\x00\x00\x00\x00\x00\x00\x00\x00") == "mp3"
    assert sniff_family(b"\x00\x00\x00\x20ftypM4A \x00\x00") == "mp4"
    assert sniff_family(b"#EXTM3U\nhttp://evil/") is None
    assert sniff_family(b"MZ\x90\x00" + b"\x00" * 20) is None


def test_security_headers_and_cors(client):
    res = client.get("/api/health", headers={"Origin": "http://evil.example"})
    assert res.headers["x-frame-options"] == "DENY"
    assert "access-control-allow-origin" not in res.headers
    ok = client.get("/api/health", headers={"Origin": "http://localhost:3000"})
    assert ok.headers["access-control-allow-origin"] == "http://localhost:3000"


def test_logs_do_not_contain_transcript_or_filename(client, media_dir, caplog):
    import logging

    from .conftest import run_jobs

    caplog.set_level(logging.DEBUG)
    pid = upload(client, media_dir / "tone.wav", name="secret-client-name.wav").json()["id"]
    client.post(f"/api/projects/{pid}/transcribe", json={"provider": "mock"})
    run_jobs(client)
    joined = "\n".join(r.getMessage() for r in caplog.records)
    assert "secret-client-name" not in joined
    assert "placeholder text" not in joined
