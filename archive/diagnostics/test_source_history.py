import sqlite3

DB = "data/mika_competitive_intel.db"

con = sqlite3.connect(DB)

sql = """
SELECT
    p.price_kes,
    p.observed_date
FROM price_observations p
JOIN findings f
    ON f.finding_id = p.finding_id
WHERE p.model = ?
  AND f.brand = ?
  AND f.competitor_id = ?
  AND p.observed_date < ?
ORDER BY p.observed_date DESC, p.observation_id DESC
LIMIT 1
"""

print("=== SOURCE-AWARE HISTORY TEST ===")

hotpoint = con.execute(
    sql,
    ("RS57DG4000M9", "Samsung", 1, "2026-09-23"),
).fetchone()

samsutech = con.execute(
    sql,
    ("RS57DG4000M9", "Samsung", 8, "2026-09-23"),
).fetchone()

print("Hotpoint / Samsung / RS57DG4000M9:")
print(hotpoint)

print()

print("Samsutech / Samsung / RS57DG4000M9:")
print(samsutech)

con.close()