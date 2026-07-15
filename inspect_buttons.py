import sys
from bs4 import BeautifulSoup

sys.stdout.reconfigure(encoding='utf-8')

with open("ouedkniss_loaded_delayed.html", "r", encoding="utf-8") as f:
    html = f.read()

soup = BeautifulSoup(html, "html.parser")

print("=== ALL BUTTON ELEMENTS ===")
buttons = soup.find_all("button")
print(f"Total buttons: {len(buttons)}")
for idx, btn in enumerate(buttons, 1):
    print(f"  [{idx}] class={btn.get('class')} -> '{btn.text.strip()}'")
    
print("\n=== ALL LINKS (a tags) WITH BUTTON CLASSES ===")
links = soup.find_all("a", class_=lambda c: c and "btn" in str(c).lower())
for idx, lnk in enumerate(links, 1):
    print(f"  [{idx}] href={lnk.get('href')} class={lnk.get('class')} -> '{lnk.text.strip()}'")
