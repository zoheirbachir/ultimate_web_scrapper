import asyncio
from src.scraper_facade import Scraper, ScrapeConfig


async def main():
    scraper = Scraper()
    cfg = ScrapeConfig(
        urls=["https://httpbin.org/html", "https://example.com"],
        mode="custom",
        fields={"heading": {"selector": "h1"}},
        concurrency=2,
        rate_per_minute=120,
        use_browser_fallback=False,
    )
    results = await scraper.run(cfg, progress_cb=lambda d, t: print(f"progress {d}/{t}"))
    for r in results:
        print(r["status"], r["url"], r.get("data"))
    await scraper.aclose()


if __name__ == "__main__":
    asyncio.run(main())
