"use client";

import { usePathname, useRouter } from "next/navigation";
import { useState } from "react";
import { RefreshCw, Menu, X, Search, Command } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";

const pageTitles: Record<string, string> = {
  "/": "Dashboard",
  "/jobs": "Jobs",
  "/config": "Settings",
};

const breadcrumbsByPath: Record<string, { label: string; href?: string }[]> = {
  "/": [{ label: "Dashboard" }],
  "/jobs": [{ label: "Dashboard", href: "/" }, { label: "Jobs" }],
  "/config": [{ label: "Dashboard", href: "/" }, { label: "Settings" }],
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
  const [refreshing, setRefreshing] = useState(false);

  const isJobDetail = pathname.startsWith("/jobs/") && pathname !== "/jobs";
  const isEditor = pathname.startsWith("/editor/");
  const title =
    pageTitles[pathname] ||
    (isJobDetail ? "Job Detail" : isEditor ? "Editor" : "");

  const crumbs =
    breadcrumbsByPath[pathname] ||
    (isJobDetail
      ? [
          { label: "Dashboard", href: "/" },
          { label: "Jobs", href: "/jobs" },
          { label: "Job Detail" },
        ]
      : isEditor
        ? [{ label: "Editor" }]
        : [{ label: "Dashboard" }]);

  const handleRefresh = () => {
    setRefreshing(true);
    router.refresh();
    setTimeout(() => setRefreshing(false), 600);
  };

  return (
    <header className="sticky top-0 z-30 flex h-14 items-center justify-between gap-3 border-b border-border bg-surface/80 px-4 backdrop-blur-md md:h-16 md:px-8">
      <div className="flex min-w-0 items-center gap-3">
        {onMenuToggle && (
          <button
            onClick={onMenuToggle}
            className="rounded-md p-2 text-muted-foreground transition-colors hover:bg-muted hover:text-foreground md:hidden"
            aria-label={mobileOpen ? "Close menu" : "Open menu"}
          >
            {mobileOpen ? <X className="h-4 w-4" /> : <Menu className="h-4 w-4" />}
          </button>
        )}
        <nav aria-label="Breadcrumb" className="min-w-0">
          <ol className="flex items-center gap-1.5 text-sm">
            {crumbs.map((c, i) => {
              const last = i === crumbs.length - 1;
              return (
                <li key={i} className="flex min-w-0 items-center gap-1.5">
                  {c.href && !last ? (
                    <a
                      href={c.href}
                      className="text-muted-foreground transition-colors hover:text-foreground"
                    >
                      {c.label}
                    </a>
                  ) : (
                    <span
                      className={
                        last
                          ? "truncate font-semibold text-foreground"
                          : "text-muted-foreground"
                      }
                    >
                      {c.label}
                    </span>
                  )}
                  {!last && (
                    <span className="text-muted-foreground/50">/</span>
                  )}
                </li>
              );
            })}
          </ol>
          {title && isJobDetail === false && isEditor === false && (
            <p className="sr-only">{title}</p>
          )}
        </nav>
      </div>
      <div className="flex items-center gap-1">
        <button
          onClick={() => {
            const e = new KeyboardEvent("keydown", { key: "k", metaKey: true });
            window.dispatchEvent(e);
          }}
          className="hidden items-center gap-2 rounded-md border border-border bg-surface px-2.5 py-1.5 text-xs text-muted-foreground transition-colors hover:bg-muted hover:text-foreground md:flex"
          aria-label="Open command palette"
        >
          <Search className="h-3.5 w-3.5" />
          <span>Search</span>
          <kbd className="ml-2 flex items-center gap-0.5 rounded border border-border bg-muted px-1 py-0.5 text-2xs font-medium">
            <Command className="h-2.5 w-2.5" />K
          </kbd>
        </button>
        <button
          onClick={handleRefresh}
          className="rounded-md p-2 text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
          title="Refresh"
          aria-label="Refresh page"
        >
          <AnimatePresence mode="wait" initial={false}>
            <motion.span
              key={refreshing ? "spin" : "idle"}
              initial={{ rotate: -90, opacity: 0 }}
              animate={{ rotate: 0, opacity: 1 }}
              exit={{ rotate: 90, opacity: 0 }}
              transition={{ duration: 0.15 }}
              className="block"
            >
              <RefreshCw
                className={`h-4 w-4 ${refreshing ? "animate-spin" : ""}`}
              />
            </motion.span>
          </AnimatePresence>
        </button>
      </div>
    </header>
  );
}
