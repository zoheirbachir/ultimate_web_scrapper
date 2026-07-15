import sys
from bs4 import BeautifulSoup

sys.stdout.reconfigure(encoding='utf-8')

with open("amazon_loaded.html", "r", encoding="utf-8") as f:
    html = f.read()

soup = BeautifulSoup(html, "html.parser")
card = soup.find(attrs={"data-cy": "asin-faceout-container"})

if card:
    print("=== SEARCHING FOR PRICING IN FIRST CARD ===")
    prices = card.find_all(class_=lambda c: c and any(term in c.lower() for term in ["price", "offscreen", "amount"]))
    print(f"Total price-related elements in card: {len(prices)}")
    for idx, el in enumerate(prices, 1):
        print(f"  [{idx}] <{el.name}> class={el.get('class')} -> '{el.text.strip()}'")
        
    print("\n=== RAW HTML SIBLINGS OF TITLE IN CARD ===")
    title_section = card.find(attrs={"data-cy": "title-recipe"})
    if title_section:
        parent = title_section.parent
        for sib in parent.find_next_siblings():
            print(f"<{sib.name}> class={sib.get('class')} -> '{sib.text.strip()[:200]}'")
else:
    print("No card found")
