from pathlib import Path
import sqlite3
import sys

APP_DIR = Path(__file__).resolve().parent
PROJECT_DIR = APP_DIR.parent
DB_PATH = PROJECT_DIR / "data" / "mika_competitive_intel.db"

sys.path.insert(0, str(APP_DIR))

from database import connect


def main():
    con = connect()

    print("=" * 80)
    print("MIKA CI - PHASE 2D PRODUCT CATALOGUE AUDIT")
    print("=" * 80)
    print("Database:", DB_PATH)
    print("Database writes: DISABLED")
    print()

    tables = [
        "product_observations",
        "price_observations",
        "haier_products",
        "haier_price_observations",
        "k_elec_products",
        "bruhm_products",
    ]

    print("CATALOGUE COUNTS")
    print("-" * 80)

    for table in tables:
        count = con.execute(
            "SELECT COUNT(*) FROM {}".format(table)
        ).fetchone()[0]
        print("{:<30} {:>8}".format(table, count))

    print()
    print("GENERIC PRICE COVERAGE")
    print("-" * 80)

    rows = con.execute(
        """
        SELECT
            f.brand,
            COUNT(*) AS observations,
            COUNT(DISTINCT p.observed_date) AS dates,
            MIN(p.observed_date) AS first_date,
            MAX(p.observed_date) AS last_date
        FROM price_observations p
        JOIN findings f
          ON f.finding_id = p.finding_id
        GROUP BY f.brand
        ORDER BY observations DESC
        """
    ).fetchall()

    for row in rows:
        print(
            "{} | {} observations | {} dates | {} to {}".format(
                row["brand"],
                row["observations"],
                row["dates"],
                row["first_date"],
                row["last_date"],
            )
        )

    print()
    print("DEDICATED CATALOGUE HISTORY")
    print("-" * 80)

    rows = con.execute(
        """
        SELECT
            'Bruhm' AS catalogue,
            COUNT(*) AS products,
            COUNT(DISTINCT first_seen_date) AS first_dates,
            COUNT(DISTINCT last_seen_date) AS last_dates,
            MIN(first_seen_date) AS first_seen,
            MAX(last_seen_date) AS last_seen
        FROM bruhm_products

        UNION ALL

        SELECT
            'Haier',
            COUNT(*),
            COUNT(DISTINCT first_seen_date),
            COUNT(DISTINCT last_seen_date),
            MIN(first_seen_date),
            MAX(last_seen_date)
        FROM haier_products

        UNION ALL

        SELECT
            'K-Elec',
            COUNT(*),
            COUNT(DISTINCT first_seen_date),
            COUNT(DISTINCT last_seen_date),
            MIN(first_seen_date),
            MAX(last_seen_date)
        FROM k_elec_products
        """
    ).fetchall()

    for row in rows:
        print(
            "{} | {} products | {} to {}".format(
                row["catalogue"],
                row["products"],
                row["first_seen"],
                row["last_seen"],
            )
        )

    print()
    print("PRODUCT INTELLIGENCE READINESS")
    print("-" * 80)

    product_observation_count = con.execute(
        "SELECT COUNT(*) FROM product_observations"
    ).fetchone()[0]

    print(
        "Generic product observations: {}".format(
            "AVAILABLE" if product_observation_count > 0 else "EMPTY"
        )
    )

    price_observation_count = con.execute(
        "SELECT COUNT(*) FROM price_observations"
    ).fetchone()[0]

    print(
        "Generic price history: {}".format(
            "AVAILABLE" if price_observation_count > 0 else "EMPTY"
        )
    )

    catalogue_tables = [
        ("Bruhm", "bruhm_products"),
        ("Haier", "haier_products"),
        ("K-Elec", "k_elec_products"),
    ]

    for catalogue, table in catalogue_tables:
        row = con.execute(
            "SELECT MIN(first_seen_date), MAX(last_seen_date) FROM " + table
        ).fetchone()

        first_seen = row[0]
        last_seen = row[1]

        status = (
            "AVAILABLE"
            if first_seen and last_seen and first_seen < last_seen
            else "NOT YET ESTABLISHED"
        )

        print(
            "{} multi-day catalogue: {}".format(
                catalogue,
                status,
            )
        )
    print()

    print("Audit complete.")
    print("No database writes were performed.")

    con.close()


if __name__ == "__main__":
    main()


