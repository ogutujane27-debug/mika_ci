from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parent
BASE = ROOT / "reports" / "mika_catalogue_preview"
OUT = BASE / "mika_position"

OUT.mkdir(parents=True, exist_ok=True)

FILES = {
    "MIKA": BASE / "mika_catalogue_preview.csv",
    "BRUHM": BASE / "bruhm" / "bruhm_catalogue_preview.csv",
    "HAIER": BASE / "HAIER" / "haier_catalogue_preview.csv",
}

print("=" * 70)
print("MIKA CI - MIKA POSITION / PRODUCT COMPARISON PREVIEW")
print("=" * 70)
print()
print("DATABASE WRITES: DISABLED")
print()

frames = {}

for brand, path in FILES.items():
    if not path.exists():
        raise SystemExit(f"{brand} catalogue not found: {path}")

    df = pd.read_csv(path, dtype=str).fillna("")

    required = [
        "category",
        "sub_category",
        "mapping_status",
        "mapping_confidence",
        "product_scope",
    ]

    missing = [c for c in required if c not in df.columns]

    if missing:
        raise SystemExit(
            f"{brand} is missing required columns: {missing}"
        )

    df["brand"] = brand
    frames[brand] = df

    print(
        f"{brand:<8} | Products: {len(df):>3} | "
        f"Mapped: {(df['mapping_status'].str.lower() == 'mapped').sum():>3}"
    )

all_df = pd.concat(frames.values(), ignore_index=True)

# ------------------------------------------------------------
# 1. CATEGORY COVERAGE
# ------------------------------------------------------------

category = (
    all_df[
        ["brand", "category"]
    ]
    .query("category != ''")
    .groupby(["category", "brand"])
    .size()
    .unstack(fill_value=0)
    .reset_index()
)

for brand in FILES:
    if brand not in category.columns:
        category[brand] = 0

category["TOTAL"] = category[list(FILES)].sum(axis=1)

category = category[
    ["category", "BRUHM", "HAIER", "MIKA", "TOTAL"]
].sort_values(["TOTAL", "category"], ascending=[False, True])

category.to_csv(
    OUT / "category_coverage.csv",
    index=False
)

# ------------------------------------------------------------
# 2. SUBCATEGORY COVERAGE
# ------------------------------------------------------------

subcategory = (
    all_df[
        ["brand", "category", "sub_category"]
    ]
    .query("category != '' and sub_category != ''")
    .groupby(["category", "sub_category", "brand"])
    .size()
    .unstack(fill_value=0)
    .reset_index()
)

for brand in FILES:
    if brand not in subcategory.columns:
        subcategory[brand] = 0

subcategory["TOTAL"] = subcategory[list(FILES)].sum(axis=1)

subcategory = subcategory[
    ["category", "sub_category", "BRUHM", "HAIER", "MIKA", "TOTAL"]
].sort_values(
    ["category", "TOTAL", "sub_category"],
    ascending=[True, False, True]
)

subcategory.to_csv(
    OUT / "subcategory_coverage.csv",
    index=False
)

# ------------------------------------------------------------
# 3. MIKA VS COMPETITOR SUBCATEGORY POSITION
# ------------------------------------------------------------

position_rows = []

for _, row in subcategory.iterrows():
    mika = int(row["MIKA"])
    bruhm = int(row["BRUHM"])
    haier = int(row["HAIER"])

    competitors = bruhm + haier

    if mika > 0 and competitors > 0:
        position = "SHARED"
    elif mika > 0 and competitors == 0:
        position = "MIKA_ONLY"
    elif mika == 0 and competitors > 0:
        position = "COMPETITOR_ONLY"
    else:
        position = "NONE"

    position_rows.append({
        "category": row["category"],
        "sub_category": row["sub_category"],
        "MIKA": mika,
        "BRUHM": bruhm,
        "HAIER": haier,
        "competitor_total": competitors,
        "position": position,
    })

position_df = pd.DataFrame(position_rows)

position_df.to_csv(
    OUT / "mika_subcategory_position.csv",
    index=False
)

# ------------------------------------------------------------
# 4. MIKA-ONLY AREAS
# ------------------------------------------------------------

mika_only = position_df[
    position_df["position"] == "MIKA_ONLY"
].copy()

mika_only.to_csv(
    OUT / "mika_only_subcategories.csv",
    index=False
)

# ------------------------------------------------------------
# 5. COMPETITOR-ONLY AREAS
# ------------------------------------------------------------

competitor_only = position_df[
    position_df["position"] == "COMPETITOR_ONLY"
].copy()

competitor_only.to_csv(
    OUT / "competitor_only_subcategories.csv",
    index=False
)

# ------------------------------------------------------------
# 6. SHARED AREAS
# ------------------------------------------------------------

shared = position_df[
    position_df["position"] == "SHARED"
].copy()

shared.to_csv(
    OUT / "shared_subcategories.csv",
    index=False
)

# ------------------------------------------------------------
# 7. PRODUCT SCOPE
# ------------------------------------------------------------

scope = (
    all_df
    .groupby(["product_scope", "brand"])
    .size()
    .unstack(fill_value=0)
    .reset_index()
)

for brand in FILES:
    if brand not in scope.columns:
        scope[brand] = 0

scope.to_csv(
    OUT / "product_scope.csv",
    index=False
)

# ------------------------------------------------------------
# 8. MODEL / IDENTIFIER COVERAGE
#
# We do NOT claim that different brands' model numbers match.
# This section only measures availability of source identifiers.
# ------------------------------------------------------------

model_rows = []

for brand, df in frames.items():
    model_col = "model_no" if "model_no" in df.columns else "sku"

    identifiers = (
        df[model_col]
        .astype(str)
        .str.strip()
    )

    available = identifiers.ne("").sum()
    missing = identifiers.eq("").sum()
    unique = identifiers[identifiers.ne("")].nunique()

    model_rows.append({
        "brand": brand,
        "identifier_field": model_col,
        "products": len(df),
        "identifiers_available": int(available),
        "identifiers_missing": int(missing),
        "unique_identifiers": int(unique),
    })

model_coverage = pd.DataFrame(model_rows)

model_coverage.to_csv(
    OUT / "model_identifier_coverage.csv",
    index=False
)

# ------------------------------------------------------------
# 9. CATEGORY-LEVEL POSITION SUMMARY
# ------------------------------------------------------------

category_position = []

for _, row in category.iterrows():
    mika = int(row["MIKA"])
    competitors = int(row["BRUHM"]) + int(row["HAIER"])

    if mika > 0 and competitors > 0:
        position = "SHARED"
    elif mika > 0:
        position = "MIKA_ONLY"
    elif competitors > 0:
        position = "COMPETITOR_ONLY"
    else:
        position = "NONE"

    category_position.append({
        "category": row["category"],
        "MIKA": mika,
        "BRUHM": int(row["BRUHM"]),
        "HAIER": int(row["HAIER"]),
        "competitor_total": competitors,
        "position": position,
    })

category_position_df = pd.DataFrame(category_position)

category_position_df.to_csv(
    OUT / "mika_category_position.csv",
    index=False
)

# ------------------------------------------------------------
# 10. SUMMARY
# ------------------------------------------------------------

summary = {
    "MIKA_products": len(frames["MIKA"]),
    "BRUHM_products": len(frames["BRUHM"]),
    "HAIER_products": len(frames["HAIER"]),
    "total_products": len(all_df),
    "categories": int(all_df["category"].nunique()),
    "subcategories": int(
        all_df[
            ["category", "sub_category"]
        ]
        .drop_duplicates()
        .shape[0]
    ),
    "mika_only_subcategories": len(mika_only),
    "competitor_only_subcategories": len(competitor_only),
    "shared_subcategories": len(shared),
}

summary_df = pd.DataFrame(
    list(summary.items()),
    columns=["metric", "value"]
)

summary_df.to_csv(
    OUT / "comparison_summary.csv",
    index=False
)

# ------------------------------------------------------------
# CONSOLE REPORT
# ------------------------------------------------------------

print()
print("=" * 70)
print("CATEGORY POSITION")
print("=" * 70)
print(category_position_df.to_string(index=False))

print()
print("=" * 70)
print("MIKA-ONLY SUBCATEGORIES")
print("=" * 70)

if len(mika_only):
    print(
        mika_only[
            ["category", "sub_category", "MIKA"]
        ].to_string(index=False)
    )
else:
    print("None")

print()
print("=" * 70)
print("COMPETITOR-ONLY SUBCATEGORIES")
print("=" * 70)

if len(competitor_only):
    print(
        competitor_only[
            [
                "category",
                "sub_category",
                "BRUHM",
                "HAIER",
                "competitor_total",
            ]
        ].to_string(index=False)
    )
else:
    print("None")

print()
print("=" * 70)
print("SHARED SUBCATEGORY COUNT")
print("=" * 70)
print("Shared:", len(shared))
print("MIKA-only:", len(mika_only))
print("Competitor-only:", len(competitor_only))

print()
print("=" * 70)
print("MODEL / IDENTIFIER COVERAGE")
print("=" * 70)
print(model_coverage.to_string(index=False))

print()
print("=" * 70)
print("OUTPUT")
print("=" * 70)
print(OUT)

print()
print("DATABASE STATUS: UNCHANGED")
