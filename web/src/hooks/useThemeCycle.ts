"use client";

import { useCallback, useEffect, useState } from "react";
import { useTheme } from "next-themes";

export type ThemeChoice = "light" | "dark" | "system";
const ORDER: ThemeChoice[] = ["light", "dark", "system"];

/**
 * Theme cycling shared by the sidebar toggle and the "T" global shortcut.
 * Returns the current choice (only meaningful after mount), the resolved
 * theme next-themes thinks is active, a hydration flag, and a `cycle` fn.
 */
export function useThemeCycle() {
  const { setTheme, theme, resolvedTheme } = useTheme();
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  const cycle = useCallback(() => {
    const current = (theme as ThemeChoice | undefined) ?? "system";
    const idx = ORDER.indexOf(current);
    setTheme(ORDER[(idx + 1) % ORDER.length]);
  }, [setTheme, theme]);

  return {
    cycle,
    current: (theme as ThemeChoice | undefined) ?? "system",
    resolved: resolvedTheme,
    mounted,
  };
}
