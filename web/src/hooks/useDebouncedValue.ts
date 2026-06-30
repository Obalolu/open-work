"use client";

import { useEffect, useState } from "react";

/**
 * Debounce a rapidly-changing value. Returns the value that has been stable
 * for `delay` ms. The first change is reported immediately, subsequent
 * changes inside the window are coalesced.
 */
export function useDebouncedValue<T>(value: T, delay = 200): T {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    if (Object.is(debounced, value)) return;
    const t = setTimeout(() => setDebounced(value), delay);
    return () => clearTimeout(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [value, delay]);
  return debounced;
}
