"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { createClient } from "@/lib/supabase/client";
import type { Job } from "@/lib/types";
import { Card, Spinner, StatusBadge } from "@/components/ui";

export function JobsTable() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const supabase = createClient();
    let mounted = true;

    async function load() {
      const { data } = await supabase
        .from("jobs")
        .select("*")
        .order("created_at", { ascending: false });
      if (mounted) {
        if (data) setJobs(data as Job[]);
        setLoading(false);
      }
    }

    load();
    const channel = supabase
      .channel("jobs-list")
      .on("postgres_changes", { event: "*", schema: "public", table: "jobs" }, () => load())
      .subscribe();

    return () => {
      mounted = false;
      supabase.removeChannel(channel);
    };
  }, []);

  if (loading) {
    return (
      <Card>
        <div className="flex items-center gap-2 text-sm text-slate-500">
          <Spinner /> Loading jobs…
        </div>
      </Card>
    );
  }

  if (jobs.length === 0) {
    return (
      <Card>
        <p className="text-sm text-slate-500">No jobs yet. Start one above.</p>
      </Card>
    );
  }

  return (
    <Card className="overflow-x-auto p-0">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-slate-200 text-left text-slate-500">
            <th className="px-4 py-3 font-medium">Job</th>
            <th className="px-4 py-3 font-medium">Status</th>
            <th className="px-4 py-3 font-medium">Progress</th>
            <th className="px-4 py-3 font-medium">Created</th>
          </tr>
        </thead>
        <tbody>
          {jobs.map((job) => (
            <tr key={job.id} className="border-b border-slate-100 last:border-0 hover:bg-slate-50">
              <td className="px-4 py-3">
                <Link href={`/dashboard/jobs/${job.id}`} className="font-medium text-brand-600 hover:underline">
                  {job.id.slice(0, 8)}
                </Link>
              </td>
              <td className="px-4 py-3">
                <StatusBadge status={job.status} />
              </td>
              <td className="px-4 py-3 text-slate-600">
                {job.completed + job.failed} / {job.total}
                {job.failed > 0 && <span className="ml-1 text-red-500">({job.failed} failed)</span>}
              </td>
              <td className="px-4 py-3 text-slate-500">
                {new Date(job.created_at).toLocaleString()}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </Card>
  );
}
