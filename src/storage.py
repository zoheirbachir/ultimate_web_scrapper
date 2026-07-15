import csv
import json
import sqlite3
import os
import logging
from typing import Dict, Any, List

logger = logging.getLogger("UltimateScraper.Storage")

class FileExporter:
    """Handles exporting e-commerce item schemas to JSON or CSV file types."""
    
    @staticmethod
    def save_json(data: List[Dict[str, Any]], filepath: str):
        """Saves list of dict items into a JSON formatted file."""
        os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            logger.info(f"Successfully exported {len(data)} items to JSON: {filepath}")
        except Exception as e:
            logger.error(f"Failed exporting to JSON: {e}")

    @staticmethod
    def save_csv(data: List[Dict[str, Any]], filepath: str):
        """Saves list of dict items into a CSV formatted file."""
        if not data:
            logger.warning("No data to save to CSV.")
            return
            
        os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
        
        # Get headers from first item keys
        headers = list(data[0].keys())
        try:
            with open(filepath, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.DictWriter(f, fieldnames=headers)
                writer.writeheader()
                writer.writerows(data)
            logger.info(f"Successfully exported {len(data)} items to CSV: {filepath}")
        except Exception as e:
            logger.error(f"Failed exporting to CSV: {e}")


class SQLiteStorage:
    """Manages SQLite database storage for deduplicated e-commerce items."""
    
    def __init__(self, db_path: str = "products.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Creates products table with URL as primary key to prevent duplication."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS products (
                url TEXT PRIMARY KEY,
                title TEXT,
                sku TEXT,
                price REAL,
                currency TEXT,
                brand TEXT,
                description TEXT,
                image_url TEXT,
                in_stock INTEGER,
                specifications TEXT,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Schema migration: Add specifications column dynamically if table exists from previous steps
        try:
            cursor.execute("ALTER TABLE products ADD COLUMN specifications TEXT")
        except sqlite3.OperationalError:
            pass  # Already exists
            
        conn.commit()
        conn.close()

    def insert_product(self, product: Dict[str, Any]):
        """Inserts or replaces product record matching target URL key."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Convert bool to int for SQLite representation
        in_stock_int = None
        if product.get("in_stock") is not None:
            in_stock_int = 1 if product["in_stock"] else 0

        # Serialize specifications dict to JSON string
        specs_json = None
        if "specifications" in product:
            specs_json = json.dumps(product["specifications"], ensure_ascii=False)

        try:
            cursor.execute("""
                INSERT OR REPLACE INTO products (
                    url, title, sku, price, currency, brand, description, image_url, in_stock, specifications, updated_at
                ) VALUES (
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP
                )
            """, (
                product.get("url"),
                product.get("title"),
                product.get("sku"),
                product.get("price"),
                product.get("currency"),
                product.get("brand"),
                product.get("description"),
                product.get("image_url"),
                in_stock_int,
                specs_json
            ))
            conn.commit()
            logger.info(f"Stored item in DB: {product.get('url')}")
        except Exception as e:
            logger.error(f"Failed to insert product record into SQLite: {e}")
        finally:
            conn.close()

    def fetch_all(self) -> List[Dict[str, Any]]:
        """Returns all stored product records as dictionary objects."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Enables access by column name
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM products")
        rows = cursor.fetchall()
        
        result = []
        for row in rows:
            item = dict(row)
            # Convert SQLite int back to bool
            if item.get("in_stock") is not None:
                item["in_stock"] = bool(item["in_stock"])
            # Deserialize JSON string back to specifications dict
            if item.get("specifications") is not None:
                try:
                    item["specifications"] = json.loads(item["specifications"])
                except Exception:
                    item["specifications"] = {}
            else:
                item["specifications"] = {}
            result.append(item)
            
        conn.close()
        return result
