"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { AppConfig, ProxyPoolStatus } from "@/lib/types";
import { Settings, Wifi, RefreshCw, Check, X, Loader2 } from "lucide-react";

export default function ConfigPage() {
  const [config, setConfig] = useState<AppConfig | null>(null);
  const [proxy, setProxy] = useState<ProxyPoolStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  useEffect(() => {
    const load = async () => {
      setLoading(true);
      try {
        const [cfg, prx] = await Promise.all([
          api.config.get(),
          api.proxy.status().catch(() => null),
        ]);
        setConfig(cfg);
        setProxy(prx);
      } catch (e) {
        console.error(e);
      }
      setLoading(false);
    };
    load();
  }, []);

  const handleRefreshProxy = async () => {
    setRefreshing(true);
    try {
      const result = await api.proxy.refresh();
      if (result.ok) {
        const prx = await api.proxy.status();
        setProxy(prx);
      }
    } catch (e) {
      console.error(e);
    }
    setRefreshing(false);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-8 h-8 text-blue-500 animate-spin" />
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-slate-900">Settings</h1>
        <p className="text-slate-500 mt-1">
          Configure your open-work system
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white rounded-xl border border-slate-200 p-6">
          <div className="flex items-center gap-3 mb-6">
            <Settings className="w-5 h-5 text-slate-500" />
            <h3 className="font-semibold text-slate-800">LLM Configuration</h3>
          </div>
          {config?.llm && (
            <div className="space-y-4">
              <ConfigRow label="Provider" value={config.llm.provider} />
              <ConfigRow label="Model" value={config.llm.model} />
              <ConfigRow
                label="Temperature"
                value={String(config.llm.temperature)}
              />
              <ConfigRow
                label="API Key"
                value={config.llm.api_key_set ? "Set" : "Not set"}
                status={config.llm.api_key_set}
              />
              {config.llm.base_url && (
                <ConfigRow label="Base URL" value={config.llm.base_url} />
              )}
            </div>
          )}
        </div>

        <div className="bg-white rounded-xl border border-slate-200 p-6">
          <div className="flex items-center gap-3 mb-6">
            <Wifi className="w-5 h-5 text-slate-500" />
            <h3 className="font-semibold text-slate-800">Research APIs</h3>
          </div>
          {config?.research && (
            <div className="space-y-4">
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
                label="Max papers/query"
                value={String(config.research.max_papers_per_query)}
              />
            </div>
          )}
        </div>

        <div className="bg-white rounded-xl border border-slate-200 p-6 lg:col-span-2">
          <div className="flex items-center justify-between mb-6">
            <div className="flex items-center gap-3">
              <Wifi className="w-5 h-5 text-slate-500" />
              <h3 className="font-semibold text-slate-800">Proxy Pool</h3>
            </div>
            <button
              onClick={handleRefreshProxy}
              disabled={refreshing}
              className="flex items-center gap-2 px-3 py-1.5 border border-slate-300 rounded-lg text-sm text-slate-600 hover:bg-slate-50 disabled:opacity-50"
            >
              <RefreshCw
                className={`w-4 h-4 ${refreshing ? "animate-spin" : ""}`}
              />
              Refresh
            </button>
          </div>
          {proxy && (
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="text-center p-4 bg-slate-50 rounded-lg">
                <p className="text-2xl font-bold text-slate-800">
                  {proxy.total}
                </p>
                <p className="text-sm text-slate-500">Total</p>
              </div>
              <div className="text-center p-4 bg-green-50 rounded-lg">
                <p className="text-2xl font-bold text-green-600">
                  {proxy.working}
                </p>
                <p className="text-sm text-slate-500">Working</p>
              </div>
              <div className="text-center p-4 bg-red-50 rounded-lg">
                <p className="text-2xl font-bold text-red-600">
                  {proxy.failed}
                </p>
                <p className="text-sm text-slate-500">Failed</p>
              </div>
              <div className="text-center p-4 bg-slate-50 rounded-lg">
                <p className="text-sm font-medium text-slate-600">
                  {proxy.last_refresh
                    ? new Date(proxy.last_refresh).toLocaleString()
                    : "Never"}
                </p>
                <p className="text-sm text-slate-500">Last refresh</p>
              </div>
            </div>
          )}
        </div>
      </div>
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
    <div className="flex items-center justify-between py-2 border-b border-slate-100 last:border-0">
      <span className="text-sm text-slate-500">{label}</span>
      <span className="text-sm font-medium text-slate-800 flex items-center gap-2">
        {status !== undefined &&
          (status ? (
            <Check className="w-4 h-4 text-green-500" />
          ) : (
            <X className="w-4 h-4 text-slate-300" />
          ))}
        {value}
      </span>
    </div>
  );
}
