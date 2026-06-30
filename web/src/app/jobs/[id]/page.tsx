"use client";

import { useEffect, useState, useCallback } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { useStore } from "@/stores/jobStore";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { StatCard } from "@/components/ui/StatCard";
import { Button } from "@/components/ui/Button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/Card";
import { Input } from "@/components/ui/Input";
import { Label } from "@/components/ui/Label";
import { Checkbox } from "@/components/ui/Checkbox";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/Select";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/Dialog";
import { Skeleton } from "@/components/ui/Skeleton";
import { toast } from "sonner";
import type { JobDetail } from "@/lib/types";
import { GenerationStream } from "@/components/generation/GenerationStream";
import {
  ArrowLeft,
  Play,
  FileText,
  BookOpen,
  BarChart3,
  AlertTriangle,
  Edit,
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

export default function JobDetailPage() {
  const params = useParams();
  const jobId = params.id as string;
  const { currentJob, fetchJob, startGeneration, updateJob } = useStore();
  const [generating, setGenerating] = useState(false);
  const [notFound, setNotFound] = useState(false);
  const [style, setStyle] = useState("academic_balanced.yaml");
  const [formats, setFormats] = useState<string[]>(["md"]);
  const [skipHumanize, setSkipHumanize] = useState(false);
  const [skipReview, setSkipReview] = useState(false);
  const [selectedChapters, setSelectedChapters] = useState<Set<number>>(new Set());

  const [isEditing, setIsEditing] = useState(false);
  const [editForm, setEditForm] = useState<
    | (Partial<Omit<JobDetail, "chapters">> & {
        chapters: { name: string; template: string }[];
        research_queries: string[];
      })
    | null
  >(null);
  const [saving, setSaving] = useState(false);

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
    if (currentJob && selectedChapters.size === 0) {
      setSelectedChapters(new Set(currentJob.chapters.map((ch) => ch.chapter_number)));
    }
  }, [currentJob, selectedChapters.size]);

  const handleGenerate = useCallback(
    async (chapterNums?: number[]) => {
      if (!currentJob) return;
      const chapters = chapterNums || Array.from(selectedChapters);
      if (chapters.length === 0) {
        toast.error("Select at least one chapter");
        return;
      }
      setGenerating(true);
      try {
        await startGeneration(jobId, chapters, {
          style,
          formats,
          skip_humanize: skipHumanize,
          skip_review: skipReview,
        });
        toast.success("Generation started", {
          description: `${chapters.length} chapter${chapters.length === 1 ? "" : "s"} queued`,
        });
      } catch (e) {
        toast.error("Failed to start generation", {
          description: e instanceof Error ? e.message : String(e),
        });
      }
      setGenerating(false);
    },
    [currentJob, selectedChapters, jobId, startGeneration, style, formats, skipHumanize, skipReview]
  );

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
      toast.success("Job updated");
    } catch (e) {
      toast.error("Failed to update job", {
        description: e instanceof Error ? e.message : String(e),
      });
    }
    setSaving(false);
  };

  if (notFound || (!currentJob && !useStore.getState().loading)) {
    return (
      <div className="flex flex-col items-center justify-center py-20 text-center">
        <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-warning-soft text-warning">
          <AlertTriangle className="h-6 w-6" />
        </div>
        <p className="mt-4 text-sm text-muted-foreground">Job not found</p>
        <Button variant="link" asChild className="mt-2">
          <Link href="/jobs">Back to jobs</Link>
        </Button>
      </div>
    );
  }

  if (!currentJob) {
    return (
      <div className="space-y-6">
        <div className="flex items-center gap-3">
          <Skeleton className="h-8 w-8" />
          <div className="flex-1 space-y-2">
            <Skeleton className="h-6 w-1/3" />
            <Skeleton className="h-3 w-1/5" />
          </div>
        </div>
        <div className="grid gap-4 sm:grid-cols-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <Skeleton key={i} className="h-24" />
          ))}
        </div>
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

  const isGenerating = currentJob.status === "generating";

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div className="flex min-w-0 items-start gap-3">
          <Button variant="ghost" size="icon" asChild>
            <Link href="/jobs" aria-label="Back to jobs">
              <ArrowLeft />
            </Link>
          </Button>
          <div className="min-w-0 flex-1">
            <h1 className="truncate text-2xl font-semibold tracking-tight text-foreground">
              {currentJob.topic}
            </h1>
            <div className="mt-1 flex flex-wrap items-center gap-2 text-sm text-muted-foreground">
              <span>{currentJob.paper_type.replace(/_/g, " ")}</span>
              <span className="text-muted-foreground/50">·</span>
              <span>{currentJob.citation_style.toUpperCase()}</span>
              <span className="text-muted-foreground/50">·</span>
              <span>{currentJob.target_audience.replace(/_/g, " ")}</span>
            </div>
          </div>
        </div>
        <div className="flex shrink-0 gap-2">
          <Button variant="outline" onClick={startEdit}>
            <Edit />
            Edit
          </Button>
          <Button
            onClick={() => handleGenerate()}
            disabled={generating || isGenerating || selectedChapters.size === 0}
            loading={generating}
          >
            {!generating && !isGenerating && <Play />}
            {generating
              ? "Starting…"
              : isGenerating
                ? "Generating…"
                : `Generate ${selectedChapters.size || ""}`.trim()}
          </Button>
        </div>
      </div>

      {isGenerating && (
        <GenerationStream
          jobId={jobId}
          jobTopic={currentJob.topic}
          onComplete={() => {
            fetchJob(jobId);
            toast.success("Generation complete", {
              description: currentJob.topic,
            });
          }}
          onCancel={() => fetchJob(jobId)}
        />
      )}

      <Card>
        <CardHeader>
          <CardTitle>Generation options</CardTitle>
          <CardDescription>Style, output formats, and pipeline toggles</CardDescription>
        </CardHeader>
        <CardContent className="grid gap-6 sm:grid-cols-2">
          <div className="space-y-2">
            <Label>Style template</Label>
            <Select value={style} onValueChange={setStyle}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {STYLE_OPTIONS.map((s) => (
                  <SelectItem key={s.value} value={s.value}>
                    {s.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-2">
            <Label>Output formats</Label>
            <div className="flex flex-wrap gap-3 pt-1">
              {FORMAT_OPTIONS.map((fmt) => (
                <label key={fmt.value} className="flex items-center gap-2 text-sm">
                  <Checkbox
                    checked={formats.includes(fmt.value)}
                    onCheckedChange={() => toggleFormat(fmt.value)}
                  />
                  {fmt.label}
                </label>
              ))}
            </div>
          </div>
          <div className="flex flex-wrap gap-6 sm:col-span-2">
            <label className="flex items-center gap-2 text-sm">
              <Checkbox
                checked={skipReview}
                onCheckedChange={(c) => setSkipReview(!!c)}
              />
              Skip review
            </label>
            <label className="flex items-center gap-2 text-sm">
              <Checkbox
                checked={skipHumanize}
                onCheckedChange={(c) => setSkipHumanize(!!c)}
              />
              Skip humanize
            </label>
          </div>
        </CardContent>
      </Card>

      <div className="grid gap-4 sm:grid-cols-3">
        <StatCard
          icon={<FileText className="h-4 w-4" />}
          label="Chapters"
          value={chapters.length}
        />
        <StatCard
          icon={<BookOpen className="h-4 w-4" />}
          label="Total words"
          value={chapters.reduce((sum, ch) => sum + ch.word_count, 0).toLocaleString()}
        />
        <StatCard
          icon={<BarChart3 className="h-4 w-4" />}
          label="Avg AI score"
          value={avgAiScore}
        />
      </div>

      <div>
        <h3 className="mb-3 text-base font-semibold text-foreground">Chapters</h3>
        <Card className="divide-y divide-border">
          {chapters.map((ch) => (
            <div
              key={ch.chapter_number}
              className="flex items-center justify-between gap-3 p-4 transition-colors first:rounded-t-lg last:rounded-b-lg hover:bg-muted/30"
            >
              <div className="flex min-w-0 items-center gap-3">
                <Checkbox
                  checked={selectedChapters.has(ch.chapter_number)}
                  onCheckedChange={() => toggleChapter(ch.chapter_number)}
                  aria-label={`Select chapter ${ch.chapter_number}`}
                />
                <Link href={`/editor/${jobId}/${ch.chapter_number}`} className="min-w-0">
                  <p className="truncate text-sm font-medium text-foreground hover:text-primary">
                    Chapter {ch.chapter_number}: {ch.name}
                  </p>
                  <div className="mt-1 flex items-center gap-3 text-2xs text-muted-foreground">
                    <span>{ch.word_count.toLocaleString()} words</span>
                    {ch.ai_score !== null && (
                      <span
                        className={
                          ch.ai_score < 50 ? "text-success" : "text-warning"
                        }
                      >
                        AI: {ch.ai_score.toFixed(1)}
                      </span>
                    )}
                  </div>
                </Link>
              </div>
              <div className="flex shrink-0 items-center gap-2">
                <StatusBadge status={ch.status} size="sm" />
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={() => handleGenerate([ch.chapter_number])}
                  disabled={generating || isGenerating}
                  className="text-primary hover:bg-primary/10 hover:text-primary"
                >
                  <Play />
                  Generate
                </Button>
              </div>
            </div>
          ))}
        </Card>
      </div>

      <Dialog open={isEditing} onOpenChange={setIsEditing}>
        <DialogContent size="lg">
          {editForm && (
            <>
              <DialogHeader>
                <DialogTitle>Edit job</DialogTitle>
                <DialogDescription>
                  Update the job configuration. Existing generated chapters are not affected.
                </DialogDescription>
              </DialogHeader>
              <div className="space-y-4">
                <div className="space-y-2">
                  <Label>Topic</Label>
                  <Input
                    value={editForm.topic || ""}
                    onChange={(e) =>
                      setEditForm({ ...editForm, topic: e.target.value })
                    }
                  />
                </div>
                <div className="grid gap-4 sm:grid-cols-3">
                  <div className="space-y-2">
                    <Label>Paper type</Label>
                    <Select
                      value={editForm.paper_type}
                      onValueChange={(v) =>
                        setEditForm({ ...editForm, paper_type: v })
                      }
                    >
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="literature_review">Literature Review</SelectItem>
                        <SelectItem value="empirical_study">Empirical Study</SelectItem>
                        <SelectItem value="theoretical">Theoretical</SelectItem>
                        <SelectItem value="mixed_methods">Mixed Methods</SelectItem>
                        <SelectItem value="technical_report">Technical Report</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="space-y-2">
                    <Label>Citation style</Label>
                    <Select
                      value={editForm.citation_style}
                      onValueChange={(v) =>
                        setEditForm({ ...editForm, citation_style: v })
                      }
                    >
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="apa">APA</SelectItem>
                        <SelectItem value="mla">MLA</SelectItem>
                        <SelectItem value="chicago">Chicago</SelectItem>
                        <SelectItem value="ieee">IEEE</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="space-y-2">
                    <Label>Target audience</Label>
                    <Select
                      value={editForm.target_audience}
                      onValueChange={(v) =>
                        setEditForm({ ...editForm, target_audience: v })
                      }
                    >
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="graduate_students">Graduate Students</SelectItem>
                        <SelectItem value="undergraduate">Undergraduate</SelectItem>
                        <SelectItem value="professionals">Professionals</SelectItem>
                        <SelectItem value="general">General</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>
                <div className="space-y-2">
                  <Label>Research queries</Label>
                  {editForm.research_queries.map((q, i) => (
                    <div key={i} className="flex gap-2">
                      <Input
                        value={q}
                        onChange={(e) => {
                          const queries = [...editForm.research_queries];
                          queries[i] = e.target.value;
                          setEditForm({ ...editForm, research_queries: queries });
                        }}
                      />
                      {editForm.research_queries.length > 1 && (
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => {
                            const queries = editForm.research_queries.filter(
                              (_, j) => j !== i
                            );
                            setEditForm({ ...editForm, research_queries: queries });
                          }}
                          aria-label={`Remove query ${i + 1}`}
                        >
                          <X />
                        </Button>
                      )}
                    </div>
                  ))}
                </div>
              </div>
              <DialogFooter>
                <Button
                  variant="ghost"
                  onClick={() => setIsEditing(false)}
                  disabled={saving}
                >
                  Cancel
                </Button>
                <Button onClick={saveEdit} loading={saving}>
                  Save changes
                </Button>
              </DialogFooter>
            </>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
