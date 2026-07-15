import pytest
from src.scraper_facade import Scraper, ScrapeConfig
from src.scraper import ScraperResponse


class FakeTLS:
    def __init__(self):
        self.calls = 0

    async def fetch(self, url, **kwargs):
        self.calls += 1
        # first URL "fails" on the TLS path to exercise the browser fallback
        if url.endswith("/fail"):
            return ScraperResponse(0, "", url, {}, {}, success=False, error_message="boom")
        html = "<html><body><h1 class='t'>OK</h1></body></html>"
        return ScraperResponse(200, html, url, {}, {}, success=True)

    async def aclose(self):
        pass


class FakeBrowser:
    def __init__(self):
        self.started = False

    async def start(self):
        self.started = True

    async def fetch(self, url, **kwargs):
        html = "<html><body><h1 class='t'>FROM_BROWSER</h1></body></html>"
        return ScraperResponse(200, html, url, {}, {}, success=True)

    async def stop(self):
        pass


@pytest.mark.asyncio
async def test_facade_runs_all_urls_with_fallback_and_progress():
    progress = []
    cfg = ScrapeConfig(
        urls=["http://x.com/a", "http://x.com/fail"],
        mode="custom",
        fields={"t": {"selector": "h1.t"}},
        concurrency=2,
        rate_per_minute=6000,
    )
    scraper = Scraper(tls_client=FakeTLS(), browser_client=FakeBrowser())
    results = await scraper.run(cfg, progress_cb=lambda done, total: progress.append((done, total)))

    by_url = {r["url"]: r for r in results}
    assert by_url["http://x.com/a"]["status"] == "ok"
    assert by_url["http://x.com/a"]["data"]["t"] == "OK"
    # the /fail URL fell back to the browser client and still succeeded
    assert by_url["http://x.com/fail"]["status"] == "ok"
    assert by_url["http://x.com/fail"]["data"]["t"] == "FROM_BROWSER"
    assert progress[-1] == (2, 2)  # final progress reports all done
