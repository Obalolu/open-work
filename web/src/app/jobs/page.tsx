"use client";

import { useEffect, useState, useMemo } from "react";
import Link from "next/link";
import { motion, AnimatePresence } from "framer-motion";
import { useStore } from "@/stores/jobStore";
import type { Job } from "@/lib/types";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Label } from "@/components/ui/Label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/Select";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";
import { Empty } from "@/components/ui/Empty";
import { Skeleton } from "@/components/ui/Skeleton";
import { ProgressRing } from "@/components/ui/Progress";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/Tooltip";
import { toast } from "sonner";
import {
  FileText,
  Plus,
  Trash2,
  Play,
  AlertTriangle,
  X,
  GripVertical,
  Search,
  LayoutGrid,
  Table as TableIcon,
  Check,
  CalendarClock,
} from "lucide-react";
import { formatDistanceToNow } from "date-fns";
import { useKeyShortcut } from "@/hooks/useKeyShortcut";

const PAPER_TYPES = [
  { value: "literature_review", label: "Literature Review" },
  { value: "empirical_study", label: "Empirical Study" },
  { value: "theoretical", label: "Theoretical" },
  { value: "mixed_methods", label: "Mixed Methods" },
  { value: "technical_report", label: "Technical Report" },
];

const CITATION_STYLES = [
  { value: "apa", label: "APA" },
  { value: "mla", label: "MLA" },
  { value: "chicago", label: "Chicago" },
  { value: "ieee", label: "IEEE" },
];

const TARGET_AUDIENCES = [
  { value: "graduate_students", label: "Graduate Students" },
  { value: "undergraduate", label: "Undergraduate" },
  { value: "professionals", label: "Professionals" },
  { value: "general", label: "General" },
];

const CHAPTER_TEMPLATES = [
  { value: "chapter_1.yaml", label: "Chapter 1: Introduction" },
  { value: "chapter_2.yaml", label: "Chapter 2: Literature Review" },
  { value: "chapter_3.yaml", label: "Chapter 3: Methodology" },
];

interface ChapterInput {
  name: string;
  template: string;
}

type StatusFilter = "all" | "draft" | "generating" | "complete" | "error";
type SortKey = "updated_desc" | "created_desc" | "words_desc" | "topic_asc";
type ViewMode = "table" | "cards";

const STATUS_FILTERS: { value: StatusFilter; label: string }[] = [
  { value: "all", label: "All" },
  { value: "draft", label: "Draft" },
  { value: "generating", label: "Generating" },
  { value: "complete", label: "Complete" },
  { value: "error", label: "Error" },
];

export default function JobsPage() {
  const { jobs, loading, error, fetchJobs } = useStore();
  const [showCreate, setShowCreate] = useState(false);
  const [view, setView] = useState<ViewMode>("table");
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("all");
  const [sort, setSort] = useState<SortKey>("updated_desc");
  const [topic, setTopic] = useState("");
  const [paperType, setPaperType] = useState("literature_review");
  const [citationStyle, setCitationStyle] = useState("apa");
  const [targetAudience, setTargetAudience] = useState("graduate_students");
  const [researchQueries, setResearchQueries] = useState<string[]>([""]);
  const [chapters, setChapters] = useState<ChapterInput[]>([
    { name: "Introduction", template: "chapter_1.yaml" },
    { name: "Literature Review", template: "chapter_2.yaml" },
    { name: "Methodology", template: "chapter_3.yaml" },
  ]);
  const [creating, setCreating] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);
  const [deleteId, setDeleteId] = useState<string | null>(null);

  useEffect(() => {
    fetchJobs();
  }, [fetchJobs]);

  useKeyShortcut("n", () => setShowCreate((v) => !v), { meta: false });

  const resetForm = () => {
    setTopic("");
    setPaperType("literature_review");
    setCitationStyle("apa");
    setTargetAudience("graduate_students");
    setResearchQueries([""]);
    setChapters([
      { name: "Introduction", template: "chapter_1.yaml" },
      { name: "Literature Review", template: "chapter_2.yaml" },
      { name: "Methodology", template: "chapter_3.yaml" },
    ]);
  };

  const handleCreate = async () => {
    if (!topic.trim()) return;
    setCreating(true);
    setCreateError(null);
    try {
      const job = await useStore.getState().createJob({
        topic: topic.trim(),
        paper_type: paperType,
        citation_style: citationStyle,
        target_audience: targetAudience,
        research_queries: researchQueries.map((q) => q.trim()).filter(Boolean),
        chapters: chapters.map((ch) => ({
          name: ch.name.trim(),
          template: ch.template,
        })),
      });
      toast.success("Job created", { description: job.topic });
      resetForm();
      setShowCreate(false);
    } catch (e) {
      setCreateError(formatError(e));
      toast.error("Failed to create job", { description: formatError(e) });
    }
    setCreating(false);
  };

  const handleDelete = async (id: string) => {
    setDeleteId(null);
    await useStore.getState().deleteJob(id);
    toast.success("Job deleted");
  };

  const filtered = useMemo(() => {
    let list = jobs;
    if (search) {
      const s = search.toLowerCase();
      list = list.filter((j) => j.topic.toLowerCase().includes(s));
    }
    if (statusFilter !== "all") {
      list = list.filter((j) => j.status === statusFilter);
    }
    list = [...list];
    list.sort((a, b) => {
      switch (sort) {
        case "created_desc":
          return a.created_at < b.created_at ? 1 : -1;
        case "words_desc":
          return b.total_words - a.total_words;
        case "topic_asc":
          return a.topic.localeCompare(b.topic);
        case "updated_desc":
        default:
          return a.updated_at < b.updated_at ? 1 : -1;
      }
    });
    return list;
  }, [jobs, search, statusFilter, sort]);

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="text-3xl font-semibold tracking-tight text-foreground">
            Jobs
          </h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Manage your research paper generation jobs
          </p>
        </div>
        <Button onClick={() => setShowCreate(!showCreate)}>
          <Plus />
          New Job
          <kbd className="ml-1 hidden rounded border border-primary-foreground/30 bg-primary-foreground/10 px-1 font-mono text-2xs sm:inline-block">
            N
          </kbd>
        </Button>
      </div>

      {error && (
        <div className="flex items-center gap-2 rounded-md border border-danger-soft bg-danger-soft/40 p-3 text-sm text-danger">
          <AlertTriangle className="h-4 w-4 shrink-0" />
          {error}
          <button
            onClick={() => useStore.getState().clearError()}
            className="ml-auto text-xs underline"
          >
            Dismiss
          </button>
        </div>
      )}

      <AnimatePresence>
        {showCreate && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.2 }}
          >
            <Card>
              <CardHeader className="flex-row items-center justify-between space-y-0">
                <div>
                  <CardTitle>Create new job</CardTitle>
                </div>
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={() => {
                    resetForm();
                    setShowCreate(false);
                  }}
                  aria-label="Close"
                >
                  <X />
                </Button>
              </CardHeader>
              <CardContent className="space-y-6">
                {createError && (
                  <div className="rounded-md border border-danger-soft bg-danger-soft/40 p-3 text-sm text-danger">
                    {createError}
                  </div>
                )}

                <div className="space-y-2">
                  <Label htmlFor="job-topic">Topic</Label>
                  <Input
                    id="job-topic"
                    value={topic}
                    onChange={(e) => setTopic(e.target.value)}
                    placeholder="e.g., Impact of AI on Healthcare Diagnostics"
                  />
                </div>

                <div className="grid gap-4 sm:grid-cols-3">
                  <div className="space-y-2">
                    <Label>Paper type</Label>
                    <Select value={paperType} onValueChange={setPaperType}>
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {PAPER_TYPES.map((t) => (
                          <SelectItem key={t.value} value={t.value}>
                            {t.label}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="space-y-2">
                    <Label>Citation style</Label>
                    <Select value={citationStyle} onValueChange={setCitationStyle}>
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {CITATION_STYLES.map((s) => (
                          <SelectItem key={s.value} value={s.value}>
                            {s.label}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="space-y-2">
                    <Label>Target audience</Label>
                    <Select value={targetAudience} onValueChange={setTargetAudience}>
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {TARGET_AUDIENCES.map((a) => (
                          <SelectItem key={a.value} value={a.value}>
                            {a.label}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                </div>

                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <Label>Research queries</Label>
                    <Button
                      variant="link"
                      size="sm"
                      onClick={() => setResearchQueries((p) => [...p, ""])}
                      className="h-auto p-0"
                    >
                      + Add query
                    </Button>
                  </div>
                  <div className="space-y-2">
                    {researchQueries.map((q, i) => (
                      <div key={i} className="flex gap-2">
                        <Input
                          value={q}
                          onChange={(e) => {
                            const next = [...researchQueries];
                            next[i] = e.target.value;
                            setResearchQueries(next);
                          }}
                          placeholder={`Research query ${i + 1}`}
                        />
                        {researchQueries.length > 1 && (
                          <Button
                            variant="ghost"
                            size="icon"
                            onClick={() =>
                              setResearchQueries((p) => p.filter((_, j) => j !== i))
                            }
                            aria-label={`Remove query ${i + 1}`}
                          >
                            <X />
                          </Button>
                        )}
                      </div>
                    ))}
                  </div>
                </div>

                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <Label>Chapters</Label>
                    <Button
                      variant="link"
                      size="sm"
                      onClick={() => setChapters((p) => [...p, { name: "", template: "" }])}
                      className="h-auto p-0"
                    >
                      + Add chapter
                    </Button>
                  </div>
                  <div className="space-y-2">
                    {chapters.map((ch, i) => (
                      <div key={i} className="flex items-center gap-2">
                        <GripVertical className="h-4 w-4 shrink-0 text-muted-foreground/50" />
                        <Input
                          value={ch.name}
                          onChange={(e) => {
                            const next = [...chapters];
                            next[i] = { ...next[i], name: e.target.value };
                            setChapters(next);
                          }}
                          placeholder="Chapter name"
                        />
                        <Select
                          value={ch.template}
                          onValueChange={(v) => {
                            const next = [...chapters];
                            next[i] = { ...next[i], template: v };
                            setChapters(next);
                          }}
                        >
                          <SelectTrigger className="flex-1">
                            <SelectValue placeholder="No template" />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="">No template</SelectItem>
                            {CHAPTER_TEMPLATES.map((t) => (
                              <SelectItem key={t.value} value={t.value}>
                                {t.label}
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                        {chapters.length > 1 && (
                          <Button
                            variant="ghost"
                            size="icon"
                            onClick={() =>
                              setChapters((p) => p.filter((_, j) => j !== i))
                            }
                            aria-label={`Remove chapter ${i + 1}`}
                          >
                            <X />
                          </Button>
                        )}
                      </div>
                    ))}
                  </div>
                </div>

                <div className="flex gap-2 border-t border-border pt-4">
                  <Button
                    onClick={handleCreate}
                    loading={creating}
                    disabled={
                      !topic.trim() || chapters.some((ch) => !ch.name.trim())
                    }
                  >
                    {creating ? "Creating..." : "Create Job"}
                  </Button>
                  <Button
                    variant="ghost"
                    onClick={() => {
                      resetForm();
                      setShowCreate(false);
                    }}
                  >
                    Cancel
                  </Button>
                </div>
              </CardContent>
            </Card>
          </motion.div>
        )}
      </AnimatePresence>

      {jobs.length > 0 && (
        <div className="flex flex-wrap items-center gap-2">
          <div className="relative max-w-sm flex-1">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search jobs..."
              className="pl-9"
            />
          </div>
          <div className="flex items-center gap-1 rounded-md border border-border bg-surface p-0.5">
            {STATUS_FILTERS.map((f) => (
              <button
                key={f.value}
                onClick={() => setStatusFilter(f.value)}
                className={`rounded-sm px-2.5 py-1 text-2xs font-medium transition-colors ${
                  statusFilter === f.value
                    ? "bg-muted text-foreground"
                    : "text-muted-foreground hover:text-foreground"
                }`}
              >
                {f.label}
              </button>
            ))}
          </div>
          <Select value={sort} onValueChange={(v) => setSort(v as SortKey)}>
            <SelectTrigger className="w-44">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="updated_desc">Recently updated</SelectItem>
              <SelectItem value="created_desc">Recently created</SelectItem>
              <SelectItem value="words_desc">Most words</SelectItem>
              <SelectItem value="topic_asc">Topic (A–Z)</SelectItem>
            </SelectContent>
          </Select>
          <div className="ml-auto flex items-center gap-1 rounded-md border border-border bg-surface p-0.5">
            <Tooltip>
              <TooltipTrigger asChild>
                <button
                  onClick={() => setView("table")}
                  className={`rounded-sm p-1.5 ${
                    view === "table"
                      ? "bg-muted text-foreground"
                      : "text-muted-foreground hover:text-foreground"
                  }`}
                  aria-label="Table view"
                >
                  <TableIcon className="h-3.5 w-3.5" />
                </button>
              </TooltipTrigger>
              <TooltipContent>Table</TooltipContent>
            </Tooltip>
            <Tooltip>
              <TooltipTrigger asChild>
                <button
                  onClick={() => setView("cards")}
                  className={`rounded-sm p-1.5 ${
                    view === "cards"
                      ? "bg-muted text-foreground"
                      : "text-muted-foreground hover:text-foreground"
                  }`}
                  aria-label="Cards view"
                >
                  <LayoutGrid className="h-3.5 w-3.5" />
                </button>
              </TooltipTrigger>
              <TooltipContent>Cards</TooltipContent>
            </Tooltip>
          </div>
        </div>
      )}

      {loading && jobs.length === 0 ? (
        <Card>
          <CardContent className="space-y-3 p-3">
            {Array.from({ length: 5 }).map((_, i) => (
              <div key={i} className="flex items-center gap-3 px-3 py-3">
                <Skeleton className="h-10 w-10 rounded-md" />
                <div className="flex-1 space-y-2">
                  <Skeleton className="h-3 w-1/3" />
                  <Skeleton className="h-2 w-1/5" />
                </div>
                <Skeleton className="h-5 w-16 rounded-full" />
              </div>
            ))}
          </CardContent>
        </Card>
      ) : jobs.length === 0 ? (
        <Empty
          variant="bordered"
          icon={<FileText className="h-6 w-6" />}
          title="No jobs yet"
          description="Create your first job to start generating research papers."
          action={
            <Button onClick={() => setShowCreate(true)}>
              <Plus />
              Create your first job
            </Button>
          }
        />
      ) : filtered.length === 0 ? (
        <Empty
          variant="bordered"
          icon={<Search className="h-5 w-5" />}
          title="No matching jobs"
          description="Try a different search or filter."
        />
      ) : view === "table" ? (
        <JobsTable
          jobs={filtered}
          onDelete={(id) => setDeleteId(id)}
          confirmingId={deleteId}
          onConfirmDelete={handleDelete}
          onCancelDelete={() => setDeleteId(null)}
        />
      ) : (
        <JobsCards jobs={filtered} onDelete={(id) => setDeleteId(id)} />
      )}

      {deleteId && (
        <ConfirmDeleteDialog
          job={jobs.find((j) => j.id === deleteId)}
          onCancel={() => setDeleteId(null)}
          onConfirm={() => handleDelete(deleteId)}
        />
      )}
    </div>
  );
}

function JobsTable({
  jobs,
  onDelete,
  confirmingId,
  onConfirmDelete,
  onCancelDelete,
}: {
  jobs: Job[];
  onDelete: (id: string) => void;
  confirmingId: string | null;
  onConfirmDelete: (id: string) => void;
  onCancelDelete: () => void;
}) {
  return (
    <Card className="overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr className="border-b border-border bg-muted/40">
              <th className="px-5 py-3 text-left text-2xs font-semibold uppercase tracking-wider text-muted-foreground">
                Topic
              </th>
              <th className="hidden px-5 py-3 text-left text-2xs font-semibold uppercase tracking-wider text-muted-foreground sm:table-cell">
                Type
              </th>
              <th className="hidden px-5 py-3 text-right text-2xs font-semibold uppercase tracking-wider text-muted-foreground md:table-cell">
                Words
              </th>
              <th className="hidden px-5 py-3 text-left text-2xs font-semibold uppercase tracking-wider text-muted-foreground lg:table-cell">
                Updated
              </th>
              <th className="px-5 py-3 text-left text-2xs font-semibold uppercase tracking-wider text-muted-foreground">
                Status
              </th>
              <th className="px-5 py-3 text-right text-2xs font-semibold uppercase tracking-wider text-muted-foreground">
                Actions
              </th>
            </tr>
          </thead>
          <tbody>
            {jobs.map((job) => (
              <motion.tr
                key={job.id}
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="border-b border-border last:border-0 transition-colors hover:bg-muted/40"
              >
                <td className="px-5 py-4">
                  <Link
                    href={`/jobs/${job.id}`}
                    className="text-sm font-medium text-foreground hover:text-primary"
                  >
                    {job.topic.length > 60
                      ? job.topic.slice(0, 60) + "..."
                      : job.topic}
                  </Link>
                  <p className="text-xs text-muted-foreground sm:hidden">
                    {job.paper_type.replace(/_/g, " ")}
                  </p>
                </td>
                <td className="hidden px-5 py-4 text-sm text-muted-foreground sm:table-cell">
                  {job.paper_type.replace(/_/g, " ")}
                </td>
                <td className="hidden px-5 py-4 text-right text-sm text-muted-foreground md:table-cell">
                  {job.total_words.toLocaleString()}
                </td>
                <td className="hidden px-5 py-4 text-2xs text-muted-foreground lg:table-cell">
                  {job.updated_at
                    ? formatDistanceToNow(new Date(job.updated_at), { addSuffix: true })
                    : "—"}
                </td>
                <td className="px-5 py-4">
                  <StatusBadge status={job.status} size="sm" />
                </td>
                <td className="px-5 py-4">
                  <div className="flex items-center justify-end gap-1">
                    <Button variant="ghost" size="icon" asChild aria-label={`View ${job.topic}`}>
                      <Link href={`/jobs/${job.id}`}>
                        <Play />
                      </Link>
                    </Button>
                    {confirmingId === job.id ? (
                      <>
                        <Button
                          size="sm"
                          variant="danger"
                          onClick={() => onConfirmDelete(job.id)}
                        >
                          Confirm
                        </Button>
                        <Button size="sm" variant="ghost" onClick={onCancelDelete}>
                          Cancel
                        </Button>
                      </>
                    ) : (
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => onDelete(job.id)}
                        aria-label={`Delete ${job.topic}`}
                        className="text-muted-foreground hover:text-danger"
                      >
                        <Trash2 />
                      </Button>
                    )}
                  </div>
                </td>
              </motion.tr>
            ))}
          </tbody>
        </table>
      </div>
    </Card>
  );
}

function JobsCards({
  jobs,
  onDelete,
}: {
  jobs: Job[];
  onDelete: (id: string) => void;
}) {
  return (
    <motion.div
      initial="hidden"
      animate="show"
      variants={{
        hidden: { opacity: 0 },
        show: { opacity: 1, transition: { staggerChildren: 0.04 } },
      }}
      className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3"
    >
      {jobs.map((job) => (
        <motion.div
          key={job.id}
          variants={{ hidden: { opacity: 0, y: 4 }, show: { opacity: 1, y: 0 } }}
        >
          <Card interactive className="group h-full">
            <CardContent className="flex h-full flex-col p-5">
              <div className="flex items-start justify-between gap-3">
                <Link href={`/jobs/${job.id}`} className="min-w-0 flex-1">
                  <p className="line-clamp-2 text-sm font-medium text-foreground group-hover:text-primary">
                    {job.topic}
                  </p>
                </Link>
                <ProgressRing
                  value={
                    job.status === "complete"
                      ? 100
                      : job.status === "generating"
                        ? 50
                        : 0
                  }
                  size={32}
                  strokeWidth={3}
                />
              </div>
              <div className="mt-3 flex flex-wrap items-center gap-2 text-2xs text-muted-foreground">
                <span className="rounded-full bg-muted px-2 py-0.5">
                  {job.paper_type.replace(/_/g, " ")}
                </span>
                <span>{job.chapter_count} ch</span>
                <span>·</span>
                <span>{job.total_words.toLocaleString()} words</span>
              </div>
              <div className="mt-auto flex items-center justify-between pt-4">
                <div className="flex items-center gap-2 text-2xs text-muted-foreground">
                  <CalendarClock className="h-3 w-3" />
                  {job.updated_at
                    ? formatDistanceToNow(new Date(job.updated_at), { addSuffix: true })
                    : "—"}
                </div>
                <div className="flex items-center gap-1">
                  <StatusBadge status={job.status} size="sm" />
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={() => onDelete(job.id)}
                    className="text-muted-foreground opacity-0 transition-opacity hover:text-danger group-hover:opacity-100"
                    aria-label={`Delete ${job.topic}`}
                  >
                    <Trash2 />
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>
        </motion.div>
      ))}
    </motion.div>
  );
}

function ConfirmDeleteDialog({
  job,
  onCancel,
  onConfirm,
}: {
  job?: { id: string; topic: string; total_words?: number };
  onCancel: () => void;
  onConfirm: () => void;
}) {
  const [confirm, setConfirm] = useState("");
  const needsTypedConfirm = (job?.total_words ?? 0) > 1000;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-foreground/40 p-4 backdrop-blur-sm">
      <motion.div
        initial={{ opacity: 0, scale: 0.96 }}
        animate={{ opacity: 1, scale: 1 }}
        className="w-full max-w-sm rounded-lg border border-border bg-surface-elevated p-5 shadow-xl"
      >
        <div className="flex items-start gap-3">
          <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-danger-soft text-danger">
            <AlertTriangle className="h-4 w-4" />
          </div>
          <div className="min-w-0 flex-1">
            <p className="text-sm font-medium text-foreground">Delete job?</p>
            <p className="mt-1 line-clamp-2 text-2xs text-muted-foreground">
              {job?.topic}
            </p>
          </div>
        </div>
        {needsTypedConfirm && (
          <div className="mt-4 space-y-2">
            <p className="text-2xs text-muted-foreground">
              This job has more than 1,000 words. Type{" "}
              <code className="rounded bg-muted px-1">delete</code> to confirm.
            </p>
            <Input
              value={confirm}
              onChange={(e) => setConfirm(e.target.value)}
              placeholder="delete"
            />
          </div>
        )}
        <div className="mt-4 flex justify-end gap-2">
          <Button variant="ghost" onClick={onCancel}>
            Cancel
          </Button>
          <Button
            variant="danger"
            onClick={onConfirm}
            disabled={needsTypedConfirm && confirm !== "delete"}
          >
            <Trash2 />
            Delete
          </Button>
        </div>
      </motion.div>
    </div>
  );
}

function formatError(e: unknown): string {
  if (e instanceof Error) return e.message;
  return String(e);
}

// Suppress unused warnings for icons used in the create form
void Check;
