import inspect
import pytest
from app.services.store import FakeStore
from app.services.runner import JobRunner


class FakeScraper:
    def __init__(self, results):
        self._results = results
        self.closed = False

    async def run(self, cfg, progress_cb=None, result_cb=None):
        out = []
        for r in self._results:
            out.append(r)
            if result_cb is not None:
                maybe = result_cb(r)
                if inspect.isawaitable(maybe):
                    await maybe
        return out

    async def aclose(self):
        self.closed = True


@pytest.mark.asyncio
async def test_runner_persists_results_and_completes():
    store = FakeStore()
    uid = "u"
    job = await store.create_job(uid, {"urls": ["http://a", "http://b"], "mode": "auto"}, total=2)
    fake_results = [
        {"url": "http://a", "status": "ok", "data": {"x": 1}, "error": None},
        {"url": "http://b", "status": "failed", "data": None, "error": "boom"},
    ]
    scraper = FakeScraper(fake_results)
    runner = JobRunner(store, scraper_factory=lambda: scraper)

    await runner.submit(job["id"], uid)  # awaiting the task runs it to completion

    j = await store.get_job(job["id"], uid)
    assert j["status"] == "completed"
    assert j["completed"] == 1 and j["failed"] == 1
    results = await store.list_results(job["id"], uid)
    assert len(results) == 2
    assert (await store.get_profile(uid))["usage_count"] == 2
    assert scraper.closed is True


@pytest.mark.asyncio
async def test_runner_marks_failed_on_exception():
    store = FakeStore()
    uid = "u"
    job = await store.create_job(uid, {"urls": ["http://a"], "mode": "auto"}, total=1)

    class BoomScraper:
        async def run(self, cfg, progress_cb=None, result_cb=None):
            raise RuntimeError("scraper exploded")

        async def aclose(self):
            pass

    runner = JobRunner(store, scraper_factory=lambda: BoomScraper())
    await runner.submit(job["id"], uid)

    j = await store.get_job(job["id"], uid)
    assert j["status"] == "failed"
    assert "exploded" in (j["error"] or "")
