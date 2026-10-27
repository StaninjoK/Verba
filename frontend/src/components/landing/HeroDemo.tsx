"use client";

import { useEffect, useMemo, useState } from "react";
import { useI18n } from "@/lib/i18n";
import { LogoMark } from "@/components/Logo";

const BAR_COUNT = 56;
const STAMPS = ["00:00", "00:04", "00:09", "00:13"];

/** Decorative app-window illustration: a waveform that "types out" a transcript. */
export function HeroDemo() {
  const { t, locale } = useI18n();
  const lines = useMemo(
    () => [t("landing.hero.demoLine1"), t("landing.hero.demoLine2"), t("landing.hero.demoLine3"), t("landing.hero.demoLine4")],
    [t],
  );
  const [pos, setPos] = useState({ line: 0, chars: 0 });
  const [reduced, setReduced] = useState(false);

  // Pseudo-random but stable bar heights (no Math.random → no hydration mismatch).
  const bars = useMemo(
    () =>
      Array.from({ length: BAR_COUNT }, (_, i) => {
        const v = Math.abs(Math.sin(i * 1.7) * 0.6 + Math.sin(i * 0.43) * 0.4);
        return 18 + Math.round(v * 78);
      }),
    [],
  );

  useEffect(() => {
    const mq = window.matchMedia("(prefers-reduced-motion: reduce)");
    const update = () => setReduced(mq.matches);
    update();
    mq.addEventListener("change", update);
    return () => mq.removeEventListener("change", update);
  }, []);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- restart the animation when the language changes
    setPos({ line: 0, chars: 0 });
  }, [locale]);

  useEffect(() => {
    if (reduced) return;
    const current = lines[pos.line] ?? "";
    let delay = 26;
    if (pos.chars >= current.length) delay = pos.line >= lines.length - 1 ? 3200 : 650;
    const id = window.setTimeout(() => {
      setPos((p) => {
        const text = lines[p.line] ?? "";
        if (p.chars < text.length) return { line: p.line, chars: p.chars + 1 };
        if (p.line < lines.length - 1) return { line: p.line + 1, chars: 0 };
        return { line: 0, chars: 0 };
      });
    }, delay);
    return () => window.clearTimeout(id);
  }, [pos, lines, reduced]);

  const progress = reduced ? 100 : Math.round(((pos.line + (pos.chars / Math.max(1, (lines[pos.line] ?? "").length))) / lines.length) * 100);

  return (
    <figure className="demo" aria-label={t("landing.hero.illustration")}>
      <div className="demo-window" aria-hidden="true">
        <div className="demo-titlebar">
          <span className="demo-dots">
            <i />
            <i />
            <i />
          </span>
          <span className="demo-file">
            <LogoMark size={14} />
            {t("landing.hero.demoFile")}
          </span>
          <span className="demo-live">
            <span className="demo-live-dot" />
            {t("landing.hero.demoStatus")}
          </span>
        </div>

        <div className="demo-wave">
          <div className="demo-bars">
            {bars.map((h, i) => (
              <span
                key={i}
                className={i / BAR_COUNT <= progress / 100 ? "is-played" : undefined}
                style={{ height: `${h}%`, animationDelay: `${(i % 14) * -0.11}s` }}
              />
            ))}
          </div>
          <div className="demo-playhead" style={{ left: `${progress}%` }} />
        </div>

        <div className="demo-lines">
          {lines.map((line, i) => {
            const visible = reduced || i < pos.line;
            const active = !reduced && i === pos.line;
            const text = visible ? line : active ? line.slice(0, pos.chars) : "";
            return (
              <div key={i} className={`demo-line${active ? " is-active" : ""}${!visible && !active ? " is-pending" : ""}`}>
                <span className="demo-stamp">{STAMPS[i]}</span>
                <p>
                  {text}
                  {active && <span className="demo-caret" />}
                  {!visible && !active && <span className="demo-ghost" />}
                </p>
              </div>
            );
          })}
        </div>
      </div>
      <figcaption className="demo-caption">{t("landing.hero.illustration")}</figcaption>
    </figure>
  );
}
