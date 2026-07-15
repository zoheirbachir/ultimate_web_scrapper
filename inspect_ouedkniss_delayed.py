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
        
        url = "https://www.ouedkniss.com/شقة-بيع-3-غرف-الجزائر-الرغاية-d54315824"
        print(f"Navigating to {url}...")
        await page.goto(url, wait_until="domcontentloaded")
        
        print("Waiting 6 seconds for client-side Vue/GraphQL to fetch listing details...")
        await page.wait_for_timeout(6000)
        
        content = await page.content()
        soup = BeautifulSoup(content, "html.parser")
        
        # Save HTML
        with open("ouedkniss_loaded_delayed.html", "w", encoding="utf-8") as f:
            f.write(content)
            
        print("\n=== PAGE TEXT CONTENT ===")
        text_content = soup.get_text(separator="\n", strip=True)
        print(text_content[:2500])
        
        print("\n=== SPECIFIC SELECTORS ===")
        h1s = soup.find_all("h1")
        for idx, h1 in enumerate(h1s, 1):
            print(f"H1 [{idx}]: {h1.text.strip()}")
            
        # Look for price
        prices = soup.find_all(string=lambda t: t and ("مليار" in t or "DA" in t or "دج" in t))
        print(f"\nFound potential price labels ({len(prices)}):")
        for p in prices[:15]:
            print(f"  - {p.strip()}")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
