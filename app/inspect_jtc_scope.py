import sqlite3


DB_PATH = r".\data\mika_competitive_intel.db"


def main():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    try:
        print("=" * 78)
        print("JTC SCOPE INSPECTION")
        print("MODE: READ-ONLY")
        print("=" * 78)

        print()
        print("--- STRATEGIC ALERTS: JTC ---")

        rows = conn.execute(
            """
            SELECT
                alert_id,
                alert_type,
                competitor_id,
                competitor_name,
                brand,
                title
            FROM strategic_alerts
            WHERE title LIKE '%JTC%'
            ORDER BY alert_id
            """
        ).fetchall()

        for row in rows:
            print(dict(row))

        print()
        print("--- MARKET TRENDS: JTC ---")

        rows = conn.execute(
            """
            SELECT
                trend_id,
                signal_type,
                status,
                competitor_name,
                category,
                title
            FROM market_trends
            WHERE title LIKE '%JTC%'
               OR competitor_name LIKE '%JTC%'
            ORDER BY trend_id
            """
        ).fetchall()

        for row in rows:
            print(dict(row))

        print()
        print("=" * 78)
        print("JTC SCOPE INSPECTION COMPLETE")
        print("NO DATABASE ROWS WERE WRITTEN")
        print("=" * 78)

    finally:
        conn.close()


if __name__ == "__main__":
    main()