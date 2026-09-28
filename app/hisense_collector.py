"""Collect verified Hisense Kenya prices and promotions into SQLite.

This script:
1. Fetches the official Hisense Kenya brand page.
2. Parses current product prices.
3. Stores new price observations in SQLite.
4. Fetches the official Hisense Kenya Limited Time Offer page.
5. Stores the verified World Cup / DStv promotion as a
   structured promotion observation.
6. Prevents duplicate price and promotion observations.

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


HISENSE_URL = "https://hisensekenyaregion.co.ke/brand/hisense/"
HISENSE_OFFER_URL = "https://hisensekenyaregion.co.ke/offer/"


def fetch_page(url):
    """Fetch an official Hisense Kenya page."""
    response = requests.get(
        url,
        headers={"User-Agent": USER_AGENT},
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()
    return response.text


def extract_model(card):
    """Extract the product SKU/model, or use the stable product ID."""
    add_to_cart = card.select_one("[data-product_sku]")

    if add_to_cart:
        sku = add_to_cart.get("data-product_sku")

        if sku:
            return sku

    product_id = card.get("data-id")
    return product_id


def parse_price(element):
    """Convert a WooCommerce price amount into a float."""
    if not element:
        return None

    text = element.get_text(" ", strip=True)
    text = re.sub(r"[^\d.]", "", text)

    return float(text) if text else None


def parse_products(html):
    """Return structured Hisense product-price observations."""
    soup = BeautifulSoup(html, "html.parser")
    cards = soup.select(".product")

    products = []
    seen_urls = set()

    for card in cards:
        name_link = card.select_one(".wd-entities-title a")
        product_link = card.select_one(".product-image-link")

        current_price_element = card.select_one(
            "ins .woocommerce-Price-amount"
        )

        original_price_element = card.select_one(
            "del .woocommerce-Price-amount"
        )

        fallback_price_element = card.select_one(
            ".price .woocommerce-Price-amount"
        )

        discount = card.select_one(".onsale")

        if not name_link or not product_link:
            continue

        product_url = product_link.get("href")

        if not product_url:
            continue

        if product_url in seen_urls:
            continue

        seen_urls.add(product_url)

        current_price = parse_price(current_price_element)

        if current_price is None:
            current_price = parse_price(
                fallback_price_element
            )

        if current_price is None:
            continue

        original_price = parse_price(
            original_price_element
        )

        products.append(
            {
                "product_id": card.get("data-id"),
                "name": name_link.get_text(
                    " ",
                    strip=True,
                ),
                "model": extract_model(card),
                "url": product_url,
                "price": current_price,
                "original_price": original_price,
                "discount": (
                    discount.get_text(
                        " ",
                        strip=True,
                    )
                    if discount
                    else None
                ),
            }
        )

    return products


def observation_exists(
    con,
    model,
    price_kes,
    observed_date,
):
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


def promotion_exists(
    con,
    observed_date,
    promotion_type,
    offer_value,
    source_url,
):
    """Return True when this exact Hisense promotion already exists."""
    row = con.execute(
        """
        SELECT 1
        FROM findings f
        JOIN promotion_observations p
            ON p.finding_id = f.finding_id
        WHERE f.competitor_id = (
            SELECT competitor_id
            FROM competitors
            WHERE brand_name = ?
            LIMIT 1
        )
          AND f.finding_type = 'promotion'
          AND f.observed_date = ?
          AND f.source_url = ?
          AND p.promotion_type = ?
          AND p.offer_value = ?
        LIMIT 1
        """,
        (
            "Hisense",
            observed_date,
            source_url,
            promotion_type,
            offer_value,
        ),
    ).fetchone()

    return row is not None
    """Return True when today's Hisense promotion already exists."""
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
            "Hisense",
            observed_date,
            offer_value,
        ),
    ).fetchone()

    return row is not None


def collect_price_observations(
    con,
    run_id,
):
    """Collect normal Hisense product prices."""
    html = fetch_page(HISENSE_URL)
    products = parse_products(html)

    created = 0
    skipped = 0
    observed_date = date.today().isoformat()

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

        if (
            product["original_price"]
            and product["original_price"] != price_kes
        ):
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
            f"Model: {model}; "
            f"Product ID: {product['product_id']}; "
            f"Current price: "
            f"KSh {price_kes:,.0f}"
        )

        if product["original_price"]:
            evidence += (
                "; Current-page displayed "
                "previous/list price: "
                f"KSh "
                f"{product['original_price']:,.0f}"
            )

        if product["discount"]:
            evidence += (
                "; Displayed discount: "
                f"{product['discount']}"
            )

        add_price_finding(
            con=con,
            run_id=run_id,
            competitor_brand="Hisense",
            brand="Hisense",
            category="Home appliances",
            product_name=product["name"],
            model=model,
            price_kes=price_kes,
            source_url=product["url"],
            evidence_text=evidence,
            promotion_note=promotion_note,
        )

        created += 1

    return {
        "products": products,
        "created": created,
        "skipped": skipped,
    }


def collect_promotion(
    con,
    run_id,
):
    """Collect the verified official Hisense DStv promotion."""
    html = fetch_page(HISENSE_OFFER_URL)

    soup = BeautifulSoup(
        html,
        "html.parser",
    )

    page_text = soup.get_text(
        " ",
        strip=True,
    )

    campaign_title = "Hisense World Cup Offer"

    offer_text = (
        "Buy any Hisense 43\" and above TV "
        "and enjoy 1 month of DStv Stream "
        "at no cost."
    )

    offer_value = (
        "1 month DStv Stream at no cost"
    )

    target_segment = (
        "Buyers of Hisense 43-inch-and-above TVs"
    )

    evidence = (
        f"Official promotion page title: "
        f"{campaign_title}; "
        f"Eligibility: {offer_text}"
    )

    if campaign_title.lower() not in page_text.lower():
        raise ValueError(
            "Hisense promotion title was not found "
            "on the official offer page."
        )

    if "1 month" not in page_text.lower():
        raise ValueError(
            "Hisense DStv offer wording was not found "
            "on the official offer page."
        )

    if "43" not in page_text:
        raise ValueError(
            "Hisense 43-inch eligibility was not found "
            "on the official offer page."
        )

    observed_date = date.today().isoformat()

    if promotion_exists(
        con,
        observed_date,
        "bundled benefit",
        offer_value,
        HISENSE_OFFER_URL,
):
        return {
            "created": 0,
            "skipped": 1,
        }

    finding_id = add_promotion_finding(
        con=con,
        run_id=run_id,
        competitor_brand="Hisense",
        brand="Hisense",
        category="Television",
        promotion_type="bundled benefit",
        offer_value=offer_value,
        summary=(
            "Hisense World Cup Offer: "
            "1 month DStv Stream at no cost "
            "for buyers of Hisense 43-inch-and-above TVs"
        ),
        source_url=HISENSE_OFFER_URL,
        evidence_text=evidence,
        target_segment=target_segment,
        start_date=None,
        end_date=None,
        source_type="official website",
        verification_status="verified",
        confidence="high",
        published_date=None,
    )

    return {
        "created": 1,
        "skipped": 0,
        "finding_id": finding_id,
    }


def main():
    """Run Hisense Kenya price and promotion collection."""
    con = connect()
    run_id = start_run(con)

    try:
        price_result = collect_price_observations(
            con,
            run_id,
        )

        promotion_result = collect_promotion(
            con,
            run_id,
        )

        total_created = (
            price_result["created"]
            + promotion_result["created"]
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
        print("Hisense homepage price collection:")
        print(
            f"Products found: "
            f"{len(price_result['products'])}"
        )
        print(
            f"New price findings created: "
            f"{price_result['created']}"
        )
        print(
            f"Existing price observations skipped: "
            f"{price_result['skipped']}"
        )
        print()
        print("Verified Hisense promotion collection:")
        print(
            f"New promotion findings created: "
            f"{promotion_result['created']}"
        )
        print(
            f"Existing promotions skipped: "
            f"{promotion_result['skipped']}"
        )
        print(
            f"Promotion source: "
            f"{HISENSE_OFFER_URL}"
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