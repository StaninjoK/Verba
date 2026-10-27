from urllib.parse import quote

import pytest

from .conftest import upload


@pytest.mark.parametrize("name", ["tone.wav", "tone.mp3", "tone.m4a", "clip.mp4"])
def test_valid_uploads_accepted(client, media_dir, name):
    res = upload(client, media_dir / name)
    assert res.status_code == 201, res.text
    body = res.json()
    assert body["status"] == "ready"
    assert body["duration_seconds"] > 2
    assert body["has_transcript"] is False
    assert body["has_video"] is (name == "clip.mp4")


def test_unsupported_extension_rejected(client, media_dir):
    res = upload(client, media_dir / "tone.wav", name="notes.exe")
    assert res.status_code == 415
    assert res.json()["error"]["code"] == "unsupported_format"


def test_fake_audio_rejected_by_content(client, media_dir):
    res = upload(client, media_dir / "fake.mp3")
    assert res.status_code == 422
    assert res.json()["error"]["code"] == "content_mismatch"


def test_extension_must_match_content(client, media_dir):
    res = upload(client, media_dir / "renamed.mp3")
    assert res.status_code == 422
    assert res.json()["error"]["code"] == "content_mismatch"


def test_corrupted_file_rejected(client, media_dir):
    res = upload(client, media_dir / "truncated.wav")
    assert res.status_code == 422
    assert res.json()["error"]["code"] in {"corrupt_file", "no_duration"}


def test_video_without_audio_rejected(client, media_dir):
    res = upload(client, media_dir / "silent_video.mp4")
    assert res.status_code == 422
    assert res.json()["error"]["code"] == "no_audio"


def test_empty_upload_rejected(client):
    res = client.post("/api/projects", content=b"", headers={"X-Verba-Filename": "a.wav"})
    assert res.status_code == 400
    assert res.json()["error"]["code"] == "empty_file"


def test_missing_filename_rejected(client, media_dir):
    res = client.post("/api/projects", content=(media_dir / "tone.wav").read_bytes())
    assert res.status_code == 400


def test_upload_size_limit(build_client, media_dir):
    client = build_client(max_upload_mb=1)
    big = b"RIFF" + b"\x00" * (2 * 1024 * 1024)
    res = client.post("/api/projects", content=big, headers={"X-Verba-Filename": "big.wav"})
    assert res.status_code == 413
    assert res.json()["error"]["code"] == "file_too_large"
    # nothing is left behind in temp storage
    assert not any(client.app.state.settings.tmp_dir.iterdir())


def test_storage_limit(build_client, media_dir):
    client = build_client(max_storage_mb=1)
    assert upload(client, media_dir / "tone.wav").status_code == 201
    for _ in range(10):
        res = upload(client, media_dir / "tone.wav")
        if res.status_code != 201:
            break
    assert res.status_code == 507
    assert res.json()["error"]["code"] == "storage_full"


def test_path_traversal_filename_is_neutralised(client, media_dir):
    res = upload(client, media_dir / "tone.wav", name="../../etc/passwd.wav")
    assert res.status_code == 201
    body = res.json()
    assert body["original_filename"] == "passwd.wav"
    project = client.app.state.db.get_project(body["id"])
    stored = project["stored_filename"]
    assert "/" not in stored and ".." not in stored
    uploads = client.app.state.settings.uploads_dir
    assert (uploads / stored).exists()


def test_unicode_and_control_chars_in_filename(client, media_dir):
    res = upload(client, media_dir / "tone.wav", name="Interviews\x00 Größe\n Ñandú.wav")
    assert res.status_code == 201
    assert res.json()["title"] == "Interviews Größe Ñandú"


def test_duplicate_upload_is_flagged(client, media_dir):
    first = upload(client, media_dir / "tone.wav").json()
    second = upload(client, media_dir / "tone.wav").json()
    assert first["duplicate_of"] is None
    assert second["duplicate_of"]["id"] == first["id"]
    assert second["id"] != first["id"]


def test_too_long_recording_rejected(build_client, media_dir):
    client = build_client(max_media_duration_min=1)
    import subprocess

    long_wav = media_dir / "long.wav"
    subprocess.run(["ffmpeg", "-nostdin", "-loglevel", "error", "-y", "-f", "lavfi", "-i",
                    "anullsrc=r=8000:cl=mono", "-t", "70", str(long_wav)], check=True)
    res = client.post("/api/projects", content=long_wav.read_bytes(), headers={"X-Verba-Filename": quote("long.wav")})
    assert res.status_code == 413
    assert res.json()["error"]["code"] == "too_long"
