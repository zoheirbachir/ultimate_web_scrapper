import os

# Base directory
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ── Scraping defaults ────────────────────────────────────────────────
DEFAULT_TIMEOUT = 30.0          # seconds
MAX_RETRIES = 3
BACKOFF_FACTOR = 2.0            # exponential backoff base (seconds)

# ── TLS impersonation (curl_cffi HTTP fast-path) ─────────────────────
# "chrome" tracks curl_cffi's newest bundled Chrome JA3/JA4 profile.
# Pin to a specific build (e.g. "chrome131") only if you need reproducibility.
DEFAULT_CHROME_VERSION = "chrome"

# Fallback UA for the rare non-impersonated request. On the impersonate path,
# curl_cffi sets the correct UA + Client-Hints itself — do NOT override them.
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/131.0.0.0 Safari/537.36"
)

# Minimal, VALID headers. (Previous version shipped broken "Sec-Chua-*" names.)
# NOTE: when using curl_cffi `impersonate=`, let it own UA / sec-ch-ua / Accept
# ordering. Force-merging stale Client-Hints breaks fingerprint consistency —
# the Step 2 networking layer will stop merging these onto impersonated requests.
DEFAULT_HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br, zstd",
    "sec-ch-ua": '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Windows"',
    "Upgrade-Insecure-Requests": "1",
}

# ── Browser engine (Step 1: patched / undetected driver) ─────────────
BROWSER_ENGINE = "patchright"   # patched Playwright; fixes CDP Runtime.enable leak
BROWSER_CHANNEL = "chrome"      # real Google Chrome. Auto-falls back to "chromium".
USER_DATA_DIR = os.path.join(BASE_DIR, ".userdata")  # persistent profile == more human

# Deliberately empty. patchright handles stealth internally; extra flags such as
# --no-sandbox or --disable-blink-features=AutomationControlled are themselves
# fingerprintable automation tells, so we do NOT pass them.
BROWSER_LAUNCH_ARGS = []

# Headful is materially harder to detect than headless. Set True only for
# unattended/background runs (patchright uses Chrome's new headless mode).
PLAYWRIGHT_HEADLESS = False
PLAYWRIGHT_VIEWPORT = {"width": 1920, "height": 1080}   # used only if no_viewport is disabled
PLAYWRIGHT_LOCALE = "en-US"
# Keep timezone consistent with your proxy's geolocation. Targets ouedkniss/kricar
# are Algerian, so via an Algerian residential proxy "Africa/Algiers" is consistent.
PLAYWRIGHT_TIMEZONE = "Africa/Algiers"
PLAYWRIGHT_COLOR_SCHEME = "light"   # light matches the majority of real users

# Pool of realistic desktop Chrome UAs, rotated on block alongside the proxy.
USER_AGENT_POOL = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
]
