import sqlite3
from datetime import datetime

DB = "data/mika_competitive_intel.db"

con = sqlite3.connect(DB)
con.row_factory = sqlite3.Row

print("=" * 70)
print("MIKA CI - CANONICAL DB CONSISTENCY CHECK")
print("=" * 70)

# ------------------------------------------------------------
# 1. Invalid competitor references
# ------------------------------------------------------------

print("\nINVALID COMPETITOR REFERENCES")

rows = con.execute("""
    SELECT f.finding_id, f.competitor_id
    FROM findings f
    LEFT JOIN competitors c
        ON c.competitor_id = f.competitor_id
    WHERE c.competitor_id IS NULL
""").fetchall()

if rows:
    for row in rows:
        print(dict(row))
else:
    print("NONE")

# ------------------------------------------------------------
# 2. Invalid run references
# ------------------------------------------------------------

print("\nINVALID RUN REFERENCES")

rows = con.execute("""
    SELECT f.finding_id, f.run_id
    FROM findings f
    LEFT JOIN scan_runs s
        ON s.run_id = f.run_id
    WHERE f.run_id IS NOT NULL
      AND s.run_id IS NULL
""").fetchall()

if rows:
    for row in rows:
        print(dict(row))
else:
    print("NONE")

# ------------------------------------------------------------
# 3. Orphan child observations
# ------------------------------------------------------------

print("\nORPHAN PRICE OBSERVATIONS")

rows = con.execute("""
    SELECT p.observation_id, p.finding_id
    FROM price_observations p
    LEFT JOIN findings f
        ON f.finding_id = p.finding_id
    WHERE f.finding_id IS NULL
""").fetchall()

if rows:
    for row in rows:
        print(dict(row))
else:
    print("NONE")

print("\nORPHAN PROMOTION OBSERVATIONS")

rows = con.execute("""
    SELECT p.observation_id, p.finding_id
    FROM promotion_observations p
    LEFT JOIN findings f
        ON f.finding_id = p.finding_id
    WHERE f.finding_id IS NULL
""").fetchall()

if rows:
    for row in rows:
        print(dict(row))
else:
    print("NONE")

print("\nORPHAN NEWS OBSERVATIONS")

rows = con.execute("""
    SELECT n.observation_id, n.finding_id
    FROM news_observations n
    LEFT JOIN findings f
        ON f.finding_id = n.finding_id
    WHERE f.finding_id IS NULL
""").fetchall()

if rows:
    for row in rows:
        print(dict(row))
else:
    print("NONE")

# ------------------------------------------------------------
# 4. Findings without corresponding observation
# ------------------------------------------------------------

print("\nPRICE FINDINGS WITHOUT PRICE OBSERVATION")

rows = con.execute("""
    SELECT f.finding_id
    FROM findings f
    LEFT JOIN price_observations p
        ON p.finding_id = f.finding_id
    WHERE f.finding_type = 'price'
      AND p.finding_id IS NULL
""").fetchall()

print("COUNT:", len(rows))

for row in rows:
    print(row["finding_id"])

print("\nPROMOTION FINDINGS WITHOUT PROMOTION OBSERVATION")

rows = con.execute("""
    SELECT f.finding_id
    FROM findings f
    LEFT JOIN promotion_observations p
        ON p.finding_id = f.finding_id
    WHERE f.finding_type = 'promotion'
      AND p.finding_id IS NULL
""").fetchall()

print("COUNT:", len(rows))

for row in rows:
    print(row["finding_id"])

print("\nNEWS FINDINGS WITHOUT NEWS OBSERVATION")

rows = con.execute("""
    SELECT f.finding_id
    FROM findings f
    LEFT JOIN news_observations n
        ON n.finding_id = f.finding_id
    WHERE f.finding_type = 'news'
      AND n.finding_id IS NULL
""").fetchall()

print("COUNT:", len(rows))

for row in rows:
    print(row["finding_id"])

# ------------------------------------------------------------
# 5. Invalid finding types
# ------------------------------------------------------------

print("\nINVALID FINDING TYPES")

rows = con.execute("""
    SELECT finding_type, COUNT(*) AS n
    FROM findings
    WHERE finding_type NOT IN (
        'price',
        'promotion',
        'news',
        'product'
    )
    GROUP BY finding_type
""").fetchall()

if rows:
    for row in rows:
        print(dict(row))
else:
    print("NONE")

# ------------------------------------------------------------
# 6. Blank required finding fields
# ------------------------------------------------------------

print("\nBLANK REQUIRED FINDING FIELDS")

checks = {
    "finding_id": "finding_id",
    "scan_week": "scan_week",
    "competitor_id": "competitor_id",
    "finding_type": "finding_type",
    "summary": "summary",
    "observed_date": "observed_date",
}

for label, column in checks.items():

    if column == "competitor_id":
        sql = f"""
            SELECT COUNT(*) AS n
            FROM findings
            WHERE {column} IS NULL
        """
    else:
        sql = f"""
            SELECT COUNT(*) AS n
            FROM findings
            WHERE {column} IS NULL
               OR TRIM(CAST({column} AS TEXT)) = ''
        """

    count = con.execute(sql).fetchone()["n"]

    print(f"{label}: {count}")

# ------------------------------------------------------------
# 7. Invalid dates
# ------------------------------------------------------------

print("\nINVALID OBSERVED DATES")

rows = con.execute("""
    SELECT finding_id, observed_date
    FROM findings
    WHERE date(observed_date) IS NULL
""").fetchall()

if rows:
    for row in rows:
        print(dict(row))
else:
    print("NONE")

# ------------------------------------------------------------
# 8. Scan run consistency
# ------------------------------------------------------------

print("\nSCAN RUN CONSISTENCY")

rows = con.execute("""
    SELECT
        s.run_id,
        s.scan_week,
        s.status,
        s.findings_created,
        COUNT(f.finding_id) AS actual_findings
    FROM scan_runs s
    LEFT JOIN findings f
        ON f.run_id = s.run_id
    GROUP BY
        s.run_id,
        s.scan_week,
        s.status,
        s.findings_created
    ORDER BY s.run_id
""").fetchall()

for row in rows:

    expected = row["findings_created"]
    actual = row["actual_findings"]

    status = "OK" if expected == actual else "MISMATCH"

    print(
        f"run={row['run_id']} | "
        f"week={row['scan_week']} | "
        f"status={row['status']} | "
        f"recorded={expected} | "
        f"actual={actual} | "
        f"{status}"
    )

print("\n" + "=" * 70)
print("DB CONSISTENCY CHECK COMPLETE")
print("=" * 70)

con.close()