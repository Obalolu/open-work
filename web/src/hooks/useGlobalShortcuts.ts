"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useTheme } from "next-themes";
import { useKeyShortcut } from "@/hooks/useKeyShortcut";

/**
 * Global keyboard shortcuts. Mounted once in the Providers tree.
 *
 * N        – toggle new-job drawer (only fires on /jobs)
 * /        – focus search inputs across pages
 * G then D – go to dashboard
 * G then J – go to jobs
 * G then S – go to settings
 * G then R – go to research
 * G then P – go to proxy
 * G then A – go to activity
 * T        – cycle theme
 * ?        – open shortcut help
 */
export function useGlobalShortcuts({
  onShowHelp,
}: {
  onShowHelp: () => void;
}) {
  const router = useRouter();
  const { setTheme, theme } = useTheme();

  useKeyShortcut("/", () => {
    const target = document.querySelector<HTMLInputElement>(
      "input[data-shortcut-focus], input[type='search']"
    );
    target?.focus();
    target?.select();
  });

  useKeyShortcut("?", () => onShowHelp());

  useKeyShortcut("t", () => {
    const order = ["light", "dark", "system"] as const;
    const current = (theme ?? "system") as (typeof order)[number];
    const idx = order.indexOf(current);
    const next = order[(idx + 1) % order.length];
    setTheme(next);
  });

  // "G then X" sequence
  useEffect(() => {
    let lastG = 0;
    const handler = (e: KeyboardEvent) => {
      if (e.metaKey || e.ctrlKey || e.altKey) return;
      const target = e.target as HTMLElement | null;
      if (target && (target.tagName === "INPUT" || target.tagName === "TEXTAREA" || target.isContentEditable)) {
        return;
      }
      const now = Date.now();
      if (e.key.toLowerCase() === "g" && now - lastG < 800) {
        lastG = 0;
        return;
      }
      if (e.key.toLowerCase() === "g") {
        lastG = now;
        return;
      }
      if (now - lastG > 800) return;
      switch (e.key.toLowerCase()) {
        case "d":
          router.push("/");
          break;
        case "j":
          router.push("/jobs");
          break;
        case "s":
          router.push("/config");
          break;
        case "r":
          router.push("/research");
          break;
        case "p":
          router.push("/proxy");
          break;
        case "a":
          router.push("/activity");
          break;
      }
      lastG = 0;
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [router]);
}
