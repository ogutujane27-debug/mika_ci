import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "mika_competitive_intel.db"
BASELINE_DATE = "2026-09-22"

CATALOGUES = [
    ("Bruhm", "bruhm_products", "sku", "product_name", "category", "product_url"),
    ("Haier", "haier_products", "sku", "product_name", "category", "url"),
    ("K-Elec", "k_elec_products", "product_key", "product_name", "category", "url"),
]

def main():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    total = 0

    print("=" * 80)
    print("MIKA CI - PHASE 2E PRODUCT LAUNCH BASELINE DETECTOR")
    print("=" * 80)
    print(f"Baseline date: {BASELINE_DATE}")
    print("Database writes: DISABLED")
    for competitor, table, identity_col, name_col, category_col, url_col in CATALOGUES:
        rows = con.execute(f"SELECT {identity_col}, {name_col}, {category_col}, {url_col}, first_seen_date, last_seen_date FROM {table} WHERE first_seen_date > ? ORDER BY first_seen_date, {name_col}", (BASELINE_DATE,)).fetchall()
        print()
        print(competitor.upper())
        print("-" * 80)
        print(f"New product detections after baseline: {len(rows)}")
        for row in rows:
            print(f"{row[name_col]} | {row[category_col]} | first={row["first_seen_date"]} | {row[url_col]}")
            print("Status: NEW PRODUCT DETECTION | Launch status: NOT YET CONFIRMED")
        total += len(rows)

    print()
    print("=" * 80)
    print(f"TOTAL NEW PRODUCT DETECTIONS: {total}")
    print("=" * 80)
    print("No database writes were performed.")
    con.close()

if __name__ == "__main__":
    main()
