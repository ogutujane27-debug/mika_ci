import sqlite3
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "data" / "mika_competitive_intel.db"


def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def rows_to_dicts(rows) -> list[dict[str, Any]]:
    return [dict(row) for row in rows]


def get_active_campaigns(conn) -> list[dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT
            campaign_id,
            competitor_id,
            campaign_name,
            campaign_type,
            category,
            offer_value,
            start_date,
            end_date,
            status,
            source_url,
            evidence_text,
            verification_status,
            confidence,
            observed_date
        FROM campaigns
        WHERE status IN ('active', 'ACTIVE')
        ORDER BY
            COALESCE(end_date, '9999-12-31'),
            competitor_id,
            campaign_id
        """
    ).fetchall()

    return rows_to_dicts(rows)


def get_upcoming_campaigns(conn) -> list[dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT
            campaign_id,
            competitor_id,
            campaign_name,
            campaign_type,
            category,
            offer_value,
            start_date,
            end_date,
            status,
            source_url,
            evidence_text,
            verification_status,
            confidence,
            observed_date
        FROM campaigns
        WHERE status IN ('upcoming', 'UPCOMING')
        ORDER BY
            COALESCE(start_date, '9999-12-31'),
            competitor_id,
            campaign_id
        """
    ).fetchall()

    return rows_to_dicts(rows)


def get_price_movements(conn) -> list[dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT
            po.observation_id,
            po.product_name,
            po.model,
            po.price_kes,
            po.observed_date,
            f.finding_id,
            f.competitor_id,
            f.brand,
            f.category,
            f.summary,
            f.source_url,
            f.source_type,
            f.published_date,
            f.evidence_text,
            f.verification_status,
            f.confidence
        FROM price_observations po
        JOIN findings f
            ON f.finding_id = po.finding_id
        WHERE
            f.finding_type = 'price'
            OR f.finding_type = 'PRICE_MOVEMENT'
        ORDER BY
            po.observed_date DESC,
            po.observation_id DESC
        """
    ).fetchall()

    return rows_to_dicts(rows)


def get_strategic_alerts(conn) -> list[dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT
            alert_id,
            alert_type,
            priority,
            competitor_id,
            competitor_name,
            brand,
            category,
            title,
            description,
            evidence_source,
            evidence_reference,
            evidence_count,
            period_start,
            period_end,
            confidence,
            status,
            created_at
        FROM strategic_alerts
        WHERE status = 'OPEN'
        ORDER BY
            CASE priority
                WHEN 'HIGH' THEN 1
                WHEN 'MEDIUM' THEN 2
                WHEN 'LOW' THEN 3
                ELSE 4
            END,
            created_at DESC,
            alert_id DESC
        """
    ).fetchall()

    return rows_to_dicts(rows)


def get_market_trends(conn) -> list[dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT
            trend_id,
            signal_type,
            status,
            competitor_name,
            category,
            title,
            description,
            start_date,
            end_date,
            evidence_count,
            confidence,
            created_at
        FROM market_trends
        ORDER BY
            created_at DESC,
            trend_id DESC
        """
    ).fetchall()

    return rows_to_dicts(rows)


def get_social_evidence(conn) -> list[dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT
            so.*
        FROM social_observations so
        ORDER BY
            so.observed_date DESC,
            so.observation_id DESC
        """
    ).fetchall()

    return rows_to_dicts(rows)


def get_competitor_comparisons(conn) -> list[dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT
            comparison_id,
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
        FROM competitor_comparisons
        ORDER BY
            competitor_name,
            brand,
            dimension,
            comparison_id
        """
    ).fetchall()

    return rows_to_dicts(rows)


def get_catalogue_summary(conn) -> list[dict[str, Any]]:
    results = []

    catalogue_queries = [
        (
            "Haier",
            """
            SELECT
                COUNT(*) AS product_count,
                MIN(first_seen_date) AS first_seen,
                MAX(last_seen_date) AS last_seen
            FROM haier_products
            """
        ),
        (
            "Bruhm",
            """
            SELECT
                COUNT(*) AS product_count,
                MIN(first_seen_date) AS first_seen,
                MAX(last_seen_date) AS last_seen
            FROM bruhm_products
            """
        ),
        (
            "K-Elec",
            """
            SELECT
                COUNT(*) AS product_count,
                MIN(first_seen_date) AS first_seen,
                MAX(last_seen_date) AS last_seen
            FROM k_elec_products
            """
        ),
    ]

    for brand, query in catalogue_queries:
        row = conn.execute(query).fetchone()

        results.append(
            {
                "catalogue": brand,
                "product_count": row["product_count"],
                "first_seen": row["first_seen"],
                "last_seen": row["last_seen"],
            }
        )

    return results


def get_competitor_master(conn) -> list[dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT
            competitor_id,
            competitor_name,
            brand_name,
            official_url,
            secondary_url
        FROM competitors
        ORDER BY competitor_id
        """
    ).fetchall()

    return rows_to_dicts(rows)


def run_retrieval_audit():
    conn = connect()

    print("=" * 78)
    print("MIKA CI - PHASE 3B EVIDENCE RETRIEVAL ENGINE")
    print("=" * 78)
    print(f"Database: {DB_PATH}")
    print("MODE: READ-ONLY")
    print()

    active = get_active_campaigns(conn)
    upcoming = get_upcoming_campaigns(conn)
    prices = get_price_movements(conn)
    alerts = get_strategic_alerts(conn)
    trends = get_market_trends(conn)
    social = get_social_evidence(conn)
    comparisons = get_competitor_comparisons(conn)
    catalogues = get_catalogue_summary(conn)
    competitors = get_competitor_master(conn)

    print("RETRIEVAL COUNTS")
    print("-" * 78)
    print(f"Competitors              : {len(competitors)}")
    print(f"Active campaigns         : {len(active)}")
    print(f"Upcoming campaigns       : {len(upcoming)}")
    print(f"Price observations       : {len(prices)}")
    print(f"Open strategic alerts    : {len(alerts)}")
    print(f"Market trends            : {len(trends)}")
    print(f"Social observations      : {len(social)}")
    print(f"Competitor comparisons   : {len(comparisons)}")
    print(f"Catalogue summaries      : {len(catalogues)}")

    print()
    print("ACTIVE CAMPAIGNS")
    print("-" * 78)

    for campaign in active:
        print(
            f"{campaign['campaign_name']} | "
            f"start={campaign['start_date']} | "
            f"end={campaign['end_date']} | "
            f"status={campaign['status']}"
        )

    print()
    print("UPCOMING CAMPAIGNS")
    print("-" * 78)

    for campaign in upcoming:
        print(
            f"{campaign['campaign_name']} | "
            f"start={campaign['start_date']} | "
            f"end={campaign['end_date']} | "
            f"status={campaign['status']}"
        )

    print()
    print("OPEN STRATEGIC ALERTS")
    print("-" * 78)

    for alert in alerts:
        print(
            f"{alert['priority']} | "
            f"{alert['alert_type']} | "
            f"{alert['title']}"
        )

    print()
    print("CATALOGUE SUMMARY")
    print("-" * 78)

    for catalogue in catalogues:
        print(
            f"{catalogue['catalogue']:<10} | "
            f"{catalogue['product_count']:>4} products | "
            f"{catalogue['first_seen']} -> {catalogue['last_seen']}"
        )

    print()
    print("=" * 78)
    print("PHASE 3B RETRIEVAL AUDIT COMPLETE")
    print("NO DATABASE ROWS WERE WRITTEN")
    print("=" * 78)

    conn.close()


if __name__ == "__main__":
    run_retrieval_audit()