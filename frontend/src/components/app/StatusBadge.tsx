"use client";

import type { ProjectStatus } from "@/lib/api";
import { useI18n, type MessageKey } from "@/lib/i18n";

const STYLE: Record<ProjectStatus, string> = {
  ready: "badge",
  pending: "badge badge-accent badge-dot badge-live",
  validating: "badge badge-accent badge-dot badge-live",
  processing: "badge badge-accent badge-dot badge-live",
  completed: "badge badge-success badge-dot",
  failed: "badge badge-danger badge-dot",
  cancelled: "badge",
};

export function StatusBadge({ status }: { status: ProjectStatus }) {
  const { t } = useI18n();
  return <span className={STYLE[status]} data-status={status}>{t(`status.${status}` as MessageKey)}</span>;
}

export function MockBadge() {
  const { t } = useI18n();
  return <span className="badge badge-warning" data-testid="mock-badge">{t("status.mock")}</span>;
}
