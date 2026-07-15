import logging
import random
import re
from typing import List, Optional, Dict, Any
from curl_cffi.requests import AsyncSession

logger = logging.getLogger("UltimateScraper.Proxies")

def normalize_proxy(proxy_str: str) -> Optional[str]:
    """
    Normalizes different proxy formats into standard URI format:
    - protocol://user:pass@host:port
    - protocol://host:port
    
    Supported formats:
    - host:port
    - host:port:user:pass
    - user:pass@host:port
    - protocol://host:port
    - protocol://user:pass@host:port
    """
    if not proxy_str:
        return None
        
    proxy_str = proxy_str.strip()
    
    # Check if protocol already exists
    protocol = "http"
    if "://" in proxy_str:
        parts = proxy_str.split("://", 1)
        protocol = parts[0].lower()
        proxy_str = parts[1]
        
    # Match host:port:user:pass (common vendor format)
    match_four = re.match(r"^([^:]+):(\d+):([^:]+):([^:]+)$", proxy_str)
    if match_four:
        host, port, user, password = match_four.groups()
        return f"{protocol}://{user}:{password}@{host}:{port}"
        
    # Match user:pass@host:port
    match_user_pass = re.match(r"^([^:]+):([^@]+)@([^:]+):(\d+)$", proxy_str)
    if match_user_pass:
        user, password, host, port = match_user_pass.groups()
        return f"{protocol}://{user}:{password}@{host}:{port}"
        
    # Match host:port
    match_two = re.match(r"^([^:]+):(\d+)$", proxy_str)
    if match_two:
        host, port = match_two.groups()
        return f"{protocol}://{host}:{port}"
        
    # Fallback return if it seems already correct
    return f"{protocol}://{proxy_str}"


class ProxyRotator:
    """Manages proxy lists, checks health status, and handles rotation strategies."""
    def __init__(self, proxy_list: List[str], strategy: str = "random", max_failures: int = 3):
        self.raw_proxies = proxy_list
        self.strategy = strategy.lower()
        self.max_failures = max_failures
        
        # Normalize and filter out invalid proxies
        self.proxies = [normalized for p in proxy_list if (normalized := normalize_proxy(p))]
        
        # Stats tracking: {proxy_url: failure_count}
        self.failures: Dict[str, int] = {p: 0 for p in self.proxies}
        self.index = 0
        
        logger.info(f"Loaded {len(self.proxies)} normalized proxies for rotation (Strategy: {self.strategy})")

    def get_proxy(self) -> Optional[str]:
        """Returns the next healthy proxy based on the rotation strategy."""
        # Filter proxies that haven't exceeded max failure threshold
        active_proxies = [p for p in self.proxies if self.failures.get(p, 0) < self.max_failures]
        
        if not active_proxies:
            logger.warning("No healthy proxies remaining in the rotation pool!")
            return None
            
        if self.strategy == "random":
            return random.choice(active_proxies)
        else:  # Round robin
            self.index = (self.index + 1) % len(active_proxies)
            return active_proxies[self.index]

    def mark_failed(self, proxy: str):
        """Increments the failure counter for a proxy. Deactivates if over limit."""
        normalized = normalize_proxy(proxy)
        if normalized in self.failures:
            self.failures[normalized] += 1
            fail_count = self.failures[normalized]
            logger.warning(f"Proxy failed: {proxy} (Failure count: {fail_count}/{self.max_failures})")
            if fail_count >= self.max_failures:
                logger.error(f"Proxy deactivated: {proxy}")

    def mark_success(self, proxy: str):
        """Resets the failure counter on successful request."""
        normalized = normalize_proxy(proxy)
        if normalized in self.failures:
            self.failures[normalized] = 0

    @staticmethod
    async def validate_proxy(proxy_url: str, test_url: str = "https://httpbin.org/ip", timeout: float = 10.0) -> Dict[str, Any]:
        """
        Asynchronously validates proxy connection speed and verified IP address.
        """
        normalized = normalize_proxy(proxy_url)
        if not normalized:
            return {"valid": False, "error": "Invalid proxy format", "latency": -1, "ip": None}
            
        import time
        start_time = time.time()
        
        try:
            # We use curl_cffi for proxy validation (highly accurate and fast)
            async with AsyncSession(impersonate="chrome124") as session:
                proxies = {"http": normalized, "https": normalized}
                response = await session.get(test_url, timeout=timeout, proxies=proxies)
                
                latency = time.time() - start_time
                if response.status_code == 200:
                    try:
                        ip_data = response.json()
                        origin_ip = ip_data.get("origin")
                    except Exception:
                        origin_ip = None
                        
                    return {
                        "valid": True,
                        "error": None,
                        "latency": latency,
                        "ip": origin_ip
                    }
                else:
                    return {
                        "valid": False,
                        "error": f"HTTP status code {response.status_code}",
                        "latency": latency,
                        "ip": None
                    }
        except Exception as e:
            return {
                "valid": False,
                "error": str(e),
                "latency": time.time() - start_time,
                "ip": None
            }

def parse_to_playwright(proxy_str: str) -> Optional[Dict[str, str]]:
    """Converts a normalized proxy URI into a Playwright proxy configuration dictionary."""
    normalized = normalize_proxy(proxy_str)
    if not normalized:
        return None
        
    match = re.match(r"^([^:]+)://(?:([^:]+):([^@]+)@)?([^:]+):(\d+)$", normalized)
    if match:
        protocol, user, password, host, port = match.groups()
        result = {
            "server": f"{protocol}://{host}:{port}"
        }
        if user and password:
            result["username"] = user
            result["password"] = password
        return result
    return None
