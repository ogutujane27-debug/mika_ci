import sqlite3
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "data" / "mika_competitive_intel.db"


def connect():
    return sqlite3.connect(DB_PATH)


def table_exists(conn, table_name):
    row = conn.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
          AND name = ?
        """,
        (table_name,),
    ).fetchone()

    return row is not None


def count_rows(conn, table_name):
    if not table_exists(conn, table_name):
        return None

    return conn.execute(
        f"SELECT COUNT(*) FROM {table_name}"
    ).fetchone()[0]


def main():
    print("=" * 78)
    print("MIKA CI - PHASE 2G COMPETITOR COMPARISON AUDIT")
    print("=" * 78)
    print(f"Database: {DB_PATH}")
    print("Database writes: DISABLED")
    print()

    if not DB_PATH.exists():
        print("ERROR: Database does not exist.")
        return

    conn = connect()

    try:
        # ---------------------------------------------------------------
        # 1. TABLE COUNTS
        # ---------------------------------------------------------------
        print("TABLE COUNTS")
        print("-" * 78)

        tables = [
            "competitors",
            "findings",
            "price_observations",
            "campaigns",
            "campaign_posts",
            "social_observations",
            "social_sources",
            "haier_products",
            "haier_price_observations",
            "bruhm_products",
            "k_elec_products",
            "market_trends",
        ]

        for table in tables:
            count = count_rows(conn, table)

            if count is None:
                print(f"{table:<35} NOT FOUND")
            else:
                print(f"{table:<35} {count}")

        # ---------------------------------------------------------------
        # 2. COMPETITOR / BRAND STRUCTURE
        # ---------------------------------------------------------------
        print()
        print("=" * 78)
        print("COMPETITOR / BRAND STRUCTURE")
        print("=" * 78)

        rows = conn.execute(
            """
            SELECT
                competitor_id,
                competitor_name,
                brand_name,
                official_url
            FROM competitors
            ORDER BY competitor_id
            """
        ).fetchall()

        for row in rows:
            print(
                f"{row[0]} | "
                f"Competitor={row[1]} | "
                f"Brand={row[2]} | "
                f"URL={row[3]}"
            )

        # ---------------------------------------------------------------
        # 3. PRICE COVERAGE
        # ---------------------------------------------------------------
        print()
        print("=" * 78)
        print("PRICE EVIDENCE COVERAGE")
        print("=" * 78)

        rows = conn.execute(
            """
            SELECT
                f.competitor_id,
                c.competitor_name,
                f.brand,
                COUNT(*) AS observations,
                MIN(p.observed_date),
                MAX(p.observed_date)
            FROM price_observations p
            JOIN findings f
                ON f.finding_id = p.finding_id
            LEFT JOIN competitors c
                ON c.competitor_id = f.competitor_id
            GROUP BY
                f.competitor_id,
                c.competitor_name,
                f.brand
            ORDER BY
                observations DESC,
                c.competitor_name,
                f.brand
            """
        ).fetchall()

        for row in rows:
            competitor_id, competitor_name, brand, count, first_date, last_date = row

            print(
                f"ID={competitor_id:<3} | "
                f"{competitor_name:<22} | "
                f"{str(brand):<15} | "
                f"{count:>4} observations | "
                f"{first_date} -> {last_date}"
            )

        # ---------------------------------------------------------------
        # 4. PRICE CATEGORY COVERAGE
        # ---------------------------------------------------------------
        print()
        print("=" * 78)
        print("PRICE EVIDENCE BY CATEGORY")
        print("=" * 78)

        rows = conn.execute(
            """
            SELECT
                f.brand,
                f.category,
                COUNT(*) AS observations
            FROM price_observations p
            JOIN findings f
                ON f.finding_id = p.finding_id
            GROUP BY
                f.brand,
                f.category
            ORDER BY
                f.brand,
                observations DESC
            """
        ).fetchall()

        for brand, category, count in rows:
            print(
                f"{str(brand):<20} | "
                f"{str(category):<25} | "
                f"{count:>4}"
            )

        # ---------------------------------------------------------------
        # 5. CAMPAIGN COVERAGE
        # ---------------------------------------------------------------
        print()
        print("=" * 78)
        print("CAMPAIGN COVERAGE")
        print("=" * 78)

        rows = conn.execute(
            """
            SELECT
                c.competitor_id,
                cp.competitor_name,
                COUNT(*) AS campaigns,
                MIN(c.observed_date),
                MAX(c.observed_date)
            FROM campaigns c
            LEFT JOIN competitors cp
                ON cp.competitor_id = c.competitor_id
            GROUP BY
                c.competitor_id,
                cp.competitor_name
            ORDER BY campaigns DESC
            """
        ).fetchall()

        for row in rows:
            competitor_id, competitor_name, count, first_date, last_date = row

            print(
                f"ID={competitor_id:<3} | "
                f"{str(competitor_name):<22} | "
                f"{count:>3} campaigns | "
                f"{first_date} -> {last_date}"
            )

        # ---------------------------------------------------------------
        # 6. SOCIAL COVERAGE
        # ---------------------------------------------------------------
        print()
        print("=" * 78)
        print("SOCIAL EVIDENCE COVERAGE")
        print("=" * 78)

        social_columns = {
            row[1]
            for row in conn.execute(
                "PRAGMA table_info(social_observations)"
            ).fetchall()
        }

        if "competitor_id" in social_columns:
            rows = conn.execute(
                """
                SELECT
                    s.competitor_id,
                    c.competitor_name,
                    COUNT(*) AS observations,
                    MIN(s.observed_date),
                    MAX(s.observed_date)
                FROM social_observations s
                LEFT JOIN competitors c
                    ON c.competitor_id = s.competitor_id
                GROUP BY
                    s.competitor_id,
                    c.competitor_name
                ORDER BY observations DESC
                """
            ).fetchall()

            for row in rows:
                competitor_id, competitor_name, count, first_date, last_date = row

                print(
                    f"ID={competitor_id:<3} | "
                    f"{str(competitor_name):<22} | "
                    f"{count:>3} observations | "
                    f"{first_date} -> {last_date}"
                )
        else:
            print("competitor_id column not present.")

        # ---------------------------------------------------------------
        # 7. CATALOGUE COVERAGE
        # ---------------------------------------------------------------
        print()
        print("=" * 78)
        print("CATALOGUE COVERAGE")
        print("=" * 78)

        catalogue_tables = [
            ("bruhm_products", "Bruhm"),
            ("haier_products", "Haier"),
            ("k_elec_products", "K-Elec"),
        ]

        for table_name, label in catalogue_tables:
            if not table_exists(conn, table_name):
                print(f"{label:<10} TABLE NOT FOUND")
                continue

            row = conn.execute(
                f"""
                SELECT
                    COUNT(*),
                    MIN(first_seen),
                    MAX(last_seen)
                FROM {table_name}
                """
            ).fetchone()

            count, first_seen, last_seen = row

            print(
                f"{label:<10} | "
                f"{count:>4} products | "
                f"{first_seen} -> {last_seen}"
            )

        # ---------------------------------------------------------------
        # 8. MARKET TREND SIGNALS
        # ---------------------------------------------------------------
        print()
        print("=" * 78)
        print("MARKET TREND SIGNAL COVERAGE")
        print("=" * 78)

        rows = conn.execute(
            """
            SELECT
                signal_type,
                status,
                COUNT(*)
            FROM market_trends
            GROUP BY signal_type, status
            ORDER BY signal_type, status
            """
        ).fetchall()

        for signal_type, status, count in rows:
            print(
                f"{signal_type:<35} | "
                f"{status:<20} | "
                f"{count}"
            )

        # ---------------------------------------------------------------
        # 9. COMPARISON DATA AVAILABILITY
        # ---------------------------------------------------------------
        print()
        print("=" * 78)
        print("COMPARISON DATA AVAILABILITY")
        print("=" * 78)

        print()
        print("PRICE:")
        print("  Available through price_observations -> findings.")
        print("  Competitor, brand, category, product, model and price are available.")

        print()
        print("CAMPAIGNS:")
        print("  Available through campaigns.")
        print("  Currently concentrated in a limited number of competitors.")

        print()
        print("SOCIAL:")
        print("  Available through social_observations.")
        print("  Coverage depends on verified social sources.")

        print()
        print("CATALOGUE:")
        print("  Available for Bruhm, Haier and K-Elec.")
        print("  This must NOT be treated as complete market-wide catalogue coverage.")

        print()
        print("LAUNCHES:")
        print("  Phase 2E launch evidence exists.")
        print("  Baseline/post-baseline logic must be respected.")

        print()
        print("MARKET TRENDS:")
        print("  Phase 2F derived signals are available.")
        print("  They must be treated as evidence, not as unsupported rankings.")

        # ---------------------------------------------------------------
        # 10. FINAL
        # ---------------------------------------------------------------
        print()
        print("=" * 78)
        print("PHASE 2G AUDIT COMPLETE")
        print("Database writes: DISABLED")
        print("=" * 78)

    finally:
        conn.close()


if __name__ == "__main__":
    main()