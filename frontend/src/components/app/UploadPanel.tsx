"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useRef, useState, type DragEvent } from "react";
import { ApiError, uploadFile, type ProjectSummary, type SystemInfo, type UploadHandle } from "@/lib/api";
import { formatBytes, formatDuration } from "@/lib/format";
import { errorMessage, useI18n } from "@/lib/i18n";
import { AlertIcon, CheckIcon, FileAudioIcon, FileVideoIcon, UploadIcon, XIcon } from "../Icons";
import { TranscribeOptions } from "./TranscribeOptions";

type UploadState =
  | { kind: "idle" }
  | { kind: "uploading"; name: string; size: number; progress: number }
  | { kind: "validating"; name: string; size: number }
  | { kind: "ready"; project: ProjectSummary }
  | { kind: "error"; message: string };

export function UploadPanel({ system, onUploaded }: { system: SystemInfo | null; onUploaded: () => void }) {
  const { t, locale } = useI18n();
  const router = useRouter();
  const [state, setState] = useState<UploadState>({ kind: "idle" });
  const [dragging, setDragging] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const handleRef = useRef<UploadHandle | null>(null);
  const dragDepth = useRef(0);

  const allowed = system?.allowed_extensions ?? [".mp3", ".wav", ".m4a", ".mp4"];
  const maxBytes = system?.limits.max_upload_bytes ?? 500 * 1024 * 1024;
  const formatsLabel = allowed.map((e) => e.slice(1).toUpperCase()).join(", ");
  const disabled = system === null;

  const start = (file: File) => {
    const ext = file.name.includes(".") ? `.${file.name.split(".").pop()!.toLowerCase()}` : "";
    if (!allowed.includes(ext)) {
      setState({ kind: "error", message: t("upload.badType", { formats: formatsLabel }) });
      return;
    }
    if (file.size > maxBytes) {
      setState({ kind: "error", message: t("upload.tooLarge", { size: formatBytes(maxBytes, locale) }) });
      return;
    }
    setState({ kind: "uploading", name: file.name, size: file.size, progress: 0 });
    const handle = uploadFile(file, (fraction) => {
      setState((s) =>
        s.kind === "uploading"
          ? fraction >= 1
            ? { kind: "validating", name: s.name, size: s.size }
            : { ...s, progress: fraction }
          : s,
      );
    });
    handleRef.current = handle;
    handle.promise
      .then((project) => {
        setState({ kind: "ready", project });
        onUploaded();
      })
      .catch((err: unknown) => {
        if (err instanceof ApiError && err.code === "aborted") {
          setState({ kind: "idle" });
          return;
        }
        const message =
          err instanceof ApiError
            ? err.code === "network_error"
              ? t("upload.networkError")
              : errorMessage(t, err)
            : t("upload.failed");
        setState({ kind: "error", message });
      })
      .finally(() => {
        handleRef.current = null;
      });
  };

  const onDrop = (e: DragEvent) => {
    e.preventDefault();
    dragDepth.current = 0;
    setDragging(false);
    if (disabled) return;
    const file = e.dataTransfer.files?.[0];
    if (file) start(file);
  };

  const reset = () => {
    setState({ kind: "idle" });
    if (inputRef.current) inputRef.current.value = "";
  };

  if (state.kind === "ready") {
    const p = state.project;
    const Icon = p.has_video ? FileVideoIcon : FileAudioIcon;
    return (
      <section className="card upload-ready" aria-labelledby="upload-ready-title" data-testid="upload-ready">
        <div className="upload-ready-head">
          <div className="file-icon"><Icon size={20} /></div>
          <div className="upload-ready-text">
            <p id="upload-ready-title" className="upload-ready-name" title={p.original_filename}>{p.original_filename}</p>
            <p className="hint upload-ready-ok"><CheckIcon size={14} /> {t("upload.ready")}</p>
          </div>
          <button type="button" className="btn btn-ghost btn-sm" onClick={reset}>{t("upload.another")}</button>
        </div>
        <dl className="meta-grid">
          <div><dt>{t("meta.duration")}</dt><dd className="tabular">{formatDuration(p.duration_seconds)}</dd></div>
          <div><dt>{t("meta.size")}</dt><dd className="tabular">{formatBytes(p.size_bytes, locale)}</dd></div>
          <div><dt>{t("meta.type")}</dt><dd>{p.has_video ? t("meta.video") : t("meta.audio")}</dd></div>
          <div><dt>{t("meta.codec")}</dt><dd>{p.media_info.audio_codec?.toUpperCase() ?? "–"}</dd></div>
        </dl>
        {p.duplicate_of && (
          <div className="alert alert-info">
            <span className="alert-icon"><AlertIcon size={16} /></span>
            <span>
              {t("upload.duplicate", { title: p.duplicate_of.title })}{" "}
              <Link className="link" href={`/app/project?id=${p.duplicate_of.id}`}>{t("upload.openDuplicate")}</Link>
            </span>
          </div>
        )}
        {system && (
          <TranscribeOptions projectId={p.id} system={system} onStarted={() => router.push(`/app/project?id=${p.id}`)} />
        )}
      </section>
    );
  }

  const busy = state.kind === "uploading" || state.kind === "validating";
  return (
    <section
      className={`dropzone${dragging ? " is-dragging" : ""}${busy ? " is-busy" : ""}${disabled ? " is-disabled" : ""}`}
      onDragEnter={(e) => {
        e.preventDefault();
        dragDepth.current += 1;
        if (!busy && !disabled) setDragging(true);
      }}
      onDragOver={(e) => e.preventDefault()}
      onDragLeave={() => {
        dragDepth.current -= 1;
        if (dragDepth.current <= 0) setDragging(false);
      }}
      onDrop={busy ? (e) => e.preventDefault() : onDrop}
      aria-label={t("upload.drop")}
    >
      <input
        ref={inputRef}
        type="file"
        className="sr-only"
        id="file-input"
        accept={allowed.join(",") + ",audio/*,video/*"}
        disabled={busy || disabled}
        data-testid="file-input"
        onChange={(e) => {
          const file = e.target.files?.[0];
          if (file) start(file);
        }}
      />
      {busy ? (
        <div className="dropzone-progress" aria-live="polite">
          <div className="dropzone-file">
            <FileAudioIcon size={18} />
            <span className="dropzone-filename">{state.name}</span>
            <span className="hint tabular">{formatBytes(state.size, locale)}</span>
          </div>
          <div className={`progress${state.kind === "validating" ? " progress-indeterminate" : ""}`}
            role="progressbar" aria-valuemin={0} aria-valuemax={100}
            aria-valuenow={state.kind === "uploading" ? Math.round(state.progress * 100) : undefined}>
            <span style={state.kind === "uploading" ? { width: `${Math.round(state.progress * 100)}%` } : undefined} />
          </div>
          <div className="dropzone-progress-foot">
            <span className="hint">
              {state.kind === "uploading" ? `${t("upload.uploading")} ${Math.round(state.progress * 100)} %` : t("upload.validating")}
            </span>
            {state.kind === "uploading" && (
              <button type="button" className="btn btn-ghost btn-sm" onClick={() => handleRef.current?.abort()}>
                <XIcon size={14} /> {t("upload.cancel")}
              </button>
            )}
          </div>
        </div>
      ) : (
        <div className="dropzone-idle">
          <div className="dropzone-icon" aria-hidden="true"><UploadIcon size={22} /></div>
          <p className="dropzone-title">{t("upload.drop")}</p>
          <p className="hint">
            {t("upload.or")}{" "}
          </p>
          <label htmlFor="file-input" className={`btn btn-primary${disabled ? " is-disabled" : ""}`} aria-disabled={disabled}>
            {t("upload.browse")}
          </label>
          <p className="hint dropzone-formats">{t("upload.formats", { formats: formatsLabel, size: formatBytes(maxBytes, locale) })}</p>
          {state.kind === "error" && (
            <p className="field-error" role="alert" data-testid="upload-error"><AlertIcon size={14} /> {state.message}</p>
          )}
        </div>
      )}
    </section>
  );
}
