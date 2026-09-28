import sqlite3

connection = sqlite3.connect("data/mika_competitive_intel.db")
connection.row_factory = sqlite3.Row

print("=== competitors WHERE competitor_name = 'Samsutech' ===")
rows = connection.execute(
    "SELECT competitor_id, competitor_name, brand_name "
    "FROM competitors "
    "WHERE competitor_name = 'Samsutech'"
).fetchall()
print(f"ROWS: {len(rows)}")
for row in rows:
    print(dict(row))

print()
print("=== social_sources WHERE competitor_name = 'Samsutech' ===")
rows = connection.execute(
    "SELECT rowid, * FROM social_sources "
    "WHERE competitor_name = 'Samsutech'"
).fetchall()
print(f"ROWS: {len(rows)}")
for row in rows:
    print(dict(row))

connection.close()