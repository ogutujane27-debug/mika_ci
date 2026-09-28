import sqlite3

DB_PATH = r"C:\Users\User\Desktop\mika_ci\data\mika_competitive_intel.db"


def main():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    try:
        print("=" * 80)
        print("SOCIAL SCHEMA")
        print("=" * 80)

        for row in conn.execute(
            "PRAGMA table_info(social_observations)"
        ).fetchall():
            print(tuple(row))

        print("\n" + "=" * 80)
        print("HOTPOINT SOCIAL COUNT")
        print("=" * 80)

        row = conn.execute(
            """
            SELECT competitor_id, COUNT(*) AS observation_count
            FROM social_observations
            WHERE competitor_id = 1
            GROUP BY competitor_id
            """
        ).fetchone()

        print(dict(row) if row else "NO ROWS")

        print("\n" + "=" * 80)
        print("COMPETITOR COMPARISONS SCHEMA")
        print("=" * 80)

        for row in conn.execute(
            "PRAGMA table_info(competitor_comparisons)"
        ).fetchall():
            print(tuple(row))

        print("\n" + "=" * 80)
        print("HOTPOINT COMPARISON ROWS")
        print("=" * 80)

        rows = conn.execute(
            """
            SELECT
                comparison_id,
                competitor_id,
                competitor_name,
                brand,
                dimension,
                comparison_type,
                metric_name,
                metric_value,
                observation_count,
                period_start,
                period_end,
                evidence_summary,
                confidence,
                coverage_status
            FROM competitor_comparisons
            WHERE competitor_id = 1
            ORDER BY comparison_id
            """
        ).fetchall()

        for row in rows:
            print(dict(row))

        print("\n" + "=" * 80)
        print("RAMTONS COMPARISON ROWS")
        print("=" * 80)

        rows = conn.execute(
            """
            SELECT
                comparison_id,
                competitor_id,
                competitor_name,
                brand,
                dimension,
                comparison_type,
                metric_name,
                metric_value,
                observation_count,
                period_start,
                period_end,
                evidence_summary,
                confidence,
                coverage_status
            FROM competitor_comparisons
            WHERE competitor_id = 2
            ORDER BY comparison_id
            """
        ).fetchall()

        for row in rows:
            print(dict(row))

        print("\n" + "=" * 80)
        print("READ-ONLY INSPECTION COMPLETE")
        print("NO DATABASE ROWS WERE WRITTEN")
        print("=" * 80)

    finally:
        conn.close()


if __name__ == "__main__":
    main()