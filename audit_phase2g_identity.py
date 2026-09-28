import sqlite3

DB = r".\data\mika_competitive_intel.db"

conn = sqlite3.connect(DB)

print("=" * 70)
print("PHASE 2G - IDENTITY / COVERAGE AUDIT")
print("=" * 70)

print("\n--- PRICE IDENTITIES ---")

rows = conn.execute("""
SELECT
    f.competitor_id,
    c.competitor_name,
    f.brand,
    COUNT(*)
FROM price_observations p
JOIN findings f
    ON f.finding_id = p.finding_id
LEFT JOIN competitors c
    ON c.competitor_id = f.competitor_id
GROUP BY
    f.competitor_id,
    c.competitor_name,
    f.brand
ORDER BY
    c.competitor_name,
    f.brand
""").fetchall()

for row in rows:
    print(row)

print("\n--- CAMPAIGN IDENTITIES ---")

rows = conn.execute("""
SELECT
    c.competitor_id,
    cp.competitor_name,
    COUNT(*)
FROM campaigns c
LEFT JOIN competitors cp
    ON cp.competitor_id = c.competitor_id
GROUP BY
    c.competitor_id,
    cp.competitor_name
ORDER BY
    cp.competitor_name
""").fetchall()

for row in rows:
    print(row)

print("\n--- SOCIAL IDENTITIES ---")

rows = conn.execute("""
SELECT
    s.competitor_id,
    c.competitor_name,
    COUNT(*)
FROM social_observations s
LEFT JOIN competitors c
    ON c.competitor_id = s.competitor_id
GROUP BY
    s.competitor_id,
    c.competitor_name
ORDER BY
    c.competitor_name
""").fetchall()

for row in rows:
    print(row)

conn.close()

print("\n" + "=" * 70)
print("AUDIT COMPLETE - READ ONLY")
print("=" * 70)