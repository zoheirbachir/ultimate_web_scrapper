-- Ultimate Scraper — initial schema, RLS, profile trigger, and realtime.
-- Run this in the Supabase SQL editor (or via `supabase db push`) once the project exists.

-- ─────────────────────────────────────────────────────────────────────────────
-- Tables
-- ─────────────────────────────────────────────────────────────────────────────

create table if not exists public.profiles (
    id             uuid primary key references auth.users(id) on delete cascade,
    api_key_hash   text,
    api_key_prefix text,
    usage_count    integer not null default 0,
    created_at     timestamptz not null default now()
);

create table if not exists public.jobs (
    id          uuid primary key default gen_random_uuid(),
    user_id     uuid not null references auth.users(id) on delete cascade,
    status      text not null default 'queued'
                check (status in ('queued','running','completed','failed','canceled')),
    config      jsonb not null,
    total       integer not null default 0,
    completed   integer not null default 0,
    failed      integer not null default 0,
    error       text,
    created_at  timestamptz not null default now(),
    started_at  timestamptz,
    finished_at timestamptz
);

create table if not exists public.results (
    id         uuid primary key default gen_random_uuid(),
    job_id     uuid not null references public.jobs(id) on delete cascade,
    user_id    uuid not null references auth.users(id) on delete cascade,
    url        text not null,
    data       jsonb,
    status     text not null default 'ok' check (status in ('ok','failed')),
    error      text,
    scraped_at timestamptz not null default now()
);

create index if not exists jobs_user_created_idx on public.jobs (user_id, created_at desc);
create index if not exists results_job_idx on public.results (job_id);

-- Realtime needs full row images on update to deliver progress changes.
alter table public.jobs replica identity full;
alter table public.results replica identity full;

-- ─────────────────────────────────────────────────────────────────────────────
-- Row-Level Security — users may READ only their own rows. All writes go through
-- the backend using the service_role key, which bypasses RLS with explicit
-- user_id scoping in application code.
-- ─────────────────────────────────────────────────────────────────────────────

alter table public.profiles enable row level security;
alter table public.jobs     enable row level security;
alter table public.results  enable row level security;

drop policy if exists "profiles read own" on public.profiles;
create policy "profiles read own" on public.profiles
    for select using (id = auth.uid());

drop policy if exists "jobs read own" on public.jobs;
create policy "jobs read own" on public.jobs
    for select using (user_id = auth.uid());

drop policy if exists "results read own" on public.results;
create policy "results read own" on public.results
    for select using (user_id = auth.uid());

-- ─────────────────────────────────────────────────────────────────────────────
-- Auto-create a profile row when a new auth user signs up.
-- ─────────────────────────────────────────────────────────────────────────────

create or replace function public.handle_new_user()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
begin
    insert into public.profiles (id) values (new.id)
    on conflict (id) do nothing;
    return new;
end;
$$;

drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created
    after insert on auth.users
    for each row execute function public.handle_new_user();

-- ─────────────────────────────────────────────────────────────────────────────
-- Realtime publication — let the dashboard subscribe to job/result changes.
-- ─────────────────────────────────────────────────────────────────────────────

do $$
begin
    if not exists (
        select 1 from pg_publication_tables
        where pubname = 'supabase_realtime' and schemaname = 'public' and tablename = 'jobs'
    ) then
        alter publication supabase_realtime add table public.jobs;
    end if;
    if not exists (
        select 1 from pg_publication_tables
        where pubname = 'supabase_realtime' and schemaname = 'public' and tablename = 'results'
    ) then
        alter publication supabase_realtime add table public.results;
    end if;
    if not exists (
        select 1 from pg_publication_tables
        where pubname = 'supabase_realtime' and schemaname = 'public' and tablename = 'profiles'
    ) then
        alter publication supabase_realtime add table public.profiles;
    end if;
end$$;

-- ─────────────────────────────────────────────────────────────────────────────
-- Atomic counters — called by the backend so concurrent result writes within one
-- job never lose an increment (avoids read-modify-write races).
-- ─────────────────────────────────────────────────────────────────────────────

create or replace function public.bump_job_progress(p_job_id uuid, p_ok boolean)
returns void language sql as $$
    update public.jobs
       set completed = completed + (case when p_ok then 1 else 0 end),
           failed    = failed    + (case when p_ok then 0 else 1 end)
     where id = p_job_id;
$$;

create or replace function public.increment_usage(p_user_id uuid, p_n integer)
returns void language sql as $$
    update public.profiles set usage_count = usage_count + p_n where id = p_user_id;
$$;
