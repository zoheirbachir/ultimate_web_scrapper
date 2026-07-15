import sys
from bs4 import BeautifulSoup

sys.stdout.reconfigure(encoding='utf-8')

with open("amazon_loaded.html", "r", encoding="utf-8") as f:
    html = f.read()

soup = BeautifulSoup(html, "html.parser")

print("=== CHECKING AMAZON GRID AND ITEMS ===")

# Look for search results
search_items = soup.find_all("div", attrs={"data-component-type": "s-search-result"})
print(f"Total data-component-type='s-search-result' elements: {len(search_items)}")

# Look for result-item classes
result_items = soup.find_all(class_=lambda c: c and "s-result-item" in c)
print(f"Total s-result-item elements: {len(result_items)}")

# Look for card containers
cards = soup.find_all(class_=lambda c: c and "s-card-container" in c)
print(f"Total s-card-container elements: {len(cards)}")

# Let's inspect some of the page text to see what product names are loaded
# E.g. search for text nodes that might represent product titles (typically inside h2 or span elements)
h2s = soup.find_all("h2")
print(f"\nTotal H2 tags: {len(h2s)}")
for idx, h2 in enumerate(h2s[:15], 1):
    print(f"  H2 [{idx}]: {h2.text.strip()}")

# If search_items exist, let's print the inner HTML snippet of the first card to inspect
if search_items:
    print("\n=== FIRST SEARCH ITEM HTML ===")
    print(search_items[0].prettify()[:1500])
elif cards:
    print("\n=== FIRST CARD CONTAINER HTML ===")
    print(cards[0].prettify()[:1500])
else:
    # Let's inspect elements with class containing 'product' or 'grid'
    print("\n=== FALLBACK: SEARCHING FOR OTHER ITEMS ===")
    potential_grid = soup.find_all(class_=lambda c: c and any(term in c.lower() for term in ["grid", "list", "asin", "deal"]))
    print(f"Potential grid/listing class elements: {len(potential_grid)}")
    for idx, el in enumerate(potential_grid[:10], 1):
         print(f"  [{idx}] <{el.name}> class={el.get('class')} -> '{el.text.strip()[:100]}'")
