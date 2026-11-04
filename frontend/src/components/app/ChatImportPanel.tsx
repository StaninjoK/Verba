"use client";

import { useRouter } from "next/navigation";
import { useMemo, useRef, useState, type DragEvent } from "react";
import { ApiError, chatApi, type SystemInfo, type UploadHandle, type ChatSummary } from "@/lib/api";
import { formatBytes } from "@/lib/format";
import { errorMessage, useI18n, type MessageKey } from "@/lib/i18n";
import { languageName } from "@/lib/useSystem";
import { AlertIcon, InfoIcon, XIcon } from "../Icons";

function WhatsAppGlyph() {
  return (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" aria-hidden="true">
      <path d="M4.5 19.5l1.2-3.6A7.8 7.8 0 1 1 8.6 18.6L4.5 19.5Z" strokeLinejoin="round" />
      <path d="M9.2 8.6c.2-.5.6-.5.9-.5h.4c.2 0 .4.1.5.4l.6 1.4c.1.2 0 .5-.1.6l-.4.5c.5.9 1.3 1.7 2.3 2.2l.5-.5c.2-.2.4-.2.6-.1l1.4.6c.3.1.4.3.4.5v.4c0 .4-.2.8-.6 1-.6.3-1.4.4-2.4-.1a8.4 8.4 0 0 1-3.6-3.4c-.6-1-.6-2-.3-2.6Z"
        fill="currentColor" stroke="none" />
    </svg>
  );
}

type State =
  | { kind: "idle" }
  | { kind: "selected"; file: File }
  | { kind: "uploading"; file: File; progress: number }
  | { kind: "reading"; file: File }
  | { kind: "error"; message: string; file?: File };

export function ChatImportPanel({ system }: { system: SystemInfo | null }) {
  const { t, locale } = useI18n();
  const router = useRouter();
  const [state, setState] = useState<State>({ kind: "idle" });
  const [language, setLanguage] = useState("auto");
  const realAvailable = system?.providers.some((p) => p.kind === "local" && p.available) ?? false;
  const selectable = system?.providers.filter((p) => p.allowed && p.kind !== "external") ?? [];
  const [provider, setProvider] = useState<string | null>(null);
  const engine = provider ?? (realAvailable ? "auto" : (selectable.find((p) => p.is_mock && p.available)?.name ?? "auto"));
  const [dragging, setDragging] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const handleRef = useRef<UploadHandle<ChatSummary> | null>(null);
  const maxBytes = system?.max_chat_import_bytes ?? 2000 * 1024 * 1024;

  const languages = useMemo(
    () =>
      (system?.languages ?? [])
        .filter((c) => c !== "auto")
        .map((code) => ({ code, name: languageName(code, locale) }))
        .sort((a, b) => a.name.localeCompare(b.name, locale)),
    [system?.languages, locale],
  );

  const pick = (file: File) => {
    const ext = file.name.toLowerCase().split(".").pop();
    if (ext !== "zip" && ext !== "txt") {
      setState({ kind: "error", message: t("chat.badType") });
      return;
    }
    if (file.size > maxBytes) {
      setState({ kind: "error", message: t("upload.tooLarge", { size: formatBytes(maxBytes, locale) }) });
      return;
    }
    setState({ kind: "selected", file });
  };

  const start = () => {
    if (state.kind !== "selected" && state.kind !== "error") return;
    const file = state.file;
    if (!file) return;
    setState({ kind: "uploading", file, progress: 0 });
    const handle = chatApi.upload(file, engine, language, (f) =>
      setState((s) => (s.kind === "uploading" ? (f >= 1 ? { kind: "reading", file } : { ...s, progress: f }) : s)),
    );
    handleRef.current = handle;
    handle.promise
      .then((chat) => router.push(`/app/chat?id=${chat.id}`))
      .catch((err: unknown) => {
        if (err instanceof ApiError && err.code === "aborted") return setState({ kind: "selected", file });
        const message = err instanceof ApiError
          ? err.code === "network_error" ? t("upload.networkError") : errorMessage(t, err)
          : t("upload.failed");
        setState({ kind: "error", message, file });
      });
  };

  const onDrop = (e: DragEvent) => {
    e.preventDefault();
    setDragging(false);
    const file = e.dataTransfer.files?.[0];
    if (file && state.kind !== "uploading" && state.kind !== "reading") pick(file);
  };

  const busy = state.kind === "uploading" || state.kind === "reading";
  const file = "file" in state ? state.file : undefined;
  const chosen = system?.providers.find((p) => p.name === engine);

  return (
    <section className="card chat-import" aria-labelledby="chat-import-title" data-testid="chat-import">
      <div
        className={`dropzone chat-drop${dragging ? " is-dragging" : ""}`}
        onDragOver={(e) => { e.preventDefault(); if (!busy) setDragging(true); }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
      >
        <input ref={inputRef} id="chat-file" type="file" className="sr-only" accept=".zip,.txt,application/zip,text/plain"
          disabled={busy} data-testid="chat-file-input" onChange={(e) => { const f = e.target.files?.[0]; if (f) pick(f); }} />
        <div className="dropzone-icon chat-icon"><WhatsAppGlyph /></div>
        <h2 id="chat-import-title" className="dropzone-title">{t("chat.importTitle")}</h2>
        <p className="hint chat-import-hint">{t("chat.importHint")}</p>
        {file ? (
          <p className="chat-file"><strong>{file.name}</strong> <span className="hint tabular">{formatBytes(file.size, locale)}</span></p>
        ) : null}
        {!busy && (
          <label htmlFor="chat-file" className={`btn ${file ? "" : "btn-primary"}`}>{file ? t("upload.another") : t("chat.choose")}</label>
        )}
        <p className="hint dropzone-formats">{t("chat.formats", { size: formatBytes(maxBytes, locale) })}</p>
      </div>

      {busy && (
        <div className="chat-import-progress" aria-live="polite">
          <div className={`progress${state.kind === "reading" ? " progress-indeterminate" : ""}`}>
            <span style={state.kind === "uploading" ? { width: `${Math.round(state.progress * 100)}%` } : undefined} />
          </div>
          <div className="dropzone-progress-foot">
            <span className="hint">
              {state.kind === "uploading" ? `${t("upload.uploading")} ${Math.round(state.progress * 100)} %` : t("chat.reading")}
            </span>
            {state.kind === "uploading" && (
              <button type="button" className="btn btn-ghost btn-sm" onClick={() => handleRef.current?.abort()}>
                <XIcon size={14} /> {t("upload.cancel")}
              </button>
            )}
          </div>
        </div>
      )}

      {(state.kind === "selected" || state.kind === "error") && (
        <div className="options chat-options">
          <div className="options-grid">
            <div>
              <label className="label" htmlFor="chat-language">{t("chat.language")}</label>
              <select id="chat-language" className="select" value={language} onChange={(e) => setLanguage(e.target.value)}>
                <option value="auto">{t("chat.autoPerMessage")}</option>
                {languages.map((l) => <option key={l.code} value={l.code}>{l.name}</option>)}
              </select>
            </div>
            <div>
              <label className="label" htmlFor="chat-engine">{t("opts.engine")}</label>
              <select id="chat-engine" className="select" value={engine} onChange={(e) => setProvider(e.target.value)}>
                {realAvailable && <option value="auto">{t("engine.auto")}</option>}
                {selectable.map((p) => (
                  <option key={p.name} value={p.name} disabled={!p.available}>
                    {t(`provider.${p.name}` as MessageKey)}
                    {p.is_mock ? ` ${t("engine.mockSuffix")}` : ""}
                    {p.model && !p.is_mock ? ` · ${p.model}` : ""}
                    {!p.available ? ` (${t("engine.unavailable")})` : ""}
                  </option>
                ))}
              </select>
            </div>
          </div>
          <p className="hint options-note-neutral"><InfoIcon size={14} /> {t("chat.languageHint")}</p>
          {chosen?.is_mock && <p className="hint options-note"><InfoIcon size={14} /> {t("ws.mockBody")}</p>}
          {state.kind === "error" && (
            <p className="field-error" role="alert" data-testid="chat-error"><AlertIcon size={14} /> {state.message}</p>
          )}
          {file && (
            <button type="button" className="btn btn-primary btn-lg options-start" onClick={start} data-testid="chat-start">
              {t("chat.start")}
            </button>
          )}
        </div>
      )}
    </section>
  );
}
