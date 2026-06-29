"use client";

export default function JobsError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <div className="flex flex-col items-center justify-center min-h-[60vh]">
      <h1 className="text-2xl font-bold text-slate-800 mb-2">Failed to load jobs</h1>
      <p className="text-slate-500 mb-6 text-sm max-w-md text-center">
        {error.message || "Could not load job data"}
      </p>
      <button
        onClick={reset}
        className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700"
      >
        Try again
      </button>
    </div>
  );
}
