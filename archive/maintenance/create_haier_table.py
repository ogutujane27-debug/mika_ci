import sqlite3

DB = "data/mika_competitive_intel.db"

con = sqlite3.connect(DB)

con.execute("""
CREATE TABLE IF NOT EXISTS haier_products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sku TEXT UNIQUE,
    product_name TEXT NOT NULL,
    category TEXT,
    url TEXT,
    first_seen_date TEXT NOT NULL,
    last_seen_date TEXT NOT NULL
)
""")

con.commit()

print("Haier table created successfully.")

row = con.execute("""
SELECT name
FROM sqlite_master
WHERE type = 'table'
AND name = 'haier_products'
""").fetchone()

print("Table exists:", bool(row))

con.close()
