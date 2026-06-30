"use client";

import { useEffect, useState, useCallback } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { api } from "@/lib/api";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/Tabs";
import { Skeleton } from "@/components/ui/Skeleton";
import { Empty } from "@/components/ui/Empty";
import type { ChapterDetail, Source } from "@/lib/types";
import {
  ArrowLeft,
  Download,
  FileText,
  ExternalLink,
  AlertTriangle,
  Search,
  Quote,
} from "lucide-react";

export default function EditorPage() {
  const params = useParams();
  const jobId = params.jobId as string;
  const chapterId = params.chapterId as string;
  const chapterNum = parseInt(chapterId);

  const [chapter, setChapter] = useState<ChapterDetail | null>(null);
  const [sources, setSources] = useState<Source[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [sourceSearch, setSourceSearch] = useState("");

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
        const [ch, src] = await Promise.all([
          api.chapters.get(jobId, chapterNum),
          api.research.sources(jobId).catch(() => []),
        ]);
        setChapter(ch);
        setSources(src);
      } catch (e) {
        setError(e instanceof Error ? e.message : String(e));
      }
      setLoading(false);
    };
    load();
  }, [jobId, chapterNum]);

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
      s.authors.some((a) => a.toLowerCase().includes(sourceSearch.toLowerCase()))
  );

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
          {(["md", "docx", "pdf"] as const).map((fmt) => (
            <Button
              key={fmt}
              variant="outline"
              size="sm"
              asChild
            >
              <a
                href={api.export.url(jobId, chapterNum, fmt)}
                download
              >
                <Download />
                <span className="uppercase">{fmt}</span>
              </a>
            </Button>
          ))}
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-4">
        <div className="lg:col-span-3">
          <Tabs defaultValue="content">
            <TabsList>
              <TabsTrigger value="content">Content</TabsTrigger>
              <TabsTrigger value="sources">Sources ({sources.length})</TabsTrigger>
            </TabsList>

            <TabsContent value="content" className="mt-0">
              <Card>
                <CardContent className="p-6 md:p-8">
                  {sections.length > 0 ? (
                    <div className="space-y-6">
                      {sections.map((section, i) => (
                        <Section key={i} section={section} />
                      ))}
                    </div>
                  ) : (
                    <div
                      className="tiptap-editor prose max-w-none"
                      dangerouslySetInnerHTML={{
                        __html: renderMarkdown(chapter.content || ""),
                      }}
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
                      <input
                        value={sourceSearch}
                        onChange={(e) => setSourceSearch(e.target.value)}
                        placeholder="Search sources by title or author…"
                        className="h-9 w-full rounded-md border border-input bg-surface pl-9 pr-3 text-sm focus:border-primary focus:outline-none focus:ring-2 focus:ring-ring/40"
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
              <CardContent className="space-y-2 pt-0">
                {sections.map((section, i) => (
                  <a
                    key={i}
                    href={`#section-${i}`}
                    className="flex items-center gap-2 rounded-sm px-1 py-1 text-sm text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
                  >
                    <FileText className="h-3.5 w-3.5 shrink-0" />
                    <span className="truncate">
                      {section.title || `Section ${i + 1}`}
                    </span>
                  </a>
                ))}
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}

function Section({ section }: { section: { title: string; body: string } }) {
  const ref = useCallback(
    (el: HTMLDivElement | null) => {
      if (el) {
        el.innerHTML = renderMarkdown(section.body);
      }
    },
    [section.body]
  );

  return (
    <section id={`section-${section.title}`}>
      {section.title && (
        <h2 className="mb-3 border-b border-border pb-2 text-xl font-semibold text-foreground">
          {section.title}
        </h2>
      )}
      <div ref={ref} className="tiptap-editor prose max-w-none" />
    </section>
  );
}

function parseSections(content: string): { title: string; body: string }[] {
  const lines = content.split("\n");
  const sections: { title: string; body: string }[] = [];
  let current = { title: "", body: "" };

  for (const line of lines) {
    if (line.startsWith("### ")) {
      current.body += line + "\n";
    } else if (line.startsWith("## ")) {
      if (current.title || current.body.trim()) {
        sections.push(current);
      }
      current = { title: line.replace(/^##\s*/, ""), body: "" };
    } else if (line.startsWith("# ") && !line.startsWith("## ")) {
      if (current.title || current.body.trim()) {
        sections.push(current);
      }
      current = { title: line.replace(/^#\s*/, ""), body: "" };
    } else {
      current.body += line + "\n";
    }
  }

  if (current.title || current.body.trim()) {
    sections.push(current);
  }

  return sections;
}

function sanitizeUrl(url: string): string {
  const trimmed = url.trim();
  if (/^(https?|mailto):/i.test(trimmed)) return trimmed;
  if (trimmed.startsWith("//")) return trimmed;
  return "#";
}

function renderMarkdown(md: string): string {
  let html = md
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/^### (.+)$/gm, "<h3>$1</h3>")
    .replace(/^## (.+)$/gm, "<h2>$1</h2>")
    .replace(/^# (.+)$/gm, "<h1>$1</h1>")
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    .replace(/\*(.+?)\*/g, "<em>$1</em>")
    .replace(/`(.+?)`/g, "<code>$1</code>")
    .replace(
      /\[(.+?)\]\((.+?)\)/g,
      (_, text, url) => `<a href="${sanitizeUrl(url)}" target="_blank" rel="noopener noreferrer">${text}</a>`
    )
    .replace(/^- (.+)$/gm, "<li class='ul-item'>$1</li>")
    .replace(/^(\d+)\. (.+)$/gm, "<li class='ol-item'>$2</li>")
    .replace(/(<li class='ul-item'>[\s\S]*?<\/li>\n?)+/g, (match) => `<ul>${match}</ul>`)
    .replace(/(<li class='ol-item'>[\s\S]*?<\/li>\n?)+/g, (match) => `<ol>${match}</ol>`)
    .replace(/ class='ul-item'/g, "")
    .replace(/ class='ol-item'/g, "")
    .replace(/\n\n/g, "</p><p>")
    .replace(/\n/g, "<br>");

  html = "<p>" + html + "</p>";
  html = html
    .replace(/<p><\/p>/g, "")
    .replace(/<p>(<h[123]>)/g, "$1")
    .replace(/<\/h([123])><\/p>/g, "</h$1>")
    .replace(/<p>(<ul>)/g, "$1")
    .replace(/(<\/ul>)<\/p>/g, "$1");

  return html;
}
