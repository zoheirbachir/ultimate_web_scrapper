import asyncio
import logging
from dataclasses import dataclass, field
from typing import Callable, Dict, Any, List, Optional

from src.scraper import TLSClient, BrowserClient
from src.parser import ProductParser
from src.utils import RateLimiter

logger = logging.getLogger("UltimateScraper.Facade")


@dataclass
class ScrapeConfig:
    urls: List[str]
    mode: str = "auto"                     # "auto" | "custom"
    fields: Dict[str, Dict[str, str]] = field(default_factory=dict)
    concurrency: int = 5
    rate_per_minute: float = 60.0
    use_browser_fallback: bool = True


class Scraper:
    """Orchestrates the TLS fast path with a browser fallback under bounded
    concurrency + a rate limiter, parsing each page per the job mode."""

    def __init__(self, tls_client=None, browser_client=None, parser=None):
        self.tls = tls_client or TLSClient()
        self.browser = browser_client or BrowserClient(headless=True)
        self.parser = parser or ProductParser()
        self._browser_started = False
        self._browser_lock = asyncio.Lock()

    def _parse(self, html: str, url: str, cfg: ScrapeConfig) -> Dict[str, Any]:
        if cfg.mode == "custom":
            return self.parser.parse_custom(html, url, cfg.fields)
        return {"url": url, "data": self.parser.parse(html, url)}

    async def _ensure_browser(self):
        async with self._browser_lock:
            if not self._browser_started:
                await self.browser.start()
                self._browser_started = True

    async def _scrape_one(self, url: str, cfg: ScrapeConfig) -> Dict[str, Any]:
        resp = await self.tls.fetch(url)
        if not resp.success and cfg.use_browser_fallback:
            logger.info(f"TLS path failed for {url}; falling back to browser.")
            await self._ensure_browser()
            resp = await self.browser.fetch(url)
        if not resp.success:
            return {"url": url, "status": "failed", "error": resp.error_message, "data": None}
        parsed = self._parse(resp.text, url, cfg)
        return {"url": url, "status": "ok", "error": None, "data": parsed["data"]}

    async def run(self, cfg: ScrapeConfig,
                  progress_cb: Optional[Callable[[int, int], None]] = None) -> List[Dict[str, Any]]:
        total = len(cfg.urls)
        results: List[Optional[Dict[str, Any]]] = [None] * total
        limiter = RateLimiter(cfg.rate_per_minute)
        sem = asyncio.Semaphore(max(1, cfg.concurrency))
        done = 0
        done_lock = asyncio.Lock()

        async def worker(i: int, url: str):
            nonlocal done
            async with sem:
                await limiter.wait()
                try:
                    results[i] = await self._scrape_one(url, cfg)
                except Exception as e:  # never let one URL kill the batch
                    results[i] = {"url": url, "status": "failed", "error": str(e), "data": None}
            async with done_lock:
                done += 1
                if progress_cb:
                    progress_cb(done, total)

        await asyncio.gather(*(worker(i, u) for i, u in enumerate(cfg.urls)))
        return [r for r in results if r is not None]

    async def aclose(self):
        await self.tls.aclose()
        if self._browser_started:
            await self.browser.stop()
