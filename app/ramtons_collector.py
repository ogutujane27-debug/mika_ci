"""Collect verified Ramtons product prices and sale promotions into SQLite.

This script:
1. Fetches the Ramtons homepage.
2. Parses the current product cards.
3. Stores new price observations in SQLite.
4. Fetches the official Ramtons Sale page.
5. Parses products with an actual price reduction.
6. Stores verified promotion observations in SQLite.
7. Skips observations already recorded.

It does not modify, rename, or delete source files.
"""

import re
import sys
from datetime import date
from pathlib import Path

import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "app"))

from config import REQUEST_TIMEOUT, USER_AGENT
from database import (
    add_price_finding,
    add_promotion_finding,
    connect,
    finish_run,
    start_run,
)


RAMTONS_URL = "https://www.ramtons.com/"
RAMTONS_SALE_URL = "https://www.ramtons.com/sale"


def fetch_page(url):
    """Fetch a Ramtons page."""
    response = requests.get(
        url,
        headers={"User-Agent": USER_AGENT},
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()
    return response.text


def extract_model(name):
    """Extract a Ramtons model such as RW/218 or RM/381."""
    match = re.search(
        r"\b([A-Z]{1,5}/\d{2,5})\b",
        name.upper(),
    )
    return match.group(1) if match else None


def parse_products(html):
    """Return structured Ramtons homepage product-price observations."""
    soup = BeautifulSoup(html, "html.parser")
    cards = soup.select(".product-card")

    products = []

    for card in cards:
        name_link = card.select_one(".product-card__name")
        price_box = card.select_one(".price-box")

        if not name_link or not price_box:
            continue

        name = name_link.get_text(" ", strip=True)
        url = name_link.get("href")
        product_id = price_box.get("data-product-id")

        final_price = price_box.select_one(
            '[data-price-type="finalPrice"]'
        )

        old_price = price_box.select_one(
            '[data-price-type="oldPrice"]'
        )

        if not final_price:
            continue

        current_price = float(
            final_price.get("data-price-amount")
        )

        previous_price = None

        if old_price:
            previous_price = float(
                old_price.get("data-price-amount")
            )

        discount = card.select_one(
            ".product-card__discount"
        )

        discount_text = (
            discount.get_text(" ", strip=True)
            if discount
            else None
        )

        products.append(
            {
                "product_id": product_id,
                "name": name,
                "model": extract_model(name),
                "url": url,
                "price": current_price,
                "original_price": previous_price,
                "discount": discount_text,
            }
        )

    return products


def parse_sale_products(html):
    """Return products from the official Ramtons Sale page.

    A promotion is created only when the page explicitly provides
    both a current price and a previous price, and the current price
    is lower than the previous price.
    """
    soup = BeautifulSoup(html, "html.parser")
    cards = soup.select(".product-card")

    products = []
    seen = set()

    for card in cards:
        name_link = card.select_one(".product-card__name")
        price_box = card.select_one(".price-box")

        if not name_link or not price_box:
            continue

        name = name_link.get_text(" ", strip=True)
        url = name_link.get("href")
        product_id = price_box.get("data-product-id")

        final_price = price_box.select_one(
            '[data-price-type="finalPrice"]'
        )

        old_price = price_box.select_one(
            '[data-price-type="oldPrice"]'
        )

        if not final_price or not old_price:
            continue

        current_raw = final_price.get("data-price-amount")
        previous_raw = old_price.get("data-price-amount")

        if not current_raw or not previous_raw:
            continue

        try:
            current_price = float(current_raw)
            previous_price = float(previous_raw)
        except (TypeError, ValueError):
            continue

        if current_price >= previous_price:
            continue

        discount = card.select_one(
            ".product-card__discount"
        )

        discount_text = (
            discount.get_text(" ", strip=True)
            if discount
            else None
        )

        model = extract_model(name)

        key = (
            model or product_id or name,
            current_price,
            previous_price,
        )

        if key in seen:
            continue

        seen.add(key)

        products.append(
            {
                "product_id": product_id,
                "name": name,
                "model": model,
                "url": url,
                "price": current_price,
                "original_price": previous_price,
                "discount": discount_text,
            }
        )

    return products


def observation_exists(con, model, price_kes, observed_date):
    """Return True when this exact price observation already exists."""

    if not model:
        return False

    row = con.execute(
        """
        SELECT 1
        FROM price_observations
        WHERE model = ?
          AND price_kes = ?
          AND observed_date = ?
        LIMIT 1
        """,
        (
            model,
            price_kes,
            observed_date,
        ),
    ).fetchone()

    return row is not None


def sale_promotion_exists(
    con,
    model,
    current_price,
    previous_price,
    observed_date,
):
    """Return True when this exact sale promotion was already recorded."""

    if not model:
        return False

    row = con.execute(
        """
        SELECT 1
        FROM findings f
        JOIN promotion_observations p
            ON p.finding_id = f.finding_id
        WHERE f.competitor_id = (
            SELECT competitor_id
            FROM competitors
            WHERE competitor_name = ?
            LIMIT 1
        )
          AND f.finding_type = 'promotion'
          AND f.observed_date = ?
          AND p.offer_value = ?
        LIMIT 1
        """,
        (
            "Ramtons",
            observed_date,
            f"KSh {previous_price:,.0f} -> KSh {current_price:,.0f}",
        ),
    ).fetchone()

    return row is not None


def collect_price_observations(
    con,
    run_id,
    products,
    observed_date,
):
    """Store homepage price observations."""

    created = 0
    skipped = 0

    for product in products:
        model = product["model"]
        price_kes = product["price"]

        if observation_exists(
            con,
            model,
            price_kes,
            observed_date,
        ):
            skipped += 1
            continue

        promotion_note = None

        if product["original_price"]:
            promotion_note = (
                f"Was KSh "
                f"{product['original_price']:,.0f}; "
                f"current KSh "
                f"{price_kes:,.0f}"
            )

        if product["discount"]:
            if promotion_note:
                promotion_note += (
                    f"; displayed discount: "
                    f"{product['discount']}"
                )
            else:
                promotion_note = (
                    f"Displayed discount: "
                    f"{product['discount']}"
                )

        evidence = (
            f"Product: {product['name']}; "
            f"Model: {model or 'Not detected'}; "
            f"Product ID: {product['product_id']}; "
            f"Current price: "
            f"KSh {price_kes:,.0f}"
        )

        if product["original_price"]:
            evidence += (
                f"; Current-page displayed "
                f"previous/list price: "
                f"KSh {product['original_price']:,.0f}"
            )

        if product["discount"]:
            evidence += (
                f"; Displayed discount: "
                f"{product['discount']}"
            )

        add_price_finding(
            con=con,
            run_id=run_id,
            competitor_brand="Ramtons",
            brand="Ramtons",
            category="Home appliances",
            product_name=product["name"],
            model=model,
            price_kes=price_kes,
            source_url=product["url"],
            evidence_text=evidence,
            promotion_note=promotion_note,
        )

        created += 1

    return created, skipped


def collect_sale_promotions(
    con,
    run_id,
    sale_products,
    observed_date,
):
    """Store verified Ramtons Sale-page promotions."""

    created = 0
    skipped = 0

    for product in sale_products:
        model = product["model"]
        current_price = product["price"]
        previous_price = product["original_price"]

        if current_price is None or previous_price is None:
            continue

        if current_price >= previous_price:
            continue

        if sale_promotion_exists(
            con,
            model,
            current_price,
            previous_price,
            observed_date,
        ):
            skipped += 1
            continue

        discount_text = product["discount"]

        offer_value = (
            f"KSh {previous_price:,.0f} -> "
            f"KSh {current_price:,.0f}"
        )

        summary = (
            f"Ramtons sale: {product['name']} "
            f"reduced from KSh "
            f"{previous_price:,.0f} to KSh "
            f"{current_price:,.0f}"
        )

        evidence = (
            f"Official Ramtons Sale page; "
            f"Product: {product['name']}; "
            f"Model: {model or 'Not detected'}; "
            f"Product ID: {product['product_id']}; "
            f"Previous price: "
            f"KSh {previous_price:,.0f}; "
            f"Current sale price: "
            f"KSh {current_price:,.0f}"
        )

        if discount_text:
            evidence += (
                f"; Displayed discount: "
                f"{discount_text}"
            )

        add_promotion_finding(
            con=con,
            run_id=run_id,
            competitor_brand="Ramtons",
            brand="Ramtons",
            category="Home appliances",
            promotion_type="sale",
            offer_value=offer_value,
            summary=summary,
            source_url=RAMTONS_SALE_URL,
            evidence_text=evidence,
            target_segment=None,
            start_date=None,
            end_date=None,
            source_type="official website",
            verification_status="verified",
            confidence="high",
            published_date=None,
        )

        created += 1

    return created, skipped


def main():
    """Run Ramtons price and promotion collection."""

    con = connect()
    run_id = start_run(con)

    try:
        observed_date = date.today().isoformat()

        # -------------------------------------------------------------
        # 1. Existing homepage price collection
        # -------------------------------------------------------------
        html = fetch_page(RAMTONS_URL)
        products = parse_products(html)

        price_created, price_skipped = (
            collect_price_observations(
                con,
                run_id,
                products,
                observed_date,
            )
        )

        # -------------------------------------------------------------
        # 2. Official Sale page promotion collection
        # -------------------------------------------------------------
        sale_html = fetch_page(RAMTONS_SALE_URL)
        sale_products = parse_sale_products(sale_html)

        promotion_created, promotion_skipped = (
            collect_sale_promotions(
                con,
                run_id,
                sale_products,
                observed_date,
            )
        )

        total_created = (
            price_created + promotion_created
        )

        finish_run(
            con,
            run_id,
            status="completed",
            sources_checked=2,
            findings_created=total_created,
        )

        print("Scan completed successfully.")

        print()
        print("Ramtons homepage price collection:")
        print(f"Products found: {len(products)}")
        print(
            f"New price findings created: "
            f"{price_created}"
        )
        print(
            f"Existing price observations skipped: "
            f"{price_skipped}"
        )

        print()
        print("Verified Ramtons Sale collection:")
        print(
            f"Sale products parsed: "
            f"{len(sale_products)}"
        )
        print(
            f"New promotion findings created: "
            f"{promotion_created}"
        )
        print(
            f"Existing promotions skipped: "
            f"{promotion_skipped}"
        )

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

