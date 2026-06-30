"use client";

import Link from "next/link";
import { motion } from "framer-motion";
import { useEffect, useState } from "react";
import { useStore } from "@/stores/jobStore";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { StatCard } from "@/components/ui/StatCard";
import { Button } from "@/components/ui/Button";
import { Card, CardContent } from "@/components/ui/Card";
import { Empty } from "@/components/ui/Empty";
import { ProgressRing } from "@/components/ui/Progress";
import { GenerationStream } from "@/components/generation/GenerationStream";
import { AnimatedNumber, Sparkline } from "@/components/motion/AnimatedNumber";
import { ActivityChart, type ActivityPoint } from "@/components/dashboard/ActivityChart";
import { api } from "@/lib/api";
import { format, subDays } from "date-fns";
import {
  FileText,
  BookOpen,
  BarChart3,
  CheckCircle2,
  Plus,
  ArrowRight,
  Sparkles,
} from "lucide-react";

export default function DashboardPage() {
  const { jobs, loading, error, fetchJobs } = useStore();
  const [activity, setActivity] = useState<ActivityPoint[]>([]);
  const [health, setHealth] = useState<"ok" | "down" | null>(null);

  useEffect(() => {
    fetchJobs();
  }, [fetchJobs]);

  useEffect(() => {
    const days: Record<string, ActivityPoint> = {};
    for (let i = 29; i >= 0; i--) {
      const d = format(subDays(new Date(), i), "yyyy-MM-dd");
      days[d] = { date: d, jobs: 0, chapters: 0, words: 0 };
    }
    jobs.forEach((j) => {
      const d = j.created_at?.slice(0, 10);
      if (d && days[d]) {
        days[d].jobs += 1;
        days[d].chapters += j.chapter_count;
        days[d].words += j.total_words;
      }
    });
    setActivity(Object.values(days));

    api.health
      .get()
      .then((h) => setHealth(h.db_ok && h.llm_configured ? "ok" : "down"))
      .catch(() => setHealth("down"));
  }, [jobs]);

  if (loading && jobs.length === 0) {
    return (
      <div className="flex items-center justify-center py-24">
        <div className="h-6 w-6 animate-spin rounded-full border-2 border-muted border-t-primary" />
      </div>
    );
  }

  if (error && jobs.length === 0) {
    return (
      <Empty
        title="Failed to load data"
        description={error}
        action={
          <Button onClick={() => fetchJobs()} variant="outline">
            Retry
          </Button>
        }
      />
    );
  }

  const totalChapters = jobs.reduce((s, j) => s + j.chapter_count, 0);
  const totalWords = jobs.reduce((s, j) => s + j.total_words, 0);
  const completeJobs = jobs.filter((j) => j.status === "complete").length;
  const activeJob = jobs.find((j) => j.status === "generating") || null;

  const recent = [...jobs]
    .sort((a, b) => (b.updated_at > a.updated_at ? 1 : -1))
    .slice(0, 5);

  const recentWordCounts = [...jobs]
    .sort((a, b) => (a.created_at > b.created_at ? 1 : -1))
    .slice(-10)
    .map((j) => j.total_words);

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className="space-y-8"
    >
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-3xl font-semibold tracking-tight text-foreground">
            Dashboard
          </h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Overview of your research paper writing system
          </p>
        </div>
        <div className="flex items-center gap-2">
          <span
            className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-2xs font-medium ${
              health === "ok"
                ? "bg-success-soft text-success"
                : health === "down"
                  ? "bg-danger-soft text-danger"
                  : "bg-muted text-muted-foreground"
            }`}
            title="API health"
          >
            <span
              className={`h-1.5 w-1.5 rounded-full ${
                health === "ok"
                  ? "bg-success"
                  : health === "down"
                    ? "bg-danger"
                    : "bg-muted-foreground"
              }`}
            />
            API {health ?? "checking"}
          </span>
          <Button asChild>
            <Link href="/jobs">
              <Plus />
              New job
            </Link>
          </Button>
        </div>
      </div>

      {activeJob && (
        <GenerationStream
          key={activeJob.id}
          jobId={activeJob.id}
          jobTopic={activeJob.topic}
          onComplete={() => fetchJobs()}
        />
      )}

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          icon={<FileText className="h-4 w-4" />}
          label="Total jobs"
          value={<AnimatedNumber value={jobs.length} />}
        />
        <StatCard
          icon={<BookOpen className="h-4 w-4" />}
          label="Chapters"
          value={<AnimatedNumber value={totalChapters} />}
        />
        <StatCard
          icon={<BarChart3 className="h-4 w-4" />}
          label="Total words"
          value={<AnimatedNumber value={totalWords} />}
        />
        <StatCard
          icon={<CheckCircle2 className="h-4 w-4" />}
          label="Completed"
          value={
            <span className="inline-flex items-center gap-2">
              <AnimatedNumber value={completeJobs} />
              {activeJob && (
                <span className="text-2xs text-muted-foreground">+1 active</span>
              )}
            </span>
          }
        />
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        <div className="lg:col-span-2">
          <ActivityChart data={activity} />
        </div>
        <Card>
          <CardContent className="p-5">
            <p className="text-sm font-semibold text-foreground">
              Word velocity
            </p>
            <p className="text-2xs text-muted-foreground">
              Total words across your 10 most recent jobs
            </p>
            <div className="mt-4">
              <Sparkline
                data={recentWordCounts}
                width={300}
                height={80}
                className="w-full"
              />
            </div>
            <p className="mt-3 text-2xs text-muted-foreground">
              {recentWordCounts.length === 0
                ? "No data yet"
                : `Latest job: ${(
                    recentWordCounts[recentWordCounts.length - 1] ?? 0
                  ).toLocaleString()} words`}
            </p>
          </CardContent>
        </Card>
      </div>

      <div>
        <div className="mb-3 flex items-center justify-between">
          <h3 className="text-base font-semibold text-foreground">Recent jobs</h3>
          <Link
            href="/jobs"
            className="group inline-flex items-center gap-1 text-sm font-medium text-primary transition-colors hover:text-primary-hover"
          >
            View all
            <ArrowRight className="h-3.5 w-3.5 transition-transform group-hover:translate-x-0.5" />
          </Link>
        </div>
        {recent.length === 0 ? (
          <EmptyDashboard />
        ) : (
          <motion.ul
            initial="hidden"
            animate="show"
            variants={{
              hidden: { opacity: 0 },
              show: {
                opacity: 1,
                transition: { staggerChildren: 0.04 },
              },
            }}
            className="divide-y divide-border overflow-hidden rounded-lg border border-border bg-surface"
          >
            {recent.map((job) => {
              const ringValue =
                job.status === "complete"
                  ? 100
                  : job.status === "generating"
                    ? 50
                    : 0;
              return (
                <motion.li
                  key={job.id}
                  variants={{
                    hidden: { opacity: 0, y: 4 },
                    show: { opacity: 1, y: 0 },
                  }}
                >
                  <Link
                    href={`/jobs/${job.id}`}
                    className="group flex items-center justify-between gap-4 p-4 transition-colors hover:bg-muted/60"
                  >
                    <div className="flex min-w-0 items-center gap-4">
                      <ProgressRing
                        value={ringValue}
                        size={40}
                        strokeWidth={4}
                        className="shrink-0 text-muted-foreground"
                      />
                      <div className="min-w-0 flex-1">
                        <p className="truncate text-sm font-medium text-foreground group-hover:text-primary">
                          {job.topic}
                        </p>
                        <p className="mt-0.5 text-xs text-muted-foreground">
                          {job.paper_type.replace(/_/g, " ")} ·{" "}
                          {job.chapter_count} chapter
                          {job.chapter_count === 1 ? "" : "s"} ·{" "}
                          {job.total_words.toLocaleString()} words
                        </p>
                      </div>
                    </div>
                    <StatusBadge status={job.status} size="sm" />
                  </Link>
                </motion.li>
              );
            })}
          </motion.ul>
        )}
      </div>
    </motion.div>
  );
}

function EmptyDashboard() {
  const steps = [
    { title: "Create a job", desc: "Pick a topic, paper type, and chapters" },
    { title: "Generate", desc: "The pipeline researches, writes, and humanizes" },
    { title: "Edit & export", desc: "Review the output, refine, and download" },
  ];
  return (
    <Empty
      variant="bordered"
      icon={<Sparkles className="h-6 w-6" />}
      title="Ready to write your first paper?"
      description="Set up a job and we'll research, write, and humanize each chapter for you."
      action={
        <Button asChild>
          <Link href="/jobs">
            <Plus />
            Create your first job
          </Link>
        </Button>
      }
    >
      <div className="mx-auto mt-6 grid max-w-2xl gap-3 text-left sm:grid-cols-3">
        {steps.map((s, i) => (
          <div
            key={i}
            className="rounded-md border border-border bg-background p-4"
          >
            <div className="flex items-center gap-2">
              <span className="flex h-5 w-5 items-center justify-center rounded-full bg-primary text-2xs font-semibold text-primary-foreground">
                {i + 1}
              </span>
              <p className="text-sm font-medium text-foreground">{s.title}</p>
            </div>
            <p className="mt-1.5 text-xs text-muted-foreground">{s.desc}</p>
          </div>
        ))}
      </div>
    </Empty>
  );
}
