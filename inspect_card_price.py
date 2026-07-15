from bs4 import BeautifulSoup

with open("kricar_loaded_delayed.html", "r", encoding="utf-8") as f:
    html = f.read()

soup = BeautifulSoup(html, "html.parser")
card = soup.find("a", class_="card")

if card:
    print("=== FULL CARD HTML ===")
    print(card.prettify())
else:
    print("No card found!")
