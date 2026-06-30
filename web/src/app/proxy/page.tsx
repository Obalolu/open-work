"use client";

import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { api } from "@/lib/api";
import type { ProxyPoolStatus } from "@/lib/types";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Skeleton } from "@/components/ui/Skeleton";
import { Empty } from "@/components/ui/Empty";
import { toast } from "sonner";
import { Shield, RefreshCw, CheckCircle2, AlertTriangle } from "lucide-react";

export default function ProxyPage() {
  const [status, setStatus] = useState<ProxyPoolStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const load = async () => {
    setLoading(true);
    try {
      const s = await api.proxy.status();
      setStatus(s);
    } catch (e) {
      toast.error("Failed to load proxy status", {
        description: e instanceof Error ? e.message : String(e),
      });
    }
    setLoading(false);
  };

  useEffect(() => {
    load();
  }, []);

  const handleRefresh = async () => {
    setRefreshing(true);
    try {
      const result = await api.proxy.refresh();
      if (result.ok) {
        toast.success("Proxy pool refreshed");
        await load();
      } else {
        toast.error("Refresh failed", { description: result.error });
      }
    } catch (e) {
      toast.error("Refresh failed", {
        description: e instanceof Error ? e.message : String(e),
      });
    }
    setRefreshing(false);
  };

  if (loading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-9 w-40" />
        <Skeleton className="h-64" />
      </div>
    );
  }

  if (!status) {
    return (
      <Empty
        icon={<AlertTriangle className="h-5 w-5" />}
        title="No proxy status"
        description="The proxy manager hasn't reported any data yet."
        action={
          <Button onClick={handleRefresh} variant="outline">
            <RefreshCw />
            Refresh
          </Button>
        }
      />
    );
  }

  const successRate =
    status.total > 0
      ? Math.round((status.working / status.total) * 100)
      : 0;

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="text-3xl font-semibold tracking-tight text-foreground">
            Proxy pool
          </h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Free proxies used to bypass rate limits on research APIs
          </p>
        </div>
        <Button onClick={handleRefresh} loading={refreshing} variant="outline">
          <RefreshCw />
          Refresh
        </Button>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Stat icon={<Shield className="h-4 w-4" />} label="Total" value={status.total} />
        <Stat
          icon={<CheckCircle2 className="h-4 w-4" />}
          label="Working"
          value={status.working}
          tone="success"
        />
        <Stat
          icon={<AlertTriangle className="h-4 w-4" />}
          label="Failed"
          value={status.failed}
          tone="danger"
        />
        <Stat
          icon={<RefreshCw className="h-4 w-4" />}
          label="Success rate"
          value={`${successRate}%`}
          tone={successRate > 50 ? "success" : successRate > 20 ? "warning" : "danger"}
        />
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Pool health</CardTitle>
          <CardDescription>
            Last refreshed{" "}
            {status.last_refresh
              ? new Date(status.last_refresh).toLocaleString()
              : "never"}
          </CardDescription>
        </CardHeader>
        <CardContent className="pt-0">
          <div className="flex h-3 w-full overflow-hidden rounded-full bg-muted">
            <motion.div
              initial={{ width: 0 }}
              animate={{ width: `${(status.working / Math.max(status.total, 1)) * 100}%` }}
              transition={{ type: "spring", stiffness: 200, damping: 24 }}
              className="bg-success"
            />
          </div>
          <div className="mt-2 flex items-center justify-between text-2xs text-muted-foreground">
            <span>
              {status.working} working · {status.failed} failed
            </span>
            <span>{status.total} total</span>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

function Stat({
  icon,
  label,
  value,
  tone,
}: {
  icon: React.ReactNode;
  label: string;
  value: number | string;
  tone?: "success" | "warning" | "danger";
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 4 }}
      animate={{ opacity: 1, y: 0 }}
      className="rounded-lg border border-border bg-surface p-5"
    >
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
            {label}
          </p>
          <p
            className={`mt-2 text-2xl font-semibold tracking-tight ${
              tone === "success"
                ? "text-success"
                : tone === "warning"
                  ? "text-warning"
                  : tone === "danger"
                    ? "text-danger"
                    : "text-foreground"
            }`}
          >
            {value}
          </p>
        </div>
        <div className="rounded-md bg-muted p-2 text-muted-foreground">{icon}</div>
      </div>
    </motion.div>
  );
}
