import sqlite3
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

import product_price_movements as price_movements


DB_PATH = (
    Path(__file__).resolve().parent.parent
    / "data"
    / "mika_competitive_intel.db"
)

BASELINE_DATE = "2026-09-22"


def load_price_signals(con):
    rows = price_movements.load_price_observations(con)
    identities = price_movements.build_identities(rows)
    movements, ambiguous = price_movements.detect_movements(identities)

    return rows, identities, movements, ambiguous


def get_campaigns(con):
    return con.execute(
        """
        SELECT
            c.campaign_id,
            comp.competitor_name,
            c.campaign_name,
            c.campaign_type,
            c.category,
            c.offer_value,
            c.start_date,
            c.end_date,
            c.status,
            c.source_url,
            c.verification_status,
            c.confidence,
            c.observed_date
        FROM campaigns c
        JOIN competitors comp
            ON comp.competitor_id = c.competitor_id
        WHERE c.verification_status = 'VERIFIED'
        ORDER BY c.observed_date, c.campaign_id
        """
    ).fetchall()


def get_social_summary(con):
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


def get_catalogue_summary(con):
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


def price_section(movements):
    print()
    print("=" * 80)
    print("1. PRICE TREND SIGNALS")
    print("=" * 80)

    if not movements:
        print("No qualifying price movements.")
        print("Evidence status: NOT ESTABLISHED")
        return

    print(f"Qualifying product price movements: {len(movements)}")

    direction_counts = Counter(
        "INCREASE" if item["change"] > 0 else "DECREASE"
        for item in movements
    )

    brand_directions = defaultdict(list)

    for item in movements:
        direction = "INCREASE" if item["change"] > 0 else "DECREASE"
        brand_directions[item["brand"]].append(direction)

    print()
    print("MOVEMENT DIRECTION")

    for direction, count in sorted(direction_counts.items()):
        print(f"{direction}: {count}")

    print()
    print("PRODUCT PRICE MOVEMENTS")

    for index, item in enumerate(movements, 1):
        direction = "INCREASE" if item["change"] > 0 else "DECREASE"

        print()
        print(f"{index}. {item['brand']} | {item['model']}")
        print(f"   Product: {item['product_name']}")
        print(f"   Category: {item['category']}")
        print(f"   Direction: {direction}")
        print(
            f"   Previous: KSh {item['previous_price']:,.2f}"
            f" ({item['previous_date']})"
        )
        print(
            f"   Current:  KSh {item['current_price']:,.2f}"
            f" ({item['current_date']})"
        )
        print(
            f"   Change: {item['change']:+,.2f} KSh"
            f" ({item['percentage']:+.2f}%)"
        )
        print("   Evidence: OBSERVED PRICE MOVEMENT")

    print()
    print("BRAND-LEVEL PRICE SIGNALS")

    qualifying_brands = 0

    for brand, directions in sorted(brand_directions.items()):
        counts = Counter(directions)

        same_direction = any(
            count >= 2
            for count in counts.values()
        )

        if same_direction:
            qualifying_brands += 1
            print(
                f"{brand}: "
                + ", ".join(
                    f"{direction}={count}"
                    for direction, count in sorted(counts.items())
                )
                + " | TREND SIGNAL"
            )

    if qualifying_brands:
        print()
        print(
            f"Brand-level trend signals: {qualifying_brands}"
        )
        print("Evidence status: TREND SIGNAL AVAILABLE")
    else:
        print("Evidence status: NOT ESTABLISHED")

    distinct_brands = len(
        {
            item["brand"]
            for item in movements
        }
    )

    print()
    print("MARKET-WIDE PRICE SIGNAL")

    if distinct_brands >= 3 and len(movements) >= 3:
        print("Evidence status: ESTABLISHED")
    else:
        print(
            "Evidence status: NOT ESTABLISHED "
            "(insufficient cross-brand movement)"
        )


def campaign_section(campaigns):
    print()
    print("=" * 80)
    print("2. CAMPAIGN TREND SIGNALS")
    print("=" * 80)

    if not campaigns:
        print("No verified campaigns.")
        print("Evidence status: NOT ESTABLISHED")
        return

    competitors = sorted(
        {
            row["competitor_name"]
            for row in campaigns
        }
    )

    active = [
        row
        for row in campaigns
        if row["status"] == "active"
    ]

    categories = Counter(
        row["category"] or "UNSPECIFIED"
        for row in campaigns
    )

    print(f"Verified campaigns: {len(campaigns)}")
    print(f"Competitors represented: {len(competitors)}")
    print(f"Active campaigns: {len(active)}")

    print()
    print("CAMPAIGNS BY COMPETITOR")

    competitor_counts = Counter(
        row["competitor_name"]
        for row in campaigns
    )

    for competitor, count in sorted(
        competitor_counts.items()
    ):
        print(f"{competitor}: {count}")

    print()
    print("CAMPAIGN CATEGORY CONCENTRATION")

    for category, count in sorted(
        categories.items(),
        key=lambda item: (-item[1], item[0]),
    ):
        print(f"{category}: {count}")

    print()
    print("CAMPAIGN SIGNALS")

    print("Campaign activity: OBSERVED")

    if len(competitors) >= 2:
        print("Multi-competitor activity: OBSERVED")

    if active:
        print("Active campaign signal: OBSERVED")

    if categories:
        leading_category, leading_count = categories.most_common(1)[0]
        print(
            f"Highest observed campaign concentration: "
            f"{leading_category} ({leading_count})"
        )

    print()
    print("Evidence status: TREND SIGNAL AVAILABLE")


def catalogue_section(catalogues):
    print()
    print("=" * 80)
    print("3. PRODUCT CATALOGUE TREND SIGNALS")
    print("=" * 80)

    total_products = sum(
        item["products"]
        for item in catalogues
    )

    total_persistent = sum(
        item["persistent"]
        for item in catalogues
    )

    total_post_baseline = sum(
        item["post_baseline"]
        for item in catalogues
    )

    for item in catalogues:
        print()
        print(item["competitor"])
        print(f"   Products tracked: {item['products']}")
        print(f"   Repeated observations: {item['persistent']}")
        print(f"   Post-baseline products: {item['post_baseline']}")

    print()
    print("CATALOGUE PRESENCE")

    if total_products:
        print(
            f"Observed tracked catalogue: {total_products} products"
        )
        print("Evidence status: OBSERVED")
    else:
        print("Evidence status: NOT ESTABLISHED")

    print()
    print("CATALOGUE PERSISTENCE")

    if total_persistent:
        print(
            f"Products repeatedly observed: {total_persistent}"
        )
        print("Evidence status: PERSISTENCE SIGNAL AVAILABLE")
    else:
        print("Evidence status: NOT ESTABLISHED")

    print()
    print("CATALOGUE EXPANSION")

    if total_post_baseline:
        print(
            f"Post-baseline products detected: "
            f"{total_post_baseline}"
        )
        print("Evidence status: EXPANSION SIGNAL AVAILABLE")
    else:
        print(
            "Post-baseline products detected: 0"
        )
        print(
            "Evidence status: NOT YET ESTABLISHED"
        )


def social_section(social):
    print()
    print("=" * 80)
    print("4. SOCIAL TREND SIGNALS")
    print("=" * 80)

    observations = social["observations"] or 0
    competitors = social["competitors"] or 0
    dates = social["dates"] or 0

    print(f"Social observations: {observations}")
    print(f"Competitors represented: {competitors}")
    print(f"Observation dates: {dates}")
    print(
        f"Date range: "
        f"{social['first_date']} to {social['last_date']}"
    )

    if observations:
        print()
        print("Social activity: OBSERVED")

    if dates >= 2:
        print("Social trend history: AVAILABLE")
    else:
        print(
            "Social trend history: "
            "INSUFFICIENT HISTORY"
        )

    print()
    if observations and dates >= 2:
        print("Evidence status: TREND SIGNAL AVAILABLE")
    elif observations:
        print(
            "Evidence status: ACTIVITY ONLY "
            "(historical trend not established)"
        )
    else:
        print("Evidence status: NOT ESTABLISHED")


def campaign_active_on_date(campaign, target_date):
    start = campaign["start_date"]
    end = campaign["end_date"]

    if not start and not end:
        return False

    if start and target_date < start:
        return False

    if end and target_date > end:
        return False

    return True


def cross_signal_section(movements, campaigns):
    print()
    print("=" * 80)
    print("5. CROSS-SIGNAL ANALYSIS")
    print("=" * 80)

    concurrent = []

    for movement in movements:
        movement_dates = {
            movement["previous_date"],
            movement["current_date"],
        }

        matching_campaigns = []

        for campaign in campaigns:
            for movement_date in movement_dates:
                if campaign_active_on_date(
                    campaign,
                    movement_date,
                ):
                    matching_campaigns.append(
                        campaign
                    )
                    break

        if matching_campaigns:
            concurrent.append(
                (
                    movement,
                    matching_campaigns,
                )
            )

    print()
    print("PRICE + CAMPAIGN")

    if concurrent:
        print(
            f"Price movements with overlapping campaign "
            f"dates: {len(concurrent)}"
        )

        for movement, matching in concurrent:
            print()
            print(
                f"{movement['brand']} | "
                f"{movement['model']}"
            )

            for campaign in matching:
                print(
                    f"   Campaign: "
                    f"{campaign['competitor_name']} | "
                    f"{campaign['campaign_name']}"
                )

            print(
                "   Interpretation: "
                "CONCURRENT SIGNALS ONLY"
            )

        print()
        print(
            "Important: overlapping dates do not establish "
            "causality."
        )
    else:
        print(
            "No price/campaign overlap established."
        )

    print()
    print("CAUSALITY GUARDRAIL")
    print(
        "The engine will report concurrent observations, "
        "not causal claims."
    )


def evidence_summary(
    movements,
    campaigns,
    catalogues,
    social,
):
    print()
    print("=" * 80)
    print("6. MIKA CI MARKET TRENDS EVIDENCE SUMMARY")
    print("=" * 80)

    total_products = sum(
        item["products"]
        for item in catalogues
    )

    post_baseline = sum(
        item["post_baseline"]
        for item in catalogues
    )

    social_dates = social["dates"] or 0

    distinct_price_brands = len(
        {
            item["brand"]
            for item in movements
        }
    )

    print()
    print("CURRENT OBSERVED SIGNALS")

    print(
        f"- {len(movements)} product price movement(s)"
    )

    print(
        f"- {distinct_price_brands} brand(s) represented "
        "in price movements"
    )

    print(
        f"- {len(campaigns)} verified campaign(s)"
    )

    print(
        f"- {total_products} tracked catalogue product(s)"
    )

    print(
        f"- {social['observations'] or 0} social observation(s)"
    )

    print()
    print("SIGNALS NOT YET ESTABLISHED")

    if distinct_price_brands < 3:
        print(
            "- Market-wide price trend"
        )

    if post_baseline == 0:
        print(
            "- Catalogue expansion"
        )

    if social_dates < 2:
        print(
            "- Historical social trend"
        )

    print()
    print("INTERPRETATION STANDARD")

    print(
        "MIKA CI should distinguish observed activity, "
        "trend signals, and insufficient evidence."
    )

    print(
        "A concurrent signal must not be presented as proof "
        "of causation."
    )


def main():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row

    print("=" * 80)
    print("MIKA CI - PHASE 2F MARKET TRENDS ENGINE")
    print("=" * 80)
    print("Database writes: DISABLED")

    rows, identities, movements, ambiguous = load_price_signals(
        con
    )

    campaigns = get_campaigns(con)
    social = get_social_summary(con)
    catalogues = get_catalogue_summary(con)

    print()
    print("ENGINE INPUTS")
    print("-" * 80)
    print(f"Price observations: {len(rows)}")
    print(f"Product identities: {len(identities)}")
    print(f"Price movement candidates: {len(movements)}")
    print(f"Ambiguous same-day cases: {len(ambiguous)}")
    print(f"Verified campaigns: {len(campaigns)}")
    print(f"Social observations: {social['observations'] or 0}")

    price_section(movements)
    campaign_section(campaigns)
    catalogue_section(catalogues)
    social_section(social)
    cross_signal_section(movements, campaigns)
    evidence_summary(
        movements,
        campaigns,
        catalogues,
        social,
    )

    print()
    print("=" * 80)
    print("PHASE 2F MARKET TRENDS ENGINE COMPLETE")
    print("=" * 80)
    print("No database writes were performed.")

    con.close()


if __name__ == "__main__":
    main()