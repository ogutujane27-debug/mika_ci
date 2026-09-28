import sqlite3

connection = sqlite3.connect("data/mika_competitive_intel.db")
rows = connection.execute(
    "SELECT source_id, competitor_name, platform, source_url "
    "FROM social_sources "
    "WHERE source_url IS NOT NULL"
).fetchall()

for row in rows:
    print(row[0], row[1], row[2], repr(row[3]))

connection.close()
