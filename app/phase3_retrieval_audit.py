import sqlite3
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "data" / "mika_competitive_intel.db"


def connect():
    return sqlite3.connect(DB_PATH)


def table_count(conn, table_name):
    row = conn.execute(
        f"SELECT COUNT(*) FROM {table_name}"
    ).fetchone()
    return row[0]


def main():
    print("=" * 78)
    print("MIKA CI - PHASE 3 RETRIEVAL AUDIT")
    print("=" * 78)
    print(f"Database: {DB_PATH}")
    print("MODE: READ-ONLY")
    print()

    conn = connect()

    tables = [
        "competitors",
        "findings",
        "price_observations",
        "campaigns",
        "campaign_posts",
        "social_observations",
        "market_trends",
        "competitor_comparisons",
        "strategic_alerts",
        "haier_products",
        "bruhm_products",
        "k_elec_products",
    ]

    print("EVIDENCE TABLE COUNTS")
    print("-" * 78)

    for table in tables:
        try:
            count = table_count(conn, table)
            print(f"{table:<30} {count:>8}")
        except sqlite3.Error as exc:
            print(f"{table:<30} ERROR: {exc}")

    print()
    print("COMPETITOR MASTER")
    print("-" * 78)

    rows = conn.execute(
    """
    SELECT
        competitor_id,
        competitor_name,
        brand_name
    FROM competitors
    ORDER BY competitor_id
    """
).fetchall()

    for row in rows:
        print(
            f"{row[0]:>3} | "
            f"{row[1]:<25} | "
            f"{row[2]}"
        )

    print()
    print("PHASE 3 RETRIEVAL AUDIT COMPLETE")
    print("NO DATABASE ROWS WERE WRITTEN")

    conn.close()


if __name__ == "__main__":
    main()