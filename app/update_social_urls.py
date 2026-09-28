import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parents[1] / "data" / "mika_competitive_intel.db"

updates = [
    ("Hotpoint Appliances", "Facebook", "https://www.facebook.com/hotpointkenya"),
    ("Hotpoint Appliances", "Instagram", "https://www.instagram.com/hotpointkenya/"),
    ("Ramtons", "Facebook", "https://www.facebook.com/MyRamtons/"),
    ("Ramtons", "Instagram", "https://www.instagram.com/myramtons/"),
]

conn = sqlite3.connect(DB_PATH)

for competitor_name, platform, source_url in updates:
    conn.execute(
        """
        UPDATE social_sources
        SET source_url = ?,
            last_checked = datetime('now')
        WHERE competitor_name = ?
          AND platform = ?
          AND verification_status = 'VERIFIED'
        """,
        (source_url, competitor_name, platform),
    )

conn.commit()

rows = conn.execute(
    """
    SELECT competitor_name, platform, account_name,
           source_url, verification_status
    FROM social_sources
    ORDER BY competitor_name, platform
    """
).fetchall()

conn.close()

print("=" * 70)
print("MIKA CI - SOCIAL SOURCE REGISTRY")
print("=" * 70)

for row in rows:
    print(" | ".join(str(x) if x is not None else "NONE" for x in row))

print()
print("Registry updated.")