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

CLOUDFLARE_SIGNATURES = [
    "attention required! | cloudflare",
    "cf-browser-verification",
    "cf-cookie-error",
    "challenge-form",
    "turnstile",
    "cf-challenge"
]

DATADOME_SIGNATURES = [
    "datadome",
    "ddjs",
    "captcha.datadome.co"
]

AKAMAI_SIGNATURES = [
    "sec-cpt",
    "akamai-bot",
    "akamai_captcha"
]

CAPTCHA_SIGNATURES = [
    "captcha",
    "recaptcha",
    "g-recaptcha",
    "hcaptcha",
    "robot check",
    "please confirm you are a human"
]

def check_bot_challenges(html_content: str, url: str) -> Dict[str, Any]:
    """
    Inspects HTML content to check if requests triggered bot challenge blocks or captcha screens.
    """
    if not html_content:
        return {"blocked": False, "system": None, "reason": None}
        
    html_lower = html_content.lower()
    
    # 1. Cloudflare Check
    for sig in CLOUDFLARE_SIGNATURES:
        if sig in html_lower:
            logger.error(f"Cloudflare block challenge detected at url: {url}")
            return {"blocked": True, "system": "Cloudflare", "reason": f"Matched signature: {sig}"}
            
    # 2. DataDome Check
    for sig in DATADOME_SIGNATURES:
        if sig in html_lower:
            logger.error(f"DataDome block challenge detected at url: {url}")
            return {"blocked": True, "system": "DataDome", "reason": f"Matched signature: {sig}"}
            
    # 3. Akamai Check
    for sig in AKAMAI_SIGNATURES:
        if sig in html_lower:
            logger.error(f"Akamai block challenge detected at url: {url}")
            return {"blocked": True, "system": "Akamai", "reason": f"Matched signature: {sig}"}
            
    # 4. Generic Captchas
    for sig in CAPTCHA_SIGNATURES:
        if sig in html_lower:
            logger.error(f"Generic bot blocker/CAPTCHA page detected at url: {url}")
            return {"blocked": True, "system": "Generic CAPTCHA", "reason": f"Matched signature: {sig}"}
            
    return {"blocked": False, "system": None, "reason": None}
