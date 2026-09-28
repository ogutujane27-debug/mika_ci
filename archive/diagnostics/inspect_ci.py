import sqlite3

DB = r"data\mika_competitive_intel.db"

con = sqlite3.connect(DB)
con.row_factory = sqlite3.Row

print("\n=== MOULINEX: FINDINGS ===")

rows = con.execute("""
    SELECT
        f.finding_id,
        f.scan_week,
        f.brand,
        f.category,
        f.finding_type,
        f.summary,
        f.source_url,
        f.observed_date,
        f.verification_status,
        f.confidence
    FROM findings f
    WHERE
        LOWER(COALESCE(f.brand, '')) LIKE '%moulinex%'
        OR LOWER(COALESCE(f.summary, '')) LIKE '%moulinex%'
    ORDER BY f.observed_date DESC, f.finding_id DESC
""").fetchall()

print("Rows:", len(rows))

for r in rows:
    print(
        f"{r['finding_id']} | "
        f"{r['observed_date']} | "
        f"{r['finding_type']} | "
        f"{r['brand']} | "
        f"{r['category']} | "
        f"{r['summary']} | "
        f"{r['source_url']}"
    )

print("\n=== MOULINEX: PRICE OBSERVATIONS ===")

rows = con.execute("""
    SELECT
        p.finding_id,
        p.product_name,
        p.model,
        p.price_kes,
        p.promotion_note,
        p.observed_date,
        f.brand,
        f.source_url
    FROM price_observations p
    JOIN findings f
        ON f.finding_id = p.finding_id
    WHERE
        LOWER(COALESCE(f.brand, '')) LIKE '%moulinex%'
        OR LOWER(COALESCE(p.product_name, '')) LIKE '%moulinex%'
        OR LOWER(COALESCE(f.source_url, '')) LIKE '%moulinex%'
    ORDER BY p.observed_date DESC, p.finding_id DESC
""").fetchall()

print("Rows:", len(rows))

for r in rows:
    print(
        f"{r['observed_date']} | "
        f"{r['product_name']} | "
        f"{r['model']} | "
        f"KSh {r['price_kes']} | "
        f"{r['promotion_note']} | "
        f"{r['brand']} | "
        f"{r['source_url']}"
    )

print("\n=== MOULINEX: COMPETITOR RECORD ===")

rows = con.execute("""
    SELECT
        competitor_id,
        competitor_name,
        brand_name,
        official_url,
        secondary_url
    FROM competitors
    WHERE LOWER(brand_name) LIKE '%moulinex%'
""").fetchall()

for r in rows:
    print(
        f"{r['competitor_id']} | "
        f"{r['competitor_name']} | "
        f"{r['brand_name']} | "
        f"{r['official_url']} | "
        f"{r['secondary_url']}"
    )

con.close()