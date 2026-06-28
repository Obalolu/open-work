export interface Job {
  id: string;
  topic: string;
  paper_type: string;
  citation_style: string;
  target_audience: string;
  status: string;
  created_at: string;
  updated_at: string;
  chapter_count: number;
  total_words: number;
}

export interface JobDetail extends Job {
  config_json: string;
  chapters: ChapterSummary[];
}

export interface ChapterSummary {
  id: number;
  chapter_number: number;
  name: string;
  status: string;
  word_count: number;
  ai_score: number | null;
  style_score: number | null;
}

export interface ChapterDetail extends ChapterSummary {
  content: string;
  created_at: string;
  updated_at: string;
}

export interface GenerateRequest {
  chapters: number[];
  style?: string;
  skip_humanize?: boolean;
  skip_review?: boolean;
}

export interface GenerationStatus {
  run_id: string;
  job_id: string;
  phase: string;
  progress: number;
  message: string;
  chapter_status: ChapterGenStatus[];
}

export interface ChapterGenStatus {
  number: number;
  name: string;
  status: string;
  progress: number;
}

export interface Source {
  paper_id: string;
  title: string;
  authors: string[];
  year: number | null;
  venue: string;
  abstract_summary: string;
  paper_url: string;
  doi: string;
  source_type: string;
  citation_count: number;
  confidence: number;
}

export interface LLMConfig {
  provider: string;
  model: string;
  base_url: string;
  temperature: number;
  api_key_set: boolean;
}

export interface ResearchConfig {
  semantic_scholar_api_key_set: boolean;
  openalex_api_key_set: boolean;
  max_papers_per_query: number;
}

export interface AppConfig {
  llm: LLMConfig;
  research: ResearchConfig;
}

export interface ProxyPoolStatus {
  total: number;
  working: number;
  failed: number;
  last_refresh: string | null;
}

export interface DashboardStats {
  total_jobs: number;
  total_chapters: number;
  total_words: number;
  avg_ai_score: number | null;
  jobs_by_status: Record<string, number>;
}
