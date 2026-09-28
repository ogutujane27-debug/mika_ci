import re
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "mika_competitive_intel.db"


WEAK_MODELS = {
    "",
    "N/A",
    "NA",
    "NONE",
    "UNKNOWN",
    "SAMSUNG",
    "TEFAL",
    "SCL",
}


def normalize_text(value):
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value).strip())


def model_quality(model):
    value = normalize_text(model)

    if not value:
        return "missing"

    upper = value.upper()

    if upper in WEAK_MODELS:
        return "weak"

    if len(value) < 4:
        return "weak"

    if re.fullmatch(r"\d+(\.\d+)?\s*(W|KW|L|KG|CM|MM|INCH|INCHES)?", upper):
        return "weak"

    if re.fullmatch(r"\d+(\.\d+)?\s*(L|KG)", upper):
        return "weak"

    return "reliable"


def product_identity(source_competitor, brand, category, product_name, model):
    source = normalize_text(source_competitor)
    brand = normalize_text(brand)
    category = normalize_text(category)
    product = normalize_text(product_name)
    model = normalize_text(model)

    quality = model_quality(model)

    if quality == "reliable":
        identity = " | ".join(
            part.upper()
            for part in (source, brand, model)
            if part
        )
    else:
        identity = " | ".join(
            part.upper()
            for part in (source, brand, category, product)
            if part
        )

    return identity, quality


def load_price_observations():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row

    rows = con.execute(
        """
        SELECT
            p.observation_id,
            p.finding_id,
            p.product_name,
            p.model,
            p.price_kes,
            p.promotion_note,
            p.observed_date,
            f.competitor_id,
            c.brand_name AS source_competitor,
            f.brand,
            f.category,
            f.source_url
        FROM price_observations p
        JOIN findings f
            ON f.finding_id = p.finding_id
        JOIN competitors c
            ON c.competitor_id = f.competitor_id
        ORDER BY
            p.observed_date,
            p.observation_id
        """
    ).fetchall()

    con.close()
    return rows


def main():
    rows = load_price_observations()

    print("=" * 80)
    print("MIKA CI - PHASE 2D PRODUCT IDENTITY AUDIT")
    print("=" * 80)
    print(f"Database: {DB_PATH}")
    print(f"Price observations: {len(rows)}")
    print()

    quality_counts = {
        "reliable": 0,
        "weak": 0,
        "missing": 0,
    }

    identities = {}

    for row in rows:
        identity, quality = product_identity(
            row["source_competitor"],
            row["brand"],
            row["category"],
            row["product_name"],
            row["model"],
        )

        quality_counts[quality] += 1

        identities.setdefault(identity, []).append(row)

    print("MODEL QUALITY")
    print("-" * 80)
    for key in ("reliable", "weak", "missing"):
        print(f"{key:10} {quality_counts[key]}")
    print()

    repeated = [
        (identity, items)
        for identity, items in identities.items()
        if len(items) > 1
    ]

    print(f"Resolved identities: {len(identities)}")
    print(f"Repeated identities: {len(repeated)}")
    print()

    print("IDENTITIES WITH MULTIPLE OBSERVATIONS")
    print("-" * 80)

    shown = 0

    for identity, items in repeated:
        prices = sorted(
            {
                float(row["price_kes"])
                for row in items
                if row["price_kes"] is not None
            }
        )

        dates = sorted(
            {
                row["observed_date"]
                for row in items
            }
        )

        if len(prices) > 1:
            print()
            print(identity)
            print(f"  observations : {len(items)}")
            print(f"  dates        : {', '.join(dates)}")
            print(f"  prices       : {', '.join(f'{p:,.0f}' for p in prices)}")

            for row in items:
                print(
                    f"    {row['observed_date']} | "
                    f"{row['price_kes']:,.0f} | "
                    f"{row['product_name']} | "
                    f"model={row['model']}"
                )

            shown += 1

            if shown >= 30:
                break

    print()
    print("=" * 80)
    print("AUDIT COMPLETE - NO DATABASE WRITES")
    print("=" * 80)


if __name__ == "__main__":
    main()
