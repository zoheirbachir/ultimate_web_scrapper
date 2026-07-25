import asyncio
import logging
import random
import time
from functools import wraps
from typing import Callable, Any, List, Type, Dict

logger = logging.getLogger("UltimateScraper.Utils")

def calculate_backoff(attempt: int, base_delay: float = 2.0, max_delay: float = 60.0) -> float:
    """Calculates exponential backoff delay with random jitter."""
    # Exponential increase: base * 2^attempt
    delay = base_delay * (2 ** attempt)
    # Add random jitter (0 to 50% of delay value)
    jitter = random.uniform(0, delay * 0.5)
    total_delay = min(delay + jitter, max_delay)
    return total_delay


def retry_async(
    max_retries: int = 3,
    exceptions: List[Type[BaseException]] = (Exception,),
    base_delay: float = 2.0,
    max_delay: float = 30.0
):
    """
    Decorator to retry asynchronous functions with exponential backoff and random jitter.
    """
    def decorator(func: Callable[..., Any]):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt == max_retries:
                        logger.error(
                            f"Function {func.__name__} failed after {max_retries} retries. "
                            f"Final Error: {e}"
                        )
                        break

                    delay = calculate_backoff(attempt, base_delay, max_delay)
                    logger.warning(
                        f"Exception caught in {func.__name__}: {e}. "
                        f"Attempt {attempt + 1}/{max_retries} failed. Retrying in {delay:.2f}s..."
                    )
                    await asyncio.sleep(delay)
            raise last_exception
        return wrapper
    return decorator


class RateLimiter:
    """Simple asynchronous rate limiter ensuring a min delay gap between calls."""
    def __init__(self, requests_per_minute: float):
        self.delay_gap = 60.0 / requests_per_minute
        self.last_call_time = 0.0

    async def wait(self):
        """Asynchronously waits if the elapsed time since last call is shorter than the delay gap."""
        now = time.time()
        elapsed = now - self.last_call_time
        if elapsed < self.delay_gap:
            wait_time = self.delay_gap - elapsed
            logger.info(f"Rate Limiter -> Throttling call for {wait_time:.2f}s")
            await asyncio.sleep(wait_time)
        self.last_call_time = time.time()


# --- Anti-Bot & Bot Challenge Signatures ---

# Cloudflare: challenge page <title> text (returned even with HTTP 200 on JS challenge)
CLOUDFLARE_TITLE_MARKERS = [
    "attention required! | cloudflare",
    "just a moment...",
    "checking your browser before accessing",
]
# Cloudflare: challenge-platform script hosts (strong, low-false-positive signal)
CLOUDFLARE_SCRIPT_MARKERS = [
    "challenges.cloudflare.com/turnstile",
    "/cdn-cgi/challenge-platform/",
]
# DataDome infrastructure hosts
DATADOME_MARKERS = [
    "geo.captcha-delivery.com",
    "captcha.datadome.co",
    "js.datadome.co",
]
# Akamai Bot Manager challenge markers
AKAMAI_MARKERS = [
    "/_sec/cp_challenge/",
    "ak_bmsc",
]
# Generic CAPTCHA widgets — ONLY treated as a block when the response is also a
# challenge status, to avoid flagging normal pages that embed a captcha (e.g. logins).
GENERIC_CAPTCHA_MARKERS = [
    "g-recaptcha",
    "h-captcha",
    "hcaptcha.com/captcha",
    "www.google.com/recaptcha/api",
]
CHALLENGE_STATUS_CODES = {401, 403, 429, 503}


def _blocked(system: str, reason: str, url: str) -> Dict[str, Any]:
    logger.warning(f"{system} challenge detected at {url}: {reason}")
    return {"blocked": True, "system": system, "reason": reason}


def check_bot_challenges(
    html_content: str,
    url: str,
    status_code: int = 200,
    headers: Dict[str, str] = None,
) -> Dict[str, Any]:
    """
    Detect anti-bot / challenge responses using precise infrastructure markers,
    challenge-page titles, response headers, and status code — NOT loose body
    substrings. Backward-compatible: callers may pass only (html_content, url).
    """
    html_lower = (html_content or "").lower()
    hdrs = {k.lower(): (v or "").lower() for k, v in (headers or {}).items()}

    # 1. Cloudflare — explicit header or explicit challenge title with 403/503/429 status
    if hdrs.get("cf-mitigated") == "challenge":
        return _blocked("Cloudflare", "cf-mitigated: challenge header", url)
        
    if any(m in html_lower for m in CLOUDFLARE_TITLE_MARKERS):
        if status_code in CHALLENGE_STATUS_CODES or "cf-browser-verification" in html_lower:
            return _blocked("Cloudflare", "challenge page title", url)

    # 2. DataDome — infrastructure hosts with challenge status.
    if status_code in CHALLENGE_STATUS_CODES and any(m in html_lower for m in DATADOME_MARKERS):
        return _blocked("DataDome", "DataDome infrastructure host present", url)

    # 3. Akamai — challenge path / cookie marker with challenge status.
    if status_code in CHALLENGE_STATUS_CODES and any(m in html_lower for m in AKAMAI_MARKERS):
        return _blocked("Akamai", "Akamai Bot Manager marker present", url)

    # 4. Generic CAPTCHA widgets — only when the response itself is a challenge status.
    if status_code in CHALLENGE_STATUS_CODES and any(m in html_lower for m in GENERIC_CAPTCHA_MARKERS):
        return _blocked("Generic CAPTCHA", f"captcha widget on {status_code} response", url)

    return {"blocked": False, "system": None, "reason": None}
