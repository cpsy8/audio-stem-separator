export type ModelName =
  | "htdemucs"
  | "htdemucs_ft"
  | "htdemucs_6s"
  | "mdx"
  | "mdx_extra"
  | "mdx_q"
  | "mdx_extra_q";

export type JobStatus =
  | "queued"
  | "running"
  | "completed"
  | "cancelled"
  | "failed";

export interface JobOptions {
  model: ModelName;
  vocals_only: boolean;
  wav: boolean;
  bitrate: number;
}

export interface Job {
  id: string;
  filename: string;
  input_path: string;
  size_bytes: number;
  options: JobOptions;
  status: JobStatus;
  queued_at: string;
  started_at: string | null;
  completed_at: string | null;
  estimated_duration_sec: number;
  output_dir: string;
  error: string | null;
}

export interface QueueResponse {
  autorun: boolean;
  current_job_id: string | null;
  autorun_next_at: string | null;
  jobs: Job[];
}

export interface JobFile {
  name: string;
  path: string;
  size: number;
}

export interface LogEntry {
  seq: number;
  timestamp: string;
  level: string;
  event: string;
  [key: string]: unknown;
}

const BASE = "/api";

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, init);
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`${res.status}: ${text || res.statusText}`);
  }
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

export const api = {
  getQueue: () => req<QueueResponse>("/queue"),

  upload: (file: File, name: string, opts: JobOptions) => {
    const fd = new FormData();
    fd.append("file", file);
    fd.append("name", name);
    fd.append("model", opts.model);
    fd.append("vocals_only", String(opts.vocals_only));
    fd.append("wav", String(opts.wav));
    fd.append("bitrate", String(opts.bitrate));
    return req<{ job_id: string }>("/upload", { method: "POST", body: fd });
  },

  remove: (id: string) =>
    req<void>(`/queue/${id}`, { method: "DELETE" }),

  run: () => req<void>("/run", { method: "POST" }),
  stop: () => req<void>("/stop", { method: "POST" }),

  setAutorun: (enabled: boolean) =>
    req<void>("/autorun", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ enabled }),
    }),

  listFiles: (id: string) => req<JobFile[]>(`/jobs/${id}/files`),
  clear: (id: string) =>
    req<void>(`/jobs/${id}/clear`, { method: "DELETE" }),

  getLogs: (since = 0) => req<LogEntry[]>(`/logs?since=${since}`),

  zipUrl: (id: string) => `${BASE}/download/${id}/zip`,
  fileUrl: (id: string, path: string) =>
    `${BASE}/download/${id}/file?path=${encodeURIComponent(path)}`,
};
