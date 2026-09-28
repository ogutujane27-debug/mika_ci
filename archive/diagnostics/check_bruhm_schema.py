import sqlite3
con = sqlite3.connect("data/mika_competitive_intel.db")
cursor = con.execute("PRAGMA table_info(bruhm_products)")
for row in cursor.fetchall():
    print(row)
