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
import { Input } from "@/components/ui/Input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/Select";
import { toast } from "sonner";
import {
  Brain,
  Wifi,
  RefreshCw,
  Check,
  X,
  Shield,
  Info,
  Eye,
  EyeOff,
  KeyRound,
  FlaskConical,
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
          <LlmSettings config={config} />
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
              <ConfigRow label="Editor" value="Next.js + TipTap" />
              <ConfigRow label="Theme" value="Soft slate, system default" />
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}

function LlmSettings({ config }: { config: AppConfig | null }) {
  const [provider, setProvider] = useState(config?.llm.provider ?? "openai");
  const [model, setModel] = useState(config?.llm.model ?? "gpt-4o-mini");
  const [temperature, setTemperature] = useState(
    String(config?.llm.temperature ?? 0.7)
  );
  const [baseUrl, setBaseUrl] = useState(config?.llm.base_url ?? "");
  const [apiKey, setApiKey] = useState("");
  const [showKey, setShowKey] = useState(false);
  const [saving, setSaving] = useState(false);
  const [dirty, setDirty] = useState(false);

  useEffect(() => {
    if (!config) return;
    setProvider(config.llm.provider);
    setModel(config.llm.model);
    setTemperature(String(config.llm.temperature));
    setBaseUrl(config.llm.base_url);
    setApiKey("");
    setDirty(false);
  }, [config]);

  const handleSave = async () => {
    setSaving(true);
    try {
      await api.config.update({
        llm: {
          provider,
          model,
          temperature: parseFloat(temperature) || 0.7,
          base_url: baseUrl,
          api_key: apiKey || undefined,
        },
      });
      toast.success("LLM settings saved", {
        description: "Restart the API to apply changes to running jobs.",
      });
      setApiKey("");
      setDirty(false);
    } catch (e) {
      toast.error("Failed to save", {
        description: e instanceof Error ? e.message : String(e),
      });
    }
    setSaving(false);
  };

  const markDirty = () => setDirty(true);

  return (
    <Card>
      <CardHeader className="flex-row items-center justify-between space-y-0">
        <div>
          <CardTitle>LLM configuration</CardTitle>
          <CardDescription>
            Configure the language model provider and credentials.
          </CardDescription>
        </div>
        {dirty && (
          <span className="rounded-full bg-warning-soft px-2 py-0.5 text-2xs font-medium text-warning">
            Unsaved
          </span>
        )}
      </CardHeader>
      <CardContent className="space-y-4 pt-0">
        <div className="grid gap-4 sm:grid-cols-2">
          <div className="space-y-2">
            <label className="text-sm font-medium">Provider</label>
            <Select
              value={provider}
              onValueChange={(v) => {
                setProvider(v);
                markDirty();
              }}
            >
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="openai">OpenAI</SelectItem>
                <SelectItem value="deepseek">DeepSeek</SelectItem>
                <SelectItem value="ollama">Ollama (local)</SelectItem>
                <SelectItem value="anthropic">Anthropic (via proxy)</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-2">
            <label className="text-sm font-medium">Model</label>
            <Input
              value={model}
              onChange={(e) => {
                setModel(e.target.value);
                markDirty();
              }}
              placeholder="gpt-4o-mini"
            />
          </div>
          <div className="space-y-2">
            <label className="text-sm font-medium">Temperature</label>
            <Input
              type="number"
              step="0.1"
              min="0"
              max="2"
              value={temperature}
              onChange={(e) => {
                setTemperature(e.target.value);
                markDirty();
              }}
            />
          </div>
          <div className="space-y-2">
            <label className="text-sm font-medium">Base URL (optional)</label>
            <Input
              value={baseUrl}
              onChange={(e) => {
                setBaseUrl(e.target.value);
                markDirty();
              }}
              placeholder="https://api.openai.com/v1"
            />
          </div>
          <div className="space-y-2 sm:col-span-2">
            <label className="flex items-center gap-2 text-sm font-medium">
              <KeyRound className="h-3.5 w-3.5" />
              API key
              {config?.llm.api_key_set && (
                <span className="rounded-full bg-success-soft px-1.5 py-0.5 text-2xs font-medium text-success">
                  Set
                </span>
              )}
            </label>
            <div className="flex gap-2">
              <div className="relative flex-1">
                <Input
                  type={showKey ? "text" : "password"}
                  value={apiKey}
                  onChange={(e) => {
                    setApiKey(e.target.value);
                    markDirty();
                  }}
                  placeholder={
                    config?.llm.api_key_set
                      ? "Leave blank to keep current key"
                      : "sk-..."
                  }
                />
              </div>
              <Button
                variant="ghost"
                size="icon"
                onClick={() => setShowKey((v) => !v)}
                aria-label={showKey ? "Hide key" : "Show key"}
              >
                {showKey ? <EyeOff /> : <Eye />}
              </Button>
              <Button
                variant="outline"
                onClick={async () => {
                  try {
                    const h = await api.health.get();
                    toast.success(
                      h.llm_configured
                        ? "API reachable"
                        : "API reachable but no LLM key configured",
                      { description: `DB: ${h.db_ok ? "ok" : "down"}` }
                    );
                  } catch (e) {
                    toast.error("API unreachable", {
                      description:
                        e instanceof Error ? e.message : String(e),
                    });
                  }
                }}
                title="Test API connection"
              >
                <FlaskConical />
                Test
              </Button>
            </div>
          </div>
        </div>
        <div className="flex items-center justify-end gap-2 border-t border-border pt-3">
          <Button onClick={handleSave} loading={saving} disabled={!dirty}>
            Save changes
          </Button>
        </div>
      </CardContent>
    </Card>
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
