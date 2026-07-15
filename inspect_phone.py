import sys
import re
from bs4 import BeautifulSoup

sys.stdout.reconfigure(encoding='utf-8')

with open("ouedkniss_loaded_delayed.html", "r", encoding="utf-8") as f:
    html = f.read()

soup = BeautifulSoup(html, "html.parser")

print("=== SEARCHING FOR PHONE NUMBERS ===")
# Search for standard Algerian mobile patterns: 05xx xx xx xx, 06xx xx xx xx, 07xx xx xx xx
# or with spaces/dashes, or raw
phone_regex = r'(0[567]\d{8}|0[567]\d(?:\s?\d{2}){3}\d?)'
matches = re.findall(phone_regex, html)
print(f"Regex matches in raw HTML: {list(set(matches))}")

# Let's check DOM elements containing phone numbers or button texts
phone_buttons = soup.find_all(string=lambda t: t and any(term in t.lower() for term in ["téléphone", "phone", "اتصال", "الهاتف", "رقم"]))
print(f"\nElements containing phone labels: {len(phone_buttons)}")
for idx, btn in enumerate(phone_buttons[:10], 1):
    print(f"  [{idx}] <{btn.parent.name}> class={btn.parent.get('class')} -> '{btn.strip()}'")

# Look at parent text containing phone buttons
for btn in phone_buttons[:10]:
    p = btn.parent
    for i in range(2):
        if p:
            p = p.parent
    if p:
        print(f"  Parent context: <{p.name}> class={p.get('class')} -> '{p.text.strip()[:200]}'")
