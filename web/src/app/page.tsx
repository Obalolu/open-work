"use client";

import { useEffect } from "react";
import Link from "next/link";
import { motion, type Variants } from "framer-motion";
import { useStore } from "@/stores/jobStore";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { StatCard } from "@/components/ui/StatCard";
import { FileText, BookOpen, BarChart3, CheckCircle2, Plus, ArrowRight } from "lucide-react";

const item: Variants = {
  hidden: { opacity: 0, y: 8 },
  show: {
    opacity: 1,
    y: 0,
    transition: { type: "spring", stiffness: 380, damping: 32, mass: 0.8 },
  },
};

const container: Variants = {
  hidden: { opacity: 0 },
  show: {
    opacity: 1,
    transition: { staggerChildren: 0.04, delayChildren: 0.05 },
  },
};

export default function DashboardPage() {
  const { jobs, loading, error, fetchJobs } = useStore();

  useEffect(() => {
    fetchJobs();
  }, [fetchJobs]);

  if (loading && jobs.length === 0) {
    return (
      <div className="flex items-center justify-center py-24">
        <div className="h-6 w-6 animate-spin rounded-full border-2 border-muted border-t-primary" />
      </div>
    );
  }

  if (error && jobs.length === 0) {
    return (
      <div className="rounded-lg border border-danger-soft bg-danger-soft/40 p-6 text-center">
        <p className="font-medium text-danger">Failed to load data</p>
        <p className="mt-1 text-sm text-muted-foreground">{error}</p>
        <button
          onClick={() => fetchJobs()}
          className="mt-4 rounded-md bg-primary px-3 py-1.5 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary-hover"
        >
          Retry
        </button>
      </div>
    );
  }

  const totalChapters = jobs.reduce((s, j) => s + j.chapter_count, 0);
  const totalWords = jobs.reduce((s, j) => s + j.total_words, 0);
  const completeJobs = jobs.filter((j) => j.status === "complete").length;
  const activeJobs = jobs.filter((j) => j.status === "generating").length;

  return (
    <motion.div
      variants={container}
      initial="hidden"
      animate="show"
      className="space-y-8"
    >
      <motion.div variants={item}>
        <h1 className="text-3xl font-semibold tracking-tight text-foreground">
          Dashboard
        </h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Overview of your research paper writing system
        </p>
      </motion.div>

      <motion.div
        variants={container}
        className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4"
      >
        <motion.div variants={item}>
          <StatCard
            icon={<FileText className="h-4 w-4" />}
            label="Total jobs"
            value={jobs.length}
          />
        </motion.div>
        <motion.div variants={item}>
          <StatCard
            icon={<BookOpen className="h-4 w-4" />}
            label="Chapters"
            value={totalChapters}
          />
        </motion.div>
        <motion.div variants={item}>
          <StatCard
            icon={<BarChart3 className="h-4 w-4" />}
            label="Total words"
            value={totalWords.toLocaleString()}
          />
        </motion.div>
        <motion.div variants={item}>
          <StatCard
            icon={<CheckCircle2 className="h-4 w-4" />}
            label="Completed"
            value={`${completeJobs}${activeJobs ? ` · ${activeJobs} active` : ""}`}
          />
        </motion.div>
      </motion.div>

      <motion.div variants={item}>
        <div className="mb-4 flex items-center justify-between">
          <h3 className="text-base font-semibold text-foreground">Recent jobs</h3>
          <Link
            href="/jobs"
            className="group inline-flex items-center gap-1 text-sm font-medium text-primary transition-colors hover:text-primary-hover"
          >
            View all
            <ArrowRight className="h-3.5 w-3.5 transition-transform group-hover:translate-x-0.5" />
          </Link>
        </div>

        {jobs.length === 0 ? (
          <EmptyDashboard />
        ) : (
          <motion.ul
            variants={container}
            className="divide-y divide-border overflow-hidden rounded-lg border border-border bg-surface"
          >
            {jobs.slice(0, 5).map((job) => (
              <motion.li key={job.id} variants={item}>
                <Link
                  href={`/jobs/${job.id}`}
                  className="group flex items-center justify-between gap-4 p-4 transition-colors hover:bg-muted/60"
                >
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-medium text-foreground group-hover:text-primary">
                      {job.topic}
                    </p>
                    <p className="mt-0.5 text-xs text-muted-foreground">
                      {job.paper_type.replace(/_/g, " ")} · {job.chapter_count}{" "}
                      chapter{job.chapter_count === 1 ? "" : "s"}
                    </p>
                  </div>
                  <StatusBadge status={job.status} size="sm" />
                </Link>
              </motion.li>
            ))}
          </motion.ul>
        )}
      </motion.div>
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
    <div className="rounded-lg border border-dashed border-border bg-surface p-8 text-center md:p-12">
      <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-lg bg-primary/10 text-primary">
        <FileText className="h-6 w-6" />
      </div>
      <h4 className="mt-4 text-base font-semibold text-foreground">
        Ready to write your first paper?
      </h4>
      <p className="mx-auto mt-1 max-w-sm text-sm text-muted-foreground">
        Set up a job and we&apos;ll research, write, and humanize each chapter for you.
      </p>
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
      <Link
        href="/jobs"
        className="mt-6 inline-flex items-center gap-2 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground shadow-sm transition-colors hover:bg-primary-hover"
      >
        <Plus className="h-4 w-4" />
        Create your first job
      </Link>
    </div>
  );
}
