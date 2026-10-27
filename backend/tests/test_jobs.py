import pytest

from verba.db import InvalidTransition

from .conftest import run_jobs, upload


def _project(client, media_dir, name="tone.wav"):
    res = upload(client, media_dir / name)
    assert res.status_code == 201, res.text
    return res.json()["id"]


def test_mock_transcription_completes_and_is_flagged(client, media_dir):
    pid = _project(client, media_dir)
    res = client.post(f"/api/projects/{pid}/transcribe", json={"provider": "mock", "language": "en"})
    assert res.status_code == 202
    assert res.json()["status"] == "pending"
    run_jobs(client)
    project = client.get(f"/api/projects/{pid}").json()
    assert project["status"] == "completed"
    assert project["is_mock"] is True
    assert project["provider"] == "mock"
    assert project["job"]["progress"] == 1.0
    assert project["segments"] and all(s["text"].startswith("[MOCK]") for s in project["segments"])
    assert project["transcript_version"] == 1
    # temp wav removed after the job
    assert not list(client.app.state.settings.tmp_dir.iterdir())


def test_video_input_is_transcribed(client, media_dir):
    pid = _project(client, media_dir, "clip.mp4")
    client.post(f"/api/projects/{pid}/transcribe", json={"provider": "mock"})
    run_jobs(client)
    assert client.get(f"/api/projects/{pid}").json()["status"] == "completed"


def test_auto_without_real_engine_fails_closed(client, media_dir):
    pid = _project(client, media_dir)
    res = client.post(f"/api/projects/{pid}/transcribe", json={"provider": "auto"})
    assert res.status_code == 409
    assert res.json()["error"]["code"] == "no_engine"


def test_provider_failure_marks_job_failed(client, media_dir):
    pid = _project(client, media_dir)
    client.post(f"/api/projects/{pid}/transcribe", json={"provider": "broken"})
    run_jobs(client)
    project = client.get(f"/api/projects/{pid}").json()
    assert project["status"] == "failed"
    assert project["job"]["error"]["code"] == "engine_error"
    assert project["has_transcript"] is False


def test_retryable_failure_is_retried(client, media_dir):
    pid = _project(client, media_dir)
    client.post(f"/api/projects/{pid}/transcribe", json={"provider": "flaky"})
    run_jobs(client)
    project = client.get(f"/api/projects/{pid}").json()
    assert project["status"] == "completed"
    assert project["job"]["attempts"] == 2


def test_empty_result_is_not_completed(client, media_dir):
    pid = _project(client, media_dir)
    client.post(f"/api/projects/{pid}/transcribe", json={"provider": "empty"})
    run_jobs(client)
    project = client.get(f"/api/projects/{pid}").json()
    assert project["status"] == "failed"
    assert project["job"]["error"]["code"] == "no_speech"


def test_duplicate_submission_rejected(client, media_dir):
    pid = _project(client, media_dir)
    assert client.post(f"/api/projects/{pid}/transcribe", json={"provider": "mock"}).status_code == 202
    second = client.post(f"/api/projects/{pid}/transcribe", json={"provider": "mock"})
    assert second.status_code == 409
    assert second.json()["error"]["code"] == "job_already_running"
    run_jobs(client)
    # after completion a new run is allowed (re-transcription)
    assert client.post(f"/api/projects/{pid}/transcribe", json={"provider": "mock"}).status_code == 202


def test_cancel_pending_job(client, media_dir):
    pid = _project(client, media_dir)
    job = client.post(f"/api/projects/{pid}/transcribe", json={"provider": "mock"}).json()
    res = client.post(f"/api/jobs/{job['id']}/cancel")
    assert res.json()["status"] == "cancelled"
    run_jobs(client)
    assert client.get(f"/api/projects/{pid}").json()["status"] == "cancelled"


def test_cancel_during_processing(client, media_dir):
    pid = _project(client, media_dir)
    job = client.post(f"/api/projects/{pid}/transcribe", json={"provider": "mock"}).json()
    db = client.app.state.db
    db.transition_job(job["id"], "validating")
    db.request_cancel(job["id"])
    db.transition_job(job["id"], "pending")  # simulate being picked up again with the cancel flag set
    run_jobs(client)
    assert db.get_job(job["id"])["status"] == "cancelled"


def test_invalid_language_rejected(client, media_dir):
    pid = _project(client, media_dir)
    res = client.post(f"/api/projects/{pid}/transcribe", json={"provider": "mock", "language": "xx"})
    assert res.status_code == 422


def test_state_machine_rejects_invalid_transitions(client, media_dir):
    pid = _project(client, media_dir)
    job = client.post(f"/api/projects/{pid}/transcribe", json={"provider": "mock"}).json()
    db = client.app.state.db
    with pytest.raises(InvalidTransition):
        db.transition_job(job["id"], "completed")  # pending -> completed is not allowed
    run_jobs(client)
    with pytest.raises(InvalidTransition):
        db.transition_job(job["id"], "processing")  # terminal state


def test_recovery_after_restart(client, media_dir):
    pid = _project(client, media_dir)
    job = client.post(f"/api/projects/{pid}/transcribe", json={"provider": "mock"}).json()
    db = client.app.state.db
    db.transition_job(job["id"], "validating")
    db.increment_attempts(job["id"])
    db.transition_job(job["id"], "processing")
    # simulate a crash: job left in "processing"; recovery re-queues it
    client.app.state.jobs.recover()
    assert db.get_job(job["id"])["status"] == "pending"
    run_jobs(client)
    assert db.get_job(job["id"])["status"] == "completed"


def test_recovery_gives_up_after_attempt_limit(build_client, media_dir):
    client = build_client(max_job_attempts=1)
    pid = _project(client, media_dir)
    job = client.post(f"/api/projects/{pid}/transcribe", json={"provider": "mock"}).json()
    db = client.app.state.db
    db.transition_job(job["id"], "validating")
    db.increment_attempts(job["id"])
    client.app.state.jobs.recover()
    j = db.get_job(job["id"])
    assert j["status"] == "failed" and j["error_code"] == "interrupted"


def test_missing_source_file_fails_job(client, media_dir):
    pid = _project(client, media_dir)
    project = client.app.state.db.get_project(pid)
    (client.app.state.settings.uploads_dir / project["stored_filename"]).unlink()
    client.post(f"/api/projects/{pid}/transcribe", json={"provider": "mock"})
    run_jobs(client)
    assert client.get(f"/api/projects/{pid}").json()["job"]["error"]["code"] == "file_missing"


def test_background_worker_processes_jobs(build_client, media_dir):
    import time

    client = build_client(start_worker=True)
    pid = _project(client, media_dir)
    client.post(f"/api/projects/{pid}/transcribe", json={"provider": "mock"})
    deadline = time.time() + 20
    status = None
    while time.time() < deadline:
        status = client.get(f"/api/projects/{pid}").json()["status"]
        if status in ("completed", "failed"):
            break
        time.sleep(0.1)
    assert status == "completed"
