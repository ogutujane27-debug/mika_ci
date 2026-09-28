import sqlite3
con = sqlite3.connect("data/mika_competitive_intel.db")
rows = con.execute("SELECT model, price_kes FROM price_observations WHERE observed_date = DATE('now') ORDER BY model").fetchall()
for r in rows:
    print(r)
