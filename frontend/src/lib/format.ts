// Pure formatting helpers. Kept dependency-free so they run under `node --test`.

export interface SegmentLike {
  id: number;
  start: number;
  end: number;
  text: string;
}

/** 0:05, 12:34, 1:02:03 – for durations and timestamp buttons. */
export function formatClock(seconds: number | null | undefined): string {
  if (seconds == null || !Number.isFinite(seconds) || seconds < 0) return "0:00";
  const total = Math.floor(seconds);
  const h = Math.floor(total / 3600);
  const m = Math.floor((total % 3600) / 60);
  const s = total % 60;
  const ss = String(s).padStart(2, "0");
  return h > 0 ? `${h}:${String(m).padStart(2, "0")}:${ss}` : `${m}:${ss}`;
}

/** Human readable duration such as "1 h 4 min" or "42 s". */
export function formatDuration(seconds: number | null | undefined): string {
  if (seconds == null || !Number.isFinite(seconds) || seconds <= 0) return "–";
  if (seconds < 60) return `${Math.max(1, Math.round(seconds))} s`;
  const totalMin = Math.round(seconds / 60);
  const h = Math.floor(totalMin / 60);
  const m = totalMin % 60;
  return h > 0 ? (m > 0 ? `${h} h ${m} min` : `${h} h`) : `${m} min`;
}

export function formatBytes(bytes: number | null | undefined, locale = "en"): string {
  if (bytes == null || !Number.isFinite(bytes) || bytes < 0) return "–";
  const units = ["B", "KB", "MB", "GB", "TB"];
  let value = bytes;
  let unit = 0;
  while (value >= 1024 && unit < units.length - 1) {
    value /= 1024;
    unit += 1;
  }
  const digits = unit === 0 || value >= 100 ? 0 : 1;
  return `${new Intl.NumberFormat(locale, { maximumFractionDigits: digits, minimumFractionDigits: 0 }).format(value)} ${units[unit]}`;
}

export function segmentsToText(segments: SegmentLike[]): string {
  return segments
    .map((s) => s.text.trim())
    .filter(Boolean)
    .join("\n\n");
}

export interface Match {
  segmentId: number;
  start: number;
  end: number;
}

/** Case-insensitive search across segments. Returns matches in document order. */
export function findMatches(segments: SegmentLike[], query: string): Match[] {
  const needle = query.trim().toLocaleLowerCase();
  if (!needle) return [];
  const out: Match[] = [];
  for (const seg of segments) {
    const hay = seg.text.toLocaleLowerCase();
    let from = 0;
    while (from <= hay.length) {
      const idx = hay.indexOf(needle, from);
      if (idx === -1) break;
      out.push({ segmentId: seg.id, start: idx, end: idx + needle.length });
      from = idx + Math.max(needle.length, 1);
    }
  }
  return out;
}

/** Index of the segment playing at ``time`` (binary search over sorted starts). */
export function activeSegmentIndex(segments: SegmentLike[], time: number): number {
  let lo = 0;
  let hi = segments.length - 1;
  let found = -1;
  while (lo <= hi) {
    const mid = (lo + hi) >> 1;
    if (segments[mid].start <= time) {
      found = mid;
      lo = mid + 1;
    } else {
      hi = mid - 1;
    }
  }
  if (found >= 0 && time > segments[found].end + 0.75) return -1; // in a gap between segments
  return found;
}

export function wordCount(segments: SegmentLike[]): number {
  return segments.reduce((n, s) => n + (s.text.trim() ? s.text.trim().split(/\s+/).length : 0), 0);
}
