import asyncio
import sys
import os
from src.scraper import BrowserClient
from src.parser import ProductParser
from src.storage import SQLiteStorage, FileExporter

sys.stdout.reconfigure(encoding='utf-8')

async def scrape_ouedkniss_listing():
    print("=========================================================")
    print("   Ouedkniss Announcement Scraper (Real Site Test)      ")
    print("=========================================================")
    
    # Target URL
    target_url = "https://www.ouedkniss.com/شقة-بيع-3-غرف-الجزائر-الرغاية-d54315824"
    
    # 1. Initialize Clients & DB
    db = SQLiteStorage("ouedkniss_listings.db")
    parser = ProductParser()
    
    # Using BrowserClient to bypass Cloudflare and allow Vue/Nuxt + GraphQL loading
    client = BrowserClient(headless=True)
    
    try:
        await client.start()
        print(f"Navigating to Ouedkniss: {target_url}...")
        
        # Open page context directly
        page = await client.context.new_page()
        await page.goto(target_url, wait_until="domcontentloaded")
        
        print("Waiting 6 seconds for GraphQL API to fetch listing data and populate DOM...")
        await page.wait_for_timeout(6000)
        
        # Grab updated HTML content
        updated_html = await page.content()
        await page.close()
        
        print("Parsing listing data...")
        result = parser.parse(updated_html, target_url)
        
        # Print results
        print("\n=== SCRAPED LISTING DATA ===")
        print(f"  URL: {result['url']}")
        print(f"  Title: {result['title']}")
        print(f"  SKU/ID: {result['sku']}")
        print(f"  Price: {result['price']} {result['currency']}")
        print(f"  Brand/Agency: {result['brand']}")
        print(f"  In Stock: {result['in_stock']}")
        print(f"  Description: {result['description']}")
        print(f"  Image URL: {result['image_url']}")
        print(f"  specifications:")
        for spec_k, spec_v in result.get("specifications", {}).items():
            print(f"    {spec_k}: {spec_v}")
        
        # Save to SQLite
        db.insert_product(result)
        print("\nSaved listing successfully to ouedkniss_listings.db!")
        
        # Export to CSV & JSON (CSV uses UTF-8 with BOM so Excel displays Arabic correctly on Windows)
        FileExporter.save_json([result], "exports/ouedkniss_listings.json")
        FileExporter.save_csv([result], "exports/ouedkniss_listings.csv")
        print("CSV and JSON sheets exported to exports/ folder.")
        
    finally:
        await client.stop()

if __name__ == "__main__":
    asyncio.run(scrape_ouedkniss_listing())
