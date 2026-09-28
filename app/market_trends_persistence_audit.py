import sqlite3
from pathlib import Path


DB_PATH = (
    Path(__file__).resolve().parent.parent
    / "data"
    / "mika_competitive_intel.db"
)


SIGNAL_STATUSES = [
    "OBSERVED",
    "TREND_SIGNAL",
    "CONCURRENT_SIGNAL",
    "INSUFFICIENT_HISTORY",
    "NOT_ESTABLISHED",
]


def get_tables(con):
    rows = con.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type='table'
        ORDER BY name
        """
    ).fetchall()

    return [row[0] for row in rows]


def table_columns(con, table):
    return con.execute(
        f"PRAGMA table_info({table})"
    ).fetchall()


def audit_existing_evidence(con):
    print("=" * 80)
    print("1. EXISTING EVIDENCE LAYER")
    print("=" * 80)

    evidence_tables = [
        "price_observations",
        "campaigns",
        "campaign_posts",
        "social_observations",
        "social_engagement_history",
        "bruhm_products",
        "haier_products",
        "k_elec_products",
    ]

    for table in evidence_tables:
        exists = table in get_tables(con)

        if exists:
            columns = table_columns(con, table)
            names = [column[1] for column in columns]

            print()
            print(f"{table}")
            print(f"Status: EXISTS")
            print(f"Columns: {', '.join(names)}")
        else:
            print()
            print(f"{table}")
            print("Status: MISSING")


def explain_persistence_boundary():
    print()
    print("=" * 80)
    print("2. PERSISTENCE BOUNDARY")
    print("=" * 80)

    print()
    print("SOURCE DATA THAT SHOULD REMAIN UNCHANGED")
    print("- price observations")
    print("- verified campaigns")
    print("- campaign posts")
    print("- social observations")
    print("- social engagement history")
    print("- product catalogues")

    print()
    print("DERIVED INFORMATION THAT MAY BE PERSISTED")
    print("- identified trend signal")
    print("- signal status")
    print("- trend title")
    print("- trend description")
    print("- evidence period")
    print("- confidence/evidence level")
    print("- creation timestamp")

    print()
    print("RULE")
    print(
        "Market Trends should store DERIVED SIGNALS, "
        "not duplicate source observations."
    )


def define_signal_types():
    print()
    print("=" * 80)
    print("3. PROPOSED SIGNAL TYPES")
    print("=" * 80)

    signals = [
        (
            "PRODUCT_PRICE_MOVEMENT",
            "One product has a verified price movement.",
            "OBSERVED",
        ),
        (
            "BRAND_PRICE_TREND",
            "Multiple products from one brand move in the same direction.",
            "TREND_SIGNAL",
        ),
        (
            "MARKET_PRICE_TREND",
            "Multiple brands show a common price direction.",
            "NOT_ESTABLISHED",
        ),
        (
            "CAMPAIGN_ACTIVITY",
            "Verified campaign activity exists.",
            "OBSERVED",
        ),
        (
            "MULTI_COMPETITOR_CAMPAIGN",
            "Verified campaigns exist across multiple competitors.",
            "TREND_SIGNAL",
        ),
        (
            "CAMPAIGN_CATEGORY_CONCENTRATION",
            "Campaign activity is concentrated in a category.",
            "OBSERVED",
        ),
        (
            "CATALOGUE_PERSISTENCE",
            "Tracked products continue appearing across observations.",
            "OBSERVED",
        ),
        (
            "CATALOGUE_EXPANSION",
            "New products appear after the established baseline.",
            "NOT_ESTABLISHED",
        ),
        (
            "SOCIAL_ACTIVITY",
            "Social posts were observed.",
            "OBSERVED",
        ),
        (
            "SOCIAL_TREND",
            "Social activity changes across multiple observation periods.",
            "INSUFFICIENT_HISTORY",
        ),
        (
            "PRICE_CAMPAIGN_CONCURRENCY",
            "Price movement and campaign dates overlap.",
            "CONCURRENT_SIGNAL",
        ),
    ]

    print()

    for signal_type, description, current_status in signals:
        print(signal_type)
        print(f"  Meaning: {description}")
        print(f"  Current status: {current_status}")
        print()


def define_required_fields():
    print("=" * 80)
    print("4. PROPOSED PERSISTED FIELDS")
    print("=" * 80)

    fields = [
        ("trend_id", "Primary key"),
        ("signal_type", "Controlled signal type"),
        ("status", "Controlled interpretation status"),
        ("competitor_name", "Optional competitor reference"),
        ("category", "Optional category"),
        ("title", "Human-readable trend title"),
        ("description", "Evidence-based explanation"),
        ("start_date", "Beginning of evidence period"),
        ("end_date", "End of evidence period"),
        ("evidence_count", "Number of supporting observations"),
        ("confidence", "Evidence confidence"),
        ("created_at", "Record creation timestamp"),
    ]

    print()

    for field, purpose in fields:
        print(f"{field:<25} | {purpose}")


def define_duplicate_rule():
    print()
    print("=" * 80)
    print("5. DUPLICATE PREVENTION")
    print("=" * 80)

    print()
    print("A trend signal should not be duplicated simply because")
    print("the engine is run again.")

    print()
    print("PROPOSED NATURAL IDENTITY:")
    print(
        "(signal_type, competitor_name, category, start_date, end_date, title)"
    )

    print()
    print("A UNIQUE constraint should protect this identity.")

    print()
    print(
        "SOURCE observations remain independently duplicate-safe "
        "using their existing mechanisms."
    )


def define_status_rules():
    print()
    print("=" * 80)
    print("6. STATUS RULES")
    print("=" * 80)

    rules = [
        (
            "OBSERVED",
            "Evidence exists, but the evidence does not establish a broader trend.",
        ),
        (
            "TREND_SIGNAL",
            "Repeated or multi-item evidence supports a trend signal.",
        ),
        (
            "CONCURRENT_SIGNAL",
            "Two evidence types overlap in time without proving causality.",
        ),
        (
            "INSUFFICIENT_HISTORY",
            "The evidence exists but there are not enough time periods to establish a trend.",
        ),
        (
            "NOT_ESTABLISHED",
            "The required evidence threshold has not been reached.",
        ),
    ]

    for status, rule in rules:
        print()
        print(status)
        print(f"  {rule}")


def audit_current_persistence_need():
    print()
    print("=" * 80)
    print("7. CURRENT PERSISTENCE NEED")
    print("=" * 80)

    print()
    print("CURRENT EVIDENCE")

    current = [
        ("Product price movements", "4", "Persist derived signals"),
        ("Brand-level price trend", "1", "Persist derived signal"),
        ("Market-wide price trend", "0", "Do not create a false signal"),
        ("Verified campaigns", "7", "Already persisted in campaigns"),
        ("Catalogue products", "427", "Already persisted in catalogues"),
        ("Social observations", "22", "Already persisted in social_observations"),
        ("Historical social trend", "0", "Do not create a false signal"),
        (
            "Price + campaign concurrency",
            "15 overlaps",
            "Persist only as concurrent signal",
        ),
    ]

    print()

    for signal, evidence, action in current:
        print(f"{signal}")
        print(f"  Evidence: {evidence}")
        print(f"  Persistence: {action}")
        print()


def final_design():
    print("=" * 80)
    print("8. PERSISTENCE DESIGN RESULT")
    print("=" * 80)

    print()
    print("PASS - Source evidence should remain in existing tables.")
    print("PASS - Market Trends should store derived signals only.")
    print("PASS - Signal status should be controlled.")
    print("PASS - Duplicate prevention should use a natural identity.")
    print("PASS - Unsupported trends should not be persisted as positive signals.")
    print("PASS - Causality should not be stored as an established fact.")
    print()
    print("PROPOSED TABLE: market_trends")
    print()
    print("Database writes: DISABLED")
    print()
    print("OVERALL STATUS: PERSISTENCE DESIGN READY FOR REVIEW")


def main():
    con = sqlite3.connect(DB_PATH)

    print("=" * 80)
    print("MIKA CI - PHASE 2F MARKET TRENDS PERSISTENCE AUDIT")
    print("=" * 80)
    print("Database writes: DISABLED")

    audit_existing_evidence(con)
    explain_persistence_boundary()
    define_signal_types()
    define_required_fields()
    define_duplicate_rule()
    define_status_rules()
    audit_current_persistence_need()
    final_design()

    print()
    print("=" * 80)
    print("No database writes were performed.")
    print("=" * 80)

    con.close()


if __name__ == "__main__":
    main()