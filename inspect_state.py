import sys
import json
import re
from bs4 import BeautifulSoup

sys.stdout.reconfigure(encoding='utf-8')

with open("ouedkniss_loaded_delayed.html", "r", encoding="utf-8") as f:
    html = f.read()

soup = BeautifulSoup(html, "html.parser")

print("Searching for Nuxt/Vue state script tags...")
scripts = soup.find_all("script")
print(f"Total script tags: {len(scripts)}")

for idx, s in enumerate(scripts, 1):
    s_content = s.string or ""
    if "__NUXT__" in s_content or "__INITIAL_STATE__" in s_content or "apollo" in s_content.lower() or "window." in s_content:
        print(f"\n[{idx}] Found state script block! Length: {len(s_content)}")
        print(s_content[:500])
        # Write content to a file to examine
        with open(f"state_script_{idx}.js", "w", encoding="utf-8") as sf:
            sf.write(s_content)
        print(f"Written state block to state_script_{idx}.js")

# Check if page text contains any listing ID
print("\nIs listing ID '54315824' in HTML:", "54315824" in html)
