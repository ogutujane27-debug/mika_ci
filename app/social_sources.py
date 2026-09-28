import sqlite3
from datetime import date
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "data" / "mika_competitive_intel.db"


SOCIAL_SOURCES = [
    # Armco
    {
        "competitor_name": "Armco",
        "platform": "Facebook",
        "account_name": "Armco Kenya",
        "source_url": None,
        "verification_status": "UNVERIFIED",
        "verification_source": None,
    },
    {
        "competitor_name": "Armco",
        "platform": "Instagram",
        "account_name": "Armco Kenya",
        "source_url": None,
        "verification_status": "UNVERIFIED",
        "verification_source": None,
    },

    # Bruhm
    {
        "competitor_name": "Bruhm",
        "platform": "Facebook",
        "account_name": "Bruhm Kenya",
        "source_url": None,
        "verification_status": "UNVERIFIED",
        "verification_source": None,
    },
    {
        "competitor_name": "Bruhm",
        "platform": "Instagram",
        "account_name": "Bruhm Kenya",
        "source_url": None,
        "verification_status": "UNVERIFIED",
        "verification_source": None,
    },

    # Haier Kenya
    {
        "competitor_name": "Haier Kenya",
        "platform": "Facebook",
        "account_name": "Haier Kenya",
        "source_url": None,
        "verification_status": "UNVERIFIED",
        "verification_source": None,
    },
    {
        "competitor_name": "Haier Kenya",
        "platform": "Instagram",
        "account_name": "Haier Kenya",
        "source_url": None,
        "verification_status": "UNVERIFIED",
        "verification_source": None,
    },

    # Hisense Kenya
    {
        "competitor_name": "Hisense Kenya",
        "platform": "Facebook",
        "account_name": "Hisense Kenya",
        "source_url": None,
        "verification_status": "UNVERIFIED",
        "verification_source": "https://hisensekenya.ke/",
    },
    {
        "competitor_name": "Hisense Kenya",
        "platform": "Instagram",
        "account_name": "Hisense Kenya",
        "source_url": None,
        "verification_status": "UNVERIFIED",
        "verification_source": "https://hisensekenya.ke/",
    },

    # Hotpoint
    {
        "competitor_name": "Hotpoint Appliances",
        "platform": "Facebook",
        "account_name": "@hotpointkenya",
        "source_url": "https://www.facebook.com/hotpointkenya",
        "verification_status": "VERIFIED",
        "verification_source": "https://linktr.ee/hotpointkenya",
    },
    {
        "competitor_name": "Hotpoint Appliances",
        "platform": "Instagram",
        "account_name": "@hotpointkenya",
        "source_url": "https://www.instagram.com/hotpointkenya/",
        "verification_status": "VERIFIED",
        "verification_source": "https://linktr.ee/hotpointkenya",
    },

    # K-Elec
    {
        "competitor_name": "K-Elec",
        "platform": "Facebook",
        "account_name": "K-Elec",
        "source_url": None,
        "verification_status": "UNVERIFIED",
        "verification_source": None,
    },
    {
        "competitor_name": "K-Elec",
        "platform": "Instagram",
        "account_name": "K-Elec",
        "source_url": None,
        "verification_status": "UNVERIFIED",
        "verification_source": None,
    },

    # Opalnet
    {
        "competitor_name": "Opalnet",
        "platform": "Facebook",
        "account_name": "@opalnetlimited",
        "source_url": "https://www.facebook.com/opalnet.limited/",
        "verification_status": "VERIFIED",
        "verification_source": "https://www.opalnet.co.ke/",
    },
    {
        "competitor_name": "Opalnet",
        "platform": "Instagram",
        "account_name": "@opalnetlimited",
        "source_url": None,
        "verification_status": "UNVERIFIED",
        "verification_source": "https://www.opalnet.co.ke/",
    },

    # Ramtons
    {
        "competitor_name": "Ramtons",
        "platform": "Facebook",
        "account_name": "@myramtons",
        "source_url": "https://www.facebook.com/MyRamtons/",
        "verification_status": "VERIFIED",
        "verification_source": "https://linktr.ee/myramtons",
    },
    {
        "competitor_name": "Ramtons",
        "platform": "Instagram",
        "account_name": "@myramtons",
        "source_url": "https://www.instagram.com/myramtons/",
        "verification_status": "VERIFIED",
        "verification_source": "https://linktr.ee/myramtons",
    },

    # Samsutech
    {
        "competitor_name": "Samsutech",
        "platform": "Facebook",
        "account_name": "Samsutech",
        "source_url": None,
        "verification_status": "UNVERIFIED",
        "verification_source": None,
    },
    {
        "competitor_name": "Samsutech",
        "platform": "Instagram",
        "account_name": "Samsutech",
        "source_url": None,
        "verification_status": "UNVERIFIED",
        "verification_source": None,
    },
]


def connect():
    return sqlite3.connect(DB_PATH)


def initialize_social_sources():
    conn = connect()
    cursor = conn.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS social_sources (
            source_id INTEGER PRIMARY KEY AUTOINCREMENT,
            competitor_id INTEGER,
            competitor_name TEXT NOT NULL,
            platform TEXT NOT NULL,
            account_name TEXT NOT NULL,
            source_url TEXT,
            active INTEGER NOT NULL DEFAULT 1,
            verification_status TEXT NOT NULL DEFAULT 'UNVERIFIED',
            verification_source TEXT,
            last_checked TEXT,
            FOREIGN KEY (competitor_id)
                REFERENCES competitors(competitor_id)
        )
        """
    )

    # Controlled rebuild.
    # The complete source definition above is the source of truth.
    cursor.execute("DELETE FROM social_sources")

    for source in SOCIAL_SOURCES:
        competitor = cursor.execute(
            """
            SELECT competitor_id
            FROM competitors
            WHERE competitor_name = ?
               OR brand_name = ?
            LIMIT 1
            """,
            (
                source["competitor_name"],
                source["competitor_name"],
            ),
        ).fetchone()

        competitor_id = competitor[0] if competitor else None

        last_checked = (
            date.today().isoformat()
            if source["verification_status"] == "VERIFIED"
            else None
        )

        cursor.execute(
            """
            INSERT INTO social_sources (
                competitor_id,
                competitor_name,
                platform,
                account_name,
                source_url,
                active,
                verification_status,
                verification_source,
                last_checked
            )
            VALUES (?, ?, ?, ?, ?, 1, ?, ?, ?)
            """,
            (
                competitor_id,
                source["competitor_name"],
                source["platform"],
                source["account_name"],
                source["source_url"],
                source["verification_status"],
                source["verification_source"],
                last_checked,
            ),
        )

    conn.commit()

    total = cursor.execute(
        "SELECT COUNT(*) FROM social_sources"
    ).fetchone()[0]

    verified = cursor.execute(
        """
        SELECT COUNT(*)
        FROM social_sources
        WHERE verification_status = 'VERIFIED'
        """
    ).fetchone()[0]

    verified_with_urls = cursor.execute(
        """
        SELECT COUNT(*)
        FROM social_sources
        WHERE verification_status = 'VERIFIED'
          AND source_url IS NOT NULL
          AND TRIM(source_url) <> ''
        """
    ).fetchone()[0]

    duplicate_groups = cursor.execute(
        """
        SELECT COUNT(*)
        FROM (
            SELECT competitor_name, platform, account_name, COUNT(*) AS n
            FROM social_sources
            GROUP BY competitor_name, platform, account_name
            HAVING n > 1
        )
        """
    ).fetchone()[0]

    print("=" * 78)
    print("MIKA CI - SOCIAL SOURCE REGISTRY")
    print("=" * 78)
    print(f"Database: {DB_PATH}")
    print()
    print(f"Registered sources:        {total}")
    print(f"Verified sources:          {verified}")
    print(f"Verified sources with URL: {verified_with_urls}")
    print(f"Duplicate groups:          {duplicate_groups}")
    print()

    rows = cursor.execute(
        """
        SELECT
            competitor_name,
            platform,
            account_name,
            source_url,
            verification_status
        FROM social_sources
        ORDER BY competitor_name, platform
        """
    ).fetchall()

    for row in rows:
        competitor_name, platform, account_name, source_url, status = row

        print(
            f"{competitor_name:<22} "
            f"{platform:<10} "
            f"{account_name:<20} "
            f"{status:<10} "
            f"{source_url or 'NO DIRECT URL'}"
        )

    conn.close()


def get_social_sources(
    verified_only=False,
    active_only=True,
    urls_only=False,
):
    conn = connect()

    query = """
        SELECT
            source_id,
            competitor_id,
            competitor_name,
            platform,
            account_name,
            source_url,
            active,
            verification_status,
            verification_source,
            last_checked
        FROM social_sources
        WHERE 1 = 1
    """

    params = []

    if verified_only:
        query += " AND verification_status = 'VERIFIED'"

    if active_only:
        query += " AND active = 1"

    if urls_only:
        query += " AND source_url IS NOT NULL AND TRIM(source_url) <> ''"

    query += """
        ORDER BY competitor_name, platform
    """

    rows = conn.execute(query, params).fetchall()
    conn.close()

    return rows


def mark_source_verified(
    source_id,
    source_url,
    verification_source=None,
):
    conn = connect()

    conn.execute(
        """
        UPDATE social_sources
        SET
            source_url = ?,
            verification_status = 'VERIFIED',
            verification_source = ?,
            last_checked = ?
        WHERE source_id = ?
        """,
        (
            source_url,
            verification_source,
            date.today().isoformat(),
            source_id,
        ),
    )

    conn.commit()
    conn.close()


if __name__ == "__main__":
    initialize_social_sources()




