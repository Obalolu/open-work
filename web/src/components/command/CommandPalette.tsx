"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import { Command } from "cmdk";
import { motion, AnimatePresence } from "framer-motion";
import {
  LayoutDashboard,
  FileText,
  Settings,
  Plus,
  RefreshCw,
  Sun,
  Moon,
  Monitor,
  Search,
  Quote,
  Shield,
  Activity,
} from "lucide-react";
import { useTheme } from "next-themes";
import { api } from "@/lib/api";
import type { Job } from "@/lib/types";
import { useKeyShortcut } from "@/hooks/useKeyShortcut";
import { cn } from "@/lib/cn";

export function CommandPalette() {
  const [open, setOpen] = React.useState(false);
  const [jobs, setJobs] = React.useState<Job[]>([]);
  const [search, setSearch] = React.useState("");
  const router = useRouter();
  const { setTheme, theme } = useTheme();

  useKeyShortcut(
    (e) => (e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k",
    (e) => {
      e.preventDefault();
      setOpen((v) => !v);
    }
  );

  React.useEffect(() => {
    if (open) {
      api.jobs.list().then(setJobs).catch(() => setJobs([]));
    }
  }, [open]);

  const runCommand = React.useCallback(
    (command: () => void) => {
      setOpen(false);
      command();
    },
    []
  );

  return (
    <AnimatePresence>
      {open && (
        <div className="fixed inset-0 z-[100]">
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.15 }}
            className="absolute inset-0 bg-foreground/40 backdrop-blur-sm"
            onClick={() => setOpen(false)}
          />
          <div className="absolute left-1/2 top-[20%] -translate-x-1/2 w-full max-w-lg px-4">
            <motion.div
              initial={{ opacity: 0, scale: 0.96, y: -8 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.96, y: -8 }}
              transition={{ type: "spring", stiffness: 400, damping: 32 }}
              className="overflow-hidden rounded-xl border border-border bg-surface-elevated shadow-2xl"
            >
              <Command label="Command palette" className="flex flex-col">
                <div
                  cmdk-input-wrapper=""
                  className="flex items-center gap-2 border-b border-border px-3"
                >
                  <Search className="h-4 w-4 shrink-0 text-muted-foreground" />
                  <Command.Input
                    value={search}
                    onValueChange={setSearch}
                    placeholder="Type a command or search…"
                    className="flex h-12 w-full bg-transparent text-sm text-foreground placeholder:text-muted-foreground/70 focus:outline-none"
                  />
                </div>
                <Command.List className="max-h-80 overflow-y-auto p-1">
                  <Command.Empty className="px-3 py-6 text-center text-sm text-muted-foreground">
                    No results found.
                  </Command.Empty>

                  <Command.Group
                    heading="Navigation"
                    className="[&_[cmdk-group-heading]]:px-2 [&_[cmdk-group-heading]]:py-1.5 [&_[cmdk-group-heading]]:text-2xs [&_[cmdk-group-heading]]:font-semibold [&_[cmdk-group-heading]]:uppercase [&_[cmdk-group-heading]]:tracking-wider [&_[cmdk-group-heading]]:text-muted-foreground"
                  >
                    <PaletteItem
                      icon={<LayoutDashboard className="h-4 w-4" />}
                      label="Go to Dashboard"
                      onSelect={() => runCommand(() => router.push("/"))}
                    />
                    <PaletteItem
                      icon={<FileText className="h-4 w-4" />}
                      label="Go to Jobs"
                      onSelect={() => runCommand(() => router.push("/jobs"))}
                    />
                    <PaletteItem
                      icon={<Settings className="h-4 w-4" />}
                      label="Go to Settings"
                      onSelect={() => runCommand(() => router.push("/config"))}
                    />
                    <PaletteItem
                      icon={<Settings className="h-4 w-4" />}
                      label="Go to Research"
                      onSelect={() => runCommand(() => router.push("/research"))}
                    />
                    <PaletteItem
                      icon={<Settings className="h-4 w-4" />}
                      label="Go to Proxy"
                      onSelect={() => runCommand(() => router.push("/proxy"))}
                    />
                    <PaletteItem
                      icon={<Settings className="h-4 w-4" />}
                      label="Go to Settings"
                      onSelect={() => runCommand(() => router.push("/config"))}
                    />
                    <PaletteItem
                      icon={<Quote className="h-4 w-4" />}
                      label="Go to Research"
                      onSelect={() => runCommand(() => router.push("/research"))}
                    />
                    <PaletteItem
                      icon={<Shield className="h-4 w-4" />}
                      label="Go to Proxy"
                      onSelect={() => runCommand(() => router.push("/proxy"))}
                    />
                    <PaletteItem
                      icon={<Activity className="h-4 w-4" />}
                      label="Go to Activity"
                      onSelect={() => runCommand(() => router.push("/activity"))}
                    />
                  </Command.Group>

                  <Command.Group
                    heading="Actions"
                    className="[&_[cmdk-group-heading]]:px-2 [&_[cmdk-group-heading]]:py-1.5 [&_[cmdk-group-heading]]:text-2xs [&_[cmdk-group-heading]]:font-semibold [&_[cmdk-group-heading]]:uppercase [&_[cmdk-group-heading]]:tracking-wider [&_[cmdk-group-heading]]:text-muted-foreground"
                  >
                    <PaletteItem
                      icon={<Plus className="h-4 w-4" />}
                      label="New job"
                      onSelect={() => runCommand(() => router.push("/jobs?new=1"))}
                    />
                    <PaletteItem
                      icon={<RefreshCw className="h-4 w-4" />}
                      label="Refresh page"
                      onSelect={() =>
                        runCommand(() => {
                          router.refresh();
                        })
                      }
                    />
                  </Command.Group>

                  <Command.Group
                    heading="Theme"
                    className="[&_[cmdk-group-heading]]:px-2 [&_[cmdk-group-heading]]:py-1.5 [&_[cmdk-group-heading]]:text-2xs [&_[cmdk-group-heading]]:font-semibold [&_[cmdk-group-heading]]:uppercase [&_[cmdk-group-heading]]:tracking-wider [&_[cmdk-group-heading]]:text-muted-foreground"
                  >
                    <PaletteItem
                      icon={<Sun className="h-4 w-4" />}
                      label="Light theme"
                      right={theme === "light" ? "✓" : undefined}
                      onSelect={() =>
                        runCommand(() => setTheme("light"))
                      }
                    />
                    <PaletteItem
                      icon={<Moon className="h-4 w-4" />}
                      label="Dark theme"
                      right={theme === "dark" ? "✓" : undefined}
                      onSelect={() =>
                        runCommand(() => setTheme("dark"))
                      }
                    />
                    <PaletteItem
                      icon={<Monitor className="h-4 w-4" />}
                      label="System theme"
                      right={theme === "system" ? "✓" : undefined}
                      onSelect={() =>
                        runCommand(() => setTheme("system"))
                      }
                    />
                  </Command.Group>

                  {jobs.length > 0 && (
                    <Command.Group
                      heading="Recent jobs"
                      className="[&_[cmdk-group-heading]]:px-2 [&_[cmdk-group-heading]]:py-1.5 [&_[cmdk-group-heading]]:text-2xs [&_[cmdk-group-heading]]:font-semibold [&_[cmdk-group-heading]]:uppercase [&_[cmdk-group-heading]]:tracking-wider [&_[cmdk-group-heading]]:text-muted-foreground"
                    >
                      {jobs.slice(0, 5).map((job) => (
                        <PaletteItem
                          key={job.id}
                          icon={<FileText className="h-4 w-4" />}
                          label={job.topic}
                          right={job.status}
                          onSelect={() =>
                            runCommand(() => router.push(`/jobs/${job.id}`))
                          }
                        />
                      ))}
                    </Command.Group>
                  )}
                </Command.List>
                <div className="flex items-center justify-between border-t border-border px-3 py-2 text-2xs text-muted-foreground">
                  <div className="flex items-center gap-2">
                    <kbd className="rounded border border-border bg-muted px-1.5 font-mono">
                      ↑↓
                    </kbd>
                    <span>navigate</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <kbd className="rounded border border-border bg-muted px-1.5 font-mono">
                      ↵
                    </kbd>
                    <span>select</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <kbd className="rounded border border-border bg-muted px-1.5 font-mono">
                      esc
                    </kbd>
                    <span>close</span>
                  </div>
                </div>
              </Command>
            </motion.div>
          </div>
        </div>
      )}
    </AnimatePresence>
  );
}

function PaletteItem({
  icon,
  label,
  right,
  onSelect,
}: {
  icon: React.ReactNode;
  label: string;
  right?: string;
  onSelect: () => void;
}) {
  return (
    <Command.Item
      onSelect={onSelect}
      className={cn(
        "relative flex cursor-default select-none items-center gap-2 rounded-sm px-2 py-2 text-sm outline-none",
        "data-[selected=true]:bg-muted data-[selected=true]:text-foreground",
        "aria-[selected=true]:bg-muted"
      )}
    >
      <span className="text-muted-foreground">{icon}</span>
      <span className="flex-1 truncate text-foreground">{label}</span>
      {right && (
        <span className="text-2xs uppercase tracking-wider text-muted-foreground">
          {right}
        </span>
      )}
    </Command.Item>
  );
}
