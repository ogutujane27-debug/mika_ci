import sqlite3
con = sqlite3.connect("data/mika_competitive_intel.db")
count = con.execute("SELECT COUNT(*) FROM bruhm_products").fetchone()
print("Row count:", count[0])
sample = con.execute("SELECT sku, product_name, category, first_seen_date, last_seen_date FROM bruhm_products LIMIT 5").fetchall()
for row in sample:
    print(row)
