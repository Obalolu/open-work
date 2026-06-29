"use client";

import { usePathname, useRouter } from "next/navigation";
import { RefreshCw, Menu, X } from "lucide-react";

const pageTitles: Record<string, string> = {
  "/": "Dashboard",
  "/jobs": "Jobs",
  "/config": "Settings",
};

export function Header({
  onMenuToggle,
  mobileOpen,
}: {
  onMenuToggle?: () => void;
  mobileOpen?: boolean;
}) {
  const pathname = usePathname();
  const router = useRouter();
  const title =
    pageTitles[pathname] ||
    (pathname.startsWith("/jobs/") ? "Job Detail" : "Editor");

  return (
    <header className="h-14 md:h-16 border-b border-slate-200 bg-white flex items-center justify-between px-4 md:px-8">
      <div className="flex items-center gap-3">
        {onMenuToggle && (
          <button
            onClick={onMenuToggle}
            className="p-2 text-slate-400 hover:text-slate-600 rounded-lg hover:bg-slate-100 md:hidden"
            aria-label={mobileOpen ? "Close menu" : "Open menu"}
          >
            {mobileOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
          </button>
        )}
        <h2 className="text-lg font-semibold text-slate-800">{title}</h2>
      </div>
      <button
        onClick={() => router.refresh()}
        className="p-2 text-slate-400 hover:text-slate-600 rounded-lg hover:bg-slate-100"
        title="Refresh"
        aria-label="Refresh page"
      >
        <RefreshCw className="w-5 h-5" />
      </button>
    </header>
  );
}
