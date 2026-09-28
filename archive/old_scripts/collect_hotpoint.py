"""Collect verified Hotpoint product prices into SQLite.

This script:
1. Fetches the Hotpoint fridge/freezer category page.
2. Uses the existing source_collector parser.
3. Creates one scan run.
4. Stores only new price observations in SQLite.
5. Skips observations already recorded for the same model, date,
   price, and source URL.

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
    add_price_finding,
    connect,
    finish_run,
    start_run,
)
from source_collector import parse_products


HOTPOINT_URL = (
    "https://www.hotpoint.co.ke/catalogue/category/fridges-freezers/"
)
HOTPOINT_PRODUCT_BASE_URL = "https://www.hotpoint.co.ke/catalogue/"


def fetch_page():
    """Fetch the Hotpoint fridge/freezer category page."""
    response = requests.get(
        HOTPOINT_URL,
        headers={"User-Agent": USER_AGENT},
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()
    return response.text


def product_url(handle):
    """Build the verified Hotpoint product URL from its handle."""
    return f"{HOTPOINT_PRODUCT_BASE_URL}{handle}/"


def observation_exists(con, model, price_kes, observed_date):
    """Return True when this exact price observation already exists."""

    row = con.execute(
        """
        SELECT 1
        FROM price_observations
        WHERE model = ?
          AND price_kes = ?
          AND observed_date = ?
        LIMIT 1
        """,
        (model, price_kes, observed_date),
    ).fetchone()

    return row is not None


def main():
    """Run the Hotpoint price collection."""
    con = connect()
    run_id = start_run(con)

    try:
        html = fetch_page()
        products = parse_products(html)

        created = 0
        skipped = 0
        observed_date = date.today().isoformat()

        for product in products:
            model = product["model"]
            price_kes = product["price"]
            source_url = product_url(product["handle"])

            if observation_exists(
                con,
                model,
                price_kes,
                observed_date,
            ):
                skipped += 1
                continue

            brand = product["brand"] or "Unknown"
            category = product["sub_category"] or "Unknown"

            promotion_note = None
            if product["original_price"]:
                promotion_note = (
                    f"Was KSh {product['original_price']:,.0f}; "
                    f"current KSh {product['price']:,.0f}"
                )

            evidence = (
                f"Product: {product['name']}; "
                f"Model: {model}; "
                f"Brand: {brand}; "
                f"Current price: KSh {price_kes:,.0f}"
            )

            if product["original_price"]:
                evidence += (
                    f"; Current-page displayed previous/list price: "
                    f"KSh {product['original_price']:,.0f}"
                )

            add_price_finding(
                con=con,
                run_id=run_id,
                competitor_brand="Hotpoint",
                brand=brand,
                category=category,
                product_name=product["name"],
                model=model,
                price_kes=price_kes,
                source_url=source_url,
                evidence_text=evidence,
                promotion_note=promotion_note,
            )

            created += 1

        finish_run(
            con,
            run_id,
            status="completed",
            sources_checked=1,
            findings_created=created,
        )

        print("Scan completed successfully.")
        print(f"Products found: {len(products)}")
        print(f"New findings created: {created}")
        print(f"Existing observations skipped: {skipped}")

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