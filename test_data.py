import os
import shutil
from src.parser import ProductParser
from src.storage import FileExporter, SQLiteStorage

MOCK_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Mock Product Page</title>
    <!-- JSON-LD Product Schema -->
    <script type="application/ld+json">
    {
      "@context": "https://schema.org/",
      "@type": "Product",
      "name": "Sony WH-1000XM4 Wireless Headphones",
      "image": [
        "https://example.com/photos/1x1/photo.jpg"
      ],
      "description": "Sony industry leading noise canceling headphones.",
      "sku": "SONY-WH1000XM4-B",
      "brand": {
        "@type": "Brand",
        "name": "Sony"
      },
      "offers": {
        "@type": "Offer",
        "priceCurrency": "USD",
        "price": "298.00",
        "availability": "https://schema.org/InStock"
      }
    }
    </script>
    <!-- Meta tag overrides (e.g. if something else is here) -->
    <meta property="og:title" content="Sony WH-1000XM4 Headphones Black" />
    <meta name="product:retailer_item_id" content="123456789" />
</head>
<body>
    <h1 class="product-title">Sony WH-1000XM4 Noise Canceling Headphones</h1>
    <div class="product-sku">SKU: SONY-M4-BLACK</div>
    <span class="price">$349.99</span>
    <div class="brand">Sony Audio</div>
</body>
</html>
"""

def test_parser():
    print("--- Testing Product Parser ---")
    parser = ProductParser()
    url = "https://mockstore.com/sony-wh1000xm4"
    
    data = parser.parse(MOCK_HTML, url)
    print("Parsed Data Result:")
    print(data)
    
    # Assertions favoring JSON-LD schema parsing definitions
    assert data["title"] == "Sony WH-1000XM4 Wireless Headphones"
    assert data["sku"] == "SONY-WH1000XM4-B"
    assert data["price"] == 298.0
    assert data["currency"] == "USD"
    assert data["brand"] == "Sony"
    assert data["in_stock"] is True
    assert data["image_url"] == "https://example.com/photos/1x1/photo.jpg"
    
    print("Product parsing verification tests PASSED!")
    print()

def test_storage():
    print("--- Testing JSON, CSV, and SQLite Storage Operations ---")
    
    # Prepare clean directory
    output_dir = "test_outputs"
    os.makedirs(output_dir, exist_ok=True)
    
    csv_file = os.path.join(output_dir, "test_products.csv")
    json_file = os.path.join(output_dir, "test_products.json")
    db_file = os.path.join(output_dir, "test_products.db")
    
    # Delete DB if exists
    if os.path.exists(db_file):
        os.remove(db_file)

    # Mock parsed product items list
    items = [
        {
            "url": "https://mockstore.com/sony-wh1000xm4",
            "title": "Sony WH-1000XM4 Wireless Headphones",
            "sku": "SONY-WH1000XM4-B",
            "price": 298.0,
            "currency": "USD",
            "brand": "Sony",
            "description": "Sony industry leading noise canceling headphones.",
            "image_url": "https://example.com/photos/1x1/photo.jpg",
            "in_stock": True
        },
        {
            "url": "https://mockstore.com/bose-qc45",
            "title": "Bose QuietComfort 45 Headphones",
            "sku": "BOSE-QC45-S",
            "price": 329.0,
            "currency": "USD",
            "brand": "Bose",
            "description": "Bose noise canceling comfort headphones.",
            "image_url": "https://example.com/photos/1x1/bose.jpg",
            "in_stock": False
        }
    ]

    # 1. JSON Export
    FileExporter.save_json(items, json_file)
    assert os.path.exists(json_file)
    
    # 2. CSV Export
    FileExporter.save_csv(items, csv_file)
    assert os.path.exists(csv_file)

    # 3. SQLite Storage
    db = SQLiteStorage(db_file)
    
    # Double insert identical items to verify de-duplication URL key integrity
    for item in items:
        db.insert_product(item)
    for item in items:
        db.insert_product(item)
        
    records = db.fetch_all()
    print("Database Stored Records:")
    print(records)
    
    assert len(records) == 2  # No duplicates created
    assert records[0]["price"] == 298.0
    assert records[1]["in_stock"] is False
    
    # Cleanup test outputs
    shutil.rmtree(output_dir)
    print("JSON, CSV, and SQLite storage verification tests PASSED!")
    print()

def main():
    test_parser()
    test_storage()

if __name__ == "__main__":
    main()
