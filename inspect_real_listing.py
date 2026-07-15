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
        
        url = "https://kricar-dz.com/search"
        print(f"Navigating to {url}...")
        await page.goto(url, wait_until="domcontentloaded")
        
        print("Waiting 6 seconds for client-side API to load cars...")
        await page.wait_for_timeout(6000)
        
        content = await page.content()
        soup = BeautifulSoup(content, "html.parser")
        
        # Let's save the HTML to see what's loaded
        with open("kricar_loaded_delayed.html", "w", encoding="utf-8") as f:
            f.write(content)
            
        root = soup.find(id="root")
        print("\n=== RENDERED TEXT CONTENT ===")
        print(root.get_text(separator="\n", strip=True)[:3000] if root else "No root found")
        
        # Let's find all links and print their hrefs to see if there are product links
        print("\n=== FOUND LINKS ===")
        links = soup.find_all("a")
        for link in links:
            href = link.get("href", "")
            text = link.get_text(strip=True)
            if href and ("/car/" in href or "/vehicle/" in href or "details" in href or "/rent/" in href):
                print(f"Link: {text} -> {href}")
                
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
