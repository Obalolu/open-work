"use client";

import { useEffect, useState, useCallback } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { api } from "@/lib/api";
import { StatusBadge } from "@/components/ui/StatusBadge";
import type { ChapterDetail, Source } from "@/lib/types";
import {
  ArrowLeft,
  Download,
  FileText,
  ExternalLink,
  Loader2,
  AlertTriangle,
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
  const [activeTab, setActiveTab] = useState<"content" | "sources">("content");

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
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-8 h-8 text-blue-500 animate-spin" />
      </div>
    );
  }

  if (error || !chapter) {
    return (
      <div className="text-center py-12">
        <AlertTriangle className="w-12 h-12 text-amber-400 mx-auto mb-4" />
        <p className="text-slate-500 mb-2">{error || "Chapter not found"}</p>
        <Link href={`/jobs/${jobId}`} className="text-blue-600 hover:underline mt-2 inline-block">
          Back to job
        </Link>
      </div>
    );
  }

  const sections = parseSections(chapter.content || "");

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row items-start sm:items-center gap-4">
        <Link
          href={`/jobs/${jobId}`}
          className="p-2 text-slate-400 hover:text-slate-600 rounded-lg hover:bg-slate-100"
          aria-label="Back to job"
        >
          <ArrowLeft className="w-5 h-5" />
        </Link>
        <div className="flex-1 min-w-0">
          <h1 className="text-2xl font-bold text-slate-900 truncate">
            Chapter {chapter.chapter_number}: {chapter.name}
          </h1>
          <p className="text-slate-500 mt-1">
            {chapter.word_count.toLocaleString()} words
          </p>
        </div>
        <div className="flex gap-2 shrink-0">
          <a
            href={api.export.url(jobId, chapterNum, "md")}
            className="flex items-center gap-2 px-3 py-2 border border-slate-300 rounded-lg text-sm font-medium text-slate-700 hover:bg-slate-50"
          >
            <Download className="w-4 h-4" />
            <span className="hidden sm:inline">Download</span> MD
          </a>
          <a
            href={api.export.url(jobId, chapterNum, "docx")}
            className="flex items-center gap-2 px-3 py-2 border border-slate-300 rounded-lg text-sm font-medium text-slate-700 hover:bg-slate-50"
          >
            <Download className="w-4 h-4" />
            <span className="hidden sm:inline">Download</span> DOCX
          </a>
          <a
            href={api.export.url(jobId, chapterNum, "pdf")}
            className="flex items-center gap-2 px-3 py-2 border border-slate-300 rounded-lg text-sm font-medium text-slate-700 hover:bg-slate-50"
          >
            <Download className="w-4 h-4" />
            <span className="hidden sm:inline">Download</span> PDF
          </a>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        <div className="lg:col-span-3">
          <div className="flex gap-1 mb-4 border-b border-slate-200">
            <button
              onClick={() => setActiveTab("content")}
              className={`px-4 py-2 text-sm font-medium border-b-2 -mb-px ${
                activeTab === "content"
                  ? "border-blue-600 text-blue-600"
                  : "border-transparent text-slate-500 hover:text-slate-700"
              }`}
            >
              Content
            </button>
            <button
              onClick={() => setActiveTab("sources")}
              className={`px-4 py-2 text-sm font-medium border-b-2 -mb-px ${
                activeTab === "sources"
                  ? "border-blue-600 text-blue-600"
                  : "border-transparent text-slate-500 hover:text-slate-700"
              }`}
            >
              Sources ({sources.length})
            </button>
          </div>

          {activeTab === "content" ? (
            <div className="bg-white rounded-xl border border-slate-200">
              <div className="p-6 md:p-8">
                {sections.length > 0 ? (
                  <div className="space-y-6">
                    {sections.map((section, i) => (
                      <Section key={i} section={section} />
                    ))}
                  </div>
                ) : (
                  <div
                    className="tiptap-editor prose max-w-none"
                    dangerouslySetInnerHTML={{ __html: renderMarkdown(chapter.content || "") }}
                  />
                )}
              </div>
            </div>
          ) : (
            <div className="bg-white rounded-xl border border-slate-200 p-6 space-y-4">
              {sources.length === 0 ? (
                <p className="text-slate-500 text-center py-8">
                  No sources found for this job
                </p>
              ) : (
                sources.map((src) => (
                  <div
                    key={src.paper_id}
                    className="border border-slate-200 rounded-lg p-4 hover:border-slate-300"
                  >
                    <h4 className="font-medium text-slate-800">
                      {src.title}
                    </h4>
                    <p className="text-sm text-slate-500 mt-1">
                      {src.authors.slice(0, 3).join(", ")}
                      {src.authors.length > 3 ? " et al." : ""}
                      {src.year ? ` (${src.year})` : ""}
                    </p>
                    {src.abstract_summary && (
                      <p className="text-sm text-slate-600 mt-2 line-clamp-2">
                        {src.abstract_summary}
                      </p>
                    )}
                    <div className="flex items-center gap-3 mt-3 text-xs text-slate-400">
                      {src.venue && <span>{src.venue}</span>}
                      {src.citation_count > 0 && (
                        <span>{src.citation_count} citations</span>
                      )}
                      {src.paper_url && (
                        <a
                          href={src.paper_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="flex items-center gap-1 text-blue-500 hover:text-blue-700"
                        >
                          <ExternalLink className="w-3 h-3" />
                          Link
                        </a>
                      )}
                    </div>
                  </div>
                ))
              )}
            </div>
          )}
        </div>

        <div className="space-y-4">
          <div className="bg-white rounded-xl border border-slate-200 p-5">
            <h3 className="font-semibold text-slate-800 mb-3">Stats</h3>
            <div className="space-y-3">
              <div className="flex items-center justify-between text-sm">
                <span className="text-slate-500">Words</span>
                <span className="font-medium text-slate-800">
                  {chapter.word_count.toLocaleString()}
                </span>
              </div>
              {chapter.ai_score !== null && (
                <div className="flex items-center justify-between text-sm">
                  <span className="text-slate-500">AI Score</span>
                  <span
                    className={`font-medium ${
                      chapter.ai_score < 50 ? "text-green-600" : "text-amber-600"
                    }`}
                  >
                    {chapter.ai_score.toFixed(1)}/100
                  </span>
                </div>
              )}
              {chapter.style_score !== null && (
                <div className="flex items-center justify-between text-sm">
                  <span className="text-slate-500">Style Score</span>
                  <span className="font-medium text-slate-800">
                    {chapter.style_score}/100
                  </span>
                </div>
              )}
              <div className="flex items-center justify-between text-sm">
                <span className="text-slate-500">Status</span>
                <StatusBadge status={chapter.status} size="sm" />
              </div>
            </div>
          </div>

          <div className="bg-white rounded-xl border border-slate-200 p-5">
            <h3 className="font-semibold text-slate-800 mb-3">Sections</h3>
            <div className="space-y-2">
              {sections.map((section, i) => (
                <div
                  key={i}
                  className="text-sm text-slate-600 flex items-center gap-2"
                >
                  <FileText className="w-4 h-4 text-slate-400 shrink-0" />
                  <span className="truncate">{section.title || `Section ${i + 1}`}</span>
                </div>
              ))}
              {sections.length === 0 && (
                <p className="text-sm text-slate-400">No sections parsed</p>
              )}
            </div>
          </div>
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
    <div>
      {section.title && (
        <h2 className="text-xl font-semibold text-slate-800 border-b border-slate-200 pb-2 mb-4">
          {section.title}
        </h2>
      )}
      <div ref={ref} className="tiptap-editor prose max-w-none" />
    </div>
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
    .replace(/^- (.+)$/gm, "<li>$1</li>")
    .replace(/^(\d+)\. (.+)$/gm, "<li>$2</li>")
    .replace(/(<li>[\s\S]*?<\/li>\n?)+/g, (match) => `<ul>${match}</ul>`)
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
