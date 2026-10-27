"""Transcript exports. Timestamps come only from the engine's segments; none are invented."""

from __future__ import annotations

import io
import zipfile
from xml.sax.saxutils import escape


def format_timestamp(seconds: float, separator: str = ",") -> str:
    """HH:MM:SS,mmm (SRT) or HH:MM:SS.mmm (VTT)."""
    if seconds < 0:
        seconds = 0.0
    total_ms = int(round(seconds * 1000))
    hours, rem = divmod(total_ms, 3_600_000)
    minutes, rem = divmod(rem, 60_000)
    secs, ms = divmod(rem, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}{separator}{ms:03d}"


def format_clock(seconds: float) -> str:
    """Short [MM:SS] / [H:MM:SS] label used in plain-text exports."""
    total = int(max(0, seconds))
    h, rem = divmod(total, 3600)
    m, s = divmod(rem, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"


def _clean(text: str) -> str:
    return " ".join((text or "").split())


def _timed(segments: list[dict]) -> list[dict]:
    """Segments with usable text and a valid, monotonic time range."""
    out = []
    for seg in segments:
        text = _clean(seg.get("text", ""))
        if not text:
            continue
        start = max(0.0, float(seg.get("start", 0)))
        end = max(start, float(seg.get("end", start)))
        if end == start:
            end = start + 0.001
        out.append({"start": start, "end": end, "text": text})
    return out


def to_txt(segments: list[dict], with_timestamps: bool = False) -> str:
    lines = []
    for seg in _timed(segments):
        lines.append(f"[{format_clock(seg['start'])}] {seg['text']}" if with_timestamps else seg["text"])
    return ("\n" if with_timestamps else "\n\n").join(lines) + "\n" if lines else ""


def to_srt(segments: list[dict]) -> str:
    blocks = []
    for i, seg in enumerate(_timed(segments), start=1):
        blocks.append(f"{i}\n{format_timestamp(seg['start'])} --> {format_timestamp(seg['end'])}\n{seg['text']}\n")
    return "\n".join(blocks)


def to_vtt(segments: list[dict]) -> str:
    blocks = ["WEBVTT\n"]
    for seg in _timed(segments):
        # "-->" inside cue text would break the cue; replace the arrow defensively.
        text = seg["text"].replace("-->", "→")
        blocks.append(f"{format_timestamp(seg['start'], '.')} --> {format_timestamp(seg['end'], '.')}\n{text}\n")
    return "\n".join(blocks)


def to_docx(title: str, segments: list[dict], with_timestamps: bool = True) -> bytes:
    """Minimal standards-compliant DOCX built with the standard library only."""
    paragraphs = [f'<w:p><w:pPr><w:pStyle w:val="Title"/></w:pPr><w:r><w:t xml:space="preserve">{escape(title)}</w:t></w:r></w:p>']
    for seg in _timed(segments):
        runs = ""
        if with_timestamps:
            runs += (f'<w:r><w:rPr><w:color w:val="808080"/></w:rPr>'
                     f'<w:t xml:space="preserve">[{format_clock(seg["start"])}] </w:t></w:r>')
        runs += f'<w:r><w:t xml:space="preserve">{escape(seg["text"])}</w:t></w:r>'
        paragraphs.append(f"<w:p>{runs}</w:p>")

    document = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        f'<w:body>{"".join(paragraphs)}<w:sectPr/></w:body></w:document>'
    )
    styles = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        '<w:style w:type="paragraph" w:default="1" w:styleId="Normal"><w:name w:val="Normal"/>'
        '<w:pPr><w:spacing w:after="160" w:line="300" w:lineRule="auto"/></w:pPr>'
        '<w:rPr><w:sz w:val="22"/></w:rPr></w:style>'
        '<w:style w:type="paragraph" w:styleId="Title"><w:name w:val="Title"/><w:basedOn w:val="Normal"/>'
        '<w:rPr><w:b/><w:sz w:val="36"/></w:rPr></w:style></w:styles>'
    )
    content_types = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/word/document.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
        '<Override PartName="/word/styles.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>'
        '</Types>'
    )
    rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
        'Target="word/document.xml"/></Relationships>'
    )
    doc_rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" '
        'Target="styles.xml"/></Relationships>'
    )
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", content_types)
        zf.writestr("_rels/.rels", rels)
        zf.writestr("word/document.xml", document)
        zf.writestr("word/styles.xml", styles)
        zf.writestr("word/_rels/document.xml.rels", doc_rels)
    return buf.getvalue()
