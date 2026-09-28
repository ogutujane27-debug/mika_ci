import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "mika_competitive_intel.db"
BASELINE_DATE = "2026-09-22"

CATALOGUES = [
    ("Bruhm", "bruhm_products", "sku", "product_name", "category", "product_url"),
    ("Haier", "haier_products", "sku", "product_name", "category", "url"),
    ("K-Elec", "k_elec_products", "product_key", "product_name", "category", "url"),
]

def classify(first_seen_date):
    if first_seen_date <= BASELINE_DATE:
        return "BASELINE"
    return "FIRST_OBSERVED"

def main():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    total = 0

    print("=" * 80)
    print("MIKA CI - PHASE 2E LAUNCH EVIDENCE DETECTOR")
    print("=" * 80)
    print(f"Baseline date: {BASELINE_DATE}")
    print("Database writes: DISABLED")

    for competitor, table, identity_col, name_col, category_col, url_col in CATALOGUES:
        rows = con.execute(f"SELECT {identity_col}, {name_col}, {category_col}, {url_col}, first_seen_date, last_seen_date FROM {table} WHERE first_seen_date > ? ORDER BY first_seen_date, {name_col}", (BASELINE_DATE,)).fetchall()
        print()
        print(competitor.upper())
        print("-" * 80)
        print("-" * 80)
        
        for row in rows:
            status = classify(row["first_seen_date"])
            print()
            print(f"Product: {row[name_col]}")
            print(f"Category: {row[category_col]}")
            print(f"First observed: {row["first_seen_date"]}")
            print(f"URL: {row[url_col]}")
            print(f"Evidence status: {status}")
            print("Launch status: NOT CONFIRMED")
            total += 1

    print()
    print("=" * 80)
    print(f"TOTAL POST-BASELINE PRODUCTS: {total}")
    print("=" * 80)
    print("No database writes were performed.")
    con.close()

if __name__ == "__main__":
    main()

CONFIRMED_LAUNCH_TERMS = ("LAUNCH", "LAUNCHED", "LAUNCHING", "INTRODUCING")

def classify_evidence(evidence_text, dated_official=False):
    text = (evidence_text or "").upper()
    if dated_official and any(term in text for term in CONFIRMED_LAUNCH_TERMS):
        return "CONFIRMED_LAUNCH"
    if any(term in text for term in LAUNCH_CANDIDATE_TERMS):
        return "LAUNCH_CANDIDATE"
    return "FIRST_OBSERVED"
LAUNCH_CANDIDATE_TERMS = ("NEW ARRIVAL", "INTRODUCING", "NEW PRODUCT", "JUST LAUNCHED", "NOW AVAILABLE")
