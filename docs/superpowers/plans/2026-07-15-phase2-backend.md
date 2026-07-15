# Phase 2 — Backend Implementation Plan

> **For agentic workers:** Steps use checkbox (`- [ ]`) syntax for tracking. TDD where the unit is pure/mockable; live Supabase integration is verified manually against a real project.

**Goal:** A FastAPI backend that authenticates users (Supabase JWT or API key), creates and runs scraping jobs via an in-process `JobRunner` on top of the Phase 1 `Scraper` facade, persists jobs/results to Supabase Postgres, and serves history, results, exports, API-key rotation, and a usage meter.

**Architecture:** Reads for the dashboard go straight from the browser to Supabase (RLS + Realtime, built in Phase 3). The backend owns **actions**: create/cancel job, export, key rotation, usage, and the programmatic developer API. Jobs run as a semaphore-bounded pool of `asyncio` tasks inside the FastAPI process; each writes progress/results to Postgres, which Realtime pushes to the browser. A `Store` interface abstracts persistence so the whole backend is unit-testable against an in-memory `FakeStore`, with `SupabaseStore` as the production implementation.

**Tech Stack:** Python 3.13, FastAPI, uvicorn, supabase-py, pydantic v2, pandas + openpyxl (exports), PyJWT (verify Supabase JWT), httpx (TestClient), pytest.

**Repo layout decision:** The scraper stays at `src/` (importable by both the existing runners and the backend) rather than moving to `packages/scraper` — this avoids breaking the passing Phase 1 suite and the user's `run_*.py` scripts. The backend lives in `backend/`.

```
backend/
  app/
    main.py              # FastAPI app factory + startup reconciliation
    config.py            # env-driven settings (pydantic-settings)
    deps.py              # auth dependency: JWT or API key -> user_id
    core/
      apikeys.py         # generate / hash / verify API keys
      security.py        # Supabase JWT verification
    services/
      store.py           # Store protocol + FakeStore (in-memory)
      supabase_store.py  # SupabaseStore (production)
      runner.py          # in-process JobRunner
    routers/
      jobs.py            # /v1/jobs* + export + cancel
      keys.py            # /v1/keys/rotate
      usage.py           # /v1/usage
    schemas.py           # pydantic request/response models
  tests/
  requirements.txt
supabase/migrations/0001_init.sql
docs/SUPABASE_SETUP.md
```

---

## Task 0: Supabase migration + setup guide + backend deps

**Files:** `supabase/migrations/0001_init.sql`, `docs/SUPABASE_SETUP.md`, `backend/requirements.txt`, `backend/app/__init__.py`, `backend/tests/__init__.py`, `backend/tests/conftest.py`

- [ ] Write the SQL migration: `profiles`, `jobs`, `results`, RLS policies (`user_id = auth.uid()`), a trigger creating a `profiles` row on `auth.users` insert, and add all three tables to the `supabase_realtime` publication.
- [ ] Write `docs/SUPABASE_SETUP.md`: create project → run migration in SQL editor → copy Project URL, anon key, service_role key into `backend/.env` (from `.env.example`) → enable email auth.
- [ ] `backend/requirements.txt`: fastapi, uvicorn[standard], supabase, pydantic, pydantic-settings, pyjwt, pandas, openpyxl, python-multipart, httpx, pytest, pytest-asyncio.
- [ ] `backend/tests/conftest.py` puts repo root + `backend/` on `sys.path`.
- [ ] Install deps, `pytest` on empty backend suite exits 5. Commit.

## Task 1: API key generation / hashing (TDD)

**Files:** `backend/app/core/apikeys.py`, `backend/tests/test_apikeys.py`

- [ ] Test: `generate_api_key()` returns `(raw, prefix, hash)`; `raw` starts with `sk_`; `verify_api_key(raw, hash)` is True, wrong key False; `prefix` is the first 12 chars of `raw`.
- [ ] Implement with `secrets.token_urlsafe` + `hashlib.sha256`. Commit.

## Task 2: Store protocol + FakeStore (TDD)

**Files:** `backend/app/services/store.py`, `backend/tests/test_store.py`

- [ ] Define `Store` Protocol: `create_job`, `get_job`, `list_jobs`, `set_job_status`, `bump_job_progress`, `add_result`, `list_results`, `get_profile`, `get_profile_by_api_key_prefix`, `rotate_api_key`, `increment_usage`, `reset_running_jobs`.
- [ ] Implement `FakeStore` (dict-backed) satisfying it.
- [ ] Test: create job → get job → add results → list results → bump progress → status transitions. Commit.

## Task 3: Pydantic schemas (TDD-lite)

**Files:** `backend/app/schemas.py`, `backend/tests/test_schemas.py`

- [ ] `FieldSpec{selector, attr?}`, `JobCreate{urls[], mode, fields?, concurrency?, rate_per_minute?, use_browser_fallback?}` with validation (1..200 urls; mode in auto|custom; custom requires fields). `JobOut`, `ResultOut`, `UsageOut`, `KeyOut`.
- [ ] Test valid + invalid payloads. Commit.

## Task 4: JobRunner (TDD)

**Files:** `backend/app/services/runner.py`, `backend/tests/test_runner.py`

- [ ] `JobRunner(store, scraper_factory, max_concurrent_jobs)`; `submit(job_id)` schedules an asyncio task that: sets status running → builds `ScrapeConfig` from job.config → runs the scraper with a progress callback that calls `store.bump_job_progress` and `store.add_result` → sets status completed/failed → increments usage.
- [ ] Test with `FakeStore` + a fake scraper that yields deterministic results; assert final status, result rows, progress counts, usage increment. Commit.

## Task 5: Auth dependency (TDD)

**Files:** `backend/app/core/security.py`, `backend/app/deps.py`, `backend/tests/test_auth.py`

- [ ] `verify_supabase_jwt(token, secret)` → user_id (PyJWT, HS256, `aud=authenticated`). `resolve_user(Authorization, store)`: `sk_` → look up by prefix + `verify_api_key`; otherwise treat as JWT. Raise 401 on failure.
- [ ] Test: valid API key resolves; bad key 401; valid JWT resolves; junk 401. Commit.

## Task 6: Job endpoints (TDD with TestClient + FakeStore)

**Files:** `backend/app/routers/jobs.py`, `backend/app/main.py`, `backend/tests/test_jobs_api.py`

- [ ] `create_app(store, runner)` factory; dependency-override auth to a test user.
- [ ] `POST /v1/jobs` (validates, creates job, calls `runner.submit`, returns JobOut), `GET /v1/jobs`, `GET /v1/jobs/{id}` (404 + ownership 404), `GET /v1/jobs/{id}/results`, `POST /v1/jobs/{id}/cancel`.
- [ ] Test the full create→list→get→results flow with a synchronous fake runner. Commit.

## Task 7: Export endpoint (TDD)

**Files:** `backend/app/routers/jobs.py` (add), `backend/tests/test_export.py`

- [ ] `GET /v1/jobs/{id}/export?format=csv|json|xlsx` flattens `results[].data` (pandas) and streams the file with correct content-type/filename. `xlsx` via openpyxl.
- [ ] Test each format returns 200 + expected content-type; CSV body contains a known value. Commit.

## Task 8: Keys + usage endpoints + startup reconciliation

**Files:** `backend/app/routers/keys.py`, `backend/app/routers/usage.py`, `backend/app/main.py`, `backend/tests/test_keys_usage.py`

- [ ] `POST /v1/keys/rotate` → new raw key once + prefix; `GET /v1/usage` → `{usage_count}`.
- [ ] App startup calls `store.reset_running_jobs()` (orphan reconciliation).
- [ ] Test rotate returns `sk_` key and updates prefix; usage returns count. Commit.

## Task 9: SupabaseStore + manual integration

**Files:** `backend/app/services/supabase_store.py`, `backend/app/main.py` (wire real store), `docs/SUPABASE_SETUP.md` (run instructions)

- [ ] Implement `SupabaseStore` against supabase-py mirroring `Store`. Service-role client for writes; explicit `user_id` scoping on every query.
- [ ] Manual: with a real `.env`, `uvicorn`, create a key, `POST /v1/jobs` with a live URL, confirm rows land in Supabase and progress advances. (Not in the automated suite.)

## Self-Review
- Spec coverage: auth (T5), jobs+progress+history (T4/T6), results+export (T6/T7), dev API + keys (T5/T8), usage meter (T8), JobRunner in-process (T4), RLS/schema (T0), SupabaseStore (T9). ✓
- The dashboard read path (Realtime) is Phase 3; backend exposes GET endpoints for the programmatic API only.
