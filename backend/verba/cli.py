"""Command line: ``python -m verba.cli chat <export.zip> --language es --out chat.txt``."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .client import VerbaClient, VerbaError


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="verba", description="Verba – local transcription")
    sub = parser.add_subparsers(dest="command", required=True)

    chat = sub.add_parser("chat", help="Transcribe a WhatsApp chat export (.zip or .txt)")
    chat.add_argument("path")
    chat.add_argument("--language", default="auto", help="ISO code such as es/de, or auto (default)")
    chat.add_argument("--provider", default="auto")
    chat.add_argument("--format", default="txt", choices=["txt", "md", "json", "docx"])
    chat.add_argument("--labels", default="de", choices=["de", "en", "es"], help="Language of labels in the output")
    chat.add_argument("--out", help="Write to this file instead of the terminal")
    chat.add_argument("--timeout", type=float, default=6 * 3600)

    one = sub.add_parser("transcribe", help="Transcribe one audio/video file")
    one.add_argument("path")
    one.add_argument("--language", default="auto")

    sub.add_parser("status", help="Show engine status")
    args = parser.parse_args(argv)

    client = VerbaClient()
    try:
        client.ensure_running()
        if args.command == "status":
            info = client.get_json("/api/system")
            for p in info["providers"]:
                print(f"{p['name']:16} {'ready' if p['available'] else 'unavailable'}  {p.get('reason') or ''}")
            return 0
        if args.command == "transcribe":
            project = client.transcribe_file(Path(args.path), args.language)
            if project["status"] != "completed":
                print(f"Status: {project['status']}", file=sys.stderr)
                return 1
            print("\n".join(s["text"] for s in project["segments"]))
            return 0

        created = client.import_chat(Path(args.path), args.language, args.provider)
        print(f"Chat imported: {created['title']} – {created['total_items']} voice notes/audio/videos", file=sys.stderr)

        def show(c: dict) -> None:
            print(f"\r  {c['done_items']}/{c['total_items']} transcribed ({c['status']})   ", end="", file=sys.stderr)

        result = client.wait_for_chat(created["id"], args.timeout, show)
        print(file=sys.stderr)
        data = client.export_chat(result["id"], args.format, args.labels)
        if args.out:
            Path(args.out).write_bytes(data)
            print(f"Written to {args.out}", file=sys.stderr)
        else:
            sys.stdout.buffer.write(data)
        return 0 if result["status"] == "completed" else 1
    except VerbaError as exc:
        print(f"Error: {exc.message}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
