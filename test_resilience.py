import asyncio
import time
from src.utils import calculate_backoff, RateLimiter, check_bot_challenges
from src.scraper import TLSClient, BrowserClient

def test_backoff_calculations():
    print("--- Testing Exponential Backoff + Jitter ---")
    delays = [calculate_backoff(attempt=i, base_delay=2.0) for i in range(4)]
    print(f"Calculated delay increments: {delays}")
    
    # Assert values grow
    assert delays[0] >= 2.0
    assert delays[1] > delays[0]
    assert delays[3] > delays[1]
    
    print("Backoff math validation PASSED!")
    print()

async def test_rate_limiter():
    print("--- Testing Rate Limiter Throttling ---")
    # Limiter set to 120 RPM (one request per 0.5 seconds)
    limiter = RateLimiter(requests_per_minute=120)
    
    start_time = time.time()
    await limiter.wait()
    await limiter.wait()
    await limiter.wait()
    elapsed = time.time() - start_time
    
    print(f"Elapsed time for 3 rate limited calls: {elapsed:.2f}s (Expected: >= 1.0s)")
    assert elapsed >= 0.9  # With CPU scheduling variance allowance
    
    print("Rate limiter throttling validation PASSED!")
    print()

def test_bot_challenge_detection():
    print("--- Testing Bot Challenge Detection Signatures ---")
    
    cf_html = "<html><head><title>Attention Required! | Cloudflare</title></head></html>"
    dd_html = "<html><body><script src='https://captcha.datadome.co/captcha/'></script></body></html>"
    normal_html = "<html><body><h1>Sony WH-1000XM4</h1></body></html>"
    
    cf_res = check_bot_challenges(cf_html, "http://target.com")
    dd_res = check_bot_challenges(dd_html, "http://target.com")
    ok_res = check_bot_challenges(normal_html, "http://target.com")
    
    print(f"Cloudflare match: {cf_res}")
    print(f"DataDome match: {dd_res}")
    print(f"Legitimate page check: {ok_res}")
    
    assert cf_res["blocked"] is True and cf_res["system"] == "Cloudflare"
    assert dd_res["blocked"] is True and dd_res["system"] == "DataDome"
    assert ok_res["blocked"] is False
    
    print("Bot detection signature validation PASSED!")
    print()

async def test_client_error_retrying():
    print("--- Testing Client Retrier on Exception Triggers ---")
    
    # We test retry behavior using a bogus proxy to force request exceptions.
    # It should hit max_retries=3, causing backoff pauses, and log warnings.
    # We will set a small base delay in configuration momentarily to keep tests fast.
    from src import config
    config.MAX_RETRIES = 2
    config.BACKOFF_FACTOR = 0.1  # Fast retries for testing
    
    tls = TLSClient()
    start_time = time.time()
    response = await tls.fetch("https://httpbin.org/ip", proxy="http://127.0.0.1:54321")
    elapsed = time.time() - start_time
    
    print(f"Completed failed requests in {elapsed:.2f}s")
    print(f"Fetch success: {response.success} (Expected: False)")
    
    assert response.success is False
    assert "connect to 127.0.0.1 port 54321" in response.error_message.lower()
    
    print("Client retrier execution validation PASSED!")
    print()

async def main():
    test_backoff_calculations()
    await test_rate_limiter()
    test_bot_challenge_detection()
    await test_client_error_retrying()

if __name__ == "__main__":
    asyncio.run(main())
