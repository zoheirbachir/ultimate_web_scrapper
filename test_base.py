import asyncio
import sys

# Ensure project root is in python path
from src.scraper import TLSClient, BrowserClient

async def test_tls_scraper():
    print("--- Testing TLS Scraper (curl_cffi) ---")
    client = TLSClient()
    url = "https://httpbin.org/headers"
    response = await client.fetch(url)
    
    if response.success:
        print(f"Success! Status Code: {response.status_code}")
        print("Response Headers:")
        print(response.headers)
        print("Response Body Snippet:")
        print(response.text[:200])
    else:
        print(f"Failed! Error: {response.error_message}")
    print()

async def test_browser_scraper():
    print("--- Testing Browser Scraper (Playwright) ---")
    client = BrowserClient(headless=True)
    try:
        await client.start()
        url = "https://httpbin.org/headers"
        response = await client.fetch(url)
        
        if response.success:
            print(f"Success! Status Code: {response.status_code}")
            print("Response Body Snippet:")
            print(response.text[:200])
        else:
            print(f"Failed! Error: {response.error_message}")
    finally:
        await client.stop()
    print()

async def main():
    await test_tls_scraper()
    await test_browser_scraper()

if __name__ == "__main__":
    asyncio.run(main())
