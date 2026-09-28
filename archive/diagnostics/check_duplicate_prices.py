import sqlite3

DB = "data/mika_competitive_intel.db"

con = sqlite3.connect(DB)
con.row_factory = sqlite3.Row

rows = con.execute(
    """
    SELECT
        f.brand,
        p.product_name,
        p.model,
        p.price_kes,
        p.observed_date,
        f.source_url,
        COUNT(*) AS duplicate_count,
        GROUP_CONCAT(f.finding_id, ', ') AS finding_ids
    FROM price_observations p
    JOIN findings f
        ON f.finding_id = p.finding_id
    GROUP BY
        f.brand,
        p.product_name,
        p.model,
        p.price_kes,
        p.observed_date,
        f.source_url
    HAVING COUNT(*) > 1
    ORDER BY duplicate_count DESC, f.brand, p.product_name
    """
).fetchall()

print("DUPLICATE PRICE OBSERVATIONS")
print("=" * 80)

if not rows:
    print("NONE")
else:
    for row in rows:
        print(
            f"{row['brand']} | "
            f"{row['product_name']} | "
            f"model={row['model']} | "
            f"KSh {row['price_kes']} | "
            f"{row['observed_date']} | "
            f"duplicates={row['duplicate_count']}"
        )
        print(f"Finding IDs: {row['finding_ids']}")
        print(f"URL: {row['source_url']}")
        print("-" * 80)

print()
print(f"Duplicate groups: {len(rows)}")

con.close()