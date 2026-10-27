"use client";

import { useMemo, useState } from "react";
import { ApiError, api, type Job, type SystemInfo } from "@/lib/api";
import { errorMessage, useI18n, type MessageKey } from "@/lib/i18n";
import { languageName } from "@/lib/useSystem";
import { InfoIcon } from "../Icons";

/** Language + engine choice and the start button. Never preselects the mock engine silently. */
export function TranscribeOptions({
  projectId,
  system,
  restart = false,
  onStarted,
}: {
  projectId: string;
  system: SystemInfo;
  restart?: boolean;
  onStarted: (job: Job) => void;
}) {
  const { t, locale } = useI18n();
  const realAvailable = system.providers.some((p) => p.kind === "local" && p.available);
  const selectable = system.providers.filter((p) => p.allowed && p.kind !== "external");
  const [language, setLanguage] = useState("auto");
  const [provider, setProvider] = useState(realAvailable ? "auto" : (selectable.find((p) => p.is_mock && p.available)?.name ?? "auto"));
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const languages = useMemo(
    () =>
      system.languages
        .filter((c) => c !== "auto")
        .map((code) => ({ code, name: languageName(code, locale) }))
        .sort((a, b) => a.name.localeCompare(b.name, locale)),
    [system.languages, locale],
  );

  const chosen = system.providers.find((p) => p.name === provider);
  const start = async () => {
    setBusy(true);
    setError(null);
    try {
      const job = await api.transcribe(projectId, provider, language);
      onStarted(job);
    } catch (e) {
      setError(e instanceof ApiError ? errorMessage(t, e) : t("common.error"));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="options">
      <div className="options-grid">
        <div>
          <label className="label" htmlFor={`lang-${projectId}`}>{t("opts.language")}</label>
          <select id={`lang-${projectId}`} className="select" value={language} onChange={(e) => setLanguage(e.target.value)}>
            <option value="auto">{t("opts.autoDetect")}</option>
            {languages.map((l) => (
              <option key={l.code} value={l.code}>{l.name}</option>
            ))}
          </select>
        </div>
        <div>
          <label className="label" htmlFor={`engine-${projectId}`}>{t("opts.engine")}</label>
          <select id={`engine-${projectId}`} className="select" value={provider} onChange={(e) => setProvider(e.target.value)}>
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
      {chosen?.is_mock && (
        <p className="hint options-note" data-testid="mock-hint">
          <InfoIcon size={14} /> {t("ws.mockBody")}
        </p>
      )}
      {error && <p className="field-error" role="alert">{error}</p>}
      <button type="button" className="btn btn-primary btn-lg options-start" onClick={start} disabled={busy}>
        {busy && <span className="spinner" aria-hidden="true" />}
        {busy ? t("opts.starting") : restart ? t("opts.restart") : t("opts.start")}
      </button>
    </div>
  );
}
