import sqlite3
from datetime import datetime


DB = r".\data\mika_competitive_intel.db"


def connect():
    return sqlite3.connect(DB)


def get_price_movement_alerts(conn):
    rows = conn.execute("""
        SELECT
            trend_id,
            competitor_name,
            category,
            title,
            description,
            evidence_count,
            start_date,
            end_date,
            confidence
        FROM market_trends
        WHERE signal_type = 'PRODUCT_PRICE_MOVEMENT'
          AND status = 'OBSERVED'
        ORDER BY start_date, competitor_name, title
    """).fetchall()

    alerts = []

    for row in rows:
        (
            trend_id,
            competitor_name,
            category,
            title,
            description,
            evidence_count,
            start_date,
            end_date,
            confidence,
        ) = row

        priority = "MEDIUM"

        text = f"{title} {description}".lower()

        # Deterministic severity rule based only on documented percentage movement.
        if "%" in text:
            import re

            percentages = re.findall(r"([0-9]+(?:\.[0-9]+)?)%", text)

            if percentages:
                largest = max(float(value) for value in percentages)

                if largest >= 20:
                    priority = "HIGH"
                elif largest >= 5:
                    priority = "MEDIUM"
                else:
                    priority = "LOW"

        alerts.append({
            "alert_type": "PRICE_MOVEMENT",
            "priority": priority,
            "competitor_name": competitor_name,
            "category": category,
            "title": title,
            "description": description,
            "evidence_source": "market_trends",
            "evidence_reference": f"trend_id={trend_id}",
            "evidence_count": evidence_count,
            "period_start": start_date,
            "period_end": end_date,
            "confidence": confidence,
        })

    return alerts


def get_campaign_activity_alerts(conn):
    rows = conn.execute("""
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
        WHERE verification_status = 'VERIFIED'
          AND status IN ('active', 'upcoming')
        ORDER BY
            CASE status
                WHEN 'active' THEN 1
                WHEN 'upcoming' THEN 2
                ELSE 3
            END,
            competitor_id,
            campaign_id
    """).fetchall()

    alerts = []

    for row in rows:
        (
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
            observed_date,
        ) = row

        period_start = start_date or observed_date
        period_end = end_date

        alerts.append({
            "alert_type": "CAMPAIGN_ACTIVITY",
            "priority": "MEDIUM",
            "competitor_id": competitor_id,
            "category": category,
            "title": f"{campaign_name} - {status.upper()}",
            "description": (
                f"Verified {status} campaign activity. "
                f"Offer: {offer_value or 'Not specified'}."
            ),
            "evidence_source": "campaigns",
            "evidence_reference": f"campaign_id={campaign_id}",
            "evidence_count": 1,
            "period_start": period_start,
            "period_end": period_end,
            "confidence": confidence,
        })

    return alerts


def get_market_signal_alerts(conn):
    rows = conn.execute("""
        SELECT
            trend_id,
            signal_type,
            competitor_name,
            category,
            title,
            description,
            start_date,
            end_date,
            evidence_count,
            confidence
        FROM market_trends
        WHERE signal_type IN (
            'MULTI_COMPETITOR_CAMPAIGN',
            'CAMPAIGN_CATEGORY_CONCENTRATION',
            'PRICE_CAMPAIGN_CONCURRENCY'
        )
        AND status IN ('OBSERVED', 'CONCURRENT_SIGNAL')
        ORDER BY
            signal_type,
            start_date,
            title
    """).fetchall()

    alerts = []

    priority_map = {
        "MULTI_COMPETITOR_CAMPAIGN": "HIGH",
        "CAMPAIGN_CATEGORY_CONCENTRATION": "MEDIUM",
        "PRICE_CAMPAIGN_CONCURRENCY": "MEDIUM",
    }

    for row in rows:
        (
            trend_id,
            signal_type,
            competitor_name,
            category,
            title,
            description,
            start_date,
            end_date,
            evidence_count,
            confidence,
        ) = row

        alerts.append({
            "alert_type": signal_type,
            "priority": priority_map.get(signal_type, "MEDIUM"),
            "competitor_name": competitor_name,
            "category": category,
            "title": title,
            "description": description,
            "evidence_source": "market_trends",
            "evidence_reference": f"trend_id={trend_id}",
            "evidence_count": evidence_count,
            "period_start": start_date,
            "period_end": end_date,
            "confidence": confidence,
        })

    return alerts


def get_catalogue_persistence_alerts(conn):
    rows = conn.execute("""
        SELECT
            trend_id,
            competitor_name,
            category,
            title,
            description,
            evidence_count,
            start_date,
            end_date,
            confidence
        FROM market_trends
        WHERE signal_type = 'CATALOGUE_PERSISTENCE'
          AND status = 'OBSERVED'
        ORDER BY competitor_name, title
    """).fetchall()

    alerts = []

    for row in rows:
        (
            trend_id,
            competitor_name,
            category,
            title,
            description,
            evidence_count,
            start_date,
            end_date,
            confidence,
        ) = row

        alerts.append({
            "alert_type": "CATALOGUE_PERSISTENCE",
            "priority": "LOW",
            "competitor_name": competitor_name,
            "category": category,
            "title": title,
            "description": description,
            "evidence_source": "market_trends",
            "evidence_reference": f"trend_id={trend_id}",
            "evidence_count": evidence_count,
            "period_start": start_date,
            "period_end": end_date,
            "confidence": confidence,
        })

    return alerts


def get_evidence_gap_alerts(conn):
    competitors = conn.execute("""
        SELECT
            competitor_id,
            competitor_name,
            brand_name
        FROM competitors
        ORDER BY competitor_id
    """).fetchall()

    alerts = []

    for competitor_id, competitor_name, brand_name in competitors:

        social_sources = conn.execute("""
            SELECT COUNT(*)
            FROM social_sources
            WHERE competitor_id = ?
              AND verification_status = 'VERIFIED'
        """, (competitor_id,)).fetchone()[0]

        social_observations = conn.execute("""
            SELECT COUNT(*)
            FROM social_observations
            WHERE competitor_id = ?
        """, (competitor_id,)).fetchone()[0]

        campaign_count = conn.execute("""
            SELECT COUNT(*)
            FROM campaigns
            WHERE competitor_id = ?
              AND verification_status = 'VERIFIED'
        """, (competitor_id,)).fetchone()[0]

        price_count = conn.execute("""
            SELECT COUNT(*)
            FROM price_observations p
            JOIN findings f
              ON f.finding_id = p.finding_id
            WHERE f.competitor_id = ?
        """, (competitor_id,)).fetchone()[0]

        # Evidence gap means limited verified evidence is currently
        # available. It does NOT mean that no activity exists.
        evidence_dimensions = sum([
            social_observations > 0,
            campaign_count > 0,
            price_count > 0,
        ])

        if evidence_dimensions == 0:
            alerts.append({
                "alert_type": "EVIDENCE_GAP",
                "priority": "LOW",
                "competitor_id": competitor_id,
                "competitor_name": competitor_name,
                "brand": brand_name,
                "title": f"Limited verified evidence coverage - {competitor_name}",
                "description": (
                    "No verified observations are currently available across "
                    "the monitored social, campaign, and price evidence "
                    "dimensions for the current database window."
                ),
                "evidence_source": "evidence_coverage",
                "evidence_reference": (
                    f"social_sources={social_sources};"
                    f"social_observations={social_observations};"
                    f"campaigns={campaign_count};"
                    f"price_observations={price_count}"
                ),
                "evidence_count": 0,
                "period_start": None,
                "period_end": None,
                "confidence": "MEDIUM",
            })

    return alerts


def collect_alerts(conn):
    alerts = []

    alerts.extend(get_price_movement_alerts(conn))
    alerts.extend(get_campaign_activity_alerts(conn))
    alerts.extend(get_market_signal_alerts(conn))
    alerts.extend(get_catalogue_persistence_alerts(conn))

    return alerts


def print_alerts(alerts):
    print("\n" + "=" * 70)
    print("PHASE 2H - STRATEGIC ALERT ENGINE")
    print("READ-ONLY ALERT PREVIEW")
    print("=" * 70)

    print(f"\nTOTAL ALERTS GENERATED: {len(alerts)}")

    by_type = {}

    for alert in alerts:
        alert_type = alert["alert_type"]
        by_type[alert_type] = by_type.get(alert_type, 0) + 1

    print("\nALERTS BY TYPE:")

    for alert_type in sorted(by_type):
        print(f"  {alert_type}: {by_type[alert_type]}")

    by_priority = {}

    for alert in alerts:
        priority = alert["priority"]
        by_priority[priority] = by_priority.get(priority, 0) + 1

    print("\nALERTS BY PRIORITY:")

    for priority in ("HIGH", "MEDIUM", "LOW"):
        if priority in by_priority:
            print(f"  {priority}: {by_priority[priority]}")

    print("\n" + "-" * 70)
    print("ALERT DETAILS")
    print("-" * 70)

    for number, alert in enumerate(alerts, start=1):
        print(f"\n[{number}] {alert['priority']} | {alert['alert_type']}")

        if alert.get("competitor_name"):
            print(f"Competitor: {alert['competitor_name']}")

        if alert.get("brand"):
            print(f"Brand: {alert['brand']}")

        if alert.get("category"):
            print(f"Category: {alert['category']}")

        print(f"Title: {alert['title']}")
        print(f"Description: {alert['description']}")
        print(f"Evidence: {alert['evidence_source']}")
        print(f"Reference: {alert['evidence_reference']}")
        print(f"Evidence count: {alert['evidence_count']}")

        if alert.get("period_start") or alert.get("period_end"):
            print(
                f"Period: "
                f"{alert.get('period_start') or 'N/A'}"
                f" -> "
                f"{alert.get('period_end') or 'N/A'}"
            )

        print(f"Confidence: {alert['confidence']}")

    print("\n" + "=" * 70)
    print("READ-ONLY PREVIEW COMPLETE")
    print("NO strategic_alerts ROWS WERE WRITTEN")
    print("=" * 70)


def main():
    conn = connect()

    try:
        alerts = collect_alerts(conn)
        print_alerts(alerts)
    finally:
        conn.close()


if __name__ == "__main__":
    main()