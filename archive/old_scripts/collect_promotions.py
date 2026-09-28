"""Collect verified competitor promotions into SQLite.

This collector currently handles the verified Hotpoint campaign:

    ENJOY EXTRA 5% OFF VON AND HISENSE

The collector:
1. Fetches the official Hotpoint offer page.
2. Verifies the campaign title exists on the page.
3. Creates one promotion finding and linked promotion observation.
4. Skips the campaign when the same promotion was already observed
   from the same source.
5. Does not invent promotion dates or target segments.

It does not modify, rename, or delete source files.
"""

import sys
from datetime import date
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "app"))

from config import REQUEST_TIMEOUT, USER_AGENT
from database import (
    add_promotion_finding,
    connect,
    finish_run,
    start_run,
)


HOTPOINT_PROMOTION_URL = (
    "https://www.hotpoint.co.ke/offers/"
    "enjoy-extra-5-off-von-and-hisense/"
)

CAMPAIGN_TITLE = "ENJOY EXTRA 5% OFF VON AND HISENSE"


def fetch_page():
    """Fetch the official Hotpoint promotion page."""
    response = requests.get(
        HOTPOINT_PROMOTION_URL,
        headers={"User-Agent": USER_AGENT},
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()
    return response.text


def promotion_exists(con, source_url, offer_value):
    """Return True when this promotion was already recorded from this source."""

    row = con.execute(
        """
        SELECT 1
        FROM findings f
        JOIN promotion_observations p
            ON p.finding_id = f.finding_id
        WHERE f.finding_type = ?
          AND f.source_url = ?
          AND p.offer_value = ?
        LIMIT 1
        """,
        ("promotion", source_url, offer_value),
    ).fetchone()

    return row is not None


def main():
    """Run the promotion collection."""
    con = connect()
    run_id = start_run(con)

    try:
        html = fetch_page()

        if CAMPAIGN_TITLE not in html.upper():
            raise ValueError(
                f"Verified campaign title not found: {CAMPAIGN_TITLE}"
            )

        offer_value = "Extra 5% off VON and Hisense products"

        if promotion_exists(
            con,
            HOTPOINT_PROMOTION_URL,
            offer_value,
        ):
            finish_run(
                con,
                run_id,
                status="completed",
                sources_checked=1,
                findings_created=0,
            )

            print("Scan completed successfully.")
            print("Campaign found: YES")
            print("New promotion findings created: 0")
            print("Existing promotion skipped: 1")
            return

        evidence = (
            "Offer page title: ENJOY EXTRA 5% OFF VON AND HISENSE"
        )

        finding_id = add_promotion_finding(
            con=con,
            run_id=run_id,
            competitor_brand="Hotpoint",
            brand="VON / Hisense",
            category="Multiple",
            promotion_type="discount",
            offer_value=offer_value,
            summary="Hotpoint promotion: extra 5% off VON and Hisense",
            source_url=HOTPOINT_PROMOTION_URL,
            evidence_text=evidence,
            target_segment=None,
            start_date=None,
            end_date=None,
            source_type="official website",
            verification_status="verified",
            confidence="high",
        )

        finish_run(
            con,
            run_id,
            status="completed",
            sources_checked=1,
            findings_created=1,
        )

        print("Scan completed successfully.")
        print("Campaign found: YES")
        print(f"New promotion finding created: {finding_id}")

    except Exception as exc:
        finish_run(
            con,
            run_id,
            status="failed",
            sources_checked=0,
            findings_created=0,
            error=str(exc),
        )
        raise

    finally:
        con.close()


if __name__ == "__main__":
    main()