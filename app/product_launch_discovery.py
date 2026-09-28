from pathlib import Path
import sqlite3
from datetime import date, timedelta

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "mika_competitive_intel.db"

WINDOW_DAYS = 7


def main():
    today = date.today()
    window_start = today - timedelta(days=WINDOW_DAYS - 1)

    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row

    print("=" * 80)
    print("MIKA CI - PHASE 2E PRODUCT LAUNCH DISCOVERY")
    print("=" * 80)
    print(f"Database: {DB_PATH}")
    print(f"Window: {window_start} to {today}")
    print("Database writes: DISABLED")
    print()

    catalogues = [
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

    total = 0

    for competitor, table, identity_column, name_column, category_column, url_column in catalogues:
        rows = con.execute(
            f"""
            SELECT
                {identity_column} AS identity_value,
                {name_column} AS product_name,
                {category_column} AS category,
                {url_column} AS product_url,
                first_seen_date,
                last_seen_date
            FROM {table}
            WHERE first_seen_date BETWEEN ? AND ?
            ORDER BY first_seen_date, product_name
            """,
            (window_start.isoformat(), today.isoformat()),
        ).fetchall()

        print()
        print(competitor.upper())
        print("-" * 80)
        print(f"New product candidates: {len(rows)}")

        for row in rows:
            print()
            print(f"Product: {row['product_name']}")
            print(f"Identity: {row['identity_value'] or 'NONE'}")
            print(f"Category: {row['category'] or 'NONE'}")
            print(f"First observed: {row['first_seen_date']}")
            print(f"Last observed: {row['last_seen_date']}")
            print(f"URL: {row['product_url'] or 'NONE'}")
            print("Status: NEW PRODUCT CANDIDATE")

        total += len(rows)

    print()
    print("=" * 80)
    print(f"TOTAL NEW PRODUCT CANDIDATES: {total}")
    print("=" * 80)
    print("Discovery complete.")
    print("No database writes were performed.")

    con.close()


if __name__ == "__main__":
    main()
