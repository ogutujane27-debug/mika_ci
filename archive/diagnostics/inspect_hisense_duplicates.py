import sqlite3

DB = "data/mika_competitive_intel.db"

finding_ids = [
    "CI-2026-09-00127",
    "CI-2026-09-00143",
    "CI-2026-09-00128",
    "CI-2026-09-00144",
    "CI-2026-09-00131",
    "CI-2026-09-00145",
]

con = sqlite3.connect(DB)
con.row_factory = sqlite3.Row

rows = con.execute(
    """
    SELECT
        f.finding_id,
        f.run_id,
        f.scan_week,
        f.observed_date,
        f.brand,
        f.category,
        f.summary,
        f.source_url,
        f.source_type,
        f.verification_status,
        f.confidence,
        p.observation_id,
        p.product_name,
        p.model,
        p.price_kes
    FROM findings f
    JOIN price_observations p
        ON p.finding_id = f.finding_id
    WHERE f.finding_id IN (?, ?, ?, ?, ?, ?)
    ORDER BY f.finding_id
    """,
    finding_ids,
).fetchall()

print("HISENSE DUPLICATE DETAILS")
print("=" * 80)

for row in rows:
    print(
        f"{row['finding_id']} | "
        f"run={row['run_id']} | "
        f"week={row['scan_week']} | "
        f"date={row['observed_date']}"
    )
    print(f"Observation ID: {row['observation_id']}")
    print(f"Product: {row['product_name']}")
    print(f"Model: {row['model']}")
    print(f"Price: KSh {row['price_kes']}")
    print(f"Brand: {row['brand']}")
    print(f"Category: {row['category']}")
    print(f"Source type: {row['source_type']}")
    print(f"Verification: {row['verification_status']}")
    print(f"Confidence: {row['confidence']}")
    print(f"URL: {row['source_url']}")
    print(f"Summary: {row['summary']}")
    print("-" * 80)

con.close()