import csv
from pathlib import Path
from collections import defaultdict

BASE = Path(__file__).resolve().parent
INPUT_DIR = BASE / "reports" / "mika_catalogue_preview" / "mika_position"
OUTPUT_DIR = INPUT_DIR / "product_gap_analysis"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

INPUT_FILE = INPUT_DIR / "subcategory_coverage.csv"

if not INPUT_FILE.exists():
    raise SystemExit(f"INPUT NOT FOUND: {INPUT_FILE}")

with INPUT_FILE.open("r", encoding="utf-8-sig", newline="") as f:
    rows = list(csv.DictReader(f))

if not rows:
    raise SystemExit("No rows found in subcategory_coverage.csv")

# Detect the actual column names without making assumptions about ordering.
fields = rows[0].keys()

required = {"category", "sub_category"}
missing = required - set(fields)
if missing:
    raise SystemExit(
        f"Missing required columns: {sorted(missing)}\n"
        f"Available columns: {list(fields)}"
    )

# Identify brand count columns.
brand_columns = {}
for field in fields:
    upper = field.upper()
    if upper in {"MIKA", "BRUHM", "HAIER"}:
        brand_columns[upper] = field

for brand in ("MIKA", "BRUHM", "HAIER"):
    if brand not in brand_columns:
        raise SystemExit(
            f"Missing brand column for {brand}. Available columns: {list(fields)}"
        )

analysis_rows = []

for row in rows:
    category = (row.get("category") or "").strip()
    subcategory = (row.get("sub_category") or "").strip()

    def count(brand):
        value = row.get(brand_columns[brand], "")
        try:
            return int(float(value))
        except (ValueError, TypeError):
            return 0

    mika = count("MIKA")
    bruhm = count("BRUHM")
    haier = count("HAIER")

    competitor_total = bruhm + haier

    if mika > 0 and competitor_total > 0:
        coverage_status = "SHARED"
    elif mika > 0 and competitor_total == 0:
        coverage_status = "MIKA_ONLY"
    elif mika == 0 and competitor_total > 0:
        coverage_status = "COMPETITOR_ONLY"
    else:
        coverage_status = "NO_COVERAGE"

    if coverage_status == "SHARED":
        if mika > competitor_total:
            breadth_signal = "MIKA_CATALOGUE_BREADTH_HIGHER"
        elif mika < competitor_total:
            breadth_signal = "COMPETITOR_CATALOGUE_BREADTH_HIGHER"
        else:
            breadth_signal = "SIMILAR_CATALOGUE_BREADTH"
    elif coverage_status == "MIKA_ONLY":
        breadth_signal = "MIKA_UNIQUE_COVERAGE"
    elif coverage_status == "COMPETITOR_ONLY":
        breadth_signal = "COMPETITOR_COVERAGE_NOT_IN_MIKA_CATALOGUE"
    else:
        breadth_signal = "NO_COVERAGE"

    analysis_rows.append({
        "category": category,
        "sub_category": subcategory,
        "mika_products": mika,
        "bruhm_products": bruhm,
        "haier_products": haier,
        "competitor_products": competitor_total,
        "coverage_status": coverage_status,
        "breadth_signal": breadth_signal,
        "assessment_status": (
            "VALIDATE_BEFORE_GAP_CLAIM"
            if coverage_status in {"MIKA_ONLY", "COMPETITOR_ONLY"}
            else "COMPARABLE_COVERAGE"
        ),
    })

# Sort for readability.
analysis_rows.sort(
    key=lambda r: (
        r["category"],
        r["coverage_status"],
        -r["competitor_products"],
        -r["mika_products"],
        r["sub_category"],
    )
)

# Main analysis.
main_file = OUTPUT_DIR / "product_type_gap_analysis.csv"

fieldnames = [
    "category",
    "sub_category",
    "mika_products",
    "bruhm_products",
    "haier_products",
    "competitor_products",
    "coverage_status",
    "breadth_signal",
    "assessment_status",
]

with main_file.open("w", encoding="utf-8", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(analysis_rows)

# Separate outputs.
def write_subset(filename, predicate):
    subset = [r for r in analysis_rows if predicate(r)]
    path = OUTPUT_DIR / filename

    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(subset)

    return len(subset)

shared_count = write_subset(
    "shared_product_types.csv",
    lambda r: r["coverage_status"] == "SHARED",
)

mika_only_count = write_subset(
    "mika_only_product_types.csv",
    lambda r: r["coverage_status"] == "MIKA_ONLY",
)

competitor_only_count = write_subset(
    "competitor_only_product_types.csv",
    lambda r: r["coverage_status"] == "COMPETITOR_ONLY",
)

# Shared product types where competitor catalogue breadth is higher.
competitor_breadth_count = write_subset(
    "shared_where_competitor_breadth_higher.csv",
    lambda r: (
        r["coverage_status"] == "SHARED"
        and r["breadth_signal"] == "COMPETITOR_CATALOGUE_BREADTH_HIGHER"
    ),
)

# Shared product types where MIKA catalogue breadth is higher.
mika_breadth_count = write_subset(
    "shared_where_mika_breadth_higher.csv",
    lambda r: (
        r["coverage_status"] == "SHARED"
        and r["breadth_signal"] == "MIKA_CATALOGUE_BREADTH_HIGHER"
    ),
)

# Shared product types with approximately equal catalogue breadth.
similar_count = write_subset(
    "shared_with_similar_breadth.csv",
    lambda r: (
        r["coverage_status"] == "SHARED"
        and r["breadth_signal"] == "SIMILAR_CATALOGUE_BREADTH"
    ),
)

# Category-level summary.
category_data = defaultdict(
    lambda: {
        "mika": 0,
        "bruhm": 0,
        "haier": 0,
        "shared": 0,
        "mika_only": 0,
        "competitor_only": 0,
    }
)

for row in analysis_rows:
    cat = row["category"]

    category_data[cat]["mika"] += row["mika_products"]
    category_data[cat]["bruhm"] += row["bruhm_products"]
    category_data[cat]["haier"] += row["haier_products"]

    if row["coverage_status"] == "SHARED":
        category_data[cat]["shared"] += 1
    elif row["coverage_status"] == "MIKA_ONLY":
        category_data[cat]["mika_only"] += 1
    elif row["coverage_status"] == "COMPETITOR_ONLY":
        category_data[cat]["competitor_only"] += 1

category_rows = []

for category, values in sorted(category_data.items()):
    competitor_total = values["bruhm"] + values["haier"]

    if values["mika"] > 0 and competitor_total > 0:
        category_status = "SHARED"
    elif values["mika"] > 0:
        category_status = "MIKA_ONLY"
    else:
        category_status = "COMPETITOR_ONLY"

    category_rows.append({
        "category": category,
        "mika_products": values["mika"],
        "bruhm_products": values["bruhm"],
        "haier_products": values["haier"],
        "competitor_products": competitor_total,
        "shared_product_types": values["shared"],
        "mika_only_product_types": values["mika_only"],
        "competitor_only_product_types": values["competitor_only"],
        "category_coverage_status": category_status,
    })

category_file = OUTPUT_DIR / "category_gap_summary.csv"

category_fields = [
    "category",
    "mika_products",
    "bruhm_products",
    "haier_products",
    "competitor_products",
    "shared_product_types",
    "mika_only_product_types",
    "competitor_only_product_types",
    "category_coverage_status",
]

with category_file.open("w", encoding="utf-8", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=category_fields)
    writer.writeheader()
    writer.writerows(category_rows)

# Executive summary.
summary_file = OUTPUT_DIR / "gap_analysis_summary.txt"

with summary_file.open("w", encoding="utf-8") as f:
    f.write("MIKA PRODUCT-TYPE GAP ANALYSIS — PREVIEW\n")
    f.write("=" * 60 + "\n\n")

    f.write(f"Product-type rows analysed: {len(analysis_rows)}\n")
    f.write(f"Shared product types: {shared_count}\n")
    f.write(f"MIKA-only product types: {mika_only_count}\n")
    f.write(f"Competitor-only product types: {competitor_only_count}\n\n")

    f.write("SHARED PRODUCT-TYPE BREADTH\n")
    f.write("-" * 40 + "\n")
    f.write(f"Competitor catalogue breadth higher: {competitor_breadth_count}\n")
    f.write(f"MIKA catalogue breadth higher: {mika_breadth_count}\n")
    f.write(f"Similar catalogue breadth: {similar_count}\n\n")

    f.write("INTERPRETATION RULE\n")
    f.write("-" * 40 + "\n")
    f.write(
        "MIKA-only and competitor-only product types are catalogue coverage "
        "signals, not confirmed competitive gaps.\n"
    )
    f.write(
        "Before treating a competitor-only type as a genuine MIKA product gap, "
        "validate product architecture, naming differences, current availability, "
        "and commercial relevance.\n"
    )
    f.write(
        "This preview does not modify the SQLite database.\n"
    )

print("=" * 70)
print("MIKA PRODUCT-TYPE GAP ANALYSIS — PREVIEW")
print("=" * 70)
print(f"Input : {INPUT_FILE}")
print(f"Output: {OUTPUT_DIR}")
print()
print(f"Product-type rows analysed : {len(analysis_rows)}")
print(f"Shared product types       : {shared_count}")
print(f"MIKA-only product types    : {mika_only_count}")
print(f"Competitor-only types      : {competitor_only_count}")
print()
print("Shared breadth signals:")
print(f"  Competitor breadth higher: {competitor_breadth_count}")
print(f"  MIKA breadth higher      : {mika_breadth_count}")
print(f"  Similar breadth          : {similar_count}")
print()
print("DATABASE WRITES: NONE")
print("=" * 70)
