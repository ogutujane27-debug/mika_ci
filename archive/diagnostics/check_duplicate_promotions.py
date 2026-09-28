import sqlite3

DB = "data/mika_competitive_intel.db"

con = sqlite3.connect(DB)
con.row_factory = sqlite3.Row

print("=" * 70)
print("MIKA CI - PROMOTION INTEGRITY CHECK")
print("=" * 70)

print("\nPROMOTION OBSERVATIONS")

rows = con.execute("""
    SELECT
        p.observation_id,
        p.finding_id,
        f.run_id,
        f.scan_week,
        f.competitor_id,
        f.brand,
        f.category,
        f.observed_date,
        f.summary,
        f.source_url,
        p.promotion_type,
        p.offer_value,
        p.start_date,
        p.end_date,
        p.target_segment
    FROM promotion_observations p
    JOIN findings f
        ON f.finding_id = p.finding_id
    ORDER BY
        f.observed_date,
        f.competitor_id,
        p.observation_id
""").fetchall()

print(f"Total promotion observations: {len(rows):,}")

for row in rows:
    print(
        f"{row['observation_id']} | "
        f"{row['finding_id']} | "
        f"run={row['run_id']} | "
        f"{row['observed_date']} | "
        f"{row['brand']} | "
        f"{row['promotion_type']} | "
        f"{row['offer_value']}"
    )

print("\n" + "-" * 70)
print("DUPLICATE PROMOTIONS")
print("-" * 70)

duplicates = con.execute("""
    SELECT
        f.competitor_id,
        f.brand,
        f.observed_date,
        p.promotion_type,
        p.offer_value,
        p.start_date,
        p.end_date,
        p.target_segment,
        COUNT(*) AS n
    FROM promotion_observations p
    JOIN findings f
        ON f.finding_id = p.finding_id
    GROUP BY
        f.competitor_id,
        f.brand,
        f.observed_date,
        p.promotion_type,
        p.offer_value,
        p.start_date,
        p.end_date,
        p.target_segment
    HAVING COUNT(*) > 1
    ORDER BY n DESC
""").fetchall()

if duplicates:
    for row in duplicates:
        print(dict(row))
else:
    print("NONE")

print("\n" + "-" * 70)
print("PROMOTION FINDING LINK CHECK")
print("-" * 70)

orphan_count = con.execute("""
    SELECT COUNT(*) AS n
    FROM promotion_observations p
    LEFT JOIN findings f
        ON f.finding_id = p.finding_id
    WHERE f.finding_id IS NULL
""").fetchone()["n"]

print(f"Orphan promotion observations: {orphan_count}")

print("\n" + "=" * 70)
print("PROMOTION INTEGRITY CHECK COMPLETE")
print("=" * 70)

con.close()