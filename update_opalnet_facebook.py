import sqlite3

connection = sqlite3.connect("data/mika_competitive_intel.db")

connection.execute(
    "UPDATE social_sources "
    "SET source_url = ? "
    "WHERE competitor_name = ? AND platform = ?",
    ("https://www.facebook.com/opalnet.limited/", "Opalnet", "Facebook"),
)

connection.commit()

rows = connection.execute(
    "SELECT source_id, competitor_name, platform, source_url, verification_status "
    "FROM social_sources WHERE competitor_name = ?",
    ("Opalnet",),
).fetchall()

for row in rows:
    print(row)

connection.close()
