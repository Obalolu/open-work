import type {
  Job,
  JobDetail,
  ChapterDetail,
  GenerateRequest,
  GenerationStatus,
  Source,
  AppConfig,
  ProxyPoolStatus,
} from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`API error ${res.status}: ${body}`);
  }
  return res.json();
}

export const api = {
  jobs: {
    list: () => request<Job[]>("/api/jobs"),
    get: (id: string) => request<JobDetail>(`/api/jobs/${id}`),
    create: (data: {
      topic: string;
      paper_type?: string;
      citation_style?: string;
      target_audience?: string;
      chapters?: { name: string }[];
    }) =>
      request<Job>("/api/jobs", {
        method: "POST",
        body: JSON.stringify(data),
      }),
    delete: (id: string) =>
      request<{ ok: boolean }>(`/api/jobs/${id}`, { method: "DELETE" }),
  },

  chapters: {
    list: (jobId: string) =>
      request<{ id: number; chapter_number: number; name: string; status: string; word_count: number; ai_score: number | null; style_score: number | null }[]>(
        `/api/jobs/${jobId}/chapters`
      ),
    get: (jobId: string, num: number) =>
      request<ChapterDetail>(`/api/jobs/${jobId}/chapters/${num}`),
    references: (jobId: string) =>
      request<{ content: string }>(`/api/jobs/${jobId}/references`),
  },

  generate: {
    start: (jobId: string, data: GenerateRequest) =>
      request<{ run_id: string; status: string }>(`/api/jobs/${jobId}/generate`, {
        method: "POST",
        body: JSON.stringify(data),
      }),
    status: (jobId: string) =>
      request<GenerationStatus>(`/api/jobs/${jobId}/generate/status`),
  },

  research: {
    sources: (jobId: string) =>
      request<Source[]>(`/api/jobs/${jobId}/research`),
  },

  config: {
    get: () => request<AppConfig>("/api/config"),
    update: (data: Record<string, unknown>) =>
      request<{ ok: boolean }>("/api/config", { method: "PUT", body: JSON.stringify(data) }),
  },

  proxy: {
    status: () => request<ProxyPoolStatus>("/api/proxy/pool"),
    refresh: () =>
      request<{ ok: boolean; output?: string; error?: string }>(
        "/api/proxy/refresh",
        { method: "POST" }
      ),
  },

  export: {
    url: (jobId: string, chapter: number, format: string) =>
      `${API_BASE}/api/jobs/${jobId}/chapters/${chapter}/export?format=${format}`,
  },
};
