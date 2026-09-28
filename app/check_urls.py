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
    """
    Open the MIKA CI SQLite database.

    The database is located relative to the project root,
    not relative to the current working directory.
    """

    if not DB_PATH.exists():
        raise FileNotFoundError(
            f"MIKA CI database was not found: {DB_PATH}"
        )

    return sqlite3.connect(DB_PATH)


# ============================================================
# DATABASE CHECK
# ============================================================

def check_database():
    """Check that the database exists and list its tables."""

    connection = get_connection()

    try:
        tables = connection.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
            ORDER BY name
            """
        ).fetchall()

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


# ============================================================
# IMPORTANT:
# Only run the check when this file is executed directly.
# Importing this module must NOT open the database.
# ============================================================

if __name__ == "__main__":
    check_database()
