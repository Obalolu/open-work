"use client";

import { useEffect, useState, useCallback } from "react";
import { motion } from "framer-motion";
import { api } from "@/lib/api";
import type { AppConfig, ProxyPoolStatus } from "@/lib/types";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Skeleton } from "@/components/ui/Skeleton";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/Tabs";
import { Empty } from "@/components/ui/Empty";
import { toast } from "sonner";
import {
  Brain,
  Wifi,
  RefreshCw,
  Check,
  X,
  Shield,
  Info,
} from "lucide-react";

export default function ConfigPage() {
  const [config, setConfig] = useState<AppConfig | null>(null);
  const [proxy, setProxy] = useState<ProxyPoolStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [cfg, prx] = await Promise.all([
        api.config.get(),
        api.proxy.status().catch(() => null),
      ]);
      setConfig(cfg);
      setProxy(prx);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
    setLoading(false);
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const handleRefreshProxy = async () => {
    setRefreshing(true);
    try {
      const result = await api.proxy.refresh();
      if (result.ok) {
        const prx = await api.proxy.status();
        setProxy(prx);
        toast.success("Proxy pool refreshed");
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
        <div className="grid gap-4 lg:grid-cols-2">
          <Skeleton className="h-64" />
          <Skeleton className="h-64" />
        </div>
        <Skeleton className="h-32" />
      </div>
    );
  }

  if (error) {
    return (
      <Empty
        icon={<X className="h-5 w-5" />}
        title="Failed to load settings"
        description={error}
        action={
          <Button onClick={load} variant="outline">
            <RefreshCw />
            Retry
          </Button>
        }
      />
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-semibold tracking-tight text-foreground">
          Settings
        </h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Configure your open-work system
        </p>
      </div>

      <Tabs defaultValue="llm">
        <TabsList>
          <TabsTrigger value="llm">
            <Brain />
            LLM
          </TabsTrigger>
          <TabsTrigger value="research">
            <Wifi />
            Research
          </TabsTrigger>
          <TabsTrigger value="proxy">
            <Shield />
            Proxy
          </TabsTrigger>
          <TabsTrigger value="about">
            <Info />
            About
          </TabsTrigger>
        </TabsList>

        <TabsContent value="llm" className="mt-4">
          <Card>
            <CardHeader>
              <CardTitle>LLM configuration</CardTitle>
              <CardDescription>
                Edit <code className="rounded bg-muted px-1 py-0.5 text-2xs">~/.config/open-work/config.toml</code> to change these values.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-3 pt-0">
              {config?.llm && (
                <>
                  <ConfigRow label="Provider" value={config.llm.provider} />
                  <ConfigRow label="Model" value={config.llm.model} />
                  <ConfigRow
                    label="Temperature"
                    value={String(config.llm.temperature)}
                  />
                  <ConfigRow
                    label="API key"
                    value={config.llm.api_key_set ? "Set" : "Not set"}
                    status={config.llm.api_key_set}
                  />
                  {config.llm.base_url && (
                    <ConfigRow label="Base URL" value={config.llm.base_url} />
                  )}
                </>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="research" className="mt-4">
          <Card>
            <CardHeader>
              <CardTitle>Research APIs</CardTitle>
              <CardDescription>
                External sources for finding papers and citations.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-3 pt-0">
              {config?.research && (
                <>
                  <ConfigRow
                    label="Semantic Scholar"
                    value={
                      config.research.semantic_scholar_api_key_set
                        ? "Configured"
                        : "Not set"
                    }
                    status={config.research.semantic_scholar_api_key_set}
                  />
                  <ConfigRow
                    label="OpenAlex"
                    value={
                      config.research.openalex_api_key_set
                        ? "Configured"
                        : "Not set"
                    }
                    status={config.research.openalex_api_key_set}
                  />
                  <ConfigRow
                    label="Max papers per query"
                    value={String(config.research.max_papers_per_query)}
                  />
                </>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="proxy" className="mt-4">
          <Card>
            <CardHeader className="flex-row items-center justify-between space-y-0">
              <div>
                <CardTitle>Proxy pool</CardTitle>
                <CardDescription>
                  Free proxies used to bypass rate limits on research APIs.
                </CardDescription>
              </div>
              <Button
                variant="outline"
                size="sm"
                onClick={handleRefreshProxy}
                loading={refreshing}
              >
                <RefreshCw />
                Refresh
              </Button>
            </CardHeader>
            <CardContent className="pt-0">
              {proxy ? (
                <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
                  <Stat label="Total" value={proxy.total} />
                  <Stat label="Working" value={proxy.working} tone="success" />
                  <Stat label="Failed" value={proxy.failed} tone="danger" />
                  <Stat
                    label="Last refresh"
                    value={
                      proxy.last_refresh
                        ? new Date(proxy.last_refresh).toLocaleString()
                        : "Never"
                    }
                    valueClassName="text-xs"
                  />
                </div>
              ) : (
                <p className="text-sm text-muted-foreground">
                  No proxy status available.
                </p>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="about" className="mt-4">
          <Card>
            <CardHeader>
              <CardTitle>About open-work</CardTitle>
              <CardDescription>
                Automated chapter-by-chapter research paper writing system.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-2 pt-0 text-sm">
              <ConfigRow label="Version" value="1.0.0" />
              <ConfigRow label="Editor" value="Next.js + TipTap (soon)" />
              <ConfigRow label="Theme" value="Soft slate, system default" />
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}

function ConfigRow({
  label,
  value,
  status,
}: {
  label: string;
  value: string;
  status?: boolean;
}) {
  return (
    <div className="flex items-center justify-between border-b border-border py-2 last:border-0">
      <span className="text-sm text-muted-foreground">{label}</span>
      <span className="inline-flex items-center gap-2 text-sm font-medium text-foreground">
        {status !== undefined &&
          (status ? (
            <Check className="h-4 w-4 text-success" />
          ) : (
            <X className="h-4 w-4 text-muted-foreground/50" />
          ))}
        {value}
      </span>
    </div>
  );
}

function Stat({
  label,
  value,
  tone,
  valueClassName,
}: {
  label: string;
  value: number | string;
  tone?: "success" | "danger";
  valueClassName?: string;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 4 }}
      animate={{ opacity: 1, y: 0 }}
      className="rounded-md bg-muted/50 p-3 text-center"
    >
      <p
        className={
          valueClassName ||
          `text-2xl font-semibold ${
            tone === "success"
              ? "text-success"
              : tone === "danger"
                ? "text-danger"
                : "text-foreground"
          }`
        }
      >
        {value}
      </p>
      <p className="mt-0.5 text-2xs uppercase tracking-wider text-muted-foreground">
        {label}
      </p>
    </motion.div>
  );
}
