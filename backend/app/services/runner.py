import asyncio
import logging
from typing import Any, Callable, Dict, Optional

from src.scraper_facade import Scraper, ScrapeConfig
from app.services.store import Store

logger = logging.getLogger("UltimateScraper.Runner")


class JobRunner:
    """Runs jobs as a bounded pool of in-process asyncio tasks. Each task drives the
    Phase 1 Scraper facade and persists progress/results to the store as it goes."""

    def __init__(self, store: Store, scraper_factory: Optional[Callable[[], Any]] = None,
                 max_concurrent_jobs: int = 3):
        self.store = store
        self.scraper_factory = scraper_factory or (lambda: Scraper())
        self._sem = asyncio.Semaphore(max_concurrent_jobs)
        self._tasks: set = set()

    def submit(self, job_id: str, user_id: str) -> asyncio.Task:
        """Schedule a job and return its Task (awaitable for tests / graceful shutdown)."""
        task = asyncio.create_task(self._run(job_id, user_id))
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)
        return task

    async def _run(self, job_id: str, user_id: str) -> None:
        async with self._sem:
            if hasattr(self.store, "claim_job"):
                claimed = await self.store.claim_job(job_id)
                if not claimed:
                    return
            else:
                job = await self.store.get_job(job_id, user_id)
                if not job or job["status"] == "canceled":
                    return
                await self.store.set_job_status(job_id, "running", started=True)

            job = await self.store.get_job(job_id, user_id)

            cfg = job["config"]
            scraper = self.scraper_factory()
            processed = 0
            try:
                scrape_cfg = ScrapeConfig(
                    urls=list(cfg.get("urls", [])),
                    mode=cfg.get("mode", "auto"),
                    fields=cfg.get("fields") or {},
                    concurrency=int(cfg.get("concurrency", 5)),
                    rate_per_minute=float(cfg.get("rate_per_minute", 60)),
                    use_browser_fallback=bool(cfg.get("use_browser_fallback", True)),
                )

                async def on_result(r: Dict[str, Any]) -> None:
                    nonlocal processed
                    processed += 1
                    await self.store.add_result(
                        job_id, user_id, r.get("url"), r.get("data"),
                        r.get("status", "failed"), r.get("error"),
                    )
                    await self.store.bump_job_progress(job_id, ok=(r.get("status") == "ok"))

                await scraper.run(scrape_cfg, result_cb=on_result)
                await self.store.set_job_status(job_id, "completed", finished=True)
                await self.store.increment_usage(user_id, processed)
            except Exception as e:  # noqa: BLE001 — record any failure on the job row
                logger.exception("Job %s failed", job_id)
                await self.store.set_job_status(job_id, "failed", error=str(e), finished=True)
            finally:
                close = getattr(scraper, "aclose", None)
                if close is not None:
                    try:
                        await close()
                    except Exception:
                        pass

    async def wait_all(self) -> None:
        if self._tasks:
            await asyncio.gather(*list(self._tasks), return_exceptions=True)
