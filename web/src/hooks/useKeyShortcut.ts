"use client";

import { useEffect } from "react";

type Key = string | ((e: KeyboardEvent) => boolean);

export function useKeyShortcut(
  key: Key,
  handler: (e: KeyboardEvent) => void,
  options: { meta?: boolean; shift?: boolean; alt?: boolean; preventDefault?: boolean } = {}
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

      if (options.preventDefault !== false) e.preventDefault();
      handler(e);
    };

    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [key, handler, options.meta, options.shift, options.alt, options.preventDefault]);
}
