import sqlite3

con = sqlite3.connect(r".\data\mika_competitive_intel.db")

tables = [
    ("HAIER", "haier_products"),
    ("BRUHM", "bruhm_products"),
    ("K-ELEC", "k_elec_products"),
]

for name, table in tables:
    print()
    print(name)
    print("-" * 40)

    rows = con.execute(
        f"""
        SELECT first_seen_date, COUNT(*)
        FROM {table}
        GROUP BY first_seen_date
        ORDER BY first_seen_date
        """
    ).fetchall()

    for row in rows:
        print(f"{row[0]} | {row[1]}")

con.close()
