import sqlite3
from collections import Counter
from pathlib import Path

import product_price_movements as price_movements


DB_PATH = Path(__file__).resolve().parent.parent / "data" / "mika_competitive_intel.db"


def main():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row

    rows = price_movements.load_price_observations(con)
    identities = price_movements.build_identities(rows)
    movements, ambiguous = price_movements.detect_movements(identities)

    print("=" * 80)
    print("MIKA CI - PHASE 2F PRICE TREND SIGNAL AUDIT")
    print("=" * 80)
    print("Database writes: DISABLED")

    print()
    print("BASE DATA")
    print("-" * 80)
    print(f"Price observations: {len(rows)}")
    print(f"Product identities: {len(identities)}")
    print(f"Movement candidates: {len(movements)}")
    print(f"Ambiguous same-day cases: {len(ambiguous)}")

    print()
    print("MOVEMENTS BY BRAND")
    print("-" * 80)

    brand_counts = Counter(item["brand"] for item in movements)

    if brand_counts:
        for brand, count in sorted(brand_counts.items()):
            print(f"{brand}: {count}")
    else:
        print("No movement candidates.")

    print()
    print("MOVEMENTS BY CATEGORY")
    print("-" * 80)

    category_counts = Counter(item["category"] for item in movements)

    if category_counts:
        for category, count in sorted(category_counts.items()):
            print(f"{category}: {count}")
    else:
        print("No movement candidates.")

    print()
    print("MOVEMENT DIRECTION")
    print("-" * 80)

    increases = [
        item for item in movements
        if item["change"] > 0
    ]

    decreases = [
        item for item in movements
        if item["change"] < 0
    ]

    print(f"Price increases: {len(increases)}")
    print(f"Price decreases: {len(decreases)}")

    print()
    print("SIGNIFICANT MOVEMENTS")
    print("-" * 80)

    for index, item in enumerate(
        sorted(
            movements,
            key=lambda x: abs(x["percentage"]),
            reverse=True,
        ),
        1,
    ):
        direction = "INCREASE" if item["change"] > 0 else "DECREASE"

        print()
        print(f"{index}. {item['brand']} | {item['model']}")
        print(f"   Product: {item['product_name']}")
        print(f"   Category: {item['category']}")
        print(f"   Direction: {direction}")
        print(
            f"   Previous: KSh {item['previous_price']:,.2f} "
            f"({item['previous_date']})"
        )
        print(
            f"   Current:  KSh {item['current_price']:,.2f} "
            f"({item['current_date']})"
        )
        print(
            f"   Change: {item['change']:+,.2f} KSh "
            f"({item['percentage']:+.2f}%)"
        )

    print()
    print("=" * 80)
    print("PRICE TREND SIGNAL READINESS")
    print("=" * 80)

    if movements:
        print("Price movement signal: AVAILABLE")
    else:
        print("Price movement signal: NOT AVAILABLE")

    if len(movements) >= 2:
        print("Multi-product movement signal: AVAILABLE")
    else:
        print("Multi-product movement signal: NOT YET ESTABLISHED")

    if category_counts:
        repeated_categories = [
            category
            for category, count in category_counts.items()
            if count >= 2
        ]

        if repeated_categories:
            print(
                "Repeated category movement: AVAILABLE"
            )
        else:
            print(
                "Repeated category movement: NOT YET ESTABLISHED"
            )
    else:
        print(
            "Repeated category movement: NOT YET ESTABLISHED"
        )

    print()
    print("Audit complete. No database writes were performed.")

    con.close()


if __name__ == "__main__":
    main()