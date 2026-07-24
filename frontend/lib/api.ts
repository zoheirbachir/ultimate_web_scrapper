import { createClient } from "@/lib/supabase/client";

function getApiUrl(): string {
  if (typeof window !== "undefined") {
    // In browser, use local same-origin Next.js proxy (/api) to avoid cross-origin / VPN fetch failures
    return "/api";
  }
  return process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
}

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
  try {
    const supabase = createClient();
    let { data: { session } } = await supabase.auth.getSession();
    
    if (!session?.access_token) {
      await supabase.auth.getUser();
      const res = await supabase.auth.getSession();
      session = res.data.session;
    }

    if (session?.access_token) {
      return { Authorization: `Bearer ${session.access_token}` };
    }
  } catch (err) {
    console.error("Error getting session:", err);
  }
  return {};
}

async function detail(res: Response): Promise<string> {
  try {
    const body = await res.json();
    return body.detail || `Request failed (${res.status})`;
  } catch {
    return `Request failed (${res.status})`;
  }
}

async function safeFetch(path: string, init?: RequestInit): Promise<Response> {
  const url = `${getApiUrl()}${path}`;
  try {
    return await fetch(url, init);
  } catch (err) {
    console.error(`Fetch error for ${url}:`, err);
    throw new Error(
      "Could not connect to backend server. Please make sure START_PLATFORM.bat is running."
    );
  }
}

export async function createJob(payload: CreateJobPayload) {
  const headers = await authHeader();
  const res = await safeFetch("/v1/jobs", {
    method: "POST",
    headers: { "Content-Type": "application/json", ...headers },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error(await detail(res));
  return res.json();
}

export async function cancelJob(jobId: string) {
  const headers = await authHeader();
  const res = await safeFetch(`/v1/jobs/${jobId}/cancel`, {
    method: "POST",
    headers,
  });
  if (!res.ok) throw new Error(await detail(res));
  return res.json();
}

export async function downloadExport(jobId: string, format: "csv" | "json" | "xlsx") {
  const headers = await authHeader();
  const res = await safeFetch(`/v1/jobs/${jobId}/export?format=${format}`, {
    headers,
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
  const headers = await authHeader();
  const res = await safeFetch("/v1/keys/rotate", {
    method: "POST",
    headers,
  });
  if (!res.ok) throw new Error(await detail(res));
  return res.json();
}

export async function getUsage(): Promise<{ usage_count: number }> {
  const headers = await authHeader();
  const res = await safeFetch("/v1/usage", { headers });
  if (!res.ok) throw new Error(await detail(res));
  return res.json();
}
