import io
import re
import zipfile
from xml.etree import ElementTree

from verba import exports

from .conftest import run_jobs, upload

SRT_TIME = r"\d{2}:\d{2}:\d{2},\d{3}"
VTT_TIME = r"\d{2}:\d{2}:\d{2}\.\d{3}"


def _completed(client, media_dir):
    pid = upload(client, media_dir / "tone.wav").json()["id"]
    client.post(f"/api/projects/{pid}/transcribe", json={"provider": "mock"})
    run_jobs(client)
    return client.get(f"/api/projects/{pid}").json()


# ------------------------------------------------------------------ projects
def test_list_search_rename_delete(client, media_dir):
    p1 = upload(client, media_dir / "tone.wav", name="Weekly standup.wav").json()
    p2 = upload(client, media_dir / "tone.mp3", name="Podcast episode.mp3").json()
    listed = client.get("/api/projects").json()["projects"]
    assert {p["id"] for p in listed} == {p1["id"], p2["id"]}

    found = client.get("/api/projects", params={"q": "podcast"}).json()["projects"]
    assert [p["id"] for p in found] == [p2["id"]]

    res = client.patch(f"/api/projects/{p1['id']}", json={"title": "  Team   meeting  "})
    assert res.status_code == 200 and res.json()["title"] == "Team meeting"
    assert client.patch(f"/api/projects/{p1['id']}", json={"title": "   "}).status_code == 422
    assert client.patch(f"/api/projects/{p1['id']}", json={"title": ""}).status_code == 422

    stored = client.app.state.db.get_project(p1["id"])["stored_filename"]
    path = client.app.state.settings.uploads_dir / stored
    assert path.exists()
    assert client.delete(f"/api/projects/{p1['id']}").status_code == 204
    assert not path.exists()
    assert client.get(f"/api/projects/{p1['id']}").status_code == 404


def test_search_matches_transcript_text_and_escapes_wildcards(client, media_dir):
    project = _completed(client, media_dir)
    assert client.get("/api/projects", params={"q": "placeholder text"}).json()["projects"][0]["id"] == project["id"]
    assert client.get("/api/projects", params={"q": "%"}).json()["projects"] == []


def test_invalid_ids_are_404(client):
    assert client.get("/api/projects/../../etc").status_code == 404
    assert client.get("/api/projects/notanid").status_code == 404
    assert client.get("/api/jobs/notanid").status_code == 404


def test_media_is_served_with_range_support(client, media_dir):
    pid = upload(client, media_dir / "tone.mp3").json()["id"]
    res = client.get(f"/api/projects/{pid}/media")
    assert res.status_code == 200 and res.headers["content-type"] == "audio/mpeg"
    assert res.headers["x-content-type-options"] == "nosniff"
    part = client.get(f"/api/projects/{pid}/media", headers={"Range": "bytes=0-99"})
    assert part.status_code == 206 and len(part.content) == 100


# ------------------------------------------------------------------- editing
def test_edit_transcript_with_versioning(client, media_dir):
    project = _completed(client, media_dir)
    pid, version = project["id"], project["transcript_version"]
    seg = project["segments"][0]
    res = client.put(f"/api/projects/{pid}/transcript",
                     json={"version": version, "segments": [{"id": seg["id"], "text": "Edited first line."}]})
    assert res.status_code == 200
    new_version = res.json()["version"]
    assert new_version == version + 1

    updated = client.get(f"/api/projects/{pid}").json()
    assert updated["segments"][0]["text"] == "Edited first line."
    assert updated["segments"][0]["start"] == seg["start"]  # timestamps untouched
    assert updated["transcript_edited"] is True

    stale = client.put(f"/api/projects/{pid}/transcript",
                       json={"version": version, "segments": [{"id": seg["id"], "text": "Lost update"}]})
    assert stale.status_code == 409 and stale.json()["error"]["code"] == "version_conflict"
    assert client.get(f"/api/projects/{pid}").json()["segments"][0]["text"] == "Edited first line."


def test_edit_rejects_unknown_segments_and_missing_transcript(client, media_dir):
    project = _completed(client, media_dir)
    res = client.put(f"/api/projects/{project['id']}/transcript",
                     json={"version": project["transcript_version"], "segments": [{"id": 999, "text": "x"}]})
    assert res.status_code == 422
    fresh = upload(client, media_dir / "tone.wav").json()
    res = client.put(f"/api/projects/{fresh['id']}/transcript", json={"version": 0, "segments": []})
    assert res.status_code == 409


def test_edit_blocked_while_job_active(client, media_dir):
    project = _completed(client, media_dir)
    client.post(f"/api/projects/{project['id']}/transcribe", json={"provider": "mock"})
    res = client.put(f"/api/projects/{project['id']}/transcript",
                     json={"version": project["transcript_version"], "segments": []})
    assert res.status_code == 409 and res.json()["error"]["code"] == "job_active"


# ------------------------------------------------------------------- exports
def test_export_txt(client, media_dir):
    project = _completed(client, media_dir)
    res = client.get(f"/api/projects/{project['id']}/export", params={"format": "txt"})
    assert res.status_code == 200
    assert "attachment" in res.headers["content-disposition"]
    assert "[MOCK]" in res.text
    stamped = client.get(f"/api/projects/{project['id']}/export", params={"format": "txt", "timestamps": "true"}).text
    assert re.match(r"^\[\d{2}:\d{2}\] ", stamped)


def _parse_cues(text: str, time_re: str):
    cues = []
    for block in text.strip().split("\n\n"):
        lines = block.strip().splitlines()
        timing = next(l for l in lines if "-->" in l)
        m = re.fullmatch(rf"({time_re}) --> ({time_re})", timing)
        assert m, timing
        cues.append((m.group(1), m.group(2), lines[-1]))
    return cues


def test_export_srt_is_valid(client, media_dir):
    project = _completed(client, media_dir)
    text = client.get(f"/api/projects/{project['id']}/export", params={"format": "srt"}).text
    blocks = text.strip().split("\n\n")
    for i, block in enumerate(blocks, start=1):
        assert block.splitlines()[0] == str(i)
    cues = _parse_cues(text, SRT_TIME)
    assert len(cues) == len(project["segments"])
    for start, end, _ in cues:
        assert start < end


def test_export_vtt_is_valid(client, media_dir):
    project = _completed(client, media_dir)
    text = client.get(f"/api/projects/{project['id']}/export", params={"format": "vtt"}).text
    assert text.startswith("WEBVTT\n")
    cues = _parse_cues(text.split("\n", 1)[1], VTT_TIME)
    assert len(cues) == len(project["segments"])


def test_export_docx_is_valid_zip(client, media_dir):
    project = _completed(client, media_dir)
    res = client.get(f"/api/projects/{project['id']}/export", params={"format": "docx"})
    with zipfile.ZipFile(io.BytesIO(res.content)) as zf:
        root = ElementTree.fromstring(zf.read("word/document.xml"))
        assert "[Content_Types].xml" in zf.namelist()
    text = "".join(t.text or "" for t in root.iter("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t"))
    assert "[MOCK]" in text


def test_export_without_transcript_and_bad_format(client, media_dir):
    pid = upload(client, media_dir / "tone.wav").json()["id"]
    assert client.get(f"/api/projects/{pid}/export", params={"format": "txt"}).status_code == 409
    assert client.get(f"/api/projects/{pid}/export", params={"format": "exe"}).status_code == 422


def test_export_filename_is_safe(client, media_dir):
    project = _completed(client, media_dir)
    client.patch(f"/api/projects/{project['id']}", json={"title": 'Bad "name"\r\nX-Injected: 1 / ü'})
    res = client.get(f"/api/projects/{project['id']}/export", params={"format": "srt"})
    disposition = res.headers["content-disposition"]
    assert "\n" not in disposition and "x-injected" not in {k.lower() for k in res.headers}
    assert disposition.startswith('attachment; filename="Bad_name_X-Injected_1_u.srt"')


# ------------------------------------------------------- timestamp formatting
def test_timestamp_formatting():
    assert exports.format_timestamp(0) == "00:00:00,000"
    assert exports.format_timestamp(61.5) == "00:01:01,500"
    assert exports.format_timestamp(3725.042, ".") == "01:02:05.042"
    assert exports.format_timestamp(59.9996) == "00:01:00,000"
    assert exports.format_timestamp(-3) == "00:00:00,000"
    assert exports.format_clock(65) == "01:05"
    assert exports.format_clock(3725) == "1:02:05"


def test_exports_skip_empty_segments_and_fix_zero_length():
    segs = [{"start": 1, "end": 1, "text": "a"}, {"start": 2, "end": 3, "text": "   "}, {"start": 4, "end": 5, "text": "b --> c"}]
    srt = exports.to_srt(segs)
    assert srt.count("-->") == 3  # two cues + literal arrow kept in SRT text
    vtt = exports.to_vtt(segs)
    assert "b → c" in vtt
    assert "00:00:01.000 --> 00:00:01.001" in vtt
