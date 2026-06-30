import { create } from "zustand";
import type { Job, JobDetail, GenerationStatus } from "@/lib/types";
import { api } from "@/lib/api";

function formatError(e: unknown): string {
  if (e instanceof Error) return e.message;
  if (typeof e === "object" && e !== null && "detail" in e) {
    return String((e as { detail: unknown }).detail);
  }
  return String(e);
}

interface AppState {
  jobs: Job[];
  currentJob: JobDetail | null;
  generationStatus: GenerationStatus | null;
  loading: boolean;
  error: string | null;

  fetchJobs: () => Promise<void>;
  fetchJob: (id: string) => Promise<void>;
  createJob: (data: {
    topic: string;
    paper_type?: string;
    citation_style?: string;
    target_audience?: string;
    research_queries?: string[];
    chapters?: { name: string; template?: string }[];
  }) => Promise<Job>;
  deleteJob: (id: string) => Promise<void>;
  updateJob: (id: string, data: {
    topic?: string;
    paper_type?: string;
    citation_style?: string;
    target_audience?: string;
    research_queries?: string[];
    chapters?: { name: string; template?: string }[];
  }) => Promise<Job>;
  startGeneration: (jobId: string, chapters: number[], options?: {
    style?: string;
    formats?: string[];
    skip_humanize?: boolean;
    skip_review?: boolean;
  }) => Promise<void>;
  pollGenerationStatus: (jobId: string) => Promise<GenerationStatus>;
  clearError: () => void;
}

export const useStore = create<AppState>((set, get) => ({
  jobs: [],
  currentJob: null,
  generationStatus: null,
  loading: false,
  error: null,

  fetchJobs: async () => {
    set({ loading: true, error: null });
    try {
      const jobs = await api.jobs.list();
      set({ jobs, loading: false });
    } catch (e: unknown) {
      set({ error: formatError(e), loading: false });
    }
  },

  fetchJob: async (id: string) => {
    set({ loading: true, error: null });
    try {
      const job = await api.jobs.get(id);
      set({ currentJob: job, loading: false });
    } catch (e: unknown) {
      set({ error: formatError(e), loading: false });
    }
  },

  createJob: async (data) => {
    set({ loading: true, error: null });
    try {
      const job = await api.jobs.create(data);
      set((s) => ({ jobs: [job, ...s.jobs], loading: false }));
      return job;
    } catch (e: unknown) {
      set({ error: formatError(e), loading: false });
      throw e;
    }
  },

  deleteJob: async (id: string) => {
    set({ error: null });
    try {
      await api.jobs.delete(id);
      set((s) => ({
        jobs: s.jobs.filter((j) => j.id !== id),
        currentJob: s.currentJob?.id === id ? null : s.currentJob,
      }));
    } catch (e: unknown) {
      set({ error: formatError(e) });
    }
  },

  updateJob: async (id, data) => {
    set({ error: null });
    try {
      const job = await api.jobs.update(id, data);
      set((s) => ({
        jobs: s.jobs.map((j) => (j.id === id ? job : j)),
        currentJob: s.currentJob?.id === id ? { ...s.currentJob, ...job } : s.currentJob,
      }));
      return job;
    } catch (e: unknown) {
      set({ error: formatError(e) });
      throw e;
    }
  },

  startGeneration: async (jobId, chapters, options = {}) => {
    set({ error: null });
    try {
      await api.generate.start(jobId, {
        chapters,
        style: options.style,
        formats: options.formats,
        skip_humanize: options.skip_humanize,
        skip_review: options.skip_review,
      });
    } catch (e: unknown) {
      set({ error: formatError(e) });
      throw e;
    }
  },

  pollGenerationStatus: async (jobId: string) => {
    const status = await api.generate.status(jobId);
    set({ generationStatus: status });
    return status;
  },

  clearError: () => set({ error: null }),
}));
