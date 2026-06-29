"use client";

const colorMap: Record<string, string> = {
  draft: "bg-slate-100 text-slate-600",
  pending: "bg-slate-100 text-slate-600",
  generating: "bg-blue-100 text-blue-700",
  complete: "bg-green-100 text-green-700",
  error: "bg-red-100 text-red-700",
};

export function StatusBadge({
  status,
  size = "md",
}: {
  status: string;
  size?: "sm" | "md";
}) {
  const padding = size === "sm" ? "px-2 py-0.5" : "px-3 py-1";
  return (
    <span
      role="status"
      className={`${padding} rounded-full text-xs font-medium ${
        colorMap[status] || colorMap.pending
      }`}
    >
      {status}
    </span>
  );
}
