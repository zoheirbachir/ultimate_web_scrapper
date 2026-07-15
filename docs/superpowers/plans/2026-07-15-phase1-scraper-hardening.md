# Phase 1 — Scraper Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Harden the existing Python scraper so it runs reliably as a service — precise anti-bot detection, session reuse, fingerprint rotation on block, real patchright stealth, a generalized parser, and a concurrency-bounded `Scraper` facade with a progress callback.

**Architecture:** Keep the current `src/` package in place; fix behavior in each module and add one new `src/scraper_facade.py` that orchestrates the fast (curl_cffi) path with a browser (patchright) fallback under a semaphore + rate limiter. A new `pytest` suite under `tests/` covers the changes with mocked network; existing root `test_*.py` scripts stay as manual integration checks.

**Tech Stack:** Python 3.13, curl_cffi, patchright/playwright, selectolax, BeautifulSoup, numpy, pytest, pytest-asyncio.

---

## File map

- Modify: `src/utils.py` — precise `check_bot_challenges(html, url, status_code=200, headers=None)`
- Modify: `src/scraper.py` — session reuse in `TLSClient`; rotation-on-block retry loop; patchright `BrowserClient`
- Modify: `src/config.py` — add `USER_AGENT_POOL`
- Modify: `src/parser.py` — add `parse_custom(html, url, fields)`
- Create: `src/scraper_facade.py` — `Scraper` facade (concurrency, rate limit, fallback, progress)
- Create: `tests/__init__.py`, `tests/conftest.py`
- Create: `tests/test_bot_detection.py`, `tests/test_tls_client.py`, `tests/test_browser_config.py`, `tests/test_parser_custom.py`, `tests/test_facade.py`
- Create: `pytest.ini`
- Modify: `requirements.txt` — add `pytest`, `pytest-asyncio`

---

## Task 0: Test tooling + repo init

**Files:**
- Create: `pytest.ini`, `tests/__init__.py`, `tests/conftest.py`
- Modify: `requirements.txt`

- [ ] **Step 1: Initialize git (first run only)**

Run:
```bash
git init
printf "venv/\n__pycache__/\n*.pyc\n.userdata/\nexports/\n*.db\n.env\nnode_modules/\n.next/\n" > .gitignore
git add -A && git commit -m "chore: baseline before scraper hardening"
```

- [ ] **Step 2: Add test deps to `requirements.txt`**

Append these lines:
```
# ── Testing ──────────────────────────────────────────────────────────
pytest>=8.0.0
pytest-asyncio>=0.23.0
```

Run: `pip install pytest pytest-asyncio`

- [ ] **Step 3: Create `pytest.ini`** (collect only from `tests/`, enable asyncio)

```ini
[pytest]
testpaths = tests
asyncio_mode = auto
addopts = -ra -q
```

- [ ] **Step 4: Create `tests/__init__.py`** (empty file)

```python
```

- [ ] **Step 5: Create `tests/conftest.py`** (ensure project root importable)

```python
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
```

- [ ] **Step 6: Verify pytest runs with no tests yet**

Run: `pytest`
Expected: exit code 5 ("no tests ran") — confirms config is valid.

- [ ] **Step 7: Commit**

```bash
git add requirements.txt pytest.ini tests/__init__.py tests/conftest.py
git commit -m "chore: add pytest suite scaffolding"
```

---

## Task 1: Precise anti-bot challenge detection

Replace body-substring matching (which flags any page containing the word "captcha") with detection keyed on infrastructure markers, challenge titles, headers, and status code. Signature stays backward-compatible so existing scripts keep working.

**Files:**
- Modify: `src/utils.py:73-138` (the signatures block + `check_bot_challenges`)
- Test: `tests/test_bot_detection.py`

- [ ] **Step 1: Write the failing test**

`tests/test_bot_detection.py`:
```python
from src.utils import check_bot_challenges


def test_normal_page_mentioning_captcha_is_not_blocked():
    html = "<html><body><p>Please solve the captcha to post a comment.</p></body></html>"
    res = check_bot_challenges(html, "http://shop.example/item", status_code=200,
                               headers={"server": "nginx"})
    assert res["blocked"] is False


def test_cloudflare_title_challenge_blocked():
    html = "<html><head><title>Just a moment...</title></head></html>"
    res = check_bot_challenges(html, "http://x.com", status_code=403,
                               headers={"server": "cloudflare"})
    assert res["blocked"] is True
    assert res["system"] == "Cloudflare"


def test_cloudflare_mitigated_header_blocked():
    res = check_bot_challenges("<html></html>", "http://x.com", status_code=403,
                               headers={"cf-mitigated": "challenge"})
    assert res["blocked"] is True
    assert res["system"] == "Cloudflare"


def test_cloudflare_turnstile_script_blocked():
    html = "<html><body><script src='https://challenges.cloudflare.com/turnstile/v0/api.js'></script></body></html>"
    res = check_bot_challenges(html, "http://x.com", status_code=200, headers={})
    assert res["blocked"] is True
    assert res["system"] == "Cloudflare"


def test_datadome_marker_blocked():
    html = "<html><body><script src='https://geo.captcha-delivery.com/captcha/'></script></body></html>"
    res = check_bot_challenges(html, "http://x.com", status_code=403, headers={})
    assert res["blocked"] is True
    assert res["system"] == "DataDome"


def test_generic_recaptcha_only_on_challenge_status():
    html = "<html><body><div class='g-recaptcha'></div></body></html>"
    # 200 with a recaptcha widget (e.g. a normal login page) -> not a block
    assert check_bot_challenges(html, "http://x.com", status_code=200, headers={})["blocked"] is False
    # same widget behind a 403 wall -> block
    assert check_bot_challenges(html, "http://x.com", status_code=403, headers={})["blocked"] is True


def test_backward_compatible_two_arg_call():
    # old call sites pass only (html, url); CF title must still be detected
    old_cf = "<html><head><title>Attention Required! | Cloudflare</title></head></html>"
    assert check_bot_challenges(old_cf, "http://x.com")["blocked"] is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_bot_detection.py -v`
Expected: FAIL — current `check_bot_challenges` takes only `(html_content, url)` and matches on substrings, so `test_generic_recaptcha_only_on_challenge_status` and the keyword-arg calls fail.

- [ ] **Step 3: Replace the detection block in `src/utils.py`**

Replace lines 73-138 (from `# --- Anti-Bot & Bot Challenge Signatures ---` through the end of `check_bot_challenges`) with:

```python
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

    # 1. Cloudflare — header, then script host, then challenge title.
    if hdrs.get("cf-mitigated") == "challenge":
        return _blocked("Cloudflare", "cf-mitigated: challenge header", url)
    if any(m in html_lower for m in CLOUDFLARE_SCRIPT_MARKERS):
        return _blocked("Cloudflare", "challenge-platform script present", url)
    if any(m in html_lower for m in CLOUDFLARE_TITLE_MARKERS):
        return _blocked("Cloudflare", "challenge page title", url)

    # 2. DataDome — infrastructure hosts.
    if any(m in html_lower for m in DATADOME_MARKERS):
        return _blocked("DataDome", "DataDome infrastructure host present", url)

    # 3. Akamai — challenge path / cookie marker.
    if any(m in html_lower for m in AKAMAI_MARKERS):
        return _blocked("Akamai", "Akamai Bot Manager marker present", url)

    # 4. Generic CAPTCHA widgets — only when the response itself is a challenge status.
    if status_code in CHALLENGE_STATUS_CODES and any(m in html_lower for m in GENERIC_CAPTCHA_MARKERS):
        return _blocked("Generic CAPTCHA", f"captcha widget on {status_code} response", url)

    return {"blocked": False, "system": None, "reason": None}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_bot_detection.py -v`
Expected: PASS (7 passed)

- [ ] **Step 5: Update call sites in `src/scraper.py` to pass status + headers**

In `TLSClient._fetch_raw`, replace the two `check_bot_challenges(response.text, url)` calls (around lines 83 and 89) with:
```python
challenge_res = check_bot_challenges(
    response.text, url, status_code=response.status_code, headers=dict(response.headers)
)
```

In `BrowserClient._fetch_raw`, replace `check_bot_challenges(content, url)` (around line 210) with:
```python
res_headers_for_check = await response.all_headers() if response else {}
challenge_res = check_bot_challenges(
    content, url, status_code=status, headers=res_headers_for_check
)
```

- [ ] **Step 6: Run the full suite**

Run: `pytest -v`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add src/utils.py src/scraper.py tests/test_bot_detection.py
git commit -m "feat(scraper): precise anti-bot detection to remove false positives"
```

---

## Task 2: Reuse the curl_cffi session in TLSClient

`TLSClient` currently opens a fresh `AsyncSession` per request (no keep-alive, no cookie persistence). Create one session, reuse it, and close it explicitly. A `session_factory` parameter makes it unit-testable.

**Files:**
- Modify: `src/scraper.py` (`TLSClient`)
- Test: `tests/test_tls_client.py`

- [ ] **Step 1: Write the failing test**

`tests/test_tls_client.py`:
```python
import pytest
from src.scraper import TLSClient, ScraperResponse


class FakeResponse:
    def __init__(self, status_code=200, text="<html>ok</html>", url="http://x.com"):
        self.status_code = status_code
        self.text = text
        self.url = url
        self.headers = {"server": "nginx"}
        self.cookies = type("C", (), {"get_dict": lambda self: {}})()


class FakeSession:
    instances = 0

    def __init__(self, *args, **kwargs):
        FakeSession.instances += 1

    async def request(self, *args, **kwargs):
        return FakeResponse()

    async def close(self):
        pass


@pytest.mark.asyncio
async def test_session_is_reused_across_fetches():
    FakeSession.instances = 0
    client = TLSClient(session_factory=lambda: FakeSession())
    r1 = await client.fetch("http://x.com/a")
    r2 = await client.fetch("http://x.com/b")
    await client.aclose()
    assert r1.success and r2.success
    assert FakeSession.instances == 1  # one session shared by both fetches
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_tls_client.py -v`
Expected: FAIL — `TLSClient.__init__` has no `session_factory` param and no `aclose`.

- [ ] **Step 3: Refactor `TLSClient` for session reuse**

In `src/scraper.py`, replace the `TLSClient` `__init__` and the `async with AsyncSession(...)` block. New `__init__`:
```python
class TLSClient:
    """
    High-performance request client using curl_cffi to impersonate browser TLS
    signatures. A single AsyncSession is created lazily and reused for keep-alive
    and cookie persistence across requests.
    """
    def __init__(self, impersonate: str = config.DEFAULT_CHROME_VERSION, session_factory=None):
        self.impersonate = impersonate
        self._session_factory = session_factory or (lambda: AsyncSession(impersonate=self.impersonate))
        self._session = None

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
```

In `_fetch_raw`, replace:
```python
            async with AsyncSession(impersonate=self.impersonate) as session:
                response = await session.request(
```
with:
```python
            session = self._get_session()
            response = await session.request(
```
and de-indent the rest of that `try` block by one level (remove the `async with` wrapper — keep the `try/except` that surrounds it).

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_tls_client.py -v`
Expected: PASS

- [ ] **Step 5: Run the full suite**

Run: `pytest`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/scraper.py tests/test_tls_client.py
git commit -m "feat(scraper): reuse curl_cffi session for keep-alive and cookie persistence"
```

---

## Task 3: Rotate proxy + user-agent on block

On a `ScraperBlockError`, retrying the same fingerprint is wasted effort. Give `TLSClient.fetch` a retry loop that, when a rotator is supplied, marks the current proxy failed and switches proxy + UA before the next attempt.

**Files:**
- Modify: `src/config.py` (add `USER_AGENT_POOL`)
- Modify: `src/scraper.py` (`TLSClient.fetch`)
- Test: `tests/test_tls_client.py` (add cases)

- [ ] **Step 1: Add `USER_AGENT_POOL` to `src/config.py`**

Append:
```python
# Pool of realistic desktop Chrome UAs, rotated on block alongside the proxy.
USER_AGENT_POOL = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
]
```

- [ ] **Step 2: Write the failing test** (append to `tests/test_tls_client.py`)

```python
from src.scraper import ScraperBlockError


class RotatingFakeSession:
    """Blocks on the first proxy, succeeds on any other."""
    def __init__(self):
        pass

    async def request(self, *args, **kwargs):
        proxies = kwargs.get("proxies") or {}
        if proxies.get("https") == "http://bad:1@h:1":
            return FakeResponse(status_code=403,
                                text="<title>Just a moment...</title>",
                                url="http://x.com")
        return FakeResponse(status_code=200, text="<html>ok</html>")

    async def close(self):
        pass


class StubRotator:
    def __init__(self):
        self.calls = ["http://bad:1@h:1", "http://good:1@h:2"]
        self.i = -1
        self.failed = []

    def get_proxy(self):
        self.i += 1
        return self.calls[min(self.i, len(self.calls) - 1)]

    def mark_failed(self, p):
        self.failed.append(p)

    def mark_success(self, p):
        pass


@pytest.mark.asyncio
async def test_rotates_proxy_and_ua_on_block():
    from src import config
    config.MAX_RETRIES = 3
    config.BACKOFF_FACTOR = 0.01
    rotator = StubRotator()
    client = TLSClient(session_factory=lambda: RotatingFakeSession(), rotator=rotator)
    res = await client.fetch("http://x.com")
    await client.aclose()
    assert res.success is True                     # recovered after rotating
    assert "http://bad:1@h:1" in rotator.failed    # first proxy marked failed
```

- [ ] **Step 3: Run test to verify it fails**

Run: `pytest tests/test_tls_client.py::test_rotates_proxy_and_ua_on_block -v`
Expected: FAIL — `TLSClient` takes no `rotator`, and `fetch` doesn't rotate.

- [ ] **Step 4: Implement rotation in `TLSClient`**

Add `rotator` and `ua_pool` to `__init__`:
```python
    def __init__(self, impersonate: str = config.DEFAULT_CHROME_VERSION,
                 session_factory=None, rotator=None, ua_pool=None):
        self.impersonate = impersonate
        self._session_factory = session_factory or (lambda: AsyncSession(impersonate=self.impersonate))
        self._session = None
        self.rotator = rotator
        self.ua_pool = ua_pool or list(config.USER_AGENT_POOL)
```

Remove the `@retry_async(...)` decorator from `_fetch_raw` (rotation is now handled in `fetch`). Replace the `fetch` method body with an explicit rotation-aware retry loop:
```python
    async def fetch(self, url, method="GET", headers=None, cookies=None, data=None,
                    json=None, timeout=config.DEFAULT_TIMEOUT, proxy=None):
        import random
        from src.utils import calculate_backoff
        last_error = None
        current_proxy = proxy or (self.rotator.get_proxy() if self.rotator else None)
        for attempt in range(config.MAX_RETRIES + 1):
            req_headers = dict(headers or {})
            if self.ua_pool:
                req_headers.setdefault("User-Agent", random.choice(self.ua_pool))
            try:
                res = await self._fetch_raw(url, method=method, headers=req_headers,
                                            cookies=cookies, data=data, json=json,
                                            timeout=timeout, proxy=current_proxy)
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
```

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest tests/test_tls_client.py -v`
Expected: PASS (all cases, including the session-reuse test from Task 2)

- [ ] **Step 6: Commit**

```bash
git add src/config.py src/scraper.py tests/test_tls_client.py
git commit -m "feat(scraper): rotate proxy and user-agent on anti-bot block"
```

---

## Task 4: Switch BrowserClient to patchright + persistent context

Replace vanilla Playwright + manual JS evasion (a detectable tell) with patchright's persistent context, applying the configured timezone/locale and dropping the fingerprintable launch args. The context-kwargs builder is a pure function so it can be unit-tested without launching a browser.

**Files:**
- Modify: `src/scraper.py` (`BrowserClient`)
- Test: `tests/test_browser_config.py`

- [ ] **Step 1: Write the failing test**

`tests/test_browser_config.py`:
```python
from src.scraper import build_persistent_context_kwargs
from src import config


def test_context_kwargs_apply_stealth_config():
    kwargs = build_persistent_context_kwargs(headless=True, proxy=None)
    assert kwargs["locale"] == config.PLAYWRIGHT_LOCALE
    assert kwargs["timezone_id"] == config.PLAYWRIGHT_TIMEZONE
    assert kwargs["channel"] == config.BROWSER_CHANNEL
    assert kwargs["user_data_dir"] == config.USER_DATA_DIR
    # fingerprintable automation flags must NOT be present
    args = kwargs.get("args", [])
    assert "--disable-blink-features=AutomationControlled" not in args
    assert "--no-sandbox" not in args


def test_context_kwargs_include_proxy_when_given():
    kwargs = build_persistent_context_kwargs(headless=True,
                                             proxy="http://user:pass@host:8080")
    assert kwargs["proxy"]["server"] == "http://host:8080"
    assert kwargs["proxy"]["username"] == "user"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_browser_config.py -v`
Expected: FAIL — `build_persistent_context_kwargs` does not exist.

- [ ] **Step 3: Add the builder and rewrite `BrowserClient.start`**

In `src/scraper.py`, change the top import:
```python
try:
    from patchright.async_api import async_playwright, Browser, BrowserContext, Page
except ImportError:  # fallback if patchright is unavailable
    from playwright.async_api import async_playwright, Browser, BrowserContext, Page
```

Add this module-level function above `BrowserClient`:
```python
def build_persistent_context_kwargs(headless: bool, proxy: Optional[str] = None) -> Dict[str, Any]:
    """Assemble launch_persistent_context kwargs from stealth config (pure function)."""
    kwargs: Dict[str, Any] = {
        "user_data_dir": config.USER_DATA_DIR,
        "channel": config.BROWSER_CHANNEL,
        "headless": headless,
        "locale": config.PLAYWRIGHT_LOCALE,
        "timezone_id": config.PLAYWRIGHT_TIMEZONE,
        "color_scheme": config.PLAYWRIGHT_COLOR_SCHEME,
        "viewport": config.PLAYWRIGHT_VIEWPORT,
        "args": list(config.BROWSER_LAUNCH_ARGS),   # deliberately empty
    }
    if proxy:
        from src.proxies import parse_to_playwright
        pw_proxy = parse_to_playwright(proxy)
        if pw_proxy:
            kwargs["proxy"] = pw_proxy
    return kwargs
```

Rewrite `BrowserClient.start` to use a persistent context (no manual evasion script, no flagged args):
```python
    async def start(self):
        logger.info("Initializing patchright persistent browser context...")
        self.playwright = await async_playwright().start()
        kwargs = build_persistent_context_kwargs(self.headless, self.proxy)
        self.context = await self.playwright.chromium.launch_persistent_context(**kwargs)
        self.browser = self.context.browser  # may be None for persistent contexts
```

Update `BrowserClient.stop` to not double-close a `None` browser:
```python
    async def stop(self):
        if self.context:
            await self.context.close()
        if self.playwright:
            await self.playwright.stop()
        logger.info("patchright Browser Client Stopped.")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_browser_config.py -v`
Expected: PASS

- [ ] **Step 5: Run the full suite**

Run: `pytest`
Expected: PASS

- [ ] **Step 6: Install the patchright browser binary (one-time, manual)**

Run: `patchright install chrome`
Note: if that fails in your environment, `playwright install chromium` + set `config.BROWSER_CHANNEL = "chromium"` is the fallback. This is an environment step, not covered by unit tests.

- [ ] **Step 7: Commit**

```bash
git add src/scraper.py tests/test_browser_config.py
git commit -m "feat(scraper): patchright persistent context replaces JS evasion script"
```

---

## Task 5: Generalized parser — custom fields mode

The parser only returns a fixed product schema. Add `parse_custom(html, url, fields)` so a job can extract arbitrary user-defined fields via CSS selectors (+ optional attribute), enabling non-e-commerce use.

**Files:**
- Modify: `src/parser.py` (`ProductParser`)
- Test: `tests/test_parser_custom.py`

- [ ] **Step 1: Write the failing test**

`tests/test_parser_custom.py`:
```python
from src.parser import ProductParser

HTML = """
<html><body>
  <h1 class="headline">Big News Today</h1>
  <span class="author">Jane Doe</span>
  <a class="src" href="https://example.com/full">read more</a>
  <img class="hero" src="/img/x.jpg">
</body></html>
"""


def test_parse_custom_extracts_text_and_attributes():
    parser = ProductParser()
    fields = {
        "title": {"selector": "h1.headline"},
        "author": {"selector": ".author"},
        "link": {"selector": "a.src", "attr": "href"},
        "image": {"selector": "img.hero", "attr": "src"},
        "missing": {"selector": ".nope"},
    }
    out = parser.parse_custom(HTML, "https://example.com/article", fields)
    assert out["url"] == "https://example.com/article"
    assert out["data"]["title"] == "Big News Today"
    assert out["data"]["author"] == "Jane Doe"
    assert out["data"]["link"] == "https://example.com/full"
    assert out["data"]["image"] == "https://example.com/img/x.jpg"  # resolved to absolute
    assert out["data"]["missing"] is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_parser_custom.py -v`
Expected: FAIL — `ProductParser` has no `parse_custom`.

- [ ] **Step 3: Add `parse_custom` to `ProductParser`**

In `src/parser.py`, add this method to the `ProductParser` class:
```python
    def parse_custom(self, html: str, url: str, fields: Dict[str, Dict[str, str]]) -> Dict[str, Any]:
        """
        Extract user-defined fields. `fields` maps a field name to
        {"selector": <css>, "attr": <optional attribute>}. When "attr" is set,
        the attribute value is returned (URLs resolved absolute); otherwise the
        element's text is returned. Missing selectors yield None.
        """
        from urllib.parse import urljoin
        tree = HTMLParser(html or "")
        data: Dict[str, Any] = {}
        for name, spec in (fields or {}).items():
            selector = spec.get("selector")
            attr = spec.get("attr")
            value = None
            if selector:
                node = tree.css_first(selector)
                if node is not None:
                    if attr:
                        raw = node.attributes.get(attr)
                        if raw and attr in ("href", "src") and url:
                            raw = urljoin(url, raw)
                        value = raw
                    else:
                        value = self.clean_text(node.text())
            data[name] = value
        return {"url": url, "data": data}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_parser_custom.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/parser.py tests/test_parser_custom.py
git commit -m "feat(parser): add custom-fields extraction mode"
```

---

## Task 6: Scraper facade — concurrency, rate limit, fallback, progress

Tie the pieces together in one entry point the backend worker will call: iterate URLs with bounded concurrency and a rate limiter, try the TLS fast path first and fall back to the browser on failure, parse per mode, and emit a progress callback after each URL.

**Files:**
- Create: `src/scraper_facade.py`
- Test: `tests/test_facade.py`

- [ ] **Step 1: Write the failing test**

`tests/test_facade.py`:
```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_facade.py -v`
Expected: FAIL — `src/scraper_facade.py` does not exist.

- [ ] **Step 3: Create `src/scraper_facade.py`**

```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_facade.py -v`
Expected: PASS

- [ ] **Step 5: Run the full suite**

Run: `pytest`
Expected: PASS (all tests across every file)

- [ ] **Step 6: Commit**

```bash
git add src/scraper_facade.py tests/test_facade.py
git commit -m "feat(scraper): add Scraper facade with concurrency, rate limit, and fallback"
```

---

## Task 7: End-to-end smoke check (manual, network)

A non-unit sanity run to confirm the hardened pieces work against a live, permissive endpoint. Not part of the automated suite.

**Files:**
- Create: `smoke_facade.py` (repo root)

- [ ] **Step 1: Create `smoke_facade.py`**

```python
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
```

- [ ] **Step 2: Run it**

Run: `python smoke_facade.py`
Expected: two `progress` lines and two `ok` rows with a `heading` value (httpbin's `<h1>Herman Melville - Moby-Dick</h1>`, example.com's `<h1>Example Domain</h1>`).

- [ ] **Step 3: Commit**

```bash
git add smoke_facade.py
git commit -m "chore: add facade smoke script"
```

---

## Self-Review

**Spec coverage (spec §7 — scraper hardening):**
- patchright + persistent context + timezone/locale, drop JS evasion → Task 4 ✓
- reuse curl_cffi session → Task 2 ✓
- rotate proxy/UA on block → Task 3 ✓
- tighten `check_bot_challenges` → Task 1 ✓
- generalize parser (auto + custom) → Task 5 ✓
- wire RateLimiter + concurrency Semaphore → Task 6 ✓
- keep existing tests working → Task 0 scopes pytest to `tests/`, Task 1 keeps a backward-compatible signature ✓
- CAPTCHA solving stays out; opt-in hook only → not implemented (correct for this phase) ✓
- Move scraper to `packages/scraper` → deferred to Phase 2 (backend scaffolding), noted in spec §12; Phase 1 hardens in `src/` to avoid import churn while the app skeleton doesn't exist yet.

**Type consistency:** `ScraperResponse(status_code, text, url, headers, cookies, success, error_message)` is used consistently; `check_bot_challenges(html, url, status_code, headers)` matches all call sites; `parse_custom` returns `{"url", "data"}`, consumed by `Scraper._parse`; `ScrapeConfig` field names (`urls/mode/fields/concurrency/rate_per_minute/use_browser_fallback`) match the test and facade.

**Placeholder scan:** no TBD/TODO; every code step shows complete code.
