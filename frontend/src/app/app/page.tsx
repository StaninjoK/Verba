"use client";

import { useState } from "react";
import { AppHeader } from "@/components/app/AppHeader";
import { ChatImportPanel } from "@/components/app/ChatImportPanel";
import { ChatList } from "@/components/app/ChatList";
import { ProjectLibrary } from "@/components/app/ProjectLibrary";
import { UploadPanel } from "@/components/app/UploadPanel";
import { WhisperSetupCard } from "@/components/app/WhisperSetupCard";
import { AlertIcon, ShieldIcon } from "@/components/Icons";
import { formatBytes } from "@/lib/format";
import { useI18n } from "@/lib/i18n";
import { useSystem } from "@/lib/useSystem";
import "../app.css";

export default function Dashboard() {
  const { t, locale } = useI18n();
  const { state, refresh } = useSystem();
  const [refreshKey, setRefreshKey] = useState(0);
  const [tab, setTab] = useState<"media" | "chat">("media");
  const info = state.kind === "ready" ? state.info : null;
  const noRealEngine = info && !info.real_engine_available;

  return (
    <>
      <AppHeader state={state} />
      <main id="main" className="container dashboard">
        <div className="dash-intro">
          <h1>{t("dash.title")}</h1>
          <p className="muted">{t("dash.subtitle")}</p>
        </div>

        {state.kind === "offline" && (
          <div className="alert alert-danger" role="alert">
            <span className="alert-icon"><AlertIcon size={16} /></span>
            <span><strong>{t("engine.offline")}.</strong> {t("engine.offlineHelp")}</span>
            <button type="button" className="btn btn-sm" onClick={refresh}>{t("common.retry")}</button>
          </div>
        )}
        {noRealEngine && <WhisperSetupCard onReady={refresh} />}

        <div className="dash-grid">
          <div className="dash-main">
            <div className="segmented dash-tabs" role="tablist" aria-label={t("dash.title")}>
              <button type="button" role="tab" aria-selected={tab === "media"} className={tab === "media" ? "is-active" : ""}
                onClick={() => setTab("media")}>{t("dash.tabMedia")}</button>
              <button type="button" role="tab" aria-selected={tab === "chat"} className={tab === "chat" ? "is-active" : ""}
                onClick={() => setTab("chat")} data-testid="tab-chat">💬 {t("dash.tabChat")}</button>
            </div>
            {tab === "media" ? (
              <UploadPanel system={info} onUploaded={() => setRefreshKey((n) => n + 1)} />
            ) : (
              <ChatImportPanel system={info} />
            )}
            <ChatList refreshKey={refreshKey} />
            <ProjectLibrary refreshKey={refreshKey} />
          </div>
          <aside className="dash-side">
            <section className="card card-pad privacy-card" aria-labelledby="privacy-title">
              <div className="privacy-icon"><ShieldIcon size={18} /></div>
              <h2 id="privacy-title">{t("privacy.title")}</h2>
              <p className="muted">{t("privacy.body")}</p>
              {info && (
                <>
                  <hr className="divider" />
                  <div className="privacy-row">
                    <span className="hint">{t("privacy.location")}</span>
                    <code className="path" title={info.storage.data_dir}>{info.storage.data_dir}</code>
                  </div>
                  <div className="privacy-row">
                    <div className="progress" aria-hidden="true">
                      <span style={{ width: `${Math.min(100, (info.storage.used_bytes / info.limits.max_storage_bytes) * 100)}%` }} />
                    </div>
                    <span className="hint tabular">
                      {t("dash.storage", {
                        used: formatBytes(info.storage.used_bytes, locale),
                        max: formatBytes(info.limits.max_storage_bytes, locale),
                      })}
                    </span>
                  </div>
                </>
              )}
              <p className="hint">{t("privacy.delete")}</p>
            </section>
          </aside>
        </div>
      </main>
    </>
  );
}
