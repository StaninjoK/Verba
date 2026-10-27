"use client";

import { useEffect, useState } from "react";
import { api, ApiError, type Job } from "@/lib/api";
import { formatClock } from "@/lib/format";
import { errorMessage, useI18n, type MessageKey } from "@/lib/i18n";
import { CheckIcon } from "../Icons";
import { useToast } from "../Toast";

const STAGES: { status: Job["status"]; key: MessageKey }[] = [
  { status: "pending", key: "job.stageQueue" },
  { status: "validating", key: "job.stagePrepare" },
  { status: "processing", key: "job.stageTranscribe" },
];

function useElapsed(from: string | null) {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    const id = window.setInterval(() => setNow(Date.now()), 1000);
    return () => window.clearInterval(id);
  }, []);
  return from ? Math.max(0, (now - new Date(from).getTime()) / 1000) : 0;
}

export function JobPanel({ job, onChanged }: { job: Job; onChanged: () => void }) {
  const { t } = useI18n();
  const toast = useToast();
  const [cancelling, setCancelling] = useState(false);
  const elapsed = useElapsed(job.started_at ?? job.created_at);
  const stageIndex = STAGES.findIndex((s) => s.status === job.status);
  const known = job.status === "processing" && job.progress_reported && job.progress != null;
  const pct = known ? Math.round((job.progress ?? 0) * 100) : null;

  const cancel = async () => {
    setCancelling(true);
    try {
      await api.cancelJob(job.id);
      onChanged();
    } catch (e) {
      toast(e instanceof ApiError ? errorMessage(t, e) : t("common.error"), "error");
      setCancelling(false);
    }
  };

  return (
    <section className="card card-pad job-panel" aria-live="polite" data-testid="job-panel">
      <ol className="stages">
        {STAGES.map((s, i) => (
          <li key={s.status} className={i < stageIndex ? "is-done" : i === stageIndex ? "is-current" : ""}>
            <span className="stage-dot">{i < stageIndex ? <CheckIcon size={12} /> : i + 1}</span>
            <span>{t(s.key)}</span>
          </li>
        ))}
      </ol>
      <div className={`progress${known ? "" : " progress-indeterminate"}`} role="progressbar" aria-valuemin={0}
        aria-valuemax={100} aria-valuenow={pct ?? undefined} aria-label={t(STAGES[Math.max(0, stageIndex)].key)}>
        <span style={known ? { width: `${pct}%` } : undefined} />
      </div>
      <div className="job-foot">
        <div className="hint">
          {known ? t("job.progressKnown", { pct: pct ?? 0 }) : job.status === "processing" && !job.progress_reported ? t("job.progressUnknown") : t("job.background")}
          <span className="job-elapsed tabular"> · {t("job.elapsed", { time: formatClock(elapsed) })}</span>
          {job.attempts > 1 && <span> · {t("job.attempt", { n: job.attempts })}</span>}
        </div>
        <button type="button" className="btn btn-sm" onClick={cancel} disabled={cancelling || job.cancel_requested}>
          {cancelling || job.cancel_requested ? t("job.cancelling") : t("job.cancel")}
        </button>
      </div>
    </section>
  );
}
