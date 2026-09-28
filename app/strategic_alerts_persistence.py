import sqlite3

DB = r".\data\mika_competitive_intel.db"


def connect():
    return sqlite3.connect(DB)


def create_table(conn):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS strategic_alerts (
            alert_id INTEGER PRIMARY KEY AUTOINCREMENT,

            alert_type TEXT NOT NULL,
            priority TEXT NOT NULL,

            competitor_id INTEGER,
            competitor_name TEXT,
            brand TEXT,
            category TEXT,

            title TEXT NOT NULL,
            description TEXT NOT NULL,

            evidence_source TEXT NOT NULL,
            evidence_reference TEXT,

            evidence_count INTEGER NOT NULL DEFAULT 0,

            period_start TEXT,
            period_end TEXT,

            confidence TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'OPEN',

            created_at TEXT NOT NULL,

            UNIQUE (
                alert_type,
                competitor_id,
                competitor_name,
                brand,
                category,
                title,
                period_start,
                period_end
            )
        )
    """)

    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_strategic_alerts_type
        ON strategic_alerts(alert_type)
    """)

    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_strategic_alerts_priority
        ON strategic_alerts(priority)
    """)

    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_strategic_alerts_competitor
        ON strategic_alerts(competitor_id)
    """)

    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_strategic_alerts_period
        ON strategic_alerts(period_start, period_end)
    """)

    conn.commit()


def main():
    print("=" * 70)
    print("MIKA CI - PHASE 2H STRATEGIC ALERTS PERSISTENCE")
    print("=" * 70)

    conn = connect()

    create_table(conn)

    table = conn.execute("""
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
          AND name = 'strategic_alerts'
    """).fetchone()

    if table:
        print("\nTABLE CREATED / VERIFIED:")
        print("strategic_alerts")

    print("\nCOLUMNS:")

    columns = conn.execute("""
        PRAGMA table_info(strategic_alerts)
    """).fetchall()

    for column in columns:
        print(column)

    print("\nINDEXES:")

    indexes = conn.execute("""
        SELECT name
        FROM sqlite_master
        WHERE type = 'index'
          AND tbl_name = 'strategic_alerts'
        ORDER BY name
    """).fetchall()

    for index in indexes:
        print(index[0])

    conn.close()

    print("\n" + "=" * 70)
    print("SCHEMA CREATION COMPLETE - DATABASE WRITE")
    print("=" * 70)


if __name__ == "__main__":
    main()