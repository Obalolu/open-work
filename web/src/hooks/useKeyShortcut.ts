"use client";

import { useEffect } from "react";

type Key = string | ((e: KeyboardEvent) => boolean);

export function useKeyShortcut(
  key: Key,
  handler: (e: KeyboardEvent) => void,
  options: {
    meta?: boolean;
    shift?: boolean;
    alt?: boolean;
    /**
     * If true (default), do not fire while focus is in an input, textarea,
     * or contenteditable element. Pass `false` to override.
     */
    ignoreInputs?: boolean;
    preventDefault?: boolean;
  } = {}
) {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const matched =
        typeof key === "function"
          ? key(e)
          : e.key.toLowerCase() === key.toLowerCase();

      if (!matched) return;

      if (options.meta && !(e.metaKey || e.ctrlKey)) return;
      if (options.shift && !e.shiftKey) return;
      if (options.alt && !e.altKey) return;

      const ignoreInputs = options.ignoreInputs !== false;
      if (ignoreInputs) {
        const target = e.target as HTMLElement | null;
        if (target) {
          const tag = target.tagName;
          if (
            tag === "INPUT" ||
            tag === "TEXTAREA" ||
            tag === "SELECT" ||
            target.isContentEditable
          ) {
            return;
          }
        }
      }

      if (options.preventDefault !== false) e.preventDefault();
      handler(e);
    };

    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [
    key,
    handler,
    options.meta,
    options.shift,
    options.alt,
    options.ignoreInputs,
    options.preventDefault,
  ]);
}
