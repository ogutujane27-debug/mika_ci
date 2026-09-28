import sqlite3
from pathlib import Path


DB_PATH = (
    Path(__file__).resolve().parent.parent
    / "data"
    / "mika_competitive_intel.db"
)


def main():
    con = sqlite3.connect(DB_PATH)

    con.execute(
        """
        CREATE TABLE IF NOT EXISTS market_trends (
            trend_id INTEGER PRIMARY KEY AUTOINCREMENT,
            signal_type TEXT NOT NULL,
            status TEXT NOT NULL,
            competitor_name TEXT,
            category TEXT,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            start_date TEXT,
            end_date TEXT,
            evidence_count INTEGER NOT NULL DEFAULT 0,
            confidence TEXT,
            created_at TEXT NOT NULL
        )
        """
    )

    con.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS
        ux_market_trends_identity
        ON market_trends (
            signal_type,
            competitor_name,
            category,
            start_date,
            end_date,
            title
        )
        """
    )

    con.commit()

    print("=" * 80)
    print("MIKA CI - PHASE 2F MARKET TRENDS TABLE")
    print("=" * 80)
    print("Database writes: ENABLED")
    print()
    print("Table: market_trends")
    print("Status: CREATED OR ALREADY EXISTS")
    print("Unique identity protection: ENABLED")
    print()

    row = con.execute(
        """
        SELECT COUNT(*)
        FROM market_trends
        """
    ).fetchone()

    print(f"Current market_trends records: {row[0]}")
    print()
    print("Schema:")
    
    columns = con.execute(
        "PRAGMA table_info(market_trends)"
    ).fetchall()

    for column in columns:
        print(
            f"{column[1]:<25} "
            f"{column[2]:<15} "
            f"NOT NULL={bool(column[3])}"
        )

    print()
    print("Indexes:")

    indexes = con.execute(
        """
        PRAGMA index_list(market_trends)
        """
    ).fetchall()

    for index in indexes:
        print(f"- {index[1]}")

    print()
    print("Phase 2F persistence table ready.")

    con.close()


if __name__ == "__main__":
    main()