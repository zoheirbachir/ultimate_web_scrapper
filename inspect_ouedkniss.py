import asyncio
import sys
from bs4 import BeautifulSoup
from src.scraper import BrowserClient

sys.stdout.reconfigure(encoding='utf-8')

async def main():
    client = BrowserClient(headless=True)
    try:
        await client.start()
        url = "https://www.ouedkniss.com/شقة-بيع-3-غرف-الجزائر-الرغاية-d54315824"
        print(f"Navigating to {url}...")
        response = await client.fetch(url, timeout=30)
        
        print("Page Success Status:", response.success)
        print("Final Page URL:", response.url)
        print("Status Code:", response.status_code)
        print("Error Message:", response.error_message)
        
        if response.success:
            with open("ouedkniss_loaded.html", "w", encoding="utf-8") as f:
                f.write(response.text)
            print("Loaded HTML dumped to ouedkniss_loaded.html")
            
            soup = BeautifulSoup(response.text, "html.parser")
            print("\n=== PAGE TEXT CONTENT PREVIEW ===")
            # Let's print out the body text snippet
            print(soup.body.get_text(separator="\n", strip=True)[:2500] if soup.body else "No body element")
            
    finally:
        await client.stop()

if __name__ == "__main__":
    asyncio.run(main())
