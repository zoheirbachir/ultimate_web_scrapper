import asyncio
import sys
from bs4 import BeautifulSoup
from src.scraper import BrowserClient

sys.stdout.reconfigure(encoding='utf-8')

async def main():
    client = BrowserClient(headless=True)
    try:
        await client.start()
        url = "https://www.amazon.fr/-/en/b/?_encoding=UTF8&node=203888434031&language=en_GB"
        print(f"Navigating to Amazon: {url}...")
        
        page = await client.context.new_page()
        await page.goto(url, wait_until="domcontentloaded")
        await page.wait_for_timeout(6000)
        
        content = await page.content()
        soup = BeautifulSoup(content, "html.parser")
        
        # Save HTML
        with open("amazon_zero_debug.html", "w", encoding="utf-8") as f:
            f.write(content)
            
        print("Page Title:", soup.title.text if soup.title else "None")
        
        # Check if CAPTCHA or Robot check is displayed
        print("Is robot check in text:", "robot check" in content.lower() or "captcha" in content.lower() or "enter the characters" in content.lower())
        
        # Let's count data-cy="asin-faceout-container" elements
        cards = soup.find_all(attrs={"data-cy": "asin-faceout-container"})
        print(f"Total cards found: {len(cards)}")
        
        # Let's find H2 elements
        h2s = soup.find_all("h2")
        print(f"Total H2 elements: {len(h2s)}")
        for idx, h2 in enumerate(h2s[:10], 1):
            print(f"  H2 [{idx}]: {h2.text.strip()}")
            
        await page.close()
    finally:
        await client.stop()

if __name__ == "__main__":
    asyncio.run(main())
