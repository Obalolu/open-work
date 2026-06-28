"use client";

import { useEffect, useRef, useCallback, useState } from "react";
import type { GenerationStatus } from "@/lib/types";

export function usePolling(
  jobId: string | null,
  pollFn: (jobId: string) => Promise<GenerationStatus>,
  intervalMs = 2000
) {
  const [status, setStatus] = useState<GenerationStatus | null>(null);
  const [isPolling, setIsPolling] = useState(false);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const stopPolling = useCallback(() => {
    if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }
    setIsPolling(false);
  }, []);

  const startPolling = useCallback(() => {
    if (!jobId) return;
    setIsPolling(true);

    const poll = async () => {
      try {
        const s = await pollFn(jobId);
        setStatus(s);
        if (s.phase === "complete" || s.phase === "error" || s.phase === "idle") {
          stopPolling();
        }
      } catch {
        stopPolling();
      }
    };

    poll();
    timerRef.current = setInterval(poll, intervalMs);
  }, [jobId, pollFn, intervalMs, stopPolling]);

  useEffect(() => {
    return () => stopPolling();
  }, [stopPolling]);

  return { status, isPolling, startPolling, stopPolling };
}
