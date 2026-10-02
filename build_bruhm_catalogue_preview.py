import csv
import sqlite3
from pathlib import Path

DB = Path("data/mika_competitive_intel.db")
OUT_DIR = Path("reports/mika_catalogue_preview/bruhm")
OUT_DIR.mkdir(parents=True, exist_ok=True)

OUT = OUT_DIR / "bruhm_catalogue_preview.csv"
CATEGORY_OUT = OUT_DIR / "category_distribution.csv"
SUBCATEGORY_OUT = OUT_DIR / "subcategory_distribution.csv"
REVIEW_OUT = OUT_DIR / "review_rows.csv"
SUSPICIOUS_OUT = OUT_DIR / "suspicious_mappings.csv"


def classify(name, raw_category, url):
    text = " ".join([
        str(name or ""),
        str(raw_category or ""),
        str(url or "")
    ]).lower()

    # Refrigeration
    if any(x in text for x in [
        "refrigerator", "fridge", "freezer", "beverage cooler",
        "wine cooler", "show-case", "showcase", "chest freezer",
        "upright freezer"
    ]):
        if "freezer" in text:
            if "show-case" in text or "showcase" in text or "glass-door" in text:
                return "Refrigeration", "Showcase Chillers", "high", "Explicit refrigeration/freezer source category"
            return "Refrigeration", "Freezers", "high", "Explicit freezer source category"

        if "beverage cooler" in text:
            return "Refrigeration", "Beverage Coolers", "high", "Explicit beverage cooler product type"

        if "wine" in text:
            return "Refrigeration", "Wine Chillers", "high", "Explicit wine cooler product type"

        if "bottom-mount" in text:
            return "Refrigeration", "Bottom Mount Refrigerators", "high", "Explicit refrigerator type"

        if "side-by-side" in text or "sbs" in text:
            return "Refrigeration", "Side-by-Side Refrigerators", "high", "Explicit refrigerator type"

        if "multi-door" in text:
            return "Refrigeration", "Multi-Door Refrigerators", "high", "Explicit refrigerator type"

        if "single-door" in text:
            return "Refrigeration", "Single Door Refrigerators", "high", "Explicit refrigerator type"

        return "Refrigeration", "Refrigerators", "high", "Explicit refrigerator source category"

    # Laundry
    if any(x in text for x in [
        "washer", "washing machine", "laundry",
        "dryer", "drying machine", "iron"
    ]):
        if "iron" in text:
            return "Laundry", "Irons", "high", "Explicit iron product type"

        if "dryer" in text:
            return "Laundry", "Clothes Dryers", "high", "Explicit dryer product type"

        if "front-load" in text or "front load" in text:
            return "Laundry", "Front Load Washing Machines", "high", "Explicit front-load washer type"

        if "twin-tub" in text or "twin tub" in text:
            return "Laundry", "Twin Tub Washing Machines", "high", "Explicit twin-tub washer type"

        if "top-load" in text or "top load" in text:
            return "Laundry", "Top Load Washing Machines", "high", "Explicit top-load washer type"

        return "Laundry", "Washing Machines", "high", "Explicit laundry/washer product type"

        # Water heaters must be classified before the generic "heater" rule
    if "water-heater" in text or "water heater" in text:
        return "Water", "Electric Water Heaters", "high", "Explicit electric water heater product type"

    # Air & Climate
    if any(x in text for x in [
        "air-conditioner", "air conditioner", "air-conditioning",
        "split-ac", "split-inverter-ac", "floor-standing-ac",
        "air-curtain", "standing-fan", "fan", "heater"
    ]):
        if "air-curtain" in text:
            return "Air & Climate", "Air Curtains", "high", "Explicit air curtain product type"

        if "fan" in text:
            return "Air & Climate", "Fans", "high", "Explicit fan product type"

        if "heater" in text:
            return "Air & Climate", "Heaters", "high", "Explicit space heater product type"

        return "Air & Climate", "Air Conditioners", "high", "Explicit air conditioner source category"
        if "air-curtain" in text:
            return "Air & Climate", "Air Curtains", "high", "Explicit air curtain product type"

        if "fan" in text:
            return "Air & Climate", "Fans", "high", "Explicit fan product type"

        if "heater" in text:
            return "Air & Climate", "Heaters", "high", "Explicit heater product type"

        return "Air & Climate", "Air Conditioners", "high", "Explicit air conditioner source category"

    # TV & Audio
    if any(x in text for x in [
        "television", "tv", "smart tv", "qled"
    ]):
        return "TV & Audio", "Televisions", "high", "Explicit television product type"

    # Water
    if "water-dispenser" in text or "water dispenser" in text:
        return "Water", "Water Dispensers", "high", "Explicit water dispenser product type"

    if "water-heater" in text or "water heater" in text:
        return "Water", "Electric Water Heaters", "high", "Explicit electric water heater product type"

    # Cooking
    if any(x in text for x in [
        "gas-cooker", "gas cooker", "gas stove", "gas-stove",
        "cooker", "hob", "microwave", "hood",
        "oven", "rice-cooker", "rice cooker"
    ]):
        if "microwave" in text:
            return "Small Kitchen Appliances", "Microwaves", "high", "Explicit standard/countertop microwave product type"

        if "hood" in text:
            return "Cooking", "Cooker Hoods", "high", "Explicit hood product type"

        if "hob" in text:
            return "Cooking", "Gas Hobs", "high", "Explicit hob product type"

        if "rice-cooker" in text or "rice cooker" in text:
            return "Small Kitchen Appliances", "Rice Cookers", "high", "Explicit rice cooker / small appliance product type"

        if "oven" in text and "microwave" not in text:
            return "Cooking", "Ovens", "high", "Explicit oven product type"

        return "Cooking", "Cookers & Gas Stoves", "high", "Explicit cooking product type"

    # Small Kitchen Appliances
    if any(x in text for x in [
        "kettle", "blender", "air-fryer", "air fryer",
        "sandwich-maker", "sandwich maker", "toaster",
        "small-appliances", "small appliances"
    ]):
        if "kettle" in text:
            return "Small Kitchen Appliances", "Kettles", "high", "Explicit kettle product type"

        if "blender" in text:
            return "Small Kitchen Appliances", "Blenders", "high", "Explicit blender product type"

        if "air-fryer" in text or "air fryer" in text:
            return "Small Kitchen Appliances", "Air Fryers", "high", "Explicit air fryer product type"

        if "sandwich" in text:
            return "Small Kitchen Appliances", "Sandwich Makers", "high", "Explicit sandwich maker product type"

        if "toaster" in text:
            return "Small Kitchen Appliances", "Toasters", "high", "Explicit toaster product type"

    # Home Care & Power
    if any(x in text for x in [
        "generator", "automatic-voltage-regulator",
        "voltage regulator", "power protector", "power protection"
    ]):
        if "generator" in text:
            return "Home Care & Power", "Generators", "high", "Explicit generator product type"

        return "Home Care & Power", "Power Protection", "high", "Explicit power protection product type"

    return "REVIEW", "REVIEW", "low", "Insufficient evidence for normalized classification"


def product_scope(category, subcategory):
    if category == "REVIEW":
        return "other"

    if "accessor" in str(subcategory).lower():
        return "accessory"

    return "core_appliance"


conn = sqlite3.connect(DB)

rows = conn.execute("""
    SELECT
        competitor,
        product_name,
        sku,
        category,
        product_url,
        first_seen_date,
        last_seen_date
    FROM bruhm_products
    ORDER BY id
""").fetchall()

conn.close()

records = []

for competitor, name, sku, raw_category, url, first_seen, last_seen in rows:
    category, subcategory, confidence, reason = classify(
        name,
        raw_category,
        url
    )

    status = "review" if category == "REVIEW" else "mapped"

    records.append({
        "competitor": competitor or "Bruhm",
        "product_name": name,
        "sku": sku,
        "raw_category": raw_category,
        "category": category,
        "sub_category": subcategory,
        "mapping_status": status,
        "mapping_confidence": confidence,
        "inferred_category_source": "source_category + product_name + product_url_slug",
        "mapping_reason": reason,
        "product_scope": product_scope(category, subcategory),
        "product_url": url,
        "first_seen_date": first_seen,
        "last_seen_date": last_seen,
    })


fields = list(records[0].keys())

with OUT.open("w", newline="", encoding="utf-8-sig") as f:
    writer = csv.DictWriter(f, fieldnames=fields)
    writer.writeheader()
    writer.writerows(records)


def write_distribution(path, rows):
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(rows[0])
        writer.writerows(rows[1:])


from collections import Counter

cat = Counter(r["category"] for r in records)
sub = Counter((r["category"], r["sub_category"]) for r in records)

write_distribution(
    CATEGORY_OUT,
    [["category", "count"]] +
    [[k, v] for k, v in cat.most_common()]
)

write_distribution(
    SUBCATEGORY_OUT,
    [["category", "sub_category", "count"]] +
    [[k[0], k[1], v] for k, v in sub.most_common()]
)

review = [r for r in records if r["mapping_status"] == "review"]

with REVIEW_OUT.open("w", newline="", encoding="utf-8-sig") as f:
    writer = csv.DictWriter(f, fieldnames=fields)
    writer.writeheader()
    writer.writerows(review)

suspicious = [
    r for r in records
    if r["mapping_confidence"] != "high"
    or r["mapping_status"] == "review"
    or r["product_scope"] != "core_appliance"
]

with SUSPICIOUS_OUT.open("w", newline="", encoding="utf-8-sig") as f:
    writer = csv.DictWriter(f, fieldnames=fields)
    writer.writeheader()
    writer.writerows(suspicious)


print("=" * 70)
print("BRUHM CATALOGUE NORMALIZATION PREVIEW")
print("=" * 70)
print(f"Products loaded: {len(records)}")
print(f"Mapped: {len(records) - len(review)}")
print(f"Review: {len(review)}")

print("\nCATEGORY DISTRIBUTION")
for k, v in cat.most_common():
    print(f"{v:4} | {k}")

print("\nCONFIDENCE")
confidence = Counter(r["mapping_confidence"] for r in records)
for k, v in confidence.most_common():
    print(f"{v:4} | {k}")

print("\nPRODUCT SCOPE")
scope = Counter(r["product_scope"] for r in records)
for k, v in scope.most_common():
    print(f"{v:4} | {k}")

print("\nOUTPUTS")
print(OUT)
print(CATEGORY_OUT)
print(SUBCATEGORY_OUT)
print(REVIEW_OUT)
print(SUSPICIOUS_OUT)

print("\nDATABASE STATUS: UNCHANGED")
