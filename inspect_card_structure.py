from bs4 import BeautifulSoup

with open("kricar_loaded_delayed.html", "r", encoding="utf-8") as f:
    html = f.read()

soup = BeautifulSoup(html, "html.parser")

# Find a div or span that contains "Fiat Scudo" or "Seat Cupra"
target_element = soup.find(string=lambda text: text and "Seat Cupra" in text)

if target_element:
    print("Found 'Seat Cupra' text. Inspecting its parent elements...")
    parent = target_element.parent
    # Go up 3 levels
    for i in range(5):
        if not parent:
            break
        print(f"\n--- LEVEL {i} parent (Tag: <{parent.name}>, Classes: {parent.get('class')}) ---")
        print(str(parent)[:500])
        parent = parent.parent
else:
    print("Could not find 'Seat Cupra' in loaded HTML.")
