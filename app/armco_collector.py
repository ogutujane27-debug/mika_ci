"""Collect Armco price and verified sale observations into SQLite.

This collector handles two official Armco sources:

1. Armco homepage:
       https://armcokenya.com/

   Used for the existing product-price collection.

2. Armco official On Sale page:
       https://armcokenya.com/product-category/on-sale/

   Used for verified product-level sale/promotion observations.

The collector:
- preserves the existing Armco price collection behavior;
- never invents prices;
- prevents duplicate price observations;
- parses the dedicated official On Sale page separately;
- records sale promotions only when both previous and current prices
  are available and the current price is lower;
- does not invent promotion dates or target segments;
- does not modify, rename, or delete source files.
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


ARMCO_URL = "https://armcokenya.com/"

ARMCO_ON_SALE_URL = (
    "https://armcokenya.com/product-category/on-sale/"
)


# =====================================================================
# HTTP
# =====================================================================

def fetch_page():
    """Fetch the main official Armco website."""
    response = requests.get(
        ARMCO_URL,
        headers={"User-Agent": USER_AGENT},
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()
    return response.text


def fetch_on_sale_page():
    """Fetch Armco's official On Sale page."""
    response = requests.get(
        ARMCO_ON_SALE_URL,
        headers={"User-Agent": USER_AGENT},
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()
    return response.text


# =====================================================================
# PRICE / MODEL PARSING
# =====================================================================

def parse_price(element):
    """Extract a numeric KSh price from a BeautifulSoup element."""
    if element is None:
        return None

    text = element.get_text(" ", strip=True)

    if not text:
        return None

    # Remove commas and retain the first numeric price.
    match = re.search(
        r"(?:KSh|KES)?\s*([\d,]+(?:\.\d+)?)",
        text,
        flags=re.IGNORECASE,
    )

    if not match:
        return None

    try:
        return float(match.group(1).replace(",", ""))
    except ValueError:
        return None


def extract_model(card, name):
    """Extract an Armco model number from a product card.

    The existing model extraction strategy is retained here, with
    conservative fallbacks. If no reliable model can be identified,
    the product is skipped rather than inventing one.
    """

    # Existing Armco cards commonly expose the model in the product
    # title/name. Keep the extraction conservative.
    text = " ".join(
        part.strip()
        for part in [
            name or "",
            card.get("data-product_sku", ""),
            card.get("data-product-id", ""),
        ]
        if part
    )

    # WooCommerce product SKU, when available.
    sku = card.get("data-product_sku")
    if sku:
        sku = str(sku).strip()
        if sku:
            return sku

    # Product title/model patterns used by Armco.
    patterns = [
        r"\bREF-[A-Z0-9][A-Z0-9._()/ -]*",
        r"\bGAS-[A-Z0-9][A-Z0-9._()/ -]*",
        r"\bHOM-[A-Z0-9][A-Z0-9._()/ -]*",
        r"\bFAN-[A-Z0-9][A-Z0-9._()/ -]*",
        r"\bARF-[A-Z0-9][A-Z0-9._()/ -]*",
        r"\bAPT-[A-Z0-9][A-Z0-9._()/ -]*",
        r"\bAWM-[A-Z0-9][A-Z0-9._()/ -]*",
        r"\bAHT-[A-Z0-9][A-Z0-9._()/ -]*",
        r"\bASC-[A-Z0-9][A-Z0-9._()/ -]*",
        r"\bABL-[A-Z0-9][A-Z0-9._()/ -]*",
        r"\bDFR-[A-Z0-9][A-Z0-9._()/ -]*",
        r"\bDVB-[A-Z0-9][A-Z0-9._()/ -]*",
        r"\bLED-[A-Z0-9][A-Z0-9._()/ -]*",
        r"\b[A-Z]{2,}[0-9][A-Z0-9._()/ -]*",
        r"\b[0-9]{2,}[A-Z][A-Z0-9._()/ -]*",
    ]

    for pattern in patterns:
        match = re.search(
            pattern,
            text,
            flags=re.IGNORECASE,
        )

        if match:
            model = match.group(0).strip()
            model = re.sub(r"\s+", " ", model)

            # Remove trailing descriptive words that are unlikely
            # to be part of the model.
            model = model.rstrip(" -")

            if model:
                return model

    return None


# =====================================================================
# EXISTING HOMEPAGE PRODUCT PARSER
# =====================================================================

def parse_products(html):
    """Parse products from the main Armco homepage.

    This preserves the existing price collector behavior:
    - current price from <ins>, then .price;
    - previous price from <del>;
    - displayed discount from .custom-sale-badge;
    - out-of-stock detection;
    - duplicate-card prevention.
    """

    soup = BeautifulSoup(html, "html.parser")

    cards = soup.select(".product-small")
    products = []
    seen = set()

    for card in cards:
        name_link = card.select_one(".product-title a")

        if not name_link:
            continue

        name = name_link.get_text(" ", strip=True)
        url = name_link.get("href")

        model = extract_model(card, name)

        current_price = parse_price(
            card.select_one(".price ins")
        )

        if current_price is None:
            current_price = parse_price(
                card.select_one(".price")
            )

        old_price = parse_price(
            card.select_one(".price del")
        )

        badge = card.select_one(".custom-sale-badge")

        discount = (
            badge.get("data-percentage")
            if badge
            else None
        )

        card_text = card.get_text(" ", strip=True)

        out_of_stock = (
            "out of stock" in card_text.lower()
        )

        if not model:
            continue

        # Prevent duplicate cards such as the ASC-700 duplicate.
        key = (model, current_price, url)

        if key in seen:
            continue

        seen.add(key)

        products.append(
            {
                "name": name,
                "url": url,
                "model": model,
                "price": current_price,
                "original_price": old_price,
                "discount": discount,
                "out_of_stock": out_of_stock,
            }
        )

    return products


# =====================================================================
# VERIFIED ON-SALE PAGE PARSER
# =====================================================================

def parse_sale_products(html):
    """Parse unique discounted products from Armco's official On Sale page.

    Only products with:
        - a product name;
        - a model;
        - a product URL;
        - a previous/original price;
        - a current price;
        - current price < previous price

    are returned as promotion candidates.

    The On Sale page contains duplicate product cards, so products are
    deduplicated primarily by product URL.
    """

    soup = BeautifulSoup(html, "html.parser")

    cards = soup.select(".product-small")

    products = []
    seen = set()

    for card in cards:
        name_link = card.select_one(".product-title a")

        if not name_link:
            continue

        name = name_link.get_text(" ", strip=True)
        url = name_link.get("href")

        if not name or not url:
            continue

        model = extract_model(card, name)

        if not model:
            continue

        # Dedicated sale-page markup normally uses <del> for the
        # previous price and <ins> for the current price.
        old_price = parse_price(
            card.select_one(".price del")
        )

        current_price = parse_price(
            card.select_one(".price ins")
        )

        # Conservative fallback when <ins> is absent.
        if current_price is None:
            price_element = card.select_one(".price")

            if price_element:
                ins = price_element.select_one("ins")

                if ins:
                    current_price = parse_price(ins)

        if old_price is None or current_price is None:
            continue

        if current_price >= old_price:
            continue

        key = (
            url,
            model,
            old_price,
            current_price,
        )

        if key in seen:
            continue

        seen.add(key)

        discount_pct = round(
            ((old_price - current_price) / old_price) * 100
        )

        products.append(
            {
                "name": name,
                "url": url,
                "model": model,
                "original_price": old_price,
                "price": current_price,
                "discount_pct": discount_pct,
            }
        )

    return products


# =====================================================================
# PRICE OBSERVATION DUPLICATE CHECK
# =====================================================================

def observation_exists(
    con,
    model,
    price_kes,
    observed_date,
):
    """Return True when the same price was already observed today."""

    row = con.execute(
        """
        SELECT 1
        FROM findings f
        JOIN price_observations p
            ON p.finding_id = f.finding_id
        WHERE f.finding_type = ?
          AND p.model = ?
          AND p.price_kes = ?
          AND f.observed_date = ?
        LIMIT 1
        """,
        (
            "price",
            model,
            price_kes,
            observed_date,
        ),
    ).fetchone()

    return row is not None


# =====================================================================
# PROMOTION OBSERVATION DUPLICATE CHECK
# =====================================================================

def sale_promotion_exists(
    con,
    model,
    original_price,
    current_price,
    observed_date,
):
    """Return True when this exact sale was already recorded today."""

    row = con.execute(
        """
        SELECT 1
        FROM findings f
        JOIN promotion_observations p
            ON p.finding_id = f.finding_id
        WHERE f.finding_type = ?
          AND f.source_url = ?
          AND f.observed_date = ?
          AND p.offer_value = ?
        LIMIT 1
        """,
        (
            "promotion",
            ARMCO_ON_SALE_URL,
            observed_date,
            (
                f"KSh {original_price:,.0f} -> "
                f"KSh {current_price:,.0f}"
            ),
        ),
    ).fetchone()

    return row is not None


# =====================================================================
# VERIFIED ON-SALE COLLECTION
# =====================================================================

def collect_sale_promotions(
    con,
    run_id,
    observed_date,
):
    """Collect verified product-level promotions from Armco On Sale."""

    html = fetch_on_sale_page()

    soup = BeautifulSoup(html, "html.parser")

    page_title = (
        soup.title.get_text(" ", strip=True)
        if soup.title
        else ""
    )

    # The page itself identifies this as Armco's discounted-products
    # source. This is source verification, not an invented campaign.
    if "on sale" not in page_title.lower():
        raise ValueError(
            "Armco On Sale page title could not be verified."
        )

    sale_products = parse_sale_products(html)

    created = 0
    skipped_existing = 0
    skipped_no_discount = 0

    for product in sale_products:
        model = product["model"]
        original_price = product["original_price"]
        current_price = product["price"]
        discount_pct = product["discount_pct"]

        if (
            original_price is None
            or current_price is None
            or current_price >= original_price
        ):
            skipped_no_discount += 1
            continue

        if sale_promotion_exists(
            con,
            model,
            original_price,
            current_price,
            observed_date,
        ):
            skipped_existing += 1
            continue

        offer_value = (
            f"KSh {original_price:,.0f} -> "
            f"KSh {current_price:,.0f}"
        )

        summary = (
            f"Armco sale: {product['name']} "
            f"reduced from KSh {original_price:,.0f} "
            f"to KSh {current_price:,.0f}"
        )

        evidence = (
            f"Official Armco On Sale page; "
            f"Product: {product['name']}; "
            f"Model: {model}; "
            f"Displayed previous/list price: "
            f"KSh {original_price:,.0f}; "
            f"Displayed current price: "
            f"KSh {current_price:,.0f}; "
            f"Calculated reduction: {discount_pct}%"
        )

        add_promotion_finding(
            con=con,
            run_id=run_id,
            competitor_brand="Armco",
            brand="Armco",
            category="Home appliances",
            promotion_type="sale",
            offer_value=offer_value,
            summary=summary,
            source_url=ARMCO_ON_SALE_URL,
            evidence_text=evidence,
            target_segment=None,
            start_date=None,
            end_date=None,
            source_type="official website",
            verification_status="verified",
            confidence="high",
        )

        created += 1

    return {
        "parsed": len(sale_products),
        "created": created,
        "skipped_existing": skipped_existing,
        "skipped_no_discount": skipped_no_discount,
        "page_title": page_title,
    }


# =====================================================================
# MAIN
# =====================================================================

def main():
    con = connect()
    run_id = start_run(con)

    try:
        # =============================================================
        # EXISTING ARMCO PRICE COLLECTION
        # =============================================================

        html = fetch_page()
        products = parse_products(html)

        created = 0
        skipped_existing = 0
        skipped_no_price = 0

        observed_date = date.today().isoformat()

        for product in products:
            model = product["model"]
            price_kes = product["price"]

            # Never invent a price.
            if price_kes is None:
                skipped_no_price += 1
                continue

            if observation_exists(
                con,
                model,
                price_kes,
                observed_date,
            ):
                skipped_existing += 1
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
                discount_text = (
                    f"Displayed discount: "
                    f"{product['discount']}%"
                )

                promotion_note = (
                    f"{promotion_note}; {discount_text}"
                    if promotion_note
                    else discount_text
                )

            if product["out_of_stock"]:
                stock_note = "Out of stock"

                promotion_note = (
                    f"{promotion_note}; {stock_note}"
                    if promotion_note
                    else stock_note
                )

            evidence = (
                f"Product: {product['name']}; "
                f"Model: {model}; "
                f"Current price: "
                f"KSh {price_kes:,.0f}"
            )

            if product["original_price"]:
                evidence += (
                    "; Displayed previous/list price: "
                    f"KSh {product['original_price']:,.0f}"
                )

            if product["discount"]:
                evidence += (
                    "; Displayed discount: "
                    f"{product['discount']}%"
                )

            if product["out_of_stock"]:
                evidence += (
                    "; Availability: Out of stock"
                )

            add_price_finding(
                con=con,
                run_id=run_id,
                competitor_brand="Armco",
                brand="Armco",
                category="Home appliances",
                product_name=product["name"],
                model=model,
                price_kes=price_kes,
                source_url=product["url"] or ARMCO_URL,
                evidence_text=evidence,
                promotion_note=promotion_note,
            )

            created += 1

        # =============================================================
        # VERIFIED ARMCO ON-SALE COLLECTION
        # =============================================================

        sale_result = None
        sale_error = None

        try:
            sale_result = collect_sale_promotions(
                con=con,
                run_id=run_id,
                observed_date=observed_date,
            )
        except requests.RequestException as exc:
            # Do not break the working price collector merely because
            # the separate On Sale source is temporarily unavailable.
            sale_error = (
                f"On Sale source unavailable: {exc}"
            )

        # =============================================================
        # COMPLETE RUN
        # =============================================================

        finish_run(
            con,
            run_id,
            status="completed",
            sources_checked=2 if sale_result else 1,
            findings_created=(
                created
                + (
                    sale_result["created"]
                    if sale_result
                    else 0
                )
            ),
        )

        print("Scan completed successfully.")
        print(f"Products parsed: {len(products)}")
        print(f"New price findings created: {created}")
        print(
            f"Existing price observations skipped: "
            f"{skipped_existing}"
        )
        print(
            f"Products skipped without current price: "
            f"{skipped_no_price}"
        )

        if sale_result:
            print("")
            print("Verified Armco On Sale collection:")
            print(
                f"Sale products parsed: "
                f"{sale_result['parsed']}"
            )
            print(
                f"New promotion findings created: "
                f"{sale_result['created']}"
            )
            print(
                f"Existing promotions skipped: "
                f"{sale_result['skipped_existing']}"
            )
            print(
                f"Sale products skipped without valid "
                f"price reduction: "
                f"{sale_result['skipped_no_discount']}"
            )
            print(
                f"On Sale page title: "
                f"{sale_result['page_title']}"
            )

        if sale_error:
            print("")
            print(f"WARNING: {sale_error}")

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


            
