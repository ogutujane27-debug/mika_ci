import sqlite3
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

import market_trends_engine as engine


DB_PATH = (
    Path(__file__).resolve().parent.parent
    / "data"
    / "mika_competitive_intel.db"
)

# Keep this FALSE until the preview has been verified.
WRITE_ENABLED = True


def now():
    return datetime.now().isoformat(timespec="seconds")


def trend_exists(
    con,
    signal_type,
    competitor_name,
    category,
    start_date,
    end_date,
    title,
):
    row = con.execute(
        """
        SELECT trend_id
        FROM market_trends
        WHERE signal_type = ?
          AND competitor_name IS ?
          AND category IS ?
          AND start_date IS ?
          AND end_date IS ?
          AND title = ?
        """,
        (
            signal_type,
            competitor_name,
            category,
            start_date,
            end_date,
            title,
        ),
    ).fetchone()

    return row["trend_id"] if row else None


def insert_trend(
    con,
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
):
    existing_id = trend_exists(
        con,
        signal_type,
        competitor_name,
        category,
        start_date,
        end_date,
        title,
    )

    if existing_id:
        print(
            f"SKIP EXISTING | "
            f"{signal_type} | {title} | "
            f"trend_id={existing_id}"
        )
        return "existing"

    print(
        f"CREATE | {signal_type} | {status} | "
        f"{title}"
    )

    if WRITE_ENABLED:
        con.execute(
            """
            INSERT INTO market_trends (
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
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
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
                now(),
            ),
        )

        return "created"

    return "preview"


def write_price_signals(con, movements):
    print()
    print("=" * 80)
    print("PRICE SIGNALS")
    print("=" * 80)

    created = 0
    existing = 0

    for movement in movements:
        direction = (
            "INCREASE"
            if movement["change"] > 0
            else "DECREASE"
        )

        title = (
            f"{movement['brand']} "
            f"{movement['model']} price {direction.lower()}"
        )

        description = (
            f"{movement['product_name']} changed from "
            f"KSh {movement['previous_price']:,.2f} on "
            f"{movement['previous_date']} to "
            f"KSh {movement['current_price']:,.2f} on "
            f"{movement['current_date']}. "
            f"Change: {movement['change']:+,.2f} KSh "
            f"({movement['percentage']:+.2f}%)."
        )

        result = insert_trend(
            con,
            "PRODUCT_PRICE_MOVEMENT",
            "OBSERVED",
            movement["brand"],
            movement["category"],
            title,
            description,
            movement["previous_date"],
            movement["current_date"],
            1,
            "HIGH",
        )

        # Preview counts as a planned creation.
        if result in ("created", "preview"):
            created += 1
        elif result == "existing":
            existing += 1

    print(
        f"Price signals: {created} new, "
        f"{existing} existing"
    )


def write_brand_price_trends(con, movements):
    print()
    print("=" * 80)
    print("BRAND PRICE TRENDS")
    print("=" * 80)

    grouped = defaultdict(list)

    for movement in movements:
        direction = (
            "INCREASE"
            if movement["change"] > 0
            else "DECREASE"
        )

        grouped[
            (movement["brand"], direction)
        ].append(movement)

    created = 0
    existing = 0

    for (brand, direction), items in sorted(
        grouped.items()
    ):
        # A brand trend requires at least two products
        # moving in the same direction.
        if len(items) < 2:
            continue

        start_date = min(
            item["previous_date"]
            for item in items
        )

        end_date = max(
            item["current_date"]
            for item in items
        )

        title = (
            f"{brand} multi-product price "
            f"{direction.lower()} trend"
        )

        description = (
            f"{len(items)} products from {brand} "
            f"showed price {direction.lower()} movements "
            f"between {start_date} and {end_date}. "
            f"This is a brand-level trend signal."
        )

        result = insert_trend(
            con,
            "BRAND_PRICE_TREND",
            "TREND_SIGNAL",
            brand,
            None,
            title,
            description,
            start_date,
            end_date,
            len(items),
            "HIGH",
        )

        # Preview counts as a planned creation.
        if result in ("created", "preview"):
            created += 1
        elif result == "existing":
            existing += 1

    print(
        f"Brand trends: {created} new, "
        f"{existing} existing"
    )


def write_campaign_signals(con, campaigns):
    print()
    print("=" * 80)
    print("CAMPAIGN SIGNALS")
    print("=" * 80)

    if not campaigns:
        print("No verified campaigns.")
        return

    competitors = sorted(
        {
            row["competitor_name"]
            for row in campaigns
        }
    )

    categories = Counter(
        row["category"] or "UNSPECIFIED"
        for row in campaigns
    )

    dates = [
        row["observed_date"]
        for row in campaigns
        if row["observed_date"]
    ]

    start_date = min(dates) if dates else None
    end_date = max(dates) if dates else None

    confidence = (
        "HIGH"
        if all(
            (row["confidence"] or "").upper() == "HIGH"
            for row in campaigns
        )
        else "MEDIUM"
    )

    result = insert_trend(
        con,
        "CAMPAIGN_ACTIVITY",
        "OBSERVED",
        None,
        None,
        "Verified competitor campaign activity",
        (
            f"{len(campaigns)} verified campaigns were "
            f"observed across {len(competitors)} competitors."
        ),
        start_date,
        end_date,
        len(campaigns),
        confidence,
    )

    print(
        f"Campaign activity result: {result}"
    )

    # Keep this as OBSERVED. The current campaign history
    # is too short to treat multi-competitor activity as
    # an established longer-term trend.
    if len(competitors) >= 2:
        result = insert_trend(
            con,
            "MULTI_COMPETITOR_CAMPAIGN",
            "OBSERVED",
            None,
            None,
            "Multi-competitor campaign activity",
            (
                f"Verified campaign activity was observed "
                f"across {len(competitors)} competitors: "
                f"{', '.join(competitors)}."
            ),
            start_date,
            end_date,
            len(campaigns),
            confidence,
        )

        print(
            f"Multi-competitor campaign result: {result}"
        )

    if categories:
        category, count = categories.most_common(1)[0]

        result = insert_trend(
            con,
            "CAMPAIGN_CATEGORY_CONCENTRATION",
            "OBSERVED",
            None,
            category,
            f"Campaign activity concentrated in {category}",
            (
                f"{count} of {len(campaigns)} verified "
                f"campaigns were classified under {category}."
            ),
            start_date,
            end_date,
            count,
            confidence,
        )

        print(
            f"Campaign concentration result: {result}"
        )


def write_catalogue_signals(con, catalogues):
    print()
    print("=" * 80)
    print("CATALOGUE SIGNALS")
    print("=" * 80)

    for item in catalogues:
        if item["persistent"] <= 0:
            continue

        title = (
            f"{item['competitor']} catalogue persistence"
        )

        description = (
            f"{item['competitor']} had "
            f"{item['products']} tracked catalogue products, "
            f"with {item['persistent']} repeatedly observed "
            f"across the tracked period."
        )

        result = insert_trend(
            con,
            "CATALOGUE_PERSISTENCE",
            "OBSERVED",
            item["competitor"],
            None,
            title,
            description,
            None,
            None,
            item["persistent"],
            "HIGH",
        )

        print(
            f"{item['competitor']}: {result}"
        )


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


def write_concurrent_signals(
    con,
    movements,
    campaigns,
):
    print()
    print("=" * 80)
    print("PRICE + CAMPAIGN CONCURRENT SIGNALS")
    print("=" * 80)

    count = 0

    for movement in movements:
        movement_dates = {
            movement["previous_date"],
            movement["current_date"],
        }

        matching = []

        for campaign in campaigns:
            if any(
                campaign_active_on_date(
                    campaign,
                    movement_date,
                )
                for movement_date in movement_dates
            ):
                matching.append(campaign)

        if not matching:
            continue

        for campaign in matching:
            title = (
                f"{movement['brand']} "
                f"{movement['model']} and "
                f"{campaign['competitor_name']} "
                f"{campaign['campaign_name']} "
                f"date overlap"
            )

            description = (
                f"The price movement for "
                f"{movement['brand']} {movement['model']} "
                f"overlapped in time with the verified campaign "
                f"'{campaign['campaign_name']}'. "
                f"This is a concurrent signal only and does not "
                f"establish causality."
            )

            result = insert_trend(
                con,
                "PRICE_CAMPAIGN_CONCURRENCY",
                "CONCURRENT_SIGNAL",
                campaign["competitor_name"],
                movement["category"],
                title,
                description,
                movement["previous_date"],
                movement["current_date"],
                2,
                "MEDIUM",
            )

            print(
                f"Overlap result: {result}"
            )

            count += 1

    print(
        f"Concurrent signals processed: {count}"
    )


def main():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row

    print("=" * 80)
    print("MIKA CI - PHASE 2F MARKET TRENDS WRITER")
    print("=" * 80)

    print(
        f"Database writes: "
        f"{'ENABLED' if WRITE_ENABLED else 'DISABLED - PREVIEW'}"
    )

    rows, identities, movements, ambiguous = (
        engine.load_price_signals(con)
    )

    campaigns = engine.get_campaigns(con)
    social = engine.get_social_summary(con)
    catalogues = engine.get_catalogue_summary(con)

    print()
    print("INPUTS")
    print("-" * 80)
    print(f"Price observations: {len(rows)}")
    print(f"Product identities: {len(identities)}")
    print(f"Price movements: {len(movements)}")
    print(f"Ambiguous movements: {len(ambiguous)}")
    print(f"Verified campaigns: {len(campaigns)}")
    print(
        f"Social observations: "
        f"{social['observations'] or 0}"
    )

    if ambiguous:
        print()
        print(
            "WARNING: ambiguous price movements detected."
        )
        print(
            "Price signals will not be written until "
            "ambiguity is resolved."
        )
    else:
        write_price_signals(
            con,
            movements,
        )

        write_brand_price_trends(
            con,
            movements,
        )

    write_campaign_signals(
        con,
        campaigns,
    )

    write_catalogue_signals(
        con,
        catalogues,
    )

    write_concurrent_signals(
        con,
        movements,
        campaigns,
    )

    if WRITE_ENABLED:
        con.commit()

    print()
    print("=" * 80)
    print("WRITER COMPLETE")
    print("=" * 80)

    if WRITE_ENABLED:
        print("Database changes committed.")
    else:
        print(
            "PREVIEW ONLY - no database changes committed."
        )

    row = con.execute(
        """
        SELECT COUNT(*)
        FROM market_trends
        """
    ).fetchone()

    print(
        f"market_trends records currently stored: {row[0]}"
    )

    con.close()


if __name__ == "__main__":
    main()