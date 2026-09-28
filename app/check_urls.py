from pathlib import Path
import sqlite3


# ============================================================
# MIKA CI PROJECT PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "data" / "mika_competitive_intel.db"


# ============================================================
# DATABASE CONNECTION
# ============================================================

def get_connection():
    """Open the MIKA CI SQLite database from the project root."""

    if not DB_PATH.exists():
        raise FileNotFoundError(
            f"MIKA CI database was not found: {DB_PATH}"
        )

    return sqlite3.connect(DB_PATH)


# ============================================================
# STANDALONE DATABASE CHECK
# ============================================================

if __name__ == "__main__":

    connection = get_connection()

    try:
        cursor = connection.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
            ORDER BY name
            """
        )

        tables = cursor.fetchall()

        print("=" * 70)
        print("MIKA CI DATABASE CHECK")
        print("=" * 70)

        print(f"Database : {DB_PATH}")
        print(f"Exists   : {DB_PATH.exists()}")
        print(f"Tables   : {len(tables)}")
        print()

        for table in tables:
            print(f" - {table[0]}")

        print()
        print("Database check completed successfully.")

    finally:
        connection.close()
