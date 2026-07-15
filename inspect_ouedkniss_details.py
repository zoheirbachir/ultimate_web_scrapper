import sys
from bs4 import BeautifulSoup

sys.stdout.reconfigure(encoding='utf-8')

with open("ouedkniss_loaded.html", "r", encoding="utf-8") as f:
    html = f.read()

soup = BeautifulSoup(html, "html.parser")

# Print page title
print("Page Title Tag:", soup.title.text if soup.title else "None")

# Find main content h1
h1s = soup.find_all("h1")
print(f"H1 tags ({len(h1s)}):")
for idx, h1 in enumerate(h1s, 1):
    print(f"  [{idx}] {h1.text.strip()}")

# Let's search for class names or structures.
# Let's check if the text contains Reghaia (الرغاية) or price (مليار) or room count (3 غرف)
text_content = soup.get_text(separator="\n", strip=True)
print("\nContains 'الرغاية' (Reghaia):", "الرغاية" in text_content)
print("Contains 'غرف' (rooms):", "غرف" in text_content)

# Print a larger chunk of text from the body to see if it is loaded
print("\n=== BODY SNAPSHOT (1000 - 3000 chars) ===")
print(text_content[1000:3000])
