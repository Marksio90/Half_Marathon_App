# quick_fix.py
import re

print("🔧 Fixing test_pipeline.py...")

with open('test_pipeline.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Fix: Spaces prefix (szukaj w root, nie data/)
content = content.replace("Prefix='data/'", "Prefix=''")

# Fix: Required files (bez data/)
content = content.replace(
    "'data/halfmarathon_wroclaw_2023__final.csv'",
    "'halfmarathon_wroclaw_2023__final.csv'"
)
content = content.replace(
    "'data/halfmarathon_wroclaw_2024__final.csv'",
    "'halfmarathon_wroclaw_2024__final.csv'"
)

# Fix: Display text
content = re.sub(
    r'print\(f"  📁 Pliki w data/.*?\)',
    'print(f"  📁 Pliki w bucket ({len(response[\'Contents\'])})")',
    content
)

with open('test_pipeline.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("✅ test_pipeline.py naprawiony!")