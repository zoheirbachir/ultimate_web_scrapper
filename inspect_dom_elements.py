import sys
from bs4 import BeautifulSoup

sys.stdout.reconfigure(encoding='utf-8')

with open("ouedkniss_loaded_delayed.html", "r", encoding="utf-8") as f:
    html = f.read()

soup = BeautifulSoup(html, "html.parser")

# Let's find divs containing text like "نوع" (Type), "غرف" (Rooms), "المساحة" (Area), or "عقد ملكية" (Document type)
print("=== SPECIFICATION GRID ELEMENTS SEARCH ===")
keywords = ["نوع", "عدد الغرف", "المساحة", "الوثائق", "شقة", "مليار", "دج", "الرغاية"]
for kw in keywords:
    el = soup.find(string=lambda t: t and kw in t)
    if el:
        print(f"\nKeyword '{kw}' found in text: '{el.strip()}'")
        # Go up 3 levels to inspect parents
        parent = el.parent
        for level in range(3):
            if not parent: break
            print(f"  Level {level} parent: <{parent.name}> class={parent.get('class')} attrs={parent.attrs}")
            parent = parent.parent

# Let's search for list items or elements that have grid classes or layout classes
print("\n=== SPECIFICATION LIST ITEMS ===")
# Ouedkniss usually stores specifications in list items or grid divs
for tag in soup.find_all(["div", "span", "p", "li"]):
    text = tag.text.strip()
    if any(k in text for k in ["عدد الغرف", "المساحة", "عقد ملكية"]) and len(text) < 150:
        print(f"<{tag.name}> class={tag.get('class')} -> '{text}'")
