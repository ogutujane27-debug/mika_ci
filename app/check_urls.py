from pathlib import Path
import sqlite3

# Project root:
# C:\Users\User\Desktop\mika_ci
BASE_DIR = Path(__file__).resolve().parent.parent

DB_PATH = BASE_DIR / "data" / "mika_competitive_intel.db"


def get_connection():
    """Open the MIKA CI SQLite database using an absolute project path."""
    if not DB_PATH.exists():
        raise FileNotFoundError(
            f"MIKA CI database was not found: {DB_PATH}"
        )

    return sqlite3.connect(DB_PATH)


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

    print("MIKA CI DATABASE CHECK")
    print("======================")
    print(f"Database: {DB_PATH}")
    print(f"Exists: {DB_PATH.exists()}")
    print(f"Tables found: {len(tables)}")

    for table in tables:
        print(f" - {table[0]}")

finally:
    connection.close()
