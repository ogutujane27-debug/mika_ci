import sqlite3

DB = "data/mika_competitive_intel.db"

con = sqlite3.connect(DB)
con.row_factory = sqlite3.Row

row = con.execute(
    """
    SELECT run_id, scan_week, started_at, completed_at,
           status, sources_checked, findings_created, error_message
    FROM scan_runs
    ORDER BY run_id DESC
    LIMIT 1
    """
).fetchone()

print("LATEST SCAN RUN")
print("=" * 70)

if row:
    for key in row.keys():
        print(f"{key}: {row[key]}")
else:
    print("No scan runs found.")

con.close()