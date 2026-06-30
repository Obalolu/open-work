"use client";

import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/Dialog";
import { Kbd } from "@/components/ui/Kbd";

const groups: { label: string; items: { keys: string[]; label: string }[] }[] = [
  {
    label: "Navigation",
    items: [
      { keys: ["G", "D"], label: "Go to Dashboard" },
      { keys: ["G", "J"], label: "Go to Jobs" },
      { keys: ["G", "R"], label: "Go to Research" },
      { keys: ["G", "P"], label: "Go to Proxy" },
      { keys: ["G", "A"], label: "Go to Activity" },
      { keys: ["G", "S"], label: "Go to Settings" },
    ],
  },
  {
    label: "Actions",
    items: [
      { keys: ["⌘", "K"], label: "Open command palette" },
      { keys: ["N"], label: "New job (on /jobs)" },
      { keys: ["/"], label: "Focus search" },
      { keys: ["T"], label: "Cycle theme" },
    ],
  },
  {
    label: "General",
    items: [
      { keys: ["?"], label: "Show this help" },
      { keys: ["Esc"], label: "Close any modal" },
    ],
  },
];

export function ShortcutHelp({
  open,
  onOpenChange,
}: {
  open: boolean;
  onOpenChange: (v: boolean) => void;
}) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent size="md">
        <DialogHeader>
          <DialogTitle>Keyboard shortcuts</DialogTitle>
          <DialogDescription>
            Navigate the app without leaving the keyboard.
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-5">
          {groups.map((g) => (
            <div key={g.label}>
              <p className="mb-2 text-2xs font-semibold uppercase tracking-wider text-muted-foreground">
                {g.label}
              </p>
              <ul className="space-y-1.5">
                {g.items.map((it) => (
                  <li
                    key={it.label}
                    className="flex items-center justify-between gap-3 rounded-md px-2 py-1.5 text-sm hover:bg-muted"
                  >
                    <span className="text-foreground">{it.label}</span>
                    <span className="flex items-center gap-1">
                      {it.keys.map((k, i) => (
                        <span key={i} className="flex items-center gap-1">
                          <Kbd>{k}</Kbd>
                          {i < it.keys.length - 1 && (
                            <span className="text-2xs text-muted-foreground">
                              {k === "G" ? "then" : "+"}
                            </span>
                          )}
                        </span>
                      ))}
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      </DialogContent>
    </Dialog>
  );
}
