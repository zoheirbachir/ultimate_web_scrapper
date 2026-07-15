"use client";

import { useEffect, useState } from "react";
import { createClient } from "@/lib/supabase/client";
import { rotateApiKey } from "@/lib/api";
import { Button, Card, Spinner } from "@/components/ui";

export default function SettingsPage() {
  const [prefix, setPrefix] = useState<string | null>(null);
  const [usage, setUsage] = useState<number>(0);
  const [rawKey, setRawKey] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [rotating, setRotating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const supabase = createClient();
    let mounted = true;

    async function load() {
      const {
        data: { user },
      } = await supabase.auth.getUser();
      if (!user) return;
      const { data } = await supabase
        .from("profiles")
        .select("api_key_prefix, usage_count")
        .eq("id", user.id)
        .maybeSingle();
      if (mounted && data) {
        setPrefix(data.api_key_prefix);
        setUsage(data.usage_count ?? 0);
      }
      if (mounted) setLoading(false);
    }

    load();
    const channel = supabase
      .channel("profile-changes")
      .on("postgres_changes", { event: "*", schema: "public", table: "profiles" }, () => load())
      .subscribe();

    return () => {
      mounted = false;
      supabase.removeChannel(channel);
    };
  }, []);

  async function onRotate() {
    setRotating(true);
    setError(null);
    try {
      const { api_key, prefix } = await rotateApiKey();
      setRawKey(api_key);
      setPrefix(prefix);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to rotate key");
    } finally {
      setRotating(false);
    }
  }

  if (loading) {
    return (
      <div className="flex items-center gap-2 text-slate-500">
        <Spinner /> Loading…
      </div>
    );
  }

  return (
    <div className="max-w-2xl space-y-8">
      <div>
        <h2 className="mb-4 text-xl font-semibold text-slate-900">API key</h2>
        <Card className="space-y-4">
          <p className="text-sm text-slate-500">
            Use this key to call the scraper programmatically:{" "}
            <code className="rounded bg-slate-100 px-1 py-0.5 text-xs">
              Authorization: Bearer sk_…
            </code>
          </p>

          {rawKey ? (
            <div className="rounded-lg border border-amber-200 bg-amber-50 p-3">
              <p className="mb-1 text-xs font-medium text-amber-700">
                Copy this now — it won&apos;t be shown again:
              </p>
              <code className="break-all text-sm text-slate-900">{rawKey}</code>
            </div>
          ) : (
            <p className="text-sm text-slate-600">
              Current key:{" "}
              {prefix ? (
                <code className="rounded bg-slate-100 px-1 py-0.5 text-xs">{prefix}…</code>
              ) : (
                <span className="text-slate-400">none yet</span>
              )}
            </p>
          )}

          <Button onClick={onRotate} disabled={rotating}>
            {rotating ? "Generating…" : prefix ? "Regenerate key" : "Generate key"}
          </Button>
          {error && <p className="text-sm text-red-600">{error}</p>}
        </Card>
      </div>

      <div>
        <h2 className="mb-4 text-xl font-semibold text-slate-900">Usage</h2>
        <Card>
          <div className="flex items-baseline gap-2">
            <span className="text-3xl font-bold text-slate-900">{usage.toLocaleString()}</span>
            <span className="text-sm text-slate-500">URLs scraped (all time)</span>
          </div>
        </Card>
      </div>
    </div>
  );
}
