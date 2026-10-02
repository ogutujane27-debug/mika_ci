import re
import json
import csv
from pathlib import Path
from datetime import date

BUNDLE = Path(r"reports\mika_catalogue_preview\diagnostic\mika_meteor.js")
OUT_DIR = Path(r"reports\mika_catalogue_preview")

s = BUNDLE.read_text(encoding="utf-8")

# The embedded catalogue is the large array containing itemName/modelNo/imageURL/productURL.
# We identify the first catalogue record around the confirmed product cluster,
# then find the opening '[' and matching closing ']' structurally.
anchor = s.find('itemName:"Standing Cooker')
if anchor == -1:
    raise SystemExit("Could not find catalogue anchor.")

# Walk backwards to the nearest '[' before the first product record.
array_start = s.rfind("[", 0, anchor)
if array_start == -1:
    raise SystemExit("Could not locate catalogue array start.")

# Find the matching closing bracket while respecting quoted strings.
depth = 0
in_string = False
escape = False
array_end = None

for i in range(array_start, len(s)):
    ch = s[i]

    if in_string:
        if escape:
            escape = False
        elif ch == "\\":
            escape = True
        elif ch == '"':
            in_string = False
        continue

    if ch == '"':
        in_string = True
    elif ch == "[":
        depth += 1
    elif ch == "]":
        depth -= 1
        if depth == 0:
            array_end = i
            break

if array_end is None:
    raise SystemExit("Could not locate catalogue array end.")

catalogue_text = s[array_start:array_end + 1]

print("Bundle:", BUNDLE)
print("Bundle characters:", len(s))
print("Catalogue array start:", array_start)
print("Catalogue array end:", array_end)
print("Catalogue characters:", len(catalogue_text))

# The objects are simple JS object literals with five known fields.
pattern = re.compile(
    r'\{'
    r'itemName:"(?P<item_name>(?:\\.|[^"\\])*)",'
    r'modelNo:"(?P<model_no>(?:\\.|[^"\\])*)",'
    r'imageURL:"(?P<image_url>(?:\\.|[^"\\])*)",'
    r'productURL:"(?P<product_url>(?:\\.|[^"\\])*)",'
    r'warrantyPeriod:"(?P<warranty_period>(?:\\.|[^"\\])*)"'
    r'\}'
)

rows = []

for m in pattern.finditer(catalogue_text):
    row = {
        "brand": "MIKA",
        "item_name": m.group("item_name"),
        "model_no": m.group("model_no"),
        "image_url": m.group("image_url"),
        "product_url": m.group("product_url"),
        "warranty_period": m.group("warranty_period"),
        "source": "MIKA embedded catalogue",
        "extracted_date": str(date.today()),
    }
    rows.append(row)

print("Raw product records extracted:", len(rows))

# Deduplicate by model number.
deduped = {}
duplicates = []

for row in rows:
    model = row["model_no"].strip()

    if not model:
        continue

    if model in deduped:
        duplicates.append(row)
    else:
        deduped[model] = row

rows = list(deduped.values())

print("Unique products by model_no:", len(rows))
print("Duplicate records removed:", len(duplicates))

# Save raw extraction only.
OUT_DIR.mkdir(parents=True, exist_ok=True)

raw_csv = OUT_DIR / "mika_catalogue_raw_extracted.csv"

fields = [
    "brand",
    "item_name",
    "model_no",
    "image_url",
    "product_url",
    "warranty_period",
    "source",
    "extracted_date",
]

with raw_csv.open("w", newline="", encoding="utf-8-sig") as f:
    writer = csv.DictWriter(f, fieldnames=fields)
    writer.writeheader()
    writer.writerows(rows)

print()
print("RAW PREVIEW CREATED")
print(raw_csv)
print()
print("First 10 products:")

for row in rows[:10]:
    print(
        f'{row["model_no"]} | '
        f'{row["item_name"]} | '
        f'{row["warranty_period"]}'
    )
