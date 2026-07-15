export type JobStatus = "queued" | "running" | "completed" | "failed" | "canceled";

export interface Job {
  id: string;
  user_id: string;
  status: JobStatus;
  config: Record<string, unknown>;
  total: number;
  completed: number;
  failed: number;
  error: string | null;
  created_at: string;
  started_at: string | null;
  finished_at: string | null;
}

export interface ScrapeResult {
  id: string;
  job_id: string;
  user_id: string;
  url: string;
  data: Record<string, unknown> | null;
  status: string;
  error: string | null;
  scraped_at: string;
}
