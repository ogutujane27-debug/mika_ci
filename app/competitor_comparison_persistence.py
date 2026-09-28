import sqlite3
from datetime import datetime

DB = r".\data\mika_competitive_intel.db"


def connect():
    return sqlite3.connect(DB)


def create_table(conn):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS competitor_comparisons (
            comparison_id INTEGER PRIMARY KEY AUTOINCREMENT,

            competitor_id INTEGER NOT NULL,
            competitor_name TEXT NOT NULL,
            brand TEXT,

            dimension TEXT NOT NULL,
            comparison_type TEXT NOT NULL,

            metric_name TEXT NOT NULL,
            metric_value REAL,

            observation_count INTEGER NOT NULL DEFAULT 0,

            period_start TEXT,
            period_end TEXT,

            evidence_summary TEXT NOT NULL,

            confidence TEXT,
            coverage_status TEXT NOT NULL,

            created_at TEXT NOT NULL,

            UNIQUE (
                competitor_id,
                brand,
                dimension,
                comparison_type,
                metric_name,
                period_start,
                period_end
            )
        )
    """)

    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_competitor_comparisons_competitor
        ON competitor_comparisons(competitor_id)
    """)

    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_competitor_comparisons_dimension
        ON competitor_comparisons(dimension)
    """)

    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_competitor_comparisons_period
        ON competitor_comparisons(period_start, period_end)
    """)

    conn.commit()


def main():
    print("=" * 70)
    print("MIKA CI - PHASE 2G COMPARISON PERSISTENCE")
    print("=" * 70)

    conn = connect()

    create_table(conn)

    row = conn.execute("""
        SELECT
            name
        FROM sqlite_master
        WHERE type = 'table'
          AND name = 'competitor_comparisons'
    """).fetchone()

    if row:
        print("\nTABLE CREATED / VERIFIED:")
        print("competitor_comparisons")

    columns = conn.execute("""
        PRAGMA table_info(competitor_comparisons)
    """).fetchall()

    print("\nCOLUMNS:")
    for column in columns:
        print(column)

    indexes = conn.execute("""
        SELECT name
        FROM sqlite_master
        WHERE type = 'index'
          AND tbl_name = 'competitor_comparisons'
        ORDER BY name
    """).fetchall()

    print("\nINDEXES:")
    for index in indexes:
        print(index[0])

    conn.close()

    print("\n" + "=" * 70)
    print("SCHEMA CREATION COMPLETE - DATABASE WRITE")
    print("=" * 70)


if __name__ == "__main__":
    main()