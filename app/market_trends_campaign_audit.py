import sqlite3
from collections import Counter
from pathlib import Path


DB_PATH = Path(__file__).resolve().parent.parent / "data" / "mika_competitive_intel.db"


def main():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row

    print("=" * 80)
    print("MIKA CI - PHASE 2F CAMPAIGN TREND SIGNAL AUDIT")
    print("=" * 80)
    print("Database writes: DISABLED")

    print()
    print("CAMPAIGN BASE DATA")
    print("-" * 80)

    rows = con.execute(
        """
        SELECT
            c.campaign_id,
            c.campaign_name,
            c.campaign_type,
            c.category,
            c.offer_value,
            c.start_date,
            c.end_date,
            c.status,
            c.verification_status,
            c.confidence,
            c.observed_date,
            comp.competitor_name AS competitor
        FROM campaigns c
        JOIN competitors comp
            ON comp.competitor_id = c.competitor_id
        ORDER BY c.observed_date, comp.competitor_name, c.campaign_id
        """
    ).fetchall()

    print(f"Campaign records: {len(rows)}")

    print()
    print("CAMPAIGNS BY COMPETITOR")
    print("-" * 80)

    competitor_counts = Counter(row["competitor"] for row in rows)

    for competitor, count in sorted(competitor_counts.items()):
        print(f"{competitor}: {count}")

    print()
    print("CAMPAIGNS BY TYPE")
    print("-" * 80)

    type_counts = Counter(
        row["campaign_type"] or "UNSPECIFIED"
        for row in rows
    )

    for campaign_type, count in sorted(type_counts.items()):
        print(f"{campaign_type}: {count}")

    print()
    print("CAMPAIGNS BY CATEGORY")
    print("-" * 80)

    category_counts = Counter(
        row["category"] or "UNSPECIFIED"
        for row in rows
    )

    for category, count in sorted(category_counts.items()):
        print(f"{category}: {count}")

    print()
    print("CAMPAIGN STATUS")
    print("-" * 80)

    status_counts = Counter(
        row["status"] or "UNSPECIFIED"
        for row in rows
    )

    for status, count in sorted(status_counts.items()):
        print(f"{status}: {count}")

    print()
    print("VERIFICATION")
    print("-" * 80)

    verification_counts = Counter(
        row["verification_status"] or "UNSPECIFIED"
        for row in rows
    )

    for verification, count in sorted(verification_counts.items()):
        print(f"{verification}: {count}")

    print()
    print("CAMPAIGN DETAILS")
    print("-" * 80)

    for index, row in enumerate(rows, 1):
        print()
        print(f"{index}. {row['competitor']} | {row['campaign_name']}")
        print(f"   Type: {row['campaign_type']}")
        print(f"   Category: {row['category']}")
        print(f"   Offer: {row['offer_value']}")
        print(f"   Start: {row['start_date']}")
        print(f"   End: {row['end_date']}")
        print(f"   Status: {row['status']}")
        print(f"   Observed: {row['observed_date']}")
        print(f"   Verification: {row['verification_status']}")
        print(f"   Confidence: {row['confidence']}")

    print()
    print("=" * 80)
    print("CAMPAIGN TREND SIGNAL READINESS")
    print("=" * 80)

    if len(rows) >= 2:
        print("Campaign activity signal: AVAILABLE")
    else:
        print("Campaign activity signal: NOT AVAILABLE")

    if len(competitor_counts) >= 2:
        print("Multi-competitor campaign signal: AVAILABLE")
    else:
        print("Multi-competitor campaign signal: NOT YET ESTABLISHED")

    active_count = sum(
        1
        for row in rows
        if (row["status"] or "").lower() == "active"
    )

    if active_count >= 2:
        print("Multiple active campaigns: AVAILABLE")
    else:
        print("Multiple active campaigns: NOT YET ESTABLISHED")

    print()
    print("Audit complete. No database writes were performed.")

    con.close()


if __name__ == "__main__":
    main()