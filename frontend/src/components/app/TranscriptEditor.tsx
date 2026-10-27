"use client";

import { Fragment, useCallback, useEffect, useMemo, useRef, useState, type KeyboardEvent } from "react";
import { api, ApiError, type Project, type Segment } from "@/lib/api";
import { activeSegmentIndex, findMatches, formatClock, segmentsToText, type Match } from "@/lib/format";
import { useI18n } from "@/lib/i18n";
import {
  AlertIcon,
  CheckIcon,
  ChevronDownIcon,
  ChevronUpIcon,
  CopyIcon,
  DownloadIcon,
  PlayIcon,
  SearchIcon,
} from "../Icons";
import { useToast } from "../Toast";

type SaveState = "saved" | "dirty" | "saving" | "error" | "conflict";

interface Draft {
  baseVersion: number;
  texts: Record<number, string>;
}

const draftKey = (id: string) => `verba-draft-${id}`;
const SAVE_DELAY_MS = 900;

function readDraft(id: string): Draft | null {
  try {
    const raw = window.localStorage.getItem(draftKey(id));
    return raw ? (JSON.parse(raw) as Draft) : null;
  } catch {
    return null;
  }
}

function writeDraft(id: string, draft: Draft | null) {
  try {
    if (draft) window.localStorage.setItem(draftKey(id), JSON.stringify(draft));
    else window.localStorage.removeItem(draftKey(id));
  } catch {
    // storage full or unavailable – the in-memory copy is still kept
  }
}

/** Text with highlighted matches, used as the auto-sizing backdrop of each textarea. */
function Highlighted({ text, matches, current }: { text: string; matches: Match[]; current: Match | null }) {
  if (!matches.length) return <>{text + "​"}</>;
  const parts: React.ReactNode[] = [];
  let pos = 0;
  matches.forEach((m, i) => {
    if (m.start > pos) parts.push(text.slice(pos, m.start));
    parts.push(
      <mark key={i} className={current === m ? "is-current" : undefined}>
        {text.slice(m.start, m.end)}
      </mark>,
    );
    pos = m.end;
  });
  parts.push(text.slice(pos) + "​");
  return <>{parts.map((p, i) => <Fragment key={i}>{p}</Fragment>)}</>;
}

const EXPORTS: { format: string; timestamps?: boolean; key: Parameters<ReturnType<typeof useI18n>["t"]>[0]; ext: string }[] = [
  { format: "txt", key: "ws.dl.txt", ext: "TXT" },
  { format: "txt", timestamps: true, key: "ws.dl.txtTs", ext: "TXT" },
  { format: "srt", key: "ws.dl.srt", ext: "SRT" },
  { format: "vtt", key: "ws.dl.vtt", ext: "VTT" },
  { format: "docx", timestamps: true, key: "ws.dl.docx", ext: "DOCX" },
  { format: "json", key: "ws.dl.json", ext: "JSON" },
];

export function TranscriptEditor({ project }: { project: Project }) {
  const { t } = useI18n();
  const toast = useToast();
  const [segments, setSegments] = useState<Segment[]>(project.segments);
  const [saveState, setSaveState] = useState<SaveState>("saved");
  const [restore, setRestore] = useState<Draft | null>(null);
  const [query, setQuery] = useState("");
  const [matchIndex, setMatchIndex] = useState(0);
  const [currentTime, setCurrentTime] = useState(0);
  const [hasPlayed, setHasPlayed] = useState(false);
  const [mediaError, setMediaError] = useState(false);
  const [exportOpen, setExportOpen] = useState(false);

  const versionRef = useRef(project.transcript_version);
  const segmentsRef = useRef(segments);
  const editSeq = useRef(0);
  const savedSeq = useRef(0);
  const inFlight = useRef<Promise<boolean> | null>(null);
  const timer = useRef<number | null>(null);
  const mediaRef = useRef<HTMLMediaElement | null>(null);
  const listRef = useRef<HTMLOListElement>(null);
  const exportRef = useRef<HTMLDivElement>(null);
  const followPlayback = useRef(true);

  useEffect(() => {
    segmentsRef.current = segments;
  }, [segments]);

  // Offer to restore edits that never reached the server (crash, closed tab, offline).
  useEffect(() => {
    const draft = readDraft(project.id);
    if (!draft) return;
    const differs = project.segments.some((s) => s.id in draft.texts && draft.texts[s.id] !== s.text);
    // eslint-disable-next-line react-hooks/set-state-in-effect -- the draft only exists in browser storage
    if (differs) setRestore(draft);
    else writeDraft(project.id, null);
  }, [project.id, project.segments]);

  const saveRef = useRef<() => Promise<boolean>>(async () => true);
  const scheduleSave = useCallback(() => {
    if (timer.current) window.clearTimeout(timer.current);
    timer.current = window.setTimeout(() => void saveRef.current(), SAVE_DELAY_MS);
  }, []);

  const save = useCallback(async (): Promise<boolean> => {
    if (inFlight.current) {
      await inFlight.current;
    }
    if (editSeq.current === savedSeq.current) return true;
    const seq = editSeq.current;
    const payload = segmentsRef.current.map((s) => ({ id: s.id, text: s.text }));
    setSaveState("saving");
    const run = (async () => {
      try {
        const res = await api.saveTranscript(project.id, versionRef.current, payload);
        versionRef.current = res.version;
        savedSeq.current = seq;
        if (editSeq.current === seq) {
          writeDraft(project.id, null);
          setSaveState("saved");
        } else {
          setSaveState("dirty");
        }
        return true;
      } catch (e) {
        setSaveState(e instanceof ApiError && e.code === "version_conflict" ? "conflict" : "error");
        return false;
      } finally {
        inFlight.current = null;
      }
    })();
    inFlight.current = run;
    const ok = await run;
    if (ok && editSeq.current !== savedSeq.current) scheduleSave(); // edits arrived while saving
    return ok;
  }, [project.id, scheduleSave]);

  useEffect(() => {
    saveRef.current = save;
  }, [save]);

  const editSegment = (id: number, text: string) => {
    editSeq.current += 1;
    setSegments((prev) => {
      const next = prev.map((s) => (s.id === id ? { ...s, text } : s));
      writeDraft(project.id, { baseVersion: versionRef.current, texts: Object.fromEntries(next.map((s) => [s.id, s.text])) });
      return next;
    });
    setSaveState((s) => (s === "conflict" ? s : "dirty"));
    scheduleSave();
  };

  // Warn before leaving with unsaved edits; flush on unmount.
  useEffect(() => {
    const onBeforeUnload = (e: BeforeUnloadEvent) => {
      if (editSeq.current !== savedSeq.current) {
        e.preventDefault();
      }
    };
    window.addEventListener("beforeunload", onBeforeUnload);
    return () => {
      window.removeEventListener("beforeunload", onBeforeUnload);
      if (timer.current) window.clearTimeout(timer.current);
      if (editSeq.current !== savedSeq.current) void save();
    };
  }, [save]);

  const applyRestore = () => {
    if (!restore) return;
    editSeq.current += 1;
    setSegments((prev) => prev.map((s) => (s.id in restore.texts ? { ...s, text: restore.texts[s.id] } : s)));
    setRestore(null);
    setSaveState("dirty");
    scheduleSave();
  };

  // ------------------------------------------------------------- search
  const matches = useMemo(() => findMatches(segments, query), [segments, query]);
  const safeIndex = matches.length ? Math.min(matchIndex, matches.length - 1) : 0;
  const current = matches.length ? matches[safeIndex] : null;
  const matchesBySegment = useMemo(() => {
    const map = new Map<number, Match[]>();
    for (const m of matches) map.set(m.segmentId, [...(map.get(m.segmentId) ?? []), m]);
    return map;
  }, [matches]);

  const goTo = (delta: number) => {
    if (!matches.length) return;
    setMatchIndex((i) => (Math.min(i, matches.length - 1) + delta + matches.length) % matches.length);
  };

  useEffect(() => {
    if (!current) return;
    followPlayback.current = false;
    listRef.current?.querySelector(`[data-seg="${current.segmentId}"]`)?.scrollIntoView({ block: "center", behavior: "smooth" });
  }, [current]);

  // ------------------------------------------------------------ playback
  const activeIdx = hasPlayed ? activeSegmentIndex(segments, currentTime) : -1;
  const activeId = activeIdx >= 0 ? segments[activeIdx].id : null;
  useEffect(() => {
    if (activeId == null || !followPlayback.current || mediaRef.current?.paused) return;
    const el = listRef.current?.querySelector(`[data-seg="${activeId}"]`);
    el?.scrollIntoView({ block: "nearest", behavior: "smooth" });
  }, [activeId]);

  const seek = (time: number) => {
    const media = mediaRef.current;
    if (!media) return;
    followPlayback.current = true;
    media.currentTime = time;
    void media.play().catch(() => {});
  };

  // ------------------------------------------------------------ actions
  const copyAll = async () => {
    try {
      await navigator.clipboard.writeText(segmentsToText(segments));
      toast(t("ws.copied"));
    } catch {
      toast(t("ws.copyFailed"), "error");
    }
  };

  const download = async (format: string, timestamps?: boolean) => {
    setExportOpen(false);
    if (editSeq.current !== savedSeq.current) {
      const ok = await save();
      if (!ok) {
        toast(t("ws.saveFailed"), "error");
        return;
      }
    }
    const a = document.createElement("a");
    a.href = api.exportUrl(project.id, format, timestamps);
    a.rel = "noopener";
    document.body.appendChild(a);
    a.click();
    a.remove();
  };

  useEffect(() => {
    if (!exportOpen) return;
    const close = (e: MouseEvent) => {
      if (!exportRef.current?.contains(e.target as Node)) setExportOpen(false);
    };
    const esc = (e: globalThis.KeyboardEvent) => e.key === "Escape" && setExportOpen(false);
    document.addEventListener("mousedown", close);
    document.addEventListener("keydown", esc);
    return () => {
      document.removeEventListener("mousedown", close);
      document.removeEventListener("keydown", esc);
    };
  }, [exportOpen]);

  const onEditorKey = (e: KeyboardEvent) => {
    if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "s") {
      e.preventDefault();
      if (timer.current) window.clearTimeout(timer.current);
      void save();
    }
  };

  const saveLabel = {
    saved: t("ws.saved"),
    dirty: t("ws.unsaved"),
    saving: t("ws.saving"),
    error: t("ws.saveFailed"),
    conflict: t("ws.conflict"),
  }[saveState];

  const mediaSrc = api.mediaUrl(project.id);

  return (
    <div className="editor-layout">
      <div className="editor-media">
        {mediaError ? (
          <p className="hint media-error">{t("ws.mediaUnavailable")}</p>
        ) : project.has_video ? (
          <video ref={(el) => { mediaRef.current = el; }} src={mediaSrc} controls preload="metadata" playsInline
            className="media-video" onTimeUpdate={(e) => setCurrentTime(e.currentTarget.currentTime)} onPlay={() => setHasPlayed(true)}
            onError={() => setMediaError(true)} />
        ) : (
          <audio ref={(el) => { mediaRef.current = el; }} src={mediaSrc} controls preload="metadata" className="media-audio"
            onTimeUpdate={(e) => setCurrentTime(e.currentTarget.currentTime)} onPlay={() => setHasPlayed(true)} onError={() => setMediaError(true)} />
        )}
      </div>

      <div className="editor-toolbar">
        <div className="search editor-search">
          <SearchIcon size={16} />
          <label htmlFor="transcript-search" className="sr-only">{t("ws.searchPlaceholder")}</label>
          <input id="transcript-search" className="input" type="search" placeholder={t("ws.searchPlaceholder")} value={query}
            onChange={(e) => {
              setQuery(e.target.value);
              setMatchIndex(0);
            }}
            onKeyDown={(e) => {
              if (e.key === "Enter") {
                e.preventDefault();
                goTo(e.shiftKey ? -1 : 1);
              }
            }} />
          {query.trim() && (
            <span className="search-count hint tabular" aria-live="polite" data-testid="match-count">
              {matches.length ? t("ws.matches", { current: safeIndex + 1, total: matches.length }) : t("ws.noMatches")}
            </span>
          )}
          {matches.length > 1 && (
            <>
              <button type="button" className="btn btn-ghost btn-icon btn-sm" onClick={() => goTo(-1)} aria-label={t("ws.prevMatch")}>
                <ChevronUpIcon size={16} />
              </button>
              <button type="button" className="btn btn-ghost btn-icon btn-sm" onClick={() => goTo(1)} aria-label={t("ws.nextMatch")}>
                <ChevronDownIcon size={16} />
              </button>
            </>
          )}
        </div>
        <div className="editor-actions">
          <span className={`save-state save-${saveState}`} data-testid="save-state" aria-live="polite">
            {saveState === "saving" ? <span className="spinner" aria-hidden="true" /> : saveState === "saved" ? <CheckIcon size={14} /> : saveState === "dirty" ? null : <AlertIcon size={14} />}
            {saveState === "error" ? (
              <button type="button" className="link-button" onClick={() => void save()}>{saveLabel}</button>
            ) : (
              <span>{saveLabel}</span>
            )}
            {saveState === "conflict" && (
              <button type="button" className="link-button" onClick={() => window.location.reload()}>{t("ws.reload")}</button>
            )}
          </span>
          <button type="button" className="btn btn-sm" onClick={copyAll} aria-label={t("ws.copy")}>
            <CopyIcon size={15} /> <span className="hide-sm">{t("ws.copy")}</span>
          </button>
          <div className="export" ref={exportRef}>
            <button type="button" className="btn btn-primary btn-sm" aria-haspopup="menu" aria-expanded={exportOpen}
              onClick={() => setExportOpen((o) => !o)} data-testid="export-button">
              <DownloadIcon size={15} /> {t("ws.download")}
            </button>
            {exportOpen && (
              <div className="menu menu-right" role="menu">
                {EXPORTS.map((e) => (
                  <button key={`${e.format}-${e.timestamps ? 1 : 0}`} type="button" role="menuitem" className="menu-item"
                    data-format={`${e.format}${e.timestamps ? "-ts" : ""}`} onClick={() => void download(e.format, e.timestamps)}>
                    <span>{t(e.key)}</span>
                    <small>{e.ext}</small>
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>

      {restore && (
        <div className="alert alert-info restore">
          <span className="alert-icon"><AlertIcon size={16} /></span>
          <span><strong>{t("ws.restoreTitle")}.</strong> {t("ws.restoreBody")}</span>
          <span className="restore-actions">
            <button type="button" className="btn btn-sm btn-primary" onClick={applyRestore}>{t("ws.restore")}</button>
            <button type="button" className="btn btn-sm" onClick={() => { writeDraft(project.id, null); setRestore(null); }}>
              {t("ws.discard")}
            </button>
          </span>
        </div>
      )}

      <ol className="segments" ref={listRef} onKeyDown={onEditorKey} data-testid="segments">
        {segments.map((seg) => {
          const segMatches = matchesBySegment.get(seg.id) ?? [];
          const isActive = seg.id === activeId;
          return (
            <li key={seg.id} data-seg={seg.id}
              className={`segment${isActive ? " is-active" : ""}${segMatches.length ? " has-match" : ""}`}>
              <button type="button" className="segment-time mono" onClick={() => seek(seg.start)}
                aria-label={t("ws.playFrom", { time: formatClock(seg.start) })} disabled={mediaError}>
                <PlayIcon size={10} className="segment-play" />
                {formatClock(seg.start)}
              </button>
              <div className="segment-text">
                <div className="segment-backdrop" aria-hidden="true">
                  <Highlighted text={seg.text} matches={segMatches} current={current} />
                </div>
                <textarea
                  value={seg.text}
                  onChange={(e) => editSegment(seg.id, e.target.value)}
                  onFocus={() => { followPlayback.current = false; }}
                  aria-label={t("ws.segment", { time: formatClock(seg.start) })}
                  spellCheck
                  rows={1}
                />
              </div>
            </li>
          );
        })}
      </ol>
      <p className="hint editor-note">{t("ws.timestampsNote")} <span className="kbd">Ctrl</span> + <span className="kbd">S</span></p>
    </div>
  );
}
