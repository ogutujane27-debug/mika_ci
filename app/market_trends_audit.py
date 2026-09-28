import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "mika_competitive_intel.db"


def main():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row

    print("=" * 80)
    print("MIKA CI - PHASE 2F MARKET TRENDS AUDIT")
    print("=" * 80)
    print("Database writes: DISABLED")

    print()
    print("PRICE HISTORY")
    print("-" * 80)

    row = con.execute(
        """
        SELECT
            COUNT(*),
            COUNT(DISTINCT observed_date),
            MIN(observed_date),
            MAX(observed_date)
        FROM price_observations
        """
    ).fetchone()

    print(f"Observations: {row[0]}")
    print(f"Observation dates: {row[1]}")
    print(f"Date range: {row[2]} to {row[3]}")

    print()
    print("CAMPAIGN ACTIVITY")
    print("-" * 80)

    row = con.execute(
        """
        SELECT
            COUNT(*),
            COUNT(DISTINCT competitor_id),
            MIN(observed_date),
            MAX(observed_date)
        FROM campaigns
        """
    ).fetchone()

    print(f"Campaigns: {row[0]}")
    print(f"Competitors with campaigns: {row[1]}")
    print(f"Observed range: {row[2]} to {row[3]}")

    print()
    print("SOCIAL ACTIVITY")
    print("-" * 80)

    row = con.execute(
        """
        SELECT
            COUNT(*),
            COUNT(DISTINCT competitor_id),
            MIN(observed_date),
            MAX(observed_date)
        FROM social_observations
        """
    ).fetchone()

    print(f"Social observations: {row[0]}")
    print(f"Competitors represented: {row[1]}")
    print(f"Observed range: {row[2]} to {row[3]}")

    print()
    print("PRODUCT CATALOGUES")
    print("-" * 80)

    for table in (
        "bruhm_products",
        "haier_products",
        "k_elec_products",
    ):
        row = con.execute(
            f"""
            SELECT
                COUNT(*),
                MIN(first_seen_date),
                MAX(last_seen_date)
            FROM {table}
            """
        ).fetchone()

        print(
            f"{table}: {row[0]} products | "
            f"{row[1]} to {row[2]}"
        )

    print()
    print("=" * 80)
    print("Audit complete. No database writes were performed.")
    print("=" * 80)

    con.close()


if __name__ == "__main__":
    main()