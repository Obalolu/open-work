"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useStore } from "@/stores/jobStore";
import { api } from "@/lib/api";
import { FileText, Plus, Trash2, Play } from "lucide-react";

export default function JobsPage() {
  const { jobs, fetchJobs, deleteJob } = useStore();
  const [showCreate, setShowCreate] = useState(false);
  const [topic, setTopic] = useState("");
  const [paperType, setPaperType] = useState("literature_review");
  const [creating, setCreating] = useState(false);

  useEffect(() => {
    fetchJobs();
  }, [fetchJobs]);

  const handleCreate = async () => {
    if (!topic.trim()) return;
    setCreating(true);
    try {
      await api.jobs.create({
        topic: topic.trim(),
        paper_type: paperType,
      });
      setTopic("");
      setShowCreate(false);
      fetchJobs();
    } catch (e) {
      alert(String(e));
    }
    setCreating(false);
  };

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

      {showCreate && (
        <div className="bg-white rounded-xl border border-slate-200 p-6 space-y-4">
          <h3 className="font-semibold text-slate-800">Create New Job</h3>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">
              Topic
            </label>
            <input
              type="text"
              value={topic}
              onChange={(e) => setTopic(e.target.value)}
              placeholder="e.g., Impact of AI on Healthcare Diagnostics"
              className="w-full px-4 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">
              Paper Type
            </label>
            <select
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
          <table className="w-full">
            <thead>
              <tr className="border-b border-slate-200 bg-slate-50">
                <th className="text-left px-6 py-3 text-xs font-semibold text-slate-500 uppercase">
                  Topic
                </th>
                <th className="text-left px-6 py-3 text-xs font-semibold text-slate-500 uppercase">
                  Type
                </th>
                <th className="text-left px-6 py-3 text-xs font-semibold text-slate-500 uppercase">
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
                    <p className="text-xs text-slate-400 mt-0.5">
                      {job.id}
                    </p>
                  </td>
                  <td className="px-6 py-4 text-sm text-slate-600">
                    {job.paper_type.replace(/_/g, " ")}
                  </td>
                  <td className="px-6 py-4 text-sm text-slate-600">
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
                        title="View"
                      >
                        <Play className="w-4 h-4" />
                      </Link>
                      <button
                        onClick={() => {
                          if (confirm("Delete this job?")) {
                            deleteJob(job.id);
                          }
                        }}
                        className="p-2 text-slate-400 hover:text-red-600 rounded-lg hover:bg-red-50"
                        title="Delete"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
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
