"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { api, ApiError, isActive, type ProjectSummary } from "@/lib/api";
import { formatDuration } from "@/lib/format";
import { errorMessage, useI18n } from "@/lib/i18n";
import { languageName } from "@/lib/useSystem";
import { DotsIcon, FileAudioIcon, FileVideoIcon, PencilIcon, SearchIcon, TrashIcon } from "../Icons";
import { useToast } from "../Toast";
import { ConfirmDialog, RenameDialog } from "./Dialog";
import { MockBadge, StatusBadge } from "./StatusBadge";

function relativeDate(iso: string, locale: string): string {
  const date = new Date(iso);
  const diff = (Date.now() - date.getTime()) / 1000;
  const rtf = new Intl.RelativeTimeFormat(locale, { numeric: "auto" });
  if (diff < 60) return rtf.format(0, "minute");
  if (diff < 3600) return rtf.format(-Math.floor(diff / 60), "minute");
  if (diff < 86400) return rtf.format(-Math.floor(diff / 3600), "hour");
  if (diff < 86400 * 7) return rtf.format(-Math.floor(diff / 86400), "day");
  return new Intl.DateTimeFormat(locale, { dateStyle: "medium" }).format(date);
}

function RowMenu({ project, onRename, onDelete }: { project: ProjectSummary; onRename: () => void; onDelete: () => void }) {
  const { t } = useI18n();
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!open) return;
    const close = (e: MouseEvent) => {
      if (!ref.current?.contains(e.target as Node)) setOpen(false);
    };
    const esc = (e: KeyboardEvent) => e.key === "Escape" && setOpen(false);
    document.addEventListener("mousedown", close);
    document.addEventListener("keydown", esc);
    return () => {
      document.removeEventListener("mousedown", close);
      document.removeEventListener("keydown", esc);
    };
  }, [open]);
  return (
    <div className="row-menu" ref={ref}>
      <button type="button" className="btn btn-ghost btn-icon btn-sm" aria-haspopup="menu" aria-expanded={open}
        aria-label={t("lib.actions", { title: project.title })} onClick={() => setOpen((o) => !o)}>
        <DotsIcon />
      </button>
      {open && (
        <div className="menu menu-right" role="menu">
          <button type="button" role="menuitem" className="menu-item" onClick={() => { setOpen(false); onRename(); }}>
            <span><PencilIcon size={15} /> {t("lib.rename")}</span>
          </button>
          <button type="button" role="menuitem" className="menu-item menu-danger" onClick={() => { setOpen(false); onDelete(); }}>
            <span><TrashIcon size={15} /> {t("lib.delete")}</span>
          </button>
        </div>
      )}
    </div>
  );
}

export function ProjectLibrary({ refreshKey }: { refreshKey: number }) {
  const { t, locale } = useI18n();
  const toast = useToast();
  const [query, setQuery] = useState("");
  const [projects, setProjects] = useState<ProjectSummary[] | null>(null);
  const [error, setError] = useState(false);
  const [renaming, setRenaming] = useState<ProjectSummary | null>(null);
  const [deleting, setDeleting] = useState<ProjectSummary | null>(null);
  const [busyDelete, setBusyDelete] = useState(false);
  const [reload, setReload] = useState(0);

  useEffect(() => {
    let cancelled = false;
    const handle = window.setTimeout(async () => {
      try {
        const list = await api.listProjects(query.trim() || undefined);
        if (!cancelled) {
          setProjects(list);
          setError(false);
        }
      } catch {
        if (!cancelled) setError(true);
      }
    }, query ? 220 : 0);
    return () => {
      cancelled = true;
      window.clearTimeout(handle);
    };
  }, [query, refreshKey, reload]);

  // Keep statuses fresh while any job is running.
  const anyActive = projects?.some((p) => isActive(p.status)) ?? false;
  useEffect(() => {
    if (!anyActive) return;
    const id = window.setInterval(() => setReload((n) => n + 1), 2000);
    return () => window.clearInterval(id);
  }, [anyActive]);

  const doRename = async (title: string) => {
    if (!renaming) return;
    try {
      await api.rename(renaming.id, title);
      toast(t("lib.renamed"));
      setRenaming(null);
      setReload((n) => n + 1);
    } catch (e) {
      toast(e instanceof ApiError ? errorMessage(t, e) : t("common.error"), "error");
    }
  };

  const doDelete = async () => {
    if (!deleting) return;
    setBusyDelete(true);
    try {
      await api.remove(deleting.id);
      toast(t("lib.deleted"));
      setDeleting(null);
      setReload((n) => n + 1);
    } catch (e) {
      toast(e instanceof ApiError ? errorMessage(t, e) : t("common.error"), "error");
    } finally {
      setBusyDelete(false);
    }
  };

  return (
    <section className="library" aria-labelledby="library-title">
      <div className="library-head">
        <h2 id="library-title">{t("dash.libraryTitle")}</h2>
        <div className="search">
          <SearchIcon size={16} />
          <label htmlFor="library-search" className="sr-only">{t("dash.search")}</label>
          <input id="library-search" className="input" type="search" placeholder={t("dash.search")} value={query}
            onChange={(e) => setQuery(e.target.value)} maxLength={200} />
        </div>
      </div>

      {error && projects === null ? (
        <div className="alert alert-danger" role="alert">
          <span>{t("engine.offlineHelp")}</span>
          <button type="button" className="btn btn-sm" onClick={() => setReload((n) => n + 1)}>{t("common.retry")}</button>
        </div>
      ) : projects === null ? (
        <div className="project-list" aria-busy="true">
          {[0, 1, 2].map((i) => <div key={i} className="skeleton" style={{ height: 68 }} />)}
        </div>
      ) : projects.length === 0 ? (
        query ? (
          <p className="empty-inline muted">{t("dash.noResults", { q: query })}</p>
        ) : (
          <div className="empty">
            <div className="empty-art" aria-hidden="true">
              {Array.from({ length: 18 }).map((_, i) => <span key={i} style={{ height: `${20 + ((i * 37) % 60)}%` }} />)}
            </div>
            <h3>{t("dash.emptyTitle")}</h3>
            <p className="muted">{t("dash.emptyBody")}</p>
          </div>
        )
      ) : (
        <ul className="project-list" data-testid="project-list">
          {projects.map((p) => {
            const Icon = p.has_video ? FileVideoIcon : FileAudioIcon;
            return (
              <li key={p.id} className="project-row" data-testid="project-row">
                <Link href={`/app/project?id=${p.id}`} className="project-link">
                  <span className="file-icon"><Icon size={18} /></span>
                  <span className="project-main">
                    <span className="project-title">{p.title}</span>
                    <span className="project-meta hint">
                      <span className="tabular">{formatDuration(p.duration_seconds)}</span>
                      <span aria-hidden="true">·</span>
                      <span>{relativeDate(p.updated_at, locale)}</span>
                      {p.language_detected && (
                        <>
                          <span aria-hidden="true">·</span>
                          <span>{languageName(p.language_detected, locale)}</span>
                        </>
                      )}
                    </span>
                    {p.preview && <span className="project-preview">{p.preview}</span>}
                  </span>
                  <span className="project-badges">
                    {p.is_mock && p.has_transcript && <MockBadge />}
                    <StatusBadge status={p.status} />
                  </span>
                </Link>
                <RowMenu project={p} onRename={() => setRenaming(p)} onDelete={() => setDeleting(p)} />
              </li>
            );
          })}
        </ul>
      )}

      {renaming && <RenameDialog initial={renaming.title} onSave={doRename} onClose={() => setRenaming(null)} />}
      {deleting && (
        <ConfirmDialog
          title={t("lib.deleteTitle")}
          body={t("lib.deleteBody", { title: deleting.title })}
          confirmLabel={t("lib.deleteConfirm")}
          danger
          busy={busyDelete}
          onConfirm={doDelete}
          onClose={() => setDeleting(null)}
        />
      )}
    </section>
  );
}
