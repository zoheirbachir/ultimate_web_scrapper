import sys
from bs4 import BeautifulSoup

sys.stdout.reconfigure(encoding='utf-8')

with open("amazon_loaded.html", "r", encoding="utf-8") as f:
    html = f.read()

soup = BeautifulSoup(html, "html.parser")

# Find H2 containing "Rowenta Eole Silence Force Column Fan"
target_h2 = soup.find("h2", string=lambda t: t and "Rowenta Eole" in t)

if target_h2:
    print("Found Target H2 element! Inspecting outer parent containers...")
    parent = target_h2
    # Go up 5 levels
    for level in range(6):
        if not parent: break
        print(f"\n--- LEVEL {level} parent: <{parent.name}> class={parent.get('class')} ---")
        print(str(parent)[:800])
        parent = parent.parent
else:
    print("Could not find Target H2 containing 'Rowenta Eole'.")
