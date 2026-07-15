import sys
from bs4 import BeautifulSoup

sys.stdout.reconfigure(encoding='utf-8')

with open("ouedkniss_loaded_delayed.html", "r", encoding="utf-8") as f:
    html = f.read()

soup = BeautifulSoup(html, "html.parser")
header = soup.find("header")

if header:
    print("=== HEADER HTML ===")
    print(header.prettify())
else:
    print("No header element found!")
