# Ultimate Scraper — Internal SaaS Tool (Vertical Slice)

**Date:** 2026-07-15
**Status:** Approved design — ready for implementation planning

## 1. Overview

Wrap the existing Python web scraper (`src/`) in a small, modern, self-hostable web
application so a user can run scraping jobs from a browser, watch them progress live,
browse/export the results, and call the scraper programmatically via an API key.

This document specifies the **first vertical slice only** — a thin but complete
end-to-end path that proves the architecture. Later increments (real billing,
distributed queue, CAPTCHA solving, scheduling, teams) build on top of it.

## 2. Scope decisions (from brainstorming)

| Question | Decision |
| --- | --- |
| Goal | **Internal tool** — for the owner/team; minimal auth ceremony; no payments |
| Sequencing | **Vertical slice first**, then layer additional features |
| Stack | **Supabase** (Auth + Postgres + Realtime) + **Next.js** (App Router, Tailwind, shadcn/ui) + **Python worker** (FastAPI) |
| Billing | **None** — usage is tracked and displayed only, never enforced |

## 3. Goals / Non-goals

**Goals**
- Real authentication (sign up, log in, password reset) via Supabase Auth.
- Dashboard: submit a job (URLs + extraction config), live progress, job history.
- Results: sortable table preview with basic per-column summary stats.
- Exports: CSV, JSON, Excel (`.xlsx`).
- Developer API: per-user API key + REST endpoints to run jobs programmatically.
- Usage meter: count of requests/URLs scraped, shown in settings (display only).
- Harden the scraper's load-bearing weaknesses so it runs reliably as a service.

**Non-goals (this slice)**
- Stripe / real billing or credit enforcement.
- Redis / Celery / distributed multi-worker queue.
- CAPTCHA-solver provider integration (leave opt-in hooks only).
- Scheduled / recurring jobs, webhooks.
- Teams / organizations / role management.
- Heavy BI-style charting (a results table + summary stats is the "visualization").

## 4. Architecture

```
Next.js (App Router, Tailwind, shadcn/ui)
  │  create/cancel job, export, dev API   ── Supabase JWT ──▶  FastAPI (Python)
  │                                                              - REST + developer API
  │  reads + realtime (jobs, results)  ◀── Supabase RLS ─────    - in-process async JobRunner
  ▼                                                                    │ runs
Supabase: Postgres + Auth + Realtime  ◀──── progress/results ────── scraper (packages/scraper)
  tables: profiles, jobs, results               writes
  Row-Level Security scoped to auth.uid()
```

**Two load-bearing decisions:**

1. **Job execution = in-process async runner (no Redis).** Jobs run as a
   semaphore-bounded pool of `asyncio` tasks inside the FastAPI process, writing
   progress to Postgres. Hidden behind a `JobRunner` interface so a later swap to
   Arq+Redis is a drop-in. On startup, any job left in `running` is reconciled to
   `queued` (re-run) or `failed`. Trade-off accepted: in-flight jobs are lost on a
   hard process restart — fine for internal use.

2. **Reads go directly Supabase → frontend via RLS + Realtime; only writes go
   through FastAPI.** The worker updates a `jobs` row; Supabase Realtime pushes it to
   the browser and the progress bar advances — no polling, no custom websockets.
   FastAPI owns only actions: create/cancel job, export, and the developer API.

## 5. Data model (Postgres — all tables RLS-protected to `auth.uid()`)

```sql
-- profiles: 1:1 with auth.users, created on sign-up via trigger
profiles (
  id            uuid primary key references auth.users(id) on delete cascade,
  api_key_hash  text,          -- sha256 of the key; raw key shown once at generation
  api_key_prefix text,         -- e.g. "sk_live_ab12" for display
  usage_count   integer not null default 0,
  created_at    timestamptz not null default now()
)

jobs (
  id          uuid primary key default gen_random_uuid(),
  user_id     uuid not null references auth.users(id) on delete cascade,
  status      text not null default 'queued',  -- queued|running|completed|failed|canceled
  config      jsonb not null,   -- { urls: [], mode: 'auto'|'custom', fields: {name: {selector, attr}} }
  total       integer not null default 0,
  completed   integer not null default 0,
  failed      integer not null default 0,
  error       text,
  created_at  timestamptz not null default now(),
  started_at  timestamptz,
  finished_at timestamptz
)

results (
  id         uuid primary key default gen_random_uuid(),
  job_id     uuid not null references jobs(id) on delete cascade,
  user_id    uuid not null references auth.users(id) on delete cascade,
  url        text not null,
  data       jsonb,            -- extracted fields (schema depends on job config)
  status     text not null,    -- ok|failed
  error      text,
  scraped_at timestamptz not null default now()
)
```

Realtime is enabled on `jobs` and `results`. RLS: every policy checks
`user_id = auth.uid()` (and `results` join through `jobs`). The API key path resolves a
user server-side and uses the service role, bypassing RLS with explicit user scoping.

## 6. Job lifecycle

1. User submits the job form (URLs + extraction config) in the dashboard.
2. Frontend calls `POST /v1/jobs` on FastAPI with the Supabase JWT.
3. FastAPI validates input, inserts a `jobs` row (`status=queued`, `total=len(urls)`),
   hands it to the `JobRunner`, returns the job id.
4. Frontend shows the job and subscribes via Supabase Realtime to that `jobs` row and
   to `results` where `job_id = ...`.
5. Runner sets `status=running`, then for each URL (bounded concurrency + rate limit):
   TLS fast path → browser fallback → parse → upsert a `results` row → increment
   `completed`/`failed`. Each write propagates through Realtime; the progress bar and
   results table update live.
6. On finish: `status=completed` (or `failed` on a fatal error). User can export.
   `profiles.usage_count` is incremented by the number of URLs processed.

## 7. Scraper hardening (in this slice)

Fix the findings that block reliable service operation; defer deeper stealth polish.

- **Switch `BrowserClient` to patchright + persistent context**, apply the configured
  timezone/locale, and delete the manual JS `get_evasion_script()` (config already
  describes this target state; `scraper.py` doesn't implement it yet).
- **Reuse the curl_cffi `AsyncSession`** across requests instead of recreating it per
  call (keep-alive + cookie persistence + speed).
- **Rotate proxy/UA on `ScraperBlockError`** between retries rather than repeating the
  same fingerprint.
- **Tighten `check_bot_challenges`** to key on status code + specific markers (headers,
  challenge-page title, known challenge script hosts) to remove body-substring false
  positives.
- **Generalize the parser**: keep `auto` mode (current JSON-LD/meta/selector chain);
  add `custom` mode mapping user field names to CSS selectors (+ optional attribute).
- **Wire `RateLimiter` + a concurrency `Semaphore`** into the runner.
- Move the scraper into `packages/scraper` and keep the existing `test_*.py` suite green.

CAPTCHA solving stays out; leave a clean opt-in hook where a solver provider could plug in.

## 8. API surface (FastAPI)

Auth: dashboard calls use the Supabase JWT (`Authorization: Bearer <jwt>`); developer
calls use the API key (`Authorization: Bearer sk_...`). Both resolve to a user id.

Read endpoints (`GET /v1/jobs*`) exist for the **programmatic developer API**. The
**dashboard reads job/result data directly from Supabase** via RLS + Realtime and does
not call these GETs — it only calls the action endpoints (create, cancel, export, rotate).

- `POST   /v1/jobs`               — create + enqueue a job; body = `{ urls, mode, fields? }`
- `GET    /v1/jobs`               — list caller's jobs (history)
- `GET    /v1/jobs/{id}`          — job status + counts
- `GET    /v1/jobs/{id}/results`  — paginated results
- `POST   /v1/jobs/{id}/cancel`   — request cancellation
- `GET    /v1/jobs/{id}/export?format=csv|json|xlsx` — streamed download (pandas/openpyxl)
- `POST   /v1/keys/rotate`        — regenerate the API key (returns raw key once)
- `GET    /v1/usage`              — usage counter for display

## 9. Frontend surface (Next.js)

- **Auth pages** — sign up, log in, password reset (`@supabase/ssr`); middleware
  guards dashboard routes.
- **Dashboard / new job** — textarea or list of URLs; mode selector (auto / custom);
  custom-field builder (field name → selector → attribute); submit.
- **Active job view** — live progress bar (Realtime), running counts, results streaming
  into the table, cancel button.
- **History table** — past jobs with status, counts, timestamps; row → job detail.
- **Results table** — sortable columns, basic per-column summary stats, export buttons.
- **Settings** — API key (prefix shown, rotate reveals raw key once) + usage meter.

## 10. Error handling

- **Per-URL isolation** — one URL's failure is recorded on its `results` row and never
  aborts the job; the job completes with `completed`/`failed` counts.
- **Job-level** — a fatal runner error sets `status=failed` with `error` populated.
- **API** — structured error responses with correct status codes.
- **Startup reconciliation** — orphaned `running` jobs are re-queued or failed.
- **Frontend** — loading skeletons, empty states, error toasts.

## 11. Testing

- **Python** — pytest for the hardening changes (build on existing `test_*.py`),
  FastAPI endpoint tests, parser `custom` mode tests, `JobRunner` state-transition
  tests. Network mocked.
- **Frontend** — light for an internal tool: a smoke test of the auth guard and the
  job-create flow.

## 12. Repo structure (monorepo)

```
apps/web            # Next.js frontend
apps/api            # FastAPI app + JobRunner (imports the scraper)
packages/scraper    # hardened former src/
supabase/           # SQL migrations + RLS policies
docker-compose.yml  # runs apps/api; Supabase = cloud free tier; web via `npm run dev`
```

## 13. Deployment (internal)

Local-first: Supabase cloud free tier for Auth/DB/Realtime; `docker-compose up` for the
FastAPI service; `npm run dev` (or Vercel) for the frontend. No Redis in this slice.

## 14. Risks / notes

- **Legal/ToS** — the tool scrapes robustly and respectfully (rate limiting, stealth to
  reduce false blocks). Defeating live CAPTCHAs or ignoring site terms is out of scope
  and the operator's responsibility.
- **Playwright in-process** — patchright/Playwright runs on the FastAPI asyncio loop;
  concurrency is semaphore-bounded to protect memory/CPU on a single box.
- **In-process runner durability** — accepted limitation; mitigated by startup
  reconciliation and a clean path to Arq+Redis later.
