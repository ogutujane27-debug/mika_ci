import sqlite3

con = sqlite3.connect("data/mika_competitive_intel.db")

sql = """
SELECT
    p.model,
    p.product_name,
    p.price_kes,
    p.observed_date,
    f.brand,
    f.source_url
FROM price_observations p
JOIN findings f ON f.finding_id = p.finding_id
WHERE p.model IN ("RS57DG4000M9", "RT85K7111BS")
ORDER BY p.model, p.observed_date, p.observation_id
"""

print("=== REAL CROSS-DATE PRICE HISTORY ===")

for row in con.execute(sql):
    print(row)

con.close()
