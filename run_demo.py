import asyncio
import os
from src.scraper import TLSClient, BrowserClient
from src.parser import ProductParser
from src.storage import SQLiteStorage, FileExporter

async def run_tls_demo(parser: ProductParser, db: SQLiteStorage):
    print("=== DEMO 1: TLS Client (Fast Request Mode) ===")
    client = TLSClient()
    
    # We will scrap a page from books.toscrape.com (a safe sandbox scraping target)
    target_url = "http://books.toscrape.com/catalogue/a-light-in-the-attic_1000/index.html"
    
    print(f"Requesting target: {target_url}")
    response = await client.fetch(target_url)
    
    if response.success:
        print("Page fetched successfully! Parsing content...")
        # Parse the page
        product = parser.parse(response.text, target_url)
        
        print("\nParsed Data:")
        for key, val in product.items():
            if key == "specifications":
                print("  specifications:")
                for sk, sv in val.items():
                    print(f"    {sk}: {sv}")
            else:
                print(f"  {key}: {val}")
            
        # Store in DB
        db.insert_product(product)
    else:
        print(f"Fetch failed! Error: {response.error_message}")
    print()

async def run_browser_demo(parser: ProductParser, db: SQLiteStorage):
    print("=== DEMO 2: Browser Client (Human Emulation Mode) ===")
    client = BrowserClient(headless=True)
    
    target_url = "http://books.toscrape.com/catalogue/tipping-the-velvet_999/index.html"
    
    try:
        await client.start()
        print(f"Navigating to target: {target_url}")
        response = await client.fetch(target_url)
        
        if response.success:
            print("Page loaded successfully! Parsing content...")
            product = parser.parse(response.text, target_url)
            
            print("\nParsed Data:")
            for key, val in product.items():
                if key == "specifications":
                    print("  specifications:")
                    for sk, sv in val.items():
                        print(f"    {sk}: {sv}")
                else:
                    print(f"  {key}: {val}")
                
            # Store in DB
            db.insert_product(product)
        else:
            print(f"Fetch failed! Error: {response.error_message}")
    finally:
        await client.stop()
    print()

async def main():
    parser = ProductParser()
    db = SQLiteStorage("demo_products.db")
    
    # Run both clients
    await run_tls_demo(parser, db)
    await run_browser_demo(parser, db)
    
    # Show the stored results in SQLite
    print("=== SQLite Database Contents ===")
    records = db.fetch_all()
    for record in records:
        print(f"\nProduct: {record['title']}")
        print(f"  URL: {record['url']}")
        print(f"  SKU: {record['sku']}")
        print(f"  Price: {record['price']} {record['currency']}")
        print(f"  In Stock: {record['in_stock']}")
        print(f"  Last Updated: {record['updated_at']}")
        print(f"  specifications:")
        for spec_k, spec_v in record.get("specifications", {}).items():
            print(f"    {spec_k}: {spec_v}")
        
    # Also save to JSON/CSV files as a demo export
    FileExporter.save_json(records, "exports/products.json")
    FileExporter.save_csv(records, "exports/products.csv")

if __name__ == "__main__":
    asyncio.run(main())
