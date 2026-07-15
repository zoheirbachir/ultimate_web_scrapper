import sys
sys.stdout.reconfigure(encoding='utf-8')

with open("ouedkniss_loaded.html", "r", encoding="utf-8") as f:
    html = f.read()

print("=== FIRST 1000 CHARACTERS ===")
print(html[:1000])

print("\n=== LAST 1000 CHARACTERS ===")
print(html[-1000:])
