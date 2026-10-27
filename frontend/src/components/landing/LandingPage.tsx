"use client";

import Link from "next/link";
import { useEffect, useRef } from "react";
import { useI18n, type MessageKey } from "@/lib/i18n";
import { Logo } from "@/components/Logo";
import {
  ArrowRightIcon,
  CheckIcon,
  CpuIcon,
  DownloadIcon,
  FileVideoIcon,
  GlobeIcon,
  PencilIcon,
  PlayIcon,
  SearchIcon,
  ShieldIcon,
  UploadIcon,
} from "@/components/Icons";
import { LandingHeader } from "./LandingHeader";
import { HeroDemo } from "./HeroDemo";

const MARQUEE = [
  "Deutsch", "English", "Español", "Français", "Italiano", "Português", "Nederlands", "Polski", "Türkçe", "Українська",
  "日本語", "한국어", "中文", "العربية", "हिन्दी", "Svenska", "MP3", "WAV", "M4A", "MP4", "MOV", "FLAC", "OGG", "WebM",
  "SRT", "VTT", "DOCX", "TXT",
];

const USES: MessageKey[] = [
  "landing.uses.students",
  "landing.uses.journalists",
  "landing.uses.researchers",
  "landing.uses.podcasters",
  "landing.uses.creators",
  "landing.uses.teams",
  "landing.uses.lectures",
  "landing.uses.interviews",
  "landing.uses.meetings",
  "landing.uses.subtitles",
];

const FAQ: [MessageKey, MessageKey][] = [
  ["landing.faq.q1", "landing.faq.a1"],
  ["landing.faq.q2", "landing.faq.a2"],
  ["landing.faq.q3", "landing.faq.a3"],
  ["landing.faq.q4", "landing.faq.a4"],
  ["landing.faq.q5", "landing.faq.a5"],
  ["landing.faq.q6", "landing.faq.a6"],
];

/** Adds .is-visible to [data-reveal] elements as they scroll into view. */
function useReveal(root: React.RefObject<HTMLElement | null>) {
  useEffect(() => {
    const el = root.current;
    if (!el) return;
    const targets = Array.from(el.querySelectorAll<HTMLElement>("[data-reveal]"));
    if (!("IntersectionObserver" in window) || window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      targets.forEach((t) => t.classList.add("is-visible"));
      return;
    }
    el.classList.add("js-reveal");
    const io = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) {
            entry.target.classList.add("is-visible");
            io.unobserve(entry.target);
          }
        }
      },
      { rootMargin: "0px 0px -8% 0px", threshold: 0.08 },
    );
    targets.forEach((t) => io.observe(t));
    return () => io.disconnect();
  }, [root]);
}

function SectionHead({ eyebrow, title, accent }: { eyebrow: string; title: string; accent?: string }) {
  return (
    <div className="l-section-head" data-reveal>
      <p className="l-eyebrow">{eyebrow}</p>
      <h2>
        {title} {accent && <em>{accent}</em>}
      </h2>
    </div>
  );
}

export function LandingPage() {
  const { t } = useI18n();
  const rootRef = useRef<HTMLDivElement>(null);
  useReveal(rootRef);
  const year = new Date().getFullYear();

  return (
    <div className="landing" ref={rootRef}>
      <a className="skip-link" href="#main">
        {t("nav.skip")}
      </a>
      <LandingHeader />

      <main id="main">
        {/* ------------------------------------------------------------ Hero */}
        <section className="l-hero">
          <div className="l-hero-glow" aria-hidden="true" />
          <div className="l-hero-grid" aria-hidden="true" />
          <div className="container l-hero-inner">
            <div className="l-hero-copy">
              <p className="l-pill">
                <ShieldIcon size={15} /> {t("landing.hero.eyebrow")}
              </p>
              <h1>
                {t("landing.hero.titleA")} <em>{t("landing.hero.titleAccent")}</em> {t("landing.hero.titleB")}
              </h1>
              <p className="l-hero-sub">{t("landing.hero.subtitle")}</p>
              <div className="l-hero-ctas">
                <Link href="/app" className="btn btn-primary btn-lg l-cta-main">
                  {t("landing.hero.ctaPrimary")} <ArrowRightIcon size={17} />
                </Link>
                <a href="#how" className="btn btn-lg">
                  {t("landing.hero.ctaSecondary")}
                </a>
              </div>
              <p className="l-hero-note">{t("landing.hero.note")}</p>
            </div>
            <div className="l-hero-visual">
              <HeroDemo />
            </div>
          </div>
        </section>

        {/* --------------------------------------------------------- Marquee */}
        <section className="l-marquee" aria-label={t("landing.marquee.label")}>
          <div className="l-marquee-track">
            {[0, 1].map((copy) => (
              <ul key={copy} aria-hidden={copy === 1 ? true : undefined}>
                {MARQUEE.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            ))}
          </div>
        </section>

        {/* -------------------------------------------------------- Features */}
        <section id="features" className="l-section">
          <div className="container">
            <SectionHead
              eyebrow={t("landing.features.eyebrow")}
              title={t("landing.features.title")}
              accent={t("landing.features.titleAccent")}
            />
            <div className="l-bento">
              <article className="l-card l-card-local" data-reveal>
                <div className="l-card-icon">
                  <CpuIcon />
                </div>
                <h3>{t("landing.features.local.title")}</h3>
                <p>{t("landing.features.local.body")}</p>
                <div className="l-local-visual" aria-hidden="true">
                  <span className="l-orbit" />
                  <span className="l-orbit l-orbit-2" />
                  <span className="l-chip-core">
                    <ShieldIcon size={22} />
                  </span>
                </div>
              </article>
              <article className="l-card" data-reveal>
                <div className="l-card-icon">
                  <GlobeIcon />
                </div>
                <h3>{t("landing.features.languages.title")}</h3>
                <p>{t("landing.features.languages.body")}</p>
                <div className="l-lang-cloud" aria-hidden="true">
                  {["DE", "EN", "ES", "FR", "IT", "PT", "NL", "PL", "JA", "+"].map((c) => (
                    <span key={c}>{c}</span>
                  ))}
                </div>
              </article>
              <article className="l-card" data-reveal>
                <div className="l-card-icon">
                  <DownloadIcon />
                </div>
                <h3>{t("landing.features.exports.title")}</h3>
                <p>{t("landing.features.exports.body")}</p>
                <div className="l-formats" aria-hidden="true">
                  {["TXT", "SRT", "VTT", "DOCX", "JSON"].map((f) => (
                    <span key={f}>{f}</span>
                  ))}
                </div>
              </article>
              <article className="l-card l-card-editor" data-reveal>
                <div className="l-card-icon">
                  <PencilIcon />
                </div>
                <h3>{t("landing.features.editor.title")}</h3>
                <p>{t("landing.features.editor.body")}</p>
                <div className="l-editor-visual" aria-hidden="true">
                  <div className="l-ed-search">
                    <SearchIcon size={14} /> <span>story</span> <small>1 / 3</small>
                  </div>
                  <div className="l-ed-row">
                    <span>00:04</span>
                    <p>
                      How ideas become <mark>story</mark>…
                    </p>
                  </div>
                  <div className="l-ed-row is-active">
                    <span>00:09</span>
                    <p>It always starts with listening.</p>
                  </div>
                </div>
              </article>
              <article className="l-card" data-reveal>
                <div className="l-card-icon">
                  <FileVideoIcon />
                </div>
                <h3>{t("landing.features.formats.title")}</h3>
                <p>{t("landing.features.formats.body")}</p>
              </article>
              <article className="l-card l-card-wide" data-reveal>
                <div className="l-card-icon">
                  <PlayIcon />
                </div>
                <h3>{t("landing.features.playback.title")}</h3>
                <p>{t("landing.features.playback.body")}</p>
                <div className="l-mini-player" aria-hidden="true">
                  <span className="l-mini-play">
                    <PlayIcon size={12} />
                  </span>
                  <span className="l-mini-track">
                    <span />
                  </span>
                  <small>01:24</small>
                </div>
              </article>
            </div>
          </div>
        </section>

        {/* ----------------------------------------------------- How it works */}
        <section id="how" className="l-section l-section-alt">
          <div className="container">
            <SectionHead eyebrow={t("landing.how.eyebrow")} title={t("landing.how.title")} accent={t("landing.how.titleAccent")} />
            <ol className="l-steps">
              {[
                { icon: <UploadIcon />, title: "landing.how.step1.title", body: "landing.how.step1.body" },
                { icon: <GlobeIcon />, title: "landing.how.step2.title", body: "landing.how.step2.body" },
                { icon: <DownloadIcon />, title: "landing.how.step3.title", body: "landing.how.step3.body" },
              ].map((s, i) => (
                <li key={s.title} className="l-step" data-reveal style={{ transitionDelay: `${i * 90}ms` }}>
                  <span className="l-step-num">{String(i + 1).padStart(2, "0")}</span>
                  <span className="l-step-icon">{s.icon}</span>
                  <h3>{t(s.title as MessageKey)}</h3>
                  <p>{t(s.body as MessageKey)}</p>
                </li>
              ))}
            </ol>
          </div>
        </section>

        {/* ---------------------------------------------------------- Privacy */}
        <section id="privacy" className="l-section">
          <div className="container l-privacy">
            <div data-reveal>
              <p className="l-eyebrow">{t("landing.privacy.eyebrow")}</p>
              <h2>
                {t("landing.privacy.title")} <em>{t("landing.privacy.titleAccent")}</em>
              </h2>
              <p className="l-lead">{t("landing.privacy.body")}</p>
              <ul className="l-checks">
                {(["landing.privacy.point1", "landing.privacy.point2", "landing.privacy.point3", "landing.privacy.point4"] as const).map(
                  (k) => (
                    <li key={k}>
                      <span className="l-check">
                        <CheckIcon size={14} />
                      </span>
                      {t(k)}
                    </li>
                  ),
                )}
              </ul>
            </div>
            <div className="l-privacy-card" data-reveal aria-hidden="true">
              <p className="l-pc-title">{t("landing.privacy.cardTitle")}</p>
              <div className="l-pc-row">
                <span className="l-pc-label">
                  <CpuIcon size={16} /> {t("landing.privacy.cardLocal")}
                </span>
                <span className="badge badge-success badge-dot">{t("landing.privacy.cardOn")}</span>
              </div>
              <div className="l-pc-row is-off">
                <span className="l-pc-label">
                  <GlobeIcon size={16} /> {t("landing.privacy.cardCloud")}
                </span>
                <span className="badge">{t("landing.privacy.cardOff")}</span>
              </div>
              <div className="l-pc-flow">
                <span className="l-pc-node">
                  <UploadIcon size={16} />
                </span>
                <span className="l-pc-line" />
                <span className="l-pc-node l-pc-node-main">
                  <ShieldIcon size={18} />
                </span>
                <span className="l-pc-line" />
                <span className="l-pc-node">
                  <PencilIcon size={16} />
                </span>
              </div>
            </div>
          </div>
        </section>

        {/* ------------------------------------------------------------- Uses */}
        <section className="l-section l-section-alt l-uses">
          <div className="container">
            <SectionHead eyebrow={t("landing.uses.eyebrow")} title={t("landing.uses.title")} />
            <ul className="l-use-chips" data-reveal>
              {USES.map((k) => (
                <li key={k}>{t(k)}</li>
              ))}
            </ul>
          </div>
        </section>

        {/* -------------------------------------------------------------- FAQ */}
        <section id="faq" className="l-section">
          <div className="container l-faq-wrap">
            <SectionHead eyebrow={t("landing.faq.eyebrow")} title={t("landing.faq.title")} />
            <div className="l-faq" data-reveal>
              {FAQ.map(([q, a]) => (
                <details key={q}>
                  <summary>
                    {t(q)}
                    <span className="l-faq-plus" aria-hidden="true" />
                  </summary>
                  <p>{t(a)}</p>
                </details>
              ))}
            </div>
          </div>
        </section>

        {/* -------------------------------------------------------------- CTA */}
        <section className="l-cta-section">
          <div className="container">
            <div className="l-cta" data-reveal>
              <div className="l-cta-glow" aria-hidden="true" />
              <h2>{t("landing.cta.title")}</h2>
              <p>{t("landing.cta.body")}</p>
              <Link href="/app" className="btn btn-lg l-cta-btn">
                {t("landing.cta.button")} <ArrowRightIcon size={17} />
              </Link>
            </div>
          </div>
        </section>
      </main>

      <footer className="l-footer">
        <div className="container l-footer-inner">
          <div className="l-footer-brand">
            <Logo height={20} />
            <p>{t("landing.footer.tagline")}</p>
          </div>
          <nav aria-label={t("landing.footer.product")} className="l-footer-nav">
            <Link href="/app">{t("landing.footer.app")}</Link>
            <a href="#features">{t("landing.nav.features")}</a>
            <a href="#how">{t("landing.nav.how")}</a>
            <a href="#privacy">{t("landing.nav.privacy")}</a>
            <a href="#faq">{t("landing.nav.faq")}</a>
          </nav>
        </div>
        <div className="container">
          <p className="l-footer-rights">{t("landing.footer.rights", { year })}</p>
        </div>
      </footer>
    </div>
  );
}
