import sqlite3
from pathlib import Path

import product_price_movements as price_movements


DB_PATH = Path(__file__).resolve().parent.parent / "data" / "mika_competitive_intel.db"


def load_price_signals(con):
    rows = price_movements.load_price_observations(con)
    identities = price_movements.build_identities(rows)
    movements, ambiguous = price_movements.detect_movements(identities)

    return rows, identities, movements, ambiguous


def audit_price_signals(movements):
    print("=" * 80)
    print("PRICE SIGNAL DEFINITIONS")
    print("=" * 80)

    product_movements = len(movements)

    brand_direction = {}
    for item in movements:
        brand = item["brand"]
        direction = "INCREASE" if item["change"] > 0 else "DECREASE"

        brand_direction.setdefault(brand, {})
        brand_direction[brand][direction] = (
            brand_direction[brand].get(direction, 0) + 1
        )

    multi_product_brands = {
        brand: directions
        for brand, directions in brand_direction.items()
        if sum(directions.values()) >= 2
    }

    distinct_brands = len(
        {
            item["brand"]
            for item in movements
        }
    )

    print()
    print("1. PRODUCT PRICE MOVEMENT")
    print("   Rule: same product identity, at least two observations,")
    print("   valid price change, and no ambiguous same-day identity.")
    print(f"   Current qualifying movements: {product_movements}")
    print("   Status: AVAILABLE" if product_movements else "   Status: NOT AVAILABLE")

    print()
    print("2. BRAND PRICE TREND")
    print("   Rule: at least two products from the same brand")
    print("   move in the same direction during the observed period.")

    if multi_product_brands:
        print("   Current qualifying brands:")
        for brand, directions in multi_product_brands.items():
            print(f"   - {brand}: {directions}")
        print("   Status: AVAILABLE")
    else:
        print("   Current qualifying brands: none")
        print("   Status: NOT YET ESTABLISHED")

    print()
    print("3. MARKET-WIDE PRICE TREND")
    print("   Rule: at least three distinct brands and at least")
    print("   three products move in the same direction.")
    print(f"   Distinct brands represented in movements: {distinct_brands}")

    if distinct_brands >= 3 and len(movements) >= 3:
        print("   Status: POTENTIALLY AVAILABLE")
    else:
        print("   Status: NOT YET ESTABLISHED")


def audit_campaign_signals(con):
    print()
    print("=" * 80)
    print("CAMPAIGN SIGNAL DEFINITIONS")
    print("=" * 80)

    rows = con.execute(
        """
        SELECT
            c.campaign_id,
            comp.competitor_name,
            c.campaign_type,
            c.category,
            c.status,
            c.verification_status
        FROM campaigns c
        JOIN competitors comp
            ON comp.competitor_id = c.competitor_id
        """
    ).fetchall()

    verified = [
        row for row in rows
        if row["verification_status"] == "VERIFIED"
    ]

    active = [
        row for row in verified
        if row["status"] == "active"
    ]

    competitors = {
        row["competitor_name"]
        for row in verified
    }

    categories = {}

    for row in verified:
        category = row["category"] or "UNSPECIFIED"
        categories[category] = categories.get(category, 0) + 1

    print()
    print("1. CAMPAIGN ACTIVITY")
    print("   Rule: verified campaign records exist.")
    print(f"   Verified campaigns: {len(verified)}")
    print("   Status: AVAILABLE" if verified else "   Status: NOT AVAILABLE")

    print()
    print("2. MULTI-COMPETITOR CAMPAIGN ACTIVITY")
    print("   Rule: verified campaigns from at least two competitors.")
    print(f"   Competitors represented: {len(competitors)}")

    if len(competitors) >= 2:
        print("   Status: AVAILABLE")
    else:
        print("   Status: NOT YET ESTABLISHED")

    print()
    print("3. ACTIVE CAMPAIGN SIGNAL")
    print("   Rule: at least one verified campaign has status='active'.")
    print(f"   Active campaigns: {len(active)}")

    if active:
        print("   Status: AVAILABLE")
    else:
        print("   Status: NOT CURRENTLY OBSERVED")

    print()
    print("4. CAMPAIGN CATEGORY CONCENTRATION")
    print("   Rule: compare verified campaign counts by category.")

    for category, count in sorted(
        categories.items(),
        key=lambda item: (-item[1], item[0]),
    ):
        print(f"   - {category}: {count}")

    if categories:
        print("   Status: AVAILABLE")
    else:
        print("   Status: NOT AVAILABLE")


def audit_catalogue_signals(con):
    print()
    print("=" * 80)
    print("CATALOGUE SIGNAL DEFINITIONS")
    print("=" * 80)

    catalogues = [
        ("Bruhm", "bruhm_products"),
        ("Haier", "haier_products"),
        ("K-Elec", "k_elec_products"),
    ]

    total_products = 0
    repeated_products = 0
    post_baseline = 0

    for competitor, table in catalogues:
        rows = con.execute(
            f"""
            SELECT first_seen_date, last_seen_date
            FROM {table}
            """
        ).fetchall()

        total_products += len(rows)

        repeated = [
            row for row in rows
            if row["first_seen_date"] < row["last_seen_date"]
        ]

        new_after_baseline = [
            row for row in rows
            if row["first_seen_date"] > "2026-09-22"
        ]

        repeated_products += len(repeated)
        post_baseline += len(new_after_baseline)

        print()
        print(competitor)
        print(f"   Products tracked: {len(rows)}")
        print(f"   Repeated observations: {len(repeated)}")
        print(f"   Post-baseline products: {len(new_after_baseline)}")

    print()
    print("1. CATALOGUE PRESENCE")
    print("   Rule: tracked products exist in the catalogue layer.")
    print(f"   Total tracked products: {total_products}")
    print("   Status: AVAILABLE" if total_products else "   Status: NOT AVAILABLE")

    print()
    print("2. CATALOGUE PERSISTENCE")
    print("   Rule: products have first_seen_date earlier than last_seen_date.")
    print(f"   Products with repeated observations: {repeated_products}")

    if repeated_products:
        print("   Status: AVAILABLE")
    else:
        print("   Status: NOT YET ESTABLISHED")

    print()
    print("3. CATALOGUE EXPANSION")
    print("   Rule: products first observed after the 2026-09-22 baseline.")
    print(f"   Post-baseline products: {post_baseline}")

    if post_baseline:
        print("   Status: AVAILABLE")
    else:
        print("   Status: NOT YET ESTABLISHED")


def audit_social_signals(con):
    print()
    print("=" * 80)
    print("SOCIAL SIGNAL DEFINITIONS")
    print("=" * 80)

    row = con.execute(
        """
        SELECT
            COUNT(*),
            COUNT(DISTINCT competitor_id),
            COUNT(DISTINCT observed_date),
            MIN(observed_date),
            MAX(observed_date)
        FROM social_observations
        """
    ).fetchone()

    observations = row[0]
    competitors = row[1]
    dates = row[2]
    first_date = row[3]
    last_date = row[4]

    print()
    print("1. SOCIAL ACTIVITY")
    print("   Rule: verified social observations exist.")
    print(f"   Observations: {observations}")
    print(f"   Competitors represented: {competitors}")
    print(f"   Observation dates: {dates}")
    print(f"   Date range: {first_date} to {last_date}")

    if observations:
        print("   Status: AVAILABLE")
    else:
        print("   Status: NOT AVAILABLE")

    print()
    print("2. SOCIAL TREND")
    print("   Rule: activity must exist across multiple observation dates")
    print("   before a directional social trend is considered established.")

    if dates >= 2:
        print("   Status: AVAILABLE")
    else:
        print("   Status: NOT YET ESTABLISHED")


def audit_cross_signals(movements, con):
    print()
    print("=" * 80)
    print("CROSS-SIGNAL DEFINITIONS")
    print("=" * 80)

    campaign_count = con.execute(
        """
        SELECT COUNT(*)
        FROM campaigns
        WHERE verification_status='VERIFIED'
        """
    ).fetchone()[0]

    social_count = con.execute(
        """
        SELECT COUNT(*)
        FROM social_observations
        """
    ).fetchone()[0]

    print()
    print("1. PRICE + CAMPAIGN")
    print("   A price movement and campaign activity can be reported")
    print("   as concurrent signals when their dates overlap.")
    print(f"   Price movements: {len(movements)}")
    print(f"   Verified campaigns: {campaign_count}")

    if movements and campaign_count:
        print("   Status: AVAILABLE FOR CONCURRENT-SIGNAL ANALYSIS")
    else:
        print("   Status: NOT AVAILABLE")

    print()
    print("2. CAMPAIGN + SOCIAL")
    print("   Campaign and social activity may be compared when")
    print("   both have sufficient date coverage.")
    print(f"   Verified campaigns: {campaign_count}")
    print(f"   Social observations: {social_count}")

    if campaign_count and social_count:
        print("   Status: AVAILABLE FOR CONCURRENT-SIGNAL ANALYSIS")
    else:
        print("   Status: NOT AVAILABLE")

    print()
    print("3. CAUSALITY")
    print("   Rule: correlation between signals must NOT be treated")
    print("   as proof that one signal caused another.")
    print("   Status: INTERPRETATION GUARDRAIL")


def main():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row

    print("=" * 80)
    print("MIKA CI - PHASE 2F TREND SIGNAL DEFINITION AUDIT")
    print("=" * 80)
    print("Database writes: DISABLED")

    rows, identities, movements, ambiguous = load_price_signals(con)

    print()
    print("BASE DATA")
    print("-" * 80)
    print(f"Price observations: {len(rows)}")
    print(f"Product identities: {len(identities)}")
    print(f"Movement candidates: {len(movements)}")
    print(f"Ambiguous same-day cases: {len(ambiguous)}")

    audit_price_signals(movements)
    audit_campaign_signals(con)
    audit_catalogue_signals(con)
    audit_social_signals(con)
    audit_cross_signals(movements, con)

    print()
    print("=" * 80)
    print("PHASE 2F SIGNAL DEFINITION AUDIT COMPLETE")
    print("=" * 80)
    print("No database writes were performed.")

    con.close()


if __name__ == "__main__":
    main()