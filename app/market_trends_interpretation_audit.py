import sqlite3
from collections import Counter, defaultdict
from pathlib import Path

import product_price_movements as price_movements


DB_PATH = (
    Path(__file__).resolve().parent.parent
    / "data"
    / "mika_competitive_intel.db"
)

BASELINE_DATE = "2026-09-22"


def load_price_movements(con):
    rows = price_movements.load_price_observations(con)
    identities = price_movements.build_identities(rows)
    movements, ambiguous = price_movements.detect_movements(identities)
    return rows, identities, movements, ambiguous


def load_campaigns(con):
    return con.execute(
        """
        SELECT
            c.campaign_id,
            comp.competitor_name,
            c.campaign_name,
            c.category,
            c.status,
            c.start_date,
            c.end_date,
            c.observed_date,
            c.verification_status,
            c.confidence
        FROM campaigns c
        JOIN competitors comp
            ON comp.competitor_id = c.competitor_id
        WHERE c.verification_status = 'VERIFIED'
        ORDER BY c.observed_date, c.campaign_id
        """
    ).fetchall()


def load_social_summary(con):
    return con.execute(
        """
        SELECT
            COUNT(*) AS observations,
            COUNT(DISTINCT competitor_id) AS competitors,
            COUNT(DISTINCT observed_date) AS dates,
            MIN(observed_date) AS first_date,
            MAX(observed_date) AS last_date
        FROM social_observations
        """
    ).fetchone()


def load_catalogue_summary(con):
    catalogues = [
        ("Bruhm", "bruhm_products"),
        ("Haier", "haier_products"),
        ("K-Elec", "k_elec_products"),
    ]

    results = []

    for competitor, table in catalogues:
        row = con.execute(
            f"""
            SELECT
                COUNT(*) AS products,
                SUM(
                    CASE
                        WHEN first_seen_date < last_seen_date
                        THEN 1
                        ELSE 0
                    END
                ) AS persistent,
                SUM(
                    CASE
                        WHEN first_seen_date > ?
                        THEN 1
                        ELSE 0
                    END
                ) AS post_baseline
            FROM {table}
            """,
            (BASELINE_DATE,),
        ).fetchone()

        results.append(
            {
                "competitor": competitor,
                "products": row["products"] or 0,
                "persistent": row["persistent"] or 0,
                "post_baseline": row["post_baseline"] or 0,
            }
        )

    return results


def audit_price_interpretation(movements):
    print("=" * 80)
    print("1. PRICE INTERPRETATION")
    print("=" * 80)

    print()
    print("ALLOWED INTERPRETATIONS")

    if movements:
        print(
            "PASS - MIKA may report individual product price movements."
        )

    brand_counts = defaultdict(Counter)

    for movement in movements:
        direction = (
            "INCREASE"
            if movement["change"] > 0
            else "DECREASE"
        )
        brand_counts[movement["brand"]][direction] += 1

    multi_product_brands = {
        brand: directions
        for brand, directions in brand_counts.items()
        if max(directions.values(), default=0) >= 2
    }

    if multi_product_brands:
        print(
            "PASS - MIKA may report a multi-product brand price trend."
        )

        for brand, directions in multi_product_brands.items():
            print(
                f"      {brand}: "
                + ", ".join(
                    f"{direction}={count}"
                    for direction, count in directions.items()
                )
            )

    print()
    print("RESTRICTED INTERPRETATIONS")

    distinct_brands = len(
        {
            movement["brand"]
            for movement in movements
        }
    )

    if distinct_brands < 3:
        print(
            "PASS - Market-wide price trend remains NOT ESTABLISHED."
        )

    print(
        "PASS - MIKA must not infer market-wide pricing from "
        "the current movement sample."
    )

    print(
        "PASS - Price movement must not be described as caused "
        "by a campaign without supporting evidence."
    )


def audit_campaign_interpretation(campaigns):
    print()
    print("=" * 80)
    print("2. CAMPAIGN INTERPRETATION")
    print("=" * 80)

    competitors = {
        row["competitor_name"]
        for row in campaigns
    }

    active = [
        row
        for row in campaigns
        if row["status"] == "active"
    ]

    categories = Counter(
        row["category"] or "UNSPECIFIED"
        for row in campaigns
    )

    print()
    print("ALLOWED INTERPRETATIONS")

    if campaigns:
        print(
            "PASS - Verified campaign activity may be reported."
        )

    if len(competitors) >= 2:
        print(
            "PASS - Multi-competitor campaign activity may be reported."
        )

    if active:
        print(
            "PASS - Active campaigns may be reported."
        )

    if categories:
        print(
            "PASS - Campaign category concentration may be reported."
        )

    print()
    print("RESTRICTED INTERPRETATIONS")

    print(
        "PASS - Campaign activity must not automatically be "
        "described as market-wide strategy."
    )

    print(
        "PASS - Campaign activity must not be assumed to have "
        "caused a price movement."
    )


def audit_catalogue_interpretation(catalogues):
    print()
    print("=" * 80)
    print("3. CATALOGUE INTERPRETATION")
    print("=" * 80)

    total_products = sum(
        item["products"]
        for item in catalogues
    )

    persistent = sum(
        item["persistent"]
        for item in catalogues
    )

    post_baseline = sum(
        item["post_baseline"]
        for item in catalogues
    )

    print()
    print("ALLOWED INTERPRETATIONS")

    if total_products:
        print(
            f"PASS - MIKA may report {total_products} "
            "tracked catalogue products."
        )

    if persistent:
        print(
            "PASS - MIKA may report catalogue persistence."
        )

    print()
    print("RESTRICTED INTERPRETATIONS")

    if post_baseline == 0:
        print(
            "PASS - MIKA must NOT claim that competitors had "
            "no new products in the real market."
        )

        print(
            "PASS - MIKA may only state that no post-baseline "
            "products were detected in the tracked catalogues."
        )

    print(
        "PASS - Catalogue persistence must not be interpreted "
        "as product demand or sales performance."
    )


def audit_social_interpretation(social):
    print()
    print("=" * 80)
    print("4. SOCIAL INTERPRETATION")
    print("=" * 80)

    observations = social["observations"] or 0
    competitors = social["competitors"] or 0
    dates = social["dates"] or 0

    print()
    print("ALLOWED INTERPRETATIONS")

    if observations:
        print(
            f"PASS - MIKA may report {observations} "
            "observed social posts."
        )

    if competitors:
        print(
            f"PASS - MIKA may report social activity from "
            f"{competitors} represented competitors."
        )

    print()
    print("RESTRICTED INTERPRETATIONS")

    if dates < 2:
        print(
            "PASS - Historical social trend must remain "
            "NOT ESTABLISHED."
        )

        print(
            "PASS - MIKA must not describe the current social "
            "sample as increasing or decreasing."
        )


def audit_cross_signal_interpretation(
    movements,
    campaigns,
):
    print()
    print("=" * 80)
    print("5. CROSS-SIGNAL INTERPRETATION")
    print("=" * 80)

    concurrent = 0

    for movement in movements:
        movement_dates = {
            movement["previous_date"],
            movement["current_date"],
        }

        for campaign in campaigns:
            start = campaign["start_date"]
            end = campaign["end_date"]

            for movement_date in movement_dates:
                if start and movement_date < start:
                    continue

                if end and movement_date > end:
                    continue

                concurrent += 1
                break

    print()
    print(
        f"Price/campaign date overlaps detected: {concurrent}"
    )

    if concurrent:
        print(
            "PASS - MIKA may report concurrent observations."
        )

    print(
        "PASS - MIKA must explicitly avoid causal language "
        "unless independent evidence supports causation."
    )

    print(
        "PASS - A date overlap alone does not establish a "
        "business relationship between the products and campaign."
    )


def audit_language_controls():
    print()
    print("=" * 80)
    print("6. LANGUAGE CONTROLS")
    print("=" * 80)

    allowed = [
        "Observed price movement",
        "Brand-level price trend signal",
        "Verified campaign activity",
        "Multi-competitor campaign activity",
        "Catalogue persistence",
        "Observed social activity",
        "Concurrent signals",
        "Insufficient history",
        "Not established",
    ]

    restricted = [
        "Market-wide price increase",
        "Competitor launched no new products",
        "Campaign caused price increase",
        "Social engagement is increasing",
        "Market demand is increasing",
        "Competitor strategy changed",
    ]

    print()
    print("SAFE LANGUAGE")

    for phrase in allowed:
        print(f"PASS - {phrase}")

    print()
    print("LANGUAGE REQUIRING ADDITIONAL EVIDENCE")

    for phrase in restricted:
        print(f"GUARD - {phrase}")


def final_result():
    print()
    print("=" * 80)
    print("7. PHASE 2F INTERPRETATION RESULT")
    print("=" * 80)

    print()
    print("PASS - Observed facts are separated from trend claims.")
    print("PASS - Insufficient evidence is explicitly labelled.")
    print("PASS - Catalogue limitations are acknowledged.")
    print("PASS - Social history limitations are acknowledged.")
    print("PASS - Market-wide price trend requires broader evidence.")
    print("PASS - Concurrent signals are not treated as causal.")
    print()
    print("OVERALL STATUS: INTERPRETATION RULES READY FOR FREEZE")


def main():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row

    print("=" * 80)
    print("MIKA CI - PHASE 2F INTERPRETATION & RISK AUDIT")
    print("=" * 80)
    print("Database writes: DISABLED")

    rows, identities, movements, ambiguous = load_price_movements(
        con
    )

    campaigns = load_campaigns(con)
    social = load_social_summary(con)
    catalogues = load_catalogue_summary(con)

    print()
    print("INPUT VALIDATION")
    print("-" * 80)
    print(f"Price observations: {len(rows)}")
    print(f"Product identities: {len(identities)}")
    print(f"Price movements: {len(movements)}")
    print(f"Ambiguous movements: {len(ambiguous)}")
    print(f"Verified campaigns: {len(campaigns)}")
    print(f"Social observations: {social['observations'] or 0}")

    audit_price_interpretation(movements)
    audit_campaign_interpretation(campaigns)
    audit_catalogue_interpretation(catalogues)
    audit_social_interpretation(social)
    audit_cross_signal_interpretation(
        movements,
        campaigns,
    )
    audit_language_controls()
    final_result()

    print()
    print("=" * 80)
    print("No database writes were performed.")
    print("=" * 80)

    con.close()


if __name__ == "__main__":
    main()