"use client";

import { useEffect, useState, useCallback } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { useStore } from "@/stores/jobStore";
import { usePolling } from "@/hooks/usePolling";
import { api } from "@/lib/api";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { StatCard } from "@/components/ui/StatCard";
import type { GenerationStatus, JobDetail } from "@/lib/types";
import {
  ArrowLeft,
  Play,
  FileText,
  BookOpen,
  BarChart3,
  Loader2,
  AlertTriangle,
  Settings,
  ChevronDown,
  ChevronUp,
  Edit,
  Save,
  X,
} from "lucide-react";

const STYLE_OPTIONS = [
  { value: "academic_balanced.yaml", label: "Academic Balanced" },
  { value: "academic_formal.yaml", label: "Academic Formal" },
  { value: "narrative.yaml", label: "Narrative" },
];

const FORMAT_OPTIONS = [
  { value: "md", label: "Markdown" },
  { value: "docx", label: "DOCX" },
  { value: "pdf", label: "PDF" },
];

const CHAPTER_TEMPLATES = [
  { value: "", label: "No template" },
  { value: "chapter_1.yaml", label: "Introduction" },
  { value: "chapter_2.yaml", label: "Literature Review" },
  { value: "chapter_3.yaml", label: "Methodology" },
];

export default function JobDetailPage() {
  const params = useParams();
  const jobId = params.id as string;
  const { currentJob, fetchJob, startGeneration, updateJob } = useStore();
  const [generating, setGenerating] = useState(false);
  const [notFound, setNotFound] = useState(false);
  const [genError, setGenError] = useState<string | null>(null);
  const [showOptions, setShowOptions] = useState(false);
  const [style, setStyle] = useState("academic_balanced.yaml");
  const [formats, setFormats] = useState<string[]>(["md"]);
  const [skipHumanize, setSkipHumanize] = useState(false);
  const [skipReview, setSkipReview] = useState(false);
  const [selectedChapters, setSelectedChapters] = useState<Set<number>>(new Set());

  // Editing state
  const [isEditing, setIsEditing] = useState(false);
  const [editForm, setEditForm] = useState<
    | (Partial<Omit<JobDetail, "chapters">> & {
        chapters: { name: string; template: string }[];
        research_queries: string[];
      })
    | null
  >(null);
  const [saving, setSaving] = useState(false);

  const pollFn = useCallback((id: string) => api.generate.status(id), []);
  const { status: pollStatus, isPolling, startPolling } = usePolling(jobId, pollFn, 2000);

  useEffect(() => {
    const load = async () => {
      await fetchJob(jobId);
      const state = useStore.getState();
      if (state.error && !state.currentJob) {
        setNotFound(true);
      }
    };
    load();
  }, [jobId, fetchJob]);

  useEffect(() => {
    if (currentJob?.status === "generating") {
      startPolling();
    }
  }, [currentJob?.status, startPolling]);

  useEffect(() => {
    if (pollStatus?.phase === "complete" || pollStatus?.phase === "error") {
      fetchJob(jobId);
    }
  }, [pollStatus?.phase, jobId, fetchJob]);

  useEffect(() => {
    if (currentJob && selectedChapters.size === 0) {
      setSelectedChapters(new Set(currentJob.chapters.map((ch) => ch.chapter_number)));
    }
  }, [currentJob]);

  const handleGenerate = async (chapterNums?: number[]) => {
    if (!currentJob) return;
    const chapters = chapterNums || Array.from(selectedChapters);
    if (chapters.length === 0) {
      setGenError("Select at least one chapter");
      return;
    }
    setGenerating(true);
    setGenError(null);
    try {
      await startGeneration(jobId, chapters, {
        style,
        formats,
        skip_humanize: skipHumanize,
        skip_review: skipReview,
      });
      startPolling();
    } catch (e) {
      setGenError(e instanceof Error ? e.message : String(e));
    }
    setGenerating(false);
  };

  const toggleChapter = (num: number) => {
    setSelectedChapters((prev) => {
      const next = new Set(prev);
      if (next.has(num)) next.delete(num);
      else next.add(num);
      return next;
    });
  };

  const toggleFormat = (fmt: string) => {
    setFormats((prev) =>
      prev.includes(fmt) ? prev.filter((f) => f !== fmt) : [...prev, fmt]
    );
  };

  const startEdit = () => {
    if (!currentJob) return;
    const config = JSON.parse(currentJob.config_json || "{}");
    setEditForm({
      topic: currentJob.topic,
      paper_type: currentJob.paper_type,
      citation_style: currentJob.citation_style,
      target_audience: currentJob.target_audience,
      research_queries: config.research_queries || [""],
      chapters: currentJob.chapters.map((ch) => ({
        name: ch.name,
        template: "",
      })),
    });
    setIsEditing(true);
  };

  const saveEdit = async () => {
    if (!currentJob || !editForm) return;
    setSaving(true);
    try {
      await updateJob(jobId, {
        topic: editForm.topic,
        paper_type: editForm.paper_type,
        citation_style: editForm.citation_style,
        target_audience: editForm.target_audience,
        research_queries: editForm.research_queries.filter(Boolean),
        chapters: editForm.chapters.map((ch) => ({
          name: ch.name,
          template: ch.template || undefined,
        })),
      });
      setIsEditing(false);
      fetchJob(jobId);
    } catch (e) {
      setGenError(e instanceof Error ? e.message : String(e));
    }
    setSaving(false);
  };

  const updateEditChapter = (index: number, field: "name" | "template", value: string) => {
    setEditForm((prev) => {
      if (!prev) return prev;
      const chapters = [...prev.chapters];
      chapters[index] = { ...chapters[index], [field]: value };
      return { ...prev, chapters };
    });
  };

  const addEditChapter = () => {
    setEditForm((prev) => {
      if (!prev) return prev;
      return { ...prev, chapters: [...prev.chapters, { name: "", template: "" }] };
    });
  };

  const removeEditChapter = (index: number) => {
    setEditForm((prev) => {
      if (!prev) return prev;
      return { ...prev, chapters: prev.chapters.filter((_, i) => i !== index) };
    });
  };

  const updateEditQuery = (index: number, value: string) => {
    setEditForm((prev) => {
      if (!prev) return prev;
      const queries = [...prev.research_queries];
      queries[index] = value;
      return { ...prev, research_queries: queries };
    });
  };

  const addEditQuery = () => {
    setEditForm((prev) => {
      if (!prev) return prev;
      return { ...prev, research_queries: [...prev.research_queries, ""] };
    });
  };

  const removeEditQuery = (index: number) => {
    setEditForm((prev) => {
      if (!prev) return prev;
      return { ...prev, research_queries: prev.research_queries.filter((_, i) => i !== index) };
    });
  };

  if (notFound || (!currentJob && !useStore.getState().loading)) {
    return (
      <div className="text-center py-12">
        <AlertTriangle className="w-12 h-12 text-amber-400 mx-auto mb-4" />
        <p className="text-slate-500 mb-2">Job not found</p>
        <Link href="/jobs" className="text-blue-600 hover:underline text-sm">
          Back to jobs
        </Link>
      </div>
    );
  }

  if (!currentJob) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-8 h-8 text-blue-500 animate-spin" />
      </div>
    );
  }

  const chapters = currentJob.chapters || [];
  const chaptersWithScores = chapters.filter((ch) => ch.ai_score !== null);
  const avgAiScore =
    chaptersWithScores.length > 0
      ? (
          chaptersWithScores.reduce((sum, ch) => sum + (ch.ai_score || 0), 0) /
          chaptersWithScores.length
        ).toFixed(1)
      : "N/A";

  const errorTraceback = pollStatus?.phase === "error" && pollStatus.message ? pollStatus.message : null;

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row items-start sm:items-center gap-4">
        <Link
          href="/jobs"
          className="p-2 text-slate-400 hover:text-slate-600 rounded-lg hover:bg-slate-100"
          aria-label="Back to jobs"
        >
          <ArrowLeft className="w-5 h-5" />
        </Link>
        <div className="flex-1 min-w-0">
          <h1 className="text-2xl font-bold text-slate-900 truncate">
            {currentJob.topic}
          </h1>
          <p className="text-slate-500 mt-1">
            {currentJob.paper_type.replace(/_/g, " ")} &middot;{" "}
            {currentJob.citation_style.toUpperCase()} &middot;{" "}
            {currentJob.target_audience.replace(/_/g, " ")}
          </p>
        </div>
        <div className="flex gap-2 shrink-0">
          <button
            onClick={startEdit}
            className="flex items-center gap-2 px-4 py-2 border border-slate-300 text-slate-700 rounded-lg text-sm font-medium hover:bg-slate-50"
          >
            <Edit className="w-4 h-4" />
            Edit
          </button>
          <button
            onClick={() => handleGenerate()}
            disabled={generating || isPolling || selectedChapters.size === 0}
            className="flex items-center gap-2 px-5 py-2.5 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
          >
            {generating || isPolling ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                Generating...
              </>
            ) : (
              <>
                <Play className="w-4 h-4" />
                Generate Selected
              </>
            )}
          </button>
        </div>
      </div>

      {genError && (
        <div className="bg-red-50 border border-red-200 rounded-xl p-5" role="alert">
          <p className="font-medium text-red-800">Generation failed to start</p>
          <p className="text-sm text-red-600 mt-1">{genError}</p>
        </div>
      )}

      {isPolling && pollStatus && <GenerationProgress status={pollStatus} />}

      {pollStatus?.phase === "error" && errorTraceback && (
        <div className="bg-red-50 border border-red-200 rounded-xl p-5" role="alert">
          <p className="font-medium text-red-800">Generation failed</p>
          <p className="text-sm text-red-600 mt-1">{pollStatus.message}</p>
          {errorTraceback.includes("Traceback") && (
            <details className="mt-3">
              <summary className="text-xs text-red-700 cursor-pointer">Show traceback</summary>
              <pre className="mt-2 text-xs text-red-800 bg-red-100 p-3 rounded-lg overflow-auto max-h-64">
                {errorTraceback}
              </pre>
            </details>
          )}
        </div>
      )}

      <div className="bg-white rounded-xl border border-slate-200 p-5">
        <button
          onClick={() => setShowOptions(!showOptions)}
          className="flex items-center justify-between w-full"
        >
          <div className="flex items-center gap-2">
            <Settings className="w-4 h-4 text-slate-500" />
            <span className="font-semibold text-slate-800">Generation Options</span>
          </div>
          {showOptions ? <ChevronUp className="w-4 h-4 text-slate-500" /> : <ChevronDown className="w-4 h-4 text-slate-500" />}
        </button>

        {showOptions && (
          <div className="mt-4 grid grid-cols-1 md:grid-cols-2 gap-6 border-t border-slate-100 pt-4">
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-2">Style Template</label>
              <select
                value={style}
                onChange={(e) => setStyle(e.target.value)}
                className="w-full px-4 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                {STYLE_OPTIONS.map((s) => (
                  <option key={s.value} value={s.value}>{s.label}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-2">Output Formats</label>
              <div className="flex gap-3">
                {FORMAT_OPTIONS.map((fmt) => (
                  <label key={fmt.value} className="flex items-center gap-2 text-sm text-slate-700">
                    <input
                      type="checkbox"
                      checked={formats.includes(fmt.value)}
                      onChange={() => toggleFormat(fmt.value)}
                      className="rounded border-slate-300"
                    />
                    {fmt.label}
                  </label>
                ))}
              </div>
            </div>
            <div className="flex gap-6">
              <label className="flex items-center gap-2 text-sm text-slate-700">
                <input
                  type="checkbox"
                  checked={skipReview}
                  onChange={(e) => setSkipReview(e.target.checked)}
                  className="rounded border-slate-300"
                />
                Skip review
              </label>
              <label className="flex items-center gap-2 text-sm text-slate-700">
                <input
                  type="checkbox"
                  checked={skipHumanize}
                  onChange={(e) => setSkipHumanize(e.target.checked)}
                  className="rounded border-slate-300"
                />
                Skip humanize
              </label>
            </div>
          </div>
        )}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <StatCard icon={<FileText className="w-5 h-5 text-blue-500" />} label="Chapters" value={chapters.length} />
        <StatCard
          icon={<BookOpen className="w-5 h-5 text-green-500" />}
          label="Total Words"
          value={chapters.reduce((sum, ch) => sum + ch.word_count, 0).toLocaleString()}
        />
        <StatCard icon={<BarChart3 className="w-5 h-5 text-purple-500" />} label="Avg AI Score" value={avgAiScore} />
      </div>

      <div>
        <h3 className="text-lg font-semibold text-slate-800 mb-4">Chapters</h3>
        <div className="space-y-3">
          {chapters.map((ch) => (
            <div
              key={ch.chapter_number}
              className="block bg-white rounded-xl border border-slate-200 p-5 hover:border-blue-300 hover:shadow-sm transition-all"
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-4">
                  <input
                    type="checkbox"
                    checked={selectedChapters.has(ch.chapter_number)}
                    onChange={() => toggleChapter(ch.chapter_number)}
                    className="rounded border-slate-300"
                    aria-label={`Select chapter ${ch.chapter_number}`}
                  />
                  <Link href={`/editor/${jobId}/${ch.chapter_number}`}>
                    <h4 className="font-semibold text-slate-800 hover:text-blue-600">
                      Chapter {ch.chapter_number}: {ch.name}
                    </h4>
                    <div className="flex items-center gap-4 mt-2 text-sm text-slate-500">
                      <span>{ch.word_count.toLocaleString()} words</span>
                      {ch.ai_score !== null && (
                        <span className={ch.ai_score < 50 ? "text-green-600" : "text-amber-600"}>
                          AI: {ch.ai_score.toFixed(1)}
                        </span>
                      )}
                    </div>
                  </Link>
                </div>
                <div className="flex items-center gap-3">
                  <StatusBadge status={ch.status} />
                  <button
                    onClick={() => handleGenerate([ch.chapter_number])}
                    disabled={generating || isPolling}
                    className="flex items-center gap-1 px-3 py-1.5 text-xs font-medium text-blue-700 bg-blue-50 rounded-lg hover:bg-blue-100 disabled:opacity-50"
                  >
                    <Play className="w-3 h-3" />
                    Generate
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {isEditing && editForm && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-xl max-w-2xl w-full max-h-[90vh] overflow-auto p-6 space-y-6">
            <div className="flex items-center justify-between">
              <h3 className="font-semibold text-slate-800">Edit Job</h3>
              <button onClick={() => setIsEditing(false)} className="p-1 text-slate-400 hover:text-slate-600">
                <X className="w-4 h-4" />
              </button>
            </div>

            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Topic</label>
              <input
                type="text"
                value={editForm.topic}
                onChange={(e) => setEditForm({ ...editForm, topic: e.target.value })}
                className="w-full px-4 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Paper Type</label>
                <select
                  value={editForm.paper_type}
                  onChange={(e) => setEditForm({ ...editForm, paper_type: e.target.value })}
                  className="w-full px-4 py-2 border border-slate-300 rounded-lg text-sm"
                >
                  <option value="literature_review">Literature Review</option>
                  <option value="empirical_study">Empirical Study</option>
                  <option value="theoretical">Theoretical</option>
                  <option value="mixed_methods">Mixed Methods</option>
                  <option value="technical_report">Technical Report</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Citation Style</label>
                <select
                  value={editForm.citation_style}
                  onChange={(e) => setEditForm({ ...editForm, citation_style: e.target.value })}
                  className="w-full px-4 py-2 border border-slate-300 rounded-lg text-sm"
                >
                  <option value="apa">APA</option>
                  <option value="mla">MLA</option>
                  <option value="chicago">Chicago</option>
                  <option value="ieee">IEEE</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Target Audience</label>
                <select
                  value={editForm.target_audience}
                  onChange={(e) => setEditForm({ ...editForm, target_audience: e.target.value })}
                  className="w-full px-4 py-2 border border-slate-300 rounded-lg text-sm"
                >
                  <option value="graduate_students">Graduate Students</option>
                  <option value="undergraduate">Undergraduate</option>
                  <option value="professionals">Professionals</option>
                  <option value="general">General</option>
                </select>
              </div>
            </div>

            <div>
              <div className="flex items-center justify-between mb-2">
                <label className="block text-sm font-medium text-slate-700">Research Queries</label>
                <button onClick={addEditQuery} className="text-xs text-blue-600 hover:text-blue-800">+ Add</button>
              </div>
              <div className="space-y-2">
                {editForm.research_queries.map((q, i) => (
                  <div key={i} className="flex gap-2">
                    <input
                      type="text"
                      value={q}
                      onChange={(e) => updateEditQuery(i, e.target.value)}
                      className="flex-1 px-4 py-2 border border-slate-300 rounded-lg text-sm"
                    />
                    {editForm.research_queries.length > 1 && (
                      <button onClick={() => removeEditQuery(i)} className="p-2 text-slate-400 hover:text-red-600">
                        <X className="w-4 h-4" />
                      </button>
                    )}
                  </div>
                ))}
              </div>
            </div>

            <div>
              <div className="flex items-center justify-between mb-2">
                <label className="block text-sm font-medium text-slate-700">Chapters</label>
                <button onClick={addEditChapter} className="text-xs text-blue-600 hover:text-blue-800">+ Add</button>
              </div>
              <div className="space-y-3">
                {editForm.chapters.map((ch, i) => (
                  <div key={i} className="flex gap-2">
                    <input
                      type="text"
                      value={ch.name}
                      onChange={(e) => updateEditChapter(i, "name", e.target.value)}
                      className="flex-1 px-4 py-2 border border-slate-300 rounded-lg text-sm"
                    />
                    <select
                      value={ch.template}
                      onChange={(e) => updateEditChapter(i, "template", e.target.value)}
                      className="flex-1 px-4 py-2 border border-slate-300 rounded-lg text-sm"
                    >
                      {CHAPTER_TEMPLATES.map((t) => (
                        <option key={t.value} value={t.value}>{t.label}</option>
                      ))}
                    </select>
                    {editForm.chapters.length > 1 && (
                      <button onClick={() => removeEditChapter(i)} className="p-2 text-slate-400 hover:text-red-600">
                        <X className="w-4 h-4" />
                      </button>
                    )}
                  </div>
                ))}
              </div>
            </div>

            <div className="flex gap-3">
              <button
                onClick={saveEdit}
                disabled={saving}
                className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
              >
                <Save className="w-4 h-4" />
                {saving ? "Saving..." : "Save Changes"}
              </button>
              <button onClick={() => setIsEditing(false)} className="px-4 py-2 text-slate-600 hover:text-slate-800 text-sm font-medium">
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function GenerationProgress({ status }: { status: GenerationStatus }) {
  const phaseLabels: Record<string, string> = {
    queued: "Queued",
    starting: "Starting",
    research: "Researching",
    writing: "Writing",
    review: "Reviewing",
    humanize: "Humanizing",
    export: "Exporting",
    complete: "Complete",
    error: "Error",
  };

  return (
    <div className="bg-blue-50 border border-blue-200 rounded-xl p-5">
      <div className="flex items-center gap-3 mb-3">
        <Loader2 className="w-5 h-5 text-blue-600 animate-spin" />
        <span className="font-medium text-blue-800">{phaseLabels[status.phase] || status.phase}</span>
        <span className="text-sm text-blue-600">{status.progress}%</span>
      </div>
      <div className="w-full bg-blue-200 rounded-full h-2 mb-2">
        <div className="bg-blue-600 h-2 rounded-full transition-all" style={{ width: `${status.progress}%` }} />
      </div>
      <p className="text-sm text-blue-600">{status.message}</p>
    </div>
  );
}
