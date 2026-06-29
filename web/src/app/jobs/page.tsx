"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useStore } from "@/stores/jobStore";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { FileText, Plus, Trash2, Play, Loader2, AlertTriangle } from "lucide-react";

export default function JobsPage() {
  const { jobs, loading, error, fetchJobs, deleteJob } = useStore();
  const [showCreate, setShowCreate] = useState(false);
  const [topic, setTopic] = useState("");
  const [paperType, setPaperType] = useState("literature_review");
  const [citationStyle, setCitationStyle] = useState("apa");
  const [targetAudience, setTargetAudience] = useState("graduate_students");
  const [creating, setCreating] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);
  const [deleteId, setDeleteId] = useState<string | null>(null);

  useEffect(() => {
    fetchJobs();
  }, [fetchJobs]);

  const handleCreate = async () => {
    if (!topic.trim()) return;
    setCreating(true);
    setCreateError(null);
    try {
      await useStore.getState().createJob({
        topic: topic.trim(),
        paper_type: paperType,
        citation_style: citationStyle,
        target_audience: targetAudience,
      });
      setTopic("");
      setPaperType("literature_review");
      setCitationStyle("apa");
      setTargetAudience("graduate_students");
      setShowCreate(false);
    } catch (e) {
      setCreateError(formatError(e));
    }
    setCreating(false);
  };

  const handleDelete = async (id: string) => {
    setDeleteId(null);
    await deleteJob(id);
  };

  if (loading && jobs.length === 0) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-8 h-8 text-blue-500 animate-spin" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Jobs</h1>
          <p className="text-slate-500 mt-1">
            Manage your research paper generation jobs
          </p>
        </div>
        <button
          onClick={() => setShowCreate(!showCreate)}
          className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700"
        >
          <Plus className="w-4 h-4" />
          New Job
        </button>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-sm text-red-700 flex items-center gap-2" role="alert">
          <AlertTriangle className="w-4 h-4 shrink-0" />
          {error}
          <button onClick={() => useStore.getState().clearError()} className="ml-auto underline">Dismiss</button>
        </div>
      )}

      {showCreate && (
        <div className="bg-white rounded-xl border border-slate-200 p-6 space-y-4">
          <h3 className="font-semibold text-slate-800">Create New Job</h3>
          {createError && (
            <div className="bg-red-50 border border-red-200 rounded-lg p-3 text-sm text-red-700" role="alert">
              {createError}
            </div>
          )}
          <div>
            <label htmlFor="job-topic" className="block text-sm font-medium text-slate-700 mb-1">
              Topic
            </label>
            <input
              id="job-topic"
              type="text"
              value={topic}
              onChange={(e) => setTopic(e.target.value)}
              placeholder="e.g., Impact of AI on Healthcare Diagnostics"
              className="w-full px-4 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label htmlFor="job-paper-type" className="block text-sm font-medium text-slate-700 mb-1">
                Paper Type
              </label>
              <select
                id="job-paper-type"
                value={paperType}
                onChange={(e) => setPaperType(e.target.value)}
                className="w-full px-4 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="literature_review">Literature Review</option>
                <option value="empirical_study">Empirical Study</option>
                <option value="theoretical">Theoretical</option>
                <option value="mixed_methods">Mixed Methods</option>
                <option value="technical_report">Technical Report</option>
              </select>
            </div>
            <div>
              <label htmlFor="job-citation" className="block text-sm font-medium text-slate-700 mb-1">
                Citation Style
              </label>
              <select
                id="job-citation"
                value={citationStyle}
                onChange={(e) => setCitationStyle(e.target.value)}
                className="w-full px-4 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="apa">APA</option>
                <option value="mla">MLA</option>
                <option value="chicago">Chicago</option>
                <option value="ieee">IEEE</option>
              </select>
            </div>
            <div>
              <label htmlFor="job-audience" className="block text-sm font-medium text-slate-700 mb-1">
                Target Audience
              </label>
              <select
                id="job-audience"
                value={targetAudience}
                onChange={(e) => setTargetAudience(e.target.value)}
                className="w-full px-4 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="graduate_students">Graduate Students</option>
                <option value="undergraduate">Undergraduate</option>
                <option value="professionals">Professionals</option>
                <option value="general">General</option>
              </select>
            </div>
          </div>
          <div className="flex gap-3">
            <button
              onClick={handleCreate}
              disabled={creating || !topic.trim()}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
            >
              {creating ? "Creating..." : "Create Job"}
            </button>
            <button
              onClick={() => setShowCreate(false)}
              className="px-4 py-2 text-slate-600 hover:text-slate-800 text-sm font-medium"
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      {jobs.length === 0 ? (
        <div className="bg-white rounded-xl border border-slate-200 p-12 text-center">
          <FileText className="w-12 h-12 text-slate-300 mx-auto mb-4" />
          <p className="text-slate-500">No jobs found</p>
        </div>
      ) : (
        <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full" aria-label="Research jobs">
              <thead>
                <tr className="border-b border-slate-200 bg-slate-50">
                  <th className="text-left px-6 py-3 text-xs font-semibold text-slate-500 uppercase">
                    Topic
                  </th>
                  <th className="text-left px-6 py-3 text-xs font-semibold text-slate-500 uppercase hidden sm:table-cell">
                    Type
                  </th>
                  <th className="text-left px-6 py-3 text-xs font-semibold text-slate-500 uppercase hidden md:table-cell">
                    Chapters
                  </th>
                  <th className="text-left px-6 py-3 text-xs font-semibold text-slate-500 uppercase">
                    Status
                  </th>
                  <th className="text-right px-6 py-3 text-xs font-semibold text-slate-500 uppercase">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody>
                {jobs.map((job) => (
                  <tr
                    key={job.id}
                    className="border-b border-slate-100 hover:bg-slate-50"
                  >
                    <td className="px-6 py-4">
                      <Link
                        href={`/jobs/${job.id}`}
                        className="font-medium text-slate-800 hover:text-blue-600"
                      >
                        {job.topic.length > 60
                          ? job.topic.slice(0, 60) + "..."
                          : job.topic}
                      </Link>
                      <p className="text-xs text-slate-400 mt-0.5 sm:hidden">
                        {job.paper_type.replace(/_/g, " ")}
                      </p>
                    </td>
                    <td className="px-6 py-4 text-sm text-slate-600 hidden sm:table-cell">
                      {job.paper_type.replace(/_/g, " ")}
                    </td>
                    <td className="px-6 py-4 text-sm text-slate-600 hidden md:table-cell">
                      {job.chapter_count}
                    </td>
                    <td className="px-6 py-4">
                      <StatusBadge status={job.status} />
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex items-center justify-end gap-2">
                        <Link
                          href={`/jobs/${job.id}`}
                          className="p-2 text-slate-400 hover:text-blue-600 rounded-lg hover:bg-blue-50"
                          aria-label={`View ${job.topic}`}
                        >
                          <Play className="w-4 h-4" />
                        </Link>
                        {deleteId === job.id ? (
                          <div className="flex items-center gap-1">
                            <button
                              onClick={() => handleDelete(job.id)}
                              className="px-2 py-1 bg-red-600 text-white text-xs rounded hover:bg-red-700"
                            >
                              Confirm
                            </button>
                            <button
                              onClick={() => setDeleteId(null)}
                              className="px-2 py-1 text-slate-600 text-xs rounded hover:bg-slate-100"
                            >
                              Cancel
                            </button>
                          </div>
                        ) : (
                          <button
                            onClick={() => setDeleteId(job.id)}
                            className="p-2 text-slate-400 hover:text-red-600 rounded-lg hover:bg-red-50"
                            aria-label={`Delete ${job.topic}`}
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}

function formatError(e: unknown): string {
  if (e instanceof Error) return e.message;
  return String(e);
}
