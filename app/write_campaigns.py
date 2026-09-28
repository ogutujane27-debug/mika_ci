from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path

from campaign_intelligence import (
    build_candidate,
    merge_candidates,
)


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "data" / "mika_competitive_intel.db"


def connect():
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def get_social_observations(connection):
    columns = [
        "observation_id",
        "finding_id",
        "competitor_id",
        "platform",
        "account_name",
        "post_url",
        "post_text",
        "social_type",
        "product_name",
        "model",
        "published_date",
        "observed_date",
        "likes",
        "comments",
        "shares",
        "views",
        "verification_status",
        "confidence",
        "evidence_text",
    ]

    query = f"""
        SELECT
            {", ".join(columns)}
        FROM social_observations
        ORDER BY
            competitor_id,
            published_date,
            observation_id
    """

    return connection.execute(query).fetchall()


def build_candidates(connection):
    observations = get_social_observations(
        connection
    )

    candidates = []

    for observation in observations:
        candidate = build_candidate(
            observation
        )

        if candidate:
            candidates.append(candidate)

    return merge_candidates(candidates)


def get_or_create_campaign(
    connection,
    candidate,
):
    existing = connection.execute(
        """
        SELECT campaign_id
        FROM campaigns
        WHERE competitor_id = ?
          AND campaign_name = ?
          AND (
                start_date = ?
                OR (
                    start_date IS NULL
                    AND ? IS NULL
                )
              )
          AND (
                end_date = ?
                OR (
                    end_date IS NULL
                    AND ? IS NULL
                )
              )
        ORDER BY campaign_id
        LIMIT 1
        """,
        (
            candidate.competitor_id,
            candidate.campaign_name,
            candidate.start_date,
            candidate.start_date,
            candidate.end_date,
            candidate.end_date,
        ),
    ).fetchone()

    evidence_text = "\n\n".join(
        candidate.evidence
    )

    if existing:
        campaign_id = existing["campaign_id"]

        connection.execute(
            """
            UPDATE campaigns
            SET
                campaign_type = ?,
                category = ?,
                offer_value = ?,
                status = ?,
                source_url = ?,
                evidence_text = ?,
                verification_status = ?,
                confidence = ?,
                observed_date = ?
            WHERE campaign_id = ?
            """,
            (
                candidate.campaign_type,
                candidate.category,
                candidate.offer_value,
                candidate.status,
                candidate.source_url,
                evidence_text,
                candidate.verification_status,
                candidate.confidence,
                candidate.observed_date,
                campaign_id,
            ),
        )

        return campaign_id, False

    created_at = datetime.now().isoformat(
        timespec="seconds"
    )

    cursor = connection.execute(
        """
        INSERT INTO campaigns (
            competitor_id,
            campaign_name,
            campaign_type,
            category,
            offer_value,
            start_date,
            end_date,
            status,
            source_url,
            evidence_text,
            verification_status,
            confidence,
            observed_date,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            candidate.competitor_id,
            candidate.campaign_name,
            candidate.campaign_type,
            candidate.category,
            candidate.offer_value,
            candidate.start_date,
            candidate.end_date,
            candidate.status,
            candidate.source_url,
            evidence_text,
            candidate.verification_status,
            candidate.confidence,
            candidate.observed_date,
            created_at,
        ),
    )

    return cursor.lastrowid, True


def get_observation_evidence(
    connection,
    observation_id,
):
    row = connection.execute(
        """
        SELECT
            post_text,
            evidence_text
        FROM social_observations
        WHERE observation_id = ?
        """,
        (observation_id,),
    ).fetchone()

    if not row:
        raise RuntimeError(
            f"Social observation {observation_id} "
            f"was not found."
        )

    return (
        row["evidence_text"]
        or row["post_text"]
        or ""
    )


def link_campaign_post(
    connection,
    campaign_id,
    observation_id,
    evidence_text,
):
    cursor = connection.execute(
        """
        INSERT OR IGNORE INTO campaign_posts (
            campaign_id,
            observation_id,
            link_type,
            evidence_text,
            created_at
        )
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            campaign_id,
            observation_id,
            "social_observation",
            evidence_text,
            datetime.now().isoformat(
                timespec="seconds"
            ),
        ),
    )

    return cursor.rowcount == 1


def write_campaigns():
    connection = connect()

    created_campaigns = 0
    reused_campaigns = 0
    created_links = 0
    existing_links = 0

    try:
        candidates = build_candidates(
            connection
        )

        print("=" * 78)
        print(
            "MIKA CI - PHASE 2C CAMPAIGN DATABASE WRITE"
        )
        print("=" * 78)
        print()
        print(f"Database: {DB_PATH}")
        print(
            f"Detected campaign candidates: "
            f"{len(candidates)}"
        )
        print()

        connection.execute("BEGIN")

        for candidate in candidates:

            campaign_id, created = (
                get_or_create_campaign(
                    connection,
                    candidate,
                )
            )

            if created:
                created_campaigns += 1
                action = "CREATED"
            else:
                reused_campaigns += 1
                action = "REUSED"

            print(
                f"[{action}] "
                f"Competitor ID {candidate.competitor_id} - "
                f"{candidate.campaign_name} "
                f"(campaign_id={campaign_id})"
            )

            for observation_id in (
                candidate.observation_ids
            ):
                evidence_text = (
                    get_observation_evidence(
                        connection,
                        observation_id,
                    )
                )

                linked = link_campaign_post(
                    connection,
                    campaign_id,
                    observation_id,
                    evidence_text,
                )

                if linked:
                    created_links += 1
                else:
                    existing_links += 1

        connection.commit()

        print()
        print("=" * 78)
        print("WRITE COMPLETE")
        print("=" * 78)
        print()
        print(
            f"Campaigns created       : "
            f"{created_campaigns}"
        )
        print(
            f"Campaigns reused        : "
            f"{reused_campaigns}"
        )
        print(
            f"Campaign links created  : "
            f"{created_links}"
        )
        print(
            f"Campaign links existing : "
            f"{existing_links}"
        )
        print()

    except Exception as exc:
        connection.rollback()

        print()
        print("=" * 78)
        print(
            "WRITE FAILED - TRANSACTION ROLLED BACK"
        )
        print("=" * 78)
        print()
        print(f"ERROR: {exc}")

        raise

    finally:
        connection.close()


def verify_database():
    connection = connect()

    try:
        campaign_count = connection.execute(
            """
            SELECT COUNT(*)
            FROM campaigns
            """
        ).fetchone()[0]

        campaign_post_count = connection.execute(
            """
            SELECT COUNT(*)
            FROM campaign_posts
            """
        ).fetchone()[0]

        duplicate_links = connection.execute(
            """
            SELECT
                campaign_id,
                observation_id,
                COUNT(*)
            FROM campaign_posts
            GROUP BY
                campaign_id,
                observation_id
            HAVING COUNT(*) > 1
            """
        ).fetchall()

        print("=" * 78)
        print("DATABASE VERIFICATION")
        print("=" * 78)
        print()
        print(
            f"Campaigns: {campaign_count}"
        )
        print(
            f"Campaign posts: "
            f"{campaign_post_count}"
        )
        print(
            f"Duplicate campaign-post links: "
            f"{len(duplicate_links)}"
        )
        print()

        rows = connection.execute(
            """
            SELECT
                c.campaign_id,
                co.competitor_name,
                c.campaign_name,
                c.status,
                COUNT(cp.campaign_post_id)
            FROM campaigns c
            JOIN competitors co
                ON co.competitor_id =
                   c.competitor_id
            LEFT JOIN campaign_posts cp
                ON cp.campaign_id =
                   c.campaign_id
            GROUP BY
                c.campaign_id,
                co.competitor_name,
                c.campaign_name,
                c.status
            ORDER BY
                c.campaign_id
            """
        ).fetchall()

        print("Campaign summary:")
        print()

        for row in rows:
            (
                campaign_id,
                competitor_name,
                campaign_name,
                status,
                post_count,
            ) = row

            print(
                f"{campaign_id}. "
                f"{competitor_name} | "
                f"{campaign_name} | "
                f"{status} | "
                f"{post_count} posts"
            )

        print()

    finally:
        connection.close()


if __name__ == "__main__":
    write_campaigns()
    verify_database()

