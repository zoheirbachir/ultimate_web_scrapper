import asyncio
import sys
import os
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from playwright.async_api import async_playwright
from src import config
from src.storage import SQLiteStorage, FileExporter

sys.stdout.reconfigure(encoding='utf-8')

async def scrape_amazon():
    print("==================================================")
    print("   Amazon.fr Browse Node Scraper (Real Site Test)  ")
    print("==================================================")
    
    target_url = "https://www.amazon.fr/-/en/b/?_encoding=UTF8&node=203888434031&language=en_GB"
    
    # Initialize DB
    db = SQLiteStorage("amazon_products.db")
    
    print("Launching playwright...")
    async with async_playwright() as p:
        # Launch browser with anti-bot evasion arguments
        browser = await p.chromium.launch(
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-infobars",
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--window-size=1920,1080",
            ]
        )
        
        # Configure context similarly to our successful test script
        context = await browser.new_context(
            viewport=config.PLAYWRIGHT_VIEWPORT,
            user_agent=config.DEFAULT_USER_AGENT
        )
        
        # Inject stealth evasion script
        from src.stealth import get_evasion_script
        await context.add_init_script(get_evasion_script())
        
        page = await context.new_page()
        
        print(f"Navigating to Amazon: {target_url}...")
        await page.goto(target_url, wait_until="domcontentloaded")
        
        # Accept cookies if the banner shows up
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
            
        # Grab updated HTML content
        content = await page.content()
        await page.close()
        await browser.close()
        
        print("Parsing HTML content...")
        soup = BeautifulSoup(content, "html.parser")
        
        # Find all product card containers
        cards = soup.find_all(attrs={"data-cy": "asin-faceout-container"})
        print(f"Found {len(cards)} product listing cards!")
        
        scraped_products = []
        
        for idx, card in enumerate(cards, 1):
            try:
                # 1. Product Title
                title_node = card.find("h2")
                title = title_node.text.strip() if title_node else "Unknown Product"
                
                # 2. Detail Link
                link_node = card.find("a", class_=lambda c: c and "a-link-normal" in c)
                href = link_node.get("href", "") if link_node else ""
                detail_url = urljoin("https://www.amazon.fr/", href) if href else target_url
                
                # 3. Image URL
                img_node = card.find("img", class_="s-image")
                img_src = img_node.get("src", "") if img_node else ""
                img_url = img_src if img_src else ""
                
                # 4. Price
                price_node = card.find("span", class_="a-offscreen")
                price_text = price_node.text.strip() if price_node else "0"
                # Strip out currency symbols
                clean_price_text = price_text.replace("€", "").replace(" ", "").replace(",", ".").strip()
                price_val = 0.0
                try:
                    price_val = float(clean_price_text)
                except ValueError:
                    pass
                
                # 5. Rating Stars
                rating_node = card.find("span", class_="a-icon-alt")
                rating = rating_node.text.strip() if rating_node else "No rating"
                
                # ASIN extraction from link
                asin = ""
                if "/dp/" in href:
                    parts = href.split("/dp/")
                    if len(parts) > 1:
                        asin = parts[1].split("/")[0]
                
                specs = {
                    "Rating": rating,
                    "Price Visual": price_text,
                    "ASIN": asin
                }
                
                product_data = {
                    "url": detail_url,
                    "title": title,
                    "sku": asin if asin else f"AMZN-{idx}",
                    "price": price_val,
                    "currency": "EUR",
                    "brand": "Amazon",
                    "description": f"Amazon Product: {title} | Rating: {rating}",
                    "image_url": img_url,
                    "in_stock": True,
                    "specifications": specs
                }
                
                scraped_products.append(product_data)
                
                print(f"[{idx}] Scraped: {title[:60]}... -> {price_text} (Rating: {rating})")
                
                # Insert into DB
                db.insert_product(product_data)
                
            except Exception as e:
                print(f"Error parsing card {idx}: {e}")
                
        print(f"\nSuccessfully stored {len(scraped_products)} products inside database!")
        
        # Export file outputs (CSV uses UTF-8 with BOM for proper accents and € sign display)
        if scraped_products:
            FileExporter.save_json(scraped_products, "exports/amazon_products.json")
            FileExporter.save_csv(scraped_products, "exports/amazon_products.csv")
            print("CSV and JSON sheets exported to exports/ folder.")
        
if __name__ == "__main__":
    asyncio.run(scrape_amazon())
