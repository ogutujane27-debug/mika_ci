import sqlite3

con = sqlite3.connect("data/mika_competitive_intel.db")

rows = con.execute("""
SELECT
    model,
    COUNT(*) AS observations,
    MIN(observed_date),
    MAX(observed_date)
FROM price_observations
WHERE model IS NOT NULL
GROUP BY model
HAVING COUNT(*) > 1
ORDER BY observations DESC, model
""").fetchall()

print("=== MODELS WITH MULTIPLE PRICE OBSERVATIONS ===")

for row in rows:
    print(row)

print("TOTAL:", len(rows))

con.close()
