import { create } from "zustand";
import type { Job, JobDetail, GenerationStatus } from "@/lib/types";
import { api } from "@/lib/api";

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
  }) => Promise<Job>;
  deleteJob: (id: string) => Promise<void>;
  startGeneration: (
    jobId: string,
    chapters: number[]
  ) => Promise<void>;
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
      set({ error: String(e), loading: false });
    }
  },

  fetchJob: async (id: string) => {
    set({ loading: true, error: null });
    try {
      const job = await api.jobs.get(id);
      set({ currentJob: job, loading: false });
    } catch (e: unknown) {
      set({ error: String(e), loading: false });
    }
  },

  createJob: async (data) => {
    set({ loading: true, error: null });
    try {
      const job = await api.jobs.create(data);
      set((s) => ({ jobs: [job, ...s.jobs], loading: false }));
      return job;
    } catch (e: unknown) {
      set({ error: String(e), loading: false });
      throw e;
    }
  },

  deleteJob: async (id: string) => {
    set({ loading: true, error: null });
    try {
      await api.jobs.delete(id);
      set((s) => ({
        jobs: s.jobs.filter((j) => j.id !== id),
        loading: false,
      }));
    } catch (e: unknown) {
      set({ error: String(e), loading: false });
    }
  },

  startGeneration: async (jobId: string, chapters: number[]) => {
    set({ loading: true, error: null });
    try {
      await api.generate.start(jobId, { chapters });
      set({ loading: false });
    } catch (e: unknown) {
      set({ error: String(e), loading: false });
    }
  },

  pollGenerationStatus: async (jobId: string) => {
    const status = await api.generate.status(jobId);
    set({ generationStatus: status });
    return status;
  },

  clearError: () => set({ error: null }),
}));
