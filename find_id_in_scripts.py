import sys
from bs4 import BeautifulSoup

sys.stdout.reconfigure(encoding='utf-8')

with open("ouedkniss_loaded_delayed.html", "r", encoding="utf-8") as f:
    html = f.read()

soup = BeautifulSoup(html, "html.parser")
scripts = soup.find_all("script")

print("Checking which script tags contain the listing ID '54315824'...")
for idx, s in enumerate(scripts, 1):
    content = s.string or s.text or ""
    if "54315824" in content:
        print(f"\n[{idx}] Found ID in script! Length: {len(content)}")
        # Print first 1000 characters
        print(content[:1000])
        # Save to file
        with open(f"id_script_{idx}.js", "w", encoding="utf-8") as sf:
            sf.write(content)
        print(f"Saved to id_script_{idx}.js")
        
# Check other elements
print("\nChecking other tags containing ID:")
for tag in soup.find_all(True):
    # check if tag has some text and tag name is not script or style
    if tag.name not in ["script", "style"] and tag.string and "54315824" in tag.string:
        print(f"<{tag.name}> : {tag.string}")
