"use client";

import { useCallback, useState } from "react";
import { useTheme } from "next-themes";

export type ThemeChoice = "light" | "dark" | "system";
const ORDER: ThemeChoice[] = ["light", "dark", "system"];

/**
 * Theme cycling shared by the sidebar toggle and the "T" global shortcut.
 * Returns the current resolved choice and a `cycle` function.
 */
export function useThemeCycle() {
  const { setTheme, theme, resolvedTheme } = useTheme();
  const [mounted, setMounted] = useState(false);

  // `useTheme` returns "undefined" on the first render; mark mounted after
  // hydration so we can show the right icon without a hydration mismatch.
  if (typeof window !== "undefined" && !mounted) {
    // microtask-safe: the first client render reads mounted=false and the
    // effect below flips it to true.
  }

  const cycle = useCallback(() => {
    const current = (theme as ThemeChoice) ?? "system";
    const idx = ORDER.indexOf(current);
    setTheme(ORDER[(idx + 1) % ORDER.length]);
  }, [setTheme, theme]);

  return {
    cycle,
    current: (theme as ThemeChoice) ?? "system",
    resolved: resolvedTheme,
    mounted,
    setMounted,
  };
}
