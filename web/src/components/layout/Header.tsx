"use client";

import { usePathname, useRouter } from "next/navigation";
import { RefreshCw } from "lucide-react";

const pageTitles: Record<string, string> = {
  "/": "Dashboard",
  "/jobs": "Jobs",
  "/config": "Settings",
};

export function Header() {
  const pathname = usePathname();
  const router = useRouter();
  const title =
    pageTitles[pathname] ||
    (pathname.startsWith("/jobs/") ? "Job Detail" : "Editor");

  return (
    <header className="h-16 border-b border-slate-200 bg-white flex items-center justify-between px-8">
      <h2 className="text-lg font-semibold text-slate-800">{title}</h2>
      <button
        onClick={() => router.refresh()}
        className="p-2 text-slate-400 hover:text-slate-600 rounded-lg hover:bg-slate-100"
        title="Refresh"
      >
        <RefreshCw className="w-5 h-5" />
      </button>
    </header>
  );
}
