import { Skeleton } from "@/components/ui/Skeleton";

export default function JobsLoading() {
  return (
    <div className="space-y-4">
      <div className="flex items-end justify-between">
        <div className="space-y-2">
          <Skeleton className="h-8 w-24" />
          <Skeleton className="h-3 w-48" />
        </div>
        <Skeleton className="h-9 w-28" />
      </div>
      <Skeleton className="h-64 w-full" />
    </div>
  );
}
