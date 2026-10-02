from pathlib import Path
import pandas as pd


# ============================================================
# MIKA CI - CROSS-BRAND CATALOGUE VALIDATION
# READ-ONLY
# ============================================================

BASE_DIR = Path(__file__).resolve().parent
REPORT_DIR = BASE_DIR / "reports" / "mika_catalogue_preview"

FILES = {
    "MIKA": REPORT_DIR / "mika_catalogue_preview.csv",
    "BRUHM": REPORT_DIR / "bruhm" / "bruhm_catalogue_preview.csv",
    "HAIER": REPORT_DIR / "HAIER" / "haier_catalogue_preview.csv",
}

OUTPUT_DIR = REPORT_DIR / "cross_brand_validation"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


EXPECTED_CATEGORIES = {
    "Refrigeration",
    "Laundry",
    "Cooking",
    "Small Kitchen Appliances",
    "TV & Audio",
    "Air & Climate",
    "Water",
    "Home Care & Power",
    "Beauty & Personal Care",
    "Multi-category",
    "REVIEW",
}


# ============================================================
# COLUMN NORMALIZATION
# ============================================================

COLUMN_ALIASES = {
    "brand": ["brand", "competitor"],
    "item_name": ["item_name", "product_name"],
    "model_no": ["model_no", "sku"],
    "raw_category": ["raw_category", "category"],
    "category": ["category"],
    "sub_category": ["sub_category"],
    "mapping_status": ["mapping_status"],
    "mapping_confidence": ["mapping_confidence"],
    "inferred_category_source": ["inferred_category_source"],
    "mapping_reason": ["mapping_reason"],
    "product_scope": ["product_scope"],
    "product_url": ["product_url", "url"],
}


REQUIRED_CANONICAL_COLUMNS = {
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
    "product_url",
}


def normalize_columns(df, expected_brand):
    """
    Convert brand-specific preview schemas into one common
    validation schema.

    IMPORTANT:
    This changes only the in-memory DataFrame.
    It does NOT modify any source CSV.
    """

    result = pd.DataFrame(index=df.index)

    for canonical, aliases in COLUMN_ALIASES.items():

        source_column = None

        for alias in aliases:
            if alias in df.columns:
                source_column = alias
                break

        if source_column is not None:
            result[canonical] = df[source_column].fillna("").astype(str)
        else:
            result[canonical] = ""

    # Use the known brand rather than trusting the source file.
    result["brand"] = expected_brand

    return result


# ============================================================
# LOAD
# ============================================================

frames = []

print("=" * 70)
print("MIKA CI - CROSS-BRAND CATALOGUE VALIDATION")
print("=" * 70)
print()

for brand, path in FILES.items():

    print(f"{brand}:")
    print(f"  File: {path}")

    if not path.exists():
        raise SystemExit(f"ERROR: File not found: {path}")

    raw_df = pd.read_csv(path, dtype=str).fillna("")

    print(f"  Source columns: {', '.join(raw_df.columns)}")
    print(f"  Products: {len(raw_df)}")

    df = normalize_columns(raw_df, brand)

    missing = [
        column
        for column in REQUIRED_CANONICAL_COLUMNS
        if column not in df.columns
    ]

    if missing:
        raise SystemExit(
            f"ERROR: {brand} could not be normalized: "
            + ", ".join(sorted(missing))
        )

    df["brand_validation"] = brand

    frames.append(df)

    print(f"  Normalized columns: {len(df.columns)}")
    print()


all_df = pd.concat(frames, ignore_index=True)


# ============================================================
# 1. BASIC VALIDATION
# ============================================================

print("=" * 70)
print("1. BASIC VALIDATION")
print("=" * 70)

basic_rows = []

for brand in FILES.keys():

    df = all_df[all_df["brand_validation"] == brand]

    basic_rows.append({
        "brand": brand,
        "products": len(df),
        "unique_model_numbers": df["model_no"]
            .replace("", pd.NA)
            .nunique(),
        "mapped": int(
            (df["mapping_status"].str.lower() == "mapped").sum()
        ),
        "review": int(
            (df["mapping_status"].str.lower() == "review").sum()
        ),
        "high_confidence": int(
            (df["mapping_confidence"].str.lower() == "high").sum()
        ),
        "medium_confidence": int(
            (df["mapping_confidence"].str.lower() == "medium").sum()
        ),
        "low_confidence": int(
            (df["mapping_confidence"].str.lower() == "low").sum()
        ),
        "core_appliance": int(
            (df["product_scope"].str.lower() == "core_appliance").sum()
        ),
    })

basic_df = pd.DataFrame(basic_rows)

print(basic_df.to_string(index=False))
print()


# ============================================================
# 2. CATEGORY DISTRIBUTION BY BRAND
# ============================================================

print("=" * 70)
print("2. CATEGORY DISTRIBUTION")
print("=" * 70)

category_df = (
    all_df
    .groupby(["category", "brand_validation"])
    .size()
    .unstack(fill_value=0)
    .reset_index()
    .rename(columns={"brand_validation": "category"})
)

# Rebuild cleanly to avoid ambiguity.
category_df = (
    all_df
    .pivot_table(
        index="category",
        columns="brand_validation",
        values="item_name",
        aggfunc="count",
        fill_value=0,
    )
    .reset_index()
)

for brand in FILES.keys():
    if brand not in category_df.columns:
        category_df[brand] = 0

category_df["TOTAL"] = category_df[
    list(FILES.keys())
].sum(axis=1)

category_df = category_df.sort_values(
    ["TOTAL", "category"],
    ascending=[False, True]
)

print(category_df.to_string(index=False))
print()


# ============================================================
# 3. UNEXPECTED CATEGORIES
# ============================================================

print("=" * 70)
print("3. UNEXPECTED CATEGORIES")
print("=" * 70)

unexpected_categories = sorted(
    set(all_df["category"].str.strip())
    - EXPECTED_CATEGORIES
    - {""}
)

if unexpected_categories:
    for category in unexpected_categories:
        count = int(
            (all_df["category"].str.strip() == category).sum()
        )
        print(f"  {count:3d} | {category}")
else:
    print("  None")

print()


# ============================================================
# 4. SUBCATEGORY DISTRIBUTION
# ============================================================

print("=" * 70)
print("4. SUBCATEGORY DISTRIBUTION")
print("=" * 70)

subcategory_df = (
    all_df
    .pivot_table(
        index=["category", "sub_category"],
        columns="brand_validation",
        values="item_name",
        aggfunc="count",
        fill_value=0,
    )
    .reset_index()
)

for brand in FILES.keys():
    if brand not in subcategory_df.columns:
        subcategory_df[brand] = 0

subcategory_df["TOTAL"] = subcategory_df[
    list(FILES.keys())
].sum(axis=1)

subcategory_df = subcategory_df.sort_values(
    ["category", "TOTAL", "sub_category"],
    ascending=[True, False, True]
)

print(subcategory_df.to_string(index=False))
print()


# ============================================================
# 5. SUBCATEGORY NAMING CHECK
# ============================================================

print("=" * 70)
print("5. POSSIBLE SUBCATEGORY NAMING INCONSISTENCIES")
print("=" * 70)

subcats = (
    all_df["sub_category"]
    .astype(str)
    .str.strip()
)

normalization_map = {
    "Fridges": "Refrigerators",
    "Single Door Fridges": "Single Door Refrigerators",
    "Double Door Fridges": "Double Door Refrigerators",
    "Chest Freezer": "Chest Freezers",
    "Air Conditioners / AC": "Air Conditioners",
    "Rice Cooker": "Rice Cookers",
    "Microwave Ovens": "Microwaves",
    "Dishwasher": "Dishwashers",
    "Blender": "Blenders",
    "Air Fryer": "Air Fryers",
    "TVs": "Televisions",
}

naming_rows = []

for actual in sorted(subcats.unique()):

    if not actual:
        continue

    canonical = normalization_map.get(actual, actual)

    if canonical != actual:
        naming_rows.append({
            "actual_subcategory": actual,
            "possible_canonical": canonical,
            "count": int((subcats == actual).sum()),
        })

naming_df = pd.DataFrame(naming_rows)

if naming_df.empty:
    print("  No obvious naming inconsistencies detected.")
else:
    print(naming_df.to_string(index=False))

print()


# ============================================================
# 6. CROSS-BRAND SUBCATEGORY COVERAGE
# ============================================================

print("=" * 70)
print("6. CROSS-BRAND SUBCATEGORY COVERAGE")
print("=" * 70)

coverage = (
    all_df
    .groupby(["category", "sub_category"])["brand_validation"]
    .agg(lambda x: ", ".join(sorted(set(x))))
    .reset_index(name="brands")
)

coverage["brand_count"] = coverage["brands"].apply(
    lambda x: len([v for v in x.split(", ") if v])
)

coverage = coverage.sort_values(
    ["category", "sub_category"]
)

print(coverage.to_string(index=False))
print()


# ============================================================
# 7. REVIEW / SUSPICIOUS ROWS
# ============================================================

print("=" * 70)
print("7. REVIEW / SUSPICIOUS ROWS")
print("=" * 70)

review_df = all_df[
    (all_df["mapping_status"].str.lower() == "review")
    | (all_df["mapping_confidence"].str.lower() != "high")
].copy()

if review_df.empty:
    print("  No review or non-high-confidence rows.")
else:
    columns = [
        "brand_validation",
        "item_name",
        "model_no",
        "raw_category",
        "category",
        "sub_category",
        "mapping_status",
        "mapping_confidence",
        "mapping_reason",
    ]

    print(review_df[columns].to_string(index=False))

print()


# ============================================================
# 8. MISSING REQUIRED MAPPING FIELDS
# ============================================================

print("=" * 70)
print("8. MISSING REQUIRED MAPPING FIELDS")
print("=" * 70)

required_mapping_fields = [
    "item_name",
    "model_no",
    "category",
    "sub_category",
    "mapping_status",
    "mapping_confidence",
]

missing_rows = []

for field in required_mapping_fields:

    mask = all_df[field].astype(str).str.strip() == ""

    missing_rows.append({
        "field": field,
        "missing_count": int(mask.sum()),
    })

missing_df = pd.DataFrame(missing_rows)

print(missing_df.to_string(index=False))
print()


# ============================================================
# 9. PRODUCT SCOPE
# ============================================================

print("=" * 70)
print("9. PRODUCT SCOPE")
print("=" * 70)

scope_df = (
    all_df
    .pivot_table(
        index="product_scope",
        columns="brand_validation",
        values="item_name",
        aggfunc="count",
        fill_value=0,
    )
    .reset_index()
)

for brand in FILES.keys():
    if brand not in scope_df.columns:
        scope_df[brand] = 0

print(scope_df.to_string(index=False))
print()


# ============================================================
# 10. DUPLICATE MODEL NUMBERS WITHIN EACH BRAND
# ============================================================

print("=" * 70)
print("10. DUPLICATE MODEL NUMBERS")
print("=" * 70)

duplicate_rows = []

for brand in FILES.keys():

    df = all_df[
        (all_df["brand_validation"] == brand)
        & (all_df["model_no"].str.strip() != "")
    ]

    duplicates = df[
        df["model_no"].duplicated(keep=False)
    ].sort_values("model_no")

    if duplicates.empty:
        print(f"{brand}: None")
    else:
        print(f"{brand}: {len(duplicates)} duplicate rows")

        for _, row in duplicates.iterrows():
            duplicate_rows.append({
                "brand": brand,
                "model_no": row["model_no"],
                "item_name": row["item_name"],
            })

print()

duplicates_df = pd.DataFrame(duplicate_rows)


# ============================================================
# 11. SAVE VALIDATION OUTPUTS
# ============================================================

basic_df.to_csv(
    OUTPUT_DIR / "brand_validation_summary.csv",
    index=False
)

category_df.to_csv(
    OUTPUT_DIR / "cross_brand_category_distribution.csv",
    index=False
)

subcategory_df.to_csv(
    OUTPUT_DIR / "cross_brand_subcategory_distribution.csv",
    index=False
)

coverage.to_csv(
    OUTPUT_DIR / "subcategory_brand_coverage.csv",
    index=False
)

naming_df.to_csv(
    OUTPUT_DIR / "subcategory_naming_review.csv",
    index=False
)

review_df.to_csv(
    OUTPUT_DIR / "review_rows.csv",
    index=False
)

missing_df.to_csv(
    OUTPUT_DIR / "missing_required_fields.csv",
    index=False
)

duplicates_df.to_csv(
    OUTPUT_DIR / "duplicate_model_numbers.csv",
    index=False
)


# ============================================================
# FINAL STATUS
# ============================================================

print("=" * 70)
print("=" * 70)
print("FINAL VALIDATION STATUS")
print("=" * 70)

# ------------------------------------------------------------
# Final validation distinguishes actual taxonomy issues from
# documented source-data limitations.
#
# mapping_status = "review" is a true taxonomy-review signal.
# Medium confidence is still a valid mapped classification.
# Missing source identifiers are not invented or treated as
# taxonomy failures.
# ------------------------------------------------------------

actual_review_count = int(
    (
        all_df["mapping_status"]
        .astype(str)
        .str.lower()
        == "review"
    ).sum()
)

medium_confidence_count = int(
    (
        all_df["mapping_confidence"]
        .astype(str)
        .str.lower()
        == "medium"
    ).sum()
)

missing_model_total = int(
    missing_df.loc[
        missing_df["field"] == "model_no",
        "missing_count"
    ].sum()
)

unexpected_count = len(unexpected_categories)
duplicate_count = len(duplicates_df)

print("Mapping review rows:", actual_review_count)
print("Mapped medium-confidence rows:", medium_confidence_count)
print("Missing source model identifiers:", missing_model_total)
print("Unexpected categories:", unexpected_count)
print("Duplicate model-number rows:", duplicate_count)

print()

if (
    unexpected_count == 0
    and actual_review_count == 0
    and duplicate_count == 0
):
    print("STATUS: PASS WITH DATA LIMITATIONS")

    if medium_confidence_count:
        print(
            f" - {medium_confidence_count} mapped rows have medium confidence; "
            "none are classified as review."
        )

    if missing_model_total:
        print(
            f" - {missing_model_total} model identifiers are unavailable "
            "from the source data; identifiers were not invented."
        )

else:
    print("STATUS: REVIEW REQUIRED")

    if unexpected_count:
        print(
            f" - Unexpected categories: {unexpected_count}"
        )

    if actual_review_count:
        print(
            f" - Actual mapping-review rows: {actual_review_count}"
        )

    if duplicate_count:
        print(
            f" - Duplicate model-number rows: {duplicate_count}"
        )

print()
print("OUTPUT DIRECTORY")
print(OUTPUT_DIR)

print()
print("DATABASE STATUS: UNCHANGED")
