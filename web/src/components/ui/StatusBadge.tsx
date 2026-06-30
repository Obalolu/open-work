"use client";

import { cn } from "@/lib/cn";

const colorMap: Record<string, string> = {
  draft: "bg-subtle text-subtle-foreground",
  pending: "bg-subtle text-subtle-foreground",
  queued: "bg-info-soft text-info",
  starting: "bg-info-soft text-info",
  research: "bg-info-soft text-info",
  writing: "bg-info-soft text-info",
  review: "bg-warning-soft text-warning",
  humanize: "bg-warning-soft text-warning",
  export: "bg-info-soft text-info",
  generating: "bg-info-soft text-info",
  complete: "bg-success-soft text-success",
  error: "bg-danger-soft text-danger",
};

const dotMap: Record<string, string> = {
  generating: "bg-info animate-pulse-soft",
  starting: "bg-info animate-pulse-soft",
  queued: "bg-info animate-pulse-soft",
  research: "bg-info animate-pulse-soft",
  writing: "bg-info animate-pulse-soft",
  review: "bg-warning animate-pulse-soft",
  humanize: "bg-warning animate-pulse-soft",
  export: "bg-info animate-pulse-soft",
};

export function StatusBadge({
  status,
  size = "md",
}: {
  status: string;
  size?: "sm" | "md";
}) {
  const padding = size === "sm" ? "px-2 py-0.5 text-2xs" : "px-2.5 py-0.5 text-xs";
  const showDot = ["generating", "queued", "writing", "research", "humanize", "review", "starting", "export"].includes(
    status
  );
  return (
    <span
      role="status"
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full font-medium",
        padding,
        colorMap[status] || colorMap.pending
      )}
    >
      {showDot && (
        <span
          className={cn(
            "h-1.5 w-1.5 rounded-full",
            dotMap[status] || "bg-muted-foreground"
          )}
        />
      )}
      {status}
    </span>
  );
}
