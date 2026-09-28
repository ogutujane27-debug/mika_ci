from __future__ import annotations

import sqlite3
from datetime import date
from pathlib import Path


DB_PATH = (
    Path(__file__).resolve().parent.parent
    / "data"
    / "mika_competitive_intel.db"
)


def connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def scalar(conn, sql: str, params=()):
    row = conn.execute(sql, params).fetchone()
    return row[0] if row else 0


def get_dashboard_counts():
    """
    Read-only dashboard metrics.
    No database rows are inserted, updated, or deleted.
    """

    today = date.today().isoformat()

    with connect() as conn:

        competitors = scalar(
            conn,
            "SELECT COUNT(*) FROM competitors"
        )

        price_observations = scalar(
            conn,
            "SELECT COUNT(*) FROM price_observations"
        )

        social_observations = scalar(
            conn,
            "SELECT COUNT(*) FROM social_observations"
        )

        market_trends = scalar(
            conn,
            "SELECT COUNT(*) FROM market_trends"
        )

        strategic_alerts = scalar(
            conn,
            """
            SELECT COUNT(*)
            FROM strategic_alerts
            WHERE status = 'OPEN'
            """
        )

        haier_products = scalar(
            conn,
            "SELECT COUNT(*) FROM haier_products"
        )

        bruhm_products = scalar(
            conn,
            "SELECT COUNT(*) FROM bruhm_products"
        )

        k_elec_products = scalar(
            conn,
            "SELECT COUNT(*) FROM k_elec_products"
        )

        catalogue_products = (
            haier_products
            + bruhm_products
            + k_elec_products
        )

        active_campaigns = scalar(
            conn,
            """
            SELECT COUNT(*)
            FROM campaigns
            WHERE
                start_date IS NOT NULL
                AND start_date <= ?
                AND (
                    end_date IS NULL
                    OR end_date >= ?
                )
                AND status != 'ended'
            """,
            (today, today),
        )

        upcoming_campaigns = scalar(
            conn,
            """
            SELECT COUNT(*)
            FROM campaigns
            WHERE
                start_date IS NOT NULL
                AND start_date > ?
                AND status = 'upcoming'
            """,
            (today,),
        )

    return {
        "competitors": competitors,
        "price_observations": price_observations,
        "active_campaigns": active_campaigns,
        "upcoming_campaigns": upcoming_campaigns,
        "social_observations": social_observations,
        "market_trends": market_trends,
        "strategic_alerts": strategic_alerts,
        "catalogue_products": catalogue_products,
        "haier_products": haier_products,
        "bruhm_products": bruhm_products,
        "k_elec_products": k_elec_products,
        "as_of": today,
    }


if __name__ == "__main__":
    print("=" * 70)
    print("MIKA CI - DASHBOARD DATA AUDIT")
    print("MODE: READ-ONLY")
    print("=" * 70)

    counts = get_dashboard_counts()

    for key, value in counts.items():
        print(f"{key:25}: {value}")

    print("=" * 70)
    print("DATABASE ROWS WERE NOT WRITTEN")
    print("=" * 70)