"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useI18n } from "@/lib/i18n";
import { Logo } from "@/components/Logo";
import { LanguageSwitcher, ThemeToggle } from "@/components/PreferenceControls";
import { ArrowRightIcon, XIcon } from "@/components/Icons";

const LINKS = [
  { href: "#features", key: "landing.nav.features" },
  { href: "#how", key: "landing.nav.how" },
  { href: "#privacy", key: "landing.nav.privacy" },
  { href: "#faq", key: "landing.nav.faq" },
] as const;

export function LandingHeader() {
  const { t } = useI18n();
  const [open, setOpen] = useState(false);
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 8);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && setOpen(false);
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open]);

  return (
    <header className={`l-header${scrolled ? " is-scrolled" : ""}${open ? " is-open" : ""}`}>
      <div className="container l-header-inner">
        <Logo height={22} />
        <nav className="l-nav" aria-label={t("landing.nav.main")} id="landing-nav">
          {LINKS.map((l) => (
            <a key={l.href} href={l.href} onClick={() => setOpen(false)}>
              {t(l.key)}
            </a>
          ))}
          <Link href="/app" className="btn btn-primary l-nav-cta-mobile">
            {t("nav.openApp")} <ArrowRightIcon size={16} />
          </Link>
        </nav>
        <div className="l-header-actions">
          <LanguageSwitcher />
          <ThemeToggle />
          <Link href="/app" className="btn btn-primary btn-sm l-header-cta">
            {t("nav.openApp")}
          </Link>
          <button
            type="button"
            className="btn btn-ghost btn-sm btn-icon l-menu-btn"
            aria-expanded={open}
            aria-controls="landing-nav"
            aria-label={t("landing.nav.menu")}
            onClick={() => setOpen((v) => !v)}
          >
            {open ? (
              <XIcon />
            ) : (
              <svg width="18" height="18" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" aria-hidden="true">
                <path d="M3.5 6.5h13M3.5 13.5h13" />
              </svg>
            )}
          </button>
        </div>
      </div>
    </header>
  );
}
