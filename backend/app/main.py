from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import jobs


def create_app(store, runner, settings) -> FastAPI:
    """Build the FastAPI app around injected dependencies. Tests pass a FakeStore +
    fake runner + lightweight settings; production wiring lives in
    create_production_app()."""

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        # Reconcile any jobs left 'running' from a previous process back to 'queued'.
        await store.reset_running_jobs()
        yield

    app = FastAPI(title="Ultimate Scraper API", version="1.0.0", lifespan=lifespan)
    app.state.store = store
    app.state.runner = runner
    app.state.settings = settings

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(jobs.router)

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    return app
