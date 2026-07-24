from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import jobs, keys, usage


def create_app(store, runner, settings) -> FastAPI:
    """Build the FastAPI app around injected dependencies. Tests pass a FakeStore +
    fake runner + lightweight settings; production wiring lives in
    create_production_app()."""

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        # Reconcile any jobs left 'running' from a previous process back to 'queued'.
        try:
            await store.reset_running_jobs()
        except Exception as e:
            import logging
            logging.getLogger("UltimateScraper").warning("Could not reset running jobs on startup: %s", e)
        yield

    app = FastAPI(title="Ultimate Scraper API", version="1.0.0", lifespan=lifespan)
    app.state.store = store
    app.state.runner = runner
    app.state.settings = settings

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_origin_regex=r"http://(localhost|127\.0\.0\.1)(:\d+)?",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(jobs.router)
    app.include_router(keys.router)
    app.include_router(usage.router)

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    return app


def create_production_app() -> FastAPI:
    """Build the real app from environment settings. Run with:
        uvicorn "app.main:create_production_app" --factory --port 8000
    """
    from supabase import create_client

    from app.config import get_settings
    from app.services.runner import JobRunner
    from app.services.supabase_store import SupabaseStore

    settings = get_settings()
    if not settings.supabase_url or not settings.supabase_service_role_key:
        raise RuntimeError(
            "Supabase not configured. Copy backend/.env.example to backend/.env and fill "
            "in SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY (see docs/SUPABASE_SETUP.md)."
        )
    client = create_client(settings.supabase_url, settings.supabase_service_role_key)
    store = SupabaseStore(client)
    runner = JobRunner(store, max_concurrent_jobs=settings.max_concurrent_jobs)
    return create_app(store=store, runner=runner, settings=settings)
