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
        response = await client.fetch(url, timeout=30)
        
        print("Page Success Status:", response.success)
        print("Status Code:", response.status_code)
        print("Error Message:", response.error_message)
        
        with open("amazon_loaded.html", "w", encoding="utf-8") as f:
            f.write(response.text)
        print("HTML written to amazon_loaded.html")
        
        soup = BeautifulSoup(response.text, "html.parser")
        print("\n=== PAGE TEXT CONTENTS SNEAK PEEK ===")
        print(soup.text[:1500])
        
    finally:
        await client.stop()

if __name__ == "__main__":
    asyncio.run(main())
