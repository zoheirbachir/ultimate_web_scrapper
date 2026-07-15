import asyncio
from src.scraper import BrowserClient

async def inspect():
    # Run Playwright browser client
    client = BrowserClient(headless=True)
    try:
        await client.start()
        url = "https://kricar-dz.com/search"
        response = await client.fetch(url, wait_until="networkidle", timeout=20)
        
        print("Page Success Status:", response.success)
        print("Final Page URL:", response.url)
        
        # Let's save the loaded HTML to a file so we can analyze it
        with open("kricar_loaded.html", "w", encoding="utf-8") as f:
            f.write(response.text)
            
        print("Loaded HTML dumped to kricar_loaded.html")
        
        # Let's do a simple check on the HTML contents using beautifulsoup
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(response.text, "html.parser")
        
        # Let's print out some elements to see the DOM structure
        print("Checking key element counts:")
        print("  - Total 'a' links:", len(soup.find_all("a")))
        print("  - Total 'img' tags:", len(soup.find_all("img")))
        print("  - Total 'button' tags:", len(soup.find_all("button")))
        
        # Let's look for common card indicators, e.g. class names that might contain 'car', 'card', 'item', 'product'
        classes = set()
        for tag in soup.find_all(True):
            if tag.get("class"):
                for c in tag.get("class"):
                    if any(term in c.lower() for term in ["car", "card", "item", "product", "listing", "vehicle"]):
                        classes.add(c)
        print("Found related classes:", list(classes)[:20])
        
    finally:
        await client.stop()

if __name__ == "__main__":
    asyncio.run(inspect())
