import sqlite3

DB = "data/mika_competitive_intel.db"

PROBLEM_RUNS = [1, 2, 9, 10, 32, 34, 37]

con = sqlite3.connect(DB)
con.row_factory = sqlite3.Row

print("=" * 80)
print("MIKA CI - PROBLEM RUN TRACE")
print("=" * 80)

for run_id in PROBLEM_RUNS:

    print("\n" + "-" * 80)

    run = con.execute("""
        SELECT
            run_id,
            scan_week,
            started_at,
            completed_at,
            status,
            sources_checked,
            findings_created,
            error_message
        FROM scan_runs
        WHERE run_id = ?
    """, (run_id,)).fetchone()

    if not run:
        print(f"RUN {run_id}: NOT FOUND")
        continue

    print(f"RUN ID:          {run['run_id']}")
    print(f"SCAN WEEK:       {run['scan_week']}")
    print(f"STATUS:          {run['status']}")
    print(f"STARTED:         {run['started_at']}")
    print(f"COMPLETED:       {run['completed_at']}")
    print(f"SOURCES CHECKED: {run['sources_checked']}")
    print(f"RECORDED:        {run['findings_created']}")

    if run["error_message"]:
        print(f"ERROR:           {run['error_message']}")
    else:
        print("ERROR:           None")

    rows = con.execute("""
        SELECT
            f.finding_id,
            f.competitor_id,
            c.competitor_name,
            f.brand,
            f.category,
            f.finding_type,
            f.summary,
            f.observed_date,
            f.source_type
        FROM findings f
        LEFT JOIN competitors c
            ON c.competitor_id = f.competitor_id
        WHERE f.run_id = ?
        ORDER BY f.finding_id
    """, (run_id,)).fetchall()

    print(f"\nACTUAL FINDINGS: {len(rows)}")

    if not rows:
        print("NONE")
        continue

    print("\nFINDINGS BY COMPETITOR / TYPE")

    grouped = con.execute("""
        SELECT
            c.competitor_name,
            f.finding_type,
            COUNT(*) AS n
        FROM findings f
        LEFT JOIN competitors c
            ON c.competitor_id = f.competitor_id
        WHERE f.run_id = ?
        GROUP BY c.competitor_name, f.finding_type
        ORDER BY c.competitor_name, f.finding_type
    """, (run_id,)).fetchall()

    for row in grouped:
        print(
            f"{row['competitor_name']} | "
            f"{row['finding_type']} | "
            f"{row['n']}"
        )

    print("\nFINDING DETAILS")

    for row in rows:
        print(
            f"{row['finding_id']} | "
            f"{row['competitor_name']} | "
            f"{row['brand']} | "
            f"{row['category']} | "
            f"{row['finding_type']} | "
            f"{row['observed_date']} | "
            f"{row['source_type']} | "
            f"{row['summary']}"
        )

print("\n" + "=" * 80)
print("PROBLEM RUN TRACE COMPLETE")
print("=" * 80)

con.close()