import subprocess
import time

from verba import setup_whisper
from verba.setup_whisper import WhisperSetup, update_env_file

from .conftest import make_settings


def test_update_env_file_keeps_other_lines(tmp_path):
    env = tmp_path / ".env"
    env.write_text("# comment\nVERBA_WHISPER_MODEL=base\nOTHER=1\n")
    update_env_file(env, {"VERBA_WHISPER_MODEL": "small", "VERBA_WHISPER_MODEL_DIR": "/m"})
    assert env.read_text() == "# comment\nVERBA_WHISPER_MODEL=small\nOTHER=1\nVERBA_WHISPER_MODEL_DIR=/m\n"


def _wait(setup):
    for _ in range(100):
        if setup.status()["status"] != "running":
            break
        time.sleep(0.05)
    return setup.status()


def test_setup_downloads_model_and_configures(tmp_path, monkeypatch):
    monkeypatch.setattr(setup_whisper, "MODELS_DIR", tmp_path / "models")
    monkeypatch.setattr(setup_whisper, "ENV_FILE", tmp_path / ".env")
    monkeypatch.setattr(setup_whisper.importlib.util, "find_spec", lambda name: object())  # package "installed"
    calls = []

    def runner(cmd, timeout):
        calls.append(cmd)
        target = tmp_path / "models" / f"faster-whisper-{cmd[-2]}"
        target.mkdir(parents=True)
        (target / "model.bin").write_bytes(b"x")
        return subprocess.CompletedProcess(cmd, 0, "", "")

    settings = make_settings(tmp_path, allowed_providers=["mock"])
    setup = WhisperSetup(settings, runner=runner)
    setup.start("small")
    status = _wait(setup)
    assert status["status"] == "done", status
    assert len(calls) == 1 and "download_model" in calls[0][2]
    assert settings.whisper_model == "small" and settings.whisper_model_dir == (tmp_path / "models").resolve()
    assert settings.allowed_providers[0] == "faster-whisper"
    assert "VERBA_WHISPER_MODEL=small" in (tmp_path / ".env").read_text()


def test_setup_reports_failure(tmp_path, monkeypatch):
    monkeypatch.setattr(setup_whisper, "MODELS_DIR", tmp_path / "models")
    monkeypatch.setattr(setup_whisper, "ENV_FILE", tmp_path / ".env")
    monkeypatch.setattr(setup_whisper.importlib.util, "find_spec", lambda name: None)  # not installed
    setup = WhisperSetup(make_settings(tmp_path),
                         runner=lambda cmd, t: subprocess.CompletedProcess(cmd, 1, "", "ERROR: no network"))
    setup.start("base")
    status = _wait(setup)
    assert status["status"] == "failed" and "no network" in status["error"]


def test_setup_api(client, build_client):
    assert client.get("/api/setup/whisper").json()["models"]["small"] == 465
    assert client.post("/api/setup/whisper", json={"model": "../../evil"}).status_code == 422
    locked = build_client(allow_self_setup=False)
    assert locked.post("/api/setup/whisper", json={"model": "small"}).status_code == 403
