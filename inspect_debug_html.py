import sys
from bs4 import BeautifulSoup

sys.stdout.reconfigure(encoding='utf-8')

with open("amazon_zero_debug.html", "r", encoding="utf-8") as f:
    html = f.read()

soup = BeautifulSoup(html, "html.parser")

# Print first 2000 chars of body text
print("=== BODY TEXT CONTENT ===")
print(soup.body.get_text(separator="\n", strip=True)[:2500] if soup.body else "No body")
