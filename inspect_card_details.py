import sys
from bs4 import BeautifulSoup

sys.stdout.reconfigure(encoding='utf-8')

with open("amazon_loaded.html", "r", encoding="utf-8") as f:
    html = f.read()

soup = BeautifulSoup(html, "html.parser")
card = soup.find(attrs={"data-cy": "asin-faceout-container"})

if card:
    print("=== AMAZON CARD HTML ===")
    print(card.prettify()[:4000])
else:
    print("No card found with data-cy='asin-faceout-container'")
