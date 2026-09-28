import sqlite3

DB = "data/mika_competitive_intel.db"

con = sqlite3.connect(DB)
con.row_factory = sqlite3.Row

rows = con.execute(
    """
    SELECT
        f.brand,
        p.promotion_type,
        p.offer_value,
        p.start_date,
        p.end_date,
        p.target_segment,
        f.observed_date,
        COUNT(*) AS duplicate_count,
        GROUP_CONCAT(f.finding_id, ', ') AS finding_ids
    FROM promotion_observations p
    JOIN findings f
        ON f.finding_id = p.finding_id
    GROUP BY
        f.brand,
        p.promotion_type,
        p.offer_value,
        p.start_date,
        p.end_date,
        p.target_segment,
        f.observed_date
    HAVING COUNT(*) > 1
    ORDER BY f.brand, f.observed_date
    """
).fetchall()

print("CURRENT DUPLICATE PROMOTIONS")
print("=" * 80)

if not rows:
    print("NONE")
else:
    for row in rows:
        print(
            f"{row['brand']} | "
            f"type={row['promotion_type']} | "
            f"offer={row['offer_value']} | "
            f"date={row['observed_date']} | "
            f"duplicates={row['duplicate_count']}"
        )
        print(f"Finding IDs: {row['finding_ids']}")
        print(f"Start: {row['start_date']} | End: {row['end_date']}")
        print(f"Target: {row['target_segment']}")
        print("-" * 80)

print()
print(f"Duplicate groups: {len(rows)}")

con.close()