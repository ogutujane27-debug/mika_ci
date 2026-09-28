import sqlite3

db = r".\data\mika_competitive_intel.db"

conn = sqlite3.connect(db)
conn.row_factory = sqlite3.Row

rows = conn.execute("""
    SELECT
        observation_id,
        finding_id,
        product_name,
        model,
        price_kes,
        promotion_note,
        observed_date
    FROM price_observations
    WHERE model IN (
        'TEFAL',
        'SCL',
        'CLIPSOMINUT',
        'RS57DG4000M9'
    )
    ORDER BY model, observed_date, observation_id
""").fetchall()

print("=== SUSPICIOUS PRICE HISTORY ===")
print("Rows:", len(rows))

for row in rows:
    print(dict(row))

conn.close()
