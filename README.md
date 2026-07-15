# Ultimate Scraper

A small self-hostable SaaS around a hardened Python web scraper: sign in, run scraping
jobs from a browser, watch them progress live, browse/export results, and call the
scraper programmatically with an API key.

## Architecture

Three parts:

- **`src/`** — the hardened scraper (patchright stealth, curl_cffi fast path, proxy/UA
  rotation, precise anti-bot detection, generalized parser, concurrency-bounded
  `Scraper` facade). Pure Python, unit-tested.
- **`backend/`** — FastAPI app + in-process `JobRunner` that drives the scraper and
  persists jobs/results to Supabase Postgres. Exposes the dashboard actions + a
  developer API (API-key auth).
- **`frontend/`** — Next.js (App Router) + Tailwind dashboard. Reads jobs/results
  directly from Supabase (RLS + Realtime for the live progress bar); calls the backend
  for actions (create/cancel/export/rotate key).

```
Next.js ──create/cancel/export/rotate──▶ FastAPI ──runs──▶ src/ scraper
   │                                         │ writes
   └──reads + realtime──▶ Supabase Postgres ◀┘
```

## Setup

### 1. Supabase
Follow [docs/SUPABASE_SETUP.md](docs/SUPABASE_SETUP.md): create a project, run
[supabase/migrations/0001_init.sql](supabase/migrations/0001_init.sql), enable email
auth, and collect the URL + anon key + service_role key + JWT secret.

### 2. Backend
```bash
cd backend
python -m pip install -r requirements.txt          # (or use the repo venv)
cp .env.example .env                                # fill in Supabase keys
python -m uvicorn "app.main:create_production_app" --factory --reload --port 8000
```
API docs at http://localhost:8000/docs.

### 3. Frontend
```bash
cd frontend
npm install
cp .env.local.example .env.local                    # Supabase URL + anon key + API URL
npm run dev
```
Dashboard at http://localhost:3000.

## Tests

```bash
# Scraper (from repo root)
python -m pytest

# Backend
cd backend && python -m pytest

# Frontend build/typecheck
cd frontend && npm run build
```

## Notes

- Scrape responsibly: respect target sites' terms and rate limits. CAPTCHA solving is
  intentionally out of scope (opt-in solver hooks only).
- Design + implementation plans live in [docs/superpowers/](docs/superpowers/).
