"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { AppHeader } from "@/components/app/AppHeader";
import { ConfirmDialog, RenameDialog } from "@/components/app/Dialog";
import { MockBadge, StatusBadge } from "@/components/app/StatusBadge";
import { AlertIcon, ArrowLeftIcon, CopyIcon, DownloadIcon, InfoIcon, PencilIcon, RefreshIcon, TrashIcon } from "@/components/Icons";
import { useToast } from "@/components/Toast";
import { ApiError, chatApi, isChatActive, type Chat, type ChatMessage } from "@/lib/api";
import { formatBytes, formatClock } from "@/lib/format";
import { errorMessage, useI18n, type MessageKey } from "@/lib/i18n";
import { languageName, useSystem } from "@/lib/useSystem";

type Load = { kind: "loading" } | { kind: "missing" } | { kind: "error" } | { kind: "ready"; chat: Chat };
const KIND_ICON: Record<string, string> = { voice: "🎤", audio: "🎵", video: "🎬", image: "🖼", sticker: "🏷", document: "📄" };

function MessageBody({ chat, m, onSaved }: { chat: Chat; m: ChatMessage; onSaved: (m: ChatMessage) => void }) {
  const { t, locale } = useI18n();
  const toast = useToast();
  const [editing, setEditing] = useState(false);
  const isAudio = m.kind === "voice" || m.kind === "audio" || m.kind === "video";
  const isImage = m.kind === "image" || m.kind === "sticker";
  const [draft, setDraft] = useState(isAudio ? (m.transcript ?? "") : (m.image_description ?? ""));
  const [saving, setSaving] = useState(false);

  const save = async () => {
    setSaving(true);
    try {
      const updated = await chatApi.editMessage(chat.id, m.idx, isAudio ? { transcript: draft } : { image_description: draft });
      onSaved(updated);
      setEditing(false);
      toast(t("chat.saved"));
    } catch (e) {
      toast(e instanceof ApiError ? errorMessage(t, e) : t("common.error"), "error");
    } finally {
      setSaving(false);
    }
  };

  if (m.kind === "text") return <p className="msg-text">{m.text}</p>;
  if (m.kind === "omitted" || m.kind === "deleted") return <p className="msg-note">{t(`chat.kind.${m.kind}` as MessageKey)}</p>;
  if (m.kind === "document") return <p className="msg-note">📄 {m.attachment}{m.text ? ` – ${m.text}` : ""}</p>;

  const label = `${KIND_ICON[m.kind] ?? ""} ${t(`chat.kind.${m.kind}` as MessageKey)}`;
  return (
    <div className="msg-media">
      <div className="msg-media-head">
        <span className="msg-kind">{label}</span>
        {m.duration_seconds ? <span className="hint tabular">{formatClock(m.duration_seconds)}</span> : null}
        {m.transcript_language && m.transcript_language !== chat.stats?.main_language && (
          <span className="badge">{t("chat.lang", { lang: languageName(m.transcript_language, locale) })}</span>
        )}
      </div>
      {!m.has_media ? (
        <p className="msg-note">{m.attachment} – {t("chat.missingFile")}</p>
      ) : isAudio ? (
        m.kind === "video" ? (
          <video className="msg-video" src={chatApi.mediaUrl(chat.id, m.idx)} controls preload="none" />
        ) : (
          <audio className="msg-audio" src={chatApi.mediaUrl(chat.id, m.idx)} controls preload="none" />
        )
      ) : isImage ? (
        // eslint-disable-next-line @next/next/no-img-element
        <img className="msg-image" src={chatApi.mediaUrl(chat.id, m.idx)} alt={m.image_description ?? m.attachment ?? ""} loading="lazy" />
      ) : null}

      {isAudio && m.has_media && !editing && (
        m.item_status === "done" ? (
          <p className="msg-transcript">{m.transcript}</p>
        ) : (
          <p className={`msg-note${m.item_status === "failed" ? " is-error" : ""}`}>
            {m.item_status === "failed" ? `${t("chat.item.failed")}${m.item_error ? ` (${errorMessage(t, { code: m.item_error, message: m.item_error })})` : ""}`
              : m.item_status === "skipped" ? t("chat.item.skipped") : t("chat.item.pending")}
          </p>
        )
      )}
      {isImage && m.image_text && <p className="msg-note"><strong>{t("chat.ocr")}:</strong> {m.image_text}</p>}
      {isImage && m.image_description && !editing && <p className="msg-transcript"><strong>{t("chat.describe")}:</strong> {m.image_description}</p>}
      {m.text && <p className="msg-note"><strong>{t("chat.caption")}:</strong> {m.text}</p>}

      {editing ? (
        <div className="msg-edit">
          <label className="sr-only" htmlFor={`edit-${m.idx}`}>{isAudio ? t("chat.edit") : t("chat.describe")}</label>
          <textarea id={`edit-${m.idx}`} className="input msg-textarea" value={draft} rows={3}
            placeholder={isImage ? t("chat.describePlaceholder") : undefined} onChange={(e) => setDraft(e.target.value)} />
          <div className="msg-edit-actions">
            <button type="button" className="btn btn-sm" onClick={() => setEditing(false)}>{t("lib.cancel")}</button>
            <button type="button" className="btn btn-sm btn-primary" onClick={save} disabled={saving}>{t("chat.save")}</button>
          </div>
        </div>
      ) : (m.has_media && (isImage || m.item_status === "done" || m.item_status === "failed")) ? (
        <button type="button" className="link-button msg-edit-link" onClick={() => setEditing(true)}>
          {isImage && !m.image_description ? t("chat.describePlaceholder") : t("chat.edit")}
        </button>
      ) : null}
    </div>
  );
}

export function ChatWorkspace() {
  const id = useSearchParams().get("id") ?? "";
  const router = useRouter();
  const { t, locale } = useI18n();
  const toast = useToast();
  const { state: system } = useSystem();
  const [load, setLoad] = useState<Load>({ kind: "loading" });
  const [view, setView] = useState<"block" | "messages">("block");
  const [block, setBlock] = useState<string>("");
  const [renaming, setRenaming] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [exportOpen, setExportOpen] = useState(false);
  const exportRef = useRef<HTMLDivElement>(null);

  const fetchChat = useCallback(async () => {
    try {
      const chat = await chatApi.get(id);
      setLoad({ kind: "ready", chat });
    } catch (e) {
      setLoad((prev) => (e instanceof ApiError && e.status === 404 ? { kind: "missing" } : prev.kind === "ready" ? prev : { kind: "error" }));
    }
  }, [id]);

  useEffect(() => {
    void fetchChat();
  }, [fetchChat]);

  const chat = load.kind === "ready" ? load.chat : null;
  const active = chat ? isChatActive(chat.status) : false;
  useEffect(() => {
    if (!active) return;
    const handle = window.setInterval(fetchChat, 2000);
    return () => window.clearInterval(handle);
  }, [active, fetchChat]);

  // Text block in the UI language; refreshed whenever the chat changes.
  const version = chat ? `${chat.updated_at}-${chat.done_items}-${chat.status}` : "";
  useEffect(() => {
    if (!chat) return;
    let cancelled = false;
    chatApi.exportText(chat.id, locale).then((text) => !cancelled && setBlock(text)).catch(() => {});
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [version, locale]);

  useEffect(() => {
    if (chat) document.title = `${chat.title} · Verba`;
  }, [chat]);

  useEffect(() => {
    if (!exportOpen) return;
    const close = (e: MouseEvent) => !exportRef.current?.contains(e.target as Node) && setExportOpen(false);
    document.addEventListener("mousedown", close);
    return () => document.removeEventListener("mousedown", close);
  }, [exportOpen]);

  const days = useMemo(() => {
    const groups: { day: string; messages: ChatMessage[] }[] = [];
    for (const m of chat?.messages ?? []) {
      const day = new Intl.DateTimeFormat(locale, { weekday: "long", day: "numeric", month: "long", year: "numeric" }).format(new Date(m.ts));
      if (!groups.length || groups[groups.length - 1].day !== day) groups.push({ day, messages: [] });
      groups[groups.length - 1].messages.push(m);
    }
    return groups;
  }, [chat?.messages, locale]);

  const replaceMessage = (m: ChatMessage) =>
    setLoad((prev) => prev.kind === "ready"
      ? { kind: "ready", chat: { ...prev.chat, updated_at: new Date().toISOString(), messages: prev.chat.messages.map((x) => (x.idx === m.idx ? m : x)) } }
      : prev);

  const act = async (fn: () => Promise<unknown>) => {
    try {
      await fn();
      await fetchChat();
    } catch (e) {
      toast(e instanceof ApiError ? errorMessage(t, e) : t("common.error"), "error");
    }
  };

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(block);
      toast(t("chat.copied"));
    } catch {
      toast(t("ws.copyFailed"), "error");
    }
  };

  const download = (format: string) => {
    setExportOpen(false);
    const a = document.createElement("a");
    a.href = chatApi.exportUrl(id, format, locale);
    document.body.appendChild(a);
    a.click();
    a.remove();
  };

  const s = chat?.stats;
  const pct = chat && chat.total_items ? Math.round((chat.done_items / chat.total_items) * 100) : 0;
  const retryLanguage = chat?.language_requested ?? "auto";
  const retryProvider = chat?.provider ?? "auto";

  return (
    <>
      <AppHeader state={system} />
      <main id="main" className="container workspace chat-workspace">
        <Link href="/app" className="back-link"><ArrowLeftIcon size={16} /> {t("ws.back")}</Link>

        {load.kind === "loading" && <div className="skeleton" style={{ height: 240 }} aria-busy="true" />}
        {load.kind === "missing" && (
          <div className="empty"><h1 className="empty-title">{t("chat.notFound")}</h1><Link href="/app" className="btn btn-primary">{t("ws.back")}</Link></div>
        )}
        {load.kind === "error" && (
          <div className="alert alert-danger" role="alert">
            <span className="alert-icon"><AlertIcon size={16} /></span>
            <span>{t("ws.loadFailed")}</span>
            <button type="button" className="btn btn-sm" onClick={fetchChat}>{t("common.retry")}</button>
          </div>
        )}

        {chat && (
          <>
            <header className="ws-head">
              <div className="ws-title-row">
                <h1 className="ws-title" data-testid="chat-title">💬 {chat.title}</h1>
                <button type="button" className="btn btn-ghost btn-icon btn-sm" onClick={() => setRenaming(true)} aria-label={t("ws.rename")}>
                  <PencilIcon size={16} />
                </button>
                <span className="ws-badges">
                  {chat.is_mock && <MockBadge />}
                  <StatusBadge status={chat.status} />
                </span>
              </div>
              {s && (
                <dl className="ws-meta">
                  {chat.participants.length > 0 && <div><dt>{t("chat.participants")}</dt><dd>{chat.participants.join(", ")}</dd></div>}
                  {s.first && s.last && (
                    <div><dt>{t("chat.period")}</dt><dd>
                      {new Intl.DateTimeFormat(locale, { dateStyle: "medium" }).format(new Date(s.first))} – {new Intl.DateTimeFormat(locale, { dateStyle: "medium" }).format(new Date(s.last))}
                    </dd></div>
                  )}
                  <div><dt>{t("chat.viewMessages")}</dt><dd className="tabular">
                    {t("chat.nMessages", { n: s.messages })} · {t("chat.nVoice", { n: s.voice_notes })} · {t("chat.nImages", { n: s.images })}
                  </dd></div>
                  {s.main_language && <div><dt>{t("chat.mainLanguage")}</dt><dd>{languageName(s.main_language, locale)}</dd></div>}
                  <div><dt>{t("meta.size")}</dt><dd className="tabular">{formatBytes(chat.size_bytes, locale)}</dd></div>
                </dl>
              )}
            </header>

            {chat.is_mock && (
              <div className="alert alert-warning" role="note" data-testid="mock-banner">
                <span className="alert-icon"><AlertIcon size={16} /></span>
                <span><strong>{t("ws.mockTitle")}.</strong> {t("ws.mockBody")}</span>
              </div>
            )}

            {active && (
              <section className="card card-pad job-panel" aria-live="polite" data-testid="chat-progress">
                <strong>{chat.status === "pending" ? t("chat.queued") : t("chat.progress", { done: chat.done_items, total: chat.total_items })}</strong>
                <div className={`progress${chat.status === "pending" ? " progress-indeterminate" : ""}`} role="progressbar"
                  aria-valuemin={0} aria-valuemax={100} aria-valuenow={pct}>
                  <span style={chat.status === "pending" ? undefined : { width: `${pct}%` }} />
                </div>
                <div className="job-foot">
                  <span className="hint">{t("job.background")}</span>
                  <button type="button" className="btn btn-sm" disabled={chat.cancel_requested} onClick={() => act(() => chatApi.cancel(chat.id))}>
                    {chat.cancel_requested ? t("job.cancelling") : t("job.cancel")}
                  </button>
                </div>
              </section>
            )}

            {(chat.status === "failed" || chat.status === "cancelled") && (
              <div className={`alert ${chat.status === "failed" ? "alert-danger" : ""}`} role="alert" data-testid="chat-error">
                <span className="alert-icon"><AlertIcon size={16} /></span>
                <span>
                  <strong>{chat.status === "failed" ? t("chat.failedTitle") : t("chat.cancelledTitle")}.</strong>{" "}
                  {errorMessage(t, chat.error)}
                </span>
                <button type="button" className="btn btn-sm" onClick={() => act(() => chatApi.retry(chat.id, retryProvider, retryLanguage))}>
                  {t("job.retry")}
                </button>
              </div>
            )}

            {chat.status === "completed" && chat.total_items === 0 && (
              <p className="alert alert-info"><InfoIcon size={16} /> {t("chat.noAudio")}</p>
            )}

            <div className="editor-toolbar">
              <div className="segmented" role="tablist" aria-label={t("chat.viewBlock")}>
                <button type="button" role="tab" aria-selected={view === "block"} className={view === "block" ? "is-active" : ""}
                  onClick={() => setView("block")}>{t("chat.viewBlock")}</button>
                <button type="button" role="tab" aria-selected={view === "messages"} className={view === "messages" ? "is-active" : ""}
                  onClick={() => setView("messages")} data-testid="view-messages">{t("chat.viewMessages")}</button>
              </div>
              <div className="editor-actions">
                {!active && s && s.failed > 0 && (
                  <button type="button" className="btn btn-sm" onClick={() => act(() => chatApi.retry(chat.id, retryProvider, retryLanguage))}>
                    <RefreshIcon size={15} /> {t("chat.retryFailed")}
                  </button>
                )}
                <button type="button" className="btn btn-sm" onClick={copy} data-testid="chat-copy"><CopyIcon size={15} /> <span className="hide-sm">{t("chat.copyAll")}</span></button>
                <div className="export" ref={exportRef}>
                  <button type="button" className="btn btn-primary btn-sm" aria-haspopup="menu" aria-expanded={exportOpen}
                    onClick={() => setExportOpen((o) => !o)} data-testid="chat-export"><DownloadIcon size={15} /> {t("ws.download")}</button>
                  {exportOpen && (
                    <div className="menu menu-right" role="menu">
                      {(["txt", "md", "docx", "json"] as const).map((f) => (
                        <button key={f} type="button" role="menuitem" className="menu-item" data-format={f} onClick={() => download(f)}>
                          <span>{t(`chat.dl.${f}` as MessageKey)}</span><small>{f.toUpperCase()}</small>
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            </div>

            {view === "block" ? (
              <pre className="chat-block" data-testid="chat-block">{block}</pre>
            ) : (
              <div className="chat-messages" data-testid="chat-messages">
                {days.map((d) => (
                  <section key={d.day} className="chat-day">
                    <h2 className="chat-day-title">{d.day}</h2>
                    <ol className="chat-list">
                      {d.messages.map((m) => (
                        m.kind === "system" ? (
                          <li key={m.idx} className="msg msg-system">{m.text}</li>
                        ) : (
                          <li key={m.idx} className="msg" data-kind={m.kind}>
                            <div className="msg-head">
                              <span className="msg-sender">{m.sender}</span>
                              <time className="hint tabular" dateTime={m.ts}>{new Intl.DateTimeFormat(locale, { timeStyle: "short" }).format(new Date(m.ts))}</time>
                            </div>
                            <MessageBody chat={chat} m={m} onSaved={replaceMessage} />
                          </li>
                        )
                      ))}
                    </ol>
                  </section>
                ))}
              </div>
            )}

            {s && s.images > s.images_described && <p className="hint"><InfoIcon size={14} /> {t("chat.claudeHint")}</p>}

            {!active && chat.total_items > 0 && (
              <details className="card card-pad ws-again">
                <summary>{t("chat.redoAll")}</summary>
                <button type="button" className="btn" onClick={() => act(() => chatApi.retry(chat.id, retryProvider, retryLanguage, true))}>
                  <RefreshIcon size={15} /> {t("chat.redoAll")}
                </button>
              </details>
            )}

            <div>
              <button type="button" className="btn btn-sm btn-danger" onClick={() => setDeleting(true)} disabled={chat.status === "processing"}>
                <TrashIcon size={15} /> {t("lib.delete")}
              </button>
            </div>

            {renaming && (
              <RenameDialog initial={chat.title} onClose={() => setRenaming(false)}
                onSave={async (title) => { await act(() => chatApi.rename(chat.id, title)); setRenaming(false); }} />
            )}
            {deleting && (
              <ConfirmDialog title={t("chat.deleteTitle")} body={t("chat.deleteBody", { title: chat.title })} confirmLabel={t("lib.deleteConfirm")}
                danger onClose={() => setDeleting(false)}
                onConfirm={async () => {
                  try {
                    await chatApi.remove(chat.id);
                    toast(t("chat.deleted"));
                    router.push("/app");
                  } catch (e) {
                    toast(e instanceof ApiError ? errorMessage(t, e) : t("common.error"), "error");
                  }
                }} />
            )}
          </>
        )}
      </main>
    </>
  );
}
