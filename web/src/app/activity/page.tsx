"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/Card";
import { Skeleton } from "@/components/ui/Skeleton";
import { Empty } from "@/components/ui/Empty";
import { Badge } from "@/components/ui/Badge";
import { motion } from "framer-motion";
import { formatDistanceToNow } from "date-fns";
import {
  Activity as ActivityIcon,
  FileText,
  Plus,
  Trash2,
  RefreshCw,
  CheckCircle2,
  AlertCircle,
  Pencil,
  Sparkles,
} from "lucide-react";
import type { Job } from "@/lib/types";

interface Event {
  id: string;
  type: "job_created" | "job_deleted" | "job_completed" | "job_error" | "job_started";
  timestamp: string;
  jobId: string;
  topic: string;
}

export default function ActivityPage() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.jobs.list().then((js) => {
      setJobs(js);
      setLoading(false);
    });
  }, []);

  const events: Event[] = jobs
    .flatMap((j) => {
      const created: Event = {
        id: `${j.id}-created`,
        type: "job_created",
        timestamp: j.created_at,
        jobId: j.id,
        topic: j.topic,
      };
      const completed: Event | null =
        j.status === "complete"
          ? {
              id: `${j.id}-complete`,
              type: "job_completed",
              timestamp: j.updated_at,
              jobId: j.id,
              topic: j.topic,
            }
          : null;
      const errored: Event | null =
        j.status === "error"
          ? {
              id: `${j.id}-error`,
              type: "job_error",
              timestamp: j.updated_at,
              jobId: j.id,
              topic: j.topic,
            }
          : null;
      return [created, completed, errored].filter(Boolean) as Event[];
    })
    .sort((a, b) => (a.timestamp < b.timestamp ? 1 : -1))
    .slice(0, 100);

  if (loading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-9 w-40" />
        {Array.from({ length: 5 }).map((_, i) => (
          <Skeleton key={i} className="h-16" />
        ))}
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-semibold tracking-tight text-foreground">
          Activity
        </h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Global feed of jobs created, completed, and failed
        </p>
      </div>

      {events.length === 0 ? (
        <Empty
          variant="bordered"
          icon={<ActivityIcon className="h-6 w-6" />}
          title="No activity yet"
          description="Activity will appear here as you create and run jobs."
        />
      ) : (
        <Card>
          <CardHeader>
            <CardTitle>Recent activity</CardTitle>
            <CardDescription>Last 100 events across all jobs</CardDescription>
          </CardHeader>
          <CardContent className="pt-0">
            <motion.ol
              initial="hidden"
              animate="show"
              variants={{
                hidden: { opacity: 0 },
                show: { opacity: 1, transition: { staggerChildren: 0.02 } },
              }}
              className="divide-y divide-border"
            >
              {events.map((e) => (
                <motion.li
                  key={e.id}
                  variants={{ hidden: { opacity: 0, y: 4 }, show: { opacity: 1, y: 0 } }}
                  className="flex items-center justify-between gap-3 py-3 first:pt-0 last:pb-0"
                >
                  <div className="flex min-w-0 items-center gap-3">
                    <EventIcon type={e.type} />
                    <div className="min-w-0">
                      <p className="truncate text-sm text-foreground">
                        <EventLabel event={e} />
                      </p>
                      <p className="mt-0.5 text-2xs text-muted-foreground">
                        {formatDistanceToNow(new Date(e.timestamp), { addSuffix: true })}
                      </p>
                    </div>
                  </div>
                  <Link
                    href={`/jobs/${e.jobId}`}
                    className="shrink-0 text-2xs text-primary hover:underline"
                  >
                    View →
                  </Link>
                </motion.li>
              ))}
            </motion.ol>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

function EventIcon({ type }: { type: Event["type"] }) {
  const map: Record<Event["type"], { icon: React.ReactNode; tone: string }> = {
    job_created: { icon: <Plus className="h-3.5 w-3.5" />, tone: "text-info" },
    job_completed: { icon: <CheckCircle2 className="h-3.5 w-3.5" />, tone: "text-success" },
    job_error: { icon: <AlertCircle className="h-3.5 w-3.5" />, tone: "text-danger" },
    job_started: { icon: <RefreshCw className="h-3.5 w-3.5" />, tone: "text-warning" },
    job_deleted: { icon: <Trash2 className="h-3.5 w-3.5" />, tone: "text-danger" },
  };
  const { icon, tone } = map[type];
  return (
    <div className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-muted ${tone}`}>
      {icon}
    </div>
  );
}

function EventLabel({ event }: { event: Event }) {
  switch (event.type) {
    case "job_created":
      return (
        <>
          <Badge variant="info" className="mr-1">Created</Badge>
          {event.topic}
        </>
      );
    case "job_completed":
      return (
        <>
          <Badge variant="success" className="mr-1">Completed</Badge>
          {event.topic}
        </>
      );
    case "job_error":
      return (
        <>
          <Badge variant="danger" className="mr-1">Error</Badge>
          {event.topic}
        </>
      );
    case "job_started":
      return (
        <>
          <Badge variant="warning" className="mr-1">Started</Badge>
          {event.topic}
        </>
      );
    case "job_deleted":
      return (
        <>
          <Badge variant="danger" className="mr-1">Deleted</Badge>
          {event.topic}
        </>
      );
    default:
      return <>{event.topic}</>;
  }
}
