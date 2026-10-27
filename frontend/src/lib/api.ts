// Typed client for the Verba backend.

export const API_BASE = (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000").replace(/\/$/, "");

export type JobStatus = "pending" | "validating" | "processing" | "completed" | "failed" | "cancelled";
export type ProjectStatus = JobStatus | "ready";

export interface ApiErrorBody {
  code: string;
  message: string;
}

export class ApiError extends Error {
  constructor(
    public status: number,
    public code: string,
    message: string,
  ) {
    super(message);
  }
}

export interface Job {
  id: string;
  status: JobStatus;
  provider: string;
  model: string | null;
  language_requested: string | null;
  progress: number | null;
  progress_reported: boolean;
  cancel_requested: boolean;
  attempts: number;
  error: ApiErrorBody | null;
  created_at: string;
  updated_at: string;
  started_at: string | null;
  finished_at: string | null;
}

export interface Segment {
  id: number;
  start: number;
  end: number;
  text: string;
}

export interface ProjectSummary {
  id: string;
  title: string;
  original_filename: string;
  media_type: string;
  container: string;
  size_bytes: number;
  duration_seconds: number | null;
  has_video: boolean;
  media_info: { audio_codec?: string | null; sample_rate?: number | null; channels?: number | null };
  language_detected: string | null;
  provider: string | null;
  model: string | null;
  is_mock: boolean;
  has_transcript: boolean;
  transcript_version: number;
  transcript_edited: boolean;
  word_count: number;
  status: ProjectStatus;
  job: Job | null;
  created_at: string;
  updated_at: string;
  preview?: string;
  duplicate_of?: { id: string; title: string } | null;
}

export interface Project extends ProjectSummary {
  segments: Segment[];
}

export interface ProviderInfo {
  name: string;
  label: string;
  kind: "local" | "external" | "mock";
  available: boolean;
  allowed: boolean;
  reason: string | null;
  model: string | null;
  language_detection: boolean;
  reports_progress: boolean;
  supports_cancel: boolean;
  is_mock: boolean;
  sends_data_externally: boolean;
}

export interface SystemInfo {
  version: string;
  ffmpeg_available: boolean;
  providers: ProviderInfo[];
  real_engine_available: boolean;
  default_provider: string;
  external_providers_enabled: boolean;
  processing_location: string;
  limits: {
    max_upload_bytes: number;
    max_storage_bytes: number;
    max_concurrent_jobs: number;
    max_media_duration_seconds: number;
  };
  storage: { used_bytes: number; data_dir: string; orphan_files: number };
  allowed_extensions: string[];
  languages: string[];
}

export const ACTIVE_STATUSES: ProjectStatus[] = ["pending", "validating", "processing"];
export const isActive = (status: ProjectStatus) => ACTIVE_STATUSES.includes(status);

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${API_BASE}${path}`, { cache: "no-store", ...init });
  } catch {
    throw new ApiError(0, "network_error", "The Verba backend is not reachable.");
  }
  if (res.status === 204) return undefined as T;
  const body = await res.json().catch(() => null);
  if (!res.ok) {
    const err = body?.error as ApiErrorBody | undefined;
    throw new ApiError(res.status, err?.code ?? "http_error", err?.message ?? `Request failed (${res.status})`);
  }
  return body as T;
}

const json = (method: string, data: unknown): RequestInit => ({
  method,
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(data),
});

export const api = {
  system: () => request<SystemInfo>("/api/system"),
  listProjects: (q?: string) =>
    request<{ projects: ProjectSummary[] }>(`/api/projects${q ? `?q=${encodeURIComponent(q)}` : ""}`).then((r) => r.projects),
  getProject: (id: string) => request<Project>(`/api/projects/${encodeURIComponent(id)}`),
  rename: (id: string, title: string) => request<ProjectSummary>(`/api/projects/${encodeURIComponent(id)}`, json("PATCH", { title })),
  remove: (id: string) => request<void>(`/api/projects/${encodeURIComponent(id)}`, { method: "DELETE" }),
  transcribe: (id: string, provider: string, language: string) =>
    request<Job>(`/api/projects/${encodeURIComponent(id)}/transcribe`, json("POST", { provider, language })),
  cancelJob: (jobId: string) => request<Job>(`/api/jobs/${encodeURIComponent(jobId)}/cancel`, { method: "POST" }),
  saveTranscript: (id: string, version: number, segments: { id: number; text: string }[]) =>
    request<{ version: number; saved_at: string }>(`/api/projects/${encodeURIComponent(id)}/transcript`, json("PUT", { version, segments })),
  mediaUrl: (id: string) => `${API_BASE}/api/projects/${encodeURIComponent(id)}/media`,
  exportUrl: (id: string, format: string, timestamps = false) =>
    `${API_BASE}/api/projects/${encodeURIComponent(id)}/export?format=${format}${timestamps ? "&timestamps=true" : ""}`,
};

export interface UploadHandle {
  promise: Promise<ProjectSummary>;
  abort: () => void;
}

/** Upload with real byte progress (fetch cannot report upload progress, XHR can). */
export function uploadFile(file: File, onProgress: (fraction: number) => void): UploadHandle {
  const xhr = new XMLHttpRequest();
  const promise = new Promise<ProjectSummary>((resolve, reject) => {
    xhr.open("POST", `${API_BASE}/api/projects`);
    xhr.setRequestHeader("X-Verba-Filename", encodeURIComponent(file.name));
    xhr.setRequestHeader("Content-Type", "application/octet-stream");
    xhr.upload.onprogress = (e) => {
      if (e.lengthComputable) onProgress(e.loaded / e.total);
    };
    xhr.onload = () => {
      let body: unknown = null;
      try {
        body = JSON.parse(xhr.responseText);
      } catch {
        // non-JSON error body
      }
      if (xhr.status >= 200 && xhr.status < 300) {
        resolve(body as ProjectSummary);
      } else {
        const err = (body as { error?: ApiErrorBody } | null)?.error;
        reject(new ApiError(xhr.status, err?.code ?? "upload_failed", err?.message ?? "Upload failed"));
      }
    };
    xhr.onerror = () => reject(new ApiError(0, "network_error", "The Verba backend is not reachable."));
    xhr.onabort = () => reject(new ApiError(0, "aborted", "Upload cancelled"));
    xhr.send(file);
  });
  return { promise, abort: () => xhr.abort() };
}
