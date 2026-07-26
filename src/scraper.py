import asyncio
import logging
from dataclasses import dataclass
from typing import Dict, Any, Optional
from curl_cffi.requests import AsyncSession
try:
    from patchright.async_api import async_playwright, Browser, BrowserContext, Page
except ImportError:  # fallback if patchright is unavailable
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
    High-performance request client using curl_cffi to impersonate browser TLS
    signatures. A single AsyncSession is created lazily and reused for keep-alive
    and cookie persistence across requests.
    """
    def __init__(self, impersonate: str = config.DEFAULT_CHROME_VERSION,
                 session_factory=None, rotator=None, ua_pool=None):
        self.impersonate = impersonate
        self._session_factory = session_factory or (lambda: AsyncSession(impersonate=self.impersonate))
        self._session = None
        self.rotator = rotator
        self.ua_pool = ua_pool or list(config.USER_AGENT_POOL)

    def _get_session(self):
        if self._session is None:
            self._session = self._session_factory()
        return self._session

    async def aclose(self):
        if self._session is not None:
            try:
                await self._session.close()
            except Exception:
                pass
            self._session = None

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
            session = self._get_session()
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
        """Fetch with a rotation-aware retry loop. On an anti-bot block, the current
        proxy is marked failed and proxy + user-agent are rotated before retrying."""
        import random
        from src.utils import calculate_backoff
        last_error = None
        current_proxy = proxy or (self.rotator.get_proxy() if self.rotator else None)
        for attempt in range(config.MAX_RETRIES + 1):
            req_headers = dict(headers or {})
            if self.ua_pool:
                req_headers.setdefault("User-Agent", random.choice(self.ua_pool))
            try:
                res = await self._fetch_raw(
                    url, method=method, headers=req_headers, cookies=cookies,
                    data=data, json=json, timeout=timeout, proxy=current_proxy
                )
                if self.rotator and current_proxy:
                    self.rotator.mark_success(current_proxy)
                return res
            except ScraperBlockError as e:
                last_error = e
                if self.rotator and current_proxy:
                    self.rotator.mark_failed(current_proxy)
                    current_proxy = self.rotator.get_proxy()
                if attempt < config.MAX_RETRIES:
                    await asyncio.sleep(calculate_backoff(attempt, config.BACKOFF_FACTOR))
            except ScraperError as e:
                last_error = e
                if attempt < config.MAX_RETRIES:
                    await asyncio.sleep(calculate_backoff(attempt, config.BACKOFF_FACTOR))
            except Exception as e:
                last_error = e
                break
        return ScraperResponse(status_code=0, text="", url=url, headers={}, cookies={},
                               success=False, error_message=str(last_error))


def build_persistent_context_kwargs(headless: bool, proxy: Optional[str] = None) -> Dict[str, Any]:
    """Assemble launch_persistent_context kwargs from stealth config (pure function)."""
    import os, sys, tempfile
    is_cloud_linux = sys.platform != "win32" or bool(os.environ.get("RENDER") or os.environ.get("PORT"))

    user_dir = tempfile.mkdtemp(prefix="pw_userdata_") if is_cloud_linux else config.USER_DATA_DIR
    launch_headless = True if is_cloud_linux else headless
    launch_channel = None if is_cloud_linux else config.BROWSER_CHANNEL
    launch_args = ["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"] if is_cloud_linux else list(config.BROWSER_LAUNCH_ARGS)

    kwargs: Dict[str, Any] = {
        "user_data_dir": user_dir,
        "headless": launch_headless,
        "locale": config.PLAYWRIGHT_LOCALE,
        "timezone_id": config.PLAYWRIGHT_TIMEZONE,
        "color_scheme": config.PLAYWRIGHT_COLOR_SCHEME,
        "viewport": config.PLAYWRIGHT_VIEWPORT,
        "args": launch_args,
    }
    if launch_channel:
        kwargs["channel"] = launch_channel

    if proxy:
        from src.proxies import parse_to_playwright
        pw_proxy = parse_to_playwright(proxy)
        if pw_proxy:
            kwargs["proxy"] = pw_proxy
    return kwargs


class BrowserClient:
    """
    patchright-based browser client for dynamic scraping and heavy interactive
    tasks. Uses a persistent context so the profile looks like a real user; stealth
    is handled at the CDP level by patchright (no injected JS evasion script).
    """
    def __init__(self, headless: bool = config.PLAYWRIGHT_HEADLESS, proxy: Optional[str] = None):
        self.headless = headless
        self.proxy = proxy
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None

    async def start(self):
        if self.context:
            return
        logger.info("Initializing patchright persistent browser context...")
        try:
            self.playwright = await async_playwright().start()
            kwargs = build_persistent_context_kwargs(self.headless, self.proxy)
            self.context = await self.playwright.chromium.launch_persistent_context(**kwargs)
            self.browser = self.context.browser  # may be None for persistent contexts
        except Exception as e:
            if "Executable doesn't exist" in str(e) or "patchright install" in str(e):
                logger.warning("Patchright browser binary missing; auto-installing patchright chromium...")
                import subprocess, sys
                subprocess.run([sys.executable, "-m", "patchright", "install", "chromium"], check=True)
                if not self.playwright:
                    self.playwright = await async_playwright().start()
                kwargs = build_persistent_context_kwargs(self.headless, self.proxy)
                self.context = await self.playwright.chromium.launch_persistent_context(**kwargs)
                self.browser = self.context.browser
            else:
                raise e

    @retry_async(max_retries=config.MAX_RETRIES, exceptions=(ScraperError,), base_delay=config.BACKOFF_FACTOR)
    async def _fetch_raw(
        self,
        url: str,
        wait_until: str = "domcontentloaded",
        timeout: float = config.DEFAULT_TIMEOUT
    ) -> ScraperResponse:
        if not self.context:
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

            # Allow client-side rendering (APIs/GraphQL) to execute for known SPA websites
            if any(domain in url.lower() for domain in ["kricar-dz.com", "ouedkniss.com"]):
                logger.info("SPA detected, waiting 6 seconds for client-side scripts to render...")
                await page.wait_for_timeout(6000)

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
        if self.playwright:
            await self.playwright.stop()
        logger.info("patchright Browser Client Stopped.")
