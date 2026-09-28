import sqlite3
from datetime import datetime

DB_PATH = r".\data\mika_competitive_intel.db"
SCAN_WEEK = "2026-W39"
RUN_ID = 40


def connect():
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def build_report(connection):
    campaigns = connection.execute(
        """
        SELECT
            c.campaign_id,
            c.campaign_name,
            c.campaign_type,
            c.category,
            c.offer_value,
            c.start_date,
            c.end_date,
            c.status,
            c.source_url,
            c.evidence_text,
            c.verification_status,
            c.confidence,
            c.observed_date,
            comp.competitor_name
        FROM campaigns c
        JOIN competitors comp
            ON comp.competitor_id = c.competitor_id
        ORDER BY
            comp.competitor_name,
            c.campaign_id
        """
    ).fetchall()

    lines = []

    lines.append("MIKA COMPETITIVE INTELLIGENCE")
    lines.append("PHASE 2C - CAMPAIGN INTELLIGENCE REPORT")
    lines.append("=" * 78)
    lines.append("")
    lines.append(f"Reporting week : {SCAN_WEEK}")
    lines.append(f"Source run     : {RUN_ID}")
    lines.append(
        f"Generated at   : {datetime.now().isoformat(timespec='seconds')}"
    )
    lines.append("")

    lines.append("EXECUTIVE SUMMARY")
    lines.append("-" * 78)
    lines.append(
        f"{len(campaigns)} campaign records are stored for {SCAN_WEEK}."
    )

    competitor_counts = {}
    status_counts = {}
    type_counts = {}

    for campaign in campaigns:
        competitor_counts[campaign["competitor_name"]] = (
            competitor_counts.get(campaign["competitor_name"], 0) + 1
        )

        status = campaign["status"] or "unspecified"
        status_counts[status] = status_counts.get(status, 0) + 1

        campaign_type = campaign["campaign_type"] or "unspecified"
        type_counts[campaign_type] = (
            type_counts.get(campaign_type, 0) + 1
        )

    lines.append("")
    lines.append("Campaigns by competitor:")
    for name in sorted(competitor_counts):
        lines.append(
            f"  - {name}: {competitor_counts[name]}"
        )

    lines.append("")
    lines.append("Campaign status:")
    for status in sorted(status_counts):
        lines.append(
            f"  - {status}: {status_counts[status]}"
        )

    lines.append("")
    lines.append("Campaign type:")
    for campaign_type in sorted(type_counts):
        lines.append(
            f"  - {campaign_type}: {type_counts[campaign_type]}"
        )

    lines.append("")
    lines.append("CAMPAIGN DETAIL")
    lines.append("-" * 78)

    for index, campaign in enumerate(campaigns, start=1):
        post_count = connection.execute(
            """
            SELECT COUNT(*)
            FROM campaign_posts
            WHERE campaign_id = ?
            """,
            (campaign["campaign_id"],),
        ).fetchone()[0]

        lines.append("")
        lines.append(
            f"{index}. {campaign['competitor_name']} - "
            f"{campaign['campaign_name']}"
        )
        lines.append(
            f"   Campaign ID     : {campaign['campaign_id']}"
        )
        lines.append(
            f"   Type            : "
            f"{campaign['campaign_type'] or 'Not specified'}"
        )
        lines.append(
            f"   Category        : "
            f"{campaign['category'] or 'Not specified'}"
        )
        lines.append(
            f"   Offer           : "
            f"{campaign['offer_value'] or 'Not specified'}"
        )
        lines.append(
            f"   Start date      : "
            f"{campaign['start_date'] or 'Not specified'}"
        )
        lines.append(
            f"   End date        : "
            f"{campaign['end_date'] or 'Not specified'}"
        )
        lines.append(
            f"   Status          : "
            f"{campaign['status'] or 'Not specified'}"
        )
        lines.append(
            f"   Verification    : "
            f"{campaign['verification_status'] or 'Not specified'}"
        )
        lines.append(
            f"   Confidence      : "
            f"{campaign['confidence'] or 'Not specified'}"
        )
        lines.append(
            f"   Supporting posts: {post_count}"
        )
        lines.append(
            f"   Source URL      : "
            f"{campaign['source_url'] or 'Not specified'}"
        )

        if campaign["evidence_text"]:
            lines.append(
                f"   Evidence        : {campaign['evidence_text']}"
            )

    lines.append("")
    lines.append("SOURCE EVIDENCE")
    lines.append("-" * 78)

    for campaign in campaigns:
        posts = connection.execute(
            """
            SELECT
                cp.campaign_post_id,
                cp.observation_id,
                cp.link_type,
                cp.evidence_text,
                so.platform,
                so.account_name,
                so.post_url,
                so.published_date,
                so.social_type
            FROM campaign_posts cp
            JOIN social_observations so
                ON so.observation_id = cp.observation_id
            WHERE cp.campaign_id = ?
            ORDER BY so.published_date, so.observation_id
            """,
            (campaign["campaign_id"],),
        ).fetchall()

        lines.append("")
        lines.append(
            f"{campaign['competitor_name']} - "
            f"{campaign['campaign_name']}"
        )

        for post in posts:
            lines.append(
                f"  Observation {post['observation_id']} | "
                f"{post['published_date']} | "
                f"{post['social_type'] or 'unspecified'}"
            )
            lines.append(
                f"  Platform      : "
                f"{post['platform'] or 'Not specified'}"
            )
            lines.append(
                f"  Account       : "
                f"{post['account_name'] or 'Not specified'}"
            )
            lines.append(
                f"  Link type     : "
                f"{post['link_type'] or 'Not specified'}"
            )
            lines.append(
                f"  Post URL      : "
                f"{post['post_url'] or 'Not specified'}"
            )

            if post["evidence_text"]:
                lines.append(
                    f"  Evidence      : {post['evidence_text']}"
                )

    lines.append("")
    lines.append("FACTUAL COMPETITIVE OBSERVATIONS")
    lines.append("-" * 78)

    lines.append(
        "1. Hotpoint Appliances has campaign evidence covering "
        "cooking promotions, a commercial laundry event, a clearance "
        "sale, monthly offers, and a limited-time Night Rush promotion."
    )

    lines.append(
        "2. Ramtons has campaign evidence covering a continuing sale "
        "advertised at up to 70% off selected appliances and a separate "
        "flash-offer event scheduled for 28 September."
    )

    lines.append(
        "3. Campaign records are linked to their supporting social "
        "observations, allowing the campaign view to be traced back "
        "to individual source posts."
    )

    lines.append(
        "4. Campaign status is derived from the stored campaign dates "
        "and the report generation date; campaigns without sufficient "
        "date information remain unspecified rather than being inferred."
    )

    lines.append("")
    lines.append("DATA QUALITY / SCOPE")
    lines.append("-" * 78)
    lines.append(
        "This report contains campaign records detected and persisted "
        "during Phase 2C from the available verified social observations."
    )
    lines.append(
        "It is not a complete market census. Absence of a campaign record "
        "does not establish that a competitor had no campaign."
    )
    lines.append(
        "Verification and confidence values are carried from the "
        "underlying campaign records."
    )

    lines.append("")
    lines.append("=" * 78)
    lines.append("END OF REPORT")

    return "\n".join(lines)


def main():
    connection = connect()

    try:
        existing = connection.execute(
            """
            SELECT report_id
            FROM reports
            WHERE scan_week = ?
              AND run_id = ?
            ORDER BY report_id DESC
            LIMIT 1
            """,
            (SCAN_WEEK, RUN_ID),
        ).fetchone()

        if existing:
            print(
                f"REPORT ALREADY EXISTS: report_id={existing['report_id']}"
            )
            return

        report_text = build_report(connection)

        cursor = connection.execute(
            """
            INSERT INTO reports (
                scan_week,
                run_id,
                generated_at,
                report_text,
                delivered_at
            )
            VALUES (?, ?, ?, ?, NULL)
            """,
            (
                SCAN_WEEK,
                RUN_ID,
                datetime.now().isoformat(timespec="seconds"),
                report_text,
            ),
        )

        report_id = cursor.lastrowid
        connection.commit()

        print("=" * 78)
        print("MIKA CI - PHASE 2C REPORT")
        print("=" * 78)
        print()
        print(f"Report created successfully.")
        print(f"Report ID : {report_id}")
        print(f"Scan week : {SCAN_WEEK}")
        print(f"Run ID    : {RUN_ID}")
        print()

        saved = connection.execute(
            """
            SELECT
                report_id,
                scan_week,
                run_id,
                generated_at,
                delivered_at,
                length(report_text) AS report_length
            FROM reports
            WHERE report_id = ?
            """,
            (report_id,),
        ).fetchone()

        print("DATABASE VERIFICATION")
        print("-" * 78)
        print(f"Report ID       : {saved['report_id']}")
        print(f"Scan week       : {saved['scan_week']}")
        print(f"Run ID          : {saved['run_id']}")
        print(f"Generated at    : {saved['generated_at']}")
        print(f"Delivered at    : {saved['delivered_at']}")
        print(f"Report length   : {saved['report_length']} characters")
        print()
        print("Campaign records were not modified.")
        print("Campaign-post links were not modified.")
        print("=" * 78)

    finally:
        connection.close()


if __name__ == "__main__":
    main()
