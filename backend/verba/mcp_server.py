"""Verba as a tool for Claude: a Model Context Protocol (MCP) server over stdio.

Claude Desktop / Claude Code start this process and call its tools. It talks to
the local Verba backend over HTTP (and starts it if needed). All transcription
stays on this computer; image descriptions are written by Claude itself after it
has looked at the images returned by ``get_chat_images``.

Run: ``python backend/verba_mcp.py`` (see docs/CLAUDE_TOOL.md).
"""

from __future__ import annotations

import base64
import json
import sys
import traceback
from pathlib import Path

from .client import VerbaClient, VerbaError

SERVER_INFO = {"name": "verba", "version": "0.2.0"}
DEFAULT_PROTOCOL = "2025-06-18"
MAX_IMAGE_BYTES = 3_500_000
CLAUDE_IMAGE_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp"}

INSTRUCTIONS = (
    "Verba transcribes audio locally with Whisper. For a WhatsApp chat export (.zip from 'Export chat' with media, "
    "or _chat.txt) call transcribe_whatsapp_chat; it transcribes every voice note and returns one chronological text "
    "block with date, time and sender. If it returns while still processing, call get_whatsapp_chat later. To analyse "
    "pictures, call get_chat_images, look at each image, then save a short factual description per image with "
    "set_image_descriptions, and fetch the chat again so the descriptions appear in the text."
)

LANG_PROP = {"type": "string", "description": "Spoken language as ISO code (e.g. 'es', 'de') or 'auto' to detect per "
                                              "voice note. Use 'auto' for mixed-language chats.", "default": "auto"}

TOOLS = [
    {
        "name": "verba_status",
        "description": "Check whether Verba is running and which local transcription engine and model are available.",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "transcribe_whatsapp_chat",
        "description": "Import a WhatsApp chat export (path to the .zip with media, or the _chat.txt) and transcribe all "
                       "voice notes, audio files and videos locally. Returns the whole chat as one text block with date, "
                       "time, sender, text messages and transcripts. Long chats can take minutes.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Absolute path to the exported .zip or .txt file."},
                "language": LANG_PROP,
                "wait_seconds": {"type": "integer", "default": 600, "minimum": 0, "maximum": 3600,
                                 "description": "How long to wait for transcription before returning the status."},
                "output_language": {"type": "string", "enum": ["de", "en", "es"], "default": "de",
                                    "description": "Language of labels in the text block."},
            },
            "required": ["path"],
        },
    },
    {
        "name": "get_whatsapp_chat",
        "description": "Get progress and the transcribed text of an imported chat.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "chat_id": {"type": "string"},
                "format": {"type": "string", "enum": ["txt", "md", "json"], "default": "txt"},
                "output_language": {"type": "string", "enum": ["de", "en", "es"], "default": "de"},
                "wait_seconds": {"type": "integer", "default": 0, "minimum": 0, "maximum": 3600},
            },
            "required": ["chat_id"],
        },
    },
    {
        "name": "list_whatsapp_chats",
        "description": "List imported WhatsApp chats with their status. Optional search in titles and transcripts.",
        "inputSchema": {"type": "object", "properties": {"query": {"type": "string"}}},
    },
    {
        "name": "get_chat_images",
        "description": "Return images (photos, stickers) from an imported chat so you can look at them. Each image comes "
                       "with its message index, sender, time and caption. Then call set_image_descriptions.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "chat_id": {"type": "string"},
                "only_undescribed": {"type": "boolean", "default": True},
                "offset": {"type": "integer", "default": 0, "minimum": 0},
                "limit": {"type": "integer", "default": 5, "minimum": 1, "maximum": 10},
            },
            "required": ["chat_id"],
        },
    },
    {
        "name": "set_image_descriptions",
        "description": "Save descriptions for chat images (by message index). They appear in the chat text block.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "chat_id": {"type": "string"},
                "descriptions": {
                    "type": "array",
                    "items": {"type": "object", "properties": {"message_index": {"type": "integer"},
                                                               "description": {"type": "string"}},
                              "required": ["message_index", "description"]},
                },
            },
            "required": ["chat_id", "descriptions"],
        },
    },
    {
        "name": "transcribe_audio_file",
        "description": "Transcribe a single local audio or video file (mp3, wav, m4a, mp4, ogg, opus, …) and return the text.",
        "inputSchema": {
            "type": "object",
            "properties": {"path": {"type": "string"}, "language": LANG_PROP,
                           "wait_seconds": {"type": "integer", "default": 900, "minimum": 0, "maximum": 3600}},
            "required": ["path"],
        },
    },
]


class Server:
    def __init__(self, client: VerbaClient | None = None, out=None) -> None:
        self.client = client or VerbaClient()
        self.out = out or sys.stdout

    # --------------------------------------------------------------- protocol
    def send(self, message: dict) -> None:
        self.out.write(json.dumps(message, ensure_ascii=False) + "\n")
        self.out.flush()

    def handle(self, msg: dict) -> dict | None:
        method = msg.get("method")
        msg_id = msg.get("id")
        params = msg.get("params") or {}
        if msg_id is None:  # notification (e.g. notifications/initialized) – nothing to answer
            return None
        try:
            if method == "initialize":
                result = {"protocolVersion": params.get("protocolVersion") or DEFAULT_PROTOCOL,
                          "capabilities": {"tools": {"listChanged": False}}, "serverInfo": SERVER_INFO,
                          "instructions": INSTRUCTIONS}
            elif method == "ping":
                result = {}
            elif method == "tools/list":
                result = {"tools": TOOLS}
            elif method == "tools/call":
                token = (params.get("_meta") or {}).get("progressToken")
                result = self.call_tool(params.get("name", ""), params.get("arguments") or {}, token)
            else:
                return {"jsonrpc": "2.0", "id": msg_id, "error": {"code": -32601, "message": f"Unknown method {method}"}}
        except Exception as exc:  # never crash the server on one bad request
            traceback.print_exc(file=sys.stderr)
            return {"jsonrpc": "2.0", "id": msg_id, "error": {"code": -32603, "message": str(exc)}}
        return {"jsonrpc": "2.0", "id": msg_id, "result": result}

    def progress(self, token, done: int, total: int, message: str) -> None:
        if token is None:
            return
        self.send({"jsonrpc": "2.0", "method": "notifications/progress",
                   "params": {"progressToken": token, "progress": done, "total": max(total, 1), "message": message}})

    # ------------------------------------------------------------------ tools
    def call_tool(self, name: str, args: dict, token=None) -> dict:
        try:
            self.client.ensure_running()
            handler = getattr(self, f"tool_{name}", None)
            if handler is None:
                return _error(f"Unknown tool: {name}")
            return handler(args, token)
        except VerbaError as exc:
            return _error(f"{exc.message} ({exc.code})")

    def tool_verba_status(self, args, token):
        info = self.client.get_json("/api/system")
        engines = [f"- {p['name']}: {'available' if p['available'] else 'unavailable'}"
                   f"{' · model ' + p['model'] if p.get('model') and p['available'] else ''}"
                   f"{'' if p['available'] else ' (' + (p.get('reason') or '') + ')'}"
                   for p in info["providers"] if p["kind"] != "external"]
        lines = [f"Verba {info['version']} is running at {self.client.base_url}.",
                 f"Real local engine available: {'yes' if info['real_engine_available'] else 'NO – only the test engine'}",
                 *engines, f"Image OCR (Tesseract): {'yes' if info.get('ocr_available') else 'no'}",
                 f"Data folder: {info['storage']['data_dir']}"]
        return _text("\n".join(lines))

    def _chat_result(self, chat: dict, fmt: str, lang: str) -> dict:
        status = chat["status"]
        header = (f"chat_id: {chat['id']}\nstatus: {status} · voice notes/audio done: {chat['done_items']} of "
                  f"{chat['total_items']}")
        if chat.get("is_mock"):
            header += "\nWARNING: processed with the TEST engine – transcripts are placeholders, not real speech."
        if chat.get("error"):
            header += f"\nerror: {chat['error']['message']}"
        if status in ("pending", "processing"):
            header += "\nStill processing – call get_whatsapp_chat with this chat_id (and wait_seconds) to get the result."
        text = self.client.export_chat(chat["id"], fmt, lang).decode("utf-8")
        return _text(header + "\n\n" + text)

    def tool_transcribe_whatsapp_chat(self, args, token):
        path = Path(args["path"]).expanduser()
        chat = self.client.import_chat(path, args.get("language") or "auto", args.get("provider") or "auto")
        chat = self.client.wait_for_chat(chat["id"], float(args.get("wait_seconds", 600)),
                                         lambda c: self.progress(token, c["done_items"], c["total_items"],
                                                                 f"{c['done_items']}/{c['total_items']} transcribed"))
        return self._chat_result(chat, "txt", args.get("output_language") or "de")

    def tool_get_whatsapp_chat(self, args, token):
        chat_id = args["chat_id"]
        chat = self.client.wait_for_chat(chat_id, float(args.get("wait_seconds", 0)),
                                         lambda c: self.progress(token, c["done_items"], c["total_items"], c["status"]))
        return self._chat_result(chat, args.get("format") or "txt", args.get("output_language") or "de")

    def tool_list_whatsapp_chats(self, args, token):
        q = args.get("query")
        chats = self.client.get_json("/api/chats" + (f"?q={_quote(q)}" if q else ""))["chats"]
        if not chats:
            return _text("No chats imported yet.")
        return _text("\n".join(f"{c['id']} · {c['title']} · {c['status']} · {c['done_items']}/{c['total_items']} "
                               f"voice notes · imported {c['created_at'][:16]}" for c in chats))

    def tool_get_chat_images(self, args, token):
        chat = self.client.get_json(f"/api/chats/{args['chat_id']}")
        images = [m for m in chat["messages"] if m["kind"] in ("image", "sticker") and m["has_media"]
                  and not (args.get("only_undescribed", True) and m["image_description"])]
        offset, limit = int(args.get("offset", 0)), int(args.get("limit", 5))
        page = images[offset:offset + limit]
        if not page:
            return _text("No (more) images to describe in this chat.")
        content: list[dict] = [{"type": "text", "text": f"{len(images)} image(s) total; showing {offset + 1}–"
                                                        f"{offset + len(page)}. Describe each briefly and factually, "
                                                        "then call set_image_descriptions."}]
        for m in page:
            caption = f" · caption: {m['text']}" if m["text"] else ""
            ocr = f" · text found by OCR: {m['image_text']}" if m.get("image_text") else ""
            content.append({"type": "text", "text": f"message_index {m['idx']} · {m['sender']} · {m['ts']}{caption}{ocr}"})
            data, mime = self.client.get_bytes(f"/api/chats/{chat['id']}/media/{m['idx']}")
            mime = mime.split(";")[0].strip()
            if mime not in CLAUDE_IMAGE_TYPES:
                content.append({"type": "text", "text": f"(format {mime} cannot be shown – skip or describe as unknown)"})
            elif len(data) > MAX_IMAGE_BYTES:
                content.append({"type": "text", "text": "(image too large to show)"})
            else:
                content.append({"type": "image", "data": base64.b64encode(data).decode(), "mimeType": mime})
        return {"content": content, "isError": False}

    def tool_set_image_descriptions(self, args, token):
        saved = 0
        for item in args.get("descriptions") or []:
            self.client.send_json("PATCH", f"/api/chats/{args['chat_id']}/messages/{int(item['message_index'])}",
                                  {"image_description": str(item["description"])})
            saved += 1
        return _text(f"Saved {saved} description(s). Call get_whatsapp_chat to see the updated text.")

    def tool_transcribe_audio_file(self, args, token):
        project = self.client.transcribe_file(Path(args["path"]), args.get("language") or "auto",
                                              timeout=float(args.get("wait_seconds", 900)),
                                              on_progress=lambda p: self.progress(
                                                  token, int(((p.get("job") or {}).get("progress") or 0) * 100), 100,
                                                  p["status"]))
        if project["status"] != "completed":
            err = (project.get("job") or {}).get("error") or {}
            return _text(f"project_id: {project['id']}\nstatus: {project['status']}"
                         + (f"\nerror: {err.get('message')}" if err else ""))
        text = "\n".join(s["text"] for s in project["segments"])
        warn = "\nWARNING: test engine output, not a real transcription." if project["is_mock"] else ""
        return _text(f"project_id: {project['id']} · language: {project['language_detected']}{warn}\n\n{text}")


def _text(text: str) -> dict:
    return {"content": [{"type": "text", "text": text}], "isError": False}


def _error(text: str) -> dict:
    return {"content": [{"type": "text", "text": text}], "isError": True}


def _quote(value: str) -> str:
    from urllib.parse import quote

    return quote(value)


def main() -> None:
    # stdout carries the protocol; everything else goes to stderr.
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    server = Server()
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            server.send({"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "Parse error"}})
            continue
        reply = server.handle(msg)
        if reply is not None:
            server.send(reply)


if __name__ == "__main__":
    main()
