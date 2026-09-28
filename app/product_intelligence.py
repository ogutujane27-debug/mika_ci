import re
import sqlite3

import product_price_movements as price_movements
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
    "CLIPSOMINUT",
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


def print_price_movements():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row

    rows = price_movements.load_price_observations(con)
    identities = price_movements.build_identities(rows)
    movements, ambiguous = price_movements.detect_movements(identities)

    print()
    print("PRICE MOVEMENTS")
    print("-" * 80)
    print(f"Price observations analysed: {len(rows)}")
    print(f"Identities analysed: {len(identities)}")
    print(f"Movement candidates: {len(movements)}")
    print(f"Ambiguous same-day identity cases: {len(ambiguous)}")

    for index, item in enumerate(movements, 1):
        print()
        print(f"{index}. {item['brand']} | {item['model']}")
        print(f"   Product: {item['product_name']}")
        print(f"   Category: {item['category']}")
        print(f"   Previous: KSh {item['previous_price']:,.2f} ({item['previous_date']})")
        print(f"   Current:  KSh {item['current_price']:,.2f} ({item['current_date']})")
        print(f"   Change: {item['change']:+,.2f} KSh ({item['percentage']:+.2f}%)")
        print("   Status: PRICE MOVEMENT CANDIDATE")
        print("   Confidence: HIGH")

    con.close()

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
            print(f"  prices       : {", ".join(f"{p:,.0f}" for p in prices)}")
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
    print_price_movements()
    print("AUDIT COMPLETE - NO DATABASE WRITES")
    print("=" * 80)


if __name__ == "__main__":
    main()



