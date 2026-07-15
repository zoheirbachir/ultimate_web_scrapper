# Supabase setup (Phase 2 backend)

You only need to do this once. It gives the backend a database, auth, and realtime.

## 1. Create the project
1. Go to https://supabase.com, sign in, and click **New project**.
2. Pick a name (e.g. `ultimate-scraper`), a strong database password, and a region
   close to you. Wait ~2 minutes for it to provision.

## 2. Run the schema migration
1. In the project, open **SQL Editor → New query**.
2. Paste the entire contents of [`supabase/migrations/0001_init.sql`](../supabase/migrations/0001_init.sql).
3. Click **Run**. You should see "Success. No rows returned."
   This creates the `profiles`, `jobs`, `results` tables, RLS policies, the
   new-user trigger, and enables realtime.

## 3. Enable email auth
1. **Authentication → Providers → Email**: make sure **Email** is enabled.
2. For local development you can turn **Confirm email** off (Authentication →
   Providers → Email → "Confirm email") so sign-ups work without an inbox round-trip.

## 4. Collect the keys the backend needs
Open **Project Settings → API** and copy:
- **Project URL** (e.g. `https://abcd1234.supabase.co`)
- **anon public** key (safe for the browser / frontend)
- **service_role** key (SECRET — backend only, never in the frontend or git)
- **JWT secret** (Project Settings → API → **JWT Settings → JWT Secret**) — the backend
  uses this to verify user tokens.

## 5. Put them in the backend env file
Copy `backend/.env.example` to `backend/.env` and fill in:

```
SUPABASE_URL=https://YOUR-PROJECT.supabase.co
SUPABASE_ANON_KEY=your-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key
SUPABASE_JWT_SECRET=your-jwt-secret
```

`backend/.env` is git-ignored. Keep the service_role key and JWT secret out of the
frontend and out of version control — treat them like passwords.

## 6. Run the backend
```
cd backend
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload --port 8000
```
Then open http://localhost:8000/docs for the interactive API.
