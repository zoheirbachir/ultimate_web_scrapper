import sys
from bs4 import BeautifulSoup

sys.stdout.reconfigure(encoding='utf-8')

with open("ouedkniss_loaded_delayed.html", "r", encoding="utf-8") as f:
    html = f.read()

soup = BeautifulSoup(html, "html.parser")

print("=== SEARCHING FOR LISTING TITLE TAGS ===")
# Find elements that contain the exact title text
title_text = "بيع شقة 3 غرف الجزائر الرغاية"
tags = soup.find_all(lambda tag: tag.name not in ["script", "style", "title"] and tag.string and title_text in tag.string)

for idx, tag in enumerate(tags, 1):
    print(f"  [{idx}] <{tag.name}> class={tag.get('class')} -> '{tag.text.strip()}'")
    
# Let's search by text matching inside child nodes if direct string matches are sparse
print("\n=== SEARCHING BY PARENT CONTAINERS ===")
containers = soup.find_all(lambda tag: tag.name not in ["script", "style", "html", "body"] and title_text in tag.text)
for idx, c in enumerate(containers[:10], 1):
    # Print tags that have length of text close to title
    if len(c.text.strip()) < 150:
        print(f"  [{idx}] <{c.name}> class={c.get('class')} -> '{c.text.strip()}'")
