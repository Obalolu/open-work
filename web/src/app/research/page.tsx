"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { Job, Source } from "@/lib/types";
import { Card, CardContent } from "@/components/ui/Card";
import { Input } from "@/components/ui/Input";
import { Skeleton } from "@/components/ui/Skeleton";
import { Empty } from "@/components/ui/Empty";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import {
  Search,
  Quote,
  ExternalLink,
  Calendar,
  Users,
  ChevronRight,
} from "lucide-react";
import { motion } from "framer-motion";

export default function ResearchPage() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [jobId, setJobId] = useState<string | null>(null);
  const [sources, setSources] = useState<Source[]>([]);
  const [search, setSearch] = useState("");
  const [yearFilter, setYearFilter] = useState<string>("all");
  const [typeFilter, setTypeFilter] = useState<string>("all");
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState<Source | null>(null);

  useEffect(() => {
    api.jobs.list().then((js) => {
      setJobs(js);
      if (js.length > 0) setJobId(js[0].id);
    });
  }, []);

  useEffect(() => {
    if (!jobId) return;
    setLoading(true);
    api.research
      .sources(jobId)
      .then(setSources)
      .finally(() => setLoading(false));
  }, [jobId]);

  const years = Array.from(
    new Set(sources.map((s) => s.year).filter((y): y is number => y !== null))
  ).sort((a, b) => b - a);

  const types = Array.from(new Set(sources.map((s) => s.source_type).filter(Boolean)));

  const filtered = sources.filter((s) => {
    if (search) {
      const s2 = search.toLowerCase();
      const matches =
        s.title.toLowerCase().includes(s2) ||
        s.authors.some((a) => a.toLowerCase().includes(s2));
      if (!matches) return false;
    }
    if (yearFilter !== "all" && s.year !== parseInt(yearFilter)) return false;
    if (typeFilter !== "all" && s.source_type !== typeFilter) return false;
    return true;
  });

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="text-3xl font-semibold tracking-tight text-foreground">
            Research
          </h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Browse sources collected across all your jobs
          </p>
        </div>
        {jobs.length > 0 && (
          <select
            value={jobId ?? ""}
            onChange={(e) => setJobId(e.target.value)}
            className="h-9 rounded-md border border-input bg-surface px-3 text-sm focus:border-primary focus:outline-none focus:ring-2 focus:ring-ring/40"
          >
            {jobs.map((j) => (
              <option key={j.id} value={j.id}>
                {j.topic.length > 50 ? j.topic.slice(0, 50) + "…" : j.topic}
              </option>
            ))}
          </select>
        )}
      </div>

      {loading ? (
        <div className="grid gap-4 lg:grid-cols-2">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-32" />
          ))}
        </div>
      ) : sources.length === 0 ? (
        <Empty
          variant="bordered"
          icon={<Quote className="h-6 w-6" />}
          title="No research collected"
          description="Run a generation to start collecting sources."
        />
      ) : (
        <>
          <div className="flex flex-wrap items-center gap-2">
            <div className="relative max-w-sm flex-1">
              <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Search title or author…"
                className="pl-9"
              />
            </div>
            <select
              value={yearFilter}
              onChange={(e) => setYearFilter(e.target.value)}
              className="h-9 rounded-md border border-input bg-surface px-3 text-sm focus:border-primary focus:outline-none focus:ring-2 focus:ring-ring/40"
            >
              <option value="all">All years</option>
              {years.map((y) => (
                <option key={y} value={y}>
                  {y}
                </option>
              ))}
            </select>
            <select
              value={typeFilter}
              onChange={(e) => setTypeFilter(e.target.value)}
              className="h-9 rounded-md border border-input bg-surface px-3 text-sm focus:border-primary focus:outline-none focus:ring-2 focus:ring-ring/40"
            >
              <option value="all">All sources</option>
              {types.map((t) => (
                <option key={t} value={t}>
                  {t}
                </option>
              ))}
            </select>
            <span className="ml-auto text-2xs text-muted-foreground">
              {filtered.length} of {sources.length} sources
            </span>
          </div>

          {filtered.length === 0 ? (
            <Empty
              variant="bordered"
              icon={<Search className="h-5 w-5" />}
              title="No matching sources"
              description="Try a different search or filter."
            />
          ) : (
            <motion.div
              initial="hidden"
              animate="show"
              variants={{
                hidden: { opacity: 0 },
                show: { opacity: 1, transition: { staggerChildren: 0.04 } },
              }}
              className="grid gap-3 lg:grid-cols-2"
            >
              {filtered.map((src) => (
                <motion.div
                  key={src.paper_id}
                  variants={{ hidden: { opacity: 0, y: 4 }, show: { opacity: 1, y: 0 } }}
                >
                  <button
                    onClick={() => setSelected(src)}
                    className="w-full text-left"
                  >
                    <Card interactive className="h-full">
                      <CardContent className="space-y-2 p-4">
                        <div className="flex items-start gap-2">
                          <div className="min-w-0 flex-1">
                            <h4 className="line-clamp-2 text-sm font-medium text-foreground">
                              {src.title}
                            </h4>
                            <p className="mt-1 text-2xs text-muted-foreground">
                              {src.authors.slice(0, 3).join(", ")}
                              {src.authors.length > 3 ? " et al." : ""}
                              {src.year ? ` · ${src.year}` : ""}
                            </p>
                          </div>
                          <ChevronRight className="h-4 w-4 shrink-0 text-muted-foreground" />
                        </div>
                        {src.abstract_summary && (
                          <p className="line-clamp-2 text-2xs text-muted-foreground">
                            {src.abstract_summary}
                          </p>
                        )}
                        <div className="flex flex-wrap items-center gap-2 text-2xs text-muted-foreground">
                          {src.venue && <Badge variant="secondary">{src.venue}</Badge>}
                          {src.citation_count > 0 && (
                            <span>{src.citation_count} citations</span>
                          )}
                          {src.confidence > 0 && (
                            <span>{Math.round(src.confidence * 100)}% confidence</span>
                          )}
                        </div>
                      </CardContent>
                    </Card>
                  </button>
                </motion.div>
              ))}
            </motion.div>
          )}
        </>
      )}

      {selected && (
        <SourcePanel source={selected} onClose={() => setSelected(null)} />
      )}
    </div>
  );
}

function SourcePanel({
  source,
  onClose,
}: {
  source: Source;
  onClose: () => void;
}) {
  return (
    <div className="fixed inset-0 z-50 flex items-stretch justify-end bg-foreground/40 backdrop-blur-sm">
      <motion.div
        initial={{ x: 24, opacity: 0 }}
        animate={{ x: 0, opacity: 1 }}
        className="flex h-full w-full max-w-md flex-col border-l border-border bg-surface-elevated shadow-2xl"
      >
        <div className="flex items-start justify-between gap-3 border-b border-border p-5">
          <h2 className="text-base font-semibold text-foreground">{source.title}</h2>
          <Button variant="ghost" size="sm" onClick={onClose}>
            Close
          </Button>
        </div>
        <div className="flex-1 space-y-4 overflow-y-auto p-5">
          {source.authors.length > 0 && (
            <div>
              <p className="mb-1 flex items-center gap-1.5 text-2xs font-semibold uppercase tracking-wider text-muted-foreground">
                <Users className="h-3 w-3" /> Authors
              </p>
              <p className="text-sm text-foreground">
                {source.authors.join(", ")}
              </p>
            </div>
          )}
          {source.year && (
            <div>
              <p className="mb-1 flex items-center gap-1.5 text-2xs font-semibold uppercase tracking-wider text-muted-foreground">
                <Calendar className="h-3 w-3" /> Year
              </p>
              <p className="text-sm text-foreground">{source.year}</p>
            </div>
          )}
          {source.venue && (
            <div>
              <p className="mb-1 text-2xs font-semibold uppercase tracking-wider text-muted-foreground">
                Venue
              </p>
              <Badge variant="secondary">{source.venue}</Badge>
            </div>
          )}
          {source.abstract_summary && (
            <div>
              <p className="mb-1 text-2xs font-semibold uppercase tracking-wider text-muted-foreground">
                Abstract
              </p>
              <p className="text-sm leading-relaxed text-foreground">
                {source.abstract_summary}
              </p>
            </div>
          )}
          {source.doi && (
            <div>
              <p className="mb-1 text-2xs font-semibold uppercase tracking-wider text-muted-foreground">
                DOI
              </p>
              <code className="rounded bg-muted px-2 py-1 font-mono text-2xs">
                {source.doi}
              </code>
            </div>
          )}
        </div>
        <div className="border-t border-border p-5">
          {source.paper_url && (
            <Button asChild className="w-full">
              <a href={source.paper_url} target="_blank" rel="noopener noreferrer">
                <ExternalLink />
                Open paper
              </a>
            </Button>
          )}
        </div>
      </motion.div>
    </div>
  );
}
