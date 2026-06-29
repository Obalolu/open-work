"use client";

import { useEffect } from "react";
import Link from "next/link";
import { useStore } from "@/stores/jobStore";
import { FileText, BookOpen, BarChart3, Clock, Loader2 } from "lucide-react";

export default function DashboardPage() {
  const { jobs, loading, error, fetchJobs } = useStore();

  useEffect(() => {
    fetchJobs();
  }, [fetchJobs]);

  if (loading && jobs.length === 0) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-8 h-8 text-blue-500 animate-spin" />
      </div>
    );
  }

  if (error && jobs.length === 0) {
    return (
      <div className="text-center py-12">
        <p className="text-red-500 mb-2">Failed to load data</p>
        <p className="text-sm text-slate-400">{error}</p>
        <button onClick={() => fetchJobs()} className="mt-4 text-sm text-blue-600 hover:underline">Retry</button>
      </div>
    );
  }

  const totalChapters = jobs.reduce((s, j) => s + j.chapter_count, 0);
  const totalWords = jobs.reduce((s, j) => s + j.total_words, 0);
  const completeJobs = jobs.filter((j) => j.status === "complete").length;

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-slate-900">Dashboard</h1>
        <p className="text-slate-500 mt-1">
          Overview of your research paper writing system
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <StatCard
          icon={<FileText className="w-6 h-6 text-blue-500" />}
          label="Total Jobs"
          value={jobs.length}
        />
        <StatCard
          icon={<BookOpen className="w-6 h-6 text-green-500" />}
          label="Chapters Generated"
          value={totalChapters}
        />
        <StatCard
          icon={<BarChart3 className="w-6 h-6 text-purple-500" />}
          label="Total Words"
          value={totalWords.toLocaleString()}
        />
        <StatCard
          icon={<Clock className="w-6 h-6 text-amber-500" />}
          label="Completed"
          value={completeJobs}
        />
      </div>

      <div>
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-slate-800">Recent Jobs</h3>
          <Link
            href="/jobs"
            className="text-sm text-blue-600 hover:text-blue-800 font-medium"
          >
            View all
          </Link>
        </div>

        {jobs.length === 0 ? (
          <div className="bg-white rounded-xl border border-slate-200 p-12 text-center">
            <FileText className="w-12 h-12 text-slate-300 mx-auto mb-4" />
            <p className="text-slate-500 mb-4">No jobs yet</p>
            <Link
              href="/jobs"
              className="inline-flex items-center px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700"
            >
              Create your first job
            </Link>
          </div>
        ) : (
          <div className="space-y-3">
            {jobs.slice(0, 5).map((job) => (
              <Link
                key={job.id}
                href={`/jobs/${job.id}`}
                className="block bg-white rounded-xl border border-slate-200 p-5 hover:border-blue-300 hover:shadow-sm transition-all"
              >
                <div className="flex items-center justify-between">
                  <div>
                    <h4 className="font-semibold text-slate-800">
                      {job.topic}
                    </h4>
                    <p className="text-sm text-slate-500 mt-1">
                      {job.paper_type.replace(/_/g, " ")} &middot;{" "}
                      {job.chapter_count} chapters
                    </p>
                  </div>
                  <StatusBadge status={job.status} />
                </div>
              </Link>
            ))}
          </div>
        )}
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
    <div className="bg-white rounded-xl border border-slate-200 p-6">
      <div className="flex items-center gap-4">
        <div className="p-3 bg-slate-50 rounded-lg">{icon}</div>
        <div>
          <p className="text-2xl font-bold text-slate-900">{value}</p>
          <p className="text-sm text-slate-500">{label}</p>
        </div>
      </div>
    </div>
  );
}

function StatusBadge({ status }: { status: string }) {
  const colors: Record<string, string> = {
    draft: "bg-slate-100 text-slate-600",
    generating: "bg-blue-100 text-blue-700",
    complete: "bg-green-100 text-green-700",
    error: "bg-red-100 text-red-700",
  };
  return (
    <span
      className={`px-3 py-1 rounded-full text-xs font-medium ${
        colors[status] || colors.draft
      }`}
    >
      {status}
    </span>
  );
}
