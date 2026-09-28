import sqlite3
from collections import Counter
from pathlib import Path


DB_PATH = Path(__file__).resolve().parent.parent / "data" / "mika_competitive_intel.db"


CATALOGUES = [
    (
        "Bruhm",
        "bruhm_products",
        "sku",
        "product_name",
        "category",
        "product_url",
    ),
    (
        "Haier",
        "haier_products",
        "sku",
        "product_name",
        "category",
        "url",
    ),
    (
        "K-Elec",
        "k_elec_products",
        "product_key",
        "product_name",
        "category",
        "url",
    ),
]


def main():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row

    print("=" * 80)
    print("MIKA CI - PHASE 2F PRODUCT CATALOGUE TREND AUDIT")
    print("=" * 80)
    print("Database writes: DISABLED")

    total_products = 0
    total_new_after_baseline = 0

    for (
        competitor,
        table,
        identity_col,
        name_col,
        category_col,
        url_col,
    ) in CATALOGUES:

        print()
        print("=" * 80)
        print(competitor.upper())
        print("=" * 80)

        row = con.execute(
            f"""
            SELECT
                COUNT(*),
                COUNT(DISTINCT {identity_col}),
                MIN(first_seen_date),
                MAX(last_seen_date)
            FROM {table}
            """
        ).fetchone()

        product_count = row[0]
        unique_count = row[1]
        first_seen = row[2]
        last_seen = row[3]

        total_products += product_count

        print(f"Products stored: {product_count}")
        print(f"Unique identities: {unique_count}")
        print(f"First observed: {first_seen}")
        print(f"Last observed: {last_seen}")

        print()
        print("PRODUCTS BY FIRST-SEEN DATE")
        print("-" * 80)

        first_seen_rows = con.execute(
            f"""
            SELECT
                first_seen_date,
                COUNT(*)
            FROM {table}
            GROUP BY first_seen_date
            ORDER BY first_seen_date
            """
        ).fetchall()

        for date_value, count in first_seen_rows:
            print(f"{date_value}: {count}")

        print()
        print("PRODUCTS AFTER BASELINE")
        print("-" * 80)

        new_rows = con.execute(
            f"""
            SELECT
                {name_col},
                {category_col},
                first_seen_date,
                last_seen_date
            FROM {table}
            WHERE first_seen_date > '2026-09-22'
            ORDER BY first_seen_date, {name_col}
            """
        ).fetchall()

        print(f"Post-baseline products: {len(new_rows)}")

        for product in new_rows:
            print(
                f"{product[0]} | "
                f"{product[1]} | "
                f"first={product[2]} | "
                f"last={product[3]}"
            )

        total_new_after_baseline += len(new_rows)

        print()
        print("CATEGORY DISTRIBUTION")
        print("-" * 80)

        category_rows = con.execute(
            f"""
            SELECT
                COALESCE({category_col}, 'UNSPECIFIED'),
                COUNT(*)
            FROM {table}
            GROUP BY {category_col}
            ORDER BY COUNT(*) DESC
            """
        ).fetchall()

        for category, count in category_rows:
            print(f"{category}: {count}")

        print()
        print("REPEATEDLY OBSERVED PRODUCTS")
        print("-" * 80)

        repeated_rows = con.execute(
            f"""
            SELECT
                {name_col},
                first_seen_date,
                last_seen_date
            FROM {table}
            WHERE first_seen_date < last_seen_date
            ORDER BY first_seen_date, {name_col}
            """
        ).fetchall()

        print(f"Products observed across multiple dates: {len(repeated_rows)}")

        if repeated_rows:
            for product in repeated_rows[:20]:
                print(
                    f"{product[0]} | "
                    f"first={product[1]} | "
                    f"last={product[2]}"
                )

            if len(repeated_rows) > 20:
                print(
                    f"... {len(repeated_rows) - 20} additional repeated products"
                )

    print()
    print("=" * 80)
    print("CATALOGUE TREND SIGNAL READINESS")
    print("=" * 80)

    print(f"Total catalogue products: {total_products}")
    print(f"Post-baseline products: {total_new_after_baseline}")

    if total_products > 0:
        print("Catalogue presence signal: AVAILABLE")
    else:
        print("Catalogue presence signal: NOT AVAILABLE")

    if total_new_after_baseline > 0:
        print("Catalogue expansion signal: AVAILABLE")
    else:
        print("Catalogue expansion signal: NOT YET ESTABLISHED")

    print()
    print("Audit complete. No database writes were performed.")

    con.close()


if __name__ == "__main__":
    main()