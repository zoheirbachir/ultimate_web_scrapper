import asyncio
import sys
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright
from src import config

sys.stdout.reconfigure(encoding='utf-8')

async def main():
    print("Launching playwright...")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport=config.PLAYWRIGHT_VIEWPORT,
            user_agent=config.DEFAULT_USER_AGENT
        )
        page = await context.new_page()
        
        # Inject stealth evasion script
        from src.stealth import get_evasion_script
        await context.add_init_script(get_evasion_script())
        
        url = "https://www.amazon.fr/-/en/b/?_encoding=UTF8&node=203888434031&language=en_GB"
        print(f"Navigating to {url}...")
        await page.goto(url, wait_until="domcontentloaded")
        
        # Check if cookie consent is present
        print("Checking for cookie consent banner...")
        try:
            accept_button = await page.wait_for_selector("#sp-cc-accept", timeout=3000)
            if accept_button:
                print("Cookie consent banner found! Clicking Accept...")
                await page.click("#sp-cc-accept")
                print("Clicked! Waiting 5 seconds for products to render...")
                await page.wait_for_timeout(5000)
        except Exception:
            print("No cookie consent banner found (or timed out). Waiting anyway...")
            await page.wait_for_timeout(5000)
            
        content = await page.content()
        soup = BeautifulSoup(content, "html.parser")
        
        # Let's count data-cy="asin-faceout-container" elements
        cards = soup.find_all(attrs={"data-cy": "asin-faceout-container"})
        print(f"\nTotal product cards found: {len(cards)}")
        
        # Let's find H2 elements
        h2s = soup.find_all("h2")
        print(f"Total H2 elements: {len(h2s)}")
        for idx, h2 in enumerate(h2s[:15], 1):
            text = h2.text.strip()
            if len(text) > 10:
                print(f"  [{idx}] {text}")
            
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
