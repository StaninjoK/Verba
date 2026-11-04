"""End-to-end test of the MCP server against a real HTTP backend (test engine, temp data)."""

import io
import socket
import threading
import time
import zipfile

import pytest
import uvicorn

from verba.api import create_app
from verba.client import VerbaClient
from verba.mcp_server import TOOLS, Server

from .conftest import make_settings
from .test_whatsapp import ANDROID_DE, _ffmpeg


class Capture:
    def __init__(self):
        self.lines = []

    def write(self, s):
        self.lines.append(s)

    def flush(self):
        pass


@pytest.fixture
def live_backend(tmp_path):
    settings = make_settings(tmp_path, start_worker=True, allowed_providers=["mock"])
    app = create_app(settings)
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning"))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    for _ in range(100):
        if server.started:
            break
        time.sleep(0.05)
    yield f"http://127.0.0.1:{port}"
    server.should_exit = True
    thread.join(5)


@pytest.fixture
def export_zip(tmp_path):
    _ffmpeg("-f", "lavfi", "-i", "sine=frequency=300:duration=3", "-c:a", "libopus", str(tmp_path / "v.opus"))
    _ffmpeg("-f", "lavfi", "-i", "color=c=blue:s=32x32", "-frames:v", "1", str(tmp_path / "p.jpg"))
    path = tmp_path / "WhatsApp Chat mit María López.zip"
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr("_chat.txt", ANDROID_DE)
        zf.write(tmp_path / "v.opus", "PTT-20261104-WA0001.opus")
        zf.write(tmp_path / "p.jpg", "IMG-20261104-WA0002.jpg")
    return path


def call(server, name, args, msg_id=1):
    reply = server.handle({"jsonrpc": "2.0", "id": msg_id, "method": "tools/call",
                           "params": {"name": name, "arguments": args, "_meta": {"progressToken": "t1"}}})
    return reply["result"]


def test_protocol_basics():
    server = Server(client=VerbaClient("http://127.0.0.1:9", autostart=False), out=Capture())
    init = server.handle({"jsonrpc": "2.0", "id": 1, "method": "initialize",
                          "params": {"protocolVersion": "2025-06-18", "capabilities": {}}})
    assert init["result"]["serverInfo"]["name"] == "verba"
    assert init["result"]["protocolVersion"] == "2025-06-18"
    assert server.handle({"jsonrpc": "2.0", "method": "notifications/initialized"}) is None
    names = {t["name"] for t in server.handle({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})["result"]["tools"]}
    assert names == {t["name"] for t in TOOLS}
    assert server.handle({"jsonrpc": "2.0", "id": 3, "method": "nope"})["error"]["code"] == -32601
    # backend not reachable and autostart off → a tool error, not a crash
    result = call(server, "verba_status", {})
    assert result["isError"] is True and "not reachable" in result["content"][0]["text"]


def test_whatsapp_chat_through_mcp(live_backend, export_zip):
    out = Capture()
    server = Server(client=VerbaClient(live_backend, autostart=False), out=out)

    status = call(server, "verba_status", {})
    assert "only the test engine" in status["content"][0]["text"]

    result = call(server, "transcribe_whatsapp_chat",
                  {"path": str(export_zip), "language": "es", "provider": "mock", "wait_seconds": 30})
    text = result["content"][0]["text"]
    assert result["isError"] is False
    assert "status: completed" in text and "TEST engine" in text
    assert "🎤 Sprachnachricht" in text and "[09:16] Stan: Hola María!" in text
    assert any("notifications/progress" in line for line in out.lines)
    chat_id = text.split("chat_id: ")[1].split("\n")[0]

    images = call(server, "get_chat_images", {"chat_id": chat_id})
    kinds = [c["type"] for c in images["content"]]
    assert "image" in kinds
    img = next(c for c in images["content"] if c["type"] == "image")
    assert img["mimeType"] == "image/jpeg" and len(img["data"]) > 50
    idx = int(next(c["text"] for c in images["content"]
                   if c["type"] == "text" and c["text"].startswith("message_index")).split()[1])

    saved = call(server, "set_image_descriptions",
                 {"chat_id": chat_id, "descriptions": [{"message_index": idx, "description": "Ein blaues Quadrat"}]})
    assert "Saved 1" in saved["content"][0]["text"]
    again = call(server, "get_whatsapp_chat", {"chat_id": chat_id, "output_language": "es"})
    assert "Descripción: Ein blaues Quadrat" in again["content"][0]["text"]
    assert call(server, "get_chat_images", {"chat_id": chat_id})["content"][0]["text"].startswith("No (more)")

    listing = call(server, "list_whatsapp_chats", {})
    assert chat_id in listing["content"][0]["text"]

    missing = call(server, "transcribe_whatsapp_chat", {"path": "/nope/missing.zip"})
    assert missing["isError"] is True and "File not found" in missing["content"][0]["text"]


def test_cli_chat(live_backend, export_zip, tmp_path, monkeypatch, capsys):
    from verba import cli

    monkeypatch.setenv("VERBA_API_URL", live_backend)
    monkeypatch.setenv("VERBA_MCP_AUTOSTART", "0")
    out = tmp_path / "chat.md"
    code = cli.main(["chat", str(export_zip), "--language", "es", "--provider", "mock", "--format", "md", "--out", str(out)])
    assert code == 0
    assert out.read_text().startswith("# WhatsApp-Chat: María López")
