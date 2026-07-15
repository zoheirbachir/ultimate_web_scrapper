import sys
from bs4 import BeautifulSoup

sys.stdout.reconfigure(encoding='utf-8')

with open("ouedkniss_loaded_delayed.html", "r", encoding="utf-8") as f:
    html = f.read()

soup = BeautifulSoup(html, "html.parser")
specs_card = soup.find("div", class_="o-announ-specs")

if specs_card:
    print("=== o-announ-specs card HTML structure ===")
    # Print the outer HTML of the specs card
    print(specs_card.prettify()[:3000])
else:
    print("o-announ-specs card not found!")
