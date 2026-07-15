import asyncio
from src.proxies import normalize_proxy, parse_to_playwright, ProxyRotator
from src.scraper import TLSClient, BrowserClient

def test_normalization():
    print("--- Testing Proxy Normalization ---")
    
    # 1. Standard host:port
    assert normalize_proxy("127.0.0.1:8080") == "http://127.0.0.1:8080"
    
    # 2. host:port:user:pass
    assert normalize_proxy("127.0.0.1:8080:username:password") == "http://username:password@127.0.0.1:8080"
    
    # 3. Protocol prepended
    assert normalize_proxy("socks5://127.0.0.1:1080") == "socks5://127.0.0.1:1080"
    assert normalize_proxy("socks5://user:pass@127.0.0.1:1080") == "socks5://user:pass@127.0.0.1:1080"
    
    # 4. User:pass@host:port
    assert normalize_proxy("admin:secret@192.168.1.1:3128") == "http://admin:secret@192.168.1.1:3128"
    
    print("Proxy normalization tests PASSED!")
    print()

def test_playwright_parsing():
    print("--- Testing Playwright Proxy Format Parsing ---")
    
    p1 = parse_to_playwright("127.0.0.1:8080")
    assert p1 == {"server": "http://127.0.0.1:8080"}
    
    p2 = parse_to_playwright("socks5://user:pass@127.0.0.1:1080")
    assert p2 == {
        "server": "socks5://127.0.0.1:1080",
        "username": "user",
        "password": "pass"
    }
    
    print("Playwright proxy parsing tests PASSED!")
    print()

def test_rotator():
    print("--- Testing Proxy Rotator State Machine ---")
    proxies = [
        "1.1.1.1:80",
        "2.2.2.2:80",
        "3.3.3.3:80"
    ]
    
    rotator = ProxyRotator(proxies, strategy="round_robin", max_failures=2)
    
    # Check round robin rotation
    px1 = rotator.get_proxy()
    px2 = rotator.get_proxy()
    px3 = rotator.get_proxy()
    px4 = rotator.get_proxy()
    
    print(f"Rotation sequence: {px1} -> {px2} -> {px3} -> {px4}")
    assert px1 != px2
    assert px1 == px4  # Wraps around
    
    # Test failure marking and deactivation
    rotator.mark_failed(px1)
    rotator.mark_failed(px1)  # Reaches max_failures=2
    
    # px1 should be deactivated, getting proxy should only return the other two
    remaining = [rotator.get_proxy() for _ in range(5)]
    print(f"Remaining active proxies sequence: {remaining}")
    assert px1 not in remaining
    
    print("Proxy rotator state machine tests PASSED!")
    print()

async def test_scraper_proxy_routing():
    print("--- Testing Scraper Routing with Offline Proxy (Evasion Validation) ---")
    
    # We will pass a bogus local proxy. 
    # If the scraper attempts to route traffic through it, it should fail to connect.
    # This confirms the routing logic works. If it succeeds, it means it bypassed the proxy, which is a failure.
    bogus_proxy = "http://127.0.0.1:54321"  # No service running on this port
    
    # 1. Test TLS Scraper
    tls_client = TLSClient()
    response = await tls_client.fetch("https://httpbin.org/ip", proxy=bogus_proxy, timeout=5)
    
    print(f"TLS Scraper status code: {response.status_code} (Expected: 0 due to connection failure)")
    print(f"TLS Scraper success: {response.success} (Expected: False)")
    print(f"TLS Scraper error message: {response.error_message}")
    
    assert not response.success, "TLS Scraper did not use the proxy (it bypassed it)!"
    
    # 2. Test Browser Scraper
    browser_client = BrowserClient(headless=True, proxy=bogus_proxy)
    try:
        await browser_client.start()
        response = await browser_client.fetch("https://httpbin.org/ip", timeout=5)
        print(f"Browser Scraper status code: {response.status_code} (Expected: 0 due to proxy connection failure)")
        print(f"Browser Scraper success: {response.success} (Expected: False)")
        print(f"Browser Scraper error: {response.error_message}")
        
        assert not response.success, "Browser Scraper did not use the proxy (it bypassed it)!"
        
    finally:
        await browser_client.stop()
        
    print("Scraper proxy routing validation PASSED!")
    print()

async def main():
    test_normalization()
    test_playwright_parsing()
    test_rotator()
    await test_scraper_proxy_routing()

if __name__ == "__main__":
    asyncio.run(main())
