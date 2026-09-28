import sqlite3
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "data" / "mika_competitive_intel.db"


def connect():
    return sqlite3.connect(DB_PATH)


def get_competitor_map(conn):
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

    return {
        row[0]: {
            "competitor_name": row[1],
            "brand_name": row[2],
        }
        for row in rows
    }


def get_price_comparison(conn):
    return conn.execute(
        """
        SELECT
            f.competitor_id,
            c.competitor_name,
            f.brand,
            COUNT(*) AS observations,
            COUNT(DISTINCT p.observed_date) AS observation_days,
            MIN(p.observed_date) AS first_date,
            MAX(p.observed_date) AS last_date,
            COUNT(DISTINCT p.model) AS model_count
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
            c.competitor_name,
            f.brand
        """
    ).fetchall()


def get_price_movement_comparison(conn):
    rows = conn.execute(
        """
        SELECT
            mt.competitor_name,
            mt.title,
            mt.description,
            mt.start_date,
            mt.end_date,
            mt.evidence_count,
            mt.confidence
        FROM market_trends mt
        WHERE mt.signal_type = 'PRODUCT_PRICE_MOVEMENT'
        ORDER BY
            mt.competitor_name,
            mt.start_date,
            mt.title
        """
    ).fetchall()

    return rows


def get_campaign_comparison(conn):
    return conn.execute(
        """
        SELECT
            c.competitor_id,
            cp.competitor_name,
            COUNT(*) AS campaign_count,
            COUNT(
                DISTINCT CASE
                    WHEN c.status = 'active'
                    THEN c.campaign_id
                END
            ) AS active_campaigns,
            COUNT(
                DISTINCT CASE
                    WHEN c.status = 'upcoming'
                    THEN c.campaign_id
                END
            ) AS upcoming_campaigns,
            COUNT(DISTINCT c.campaign_type) AS campaign_types,
            COUNT(DISTINCT c.category) AS campaign_categories,
            MIN(c.observed_date) AS first_observed,
            MAX(c.observed_date) AS last_observed
        FROM campaigns c
        LEFT JOIN competitors cp
            ON cp.competitor_id = c.competitor_id
        GROUP BY
            c.competitor_id,
            cp.competitor_name
        ORDER BY
            cp.competitor_name
        """
    ).fetchall()


def get_social_comparison(conn):
    return conn.execute(
        """
        SELECT
            s.competitor_id,
            c.competitor_name,
            COUNT(*) AS observations,
            COUNT(DISTINCT s.observed_date) AS observation_days,
            MIN(s.observed_date) AS first_observed,
            MAX(s.observed_date) AS last_observed
        FROM social_observations s
        LEFT JOIN competitors c
            ON c.competitor_id = s.competitor_id
        GROUP BY
            s.competitor_id,
            c.competitor_name
        ORDER BY
            c.competitor_name
        """
    ).fetchall()


def get_bruhm_catalogue(conn):
    return conn.execute(
        """
        SELECT
            competitor,
            COUNT(*) AS products,
            COUNT(DISTINCT sku) AS sku_count,
            COUNT(DISTINCT category) AS categories,
            MIN(first_seen_date) AS first_seen,
            MAX(last_seen_date) AS last_seen
        FROM bruhm_products
        GROUP BY competitor
        """
    ).fetchall()


def get_haier_catalogue(conn):
    return conn.execute(
        """
        SELECT
            COUNT(*) AS products,
            COUNT(DISTINCT sku) AS sku_count,
            COUNT(DISTINCT category) AS categories,
            MIN(first_seen_date) AS first_seen,
            MAX(last_seen_date) AS last_seen
        FROM haier_products
        """
    ).fetchone()


def get_kelect_catalogue(conn):
    return conn.execute(
        """
        SELECT
            COUNT(*) AS products,
            COUNT(DISTINCT product_key) AS product_keys,
            COUNT(DISTINCT category) AS categories,
            MIN(first_seen_date) AS first_seen,
            MAX(last_seen_date) AS last_seen
        FROM k_elec_products
        """
    ).fetchone()


def get_launch_summary(conn):
    tables = {
        "product_launch_discovery": False,
        "product_launch_evidence": False,
    }

    existing = {
        row[0]
        for row in conn.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
            """
        ).fetchall()
    }

    return {
        "tables_available": [
            name for name in tables
            if name in existing
        ]
    }


def get_market_trend_summary(conn):
    return conn.execute(
        """
        SELECT
            signal_type,
            status,
            COUNT(*) AS signal_count
        FROM market_trends
        GROUP BY
            signal_type,
            status
        ORDER BY
            signal_type,
            status
        """
    ).fetchall()


def print_section(title):
    print()
    print("=" * 78)
    print(title)
    print("=" * 78)


def main():
    print("=" * 78)
    print("MIKA CI - PHASE 2G COMPETITOR COMPARISON ENGINE")
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
        # PRICE
        # ---------------------------------------------------------------
        print_section("1. PRICE EVIDENCE COMPARISON")

        rows = get_price_comparison(conn)

        if not rows:
            print("No price evidence found.")

        for row in rows:
            (
                competitor_id,
                competitor_name,
                brand,
                observations,
                observation_days,
                first_date,
                last_date,
                model_count,
            ) = row

            print(
                f"{competitor_name} | "
                f"{brand} | "
                f"{observations} observations | "
                f"{observation_days} days | "
                f"{model_count} models | "
                f"{first_date} -> {last_date}"
            )

        # ---------------------------------------------------------------
        # PRICE MOVEMENTS
        # ---------------------------------------------------------------
        print_section("2. DOCUMENTED PRICE MOVEMENTS")

        rows = get_price_movement_comparison(conn)

        if not rows:
            print("No persisted price movement signals found.")

        for row in rows:
            (
                competitor_name,
                title,
                description,
                start_date,
                end_date,
                evidence_count,
                confidence,
            ) = row

            print(
                f"{competitor_name} | "
                f"{title} | "
                f"{start_date} -> {end_date} | "
                f"evidence={evidence_count} | "
                f"confidence={confidence}"
            )
            print(f"  {description}")

        # ---------------------------------------------------------------
        # CAMPAIGNS
        # ---------------------------------------------------------------
        print_section("3. CAMPAIGN ACTIVITY COMPARISON")

        rows = get_campaign_comparison(conn)

        if not rows:
            print("No campaign evidence found.")

        for row in rows:
            (
                competitor_id,
                competitor_name,
                campaign_count,
                active_campaigns,
                upcoming_campaigns,
                campaign_types,
                campaign_categories,
                first_observed,
                last_observed,
            ) = row

            print(
                f"{competitor_name} | "
                f"campaigns={campaign_count} | "
                f"active={active_campaigns} | "
                f"upcoming={upcoming_campaigns} | "
                f"types={campaign_types} | "
                f"categories={campaign_categories} | "
                f"{first_observed} -> {last_observed}"
            )

        # ---------------------------------------------------------------
        # SOCIAL
        # ---------------------------------------------------------------
        print_section("4. SOCIAL EVIDENCE COMPARISON")

        rows = get_social_comparison(conn)

        if not rows:
            print("No social evidence found.")

        for row in rows:
            (
                competitor_id,
                competitor_name,
                observations,
                observation_days,
                first_observed,
                last_observed,
            ) = row

            print(
                f"{competitor_name} | "
                f"{observations} observations | "
                f"{observation_days} days | "
                f"{first_observed} -> {last_observed}"
            )

        # ---------------------------------------------------------------
        # CATALOGUE
        # ---------------------------------------------------------------
        print_section("5. TRACKED CATALOGUE COMPARISON")

        print("Bruhm:")

        for row in get_bruhm_catalogue(conn):
            (
                competitor,
                products,
                sku_count,
                categories,
                first_seen,
                last_seen,
            ) = row

            print(
                f"  {competitor} | "
                f"products={products} | "
                f"SKUs={sku_count} | "
                f"categories={categories} | "
                f"{first_seen} -> {last_seen}"
            )

        print("Haier:")

        row = get_haier_catalogue(conn)

        if row:
            (
                products,
                sku_count,
                categories,
                first_seen,
                last_seen,
            ) = row

            print(
                f"  Haier catalogue | "
                f"products={products} | "
                f"SKUs={sku_count} | "
                f"categories={categories} | "
                f"{first_seen} -> {last_seen}"
            )

        print("K-Elec:")

        row = get_kelect_catalogue(conn)

        if row:
            (
                products,
                product_keys,
                categories,
                first_seen,
                last_seen,
            ) = row

            print(
                f"  K-Elec catalogue | "
                f"products={products} | "
                f"product_keys={product_keys} | "
                f"categories={categories} | "
                f"{first_seen} -> {last_seen}"
            )

        print("Catalogue evidence is tracked-source coverage, not market-wide coverage.")

        # ---------------------------------------------------------------
        # LAUNCH
        # ---------------------------------------------------------------
        print_section("6. PRODUCT LAUNCH EVIDENCE")

        launch = get_launch_summary(conn)

        print(
            "Launch tables directly available in SQLite: "
            + (
                ", ".join(launch["tables_available"])
                if launch["tables_available"]
                else "none"
            )
        )

        print(
            "Phase 2E launch evidence must be interpreted using its "
            "baseline/post-baseline rules."
        )

        # ---------------------------------------------------------------
        # MARKET TRENDS
        # ---------------------------------------------------------------
        print_section("7. EXISTING MARKET TREND SIGNALS")

        rows = get_market_trend_summary(conn)

        for signal_type, status, count in rows:
            print(
                f"{signal_type} | "
                f"{status} | "
                f"{count}"
            )

        # ---------------------------------------------------------------
        # COMPARISON GUARDRAILS
        # ---------------------------------------------------------------
        print_section("8. PHASE 2G COMPARISON GUARDRAILS")

        print("ALLOWED:")
        print("  - Compare observed evidence by competitor and brand.")
        print("  - Compare price observation coverage.")
        print("  - Compare documented price movements.")
        print("  - Compare verified campaign activity.")
        print("  - Compare available social activity.")
        print("  - Compare tracked catalogue coverage.")
        print("  - Show evidence gaps and unequal coverage.")

        print()
        print("NOT ESTABLISHED:")
        print("  - Market share")
        print("  - Sales volume")
        print("  - Revenue")
        print("  - Overall competitive ranking")
        print("  - Market-wide product breadth")
        print("  - Market-wide launch activity")
        print("  - Competitive causality")

        print()
        print("=" * 78)
        print("PHASE 2G ENGINE COMPLETE")
        print("Database writes: DISABLED")
        print("=" * 78)

    finally:
        conn.close()


if __name__ == "__main__":
    main()