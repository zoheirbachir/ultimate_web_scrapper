import sys
from bs4 import BeautifulSoup

sys.stdout.reconfigure(encoding='utf-8')

with open("ouedkniss_loaded_delayed.html", "r", encoding="utf-8") as f:
    html = f.read()

soup = BeautifulSoup(html, "html.parser")

print("=== SEARCHING FOR PRICE IN DOM ===")
# Look for text matching dinar / millions / price classes
price_elements = soup.find_all(class_=lambda c: c and any(term in c.lower() for term in ["price", "tarif", "amount"]))
print(f"Elements matching 'price' classes: {len(price_elements)}")
for idx, el in enumerate(price_elements, 1):
    print(f"  [{idx}] <{el.name}> class={el.get('class')} -> '{el.text.strip()}'")

# Look for specific text pattern like "مليون" or "مليار" or "دج" or "DA"
for tag in soup.find_all(True):
    text = tag.text.strip()
    if any(k in text for k in ["مليون", "دج", "مليار", "DA"]) and len(text) < 100:
        # Check if it contains digits
        import re
        if re.search(r'\d', text):
            print(f"<{tag.name}> class={tag.get('class')} -> '{text}'")
