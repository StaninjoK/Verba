"use client";

import { useEffect, useState } from "react";
import { ApiError, setupApi, type WhisperSetupStatus } from "@/lib/api";
import { errorMessage, useI18n, type MessageKey } from "@/lib/i18n";
import { AlertIcon, CheckIcon, CpuIcon } from "../Icons";

/** One-click installation of local Whisper, shown while no real engine is available. */
export function WhisperSetupCard({ onReady }: { onReady: () => void }) {
  const { t } = useI18n();
  const [status, setStatus] = useState<WhisperSetupStatus | null>(null);
  const [model, setModel] = useState("small");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setupApi.status().then(setStatus).catch(() => {});
  }, []);

  const running = status?.status === "running";
  useEffect(() => {
    if (!running) return;
    const id = window.setInterval(async () => {
      try {
        const s = await setupApi.status();
        setStatus(s);
        if (s.status === "done") onReady();
      } catch {
        // backend restarting – keep polling
      }
    }, 2000);
    return () => window.clearInterval(id);
  }, [running, onReady]);

  const start = async () => {
    setError(null);
    try {
      setStatus(await setupApi.start(model));
    } catch (e) {
      setError(e instanceof ApiError ? errorMessage(t, e) : t("common.error"));
    }
  };

  const sizes = status?.models ?? { base: 145, small: 465, medium: 1500 };
  const mb = (sizes[model] ?? 0) + (status?.installed ? 0 : (status?.packages_mb ?? 450));

  return (
    <section id="setup" className="card card-pad setup-card" aria-labelledby="setup-title" data-testid="whisper-setup">
      <div className="setup-head">
        <div className="setup-icon"><CpuIcon size={20} /></div>
        <div>
          <h2 id="setup-title">{t("setup.title")}</h2>
          <p className="muted">{t("setup.body")}</p>
        </div>
      </div>

      {status?.status === "done" ? (
        <p className="alert alert-info" role="status"><CheckIcon size={16} /> {t("setup.done")}</p>
      ) : running ? (
        <div className="setup-progress" aria-live="polite">
          <strong>{t(`setup.step.${status?.step ?? "packages"}` as MessageKey)}</strong>
          <div className="progress progress-indeterminate"><span /></div>
          <span className="hint">{t("setup.duration")}</span>
        </div>
      ) : (
        <>
          <div className="setup-row">
            <div className="setup-model">
              <label className="label" htmlFor="setup-model">{t("setup.model")}</label>
              <select id="setup-model" className="select" value={model} onChange={(e) => setModel(e.target.value)}>
                {(["base", "small", "medium"] as const).map((m) => (
                  <option key={m} value={m}>{t(`setup.model.${m}` as MessageKey)}</option>
                ))}
              </select>
            </div>
            <button type="button" className="btn btn-primary btn-lg" onClick={start} data-testid="setup-start">
              {t("setup.start")}
            </button>
          </div>
          <p className="hint">{t("setup.size", { mb: mb.toLocaleString() })}</p>
          {(status?.status === "failed" || error) && (
            <div className="alert alert-danger" role="alert">
              <span className="alert-icon"><AlertIcon size={16} /></span>
              <span><strong>{t("setup.failed")}.</strong> <code className="setup-error">{error ?? status?.error}</code></span>
            </div>
          )}
        </>
      )}
    </section>
  );
}
