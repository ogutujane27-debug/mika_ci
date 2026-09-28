import sqlite3

DB = r".\data\mika_competitive_intel.db"

conn = sqlite3.connect(DB)

print("=" * 80)
print("MIKA CI - PHASE 2H STRATEGIC ALERTS AUDIT")
print("=" * 80)

print("\n--- PRICE MOVEMENT SIGNALS ---")

rows = conn.execute("""
    SELECT
        f.competitor_id,
        c.competitor_name,
        f.brand,
        f.summary,
        f.observed_date,
        f.confidence
    FROM findings f
    JOIN competitors c
        ON c.competitor_id = f.competitor_id
    WHERE LOWER(COALESCE(f.finding_type, '')) LIKE '%price%'
       OR LOWER(COALESCE(f.summary, '')) LIKE '%price increase%'
       OR LOWER(COALESCE(f.summary, '')) LIKE '%price decrease%'
    ORDER BY f.observed_date DESC
""").fetchall()

print(f"Records found: {len(rows)}")

for row in rows:
    print(row)


print("\n--- CAMPAIGN ACTIVITY ---")

rows = conn.execute("""
    SELECT
        c.competitor_id,
        cp.competitor_name,
        c.campaign_name,
        c.campaign_type,
        c.category,
        c.offer_value,
        c.start_date,
        c.end_date,
        c.status,
        c.observed_date,
        c.confidence
    FROM campaigns c
    JOIN competitors cp
        ON cp.competitor_id = c.competitor_id
    ORDER BY
        c.observed_date DESC,
        cp.competitor_name
""").fetchall()

print(f"Campaign records found: {len(rows)}")

for row in rows:
    print(row)


print("\n--- PRICE + CAMPAIGN CONCURRENCY ---")

rows = conn.execute("""
    SELECT
        signal_type,
        status,
        competitor_name,
        category,
        title,
        description,
        evidence_count,
        confidence,
        start_date,
        end_date
    FROM market_trends
    WHERE signal_type = 'PRICE_CAMPAIGN_CONCURRENCY'
    ORDER BY created_at DESC
""").fetchall()

print(f"Concurrency signals found: {len(rows)}")

for row in rows:
    print(row)


print("\n--- MULTI-COMPETITOR CAMPAIGN SIGNALS ---")

rows = conn.execute("""
    SELECT
        signal_type,
        status,
        competitor_name,
        category,
        title,
        description,
        evidence_count,
        confidence,
        start_date,
        end_date
    FROM market_trends
    WHERE signal_type = 'MULTI_COMPETITOR_CAMPAIGN'
    ORDER BY created_at DESC
""").fetchall()

print(f"Multi-competitor signals found: {len(rows)}")

for row in rows:
    print(row)


print("\n--- CAMPAIGN CATEGORY CONCENTRATION ---")

rows = conn.execute("""
    SELECT
        signal_type,
        status,
        competitor_name,
        category,
        title,
        description,
        evidence_count,
        confidence,
        start_date,
        end_date
    FROM market_trends
    WHERE signal_type = 'CAMPAIGN_CATEGORY_CONCENTRATION'
    ORDER BY created_at DESC
""").fetchall()

print(f"Category concentration signals found: {len(rows)}")

for row in rows:
    print(row)


print("\n--- CATALOGUE PERSISTENCE ---")

rows = conn.execute("""
    SELECT
        signal_type,
        status,
        competitor_name,
        category,
        title,
        description,
        evidence_count,
        confidence,
        start_date,
        end_date
    FROM market_trends
    WHERE signal_type = 'CATALOGUE_PERSISTENCE'
    ORDER BY created_at DESC
""").fetchall()

print(f"Catalogue persistence signals found: {len(rows)}")

for row in rows:
    print(row)


print("\n--- EXISTING PHASE 2G COMPARISON EVIDENCE ---")

rows = conn.execute("""
    SELECT
        dimension,
        competitor_name,
        brand,
        comparison_type,
        metric_name,
        metric_value,
        observation_count,
        period_start,
        period_end,
        coverage_status
    FROM competitor_comparisons
    ORDER BY dimension, competitor_name, brand
""").fetchall()

print(f"Comparison records found: {len(rows)}")

for row in rows:
    print(row)


conn.close()

print("\n" + "=" * 80)
print("PHASE 2H AUDIT COMPLETE - READ ONLY")
print("=" * 80)