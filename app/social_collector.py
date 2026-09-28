"""
MIKA CI - Social Intelligence Collector
Phase 2 / Social Intelligence

READ-ONLY TEST COLLECTOR
- Reads verified social sources from SQLite.
- Fetches only publicly accessible URLs.
- Does NOT write findings or observations.
- Does NOT invent posts.
"""

from __future__ import annotations

import sqlite3
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests
from bs4 import BeautifulSoup


ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data" / "mika_competitive_intel.db"

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/153.0.0.0 Safari/537.36"
)

TIMEOUT = 15


def connect():
    return sqlite3.connect(DB_PATH)


def get_verified_sources(conn):
    return conn.execute(
        """
        SELECT
            source_id,
            competitor_id,
            competitor_name,
            platform,
            account_name,
            source_url,
            verification_status
        FROM social_sources
        WHERE active = 1
          AND verification_status = 'VERIFIED'
          AND source_url IS NOT NULL
          AND TRIM(source_url) <> ''
        ORDER BY competitor_name, platform
        """
    ).fetchall()


def fetch_public_page(url: str):
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": (
            "text/html,application/xhtml+xml,application/xml;"
            "q=0.9,image/avif,image/webp,*/*;q=0.8"
        ),
        "Accept-Language": "en-US,en;q=0.9",
    }

    try:
        response = requests.get(
            url,
            headers=headers,
            timeout=TIMEOUT,
            allow_redirects=True,
        )

        return {
            "ok": response.ok,
            "status_code": response.status_code,
            "final_url": response.url,
            "content": response.text,
            "error": None,
        }

    except requests.RequestException as exc:
        return {
            "ok": False,
            "status_code": None,
            "final_url": url,
            "content": "",
            "error": str(exc),
        }


def extract_page_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")

    for tag in soup(
        ["script", "style", "noscript", "svg", "iframe"]
    ):
        tag.decompose()

    text = soup.get_text(" ", strip=True)

    return " ".join(text.split())


def inspect_source(source):
    (
        source_id,
        competitor_id,
        competitor_name,
        platform,
        account_name,
        source_url,
        verification_status,
    ) = source

    result = fetch_public_page(source_url)

    print("-" * 78)
    print(f"Competitor : {competitor_name}")
    print(f"Platform   : {platform}")
    print(f"Account    : {account_name}")
    print(f"URL        : {source_url}")

    if result["error"]:
        print("STATUS     : REQUEST ERROR")
        print(f"ERROR      : {result['error']}")
        return

    print(f"HTTP       : {result['status_code']}")
    print(f"FINAL URL  : {result['final_url']}")

    if not result["ok"]:
        print("STATUS     : NOT ACCESSIBLE")
        return

    text = extract_page_text(result["content"])

    print("STATUS     : ACCESSIBLE")
    print(f"TEXT SIZE  : {len(text):,} characters")

    if text:
        preview = text[:500].replace("\n", " ")
        print(f"PREVIEW    : {preview}")
    else:
        print("PREVIEW    : No readable page text")

    print("DATABASE   : NO WRITE")


def main():
    print("=" * 78)
    print("MIKA CI - SOCIAL INTELLIGENCE")
    print("READ-ONLY SOURCE ACCESS TEST")
    print("=" * 78)

    print(f"Database: {DB_PATH}")
    print(f"Window  : last 7 days")
    print("Writes  : DISABLED")
    print()

    if not DB_PATH.exists():
        print("ERROR: Database does not exist.")
        sys.exit(1)

    conn = connect()

    try:
        sources = get_verified_sources(conn)

        print(f"Verified sources with URLs: {len(sources)}")
        print()

        if not sources:
            print("No verified sources with URLs available.")
            return

        accessible = 0
        inaccessible = 0

        for source in sources:
            before = accessible

            result = fetch_public_page(source[5])

            if result["ok"]:
                accessible += 1
            else:
                inaccessible += 1

            inspect_source(source)

        print()
        print("=" * 78)
        print("COLLECTION TEST SUMMARY")
        print("=" * 78)
        print(f"Sources tested : {len(sources)}")
        print(f"Accessible     : {accessible}")
        print(f"Inaccessible   : {inaccessible}")
        print("Database writes: 0")
        print()
        print("READ-ONLY TEST COMPLETE.")

    finally:
        conn.close()


if __name__ == "__main__":
    main()

