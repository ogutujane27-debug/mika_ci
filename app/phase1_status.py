import sqlite3

DB = "data/mika_competitive_intel.db"

con = sqlite3.connect(DB)
con.row_factory = sqlite3.Row

print("MIKA CI - PHASE 1 CURRENT STATUS")
print("=" * 80)

print("\nTABLE COUNTS")
print("-" * 80)

tables = [
    "competitors",
    "findings",
    "price_observations",
    "promotion_observations",
    "product_observations",
    "news_observations",
    "scan_runs",
    "reports",
]

for table in tables:
    count = con.execute(
        f"SELECT COUNT(*) FROM {table}"
    ).fetchone()[0]
    print(f"{table}: {count}")

print("\nLATEST SCAN RUN")
print("-" * 80)

run = con.execute(
    """
    SELECT *
    FROM scan_runs
    ORDER BY run_id DESC
    LIMIT 1
    """
).fetchone()

for key in run.keys():
    print(f"{key}: {run[key]}")

print("\nFINDINGS BY TYPE - CURRENT WEEK")
print("-" * 80)

week = con.execute(
    """
    SELECT scan_week
    FROM scan_runs
    ORDER BY run_id DESC
    LIMIT 1
    """
).fetchone()["scan_week"]

rows = con.execute(
    """
    SELECT finding_type, COUNT(*) AS total
    FROM findings
    WHERE scan_week = ?
    GROUP BY finding_type
    ORDER BY finding_type
    """,
    (week,),
).fetchall()

print(f"Week: {week}")

for row in rows:
    print(f"{row['finding_type']}: {row['total']}")

print("\nFINDINGS BY BRAND - CURRENT WEEK")
print("-" * 80)

rows = con.execute(
    """
    SELECT brand, finding_type, COUNT(*) AS total
    FROM findings
    WHERE scan_week = ?
    GROUP BY brand, finding_type
    ORDER BY brand, finding_type
    """,
    (week,),
).fetchall()

for row in rows:
    print(
        f"{row['brand']} | "
        f"{row['finding_type']} | "
        f"{row['total']}"
    )

print("\nNEWS")
print("-" * 80)

news = con.execute(
    """
    SELECT COUNT(*)
    FROM findings
    WHERE scan_week = ?
      AND finding_type = 'news'
    """,
    (week,),
).fetchone()[0]

print(f"Current-week news findings: {news}")

con.close()