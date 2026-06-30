"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useStore } from "@/stores/jobStore";
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
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/Card";
import { Empty } from "@/components/ui/Empty";
import { Skeleton } from "@/components/ui/Skeleton";
import { motion } from "framer-motion";
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
} from "lucide-react";

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

export default function JobsPage() {
  const { jobs, loading, error, fetchJobs } = useStore();
  const [showCreate, setShowCreate] = useState(false);
  const [search, setSearch] = useState("");
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
    const prev = jobs;
    setDeleteId(null);
    await useStore.getState().deleteJob(id);
    useStore.setState({
      jobs: prev.filter((j) => j.id !== id),
    });
    toast.success("Job deleted");
  };

  const updateChapter = (index: number, field: keyof ChapterInput, value: string) => {
    setChapters((prev) =>
      prev.map((ch, i) => (i === index ? { ...ch, [field]: value } : ch))
    );
  };

  const addChapter = () => {
    setChapters((prev) => [...prev, { name: "", template: "" }]);
  };

  const removeChapter = (index: number) => {
    setChapters((prev) => prev.filter((_, i) => i !== index));
  };

  const updateResearchQuery = (index: number, value: string) => {
    setResearchQueries((prev) =>
      prev.map((q, i) => (i === index ? value : q))
    );
  };

  const addResearchQuery = () => {
    setResearchQueries((prev) => [...prev, ""]);
  };

  const removeResearchQuery = (index: number) => {
    setResearchQueries((prev) => prev.filter((_, i) => i !== index));
  };

  const filtered = jobs.filter((j) =>
    j.topic.toLowerCase().includes(search.toLowerCase())
  );

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

      {showCreate && (
        <Card>
          <CardHeader className="flex-row items-center justify-between space-y-0">
            <div>
              <CardTitle>Create new job</CardTitle>
              <CardDescription>Set up a new research paper to generate</CardDescription>
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
                  onClick={addResearchQuery}
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
                      onChange={(e) => updateResearchQuery(i, e.target.value)}
                      placeholder={`Research query ${i + 1}`}
                    />
                    {researchQueries.length > 1 && (
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => removeResearchQuery(i)}
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
                  onClick={addChapter}
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
                      onChange={(e) => updateChapter(i, "name", e.target.value)}
                      placeholder="Chapter name"
                    />
                    <Select
                      value={ch.template}
                      onValueChange={(v) => updateChapter(i, "template", v)}
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
                        onClick={() => removeChapter(i)}
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
      )}

      {jobs.length > 0 && (
        <div className="relative max-w-sm">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search jobs..."
            className="pl-9"
          />
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
      ) : (
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
                  <th className="hidden px-5 py-3 text-left text-2xs font-semibold uppercase tracking-wider text-muted-foreground md:table-cell">
                    Chapters
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
                {filtered.map((job) => (
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
                    <td className="hidden px-5 py-4 text-sm text-muted-foreground md:table-cell">
                      {job.chapter_count}
                    </td>
                    <td className="px-5 py-4">
                      <StatusBadge status={job.status} size="sm" />
                    </td>
                    <td className="px-5 py-4">
                      <div className="flex items-center justify-end gap-1">
                        {deleteId === job.id ? (
                          <>
                            <Button
                              size="sm"
                              variant="danger"
                              onClick={() => handleDelete(job.id)}
                            >
                              Confirm
                            </Button>
                            <Button
                              size="sm"
                              variant="ghost"
                              onClick={() => setDeleteId(null)}
                            >
                              Cancel
                            </Button>
                          </>
                        ) : (
                          <>
                            <Button
                              variant="ghost"
                              size="icon"
                              asChild
                              aria-label={`View ${job.topic}`}
                            >
                              <Link href={`/jobs/${job.id}`}>
                                <Play />
                              </Link>
                            </Button>
                            <Button
                              variant="ghost"
                              size="icon"
                              onClick={() => setDeleteId(job.id)}
                              aria-label={`Delete ${job.topic}`}
                              className="text-muted-foreground hover:text-danger"
                            >
                              <Trash2 />
                            </Button>
                          </>
                        )}
                      </div>
                    </td>
                  </motion.tr>
                ))}
              </tbody>
            </table>
          </div>
          {filtered.length === 0 && search && (
            <div className="border-t border-border p-8 text-center text-sm text-muted-foreground">
              No jobs match &ldquo;{search}&rdquo;.
            </div>
          )}
        </Card>
      )}
    </div>
  );
}

function formatError(e: unknown): string {
  if (e instanceof Error) return e.message;
  return String(e);
}
