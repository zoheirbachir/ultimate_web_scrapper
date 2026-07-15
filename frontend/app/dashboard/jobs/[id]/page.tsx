"use client";

import { useEffect, useMemo, useState } from "react";
import { useParams } from "next/navigation";
import { createClient } from "@/lib/supabase/client";
import { cancelJob, downloadExport } from "@/lib/api";
import type { Job, ScrapeResult } from "@/lib/types";
import { Button, Card, Spinner, StatusBadge } from "@/components/ui";

function cellValue(v: unknown): string {
  if (v === null || v === undefined) return "";
  if (typeof v === "object") return JSON.stringify(v);
  return String(v);
}

export default function JobDetailPage() {
  const params = useParams();
  const jobId = params.id as string;
  const [job, setJob] = useState<Job | null>(null);
  const [results, setResults] = useState<ScrapeResult[]>([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    const supabase = createClient();
    let mounted = true;

    async function loadJob() {
      const { data } = await supabase.from("jobs").select("*").eq("id", jobId).maybeSingle();
      if (mounted && data) setJob(data as Job);
    }
    async function loadResults() {
      const { data } = await supabase
        .from("results")
        .select("*")
        .eq("job_id", jobId)
        .order("scraped_at", { ascending: true });
      if (mounted && data) setResults(data as ScrapeResult[]);
    }

    Promise.all([loadJob(), loadResults()]).then(() => {
      if (mounted) setLoading(false);
    });

    const channel = supabase
      .channel(`job-${jobId}`)
      .on(
        "postgres_changes",
        { event: "*", schema: "public", table: "jobs", filter: `id=eq.${jobId}` },
        () => loadJob(),
      )
      .on(
        "postgres_changes",
        { event: "*", schema: "public", table: "results", filter: `job_id=eq.${jobId}` },
        () => loadResults(),
      )
      .subscribe();

    return () => {
      mounted = false;
      supabase.removeChannel(channel);
    };
  }, [jobId]);

  const columns = useMemo(() => {
    const set = new Set<string>();
    for (const r of results) {
      if (r.data) Object.keys(r.data).forEach((k) => set.add(k));
    }
    return Array.from(set);
  }, [results]);

  if (loading) {
    return (
      <div className="flex items-center gap-2 text-slate-500">
        <Spinner /> Loading job…
      </div>
    );
  }
  if (!job) return <p className="text-slate-500">Job not found.</p>;

  const done = job.completed + job.failed;
  const pct = job.total > 0 ? Math.round((done / job.total) * 100) : 0;
  const active = job.status === "queued" || job.status === "running";

  async function onCancel() {
    setBusy(true);
    try {
      await cancelJob(jobId);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <h2 className="text-xl font-semibold text-slate-900">Job {job.id.slice(0, 8)}</h2>
          <StatusBadge status={job.status} />
        </div>
        {active && (
          <Button variant="danger" onClick={onCancel} disabled={busy}>
            {busy ? "Cancelling…" : "Cancel job"}
          </Button>
        )}
      </div>

      <Card>
        <div className="mb-2 flex justify-between text-sm text-slate-600">
          <span>
            {done} / {job.total} processed
            {job.failed > 0 && <span className="ml-1 text-red-500">· {job.failed} failed</span>}
          </span>
          <span>{pct}%</span>
        </div>
        <div className="h-3 w-full overflow-hidden rounded-full bg-slate-100">
          <div
            className={`h-full rounded-full transition-all ${
              job.status === "failed" ? "bg-red-500" : "bg-brand-600"
            }`}
            style={{ width: `${pct}%` }}
          />
        </div>
        {job.error && <p className="mt-3 text-sm text-red-600">Error: {job.error}</p>}
      </Card>

      <div className="flex items-center gap-2">
        <span className="text-sm font-medium text-slate-600">Export:</span>
        {(["csv", "json", "xlsx"] as const).map((fmt) => (
          <Button
            key={fmt}
            variant="secondary"
            disabled={results.length === 0}
            onClick={() => downloadExport(jobId, fmt)}
          >
            {fmt.toUpperCase()}
          </Button>
        ))}
      </div>

      <div>
        <h3 className="mb-3 text-lg font-semibold text-slate-900">
          Results <span className="text-sm font-normal text-slate-500">({results.length})</span>
        </h3>
        {results.length === 0 ? (
          <Card>
            <p className="text-sm text-slate-500">
              {active ? "Waiting for results to come in…" : "No results."}
            </p>
          </Card>
        ) : (
          <Card className="overflow-x-auto p-0">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-200 text-left text-slate-500">
                  <th className="px-4 py-3 font-medium">URL</th>
                  <th className="px-4 py-3 font-medium">Status</th>
                  {columns.map((c) => (
                    <th key={c} className="px-4 py-3 font-medium">
                      {c}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {results.map((r) => (
                  <tr key={r.id} className="border-b border-slate-100 last:border-0">
                    <td className="max-w-xs truncate px-4 py-3 text-slate-600" title={r.url}>
                      {r.url}
                    </td>
                    <td className="px-4 py-3">
                      <StatusBadge status={r.status} />
                    </td>
                    {columns.map((c) => (
                      <td key={c} className="max-w-xs truncate px-4 py-3 text-slate-700">
                        {cellValue(r.data?.[c])}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </Card>
        )}
      </div>
    </div>
  );
}
