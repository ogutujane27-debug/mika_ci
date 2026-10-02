import csv
import re
from pathlib import Path
from collections import Counter

BASE = Path(r"reports\mika_catalogue_preview")
RAW_CSV = BASE / "mika_catalogue_raw_extracted.csv"

PREVIEW_CSV = BASE / "mika_catalogue_preview.csv"
CATEGORY_CSV = BASE / "category_distribution.csv"
SUBCATEGORY_CSV = BASE / "subcategory_distribution.csv"
REVIEW_CSV = BASE / "review_rows.csv"
SUSPICIOUS_CSV = BASE / "suspicious_mappings.csv"

with RAW_CSV.open(encoding="utf-8-sig", newline="") as f:
    rows = list(csv.DictReader(f))

print("Products loaded:", len(rows))


# ------------------------------------------------------------
# NORMALIZATION HELPERS
# ------------------------------------------------------------

def clean(value):
    return re.sub(r"\s+", " ", (value or "").strip())


def text_for(row):
    return (
        clean(row.get("item_name", "")) + " " +
        clean(row.get("product_url", ""))
    ).lower()


def assign(row):
    """
    Returns:
        category,
        sub_category,
        mapping_status,
        mapping_confidence,
        inferred_category_source,
        reason,
        product_scope
    """

    item = clean(row.get("item_name", ""))
    url = clean(row.get("product_url", ""))

    text = text_for(row)

    # --------------------------------------------------------
    # REFRIGERATION
    # --------------------------------------------------------

    if "water dispenser" in text:
        return (
            "Water",
            "Water Dispensers",
            "mapped",
            "high",
            "product_url_slug + item_name",
            "Explicit water dispenser product type",
            "core_appliance"
        )

    if "wine chiller" in text:
        return (
            "Refrigeration",
            "Wine Chillers",
            "mapped",
            "high",
            "product_url_slug + item_name",
            "Explicit wine chiller product type",
            "core_appliance"
        )

    if "showcase chiller" in text:
        return (
            "Refrigeration",
            "Showcase Chillers",
            "mapped",
            "high",
            "product_url_slug + item_name",
            "Explicit showcase chiller product type",
            "core_appliance"
        )

    if "ice maker" in text or "ice-maker" in text:
        return (
            "Refrigeration",
            "Ice Makers",
            "mapped",
            "high",
            "product_url_slug + item_name",
            "Explicit ice maker product type",
            "core_appliance"
        )

    if "freezer" in text:
        if "upright freezer" in text:
            sub = "Upright Freezers"
        elif "chest freezer" in text:
            sub = "Chest Freezers"
        else:
            sub = "Freezers"

        return (
            "Refrigeration",
            sub,
            "mapped",
            "high",
            "product_url_slug + item_name",
            "Explicit freezer product type",
            "core_appliance"
        )

    if "refrigerator" in text or "fridge" in text:
        if "side-by-side" in text or "side by side" in text:
            sub = "Side-by-Side Refrigerators"
        elif "french door" in text:
            sub = "French Door Refrigerators"
        else:
            sub = "Refrigerators"

        return (
            "Refrigeration",
            sub,
            "mapped",
            "high",
            "product_url_slug + item_name",
            "Explicit refrigerator product type",
            "core_appliance"
        )


    # --------------------------------------------------------
    # LAUNDRY
    # --------------------------------------------------------

    if "dish washer" in text or "dishwasher" in text:
        return (
            "Laundry",
            "Dishwashers",
            "mapped",
            "high",
            "product_url_slug + item_name",
            "Explicit dishwasher product type",
            "core_appliance"
        )

    if "dryer" in text and "air conditioner" not in text:
        if "heat pump" in text:
            sub = "Heat Pump Dryers"
        elif "vented" in text:
            sub = "Vented Dryers"
        else:
            sub = "Clothes Dryers"

        return (
            "Laundry",
            sub,
            "mapped",
            "high",
            "product_url_slug + item_name",
            "Explicit dryer product type",
            "core_appliance"
        )

    if "washing machine" in text or "washer dryer" in text:
        if "washer dryer combo" in text:
            sub = "Washer-Dryer Combos"
        elif "front load" in text:
            sub = "Front Load Washing Machines"
        elif "top load" in text:
            sub = "Top Load Washing Machines"
        elif "twin tub" in text:
            sub = "Twin Tub Washing Machines"
        elif "single tub" in text:
            sub = "Single Tub Washing Machines"
        else:
            sub = "Washing Machines"

        return (
            "Laundry",
            sub,
            "mapped",
            "high",
            "product_url_slug + item_name",
            "Explicit washing machine product type",
            "core_appliance"
        )

    if "iron" in text:
        if "steam iron" in text:
            sub = "Steam Irons"
        else:
            sub = "Dry Irons"

        return (
            "Laundry",
            sub,
            "mapped",
            "high",
            "product_url_slug + item_name",
            "Explicit iron product type",
            "core_appliance"
        )

    # IMPORTANT:
    # Nano steamers are beauty/personal-care products, not laundry
    # garment steamers.
    if "garment steamer" in text:
        return (
            "Laundry",
            "Garment Steamers",
            "mapped",
            "high",
            "product_url_slug + item_name",
            "Explicit garment steamer product type",
            "core_appliance"
        )


    # --------------------------------------------------------
    # BEAUTY & PERSONAL CARE
    # --------------------------------------------------------

    if "nano steamer" in text:
        if "aromatherapy" in text or "cotton pad" in text:
            sub = "Garment Steamer Accessories"
            reason = "Nano steamer accessory identified from item name"
            scope = "beauty_personal_care"
            confidence = "medium"
        elif "facial" in text:
            sub = "Facial Steamers / Beauty Accessories"
            reason = "Facial nano steamer identified from item name"
            scope = "beauty_personal_care"
            confidence = "medium"
        else:
            sub = "Beauty Steamers"
            reason = "Nano steamer associated with Beauty & Personal Care"
            scope = "beauty_personal_care"
            confidence = "medium"

        return (
            "Beauty & Personal Care",
            sub,
            "mapped",
            confidence,
            "product_url_slug + item_name",
            reason,
            scope
        )


    # --------------------------------------------------------
    # AIR & CLIMATE
    # --------------------------------------------------------

    if "air conditioner" in text:
        return (
            "Air & Climate",
            "Air Conditioners",
            "mapped",
            "high",
            "product_url_slug + item_name",
            "Explicit air conditioner product type",
            "core_appliance"
        )

    if "fan" in text and "fan heater" not in text:
        return (
            "Air & Climate",
            "Fans",
            "mapped",
            "high",
            "product_url_slug + item_name",
            "Explicit fan product type",
            "core_appliance"
        )

    if "heater" in text:
        return (
            "Air & Climate",
            "Heaters",
            "mapped",
            "high",
            "product_url_slug + item_name",
            "Explicit heater product type",
            "core_appliance"
        )


    # --------------------------------------------------------
    # TV & AUDIO
    # --------------------------------------------------------

    if (
        "smart tv" in text
        or "led colour tv" in text
        or "/product/tv-" in url.lower()
        or "tv 4k" in text
    ):
        return (
            "TV & Audio",
            "Televisions",
            "mapped",
            "high",
            "product_url_slug + item_name",
            "Explicit television product type",
            "core_appliance"
        )


    # --------------------------------------------------------
    # WATER
    # --------------------------------------------------------

    if "water" in text and "dispenser" in text:
        return (
            "Water",
            "Water Dispensers",
            "mapped",
            "high",
            "product_url_slug + item_name",
            "Explicit water dispenser product type",
            "core_appliance"
        )


    # --------------------------------------------------------
    # COOKING
    # --------------------------------------------------------

    if "standing cooker" in text:
        return (
            "Cooking",
            "Standing Cookers",
            "mapped",
            "high",
            "product_url_slug + item_name",
            "Explicit standing cooker product type",
            "core_appliance"
        )

    if "gas stove" in text:
        return (
            "Cooking",
            "Gas Stoves",
            "mapped",
            "high",
            "product_url_slug + item_name",
            "Explicit gas stove product type",
            "core_appliance"
        )

    # Explicit tabletop/double-burner classification
    if (
        "table top" in text
        and ("burner" in text or "burners" in text)
    ):
        return (
            "Cooking",
            "Tabletop Gas Stoves",
            "mapped",
            "high",
            "product_url_slug + item_name",
            "Explicit tabletop burner cooking product",
            "core_appliance"
        )

    if "gas hob" in text:
        return (
            "Cooking",
            "Gas Hobs",
            "mapped",
            "high",
            "product_url_slug + item_name",
            "Explicit gas hob product type",
            "core_appliance"
        )

    if "built-in oven" in text or "built in oven" in text:
        return (
            "Cooking",
            "Built-in Ovens",
            "mapped",
            "high",
            "product_url_slug + item_name",
            "Explicit built-in oven product type",
            "core_appliance"
        )

    if "built-in microwave" in text or "built in microwave" in text:
        return (
            "Cooking",
            "Built-in Microwaves",
            "mapped",
            "high",
            "product_url_slug + item_name",
            "Explicit built-in microwave product type",
            "core_appliance"
        )

    if "microwave" in text:
        return (
            "Small Kitchen Appliances",
            "Microwaves",
            "mapped",
            "high",
            "product_url_slug + item_name",
            "Explicit standard/countertop microwave product type",
            "core_appliance"
        )

    if "vitro" in text or "ceramic hob" in text:
        return (
            "Cooking",
            "Vitro Ceramic Hobs",
            "mapped",
            "high",
            "product_url_slug + item_name",
            "Explicit vitro/ceramic cooking product",
            "core_appliance"
        )

    if "chimney hood" in text or "cooker hood" in text:
        return (
            "Cooking",
            "Cooker Hoods",
            "mapped",
            "high",
            "product_url_slug + item_name",
            "Explicit cooker hood product type",
            "core_appliance"
        )

    if "pressure cooker" in text:
        return (
            "Cooking",
            "Pressure Cookers",
            "mapped",
            "high",
            "product_url_slug + item_name",
            "Explicit pressure cooker product type",
            "core_appliance"
        )

    if "genie cooker" in text:
        return (
            "Cooking",
            "Genie Cookers",
            "mapped",
            "high",
            "product_url_slug + item_name",
            "Explicit genie cooker product type",
            "core_appliance"
        )


    # --------------------------------------------------------
    # SMALL KITCHEN APPLIANCES
    # --------------------------------------------------------

    if "air fryer" in text or "air frier" in text:
        return (
            "Small Kitchen Appliances",
            "Air Fryers",
            "mapped",
            "high",
            "product_url_slug + item_name",
            "Explicit air fryer product type",
            "core_appliance"
        )

    if "blender" in text:
        return (
            "Small Kitchen Appliances",
            "Blenders",
            "mapped",
            "high",
            "product_url_slug + item_name",
            "Explicit blender product type",
            "core_appliance"
        )

    if "juicer" in text:
        if "citrus" in text:
            sub = "Citrus Juicers"
        elif "slow juicer" in text:
            sub = "Slow Juicers"
        else:
            sub = "Juicers"

        return (
            "Small Kitchen Appliances",
            sub,
            "mapped",
            "high",
            "product_url_slug + item_name",
            "Explicit juicer product type",
            "core_appliance"
        )

    if "kettle" in text:
        return (
            "Small Kitchen Appliances",
            "Kettles",
            "mapped",
            "high",
            "product_url_slug + item_name",
            "Explicit kettle product type",
            "core_appliance"
        )

    if "hand mixer" in text:
        return (
            "Small Kitchen Appliances",
            "Hand Mixers",
            "mapped",
            "high",
            "product_url_slug + item_name",
            "Explicit hand mixer product type",
            "core_appliance"
        )

    if "stand mixer" in text:
        return (
            "Small Kitchen Appliances",
            "Stand Mixers",
            "mapped",
            "high",
            "product_url_slug + item_name",
            "Explicit stand mixer product type",
            "core_appliance"
        )

    if "food processor" in text:
        return (
            "Small Kitchen Appliances",
            "Food Processors",
            "mapped",
            "high",
            "product_url_slug + item_name",
            "Explicit food processor product type",
            "core_appliance"
        )

    if "salad maker" in text:
        return (
            "Small Kitchen Appliances",
            "Salad Makers",
            "mapped",
            "high",
            "product_url_slug + item_name",
            "Explicit salad maker product type",
            "core_appliance"
        )

    if "sandwich maker" in text:
        return (
            "Small Kitchen Appliances",
            "Sandwich Makers",
            "mapped",
            "high",
            "product_url_slug + item_name",
            "Explicit sandwich maker product type",
            "core_appliance"
        )

    if "toaster" in text:
        return (
            "Small Kitchen Appliances",
            "Toasters",
            "mapped",
            "high",
            "product_url_slug + item_name",
            "Explicit toaster product type",
            "core_appliance"
        )

    if "nutriblast" in text or "nutri blast" in text:
        return (
            "Small Kitchen Appliances",
            "Nutri Blenders",
            "mapped",
            "high",
            "product_url_slug + item_name",
            "Explicit Nutri Blast product type",
            "core_appliance"
        )

    if "chopper" in text:
        return (
            "Small Kitchen Appliances",
            "Food Choppers",
            "mapped",
            "high",
            "product_url_slug + item_name",
            "Explicit food chopper product type",
            "core_appliance"
        )

    if "citrus juicer" in text:
        return (
            "Small Kitchen Appliances",
            "Citrus Juicers",
            "mapped",
            "high",
            "product_url_slug + item_name",
            "Explicit citrus juicer product type",
            "core_appliance"
        )

    # ... existing Nano Steamer rules ...

    # Generic Nano Ionic Steamer:
    # Beauty/personal-care product, not garment care.
    if "nano ionic steamer" in text:
        return (
            "Beauty & Personal Care",
            "Beauty Steamers",
            "mapped",
            "medium",
            "product_url_slug + item_name",
            "Nano ionic steamer is a beauty/personal-care product",
            "beauty_personal_care"
        )


    # MMTR21 / marinator:
    # It is food-preparation equipment, not cookware.
    if "marinator" in text:
        return (
            "Small Kitchen Appliances",
            "Food Preparation",
            "mapped",
            "high",
            "product_url_slug + item_name",
            "Food-preparation appliance/equipment",
            "core_appliance"
        )


    # --------------------------------------------------------
    # HOME CARE & POWER
    # --------------------------------------------------------

    if (
        "power protector" in text
        or "power protection" in text
        or "volt protector" in text
        or "avs-" in text
        or "multi-guard" in text
        or "extension plug" in text
    ):
        return (
            "Home Care & Power",
            "Power Protection",
            "mapped",
            "high",
            "product_url_slug + item_name",
            "Explicit power protection product",
            "core_appliance"
        )


    # --------------------------------------------------------
    # ACCESSORIES
    # --------------------------------------------------------

    if "cup holder" in text:
        return (
            "Multi-category",
            "Accessories",
            "mapped",
            "high",
            "product_url_slug + item_name",
            "Accessory rather than core appliance",
            "accessory"
        )

    if "lpg gas pipe" in text or "gas pipe" in text:
        return (
            "Cooking",
            "Gas Accessories",
            "mapped",
            "high",
            "product_url_slug + item_name",
            "Cooking-related gas accessory",
            "accessory"
        )

    if "bracket" in text:
        return (
            "Air & Climate",
            "Air Conditioner Accessories",
            "mapped",
            "medium",
            "product_url_slug + item_name",
            "Air-conditioner accessory",
            "accessory"
        )


    # --------------------------------------------------------
    # REVIEW
    # --------------------------------------------------------

    return (
        "REVIEW",
        "REVIEW",
        "review",
        "low",
        "unresolved",
        "No sufficiently explicit product-type evidence",
        "other"
    )


# ------------------------------------------------------------
# BUILD PREVIEW
# ------------------------------------------------------------

preview = []

for row in rows:

    (
        category,
        sub_category,
        status,
        confidence,
        source,
        reason,
        product_scope
    ) = assign(row)

    out = dict(row)

    # We do not invent a first-party raw category.
    out["raw_category"] = ""

    out["category"] = category
    out["sub_category"] = sub_category
    out["mapping_status"] = status
    out["mapping_confidence"] = confidence
    out["inferred_category_source"] = source
    out["mapping_reason"] = reason
    out["product_scope"] = product_scope

    preview.append(out)


# ------------------------------------------------------------
# WRITE MAIN PREVIEW
# ------------------------------------------------------------

fields = [
    "brand",
    "item_name",
    "model_no",
    "raw_category",
    "category",
    "sub_category",
    "mapping_status",
    "mapping_confidence",
    "inferred_category_source",
    "mapping_reason",
    "product_scope",
    "image_url",
    "product_url",
    "warranty_period",
    "source",
    "extracted_date",
]

with PREVIEW_CSV.open("w", encoding="utf-8-sig", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=fields)
    writer.writeheader()
    writer.writerows(preview)


# ------------------------------------------------------------
# CATEGORY DISTRIBUTION
# ------------------------------------------------------------

category_counts = Counter(r["category"] for r in preview)

with CATEGORY_CSV.open("w", encoding="utf-8-sig", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["category", "product_count"])

    for category, count in category_counts.most_common():
        writer.writerow([category, count])


# ------------------------------------------------------------
# SUBCATEGORY DISTRIBUTION
# ------------------------------------------------------------

subcategory_counts = Counter(
    (r["category"], r["sub_category"])
    for r in preview
)

with SUBCATEGORY_CSV.open("w", encoding="utf-8-sig", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["category", "sub_category", "product_count"])

    for (category, subcategory), count in subcategory_counts.most_common():
        writer.writerow([category, subcategory, count])


# ------------------------------------------------------------
# REVIEW ROWS
# ------------------------------------------------------------

review_rows = [
    r for r in preview
    if r["mapping_status"] == "review"
]

with REVIEW_CSV.open("w", encoding="utf-8-sig", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=fields)
    writer.writeheader()
    writer.writerows(review_rows)


# ------------------------------------------------------------
# SUSPICIOUS MAPPINGS
# ------------------------------------------------------------

suspicious = []

for r in preview:

    text = text_for(r)

    reasons = []

    if r["category"] == "REVIEW":
        reasons.append("Unresolved")

    if r["mapping_confidence"] != "high":
        reasons.append("Confidence below high")

    if r["product_scope"] == "accessory":
        reasons.append("Accessory/non-core item")

    if r["product_scope"] == "beauty_personal_care":
        reasons.append("Beauty/personal-care item outside core appliance taxonomy")

    if (
        r["category"] == "Multi-category"
        and r["product_scope"] != "accessory"
    ):
        reasons.append("Multi-category classification")

    if reasons:
        item = dict(r)
        item["suspicion_reason"] = "; ".join(reasons)
        suspicious.append(item)


with SUSPICIOUS_CSV.open("w", encoding="utf-8-sig", newline="") as f:
    writer = csv.DictWriter(
        f,
        fieldnames=fields + ["suspicion_reason"]
    )
    writer.writeheader()
    writer.writerows(suspicious)


# ------------------------------------------------------------
# CONSOLE SUMMARY
# ------------------------------------------------------------

print()
print("=" * 80)
print("MIKA CATALOGUE MAPPING PREVIEW")
print("=" * 80)

print()
print("Total products:", len(preview))
print("Mapped:", sum(r["mapping_status"] == "mapped" for r in preview))
print("Review:", sum(r["mapping_status"] == "review" for r in preview))

print()
print("CATEGORY DISTRIBUTION")
print("-" * 80)

for category, count in category_counts.most_common():
    print(f"{count:>4} | {category}")

print()
print("CONFIDENCE")
print("-" * 80)

confidence_counts = Counter(
    r["mapping_confidence"] for r in preview
)

for confidence, count in confidence_counts.most_common():
    print(f"{count:>4} | {confidence}")

print()
print("PRODUCT SCOPE")
print("-" * 80)

scope_counts = Counter(
    r["product_scope"] for r in preview
)

for scope, count in scope_counts.most_common():
    print(f"{count:>4} | {scope}")

print()
print("FILES CREATED")
print("-" * 80)
print(PREVIEW_CSV)
print(CATEGORY_CSV)
print(SUBCATEGORY_CSV)
print(REVIEW_CSV)
print(SUSPICIOUS_CSV)

print()
print("DATABASE STATUS: UNCHANGED")
