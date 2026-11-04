import io
import json
import subprocess
import zipfile
from urllib.parse import quote

import pytest

from verba.whatsapp import ChatImportError, chat_title, import_export, parse_chat_text

ANDROID_DE = """04.11.26, 09:15 - Nachrichten und Anrufe sind Ende-zu-Ende-verschlüsselt. Tippe, um mehr zu erfahren.
04.11.26, 09:16 - Stan: Hola María!
04.11.26, 09:17 - María López: PTT-20261104-WA0001.opus (Datei angehängt)
04.11.26, 09:18 - María López: IMG-20261104-WA0002.jpg (Datei angehängt)
Mira esto
04.11.26, 09:19 - Stan: <Medien ausgeschlossen>
04.11.26, 09:20 - Stan: Zeile eins
Zeile zwei
05.11.26, 18:01 - María López: Diese Nachricht wurde gelöscht
"""

IOS_ES = """‎[13/11/2026, 21:05:10] Ana: ¿Vienes mañana?
[13/11/2026, 21:06:00] Luis: ‎<adjunto: 00000003-AUDIO-2026-11-13-21-06-00.opus>
[14/11/2026, 7:02:44] Ana: ‎<adjunto: 00000004-PHOTO-2026-11-14-07-02-44.jpg>
"""

US_AMPM = """11/4/26, 9:15 PM - Bob: hi
11/13/26, 12:05 AM - Alice: <Media omitted>
"""


def test_android_german():
    chat = parse_chat_text(ANDROID_DE, {"PTT-20261104-WA0001.opus", "IMG-20261104-WA0002.jpg"})
    kinds = [m.kind for m in chat.messages]
    assert kinds == ["system", "text", "voice", "image", "omitted", "text", "deleted"]
    assert chat.messages[1].timestamp == "2026-11-04T09:16:00"
    assert chat.messages[3].text == "Mira esto"  # caption on the following line
    assert chat.messages[5].text == "Zeile eins\nZeile zwei"
    assert chat.participants == ["Stan", "María López"]
    assert chat.date_order == "dmy"


def test_ios_spanish_with_invisible_marks():
    chat = parse_chat_text(IOS_ES)
    assert [m.kind for m in chat.messages] == ["text", "voice", "image"]
    assert chat.messages[1].attachment == "00000003-AUDIO-2026-11-13-21-06-00.opus"
    assert chat.messages[2].timestamp == "2026-11-14T07:02:44"


def test_us_dates_with_am_pm():
    chat = parse_chat_text(US_AMPM)
    assert chat.date_order == "mdy"
    assert chat.messages[0].timestamp == "2026-11-04T21:15:00"
    assert chat.messages[1].timestamp == "2026-11-13T00:05:00"
    assert chat.messages[1].kind == "omitted"


def test_not_a_chat():
    with pytest.raises(ChatImportError):
        parse_chat_text("just some text\nwithout timestamps")


def test_title_from_filename():
    assert chat_title("WhatsApp Chat mit María López.zip", []) == "María López"
    assert chat_title("_chat.txt", ["Ana", "Luis"]) == "Ana, Luis"


def _ffmpeg(*args):
    subprocess.run(["ffmpeg", "-nostdin", "-loglevel", "error", "-y", *args], check=True)


@pytest.fixture(scope="module")
def chat_zip(tmp_path_factory):
    d = tmp_path_factory.mktemp("wa")
    _ffmpeg("-f", "lavfi", "-i", "sine=frequency=300:duration=3", "-c:a", "libopus", str(d / "v1.opus"))
    _ffmpeg("-f", "lavfi", "-i", "color=c=red:s=32x32", "-frames:v", "1", str(d / "p.jpg"))
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("WhatsApp Chat mit María López/_chat.txt", ANDROID_DE)
        zf.write(d / "v1.opus", "WhatsApp Chat mit María López/PTT-20261104-WA0001.opus")
        zf.write(d / "p.jpg", "WhatsApp Chat mit María López/IMG-20261104-WA0002.jpg")
        zf.writestr("../../evil.opus", b"OggS-not-really")  # traversal name: never written outside
    return buf.getvalue()


def test_import_zip_copies_media_safely(tmp_path, chat_zip):
    src = tmp_path / "export.zip"
    src.write_bytes(chat_zip)
    media = tmp_path / "media"
    chat = import_export(src, media, max_total_bytes=50 * 1024 * 1024)
    voice = next(m for m in chat.messages if m.kind == "voice")
    assert voice.stored_name and (media / voice.stored_name).exists()
    assert len(list(media.iterdir())) == 2  # only referenced media, under random names
    assert not (tmp_path / "evil.opus").exists() and not (tmp_path.parent / "evil.opus").exists()


def test_import_rejects_oversized_archive(tmp_path, chat_zip):
    src = tmp_path / "export.zip"
    src.write_bytes(chat_zip)
    with pytest.raises(ChatImportError) as exc:
        import_export(src, tmp_path / "m", max_total_bytes=100)
    assert exc.value.code == "chat_too_large"


def test_import_rejects_zip_without_chat(tmp_path):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("photo.jpg", b"x")
    src = tmp_path / "x.zip"
    src.write_bytes(buf.getvalue())
    with pytest.raises(ChatImportError) as exc:
        import_export(src, tmp_path / "m", max_total_bytes=10**7)
    assert exc.value.code == "no_chat_file"


# ------------------------------------------------------------------- API flow
def _upload(client, data, name="WhatsApp Chat mit María López.zip", **params):
    query = "&".join(f"{k}={v}" for k, v in ({"provider": "mock", "language": "es"} | params).items())
    return client.post(f"/api/chats?{query}", content=data, headers={"X-Verba-Filename": quote(name)})


def test_chat_import_transcribe_and_export(client, chat_zip):
    res = _upload(client, chat_zip)
    assert res.status_code == 201, res.text
    chat = res.json()
    assert chat["title"] == "María López" and chat["total_items"] == 1 and chat["is_mock"] is True
    client.app.state.chats.run_pending_once()

    full = client.get(f"/api/chats/{chat['id']}").json()
    assert full["status"] == "completed" and full["done_items"] == 1
    voice = next(m for m in full["messages"] if m["kind"] == "voice")
    assert voice["item_status"] == "done" and voice["transcript"].startswith("[MOCK]")
    assert voice["transcript_language"] == "es" and voice["duration_seconds"] > 2

    image = next(m for m in full["messages"] if m["kind"] == "image")
    res = client.patch(f"/api/chats/{chat['id']}/messages/{image['idx']}",
                       json={"image_description": "Ein rotes Quadrat"})
    assert res.status_code == 200 and res.json()["image_description"] == "Ein rotes Quadrat"

    txt = client.get(f"/api/chats/{chat['id']}/export", params={"format": "txt", "lang": "de"}).text
    assert "WhatsApp-Chat: María López" in txt
    assert "ACHTUNG: Testdaten" in txt
    assert "── 04.11.2026 ──" in txt and "── 05.11.2026 ──" in txt
    assert "[09:16] Stan: Hola María!" in txt
    assert "[09:17] María López – 🎤 Sprachnachricht (0:03): [MOCK]" in txt
    assert "Beschreibung: Ein rotes Quadrat | Bildunterschrift: Mira esto" in txt
    assert "(Medien nicht im Export enthalten)" in txt
    assert "Zeile eins\nZeile zwei" in txt

    md = client.get(f"/api/chats/{chat['id']}/export", params={"format": "md", "lang": "es"}).text
    assert md.startswith("# Chat de WhatsApp: María López") and "## 04.11.2026" in md
    data = client.get(f"/api/chats/{chat['id']}/export", params={"format": "json"}).json()
    assert data["stats"]["transcribed"] == 1 and len(data["messages"]) == 7
    docx = client.get(f"/api/chats/{chat['id']}/export", params={"format": "docx"})
    assert zipfile.ZipFile(io.BytesIO(docx.content)).read("word/document.xml")

    media = client.get(f"/api/chats/{chat['id']}/media/{voice['idx']}")
    assert media.status_code == 200 and media.headers["content-type"] == "audio/ogg"

    # search finds the chat by transcript text
    assert client.get("/api/chats", params={"q": "placeholder text"}).json()["chats"][0]["id"] == chat["id"]

    # edit transcript manually
    res = client.patch(f"/api/chats/{chat['id']}/messages/{voice['idx']}", json={"transcript": "Hola, ¿qué tal?"})
    assert res.json()["transcript"] == "Hola, ¿qué tal?"
    assert client.patch(f"/api/chats/{chat['id']}/messages/{voice['idx']}",
                        json={"image_description": "x"}).status_code == 422

    assert client.delete(f"/api/chats/{chat['id']}").status_code == 204
    assert not client.app.state.chats.media_dir(chat["id"]).exists()
    assert client.get(f"/api/chats/{chat['id']}").status_code == 404


def test_chat_text_only_export(client):
    res = _upload(client, ANDROID_DE.encode(), name="_chat.txt")
    assert res.status_code == 201
    chat = res.json()
    assert chat["total_items"] == 0
    client.app.state.chats.run_pending_once()
    txt = client.get(f"/api/chats/{chat['id']}/export").text
    assert "PTT-20261104-WA0001.opus – Datei fehlt im Export" in txt


def test_chat_failure_and_retry(build_client, chat_zip):
    client = build_client()
    res = _upload(client, chat_zip, provider="broken")
    chat = res.json()
    client.app.state.chats.run_pending_once()
    full = client.get(f"/api/chats/{chat['id']}").json()
    assert full["status"] == "failed" and full["error"]["code"] == "all_items_failed"
    retry = client.post(f"/api/chats/{chat['id']}/retry", json={"provider": "mock", "language": "auto"})
    assert retry.status_code == 202 and retry.json()["status"] == "pending"
    client.app.state.chats.run_pending_once()
    assert client.get(f"/api/chats/{chat['id']}").json()["status"] == "completed"


def test_chat_cancel_and_recovery(client, chat_zip):
    chat = _upload(client, chat_zip).json()
    assert client.post(f"/api/chats/{chat['id']}/cancel").json()["status"] == "cancelled"
    chat2 = _upload(client, chat_zip).json()
    store = client.app.state.chats.store
    store.update(chat2["id"], status="processing")  # simulate crash mid-way
    client.app.state.chats.recover()
    assert store.get(chat2["id"])["status"] == "pending"


def test_chat_upload_validation(client, chat_zip):
    assert _upload(client, chat_zip, name="chat.rar").status_code == 415
    assert _upload(client, b"nothing here", name="_chat.txt").json()["error"]["code"] == "not_a_chat"
    assert _upload(client, chat_zip, provider="auto").status_code == 409  # no real engine installed
    assert _upload(client, chat_zip, language="xx").status_code == 422
    assert client.get("/api/chats/../../etc").status_code == 404


def test_low_confidence_language_falls_back_to_chat_language(build_client, chat_zip, tmp_path):
    """A short note detected as another language with low confidence is redone in the chat's main language."""
    from verba.providers import Segment, TranscriptionResult
    from verba.providers.mock import MockProvider

    class Detecting(MockProvider):
        name = "detecting"

        def __init__(self):
            super().__init__(step_delay=0)
            self.calls = []

        def transcribe(self, wav_path, *, language, **kw):
            self.calls.append(language)
            if language:
                return TranscriptionResult([Segment(0, 1, f"texto en {language}")], language, self.name, "m")
            # first call per note: auto-detect; pretend the 2nd note looks Portuguese with low confidence
            lang, prob = ("es", 0.95) if len(self.calls) == 1 else ("pt", 0.4)
            return TranscriptionResult([Segment(0, 1, f"auto {lang}")], lang, self.name, "m", language_probability=prob)

    engine = Detecting()
    client = build_client(providers=[engine], allowed_providers=["detecting"])
    two_notes = ANDROID_DE + "05.11.26, 18:02 - Stan: PTT-20261105-WA0003.opus (Datei angehängt)\n"
    src = io.BytesIO()
    with zipfile.ZipFile(io.BytesIO(chat_zip)) as old, zipfile.ZipFile(src, "w") as zf:
        opus = old.read("WhatsApp Chat mit María López/PTT-20261104-WA0001.opus")
        zf.writestr("_chat.txt", two_notes)
        zf.writestr("PTT-20261104-WA0001.opus", opus)
        zf.writestr("PTT-20261105-WA0003.opus", opus)
    chat = _upload(client, src.getvalue(), provider="detecting", language="auto").json()
    client.app.state.chats.run_pending_once()
    msgs = [m for m in client.get(f"/api/chats/{chat['id']}").json()["messages"] if m["kind"] == "voice"]
    assert [m["transcript_language"] for m in msgs] == ["es", "es"]
    assert msgs[1]["transcript"] == "texto en es"
    assert engine.calls == [None, None, "es"]
    assert json.loads(json.dumps(msgs))
