import sqlite3
from datetime import datetime

DB = r".\data\mika_competitive_intel.db"


def connect():
    return sqlite3.connect(DB)


def insert_comparison(
    conn,
    competitor_id,
    competitor_name,
    brand,
    dimension,
    comparison_type,
    metric_name,
    metric_value,
    observation_count,
    period_start,
    period_end,
    evidence_summary,
    confidence,
    coverage_status,
):
    conn.execute(
        """
        INSERT OR IGNORE INTO competitor_comparisons (
            competitor_id,
            competitor_name,
            brand,
            dimension,
            comparison_type,
            metric_name,
            metric_value,
            observation_count,
            period_start,
            period_end,
            evidence_summary,
            confidence,
            coverage_status,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            competitor_id,
            competitor_name,
            brand,
            dimension,
            comparison_type,
            metric_name,
            metric_value,
            observation_count,
            period_start,
            period_end,
            evidence_summary,
            confidence,
            coverage_status,
            datetime.now().isoformat(timespec="seconds"),
        ),
    )


def write_price_comparisons(conn):
    print("\n--- WRITING PRICE COMPARISONS ---")

    rows = conn.execute(
        """
        SELECT
            f.competitor_id,
            c.competitor_name,
            f.brand,
            COUNT(*) AS observation_count,
            COUNT(DISTINCT p.model) AS model_count,
            MIN(p.observed_date) AS period_start,
            MAX(p.observed_date) AS period_end
        FROM price_observations p
        JOIN findings f
            ON f.finding_id = p.finding_id
        JOIN competitors c
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

    written = 0

    for (
        competitor_id,
        competitor_name,
        brand,
        observation_count,
        model_count,
        period_start,
        period_end,
    ) in rows:

        summary = (
            f"{observation_count} documented price observations "
            f"covering {model_count} models from "
            f"{period_start} to {period_end}."
        )

        insert_comparison(
            conn=conn,
            competitor_id=competitor_id,
            competitor_name=competitor_name,
            brand=brand,
            dimension="PRICE",
            comparison_type="OBSERVATION_COVERAGE",
            metric_name="price_observations",
            metric_value=float(observation_count),
            observation_count=observation_count,
            period_start=period_start,
            period_end=period_end,
            evidence_summary=summary,
            confidence="HIGH",
            coverage_status="DOCUMENTED",
        )

        written += 1

    print(f"Price comparison records prepared: {written}")


def write_campaign_comparisons(conn):
    print("\n--- WRITING CAMPAIGN COMPARISONS ---")

    rows = conn.execute(
        """
        SELECT
            c.competitor_id,
            cp.competitor_name,
            COUNT(*) AS campaign_count,
            MIN(c.observed_date) AS period_start,
            MAX(c.observed_date) AS period_end,
            SUM(
                CASE
                    WHEN LOWER(COALESCE(c.status, '')) = 'active'
                    THEN 1
                    ELSE 0
                END
            ) AS active_count,
            SUM(
                CASE
                    WHEN LOWER(COALESCE(c.status, '')) = 'upcoming'
                    THEN 1
                    ELSE 0
                END
            ) AS upcoming_count
        FROM campaigns c
        JOIN competitors cp
            ON cp.competitor_id = c.competitor_id
        GROUP BY
            c.competitor_id,
            cp.competitor_name
        ORDER BY
            cp.competitor_name
        """
    ).fetchall()

    written = 0

    for (
        competitor_id,
        competitor_name,
        campaign_count,
        period_start,
        period_end,
        active_count,
        upcoming_count,
    ) in rows:

        summary = (
            f"{campaign_count} documented campaign records; "
            f"{active_count} active and {upcoming_count} upcoming "
            f"within the observed period."
        )

        insert_comparison(
            conn=conn,
            competitor_id=competitor_id,
            competitor_name=competitor_name,
            brand=None,
            dimension="CAMPAIGN",
            comparison_type="ACTIVITY_COVERAGE",
            metric_name="campaign_count",
            metric_value=float(campaign_count),
            observation_count=campaign_count,
            period_start=period_start,
            period_end=period_end,
            evidence_summary=summary,
            confidence="HIGH",
            coverage_status="DOCUMENTED",
        )

        written += 1

    print(f"Campaign comparison records prepared: {written}")


def write_social_comparisons(conn):
    print("\n--- WRITING SOCIAL COMPARISONS ---")

    rows = conn.execute(
        """
        SELECT
            s.competitor_id,
            c.competitor_name,
            COUNT(*) AS observation_count,
            MIN(s.observed_date) AS period_start,
            MAX(s.observed_date) AS period_end
        FROM social_observations s
        JOIN competitors c
            ON c.competitor_id = s.competitor_id
        GROUP BY
            s.competitor_id,
            c.competitor_name
        ORDER BY
            c.competitor_name
        """
    ).fetchall()

    written = 0

    for (
        competitor_id,
        competitor_name,
        observation_count,
        period_start,
        period_end,
    ) in rows:

        summary = (
            f"{observation_count} verified social observations "
            f"available from {period_start} to {period_end}. "
            f"This is evidence coverage, not a social trend measurement."
        )

        insert_comparison(
            conn=conn,
            competitor_id=competitor_id,
            competitor_name=competitor_name,
            brand=None,
            dimension="SOCIAL",
            comparison_type="OBSERVATION_COVERAGE",
            metric_name="social_observations",
            metric_value=float(observation_count),
            observation_count=observation_count,
            period_start=period_start,
            period_end=period_end,
            evidence_summary=summary,
            confidence="HIGH",
            coverage_status="DOCUMENTED",
        )

        written += 1

    print(f"Social comparison records prepared: {written}")


def write_catalogue_comparisons(conn):
    print("\n--- WRITING CATALOGUE COMPARISONS ---")

    catalogue_sources = [
        (
            "Bruhm",
            """
            SELECT
                COUNT(*) AS product_count,
                COUNT(DISTINCT sku) AS sku_count,
                COUNT(DISTINCT category) AS category_count,
                MIN(first_seen_date),
                MAX(last_seen_date)
            FROM bruhm_products
            """,
            "products",
        ),
        (
            "Haier",
            """
            SELECT
                COUNT(*) AS product_count,
                COUNT(DISTINCT sku) AS sku_count,
                COUNT(DISTINCT category) AS category_count,
                MIN(first_seen_date),
                MAX(last_seen_date)
            FROM haier_products
            """,
            "products",
        ),
        (
            "K-Elec",
            """
            SELECT
                COUNT(*) AS product_count,
                COUNT(DISTINCT product_key) AS product_key_count,
                COUNT(DISTINCT category) AS category_count,
                MIN(first_seen_date),
                MAX(last_seen_date)
            FROM k_elec_products
            """,
            "products",
        ),
    ]

    competitor_lookup = {
        "Bruhm": conn.execute(
            "SELECT competitor_id, competitor_name FROM competitors WHERE brand_name = 'Bruhm' LIMIT 1"
        ).fetchone(),
        "Haier": conn.execute(
            "SELECT competitor_id, competitor_name FROM competitors WHERE brand_name = 'Haier' LIMIT 1"
        ).fetchone(),
        "K-Elec": conn.execute(
            "SELECT competitor_id, competitor_name FROM competitors WHERE brand_name = 'K-Elec' LIMIT 1"
        ).fetchone(),
    }

    written = 0

    for brand, query, unit_name in catalogue_sources:
        result = conn.execute(query).fetchone()

        product_count = result[0] or 0
        identity_count = result[1] or 0
        category_count = result[2] or 0
        period_start = result[3]
        period_end = result[4]

        lookup = competitor_lookup.get(brand)

        if not lookup:
            print(f"WARNING: competitor identity not found for {brand}")
            continue

        competitor_id, competitor_name = lookup

        summary = (
            f"Tracked catalogue contains {product_count} products, "
            f"{identity_count} distinct product identities and "
            f"{category_count} categories from "
            f"{period_start} to {period_end}. "
            f"This is tracked-source coverage, not market-wide product breadth."
        )

        insert_comparison(
            conn=conn,
            competitor_id=competitor_id,
            competitor_name=competitor_name,
            brand=brand,
            dimension="CATALOGUE",
            comparison_type="TRACKED_COVERAGE",
            metric_name="catalogue_products",
            metric_value=float(product_count),
            observation_count=product_count,
            period_start=period_start,
            period_end=period_end,
            evidence_summary=summary,
            confidence="HIGH",
            coverage_status="TRACKED_SOURCE",
        )

        written += 1

    print(f"Catalogue comparison records prepared: {written}")


def write_market_signal_comparisons(conn):
    print("\n--- WRITING MARKET SIGNAL COMPARISONS ---")

    rows = conn.execute(
        """
        SELECT
            signal_type,
            status,
            COUNT(*)
        FROM market_trends
        GROUP BY
            signal_type,
            status
        ORDER BY
            signal_type,
            status
        """
    ).fetchall()

    written = 0

    for signal_type, status, signal_count in rows:

        summary = (
            f"{signal_count} existing Phase 2F market-trend "
            f"signal record(s) with signal type '{signal_type}' "
            f"and status '{status}'."
        )

        insert_comparison(
            conn=conn,
            competitor_id=0,
            competitor_name="MARKET",
            brand=None,
            dimension="MARKET_SIGNAL",
            comparison_type="EXISTING_SIGNAL",
            metric_name=signal_type,
            metric_value=float(signal_count),
            observation_count=signal_count,
            period_start=None,
            period_end=None,
            evidence_summary=summary,
            confidence="HIGH",
            coverage_status="EXISTING_PHASE_2F_SIGNAL",
        )

        written += 1

    print(f"Market signal comparison records prepared: {written}")


def audit_written_records(conn):
    print("\n--- PERSISTENCE AUDIT ---")

    total = conn.execute(
        """
        SELECT COUNT(*)
        FROM competitor_comparisons
        """
    ).fetchone()[0]

    print(f"Total comparison records: {total}")

    rows = conn.execute(
        """
        SELECT
            dimension,
            comparison_type,
            COUNT(*)
        FROM competitor_comparisons
        GROUP BY
            dimension,
            comparison_type
        ORDER BY
            dimension,
            comparison_type
        """
    ).fetchall()

    for row in rows:
        print(row)

    duplicate_rows = conn.execute(
        """
        SELECT
            competitor_id,
            COALESCE(brand, ''),
            dimension,
            comparison_type,
            metric_name,
            COALESCE(period_start, ''),
            COALESCE(period_end, ''),
            COUNT(*)
        FROM competitor_comparisons
        GROUP BY
            competitor_id,
            COALESCE(brand, ''),
            dimension,
            comparison_type,
            metric_name,
            COALESCE(period_start, ''),
            COALESCE(period_end, '')
        HAVING COUNT(*) > 1
        """
    ).fetchall()

    print(f"Duplicate identity groups: {len(duplicate_rows)}")

    if duplicate_rows:
        print("WARNING: duplicate identity groups detected")
        for row in duplicate_rows:
            print(row)
    else:
        print("Duplicate identity groups: NONE")


def main():
    print("=" * 70)
    print("MIKA CI - PHASE 2G COMPARISON WRITER")
    print("=" * 70)

    conn = connect()

    try:
        write_price_comparisons(conn)
        write_campaign_comparisons(conn)
        write_social_comparisons(conn)
        write_catalogue_comparisons(conn)
        write_market_signal_comparisons(conn)

        conn.commit()

        audit_written_records(conn)

        print("\n" + "=" * 70)
        print("PHASE 2G COMPARISON PERSISTENCE COMPLETE")
        print("DATABASE WRITE: SUCCESS")
        print("=" * 70)

    except Exception:
        conn.rollback()
        print("\nDATABASE WRITE FAILED - TRANSACTION ROLLED BACK")
        raise

    finally:
        conn.close()


if __name__ == "__main__":
    main()