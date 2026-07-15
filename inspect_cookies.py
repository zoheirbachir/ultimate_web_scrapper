import sys
from bs4 import BeautifulSoup

sys.stdout.reconfigure(encoding='utf-8')

with open("amazon_zero_debug.html", "r", encoding="utf-8") as f:
    html = f.read()

soup = BeautifulSoup(html, "html.parser")

print("Searching for cookie consent buttons...")
accept_btn = soup.find(id="sp-cc-accept")
if accept_btn:
    print(f"Found 'sp-cc-accept' button: {accept_btn.prettify()}")
else:
    print("Could not find 'sp-cc-accept' button by ID.")
    
# Find all input or button tags with accept or consent in their attributes
for tag in soup.find_all(["input", "button", "a"]):
    text = tag.text.strip().lower()
    tag_id = tag.get("id", "")
    tag_name = tag.get("name", "")
    if "accept" in text or "accept" in tag_id or "accept" in tag_name:
        print(f"Found candidate: <{tag.name}> id={tag_id} name={tag_name} class={tag.get('class')} text='{text[:100]}'")
