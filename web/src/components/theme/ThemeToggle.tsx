"use client";

import { useEffect, useState } from "react";
import { useTheme } from "next-themes";
import { Moon, Sun, Monitor } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/Tooltip";

type Theme = "light" | "dark" | "system";

const order: Theme[] = ["light", "dark", "system"];

export function ThemeToggle() {
  const { theme, setTheme, resolvedTheme } = useTheme();
  const [mounted, setMounted] = useState(false);

  useEffect(() => setMounted(true), []);

  const current = (theme as Theme) ?? "system";

  const cycle = () => {
    const idx = order.indexOf(current);
    const next = order[(idx + 1) % order.length];
    setTheme(next);
  };

  const Icon = !mounted
    ? Monitor
    : current === "system"
      ? Monitor
      : current === "dark"
        ? Moon
        : Sun;

  const label = !mounted
    ? "Theme"
    : current === "system"
      ? `System (${resolvedTheme})`
      : current === "dark"
        ? "Dark"
        : "Light";

  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <button
          onClick={cycle}
          className="relative inline-flex h-8 w-8 items-center justify-center overflow-hidden rounded-md border border-border bg-surface text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
          aria-label={`Theme: ${label}. Click to change.`}
        >
          <AnimatePresence mode="wait" initial={false}>
            <motion.span
              key={current}
              initial={{ y: -16, opacity: 0, rotate: -45 }}
              animate={{ y: 0, opacity: 1, rotate: 0 }}
              exit={{ y: 16, opacity: 0, rotate: 45 }}
              transition={{ duration: 0.18, ease: [0.16, 1, 0.3, 1] }}
              className="block"
            >
              <Icon className="h-4 w-4" />
            </motion.span>
          </AnimatePresence>
        </button>
      </TooltipTrigger>
      <TooltipContent>
        <p className="font-medium">{label}</p>
        <p className="text-2xs text-muted-foreground">Click to switch</p>
      </TooltipContent>
    </Tooltip>
  );
}
