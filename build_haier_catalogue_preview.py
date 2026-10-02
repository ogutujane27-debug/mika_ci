import csv
import sqlite3
from pathlib import Path
from collections import Counter


# ============================================================
# PATHS
# ============================================================

DB = Path("data/mika_competitive_intel.db")

OUT_DIR = Path("reports/mika_catalogue_preview/HAIER")
OUT_DIR.mkdir(parents=True, exist_ok=True)

OUT = OUT_DIR / "haier_catalogue_preview.csv"
CATEGORY_OUT = OUT_DIR / "category_distribution.csv"
SUBCATEGORY_OUT = OUT_DIR / "subcategory_distribution.csv"
REVIEW_OUT = OUT_DIR / "review_rows.csv"
SUSPICIOUS_OUT = OUT_DIR / "suspicious_mappings.csv"


# ============================================================
# HAIER PRODUCT CLASSIFICATION
# ============================================================

def classify(name, raw_category, url):
    """
    Read-only normalization of Haier catalogue products.

    Evidence priority:
        1. Product name
        2. Product URL slug
        3. Raw source category

    Raw source categories are preserved separately.

    Competitor/brand tags such as JTC and Haier are NOT treated
    as normalized product categories.

    Unclear classifications go to REVIEW.
    """

    name_text = str(name or "").lower()
    raw_text = str(raw_category or "").lower()
    url_text = str(url or "").lower()

    text = " ".join([
        name_text,
        raw_text,
        url_text,
    ])

    # Padded text helps detect standalone terms such as "ac".
    padded = f" {text} "

    # --------------------------------------------------------
    # 1. WATER
    # IMPORTANT:
    # Water-heater checks MUST happen before generic
    # heat-pump / AC checks.
    # --------------------------------------------------------

    if any(x in text for x in [
        "water-heater",
        "water heater",
        "water-heaters",
    ]):
        if "heat-pump" in text or "heat pump" in text:
            return (
                "Water",
                "Heat Pump Water Heaters",
                "high",
                "Explicit heat-pump water heater product type"
            )

        return (
            "Water",
            "Electric Water Heaters",
            "high",
            "Explicit water heater product type"
        )

    if (
        "water-dispenser" in text
        or "water dispenser" in text
    ):
        return (
            "Water",
            "Water Dispensers",
            "high",
            "Explicit water dispenser product type"
        )

    # --------------------------------------------------------
    # 2. REFRIGERATION
    # --------------------------------------------------------

    refrigeration_terms = [
        "refrigerator",
        "fridge",
        "freezer",
        "chest-freezer",
        "chest freezer",
        "bottom-mount",
        "bottom mount",
        "top-mount",
        "top mount",
        "side-by-side",
        "side by side",
        "four-door",
        "four door",
        "4-door",
        "4 door",
        "single-door",
        "single door",
    ]

    if any(x in text for x in refrigeration_terms):

        # Chest freezers
        if (
            "chest-freezer" in text
            or "chest freezer" in text
        ):
            return (
                "Refrigeration",
                "Chest Freezers",
                "high",
                "Explicit chest freezer product type"
            )

        # Showcase chillers
        if (
            "showcase" in text
            or "show-case" in text
            or "glass-door" in text
            or "glass door" in text
        ):
            return (
                "Refrigeration",
                "Showcase Chillers",
                "high",
                "Explicit showcase/glass-door refrigeration product type"
            )

        # Beverage coolers
        if (
            "beverage cooler" in text
            or "beverage-cooler" in text
        ):
            return (
                "Refrigeration",
                "Beverage Coolers",
                "high",
                "Explicit beverage cooler product type"
            )

        # Wine chillers
        if (
            "wine cooler" in text
            or "wine chiller" in text
        ):
            return (
                "Refrigeration",
                "Wine Chillers",
                "high",
                "Explicit wine cooler/chiller product type"
            )

        # Bottom mount
        if (
            "bottom-mount" in text
            or "bottom mount" in text
        ):
            return (
                "Refrigeration",
                "Bottom Mount Refrigerators",
                "high",
                "Explicit bottom-mount refrigerator type"
            )

        # Side-by-side
        if (
            "side-by-side" in text
            or "side by side" in text
            or "sbs" in text
        ):
            return (
                "Refrigeration",
                "Side-by-Side Refrigerators",
                "high",
                "Explicit side-by-side refrigerator type"
            )

        # Four door
        if (
            "four-door" in text
            or "four door" in text
            or "4-door" in text
            or "4 door" in text
        ):
            return (
                "Refrigeration",
                "Four Door Refrigerators",
                "high",
                "Explicit four-door refrigerator type"
            )

        # Multi door
        if (
            "multi-door" in text
            or "multi door" in text
        ):
            return (
                "Refrigeration",
                "Multi-Door Refrigerators",
                "high",
                "Explicit multi-door refrigerator type"
            )

        # Top mount
        if (
            "top-mount" in text
            or "top mount" in text
        ):
            return (
                "Refrigeration",
                "Top Mount Refrigerators",
                "high",
                "Explicit top-mount refrigerator type"
            )

        # Single door
        if (
            "single-door" in text
            or "single door" in text
        ):
            return (
                "Refrigeration",
                "Single Door Refrigerators",
                "high",
                "Explicit single-door refrigerator type"
            )

        # Generic freezer
        if "freezer" in text:
            return (
                "Refrigeration",
                "Freezers",
                "high",
                "Explicit freezer product type"
            )

        # Generic refrigerator
        if (
            "refrigerator" in text
            or "fridge" in text
        ):
            return (
                "Refrigeration",
                "Refrigerators",
                "high",
                "Explicit refrigerator product type"
            )

    # --------------------------------------------------------
    # 3. LAUNDRY
    # --------------------------------------------------------

    # Dishwashers are Laundry for the agreed MIKA taxonomy.
    if (
        "dishwasher" in text
        or "dish-washer" in text
    ):
        return (
            "Laundry",
            "Dishwashers",
            "high",
            "Explicit dishwasher product type"
        )

    # Steam irons
    if "steam iron" in text:
        return (
            "Laundry",
            "Steam Irons",
            "high",
            "Explicit steam iron product type"
        )

    # Dry irons
    if "dry iron" in text:
        return (
            "Laundry",
            "Dry Irons",
            "high",
            "Explicit dry iron product type"
        )

    # Generic iron
    if "iron" in text:
        return (
            "Laundry",
            "Irons",
            "high",
            "Explicit iron product type"
        )

    # Washer-dryer combinations must be checked before
    # generic washing machine rules.
    if (
        "washer-dryer" in text
        or "washer dryer" in text
        or "washer-dryer combo" in text
        or "washer dryer combo" in text
    ):
        return (
            "Laundry",
            "Washer-Dryer Combos",
            "high",
            "Explicit washer-dryer combination product type"
        )

    # Washing machines
    if any(x in text for x in [
        "washing machine",
        "washing-machine",
        "washer",
        "washers-dryers",
        "washers dryers",
        "twin-tub",
        "twin tub",
    ]):

        if (
            "twin-tub" in text
            or "twin tub" in text
            or "semi-auto" in text
            or "semi auto" in text
            or "semi-automatic" in text
            or "semi automatic" in text
        ):
            return (
                "Laundry",
                "Semi-Automatic Washing Machines",
                "high",
                "Explicit semi-automatic/twin-tub washing machine type"
            )

        if (
            "front-load" in text
            or "front load" in text
        ):
            return (
                "Laundry",
                "Front Load Washing Machines",
                "high",
                "Explicit front-load washing machine type"
            )

        if (
            "top-load" in text
            or "top load" in text
        ):
            return (
                "Laundry",
                "Top Load Washing Machines",
                "high",
                "Explicit top-load washing machine type"
            )

        return (
            "Laundry",
            "Washing Machines",
            "high",
            "Explicit washing machine product type"
        )

    # --------------------------------------------------------
    # 4. AIR & CLIMATE
    # IMPORTANT:
    # This comes AFTER water-heater rules.
    # Handles AC, A/C, split AC and HSU BTU models.
    # --------------------------------------------------------

    if any(x in text for x in [
        "air-conditioner",
        "air conditioner",
        "air-conditioning",
        "air conditioning",
        "split-ac",
        "split ac",
        "split-inverter-ac",
        "split inverter ac",
        "floor-standing-ac",
        "floor standing ac",
        "floor-standing a/c",
        "floor standing a/c",
        "aircon",
        "a/c",
    ]):

        return (
            "Air & Climate",
            "Air Conditioners",
            "high",
            "Explicit air conditioner product type"
        )

    # Standalone AC abbreviation.
    if " ac " in padded:
        return (
            "Air & Climate",
            "Air Conditioners",
            "high",
            "Explicit AC product abbreviation"
        )

    # Haier HSU models with BTU are air-conditioner models in
    # the observed Haier catalogue.
    if (
        " btu " in padded
        and "hsu" in text
    ):
        return (
            "Air & Climate",
            "Air Conditioners",
            "high",
            "Haier HSU BTU model explicitly indicates air conditioner"
        )

    if (
        "air curtain" in text
        or "air-curtain" in text
    ):
        return (
            "Air & Climate",
            "Air Curtains",
            "high",
            "Explicit air curtain product type"
        )

    if "fan" in text:
        return (
            "Air & Climate",
            "Fans",
            "high",
            "Explicit fan product type"
        )

    # --------------------------------------------------------
    # 5. TV & AUDIO
    # --------------------------------------------------------

    if (
        "television" in text
        or "smart tv" in text
        or "tv-audio" in raw_text
        or " tv " in padded
        or text.endswith(" tv")
    ):
        return (
            "TV & Audio",
            "Televisions",
            "high",
            "Explicit television product type/source category"
        )

    # --------------------------------------------------------
    # 6. BUILT-IN COOKING
    # --------------------------------------------------------

    # Built-in kitchen bundles must remain ONE product.
    if (
        "bundle" in text
        and (
            "hood" in text
            or "hob" in text
            or "oven" in text
        )
    ):
        return (
            "Cooking",
            "Built-in Kitchen Bundle",
            "high",
            "Explicit built-in kitchen bundle containing cooking appliances"
        )

    # Some bundle/product names may not literally contain "bundle".
    if (
        "hood" in text
        and "hob" in text
        and "oven" in text
        and (
            "built-in" in text
            or "built in" in text
            or "kitchen" in text
        )
    ):
        return (
            "Cooking",
            "Built-in Kitchen Bundle",
            "high",
            "Explicit built-in kitchen combination"
        )

    # Cooker hoods
    if (
        "cooker hood" in text
        or "cooker-hood" in text
        or "kitchen hood" in text
        or "chimney hood" in text
        or "chimney-hood" in text
        or (
            "hood" in text
            and (
                "built-in" in text
                or "built in" in text
                or "kitchen" in text
                or "cooker" in text
            )
        )
    ):
        return (
            "Cooking",
            "Cooker Hoods",
            "high",
            "Explicit cooker/kitchen hood product type"
        )

    # Built-in hobs
    if "hob" in text:
        return (
            "Cooking",
            "Built-in Hobs",
            "high",
            "Explicit hob product type"
        )

    # Built-in ovens
    if (
        "built-in oven" in text
        or "built in oven" in text
        or "built-in multifunction oven" in text
        or "built in multifunction oven" in text
    ):
        return (
            "Cooking",
            "Built-in Ovens",
            "high",
            "Explicit built-in oven product type"
        )

    # --------------------------------------------------------
    # 7. SMALL KITCHEN APPLIANCES
    # --------------------------------------------------------

    # Microwaves
    # Built-in microwaves belong under Cooking.
    if "built-in microwave" in text or "built in microwave" in text:
        return (
            "Cooking",
            "Built-in Microwaves",
            "high",
            "Explicit built-in microwave product type"
        )

    # Standard/countertop microwaves belong under Small Kitchen Appliances.
    if "microwave" in text:
        return (
            "Small Kitchen Appliances",
            "Microwaves",
            "high",
            "Explicit standard/countertop microwave product type"
        )

    # Air fryers
    if (
        "air-fryer" in text
        or "air fryer" in text
    ):
        return (
            "Small Kitchen Appliances",
            "Air Fryers",
            "high",
            "Explicit air fryer product type"
        )

    # Blenders
    if "blender" in text:
        return (
            "Small Kitchen Appliances",
            "Blenders",
            "high",
            "Explicit blender product type"
        )

    # Kettles
    if "kettle" in text:
        return (
            "Small Kitchen Appliances",
            "Kettles",
            "high",
            "Explicit kettle product type"
        )

    # Toasters
    if "toaster" in text:
        return (
            "Small Kitchen Appliances",
            "Toasters",
            "high",
            "Explicit toaster product type"
        )

    # Rice cookers
    if (
        "rice-cooker" in text
        or "rice cooker" in text
    ):
        return (
            "Small Kitchen Appliances",
            "Rice Cookers",
            "high",
            "Explicit rice cooker product type"
        )

    # Sandwich makers
    if (
        "sandwich-maker" in text
        or "sandwich maker" in text
    ):
        return (
            "Small Kitchen Appliances",
            "Sandwich Makers",
            "high",
            "Explicit sandwich maker product type"
        )

    # --------------------------------------------------------
    # 8. COOKING
    # --------------------------------------------------------

    # Tabletop / gas burner stoves
    if any(x in text for x in [
        "tabletop burner",
        "tabletop gas",
        "table top gas",
        "gas burner stove",
        "gas burner",
        "double burner gas",
        "double burner stove",
        "gas stove",
        "gas-stove",
    ]):
        return (
            "Cooking",
            "Gas Stoves",
            "high",
            "Explicit gas stove/burner product type"
        )

    # Freestanding cookers
    if (
        "gas cooker" in text
        or "gas-cooker" in text
        or "freestanding cooker" in text
        or "free-standing cooker" in text
    ):
        return (
            "Cooking",
            "Freestanding Cookers",
            "high",
            "Explicit freestanding cooker product type"
        )

    # Generic cooker
    if "cooker" in text:

        if "electric cooker" in text:
            return (
                "Cooking",
                "Freestanding Cookers",
                "high",
                "Explicit electric cooker product type"
            )

        return (
            "Cooking",
            "Freestanding Cookers",
            "high",
            "Explicit cooker product type"
        )

    # Electric oven toaster / countertop oven toaster
    if (
        "oven toaster" in text
        or "oven-toaster" in text
    ):
        return (
            "Cooking",
            "Electric Oven Toasters",
            "high",
            "Explicit electric oven toaster product type"
        )

    # Generic oven
    if "oven" in text:
        return (
            "Cooking",
            "Ovens",
            "high",
            "Explicit oven product type"
        )

    # --------------------------------------------------------
    # 9. HOME CARE & POWER
    # --------------------------------------------------------

    if "generator" in text:
        return (
            "Home Care & Power",
            "Generators",
            "high",
            "Explicit generator product type"
        )

    if any(x in text for x in [
        "automatic-voltage-regulator",
        "automatic voltage regulator",
        "voltage regulator",
        "power protector",
        "power protection",
    ]):
        return (
            "Home Care & Power",
            "Power Protection",
            "high",
            "Explicit power protection product type"
        )

    # --------------------------------------------------------
    # 10. UNRESOLVED
    # --------------------------------------------------------

    return (
        "REVIEW",
        "REVIEW",
        "low",
        "Insufficient evidence for normalized classification"
    )


# ============================================================
# PRODUCT SCOPE
# ============================================================

def product_scope(category, subcategory):
    if category == "REVIEW":
        return "other"

    if "accessor" in str(subcategory).lower():
        return "accessory"

    return "core_appliance"


# ============================================================
# READ HAIER PRODUCTS
# DATABASE IS READ-ONLY
# ============================================================

if not DB.exists():
    raise SystemExit(
        f"ERROR: Database not found: {DB.resolve()}"
    )

conn = sqlite3.connect(DB)

try:
    rows = conn.execute("""
        SELECT sku,
               product_name,
               category,
               url,
               first_seen_date,
               last_seen_date
        FROM haier_products
        ORDER BY id
    """).fetchall()
finally:
    conn.close()


# ============================================================
# BUILD PREVIEW RECORDS
# ============================================================

records = []

for sku, name, raw_category, url, first_seen, last_seen in rows:

    competitor = "HAIER"

    category, subcategory, confidence, reason = classify(
        name,
        raw_category,
        url
    )

    status = (
        "review"
        if category == "REVIEW"
        else "mapped"
    )

    records.append({
        "competitor": competitor,
        "product_name": name,
        "sku": sku,
        "raw_category": raw_category,
        "category": category,
        "sub_category": subcategory,
        "mapping_status": status,
        "mapping_confidence": confidence,
        "inferred_category_source": (
            "source_category + product_name + product_url_slug"
        ),
        "mapping_reason": reason,
        "product_scope": product_scope(
            category,
            subcategory
        ),
        "product_url": url,
        "first_seen_date": first_seen,
        "last_seen_date": last_seen,
    })


# ============================================================
# SAFETY CHECK
# ============================================================

if not records:
    raise SystemExit(
        "ERROR: No Haier products were loaded."
    )


# ============================================================
# WRITE MAIN PREVIEW
# ============================================================

fields = list(records[0].keys())

with OUT.open(
    "w",
    newline="",
    encoding="utf-8-sig"
) as f:

    writer = csv.DictWriter(
        f,
        fieldnames=fields
    )

    writer.writeheader()
    writer.writerows(records)


# ============================================================
# DISTRIBUTIONS
# ============================================================

def write_distribution(path, rows):

    with path.open(
        "w",
        newline="",
        encoding="utf-8-sig"
    ) as f:

        writer = csv.writer(f)

        writer.writerow(rows[0])
        writer.writerows(rows[1:])


cat = Counter(
    r["category"]
    for r in records
)

sub = Counter(
    (
        r["category"],
        r["sub_category"]
    )
    for r in records
)


write_distribution(
    CATEGORY_OUT,
    [["category", "count"]]
    + [
        [k, v]
        for k, v in cat.most_common()
    ]
)


write_distribution(
    SUBCATEGORY_OUT,
    [["category", "sub_category", "count"]]
    + [
        [k[0], k[1], v]
        for k, v in sub.most_common()
    ]
)


# ============================================================
# REVIEW ROWS
# ============================================================

review = [
    r
    for r in records
    if r["mapping_status"] == "review"
]

with REVIEW_OUT.open(
    "w",
    newline="",
    encoding="utf-8-sig"
) as f:

    writer = csv.DictWriter(
        f,
        fieldnames=fields
    )

    writer.writeheader()
    writer.writerows(review)


# ============================================================
# SUSPICIOUS MAPPINGS
# ============================================================

suspicious = [
    r
    for r in records
    if (
        r["mapping_confidence"] != "high"
        or r["mapping_status"] == "review"
        or r["product_scope"] != "core_appliance"
    )
]

with SUSPICIOUS_OUT.open(
    "w",
    newline="",
    encoding="utf-8-sig"
) as f:

    writer = csv.DictWriter(
        f,
        fieldnames=fields
    )

    writer.writeheader()
    writer.writerows(suspicious)


# ============================================================
# CONSOLE REPORT
# ============================================================

print("=" * 70)
print("HAIER CATALOGUE NORMALIZATION PREVIEW")
print("=" * 70)

print(f"Products loaded: {len(records)}")
print(f"Mapped: {len(records) - len(review)}")
print(f"Review: {len(review)}")


print("\nCATEGORY DISTRIBUTION")

for k, v in cat.most_common():
    print(f"{v:4} | {k}")


print("\nCONFIDENCE")

confidence = Counter(
    r["mapping_confidence"]
    for r in records
)

for k, v in confidence.most_common():
    print(f"{v:4} | {k}")


print("\nPRODUCT SCOPE")

scope = Counter(
    r["product_scope"]
    for r in records
)

for k, v in scope.most_common():
    print(f"{v:4} | {k}")


print("\nREVIEW / SUSPICIOUS")

print(f"Review rows:      {len(review)}")
print(f"Suspicious rows:  {len(suspicious)}")


print("\nOUTPUTS")

print(OUT)
print(CATEGORY_OUT)
print(SUBCATEGORY_OUT)
print(REVIEW_OUT)
print(SUSPICIOUS_OUT)


print("\nDATABASE STATUS: UNCHANGED")