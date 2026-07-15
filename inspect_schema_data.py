import json
import sys

sys.stdout.reconfigure(encoding='utf-8')

with open("id_script_52.js", "r", encoding="utf-8") as f:
    js_content = f.read()

# Load the JSON
try:
    data = json.loads(js_content)
    print("=== SCHEMA GRAPH OBJECTS ===")
    graph = data.get("@graph", [])
    print(f"Total graph objects: {len(graph)}")
    
    for idx, obj in enumerate(graph, 1):
        obj_type = obj.get("@type")
        print(f"[{idx}] Type: {obj_type}")
        
        # Print details of the listing
        if obj_type == "Product" or obj_type == "RealEstateAgent" or obj_type == "SingleFamilyResidence" or "Listing" in str(obj_type) or obj_type == "Accommodation":
            print(json.dumps(obj, indent=2, ensure_ascii=False)[:2000])
        elif obj_type == "BreadcrumbList":
            # Print breadcrumbs to see category path
            print("  Breadcrumbs:")
            for item in obj.get("itemListElement", []):
                print(f"    - {item.get('name')} ({item.get('item')})")
        else:
            # Print first 200 chars of other objects
            print(f"  Snippet: {str(obj)[:200]}...")
            
except Exception as e:
    print("Failed to load JSON:", e)
