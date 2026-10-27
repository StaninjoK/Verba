"use client";

import { useEffect, useState } from "react";
import { LOCALES, useI18n, type Locale } from "@/lib/i18n";
import { MonitorIcon, MoonIcon, SunIcon } from "./Icons";

type ThemeChoice = "system" | "light" | "dark";
const ORDER: ThemeChoice[] = ["system", "light", "dark"];

export function ThemeToggle() {
  const { t } = useI18n();
  const [theme, setTheme] = useState<ThemeChoice>("system");

  useEffect(() => {
    try {
      const stored = window.localStorage.getItem("verba-theme");
      // eslint-disable-next-line react-hooks/set-state-in-effect -- the saved theme is only readable on the client
      if (stored === "light" || stored === "dark") setTheme(stored);
    } catch {
      // ignore
    }
  }, []);

  const cycle = () => {
    const next = ORDER[(ORDER.indexOf(theme) + 1) % ORDER.length];
    setTheme(next);
    const root = document.documentElement;
    try {
      if (next === "system") {
        delete root.dataset.theme;
        window.localStorage.removeItem("verba-theme");
      } else {
        root.dataset.theme = next;
        window.localStorage.setItem("verba-theme", next);
      }
    } catch {
      // ignore storage errors; the theme still applies for this page view
    }
  };

  const label = t(theme === "system" ? "theme.system" : theme === "light" ? "theme.light" : "theme.dark");
  const IconFor = theme === "system" ? MonitorIcon : theme === "light" ? SunIcon : MoonIcon;
  return (
    <button type="button" className="btn btn-ghost btn-icon btn-sm" onClick={cycle} title={`${t("theme.toggle")}: ${label}`}
      aria-label={`${t("theme.toggle")}: ${label}`}>
      <IconFor />
    </button>
  );
}

export function LanguageSwitcher() {
  const { locale, setLocale, t } = useI18n();
  return (
    <label className="lang-switch">
      <span className="sr-only">{t("lang.label")}</span>
      <select value={locale} onChange={(e) => setLocale(e.target.value as Locale)} aria-label={t("lang.label")}>
        {LOCALES.map((l) => (
          <option key={l.code} value={l.code}>
            {l.code.toUpperCase()}
          </option>
        ))}
      </select>
    </label>
  );
}
