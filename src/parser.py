import json
import logging
import re
from typing import Dict, Any, Optional, List
from bs4 import BeautifulSoup
from selectolax.parser import HTMLParser

logger = logging.getLogger("UltimateScraper.Parser")

class ProductParser:
    """Parses raw HTML to extract structured e-commerce product schema information."""
    
    @staticmethod
    def clean_text(text: Optional[str]) -> Optional[str]:
        """Cleans whitespaces and newline characters from string."""
        if not text:
            return None
        return re.sub(r"\s+", " ", text).strip()

    @staticmethod
    def extract_price(price_str: Optional[str]) -> Optional[float]:
        """Extracts numerical price value from text string."""
        if not price_str:
            return None
        
        # Remove currency symbols and common delimiters
        price_str = price_str.replace(",", "")
        match = re.search(r"(\d+(?:\.\d+)?)", price_str)
        if match:
            try:
                return float(match.group(1))
            except ValueError:
                return None
        return None

    def parse(self, html: str, url: str) -> Dict[str, Any]:
        """Runs parsers in priority: 1. JSON-LD Schema -> 2. Meta Tags -> 3. Standard Selectors."""
        if not html:
            return self._empty_result(url)
            
        tree = HTMLParser(html)
        soup = BeautifulSoup(html, "html.parser")
        
        # Check if the page is a search/browse list page that we can parse as a grid of items
        grid_items = []
        from urllib.parse import urljoin
        
        # 1. Kricar search grid detection
        if "kricar-dz.com" in url.lower() and "search" in url.lower():
            cards = soup.find_all("a", class_=lambda x: x and "card" in x)
            for idx, card in enumerate(cards, 1):
                try:
                    title_node = card.find("h3")
                    title = title_node.text.strip() if title_node else "Unknown"
                    href = card.get("href", "")
                    detail_url = urljoin(url, href) if href else url
                    category_node = card.find("span", class_="badge")
                    category = category_node.text.strip() if category_node else "Citadine"
                    
                    location = "Alger"
                    location_p = card.find("p", class_=lambda x: x and "text-xs" in x and "text-gray-500" in x)
                    if location_p:
                        location = location_p.text.strip()
                        
                    img_node = card.find("img")
                    img_src = img_node.get("src", "") if img_node else ""
                    img_url = urljoin(url, img_src) if img_src else ""
                    
                    specs_container = card.find("div", class_=lambda x: x and "flex" in x and "items-center" in x and "gap-3" in x)
                    seats, transmission, fuel = "5", "Manuelle", "Essence"
                    if specs_container:
                        spans = specs_container.find_all("span")
                        if len(spans) >= 3:
                            seats = spans[0].text.strip()
                            transmission = spans[1].text.strip()
                            fuel = spans[2].text.strip()
                            
                    price_node = card.find("span", class_=lambda x: x and "font-display" in x and "text-xl" in x)
                    price_val = 0.0
                    if price_node:
                        try:
                            price_val = float(price_node.text.strip().replace(",", ""))
                        except Exception:
                            pass
                            
                    grid_items.append({
                        "url": detail_url,
                        "title": title,
                        "sku": href.split("/")[-1] if "/" in href else href,
                        "price": price_val,
                        "currency": "DZD",
                        "brand": title.split(" ")[0],
                        "description": f"Car Rental: {title} in {location} ({transmission}, {fuel})",
                        "image_url": img_url,
                        "in_stock": True,
                        "specifications": {
                            "Category": category,
                            "Location": location,
                            "Seats": seats,
                            "Transmission": transmission,
                            "Fuel": fuel,
                            "Price Unit": "DA/jour"
                        }
                    })
                except Exception:
                    pass
                    
        # 2. Amazon browse grid detection
        elif "amazon.fr" in url.lower() and (soup.find(attrs={"data-cy": "asin-faceout-container"}) or "node=" in url.lower()):
            cards = soup.find_all(attrs={"data-cy": "asin-faceout-container"})
            for idx, card in enumerate(cards, 1):
                try:
                    title_node = card.find("h2")
                    title = title_node.text.strip() if title_node else "Unknown Product"
                    link_node = card.find("a", class_=lambda c: c and "a-link-normal" in c)
                    href = link_node.get("href", "") if link_node else ""
                    detail_url = urljoin("https://www.amazon.fr/", href) if href else url
                    img_node = card.find("img", class_="s-image")
                    img_url = img_node.get("src", "") if img_node else ""
                    
                    price_node = card.find("span", class_="a-offscreen")
                    price_text = price_node.text.strip() if price_node else "0"
                    clean_price = price_text.replace("€", "").replace(" ", "").replace(",", ".").strip()
                    price_val = 0.0
                    try:
                        price_val = float(clean_price)
                    except Exception:
                        pass
                        
                    rating_node = card.find("span", class_="a-icon-alt")
                    rating = rating_node.text.strip() if rating_node else "No rating"
                    
                    asin = ""
                    if "/dp/" in href:
                        parts = href.split("/dp/")
                        if len(parts) > 1:
                            asin = parts[1].split("/")[0]
                            
                    grid_items.append({
                        "url": detail_url,
                        "title": title,
                        "sku": asin if asin else f"AMZN-{idx}",
                        "price": price_val,
                        "currency": "EUR",
                        "brand": "Amazon",
                        "description": f"Amazon Product: {title} | Rating: {rating}",
                        "image_url": img_url,
                        "in_stock": True,
                        "specifications": {
                            "Rating": rating,
                            "Price Visual": price_text,
                            "ASIN": asin
                        }
                    })
                except Exception:
                    pass

        if grid_items:
            # If we found grid items, return them in the custom structure!
            return {
                "url": url,
                "title": self.clean_text(soup.title.text if soup.title else "Scraped Grid Page"),
                "sku": "GRID",
                "price": None,
                "currency": "USD",
                "brand": "Grid",
                "description": f"Auto-detected search/browse grid page. Extracted {len(grid_items)} items.",
                "image_url": None,
                "in_stock": True,
                "specifications": {"Total Scraped Items": len(grid_items)},
                "items": grid_items
            }
        
        # Attempt extracting JSON-LD first
        data = self._parse_json_ld(soup)
        
        # Fallback to Meta and Selectors if fields are missing
        meta_data = self._parse_meta(tree)
        selector_data = self._parse_selectors(tree, url)
        
        # Merge priorities
        result = {
            "url": url,
            "title": data.get("title") or meta_data.get("title") or selector_data.get("title"),
            "sku": data.get("sku") or selector_data.get("sku") or meta_data.get("sku"),
            "price": data.get("price") if data.get("price") is not None else (
                meta_data.get("price") if meta_data.get("price") is not None else selector_data.get("price")
            ),
            "currency": data.get("currency") or meta_data.get("currency") or selector_data.get("currency") or "USD",
            "brand": data.get("brand") or meta_data.get("brand") or selector_data.get("brand"),
            "description": data.get("description") or meta_data.get("description") or selector_data.get("description"),
            "image_url": data.get("image_url") or meta_data.get("image_url") or selector_data.get("image_url"),
            "in_stock": data.get("in_stock") if data.get("in_stock") is not None else (
                meta_data.get("in_stock") if meta_data.get("in_stock") is not None else selector_data.get("in_stock")
            ),
            "specifications": selector_data.get("specifications", {})
        }
        
        # Post-process for Ouedkniss listing details
        if "ouedkniss.com" in url.lower():
            # 1. Title fallback from h1.text-h5 (Arabic announcement title)
            h1_title = soup.find("h1", class_=lambda c: c and "text-h5" in c)
            if h1_title:
                result["title"] = self.clean_text(h1_title.get_text())
                
            # 2. Extract Ouedkniss dynamic specification grid
            specs = {}
            specs_card = soup.find("div", class_="o-announ-specs")
            if specs_card:
                for name_node in specs_card.find_all(class_="spec-name"):
                    key = self.clean_text(name_node.get_text())
                    val_node = name_node.find_next_sibling("div")
                    if val_node:
                        val = self.clean_text(val_node.get_text())
                        if key and val:
                            specs[key] = val
                            
            # 3. Extract visual price (e.g. 900مليون)
            price_div = soup.find("div", class_=lambda c: c and "text-primary" in c and "text-h6" in c)
            if price_div:
                specs["السعر المعروض"] = self.clean_text(price_div.get_text())
                
            # 4. Extract phone numbers from tel links
            phones = []
            for a in soup.find_all("a", href=lambda h: h and h.startswith("tel:")):
                num = a.text.strip() or a["href"].replace("tel:", "").strip()
                if num and num not in phones:
                    phones.append(num)
            if phones:
                specs["الهاتف"] = ", ".join(phones)
                # Append phones to description for visibility
                if result.get("description"):
                    result["description"] = f"{result['description']} | Téléphones: {', '.join(phones)}"
                else:
                    result["description"] = f"Téléphones: {', '.join(phones)}"
                    
            result["specifications"] = specs

        return result

    def parse_custom(self, html: str, url: str, fields: Dict[str, Dict[str, str]]) -> Dict[str, Any]:
        """
        Extract user-defined fields. `fields` maps a field name to
        {"selector": <css>, "attr": <optional attribute>}. When "attr" is set,
        the attribute value is returned (URLs resolved absolute); otherwise the
        element's text is returned. Missing selectors yield None.
        """
        from urllib.parse import urljoin
        tree = HTMLParser(html or "")
        data: Dict[str, Any] = {}
        for name, spec in (fields or {}).items():
            selector = spec.get("selector")
            attr = spec.get("attr")
            value = None
            if selector:
                node = tree.css_first(selector)
                if node is not None:
                    if attr:
                        raw = node.attributes.get(attr)
                        if raw and attr in ("href", "src") and url:
                            raw = urljoin(url, raw)
                        value = raw
                    else:
                        value = self.clean_text(node.text())
            data[name] = value
        return {"url": url, "data": data}

    def _parse_json_ld(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Extracts Product Schema objects from script tags."""
        result = {}
        for script in soup.find_all("script", type="application/ld+json"):
            if not script.string:
                continue
            try:
                schema = json.loads(script.string)
                # JSON-LD can be list or single object
                objects = schema if isinstance(schema, list) else [schema]
                for obj in objects:
                    if not isinstance(obj, dict):
                        continue
                    
                    # Resolve @graph lists if present
                    graph_objs = obj.get("@graph", [])
                    candidates = [obj] + (graph_objs if isinstance(graph_objs, list) else [])
                    
                    for candidate in candidates:
                        if candidate.get("@type") == "Product":
                            return self._map_schema_product(candidate)
            except Exception as e:
                logger.debug(f"Failed parsing JSON-LD script block: {e}")
        return result

    def _map_schema_product(self, product_schema: Dict[str, Any]) -> Dict[str, Any]:
        """Maps standard Schema.org Product attributes to internal dictionary."""
        offers = product_schema.get("offers", {})
        if isinstance(offers, list) and len(offers) > 0:
            offers = offers[0]
            
        brand = product_schema.get("brand")
        brand_name = brand.get("name") if isinstance(brand, dict) else brand
        
        price = offers.get("price")
        if price:
            price = self.extract_price(str(price))
            
        availability = offers.get("availability")
        in_stock = None
        if availability:
            in_stock = "InStock" in str(availability) or "InStoreOnly" in str(availability)

        image = product_schema.get("image")
        image_url = None
        if image:
            if isinstance(image, list):
                image_url = image[0]
            elif isinstance(image, dict):
                image_url = image.get("contentUrl") or image.get("url")
            else:
                image_url = image

        return {
            "title": self.clean_text(product_schema.get("name")),
            "sku": self.clean_text(str(product_schema.get("sku") or product_schema.get("mpn") or "")),
            "price": price,
            "currency": offers.get("priceCurrency"),
            "brand": self.clean_text(brand_name),
            "description": self.clean_text(product_schema.get("description")),
            "image_url": image_url,
            "in_stock": in_stock
        }

    def _parse_meta(self, tree: HTMLParser) -> Dict[str, Any]:
        """Parses OpenGraph and properties tag information."""
        result = {}
        
        # Helper to extract content
        def get_meta(property_name: str) -> Optional[str]:
            for selector in [f"meta[property='{property_name}']", f"meta[name='{property_name}']"]:
                node = tree.css_first(selector)
                if node:
                    return node.attributes.get("content")
            return None

        title = get_meta("og:title") or get_meta("twitter:title")
        description = get_meta("og:description") or get_meta("description")
        image = get_meta("og:image") or get_meta("twitter:image")
        
        price = get_meta("product:price:amount") or get_meta("og:price:amount")
        currency = get_meta("product:price:currency") or get_meta("og:price:standard_amount")
        
        availability = get_meta("product:availability") or get_meta("og:availability")
        in_stock = None
        if availability:
            in_stock = availability.lower() in ["instock", "in stock", "available", "true"]

        sku = get_meta("product:retailer_item_id") or get_meta("product:upc") or get_meta("product:mfr_part_no")

        result["title"] = self.clean_text(title)
        result["description"] = self.clean_text(description)
        result["image_url"] = image
        result["price"] = self.extract_price(price)
        result["currency"] = currency
        result["in_stock"] = in_stock
        result["sku"] = self.clean_text(sku)
        
        return result

    def _parse_selectors(self, tree: HTMLParser, url: Optional[str] = None) -> Dict[str, Any]:
        """Runs generic DOM query fallback logic for title, price, descriptions, and images."""
        result = {}
        
        # 1. Product title matching common patterns
        title_node = tree.css_first("h1.product-title") or tree.css_first("h1.product-name") or tree.css_first("h1")
        result["title"] = self.clean_text(title_node.text()) if title_node else None
        
        # 2. SKU / Model matching (including table fallbacks)
        sku = None
        sku_node = tree.css_first(".sku") or tree.css_first("[itemprop='sku']") or tree.css_first(".product-sku")
        if sku_node:
            sku = self.clean_text(sku_node.text())
            
        # Extract all specification table rows dynamically
        specs = {}
        for row in tree.css("tr"):
            th = row.css_first("th")
            td = row.css_first("td")
            if th and td:
                key = self.clean_text(th.text())
                val = self.clean_text(td.text())
                if key and val:
                    specs[key] = val
                    # Fallback SKU lookup from specs table if not found
                    if not sku and ("upc" in key.lower() or "sku" in key.lower() or "barcode" in key.lower()):
                        sku = val
                        
        result["sku"] = sku
        result["specifications"] = specs
        
        # 3. Price matching
        price_node = (
            tree.css_first(".price") or 
            tree.css_first(".product-price") or 
            tree.css_first("[itemprop='price']") or
            tree.css_first(".current-price") or
            tree.css_first(".price_color") or
            tree.css_first("span[class*='price']")
        )
        if price_node:
            result["price"] = self.extract_price(price_node.text())
        else:
            result["price"] = None
            
        # 4. Brand matching
        brand_node = tree.css_first(".brand") or tree.css_first(".product-brand") or tree.css_first("[itemprop='brand']")
        result["brand"] = self.clean_text(brand_node.text()) if brand_node else None
        
        # 5. Description matching
        desc_node = tree.css_first(".description") or tree.css_first(".product-description") or tree.css_first("#description")
        result["description"] = self.clean_text(desc_node.text()) if desc_node else None
        
        # 6. Image matching (including relative path resolution)
        img_node = (
            tree.css_first("img.product-image") or 
            tree.css_first("img#main-image") or 
            tree.css_first(".thumbnail img") or
            tree.css_first(".item img") or
            tree.css_first(".image_container img") or
            tree.css_first("div.carousel-inner img")
        )
        img_url = img_node.attributes.get("src") if img_node else None
        if img_url and url:
            from urllib.parse import urljoin
            img_url = urljoin(url, img_url)
        result["image_url"] = img_url
        
        # 7. Stock status
        stock_text = ""
        stock_node = tree.css_first(".stock-status") or tree.css_first(".availability") or tree.css_first(".instock")
        if stock_node:
            stock_text = stock_node.text().lower()
        
        if stock_text:
            result["in_stock"] = "out of stock" not in stock_text and "sold out" not in stock_text
        else:
            result["in_stock"] = None

        return result

    def _empty_result(self, url: str) -> Dict[str, Any]:
        return {
            "url": url, "title": None, "sku": None, "price": None,
            "currency": None, "brand": None, "description": None,
            "image_url": None, "in_stock": None, "specifications": {}
        }
