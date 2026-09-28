import sqlite3
con = sqlite3.connect("data/mika_competitive_intel.db")
con.execute("""
CREATE TABLE IF NOT EXISTS bruhm_products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id INTEGER,
    competitor TEXT,
    sku TEXT UNIQUE,
    product_name TEXT,
    category TEXT,
    product_url TEXT,
    first_seen_date DATE,
    last_seen_date DATE
)
""")
con.commit()
print("bruhm_products table created")
