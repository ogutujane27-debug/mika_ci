import sqlite3
from pathlib import Path
from datetime import date


BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "data" / "mika_competitive_intel.db"


def connect():
    return sqlite3.connect(DB_PATH)


def initialize_social_intelligence():
    con = connect()

    con.execute(
        """
        CREATE TABLE IF NOT EXISTS social_observations (
            observation_id INTEGER PRIMARY KEY AUTOINCREMENT,
            finding_id TEXT NOT NULL,
            competitor_id INTEGER NOT NULL,
            platform TEXT NOT NULL,
            account_name TEXT,
            post_url TEXT,
            post_text TEXT,
            social_type TEXT,
            product_name TEXT,
            model TEXT,
            published_date TEXT,
            observed_date TEXT NOT NULL,
            likes INTEGER,
            comments INTEGER,
            shares INTEGER,
            views INTEGER,
            verification_status TEXT,
            confidence TEXT,
            evidence_text TEXT,
            FOREIGN KEY (finding_id) REFERENCES findings(finding_id),
            FOREIGN KEY (competitor_id) REFERENCES competitors(competitor_id)
        )
        """
    )

    con.commit()
    con.close()


def get_social_summary():
    con = connect()

    total = con.execute(
        """
        SELECT COUNT(*)
        FROM social_observations
        """
    ).fetchone()[0]

    platforms = con.execute(
        """
        SELECT COUNT(DISTINCT platform)
        FROM social_observations
        """
    ).fetchone()[0]

    competitors = con.execute(
        """
        SELECT COUNT(DISTINCT competitor_id)
        FROM social_observations
        """
    ).fetchone()[0]

    con.close()

    return {
        "total": total,
        "platforms": platforms,
        "competitors": competitors,
    }


def get_recent_social(limit=50):
    con = connect()

    rows = con.execute(
        """
        SELECT
            so.observation_id,
            c.brand_name,
            so.platform,
            so.account_name,
            so.social_type,
            so.product_name,
            so.model,
            so.published_date,
            so.observed_date,
            so.likes,
            so.comments,
            so.shares,
            so.views,
            so.verification_status,
            so.confidence,
            so.post_url
        FROM social_observations so
        JOIN competitors c
            ON c.competitor_id = so.competitor_id
        ORDER BY
            COALESCE(
                so.published_date,
                so.observed_date
            ) DESC,
            so.observation_id DESC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()

    columns = [
        "Observation ID",
        "Brand",
        "Platform",
        "Account",
        "Type",
        "Product",
        "Model",
        "Published",
        "Observed",
        "Likes",
        "Comments",
        "Shares",
        "Views",
        "Verification",
        "Confidence",
        "Source",
    ]

    con.close()

    return [dict(zip(columns, row)) for row in rows]


if __name__ == "__main__":
    initialize_social_intelligence()

    summary = get_social_summary()

    print("=" * 70)
    print("MIKA CI - SOCIAL INTELLIGENCE")
    print("=" * 70)
    print("Social observations:", summary["total"])
    print("Platforms:", summary["platforms"])
    print("Competitors:", summary["competitors"])
    print("Database layer ready.")