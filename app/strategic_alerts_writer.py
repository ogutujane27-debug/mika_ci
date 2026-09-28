import sqlite3
from datetime import datetime

from strategic_alerts_engine import connect, collect_alerts


def resolve_competitor_id(conn, alert):
    """
    Resolve a competitor_id only when the database gives us
    an unambiguous match.

    Campaign alerts already carry competitor_id.
    Other alerts may identify a brand through competitor_name.
    """

    existing_id = alert.get("competitor_id")

    if existing_id is not None:
        return existing_id

    name = alert.get("competitor_name")
    brand = alert.get("brand")

    candidates = []

    if name:
        rows = conn.execute(
            """
            SELECT competitor_id
            FROM competitors
            WHERE competitor_name = ?
            """,
            (name,),
        ).fetchall()

        candidates.extend(row[0] for row in rows)

    if not candidates and brand:
        rows = conn.execute(
            """
            SELECT competitor_id
            FROM competitors
            WHERE brand_name = ?
            """,
            (brand,),
        ).fetchall()

        candidates.extend(row[0] for row in rows)

    candidates = sorted(set(candidates))

    if len(candidates) == 1:
        return candidates[0]

    return None


def insert_alerts(conn, alerts):
    inserted = 0
    skipped = 0

    created_at = datetime.now().isoformat(timespec="seconds")

    for alert in alerts:
        competitor_id = resolve_competitor_id(conn, alert)

        cursor = conn.execute(
            """
            INSERT OR IGNORE INTO strategic_alerts (
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
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                alert["alert_type"],
                alert["priority"],
                competitor_id,
                alert.get("competitor_name"),
                alert.get("brand"),
                alert.get("category"),
                alert["title"],
                alert["description"],
                alert["evidence_source"],
                alert.get("evidence_reference"),
                alert.get("evidence_count", 0),
                alert.get("period_start"),
                alert.get("period_end"),
                alert["confidence"],
                "OPEN",
                created_at,
            ),
        )

        if cursor.rowcount == 1:
            inserted += 1
        else:
            skipped += 1

    conn.commit()

    return inserted, skipped


def verify_persistence(conn):
    total = conn.execute(
        """
        SELECT COUNT(*)
        FROM strategic_alerts
        """
    ).fetchone()[0]

    print("\n" + "-" * 70)
    print("PERSISTED ALERT COUNT")
    print("-" * 70)
    print(f"TOTAL: {total}")

    print("\nALERTS BY TYPE:")

    rows = conn.execute(
        """
        SELECT alert_type, COUNT(*)
        FROM strategic_alerts
        GROUP BY alert_type
        ORDER BY alert_type
        """
    ).fetchall()

    for alert_type, count in rows:
        print(f"  {alert_type}: {count}")

    print("\nALERTS BY PRIORITY:")

    rows = conn.execute(
        """
        SELECT priority, COUNT(*)
        FROM strategic_alerts
        GROUP BY priority
        ORDER BY
            CASE priority
                WHEN 'HIGH' THEN 1
                WHEN 'MEDIUM' THEN 2
                WHEN 'LOW' THEN 3
                ELSE 4
            END
        """
    ).fetchall()

    for priority, count in rows:
        print(f"  {priority}: {count}")

    duplicate_groups = conn.execute(
        """
        SELECT
            alert_type,
            competitor_id,
            competitor_name,
            brand,
            category,
            title,
            period_start,
            period_end,
            COUNT(*)
        FROM strategic_alerts
        GROUP BY
            alert_type,
            competitor_id,
            competitor_name,
            brand,
            category,
            title,
            period_start,
            period_end
        HAVING COUNT(*) > 1
        """
    ).fetchall()

    print("\nDUPLICATE IDENTITY GROUPS:")

    if duplicate_groups:
        for row in duplicate_groups:
            print(row)
    else:
        print("  0")

    return total, duplicate_groups


def main():
    print("=" * 70)
    print("MIKA CI - PHASE 2H STRATEGIC ALERT PERSISTENCE")
    print("=" * 70)

    conn = connect()

    try:
        print("\nGenerating validated alerts from the Phase 2H engine...")

        alerts = collect_alerts(conn)

        print(f"Validated alerts received: {len(alerts)}")

        if len(alerts) != 20:
            raise RuntimeError(
                f"Expected 20 validated alerts, received {len(alerts)}. "
                "Persistence aborted."
            )

        print("\nWriting alerts to strategic_alerts...")

        inserted, skipped = insert_alerts(conn, alerts)

        print(f"Inserted: {inserted}")
        print(f"Skipped as existing: {skipped}")

        total, duplicate_groups = verify_persistence(conn)

        print("\n" + "=" * 70)

        if total == 20 and not duplicate_groups:
            print("PHASE 2H PERSISTENCE VERIFIED")
            print("20 unique strategic alerts are persisted.")
        else:
            print("PHASE 2H PERSISTENCE REQUIRES REVIEW")

        print("=" * 70)

    finally:
        conn.close()


if __name__ == "__main__":
    main()