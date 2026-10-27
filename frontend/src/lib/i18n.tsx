"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { appDe, appEn, appEs, type AppKey } from "./messages/app";
import { landingDe, landingEn, landingEs, type LandingKey } from "./messages/landing";

export type Locale = "de" | "en" | "es";
export type MessageKey = AppKey | LandingKey;

export const LOCALES: { code: Locale; label: string }[] = [
  { code: "de", label: "Deutsch" },
  { code: "en", label: "English" },
  { code: "es", label: "Español" },
];

const DICTIONARIES: Record<Locale, Record<MessageKey, string>> = {
  en: { ...appEn, ...landingEn },
  de: { ...appDe, ...landingDe },
  es: { ...appEs, ...landingEs },
};

const STORAGE_KEY = "verba-locale";
const DEFAULT_LOCALE: Locale = "de";

type Vars = Record<string, string | number>;

interface I18nValue {
  locale: Locale;
  setLocale: (locale: Locale) => void;
  t: (key: MessageKey, vars?: Vars) => string;
}

const I18nContext = createContext<I18nValue | null>(null);

export function interpolate(template: string, vars?: Vars): string {
  if (!vars) return template;
  return template.replace(/\{(\w+)\}/g, (match, name: string) => (name in vars ? String(vars[name]) : match));
}

function detectLocale(): Locale {
  try {
    const stored = window.localStorage.getItem(STORAGE_KEY);
    if (stored === "de" || stored === "en" || stored === "es") return stored;
  } catch {
    // storage unavailable (private mode) – fall through to the browser language
  }
  for (const lang of navigator.languages ?? [navigator.language]) {
    const base = lang.slice(0, 2).toLowerCase();
    if (base === "de" || base === "en" || base === "es") return base;
  }
  return DEFAULT_LOCALE;
}

export function I18nProvider({ children }: { children: ReactNode }) {
  const [locale, setLocaleState] = useState<Locale>(DEFAULT_LOCALE);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- locale is only known on the client
    setLocaleState(detectLocale());
  }, []);

  useEffect(() => {
    document.documentElement.lang = locale;
  }, [locale]);

  const setLocale = useCallback((next: Locale) => {
    setLocaleState(next);
    try {
      window.localStorage.setItem(STORAGE_KEY, next);
    } catch {
      // ignore
    }
  }, []);

  const t = useCallback(
    (key: MessageKey, vars?: Vars) => interpolate(DICTIONARIES[locale][key] ?? DICTIONARIES.en[key] ?? key, vars),
    [locale],
  );

  const value = useMemo(() => ({ locale, setLocale, t }), [locale, setLocale, t]);
  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>;
}

export function useI18n(): I18nValue {
  const ctx = useContext(I18nContext);
  if (!ctx) throw new Error("useI18n must be used inside I18nProvider");
  return ctx;
}

/** Localised text for a backend error code, falling back to the server's (English) message. */
export function errorMessage(t: I18nValue["t"], err: { code: string; message: string } | null | undefined, fallback = ""): string {
  if (!err) return fallback;
  const key = `err.${err.code}` as MessageKey;
  const text = t(key);
  return text === key ? err.message || fallback : text;
}
