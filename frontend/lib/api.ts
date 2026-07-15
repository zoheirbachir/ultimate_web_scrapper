import { createClient } from "@/lib/supabase/client";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface FieldSpec {
  selector: string;
  attr?: string;
}

export interface CreateJobPayload {
  urls: string[];
  mode: "auto" | "custom";
  fields?: Record<string, FieldSpec>;
  concurrency?: number;
  rate_per_minute?: number;
  use_browser_fallback?: boolean;
}

async function authHeader(): Promise<Record<string, string>> {
  const supabase = createClient();
  const {
    data: { session },
  } = await supabase.auth.getSession();
  return session?.access_token ? { Authorization: `Bearer ${session.access_token}` } : {};
}

async function detail(res: Response): Promise<string> {
  try {
    const body = await res.json();
    return body.detail || `Request failed (${res.status})`;
  } catch {
    return `Request failed (${res.status})`;
  }
}

export async function createJob(payload: CreateJobPayload) {
  const res = await fetch(`${API_URL}/v1/jobs`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...(await authHeader()) },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error(await detail(res));
  return res.json();
}

export async function cancelJob(jobId: string) {
  const res = await fetch(`${API_URL}/v1/jobs/${jobId}/cancel`, {
    method: "POST",
    headers: { ...(await authHeader()) },
  });
  if (!res.ok) throw new Error(await detail(res));
  return res.json();
}

export async function downloadExport(jobId: string, format: "csv" | "json" | "xlsx") {
  const res = await fetch(`${API_URL}/v1/jobs/${jobId}/export?format=${format}`, {
    headers: { ...(await authHeader()) },
  });
  if (!res.ok) throw new Error(await detail(res));
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `job_${jobId}.${format}`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

export async function rotateApiKey(): Promise<{ api_key: string; prefix: string }> {
  const res = await fetch(`${API_URL}/v1/keys/rotate`, {
    method: "POST",
    headers: { ...(await authHeader()) },
  });
  if (!res.ok) throw new Error(await detail(res));
  return res.json();
}

export async function getUsage(): Promise<{ usage_count: number }> {
  const res = await fetch(`${API_URL}/v1/usage`, { headers: { ...(await authHeader()) } });
  if (!res.ok) throw new Error(await detail(res));
  return res.json();
}
