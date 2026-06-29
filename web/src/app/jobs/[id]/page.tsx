"use client";

import { useEffect, useState, useCallback } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { useStore } from "@/stores/jobStore";
import { usePolling } from "@/hooks/usePolling";
import { api } from "@/lib/api";
import type { GenerationStatus } from "@/lib/types";
import {
  ArrowLeft,
  Play,
  FileText,
  BookOpen,
  BarChart3,
  Loader2,
  AlertTriangle,
} from "lucide-react";

export default function JobDetailPage() {
  const params = useParams();
  const jobId = params.id as string;
  const { currentJob, fetchJob, startGeneration } = useStore();
  const [generating, setGenerating] = useState(false);
  const [notFound, setNotFound] = useState(false);

  const pollFn = useCallback(
    (id: string) => api.generate.status(id),
    []
  );

  const { status: pollStatus, isPolling, startPolling, stopPolling } = usePolling(
    jobId,
    pollFn,
    2000
  );

  useEffect(() => {
    const load = async () => {
      try {
        await fetchJob(jobId);
      } catch {
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

  const handleGenerate = async () => {
    if (!currentJob) return;
    setGenerating(true);
    try {
      const chapters = (currentJob.chapters || []).map((ch: { chapter_number: number }) => ch.chapter_number);
      await startGeneration(jobId, chapters);
      startPolling();
    } catch (e) {
      alert(String(e));
    }
    setGenerating(false);
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

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <Link
          href="/jobs"
          className="p-2 text-slate-400 hover:text-slate-600 rounded-lg hover:bg-slate-100"
        >
          <ArrowLeft className="w-5 h-5" />
        </Link>
        <div className="flex-1">
          <h1 className="text-2xl font-bold text-slate-900">
            {currentJob.topic}
          </h1>
          <p className="text-slate-500 mt-1">
            {currentJob.paper_type.replace(/_/g, " ")} &middot;{" "}
            {currentJob.citation_style.toUpperCase()} &middot;{" "}
            {currentJob.target_audience.replace(/_/g, " ")}
          </p>
        </div>
        <button
          onClick={handleGenerate}
          disabled={generating || isPolling}
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
              Generate All
            </>
          )}
        </button>
      </div>

      {isPolling && pollStatus && (
        <GenerationProgress status={pollStatus} />
      )}

      {pollStatus?.phase === "error" && (
        <div className="bg-red-50 border border-red-200 rounded-xl p-5">
          <p className="font-medium text-red-800">Generation failed</p>
          <p className="text-sm text-red-600 mt-1">{pollStatus.message || "Unknown error"}</p>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <StatCard
          icon={<FileText className="w-5 h-5 text-blue-500" />}
          label="Chapters"
          value={currentJob.chapters.length}
        />
        <StatCard
          icon={<BookOpen className="w-5 h-5 text-green-500" />}
          label="Total Words"
          value={(currentJob.chapters || [])
            .reduce((sum: number, ch: { word_count: number }) => sum + ch.word_count, 0)
            .toLocaleString()}
        />
        <StatCard
          icon={<BarChart3 className="w-5 h-5 text-purple-500" />}
          label="Avg AI Score"
          value={
            (currentJob.chapters || []).filter((ch: { ai_score: number | null }) => ch.ai_score !== null).length > 0
              ? (
                  (currentJob.chapters || [])
                    .filter((ch: { ai_score: number | null }) => ch.ai_score !== null)
                    .reduce((sum: number, ch: { ai_score: number | null }) => sum + (ch.ai_score || 0), 0) /
                  (currentJob.chapters || []).filter((ch: { ai_score: number | null }) => ch.ai_score !== null)
                    .length
                ).toFixed(1)
              : "N/A"
          }
        />
      </div>

      <div>
        <h3 className="text-lg font-semibold text-slate-800 mb-4">Chapters</h3>
        <div className="space-y-3">
          {(currentJob.chapters || []).map((ch: { chapter_number: number; name: string; word_count: number; ai_score: number | null; status: string }) => (
            <Link
              key={ch.chapter_number}
              href={`/editor/${jobId}/${ch.chapter_number}`}
              className="block bg-white rounded-xl border border-slate-200 p-5 hover:border-blue-300 hover:shadow-sm transition-all"
            >
              <div className="flex items-center justify-between">
                <div>
                  <h4 className="font-semibold text-slate-800">
                    Chapter {ch.chapter_number}: {ch.name}
                  </h4>
                  <div className="flex items-center gap-4 mt-2 text-sm text-slate-500">
                    <span>{ch.word_count.toLocaleString()} words</span>
                    {ch.ai_score !== null && (
                      <span
                        className={
                          ch.ai_score < 50 ? "text-green-600" : "text-amber-600"
                        }
                      >
                        AI: {ch.ai_score.toFixed(1)}
                      </span>
                    )}
                  </div>
                </div>
                <StatusBadge status={ch.status} />
              </div>
            </Link>
          ))}
        </div>
      </div>
    </div>
  );
}

function StatCard({
  icon,
  label,
  value,
}: {
  icon: React.ReactNode;
  label: string;
  value: number | string;
}) {
  return (
    <div className="bg-white rounded-xl border border-slate-200 p-5">
      <div className="flex items-center gap-3">
        <div className="p-2 bg-slate-50 rounded-lg">{icon}</div>
        <div>
          <p className="text-xl font-bold text-slate-900">{value}</p>
          <p className="text-sm text-slate-500">{label}</p>
        </div>
      </div>
    </div>
  );
}

function StatusBadge({ status }: { status: string }) {
  const colors: Record<string, string> = {
    pending: "bg-slate-100 text-slate-600",
    generating: "bg-blue-100 text-blue-700",
    complete: "bg-green-100 text-green-700",
    error: "bg-red-100 text-red-700",
  };
  return (
    <span
      className={`px-3 py-1 rounded-full text-xs font-medium ${
        colors[status] || colors.pending
      }`}
    >
      {status}
    </span>
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
        <span className="font-medium text-blue-800">
          {phaseLabels[status.phase] || status.phase}
        </span>
        <span className="text-sm text-blue-600">{status.progress}%</span>
      </div>
      <div className="w-full bg-blue-200 rounded-full h-2 mb-2">
        <div
          className="bg-blue-600 h-2 rounded-full transition-all"
          style={{ width: `${status.progress}%` }}
        />
      </div>
      <p className="text-sm text-blue-600">{status.message}</p>
    </div>
  );
}
