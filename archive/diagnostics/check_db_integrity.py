import sqlite3

DB = "data/mika_competitive_intel.db"

con = sqlite3.connect(DB)
con.row_factory = sqlite3.Row

print("=" * 70)
print("MIKA CI - DATABASE SCHEMA CHECK")
print("=" * 70)

tables = con.execute("""
    SELECT name
    FROM sqlite_master
    WHERE type = 'table'
    AND name NOT LIKE 'sqlite_%'
    ORDER BY name
""").fetchall()

for row in tables:
    table = row["name"]

    print("\n" + "=" * 70)
    print(f"TABLE: {table}")
    print("=" * 70)

    columns = con.execute(
        f'PRAGMA table_info("{table}")'
    ).fetchall()

    for col in columns:
        print(
            f"{col['cid']:>2} | "
            f"{col['name']:<30} | "
            f"{col['type']:<15} | "
            f"NOT NULL={col['notnull']} | "
            f"PK={col['pk']} | "
            f"DEFAULT={col['dflt_value']}"
        )

    indexes = con.execute(
        f'PRAGMA index_list("{table}")'
    ).fetchall()

    if indexes:
        print("\nINDEXES")

        for index in indexes:
            print(
                f"- {index['name']} "
                f"(unique={index['unique']})"
            )

            index_columns = con.execute(
                f'PRAGMA index_info("{index["name"]}")'
            ).fetchall()

            for idx_col in index_columns:
                print(
                    f"    column: {idx_col['name']}"
                )

print("\n" + "=" * 70)
print("SCHEMA CHECK COMPLETE")
print("=" * 70)

con.close()