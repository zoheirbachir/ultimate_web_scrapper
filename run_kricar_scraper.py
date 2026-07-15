import asyncio
import sys
import os
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from src.scraper import BrowserClient
from src.storage import SQLiteStorage, FileExporter
from src.parser import ProductParser

sys.stdout.reconfigure(encoding='utf-8')

async def scrape_kricar():
    print("==================================================")
    print("   DzKricar Car Rental Scraper (Real Site Test)   ")
    print("==================================================")
    
    # 1. Initialize DB and clients
    db = SQLiteStorage("kricar_cars.db")
    
    # Using Browser Client since kricar-dz is an SPA that loads listings via client-side API
    client = BrowserClient(headless=True)
    url = "https://kricar-dz.com/search"
    
    try:
        await client.start()
        print(f"Navigating to: {url}...")
        
        # Open page
        page = await client.context.new_page()
        response = await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        
        print("Page loaded. Waiting 6 seconds for API requests to resolve and render car listings...")
        await page.wait_for_timeout(6000)
        
        content = await page.content()
        
        print("Parsing HTML content...")
        soup = BeautifulSoup(content, "html.parser")
        
        # Find all listing cards (a tags with class containing 'card')
        cards = soup.find_all("a", class_=lambda x: x and "card" in x)
        print(f"Found {len(cards)} car listing cards!")
        
        scraped_cars = []
        
        for idx, card in enumerate(cards, 1):
            try:
                # 1. Title / Model name
                title_node = card.find("h3")
                title = title_node.text.strip() if title_node else "Unknown"
                
                # 2. Detail Link
                href = card.get("href", "")
                detail_url = urljoin(url, href) if href else url
                
                # 3. Category badge
                category_node = card.find("span", class_="badge")
                category = category_node.text.strip() if category_node else "Citadine"
                
                # 4. Location (Wilaya)
                location = "Alger"
                location_p = card.find("p", class_=lambda x: x and "text-xs" in x and "text-gray-500" in x)
                if location_p:
                    location = location_p.text.strip()
                
                # 5. Image URL
                img_node = card.find("img")
                img_src = img_node.get("src", "") if img_node else ""
                img_url = urljoin(url, img_src) if img_src else ""
                
                # 6. Specs (Seats, Transmission, Fuel)
                specs_container = card.find("div", class_=lambda x: x and "flex" in x and "items-center" in x and "gap-3" in x)
                seats = "5"
                transmission = "Manuelle"
                fuel = "Essence"
                
                if specs_container:
                    spans = specs_container.find_all("span")
                    if len(spans) >= 3:
                        seats = spans[0].text.strip()
                        transmission = spans[1].text.strip()
                        fuel = spans[2].text.strip()
                
                # 7. Price
                price_node = card.find("span", class_=lambda x: x and "font-display" in x and "text-xl" in x)
                price_val = 0.0
                if price_node:
                    price_text = price_node.text.strip().replace(",", "")
                    try:
                        price_val = float(price_text)
                    except ValueError:
                        pass
                
                # Save specifications dictionary
                car_specs = {
                    "Category": category,
                    "Location": location,
                    "Seats": seats,
                    "Transmission": transmission,
                    "Fuel": fuel,
                    "Price Unit": "DA/jour"
                }
                
                car_data = {
                    "url": detail_url,
                    "title": title,
                    "sku": href.split("/")[-1] if "/" in href else href,
                    "price": price_val,
                    "currency": "DZD",
                    "brand": title.split(" ")[0] if " " in title else title,
                    "description": f"Car Rental: {title} in {location} ({transmission}, {fuel})",
                    "image_url": img_url,
                    "in_stock": True,
                    "specifications": car_specs
                }
                
                scraped_cars.append(car_data)
                
                print(f"[{idx}] Scraped: {title} - {price_val} DA/day (Location: {location}, Gearbox: {transmission})")
                
                # Insert into DB
                db.insert_product(car_data)
                
            except Exception as e:
                print(f"Error parsing card {idx}: {e}")
                
        print(f"\nSuccessfully stored {len(scraped_cars)} cars inside database!")
        
        # Export file outputs
        FileExporter.save_json(scraped_cars, "exports/kricar_cars.json")
        FileExporter.save_csv(scraped_cars, "exports/kricar_cars.csv")
        
    finally:
        await client.stop()

if __name__ == "__main__":
    asyncio.run(scrape_kricar())
