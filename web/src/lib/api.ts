import type {
  Job,
  JobDetail,
  ChapterDetail,
  GenerateRequest,
  GenerationStatus,
  Source,
  AppConfig,
  ProxyPoolStatus,
  ChapterRevisionSummary,
  ChapterRevisionDetail,
  HumanizerAttemptSummary,
  HealthResponse,
} from "./types";

const rawBase = process.env.NEXT_PUBLIC_API_URL || "";
// Ignore Docker-internal hostnames that the browser cannot resolve.
const API_BASE =
  /^https?:\/\/(api|localhost|127\.0\.0\.1)(:\d+)?\/?$/.test(rawBase) ? "" : rawBase;

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
      research_queries?: string[];
      chapters?: { name: string; template?: string }[];
    }) =>
      request<Job>("/api/jobs", {
        method: "POST",
        body: JSON.stringify(data),
      }),
    update: (id: string, data: {
      topic?: string;
      paper_type?: string;
      citation_style?: string;
      target_audience?: string;
      research_queries?: string[];
      chapters?: { name: string; template?: string }[];
    }) =>
      request<Job>(`/api/jobs/${id}`, {
        method: "PUT",
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
    update: (
      jobId: string,
      num: number,
      data: { content: string; source?: string; summary?: string }
    ) =>
      request<ChapterDetail>(`/api/jobs/${jobId}/chapters/${num}`, {
        method: "PATCH",
        body: JSON.stringify(data),
      }),
    revisions: (jobId: string, num: number) =>
      request<ChapterRevisionSummary[]>(
        `/api/jobs/${jobId}/chapters/${num}/revisions`
      ),
    revision: (jobId: string, num: number, revisionId: number) =>
      request<ChapterRevisionDetail>(
        `/api/jobs/${jobId}/chapters/${num}/revisions/${revisionId}`
      ),
    humanizerAttempts: (jobId: string, num: number) =>
      request<HumanizerAttemptSummary[]>(
        `/api/jobs/${jobId}/chapters/${num}/humanizer-attempts`
      ),
    references: (jobId: string) =>
      request<{ content: string }>(`/api/jobs/${jobId}/references`),
  },

  generate: {
    start: (jobId: string, data: GenerateRequest) =>
      request<{ run_id: string; status: string }>(`/api/jobs/${jobId}/generate`, {
        method: "POST",
        body: JSON.stringify(data),
      }),
    cancel: (jobId: string) =>
      request<{ ok: boolean; run_id: string }>(
        `/api/jobs/${jobId}/generate/cancel`,
        { method: "POST" }
      ),
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
      `/api/jobs/${jobId}/chapters/${chapter}/export?format=${format}`,
  },

  health: {
    get: () => request<HealthResponse>("/api/health"),
  },
};

/**
 * Subscribe to the SSE generation stream. Yields parsed event dicts.
 * Pass an `AbortSignal` to close the stream.
 */
export function streamGeneration(
  jobId: string,
  signal?: AbortSignal
): AsyncGenerator<Record<string, unknown>> {
  const url = `${API_BASE}/api/jobs/${jobId}/generate/stream`;
  return (async function* () {
    const res = await fetch(url, {
      headers: { Accept: "text/event-stream" },
      signal,
    });
    if (!res.ok || !res.body) {
      throw new Error(`Stream failed: ${res.status}`);
    }
    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    try {
      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const events = buffer.split("\n\n");
        buffer = events.pop() || "";
        for (const evt of events) {
          const line = evt.split("\n").find((l) => l.startsWith("data:"));
          if (!line) continue;
          const payload = line.slice(5).trim();
          if (!payload) continue;
          try {
            yield JSON.parse(payload);
          } catch {
            // ignore malformed
          }
        }
      }
    } finally {
      reader.releaseLock();
    }
  })();
}
