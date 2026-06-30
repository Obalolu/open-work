"use client";

import * as React from "react";
import { motion } from "framer-motion";
import {
  CheckCircle2,
  Circle,
  Search,
  PenLine,
  ShieldCheck,
  Download,
  X,
  Loader2,
  AlertTriangle,
  Brain,
} from "lucide-react";
import { Card, CardContent } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Progress } from "@/components/ui/Progress";
import { cn } from "@/lib/cn";
import { api, streamGeneration } from "@/lib/api";

const phases = [
  { key: "research", label: "Research", icon: Search },
  { key: "writing", label: "Write", icon: PenLine },
  { key: "review", label: "Review", icon: ShieldCheck },
  { key: "humanize", label: "Humanize", icon: Brain },
  { key: "export", label: "Export", icon: Download },
] as const;

export interface GenerationStreamProps {
  jobId: string;
  jobTopic?: string;
  initialPhase?: string;
  initialProgress?: number;
  initialMessage?: string;
  onComplete?: () => void;
  onCancel?: () => void;
}

export function GenerationStream({
  jobId,
  jobTopic,
  initialPhase,
  initialProgress,
  initialMessage,
  onComplete,
  onCancel,
}: GenerationStreamProps) {
  const [phase, setPhase] = React.useState(initialPhase ?? "queued");
  const [progress, setProgress] = React.useState(initialProgress ?? 0);
  const [message, setMessage] = React.useState(initialMessage ?? "Waiting…");
  const [chapterStatuses, setChapterStatuses] = React.useState<
    Record<number, { status: string; progress: number; message: string }>
  >({});
  const [preview, setPreview] = React.useState("");
  const [previewChapter, setPreviewChapter] = React.useState<number | null>(null);
  const [previewPhase, setPreviewPhase] = React.useState<string | null>(null);
  const [finished, setFinished] = React.useState(
    initialPhase === "complete" || initialPhase === "error"
  );
  const [error, setError] = React.useState<string | null>(null);
  const [cancelling, setCancelling] = React.useState(false);
  const previewRef = React.useRef<HTMLDivElement | null>(null);
  const abortRef = React.useRef<AbortController | null>(null);
  const completedRef = React.useRef(false);

  React.useEffect(() => {
    if (finished) return;
    const ac = new AbortController();
    abortRef.current = ac;
    (async () => {
      try {
        for await (const event of streamGeneration(jobId, ac.signal)) {
          const type = event.type as string;
          if (type === "snapshot") {
            setPhase((event.phase as string) ?? "queued");
            setProgress((event.progress as number) ?? 0);
            setMessage((event.message as string) ?? "…");
          } else if (type === "phase") {
            setPhase((event.phase as string) ?? phase);
            setProgress((event.progress as number) ?? progress);
            setMessage((event.message as string) ?? "");
          } else if (type === "chapter") {
            const num = event.chapter as number;
            setChapterStatuses((prev) => ({
              ...prev,
              [num]: {
                status: (event.status as string) ?? "pending",
                progress: (event.progress as number) ?? 0,
                message: (event.message as string) ?? "",
              },
            }));
            // When a chapter leaves the streaming phase, freeze its preview
            if (
              previewChapter === num &&
              (event.status as string) &&
              !["writing", "humanize"].includes(event.status as string)
            ) {
              // keep the buffer; user can read what was written
            }
            if ((event.status as string) === "pending" || (event.status as string) === "queued") {
              // new chapter starting; clear previous buffer
              if (previewChapter !== num) {
                setPreview("");
                setPreviewChapter(num);
                setPreviewPhase(null);
              }
            }
          } else if (type === "chunk") {
            const text = (event.text as string) ?? "";
            const num = event.chapter as number;
            const ph = (event.phase as string) ?? null;
            setPreviewChapter(num);
            setPreviewPhase(ph);
            setPreview((p) => (p + text).slice(-20000));
          } else if (type === "complete") {
            setPhase("complete");
            setProgress(100);
            setMessage("Generation complete");
            setFinished(true);
            if (!completedRef.current) {
              completedRef.current = true;
              onComplete?.();
            }
          } else if (type === "error") {
            setPhase("error");
            setMessage((event.message as string) ?? "Generation failed");
            setFinished(true);
            setError((event.message as string) ?? "Generation failed");
          } else if (type === "cancelled") {
            setPhase("cancelled");
            setMessage("Generation cancelled");
            setFinished(true);
            onCancel?.();
          }
        }
      } catch (e) {
        if ((e as Error).name === "AbortError") return;
        setError(e instanceof Error ? e.message : String(e));
      }
    })();
    return () => {
      ac.abort();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [jobId]);

  // Auto-scroll the live preview to the bottom as text streams in
  React.useEffect(() => {
    const el = previewRef.current;
    if (!el) return;
    el.scrollTop = el.scrollHeight;
  }, [preview]);

  const handleCancel = async () => {
    setCancelling(true);
    try {
      await api.generate.cancel(jobId);
    } catch {
      // ignore — UI will pick up the cancel from the stream
    }
    setCancelling(false);
  };

  if (finished && phase === "complete") {
    return (
      <Card className="border-success-soft bg-success-soft/40">
        <CardContent className="flex items-center gap-3 py-4">
          <div className="flex h-9 w-9 items-center justify-center rounded-full bg-success-soft text-success">
            <CheckCircle2 className="h-5 w-5" />
          </div>
          <div>
            <p className="text-sm font-medium text-foreground">
              Generation complete
            </p>
            {jobTopic && (
              <p className="text-2xs text-muted-foreground">{jobTopic}</p>
            )}
          </div>
        </CardContent>
      </Card>
    );
  }

  if (finished && phase === "error") {
    return (
      <Card className="border-danger-soft bg-danger-soft/40">
        <CardContent className="flex items-start gap-3 py-4">
          <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-danger-soft text-danger">
            <AlertTriangle className="h-5 w-5" />
          </div>
          <div className="flex-1">
            <p className="text-sm font-medium text-foreground">Generation failed</p>
            <p className="mt-0.5 text-2xs text-muted-foreground">{error || message}</p>
          </div>
        </CardContent>
      </Card>
    );
  }

  if (finished && phase === "cancelled") {
    return (
      <Card className="border-warning-soft bg-warning-soft/40">
        <CardContent className="flex items-center gap-3 py-4">
          <div className="flex h-9 w-9 items-center justify-center rounded-full bg-warning-soft text-warning">
            <X className="h-5 w-5" />
          </div>
          <p className="text-sm font-medium text-foreground">Generation cancelled</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardContent className="space-y-5 py-5">
        <div className="flex items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <Loader2 className="h-4 w-4 animate-spin text-info" />
            <span className="text-sm font-medium text-foreground">
              Generating
              {jobTopic && (
                <span className="ml-1 text-muted-foreground"> · {jobTopic}</span>
              )}
            </span>
          </div>
          <Button
            variant="ghost"
            size="sm"
            onClick={handleCancel}
            loading={cancelling}
            className="text-muted-foreground hover:text-danger"
          >
            <X />
            Cancel
          </Button>
        </div>

        <PhaseStepper currentPhase={phase} />

        <div className="space-y-1.5">
          <div className="flex items-center justify-between text-2xs text-muted-foreground">
            <span className="truncate">{message}</span>
            <span>{progress}%</span>
          </div>
          <Progress value={progress} className="bg-info/15" indicatorClassName="bg-info" />
        </div>

        {Object.keys(chapterStatuses).length > 0 && (
          <ul className="grid gap-2 sm:grid-cols-2">
            {Object.entries(chapterStatuses).map(([num, cs]) => (
              <li
                key={num}
                className="flex items-center gap-2 rounded-md border border-border bg-background px-3 py-2"
              >
                <ChapterStatusDot status={cs.status} />
                <span className="text-sm font-medium text-foreground">
                  Chapter {num}
                </span>
                <span className="truncate text-2xs text-muted-foreground">
                  {cs.message || cs.status}
                </span>
              </li>
            ))}
          </ul>
        )}

        {preview && previewChapter !== null && (
          <div className="space-y-1.5">
            <div className="flex items-center justify-between text-2xs text-muted-foreground">
              <span>
                Live preview · Chapter {previewChapter}
                {previewPhase && ` · ${previewPhase}`}
              </span>
              <span>{preview.length.toLocaleString()} chars</span>
            </div>
            <div
              ref={previewRef}
              className="max-h-48 overflow-auto rounded-md border border-border bg-background p-3 font-mono text-2xs leading-relaxed text-foreground"
            >
              <pre className="whitespace-pre-wrap">{preview}</pre>
              <span className="ml-0.5 inline-block h-3 w-1.5 animate-pulse bg-primary align-middle" />
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function PhaseStepper({ currentPhase }: { currentPhase: string }) {
  const currentIndex = phases.findIndex((p) => p.key === currentPhase);
  return (
    <ol className="flex items-center justify-between gap-1 overflow-x-auto">
      {phases.map((p, i) => {
        const state =
          i < currentIndex ? "done" : i === currentIndex ? "active" : "pending";
        const Icon = p.icon;
        return (
          <li key={p.key} className="flex flex-1 items-center gap-1.5">
            <motion.div
              initial={false}
              animate={{
                scale: state === "active" ? 1.05 : 1,
              }}
              className={cn(
                "flex h-8 w-8 shrink-0 items-center justify-center rounded-full border transition-colors",
                state === "done" &&
                  "border-success bg-success text-success-foreground",
                state === "active" &&
                  "border-info bg-info-soft text-info",
                state === "pending" && "border-border bg-surface text-muted-foreground"
              )}
            >
              {state === "done" ? (
                <CheckCircle2 className="h-4 w-4" />
              ) : state === "active" ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Icon className="h-3.5 w-3.5" />
              )}
            </motion.div>
            <div className="hidden min-w-0 sm:block">
              <p
                className={cn(
                  "text-2xs font-medium",
                  state === "pending"
                    ? "text-muted-foreground"
                    : "text-foreground"
                )}
              >
                {p.label}
              </p>
            </div>
            {i < phases.length - 1 && (
              <div className="mx-1 hidden h-px flex-1 bg-border sm:block" />
            )}
          </li>
        );
      })}
    </ol>
  );
}

function ChapterStatusDot({ status }: { status: string }) {
  if (status === "complete") {
    return <CheckCircle2 className="h-4 w-4 text-success" />;
  }
  if (
    ["error", "failed"].includes(status)
  ) {
    return <AlertTriangle className="h-4 w-4 text-danger" />;
  }
  if (
    [
      "research",
      "writing",
      "review",
      "humanize",
      "export",
      "starting",
      "queued",
    ].includes(status)
  ) {
    return <Loader2 className="h-4 w-4 animate-spin text-info" />;
  }
  return <Circle className="h-4 w-4 text-muted-foreground" />;
}
