import sys

sys.path.insert(0, r".\app")

from database import connect

c = connect()

rows = c.execute("""
SELECT
    f.finding_id,
    f.competitor_id,
    f.brand,
    f.category,
    p.product_name,
    p.model,
    p.price_kes,
    p.observed_date,
    f.source_url
FROM price_observations p
JOIN findings f
    ON f.finding_id = p.finding_id
WHERE p.observed_date = '2026-09-23'
ORDER BY p.observation_id
""").fetchall()

print("TOTAL:", len(rows))
print()

for row in rows:
    print(dict(row))