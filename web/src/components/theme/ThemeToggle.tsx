"use client";

import { Moon, Sun, Monitor } from "lucide-react";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/Tooltip";
import { useThemeCycle } from "@/hooks/useThemeCycle";

export function ThemeToggle() {
  const { cycle, current, mounted } = useThemeCycle();

  const label = !mounted
    ? "Theme"
    : current === "system"
      ? "System"
      : current === "dark"
        ? "Dark"
        : "Light";

  const Icon = !mounted
    ? Monitor
    : current === "system"
      ? Monitor
      : current === "dark"
        ? Moon
        : Sun;

  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <button
          onClick={cycle}
          className="relative inline-flex h-8 w-8 items-center justify-center overflow-hidden rounded-md border border-border bg-surface text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
          aria-label={`Theme: ${label}. Click to change.`}
        >
          <Icon className="h-4 w-4" />
        </button>
      </TooltipTrigger>
      <TooltipContent>
        <p className="font-medium">{label}</p>
        <p className="text-2xs text-muted-foreground">Click or press T</p>
      </TooltipContent>
    </Tooltip>
  );
}
