import sqlite3

con = sqlite3.connect("data/mika_competitive_intel.db")

rows = con.execute("""
SELECT
    f.finding_id,
    f.brand,
    f.category,
    p.product_name,
    p.model,
    p.price_kes,
    p.promotion_note,
    f.observed_date,
    f.source_url
FROM findings f
LEFT JOIN price_observations p
    ON p.finding_id = f.finding_id
WHERE f.competitor_id = 10
ORDER BY f.brand, p.product_name
""").fetchall()

print("=== SAMSUTECH RECORDS ===")

for row in rows:
    print(row)

con.close()
