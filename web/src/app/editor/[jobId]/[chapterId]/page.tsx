"use client";

import { useEffect, useState, useRef } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { api } from "@/lib/api";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/Tabs";
import { Skeleton } from "@/components/ui/Skeleton";
import { Empty } from "@/components/ui/Empty";
import { Input } from "@/components/ui/Input";
import { toast } from "sonner";
import type {
  ChapterDetail,
  ChapterRevisionSummary,
  HumanizerAttemptSummary,
  Source,
} from "@/lib/types";
import { TipTapEditor } from "@/components/editor/TipTapEditor";
import { markdownToHtml } from "@/components/editor/markdownToHtml";
import {
  ArrowLeft,
  Download,
  FileText,
  ExternalLink,
  AlertTriangle,
  Search,
  Quote,
  History,
  GitCompare,
  Sparkles,
  Check,
  Pencil,
} from "lucide-react";
import { cn } from "@/lib/cn";

interface Section {
  title: string;
  body: string;
  id: string;
}

export default function EditorPage() {
  const params = useParams();
  const jobId = params.jobId as string;
  const chapterId = params.chapterId as string;
  const chapterNum = parseInt(chapterId);

  const [chapter, setChapter] = useState<ChapterDetail | null>(null);
  const [sources, setSources] = useState<Source[]>([]);
  const [revisions, setRevisions] = useState<ChapterRevisionSummary[]>([]);
  const [attempts, setAttempts] = useState<HumanizerAttemptSummary[]>([]);
  const [activeTab, setActiveTab] = useState<"content" | "sources" | "revisions">(
    "content"
  );
  const [editing, setEditing] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [sourceSearch, setSourceSearch] = useState("");
  const [activeSection, setActiveSection] = useState<string | null>(null);
  const sectionsRef = useRef<(HTMLElement | null)[]>([]);

  useEffect(() => {
    if (isNaN(chapterNum)) {
      setError("Invalid chapter number");
      setLoading(false);
      return;
    }
    const load = async () => {
      setLoading(true);
      setError(null);
      try {
        const [ch, src, revs, atts] = await Promise.all([
          api.chapters.get(jobId, chapterNum),
          api.research.sources(jobId).catch(() => []),
          api.chapters.revisions(jobId, chapterNum).catch(() => []),
          api.chapters.humanizerAttempts(jobId, chapterNum).catch(() => []),
        ]);
        setChapter(ch);
        setSources(src);
        setRevisions(revs);
        setAttempts(atts);
      } catch (e) {
        setError(e instanceof Error ? e.message : String(e));
      }
      setLoading(false);
    };
    load();
  }, [jobId, chapterNum]);

  // Scroll-spy for floating TOC
  useEffect(() => {
    if (activeTab !== "content") return;
    const observer = new IntersectionObserver(
      (entries) => {
        const visible = entries
          .filter((e) => e.isIntersecting)
          .sort((a, b) => a.boundingClientRect.top - b.boundingClientRect.top);
        if (visible[0]) {
          setActiveSection((visible[0].target as HTMLElement).id);
        }
      },
      { rootMargin: "-30% 0px -50% 0px" }
    );
    sectionsRef.current.forEach((el) => el && observer.observe(el));
    return () => observer.disconnect();
  }, [chapter, activeTab]);

  const handleSave = async (markdown: string) => {
    try {
      const updated = await api.chapters.update(jobId, chapterNum, {
        content: markdown,
        source: "tiptap",
      });
      setChapter(updated);
      // refresh revisions
      const revs = await api.chapters.revisions(jobId, chapterNum);
      setRevisions(revs);
      toast.success("Chapter saved");
    } catch (e) {
      toast.error("Save failed", {
        description: e instanceof Error ? e.message : String(e),
      });
      throw e;
    }
  };

  if (loading) {
    return (
      <div className="space-y-6">
        <div className="flex items-center gap-3">
          <Skeleton className="h-8 w-8" />
          <div className="flex-1 space-y-2">
            <Skeleton className="h-6 w-1/3" />
            <Skeleton className="h-3 w-1/5" />
          </div>
        </div>
        <Skeleton className="h-96" />
      </div>
    );
  }

  if (error || !chapter) {
    return (
      <div className="flex flex-col items-center justify-center py-20 text-center">
        <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-warning-soft text-warning">
          <AlertTriangle className="h-6 w-6" />
        </div>
        <p className="mt-4 text-sm text-muted-foreground">
          {error || "Chapter not found"}
        </p>
        <Button variant="link" asChild className="mt-2">
          <Link href={`/jobs/${jobId}`}>Back to job</Link>
        </Button>
      </div>
    );
  }

  const sections = parseSections(chapter.content || "");
  const filteredSources = sources.filter(
    (s) =>
      s.title.toLowerCase().includes(sourceSearch.toLowerCase()) ||
      s.authors.some((a) =>
        a.toLowerCase().includes(sourceSearch.toLowerCase())
      )
  );
  const initialHtml = markdownToHtml(chapter.content || "");

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div className="flex min-w-0 items-start gap-3">
          <Button variant="ghost" size="icon" asChild>
            <Link href={`/jobs/${jobId}`} aria-label="Back to job">
              <ArrowLeft />
            </Link>
          </Button>
          <div className="min-w-0 flex-1">
            <h1 className="truncate text-2xl font-semibold tracking-tight text-foreground">
              Chapter {chapter.chapter_number}: {chapter.name}
            </h1>
            <p className="mt-1 text-sm text-muted-foreground">
              {chapter.word_count.toLocaleString()} words
            </p>
          </div>
        </div>
        <div className="flex shrink-0 flex-wrap gap-2">
          {chapter.content && !editing && (
            <Button
              variant="outline"
              size="sm"
              onClick={() => setEditing(true)}
            >
              <Pencil />
              Edit
            </Button>
          )}
          {(["md", "docx", "pdf"] as const).map((fmt) => (
            <Button key={fmt} variant="outline" size="sm" asChild>
              <a href={api.export.url(jobId, chapterNum, fmt)} download>
                <Download />
                <span className="uppercase">{fmt}</span>
              </a>
            </Button>
          ))}
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-4">
        <div className="lg:col-span-3">
          <Tabs
            value={activeTab}
            onValueChange={(v) => setActiveTab(v as typeof activeTab)}
          >
            <TabsList>
              <TabsTrigger value="content">Content</TabsTrigger>
              <TabsTrigger value="sources">Sources ({sources.length})</TabsTrigger>
              <TabsTrigger value="revisions">Revisions ({revisions.length})</TabsTrigger>
            </TabsList>

            <TabsContent value="content" className="mt-0">
              <Card>
                <CardContent className="p-6 md:p-8">
                  {chapter.content ? (
                    editing ? (
                      <TipTapEditor
                        key={chapter.id}
                        initialContent={initialHtml}
                        placeholder="Start writing your chapter…"
                        editable
                        onSave={async (md) => {
                          await handleSave(md);
                          setEditing(false);
                        }}
                        onCancel={() => setEditing(false)}
                        autosaveMs={1500}
                      />
                    ) : sections.length > 0 ? (
                      <SectionsView
                        sections={sections}
                        registerRef={(el, i) => {
                          sectionsRef.current[i] = el;
                        }}
                      />
                    ) : (
                      <div
                        className="tiptap-editor prose max-w-none"
                        dangerouslySetInnerHTML={{ __html: initialHtml }}
                      />
                    )
                  ) : (
                    <Empty
                      icon={<FileText className="h-5 w-5" />}
                      title="Empty chapter"
                      description="Generate this chapter from the job page to populate it."
                    />
                  )}
                </CardContent>
              </Card>
            </TabsContent>

            <TabsContent value="sources" className="mt-0">
              <Card>
                <CardContent className="space-y-4 p-5">
                  {sources.length > 0 && (
                    <div className="relative">
                      <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                      <Input
                        value={sourceSearch}
                        onChange={(e) => setSourceSearch(e.target.value)}
                        placeholder="Search sources by title or author…"
                        className="pl-9"
                      />
                    </div>
                  )}
                  {sources.length === 0 ? (
                    <Empty
                      icon={<Quote className="h-5 w-5" />}
                      title="No sources found"
                      description="This job has no research sources yet."
                    />
                  ) : filteredSources.length === 0 ? (
                    <p className="py-6 text-center text-sm text-muted-foreground">
                      No sources match &ldquo;{sourceSearch}&rdquo;.
                    </p>
                  ) : (
                    filteredSources.map((src) => (
                      <div
                        key={src.paper_id}
                        className="rounded-md border border-border p-4 transition-colors hover:border-subtle-foreground/30 hover:bg-muted/30"
                      >
                        <h4 className="text-sm font-medium text-foreground">
                          {src.title}
                        </h4>
                        <p className="mt-1 text-2xs text-muted-foreground">
                          {src.authors.slice(0, 3).join(", ")}
                          {src.authors.length > 3 ? " et al." : ""}
                          {src.year ? ` (${src.year})` : ""}
                        </p>
                        {src.abstract_summary && (
                          <p className="mt-2 line-clamp-2 text-sm text-muted-foreground">
                            {src.abstract_summary}
                          </p>
                        )}
                        <div className="mt-3 flex flex-wrap items-center gap-3 text-2xs text-muted-foreground">
                          {src.venue && (
                            <span className="rounded-full bg-muted px-2 py-0.5">
                              {src.venue}
                            </span>
                          )}
                          {src.citation_count > 0 && (
                            <span>{src.citation_count} citations</span>
                          )}
                          {src.confidence > 0 && (
                            <span>{Math.round(src.confidence * 100)}% confidence</span>
                          )}
                          {src.paper_url && (
                            <a
                              href={src.paper_url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="ml-auto inline-flex items-center gap-1 text-primary hover:underline"
                            >
                              <ExternalLink className="h-3 w-3" />
                              Open
                            </a>
                          )}
                        </div>
                      </div>
                    ))
                  )}
                </CardContent>
              </Card>
            </TabsContent>

            <TabsContent value="revisions" className="mt-0">
              <RevisionsView
                jobId={jobId}
                chapterNum={chapterNum}
                revisions={revisions}
                attempts={attempts}
                onRestored={() => {
                  api.chapters.get(jobId, chapterNum).then(setChapter);
                  api.chapters.revisions(jobId, chapterNum).then(setRevisions);
                }}
              />
            </TabsContent>
          </Tabs>
        </div>

        <div className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="text-sm">Stats</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3 pt-0">
              <div className="flex items-center justify-between text-sm">
                <span className="text-muted-foreground">Words</span>
                <span className="font-medium text-foreground">
                  {chapter.word_count.toLocaleString()}
                </span>
              </div>
              {chapter.ai_score !== null && (
                <div className="flex items-center justify-between text-sm">
                  <span className="text-muted-foreground">AI score</span>
                  <span
                    className={`font-medium ${
                      chapter.ai_score < 50 ? "text-success" : "text-warning"
                    }`}
                  >
                    {chapter.ai_score.toFixed(1)}/100
                  </span>
                </div>
              )}
              {chapter.style_score !== null && (
                <div className="flex items-center justify-between text-sm">
                  <span className="text-muted-foreground">Style score</span>
                  <span className="font-medium text-foreground">
                    {chapter.style_score}/100
                  </span>
                </div>
              )}
              <div className="flex items-center justify-between text-sm">
                <span className="text-muted-foreground">Status</span>
                <StatusBadge status={chapter.status} size="sm" />
              </div>
            </CardContent>
          </Card>

          {sections.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle className="text-sm">Sections</CardTitle>
              </CardHeader>
              <CardContent className="space-y-1 pt-0">
                {sections.map((s, i) => (
                  <a
                    key={s.id}
                    href={`#${s.id}`}
                    className={cn(
                      "flex items-center gap-2 rounded-sm px-2 py-1 text-sm transition-colors hover:bg-muted",
                      activeSection === s.id
                        ? "bg-muted font-medium text-foreground"
                        : "text-muted-foreground"
                    )}
                  >
                    <FileText className="h-3.5 w-3.5 shrink-0" />
                    <span className="truncate">{s.title || `Section ${i + 1}`}</span>
                  </a>
                ))}
              </CardContent>
            </Card>
          )}

          {attempts.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle className="text-sm flex items-center gap-2">
                  <Sparkles className="h-3.5 w-3.5" />
                  Humanizer runs
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-2 pt-0">
                {attempts.slice(0, 5).map((a) => (
                  <div
                    key={a.id}
                    className="flex items-center justify-between text-2xs"
                  >
                    <span className="rounded-full bg-muted px-2 py-0.5 font-medium uppercase tracking-wider text-muted-foreground">
                      {a.intensity}
                    </span>
                    {a.ai_score_before != null && a.ai_score_after != null && (
                      <span className="inline-flex items-center gap-1 text-muted-foreground">
                        {a.ai_score_before.toFixed(0)} → {a.ai_score_after.toFixed(0)}
                        {a.ai_score_after < a.ai_score_before && (
                          <Check className="h-3 w-3 text-success" />
                        )}
                      </span>
                    )}
                  </div>
                ))}
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}

function SectionsView({
  sections,
  registerRef,
}: {
  sections: Section[];
  registerRef: (el: HTMLElement | null, i: number) => void;
}) {
  return (
    <div className="space-y-6">
      {sections.map((s, i) => (
        <section
          key={s.id}
          id={s.id}
          ref={(el) => registerRef(el, i)}
          className="scroll-mt-20"
        >
          {s.title && (
            <h2 className="mb-3 border-b border-border pb-2 text-xl font-semibold text-foreground">
              {s.title}
            </h2>
          )}
          <div
            className="tiptap-editor prose max-w-none"
            dangerouslySetInnerHTML={{ __html: markdownToHtml(s.body) }}
          />
        </section>
      ))}
    </div>
  );
}

function RevisionsView({
  jobId,
  chapterNum,
  revisions,
  onRestored,
}: {
  jobId: string;
  chapterNum: number;
  revisions: ChapterRevisionSummary[];
  attempts: HumanizerAttemptSummary[];
  onRestored: () => void;
}) {
  const [selectedA, setSelectedA] = useState<number | null>(null);
  const [selectedB, setSelectedB] = useState<number | null>(null);

  useEffect(() => {
    if (revisions.length >= 2) {
      setSelectedA(revisions[1].id);
      setSelectedB(revisions[0].id);
    } else if (revisions.length === 1) {
      setSelectedA(revisions[0].id);
      setSelectedB(null);
    }
  }, [revisions]);

  const handleRestore = async (revisionId: number) => {
    try {
      const rev = await api.chapters.revision(jobId, chapterNum, revisionId);
      await api.chapters.update(jobId, chapterNum, {
        content: rev.content,
        source: "tiptap",
        summary: `Restored from revision ${revisionId}`,
      });
      toast.success("Revision restored");
      onRestored();
    } catch (e) {
      toast.error("Restore failed", {
        description: e instanceof Error ? e.message : String(e),
      });
    }
  };

  if (revisions.length === 0) {
    return (
      <Card>
        <CardContent className="p-5">
          <Empty
            icon={<History className="h-5 w-5" />}
            title="No revisions yet"
            description="Revisions are created automatically when this chapter is generated or edited."
          />
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <GitCompare className="h-4 w-4" />
            Compare revisions
          </CardTitle>
        </CardHeader>
        <CardContent className="grid gap-3 sm:grid-cols-2 pt-0">
          <RevisionPicker
            label="Revision A"
            value={selectedA}
            revisions={revisions}
            onChange={setSelectedA}
            exclude={selectedB}
          />
          <RevisionPicker
            label="Revision B (newer)"
            value={selectedB}
            revisions={revisions}
            onChange={setSelectedB}
            exclude={selectedA}
          />
        </CardContent>
      </Card>

      {selectedA && selectedB && selectedA !== selectedB && (
        <DiffView
          jobId={jobId}
          chapterNum={chapterNum}
          revisionA={selectedA}
          revisionB={selectedB}
        />
      )}

      <Card>
        <CardHeader>
          <CardTitle className="text-base">All revisions</CardTitle>
        </CardHeader>
        <CardContent className="divide-y divide-border pt-0">
          {revisions.map((r) => (
            <div
              key={r.id}
              className="flex items-center justify-between gap-3 py-3 first:pt-0 last:pb-0"
            >
              <div className="min-w-0">
                <div className="flex items-center gap-2">
                  <span className="rounded-full bg-muted px-2 py-0.5 text-2xs font-medium uppercase tracking-wider text-muted-foreground">
                    {r.source}
                  </span>
                  {r.summary && (
                    <span className="truncate text-sm text-foreground">
                      {r.summary}
                    </span>
                  )}
                </div>
                <p className="mt-0.5 text-2xs text-muted-foreground">
                  {new Date(r.created_at).toLocaleString()} ·{" "}
                  {r.word_count.toLocaleString()} words
                  {r.ai_score !== null && ` · AI: ${r.ai_score.toFixed(1)}`}
                </p>
              </div>
              <div className="flex shrink-0 items-center gap-1">
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={() => handleRestore(r.id)}
                >
                  Restore
                </Button>
              </div>
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  );
}

function RevisionPicker({
  label,
  value,
  revisions,
  onChange,
  exclude,
}: {
  label: string;
  value: number | null;
  revisions: ChapterRevisionSummary[];
  onChange: (id: number) => void;
  exclude: number | null;
}) {
  return (
    <div className="space-y-1.5">
      <label className="text-2xs font-medium uppercase tracking-wider text-muted-foreground">
        {label}
      </label>
      <select
        value={value ?? ""}
        onChange={(e) => onChange(parseInt(e.target.value))}
        className="h-9 w-full rounded-md border border-input bg-surface px-3 text-sm focus:border-primary focus:outline-none focus:ring-2 focus:ring-ring/40"
      >
        <option value="">Select…</option>
        {revisions
          .filter((r) => r.id !== exclude)
          .map((r) => (
            <option key={r.id} value={r.id}>
              #{r.id} · {new Date(r.created_at).toLocaleString()} · {r.source}
            </option>
          ))}
      </select>
    </div>
  );
}

function DiffView({
  jobId,
  chapterNum,
  revisionA,
  revisionB,
}: {
  jobId: string;
  chapterNum: number;
  revisionA: number;
  revisionB: number;
}) {
  const [contentA, setContentA] = useState<string | null>(null);
  const [contentB, setContentB] = useState<string | null>(null);

  useEffect(() => {
    setContentA(null);
    setContentB(null);
    Promise.all([
      api.chapters.revision(jobId, chapterNum, revisionA),
      api.chapters.revision(jobId, chapterNum, revisionB),
    ]).then(([a, b]) => {
      setContentA(a.content);
      setContentB(b.content);
    });
  }, [jobId, chapterNum, revisionA, revisionB]);

  if (!contentA || !contentB) {
    return (
      <Card>
        <CardContent className="p-5">
          <Skeleton className="h-32" />
        </CardContent>
      </Card>
    );
  }

  const tokensA = tokenize(contentA);
  const tokensB = tokenize(contentB);
  const diff = computeDiff(tokensA, tokensB);

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm">Diff</CardTitle>
      </CardHeader>
      <CardContent className="pt-0">
        <pre className="whitespace-pre-wrap rounded-md border border-border bg-background p-4 font-mono text-2xs leading-relaxed">
          {diff.map((d, i) => (
            <span
              key={i}
              className={cn(
                d.type === "added" && "bg-success-soft text-success",
                d.type === "removed" && "bg-danger-soft text-danger line-through"
              )}
            >
              {d.value}
            </span>
          ))}
        </pre>
      </CardContent>
    </Card>
  );
}

interface DiffToken {
  type: "same" | "added" | "removed";
  value: string;
}

function tokenize(text: string): string[] {
  return text.split(/(\s+)/);
}

function computeDiff(a: string[], b: string[]): DiffToken[] {
  const m = a.length;
  const n = b.length;
  const lcs: number[][] = Array.from({ length: m + 1 }, () =>
    new Array(n + 1).fill(0)
  );
  for (let i = m - 1; i >= 0; i--) {
    for (let j = n - 1; j >= 0; j--) {
      if (a[i] === b[j]) {
        lcs[i][j] = lcs[i + 1][j + 1] + 1;
      } else {
        lcs[i][j] = Math.max(lcs[i + 1][j], lcs[i][j + 1]);
      }
    }
  }
  const out: DiffToken[] = [];
  let i = 0;
  let j = 0;
  while (i < m && j < n) {
    if (a[i] === b[j]) {
      out.push({ type: "same", value: a[i] });
      i++;
      j++;
    } else if (lcs[i + 1][j] >= lcs[i][j + 1]) {
      out.push({ type: "removed", value: a[i] });
      i++;
    } else {
      out.push({ type: "added", value: b[j] });
      j++;
    }
  }
  while (i < m) {
    out.push({ type: "removed", value: a[i++] });
  }
  while (j < n) {
    out.push({ type: "added", value: b[j++] });
  }
  return out;
}

function parseSections(content: string): Section[] {
  const lines = content.split("\n");
  const sections: Section[] = [];
  let current: Section = { title: "", body: "", id: "" };
  let counter = 0;

  function slugify(s: string): string {
    return `section-${counter++}-${s
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/^-+|-+$/g, "")
      .slice(0, 40)}`;
  }

  function pushCurrent() {
    if (current.title || current.body.trim()) {
      current.id = current.title ? slugify(current.title) : `section-${counter++}`;
      sections.push(current);
    }
  }

  for (const line of lines) {
    if (line.startsWith("### ")) {
      current.body += line + "\n";
    } else if (line.startsWith("## ")) {
      pushCurrent();
      current = { title: line.replace(/^##\s*/, ""), body: "", id: "" };
    } else if (line.startsWith("# ") && !line.startsWith("## ")) {
      pushCurrent();
      current = { title: line.replace(/^#\s*/, ""), body: "", id: "" };
    } else {
      current.body += line + "\n";
    }
  }
  pushCurrent();
  return sections;
}
