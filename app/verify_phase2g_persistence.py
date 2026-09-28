import sqlite3

DB = r".\data\mika_competitive_intel.db"

conn = sqlite3.connect(DB)

print("=" * 80)
print("PHASE 2G - PERSISTED COMPARISON VERIFICATION")
print("=" * 80)

rows = conn.execute("""
    SELECT
        dimension,
        competitor_name,
        COALESCE(brand, ''),
        metric_name,
        metric_value,
        observation_count,
        period_start,
        period_end,
        coverage_status
    FROM competitor_comparisons
    ORDER BY
        dimension,
        competitor_name,
        COALESCE(brand, '')
""").fetchall()

print(f"\nTotal persisted records: {len(rows)}\n")

for row in rows:
    print(row)

print("\n" + "-" * 80)
print("DIMENSION COUNTS")
print("-" * 80)

counts = conn.execute("""
    SELECT
        dimension,
        COUNT(*)
    FROM competitor_comparisons
    GROUP BY dimension
    ORDER BY dimension
""").fetchall()

for row in counts:
    print(row)

print("\n" + "-" * 80)
print("DUPLICATE IDENTITY CHECK")
print("-" * 80)

duplicates = conn.execute("""
    SELECT
        competitor_id,
        COALESCE(brand, ''),
        dimension,
        comparison_type,
        metric_name,
        COALESCE(period_start, ''),
        COALESCE(period_end, ''),
        COUNT(*)
    FROM competitor_comparisons
    GROUP BY
        competitor_id,
        COALESCE(brand, ''),
        dimension,
        comparison_type,
        metric_name,
        COALESCE(period_start, ''),
        COALESCE(period_end, '')
    HAVING COUNT(*) > 1
""").fetchall()

if duplicates:
    print("DUPLICATES FOUND:")
    for row in duplicates:
        print(row)
else:
    print("NONE")

conn.close()

print("\n" + "=" * 80)
print("VERIFICATION COMPLETE - READ ONLY")
print("=" * 80)