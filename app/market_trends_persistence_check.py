import sqlite3
from collections import Counter
from pathlib import Path


DB_PATH = (
    Path(__file__).resolve().parent.parent
    / "data"
    / "mika_competitive_intel.db"
)


EXPECTED_COUNTS = {
    "PRODUCT_PRICE_MOVEMENT": 4,
    "BRAND_PRICE_TREND": 1,
    "CAMPAIGN_ACTIVITY": 1,
    "MULTI_COMPETITOR_CAMPAIGN": 1,
    "CAMPAIGN_CATEGORY_CONCENTRATION": 1,
    "CATALOGUE_PERSISTENCE": 3,
    "PRICE_CAMPAIGN_CONCURRENCY": 7,
}


def main():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row

    print("=" * 80)
    print("MIKA CI - PHASE 2F MARKET TRENDS PERSISTENCE AUDIT")
    print("=" * 80)
    print("Database writes: DISABLED")
    print()

    # ------------------------------------------------------------------
    # 1. TOTAL RECORDS
    # ------------------------------------------------------------------

    total = con.execute(
        """
        SELECT COUNT(*)
        FROM market_trends
        """
    ).fetchone()[0]

    print("1. TOTAL RECORDS")
    print("-" * 80)
    print(f"market_trends records: {total}")

    if total == 18:
        print("PASS - Expected 18 records.")
    else:
        print("FAIL - Expected 18 records.")

    # ------------------------------------------------------------------
    # 2. SIGNAL TYPE COUNTS
    # ------------------------------------------------------------------

    print()
    print("2. SIGNAL TYPE COUNTS")
    print("-" * 80)

    rows = con.execute(
        """
        SELECT
            signal_type,
            COUNT(*) AS count
        FROM market_trends
        GROUP BY signal_type
        ORDER BY signal_type
        """
    ).fetchall()

    actual_counts = {
        row["signal_type"]: row["count"]
        for row in rows
    }

    for signal_type, expected in EXPECTED_COUNTS.items():
        actual = actual_counts.get(signal_type, 0)

        status = "PASS" if actual == expected else "FAIL"

        print(
            f"{status} - "
            f"{signal_type}: {actual} "
            f"(expected {expected})"
        )

    unexpected_types = set(actual_counts) - set(
        EXPECTED_COUNTS
    )

    if unexpected_types:
        print(
            "FAIL - Unexpected signal types: "
            + ", ".join(sorted(unexpected_types))
        )
    else:
        print("PASS - No unexpected signal types.")

    # ------------------------------------------------------------------
    # 3. STATUS COUNTS
    # ------------------------------------------------------------------

    print()
    print("3. STATUS COUNTS")
    print("-" * 80)

    status_rows = con.execute(
        """
        SELECT
            status,
            COUNT(*) AS count
        FROM market_trends
        GROUP BY status
        ORDER BY status
        """
    ).fetchall()

    for row in status_rows:
        print(
            f"{row['status']}: {row['count']}"
        )

    # ------------------------------------------------------------------
    # 4. CONFIDENCE COUNTS
    # ------------------------------------------------------------------

    print()
    print("4. CONFIDENCE COUNTS")
    print("-" * 80)

    confidence_rows = con.execute(
        """
        SELECT
            confidence,
            COUNT(*) AS count
        FROM market_trends
        GROUP BY confidence
        ORDER BY confidence
        """
    ).fetchall()

    for row in confidence_rows:
        print(
            f"{row['confidence']}: {row['count']}"
        )

    # ------------------------------------------------------------------
    # 5. DUPLICATE NATURAL IDENTITIES
    # ------------------------------------------------------------------

    print()
    print("5. DUPLICATE NATURAL IDENTITIES")
    print("-" * 80)

    duplicates = con.execute(
        """
        SELECT
            signal_type,
            competitor_name,
            category,
            start_date,
            end_date,
            title,
            COUNT(*) AS count
        FROM market_trends
        GROUP BY
            signal_type,
            competitor_name,
            category,
            start_date,
            end_date,
            title
        HAVING COUNT(*) > 1
        """
    ).fetchall()

    if duplicates:
        print(
            f"FAIL - Duplicate identities found: "
            f"{len(duplicates)}"
        )

        for row in duplicates:
            print(
                f"  {row['signal_type']} | "
                f"{row['title']} | "
                f"count={row['count']}"
            )
    else:
        print(
            "PASS - No duplicate natural identities."
        )

    # ------------------------------------------------------------------
    # 6. PRICE MOVEMENT RECORDS
    # ------------------------------------------------------------------

    print()
    print("6. PRODUCT PRICE MOVEMENTS")
    print("-" * 80)

    price_rows = con.execute(
        """
        SELECT
            trend_id,
            competitor_name,
            category,
            title,
            start_date,
            end_date,
            evidence_count,
            confidence
        FROM market_trends
        WHERE signal_type = 'PRODUCT_PRICE_MOVEMENT'
        ORDER BY trend_id
        """
    ).fetchall()

    for row in price_rows:
        print(
            f"{row['trend_id']} | "
            f"{row['competitor_name']} | "
            f"{row['title']} | "
            f"{row['start_date']} -> {row['end_date']} | "
            f"evidence={row['evidence_count']} | "
            f"confidence={row['confidence']}"
        )

    if len(price_rows) == 4:
        print("PASS - Four product price movements persisted.")
    else:
        print("FAIL - Expected four product price movements.")

    # ------------------------------------------------------------------
    # 7. BRAND TREND
    # ------------------------------------------------------------------

    print()
    print("7. BRAND PRICE TREND")
    print("-" * 80)

    brand_rows = con.execute(
        """
        SELECT
            trend_id,
            competitor_name,
            status,
            title,
            start_date,
            end_date,
            evidence_count,
            confidence
        FROM market_trends
        WHERE signal_type = 'BRAND_PRICE_TREND'
        """
    ).fetchall()

    for row in brand_rows:
        print(
            f"{row['trend_id']} | "
            f"{row['competitor_name']} | "
            f"{row['status']} | "
            f"{row['title']} | "
            f"{row['start_date']} -> {row['end_date']} | "
            f"evidence={row['evidence_count']} | "
            f"confidence={row['confidence']}"
        )

    if (
        len(brand_rows) == 1
        and brand_rows[0]["competitor_name"] == "JTC"
        and brand_rows[0]["status"] == "TREND_SIGNAL"
        and brand_rows[0]["evidence_count"] == 3
    ):
        print(
            "PASS - JTC multi-product trend correctly persisted."
        )
    else:
        print(
            "FAIL - JTC brand trend does not match expected evidence."
        )

    # ------------------------------------------------------------------
    # 8. CAMPAIGN SIGNALS
    # ------------------------------------------------------------------

    print()
    print("8. CAMPAIGN SIGNALS")
    print("-" * 80)

    campaign_rows = con.execute(
        """
        SELECT
            signal_type,
            status,
            competitor_name,
            category,
            title,
            evidence_count,
            confidence
        FROM market_trends
        WHERE signal_type IN (
            'CAMPAIGN_ACTIVITY',
            'MULTI_COMPETITOR_CAMPAIGN',
            'CAMPAIGN_CATEGORY_CONCENTRATION'
        )
        ORDER BY signal_type
        """
    ).fetchall()

    for row in campaign_rows:
        print(
            f"{row['signal_type']} | "
            f"{row['status']} | "
            f"{row['title']} | "
            f"evidence={row['evidence_count']} | "
            f"confidence={row['confidence']}"
        )

    if len(campaign_rows) == 3:
        print("PASS - Three campaign-derived signals persisted.")
    else:
        print("FAIL - Expected three campaign-derived signals.")

    # ------------------------------------------------------------------
    # 9. CATALOGUE PERSISTENCE
    # ------------------------------------------------------------------

    print()
    print("9. CATALOGUE PERSISTENCE")
    print("-" * 80)

    catalogue_rows = con.execute(
        """
        SELECT
            competitor_name,
            evidence_count,
            status,
            confidence
        FROM market_trends
        WHERE signal_type = 'CATALOGUE_PERSISTENCE'
        ORDER BY competitor_name
        """
    ).fetchall()

    for row in catalogue_rows:
        print(
            f"{row['competitor_name']} | "
            f"products repeatedly observed="
            f"{row['evidence_count']} | "
            f"status={row['status']} | "
            f"confidence={row['confidence']}"
        )

    catalogue_competitors = {
        row["competitor_name"]
        for row in catalogue_rows
    }

    expected_catalogues = {
        "Bruhm",
        "Haier",
        "K-Elec",
    }

    if catalogue_competitors == expected_catalogues:
        print(
            "PASS - Bruhm, Haier and K-Elec persistence signals "
            "persisted."
        )
    else:
        print(
            "FAIL - Catalogue persistence coverage is incorrect."
        )

    # ------------------------------------------------------------------
    # 10. CONCURRENT SIGNALS
    # ------------------------------------------------------------------

    print()
    print("10. PRICE + CAMPAIGN CONCURRENT SIGNALS")
    print("-" * 80)

    concurrent_rows = con.execute(
        """
        SELECT
            trend_id,
            competitor_name,
            category,
            title,
            status,
            evidence_count,
            confidence
        FROM market_trends
        WHERE signal_type = 'PRICE_CAMPAIGN_CONCURRENCY'
        ORDER BY trend_id
        """
    ).fetchall()

    for row in concurrent_rows:
        print(
            f"{row['trend_id']} | "
            f"{row['competitor_name']} | "
            f"{row['title']} | "
            f"status={row['status']} | "
            f"confidence={row['confidence']}"
        )

    if len(concurrent_rows) == 7:
        print(
            "PASS - Seven pairwise concurrent signals persisted."
        )
    else:
        print(
            "FAIL - Expected seven concurrent signals."
        )

    wrong_status = [
        row
        for row in concurrent_rows
        if row["status"] != "CONCURRENT_SIGNAL"
    ]

    if not wrong_status:
        print(
            "PASS - All concurrency records use "
            "CONCURRENT_SIGNAL status."
        )
    else:
        print(
            "FAIL - Incorrect concurrency status detected."
        )

    # ------------------------------------------------------------------
    # 11. UNSUPPORTED POSITIVE SIGNALS
    # ------------------------------------------------------------------

    print()
    print("11. UNSUPPORTED SIGNAL CHECK")
    print("-" * 80)

    unsupported = con.execute(
        """
        SELECT
            signal_type,
            COUNT(*) AS count
        FROM market_trends
        WHERE signal_type IN (
            'MARKET_PRICE_TREND',
            'CATALOGUE_EXPANSION',
            'SOCIAL_TREND'
        )
        GROUP BY signal_type
        """
    ).fetchall()

    if unsupported:
        print(
            "FAIL - Unsupported positive signals were persisted."
        )

        for row in unsupported:
            print(
                f"  {row['signal_type']}: {row['count']}"
            )
    else:
        print(
            "PASS - No unsupported market-wide, "
            "catalogue-expansion or social-trend signals."
        )

    # ------------------------------------------------------------------
    # 12. TABLE INDEX
    # ------------------------------------------------------------------

    print()
    print("12. UNIQUE INDEX")
    print("-" * 80)

    indexes = con.execute(
        """
        PRAGMA index_list(market_trends)
        """
    ).fetchall()

    index_names = {
        row["name"]
        for row in indexes
    }

    if "ux_market_trends_identity" in index_names:
        print(
            "PASS - Natural identity unique index exists."
        )
    else:
        print(
            "FAIL - Natural identity unique index is missing."
        )

    # ------------------------------------------------------------------
    # FINAL RESULT
    # ------------------------------------------------------------------

    print()
    print("=" * 80)
    print("PHASE 2F PERSISTENCE AUDIT RESULT")
    print("=" * 80)

    checks = []

    checks.append(total == 18)
    checks.append(actual_counts == EXPECTED_COUNTS)
    checks.append(not duplicates)
    checks.append(len(price_rows) == 4)
    checks.append(
        len(brand_rows) == 1
        and brand_rows[0]["competitor_name"] == "JTC"
        and brand_rows[0]["status"] == "TREND_SIGNAL"
        and brand_rows[0]["evidence_count"] == 3
    )
    checks.append(len(campaign_rows) == 3)
    checks.append(catalogue_competitors == expected_catalogues)
    checks.append(len(concurrent_rows) == 7)
    checks.append(not wrong_status)
    checks.append(not unsupported)
    checks.append(
        "ux_market_trends_identity" in index_names
    )

    if all(checks):
        print()
        print("OVERALL STATUS: PASS")
        print()
        print(
            "Phase 2F Market Trends persistence is "
            "verified and ready to freeze."
        )
    else:
        print()
        print("OVERALL STATUS: REVIEW REQUIRED")
        print()
        print(
            "One or more persistence checks failed."
        )

    print()
    print("Database writes: DISABLED")
    print("No database changes were performed.")

    con.close()


if __name__ == "__main__":
    main()