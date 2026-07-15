import asyncio
import logging
from dataclasses import dataclass
from typing import Dict, Any, Optional
from curl_cffi.requests import AsyncSession
from playwright.async_api import async_playwright, Browser, BrowserContext, Page

from src import config
from src.utils import retry_async, check_bot_challenges

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("UltimateScraper")

# Custom Exceptions for Retry Control
class ScraperError(Exception):
    """Base exception for all scraper failures."""
    pass

class ScraperBlockError(ScraperError):
    """Raised when an anti-bot challenge is detected."""
    pass

class ScraperRequestError(ScraperError):
    """Raised on connection timeouts, status code errors, or general network issues."""
    pass


@dataclass
class ScraperResponse:
    status_code: int
    text: str
    url: str
    headers: Dict[str, str]
    cookies: Dict[str, str]
    success: bool
    error_message: Optional[str] = None


class TLSClient:
    """
    High-performance request client using curl_cffi to impersonate
    browser TLS signatures and HTTP/2 characteristics.
    """
    def __init__(self, impersonate: str = config.DEFAULT_CHROME_VERSION):
        self.impersonate = impersonate

    @retry_async(max_retries=config.MAX_RETRIES, exceptions=(ScraperError,), base_delay=config.BACKOFF_FACTOR)
    async def _fetch_raw(
        self,
        url: str,
        method: str = "GET",
        headers: Optional[Dict[str, str]] = None,
        cookies: Optional[Dict[str, str]] = None,
        data: Optional[Any] = None,
        json: Optional[Any] = None,
        timeout: float = config.DEFAULT_TIMEOUT,
        proxy: Optional[str] = None
    ) -> ScraperResponse:
        logger.info(f"TLS Mode -> Requesting: {url} (Method: {method})")
        
        req_headers = {**config.DEFAULT_HEADERS, **(headers or {})}
        proxies = {"http": proxy, "https": proxy} if proxy else None

        try:
            async with AsyncSession(impersonate=self.impersonate) as session:
                response = await session.request(
                    method=method,
                    url=url,
                    headers=req_headers,
                    cookies=cookies,
                    data=data,
                    json=json,
                    timeout=timeout,
                    proxies=proxies
                )
                
                # Check status
                if response.status_code >= 500:
                    raise ScraperRequestError(f"Server Error status code: {response.status_code}")
                elif response.status_code >= 400:
                    # e.g., 403 Forbidden might indicate a silent block
                    challenge_res = check_bot_challenges(response.text, url, status_code=response.status_code, headers=dict(response.headers))
                    if challenge_res["blocked"]:
                        raise ScraperBlockError(f"Anti-bot blocked ({challenge_res['system']}): {challenge_res['reason']}")
                    raise ScraperRequestError(f"Client Error status code: {response.status_code}")

                # Check anti-bot challenges on 200 responses (common for Cloudflare walls)
                challenge_res = check_bot_challenges(response.text, url, status_code=response.status_code, headers=dict(response.headers))
                if challenge_res["blocked"]:
                    raise ScraperBlockError(f"Anti-bot blocked ({challenge_res['system']}): {challenge_res['reason']}")

                return ScraperResponse(
                    status_code=response.status_code,
                    text=response.text,
                    url=str(response.url),
                    headers=dict(response.headers),
                    cookies=response.cookies.get_dict(),
                    success=True
                )
        except ScraperError:
            # Re-raise to let retry decorator capture it
            raise
        except Exception as e:
            raise ScraperRequestError(str(e)) from e

    async def fetch(
        self,
        url: str,
        method: str = "GET",
        headers: Optional[Dict[str, str]] = None,
        cookies: Optional[Dict[str, str]] = None,
        data: Optional[Any] = None,
        json: Optional[Any] = None,
        timeout: float = config.DEFAULT_TIMEOUT,
        proxy: Optional[str] = None
    ) -> ScraperResponse:
        """Fetch wrapper wrapping retries internally to avoid throwing uncaught errors."""
        try:
            return await self._fetch_raw(
                url=url,
                method=method,
                headers=headers,
                cookies=cookies,
                data=data,
                json=json,
                timeout=timeout,
                proxy=proxy
            )
        except Exception as e:
            return ScraperResponse(
                status_code=0,
                text="",
                url=url,
                headers={},
                cookies={},
                success=False,
                error_message=str(e)
            )


class BrowserClient:
    """
    Playwright-based browser client for dynamic dynamic scraping
    and heavy interactive tasks.
    """
    def __init__(self, headless: bool = config.PLAYWRIGHT_HEADLESS, proxy: Optional[str] = None):
        self.headless = headless
        self.proxy = proxy
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None

    async def start(self):
        logger.info("Initializing Playwright Browser Client...")
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            headless=self.headless,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-infobars",
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--window-size=1920,1080",
            ]
        )
        
        # Convert proxy to Playwright format if exists
        from src.proxies import parse_to_playwright
        pw_proxy = parse_to_playwright(self.proxy) if self.proxy else None
        
        self.context = await self.browser.new_context(
            viewport=config.PLAYWRIGHT_VIEWPORT,
            user_agent=config.DEFAULT_USER_AGENT,
            locale=config.PLAYWRIGHT_LOCALE,
            color_scheme=config.PLAYWRIGHT_COLOR_SCHEME,
            proxy=pw_proxy
        )
        # Prevent webdriver and other bot detection mechanisms
        from src.stealth import get_evasion_script
        await self.context.add_init_script(get_evasion_script())

    @retry_async(max_retries=config.MAX_RETRIES, exceptions=(ScraperError,), base_delay=config.BACKOFF_FACTOR)
    async def _fetch_raw(
        self,
        url: str,
        wait_until: str = "domcontentloaded",
        timeout: float = config.DEFAULT_TIMEOUT
    ) -> ScraperResponse:
        if not self.browser or not self.context:
            await self.start()
        
        logger.info(f"Browser Mode -> Navigating to: {url}")
        page: Optional[Page] = None
        try:
            page = await self.context.new_page()
            response = await page.goto(
                url,
                wait_until=wait_until,
                timeout=timeout * 1000
            )
            
            status = response.status if response else 200
            if status >= 500:
                raise ScraperRequestError(f"Server Error status code: {status}")
            
            content = await page.content()
            
            # Check bot challenge blocks
            res_headers_for_check = await response.all_headers() if response else {}
            challenge_res = check_bot_challenges(
                content, url, status_code=status, headers=res_headers_for_check
            )
            if challenge_res["blocked"]:
                raise ScraperBlockError(f"Anti-bot blocked ({challenge_res['system']}): {challenge_res['reason']}")
                
            if status >= 400:
                raise ScraperRequestError(f"Client Error status code: {status}")

            cookies_list = await self.context.cookies(urls=[url])
            cookies_dict = {c["name"]: c["value"] for c in cookies_list}
            res_headers = await response.all_headers() if response else {}

            return ScraperResponse(
                status_code=status,
                text=content,
                url=page.url,
                headers=res_headers,
                cookies=cookies_dict,
                success=True
            )
        except ScraperError:
            raise
        except Exception as e:
            raise ScraperRequestError(str(e)) from e
        finally:
            if page:
                await page.close()

    async def fetch(
        self,
        url: str,
        wait_until: str = "domcontentloaded",
        timeout: float = config.DEFAULT_TIMEOUT
    ) -> ScraperResponse:
        """Fetch wrapper wrapping retries internally to avoid throwing uncaught errors."""
        try:
            return await self._fetch_raw(
                url=url,
                wait_until=wait_until,
                timeout=timeout
            )
        except Exception as e:
            return ScraperResponse(
                status_code=0,
                text="",
                url=url,
                headers={},
                cookies={},
                success=False,
                error_message=str(e)
            )

    async def stop(self):
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
        logger.info("Playwright Browser Client Stopped.")
