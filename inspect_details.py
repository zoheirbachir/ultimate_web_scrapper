import sys
from bs4 import BeautifulSoup

# Reconfigure stdout to use UTF-8
sys.stdout.reconfigure(encoding='utf-8')

with open("kricar_loaded.html", "r", encoding="utf-8") as f:
    html = f.read()

soup = BeautifulSoup(html, "html.parser")

root = soup.find(id="root")
if root:
    print("=== ROOT CONTENT TEXT ===")
    print(root.get_text(separator="\n", strip=True)[:3000])
else:
    print("No #root element found!")
