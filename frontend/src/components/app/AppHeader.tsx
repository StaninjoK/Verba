"use client";

import Link from "next/link";
import { useI18n } from "@/lib/i18n";
import type { SystemState } from "@/lib/useSystem";
import { Logo } from "../Logo";
import { LanguageSwitcher, ThemeToggle } from "../PreferenceControls";

export function EngineStatus({ state }: { state: SystemState }) {
  const { t } = useI18n();
  if (state.kind === "loading") {
    return <span className="badge">{t("engine.checking")}</span>;
  }
  if (state.kind === "offline") {
    return <span className="badge badge-danger badge-dot" title={t("engine.offlineHelp")}>{t("engine.offline")}</span>;
  }
  const real = state.info.providers.find((p) => p.kind === "local" && p.available);
  return real ? (
    <span className="badge badge-success badge-dot" title={`${real.label} · ${real.model ?? ""}`}>{t("engine.ready")}</span>
  ) : (
    <span className="badge badge-warning badge-dot">{t("engine.testOnly")}</span>
  );
}

export function AppHeader({ state }: { state: SystemState }) {
  const { t } = useI18n();
  return (
    <>
      <a className="skip-link" href="#main">{t("nav.skip")}</a>
      <header className="app-header">
        <div className="container app-header-inner">
          <div className="app-header-left">
            <Logo href="/" height={20} />
            <nav aria-label="Main" className="app-nav">
              <Link href="/app" className="app-nav-link">{t("nav.library")}</Link>
            </nav>
          </div>
          <div className="app-header-right">
            <EngineStatus state={state} />
            <LanguageSwitcher />
            <ThemeToggle />
          </div>
        </div>
      </header>
    </>
  );
}
