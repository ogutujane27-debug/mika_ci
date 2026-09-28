import sqlite3

DB = "data/mika_competitive_intel.db"

finding_ids = [
    "CI-2026-09-00143",
    "CI-2026-09-00144",
    "CI-2026-09-00145",
]

con = sqlite3.connect(DB)
con.execute("PRAGMA foreign_keys = ON")

try:
    for finding_id in finding_ids:
        con.execute(
            "DELETE FROM price_observations WHERE finding_id = ?",
            (finding_id,),
        )

        con.execute(
            "DELETE FROM findings WHERE finding_id = ?",
            (finding_id,),
        )

    con.commit()

    print("CLEANUP COMPLETE")
    print("=" * 70)
    for finding_id in finding_ids:
        print(f"Removed: {finding_id}")

except Exception:
    con.rollback()
    raise

finally:
    con.close()