import sqlite3
from pathlib import Path

DB = Path("data/mika_competitive_intel.db")

con = sqlite3.connect(DB)
con.row_factory = sqlite3.Row

print("LATEST OPALNET FINDINGS")
print("=" * 70)

rows = con.execute(
    """
    SELECT
        f.finding_id,
        f.competitor_id,
        c.competitor_name,
        c.brand_name AS mapped_brand,
        f.brand,
        f.finding_type,
        f.observed_date,
        f.summary
    FROM findings f
    JOIN competitors c
        ON c.competitor_id = f.competitor_id
    WHERE f.run_id = (
        SELECT MAX(run_id)
        FROM scan_runs
    )
    ORDER BY f.finding_id
    """
).fetchall()

for row in rows:
    print(
        f"{row['finding_id']} | "
        f"competitor_id={row['competitor_id']} | "
        f"source={row['competitor_name']} | "
        f"mapped_brand={row['mapped_brand']} | "
        f"finding_brand={row['brand']} | "
        f"type={row['finding_type']}"
    )

print()
print(f"Total latest-run findings: {len(rows)}")

con.close()