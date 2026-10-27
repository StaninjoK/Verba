"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { AppHeader } from "@/components/app/AppHeader";
import { RenameDialog } from "@/components/app/Dialog";
import { JobPanel } from "@/components/app/JobPanel";
import { MockBadge, StatusBadge } from "@/components/app/StatusBadge";
import { TranscribeOptions } from "@/components/app/TranscribeOptions";
import { TranscriptEditor } from "@/components/app/TranscriptEditor";
import { AlertIcon, ArrowLeftIcon, PencilIcon } from "@/components/Icons";
import { useToast } from "@/components/Toast";
import { api, ApiError, isActive, type Project } from "@/lib/api";
import { formatBytes, formatDuration } from "@/lib/format";
import { errorMessage, useI18n, type MessageKey } from "@/lib/i18n";
import { languageName, useSystem } from "@/lib/useSystem";
import "../../../app.css";

type LoadState = { kind: "loading" } | { kind: "missing" } | { kind: "error" } | { kind: "ready"; project: Project };

export default function WorkspacePage() {
  const params = useParams<{ id: string }>();
  const id = params.id;
  const { t, locale } = useI18n();
  const toast = useToast();
  const { state: system } = useSystem();
  const [load, setLoad] = useState<LoadState>({ kind: "loading" });
  const [renaming, setRenaming] = useState(false);

  const fetchProject = useCallback(async () => {
    try {
      const project = await api.getProject(id);
      setLoad({ kind: "ready", project });
    } catch (e) {
      setLoad((prev) =>
        e instanceof ApiError && e.status === 404 ? { kind: "missing" } : prev.kind === "ready" ? prev : { kind: "error" },
      );
    }
  }, [id]);

  useEffect(() => {
    void fetchProject();
  }, [fetchProject]);

  const project = load.kind === "ready" ? load.project : null;
  const active = project ? isActive(project.status) : false;

  useEffect(() => {
    if (!active) return;
    const handle = window.setInterval(fetchProject, 1000);
    return () => window.clearInterval(handle);
  }, [active, fetchProject]);

  useEffect(() => {
    if (project) document.title = `${project.title} · Verba`;
  }, [project]);

  const rename = async (title: string) => {
    try {
      const updated = await api.rename(id, title);
      setLoad((prev) => (prev.kind === "ready" ? { kind: "ready", project: { ...prev.project, title: updated.title } } : prev));
      setRenaming(false);
      toast(t("lib.renamed"));
    } catch (e) {
      toast(e instanceof ApiError ? errorMessage(t, e) : t("common.error"), "error");
    }
  };

  const info = system.kind === "ready" ? system.info : null;
  const job = project?.job ?? null;

  return (
    <>
      <AppHeader state={system} />
      <main id="main" className="container workspace">
        <Link href="/app" className="back-link"><ArrowLeftIcon size={16} /> {t("ws.back")}</Link>

        {load.kind === "loading" && (
          <div aria-busy="true" className="ws-skeleton">
            <div className="skeleton" style={{ height: 36, width: "45%" }} />
            <div className="skeleton" style={{ height: 18, width: "70%" }} />
            <div className="skeleton" style={{ height: 240 }} />
          </div>
        )}
        {load.kind === "missing" && (
          <div className="empty">
            <h1 className="empty-title">{t("ws.notFound")}</h1>
            <Link href="/app" className="btn btn-primary">{t("ws.back")}</Link>
          </div>
        )}
        {load.kind === "error" && (
          <div className="alert alert-danger" role="alert">
            <span className="alert-icon"><AlertIcon size={16} /></span>
            <span>{t("ws.loadFailed")} {t("engine.offlineHelp")}</span>
            <button type="button" className="btn btn-sm" onClick={fetchProject}>{t("common.retry")}</button>
          </div>
        )}

        {project && (
          <>
            <header className="ws-head">
              <div className="ws-title-row">
                <h1 className="ws-title" data-testid="project-title">{project.title}</h1>
                <button type="button" className="btn btn-ghost btn-icon btn-sm" onClick={() => setRenaming(true)} aria-label={t("ws.rename")}
                  title={t("ws.rename")}>
                  <PencilIcon size={16} />
                </button>
                <span className="ws-badges">
                  {project.is_mock && project.has_transcript && <MockBadge />}
                  {project.transcript_edited && <span className="badge">{t("ws.edited")}</span>}
                  <StatusBadge status={project.status} />
                </span>
              </div>
              <dl className="ws-meta">
                <div><dt>{t("meta.duration")}</dt><dd className="tabular">{formatDuration(project.duration_seconds)}</dd></div>
                <div><dt>{t("meta.size")}</dt><dd className="tabular">{formatBytes(project.size_bytes, locale)}</dd></div>
                <div><dt>{t("meta.type")}</dt><dd>{project.has_video ? t("meta.video") : t("meta.audio")} · {project.container.toUpperCase()}</dd></div>
                {project.language_detected && (
                  <div><dt>{t("meta.language")}</dt><dd>{languageName(project.language_detected, locale)}</dd></div>
                )}
                {project.provider && (
                  <div><dt>{t("meta.engine")}</dt><dd>{t(`provider.${project.provider}` as MessageKey)}{project.model && !project.is_mock ? ` · ${project.model}` : ""}</dd></div>
                )}
                {project.has_transcript && (
                  <div><dt>{t("meta.transcript")}</dt><dd className="tabular">{t("meta.words", { n: project.word_count.toLocaleString(locale) })}</dd></div>
                )}
                <div><dt>{t("meta.created")}</dt><dd>{new Intl.DateTimeFormat(locale, { dateStyle: "medium", timeStyle: "short" }).format(new Date(project.created_at))}</dd></div>
              </dl>
            </header>

            {project.is_mock && project.has_transcript && (
              <div className="alert alert-warning mock-banner" role="note" data-testid="mock-banner">
                <span className="alert-icon"><AlertIcon size={16} /></span>
                <span><strong>{t("ws.mockTitle")}.</strong> {t("ws.mockBody")}</span>
              </div>
            )}

            {job && active && <JobPanel job={job} onChanged={fetchProject} />}

            {job && (job.status === "failed" || job.status === "cancelled") && (
              <section className="card card-pad ws-retry" data-testid="job-error">
                <div className={`alert ${job.status === "failed" ? "alert-danger" : ""}`} role={job.status === "failed" ? "alert" : undefined}>
                  <span className="alert-icon"><AlertIcon size={16} /></span>
                  <span>
                    <strong>{job.status === "failed" ? t("job.failedTitle") : t("job.cancelledTitle")}.</strong>{" "}
                    {errorMessage(t, job.error)}
                  </span>
                </div>
                {info && <TranscribeOptions projectId={project.id} system={info} restart onStarted={fetchProject} />}
              </section>
            )}

            {!job && !project.has_transcript && info && (
              <section className="card card-pad">
                <TranscribeOptions projectId={project.id} system={info} onStarted={fetchProject} />
              </section>
            )}

            {project.has_transcript && !active && (
              <TranscriptEditor key={`${project.id}-${job?.id ?? "none"}`} project={project} />
            )}

            {project.has_transcript && job?.status === "completed" && info && (
              <details className="card card-pad ws-again">
                <summary>{t("opts.restart")}</summary>
                <TranscribeOptions projectId={project.id} system={info} restart onStarted={fetchProject} />
              </details>
            )}

            {renaming && <RenameDialog initial={project.title} onSave={rename} onClose={() => setRenaming(false)} />}
          </>
        )}
      </main>
    </>
  );
}
