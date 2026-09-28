"""Collect verified Opalnet product prices and promotions into SQLite.

This script:
1. Fetches the official Opalnet homepage.
2. Parses LG and Midea product prices.
3. Stores new price observations in SQLite.
4. Captures explicit retailer promotion labels and price reductions
   as structured promotion observations.
5. Prevents duplicate price and promotion observations.

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


OPALNET_URL = "https://www.opalnet.co.ke/"


def fetch_page():
    """Fetch the official Opalnet homepage."""
    response = requests.get(
        OPALNET_URL,
        headers={"User-Agent": USER_AGENT},
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()
    return response.text


def extract_brand(product_name):
    """Extract supported manufacturer brand from product name."""
    upper_name = product_name.upper()

    if re.search(r"\bLG\b", upper_name):
        return "LG"

    if re.search(r"\bMIDEA\b", upper_name):
        return "Midea"

    return None


def extract_model(card):
    """Extract the Opalnet product SKU."""
    sku = card.select_one('[class^="product-sku-"]')

    if sku:
        value = sku.get_text(" ", strip=True)

        if value:
            return value

    return None


def parse_products(html):
    """Return structured LG and Midea product-price observations."""
    soup = BeautifulSoup(html, "html.parser")

    products = []
    seen = set()

    for card in soup.select(".product"):
        name_link = card.select_one(".product-item-link")

        if not name_link:
            continue

        name = name_link.get_text(
            " ",
            strip=True,
        )

        url = name_link.get("href")

        brand = extract_brand(name)

        if brand not in ("LG", "Midea"):
            continue

        model = extract_model(card)

        if not model:
            continue

        final_price_element = card.select_one(
            '[data-price-type="finalPrice"]'
        )

        if not final_price_element:
            continue

        final_price = final_price_element.get(
            "data-price-amount"
        )

        if final_price is None:
            continue

        try:
            current_price = float(final_price)
        except (TypeError, ValueError):
            continue

        old_price_element = card.select_one(
            '[data-price-type="oldPrice"]'
        )

        previous_price = None

        if old_price_element:
            old_price = old_price_element.get(
                "data-price-amount"
            )

            try:
                previous_price = float(old_price)
            except (TypeError, ValueError):
                previous_price = None

        sale_label = card.select_one(".sale-label")
        new_label = card.select_one(".new-label")

        sale_text = (
            sale_label.get_text(
                " ",
                strip=True,
            )
            if sale_label
            else None
        )

        new_text = (
            new_label.get_text(
                " ",
                strip=True,
            )
            if new_label
            else None
        )

        key = (
            model,
            current_price,
        )

        if key in seen:
            continue

        seen.add(key)

        products.append(
            {
                "name": name,
                "url": url,
                "model": model,
                "brand": brand,
                "price": current_price,
                "previous_price": previous_price,
                "sale_label": sale_text,
                "new_label": new_text,
            }
        )

    return products


def observation_exists(
    con,
    model,
    price_kes,
    observed_date,
):
    """Return True when this exact price observation exists."""
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
    brand,
    observed_date,
    model,
    offer_value,
):
    """Return True when this exact retailer promotion exists."""
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
          AND f.brand = ?
          AND f.observed_date = ?
          AND f.evidence_text LIKE ?
          AND p.offer_value = ?
        LIMIT 1
        """,
        (
            "Opalnet",
            brand,
            observed_date,
            f"%Model/SKU: {model}%",
            offer_value,
        ),
    ).fetchone()

    return row is not None


def get_promotion_type(
    sale_label,
    new_label,
):
    """Determine promotion type from explicit retailer labels."""
    combined = " ".join(
        value
        for value in (
            sale_label,
            new_label,
        )
        if value
    ).lower()

    if "black friday" in combined:
        return "Black Friday"

    if "combo" in combined:
        return "combo"

    if sale_label:
        return "sale"

    return None


def collect_price_observations(
    con,
    run_id,
):
    """Collect normal Opalnet LG and Midea prices."""
    html = fetch_page()
    products = parse_products(html)

    created = 0
    skipped_existing = 0

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
            skipped_existing += 1
            continue

        promotion_parts = []

        if (
            product["previous_price"] is not None
            and product["previous_price"] != price_kes
        ):
            promotion_parts.append(
                f"Was KSh "
                f"{product['previous_price']:,.0f}; "
                f"now KSh "
                f"{price_kes:,.0f}"
            )

        if product["sale_label"]:
            promotion_parts.append(
                f"Sale label: "
                f"{product['sale_label']}"
            )

        if product["new_label"]:
            promotion_parts.append(
                f"Campaign label: "
                f"{product['new_label']}"
            )

        promotion_note = (
            "; ".join(promotion_parts)
            if promotion_parts
            else None
        )

        evidence = (
            f"Product: {product['name']}; "
            f"Model/SKU: {model}; "
            f"Current price: "
            f"KSh {price_kes:,.0f}"
        )

        if product["previous_price"] is not None:
            evidence += (
                "; Displayed previous/list price: "
                f"KSh "
                f"{product['previous_price']:,.0f}"
            )

        if product["sale_label"]:
            evidence += (
                "; Sale label: "
                f"{product['sale_label']}"
            )

        if product["new_label"]:
            evidence += (
                "; Campaign label: "
                f"{product['new_label']}"
            )

        add_price_finding(
            con=con,
            run_id=run_id,
            competitor_brand=product["brand"],
            brand=product["brand"],
            category="Home appliances/electronics",
            product_name=product["name"],
            model=model,
            price_kes=price_kes,
            source_url=(
                product["url"]
                or OPALNET_URL
            ),
            evidence_text=evidence,
            promotion_note=promotion_note,
        )

        created += 1

    return {
        "products": products,
        "created": created,
        "skipped": skipped_existing,
    }


def collect_promotion_observations(
    con,
    run_id,
    products,
):
    """Create verified retailer promotion observations."""
    created = 0
    skipped = 0
    ignored = 0

    observed_date = date.today().isoformat()

    for product in products:
        previous_price = product["previous_price"]
        current_price = product["price"]

        promotion_type = get_promotion_type(
            product["sale_label"],
            product["new_label"],
        )

        # A structured promotion requires:
        # 1. An explicit promotion label.
        # 2. A real price reduction.
        if not promotion_type:
            ignored += 1
            continue

        if (
            previous_price is None
            or previous_price <= current_price
        ):
            ignored += 1
            continue

        offer_value = (
            f"KSh {previous_price:,.0f} "
            f"-> KSh {current_price:,.0f}"
        )

        if promotion_exists(
            con,
            product["brand"],
            observed_date,
            product["model"],
            offer_value,
        ):
            skipped += 1
            continue

        label_parts = []

        if product["sale_label"]:
            label_parts.append(
                f"Sale label: "
                f"{product['sale_label']}"
            )

        if product["new_label"]:
            label_parts.append(
                f"Campaign label: "
                f"{product['new_label']}"
            )

        labels = "; ".join(label_parts)

        summary = (
            f"Opalnet {promotion_type}: "
            f"{product['name']} "
            f"reduced from "
            f"KSh {previous_price:,.0f} "
            f"to "
            f"KSh {current_price:,.0f}"
        )

        evidence = (
            f"Retailer: Opalnet; "
            f"Product: {product['name']}; "
            f"Model/SKU: {product['model']}; "
            f"Previous price: "
            f"KSh {previous_price:,.0f}; "
            f"Current price: "
            f"KSh {current_price:,.0f}; "
            f"{labels}"
        )

        add_promotion_finding(
            con=con,
            run_id=run_id,
            competitor_brand=product["brand"],
            brand=product["brand"],
            category="Home appliances/electronics",
            promotion_type=promotion_type,
            offer_value=offer_value,
            summary=summary,
            source_url=OPALNET_URL,
            evidence_text=evidence,
            target_segment=None,
            start_date=None,
            end_date=None,
            source_type="retailer website",
            verification_status="verified",
            confidence="high",
            published_date=None,
        )

        created += 1

    return {
        "created": created,
        "skipped": skipped,
        "ignored": ignored,
    }


def main():
    """Run Opalnet price and promotion collection."""
    con = connect()
    run_id = start_run(con)

    try:
        price_result = collect_price_observations(
            con,
            run_id,
        )

        promotion_result = (
            collect_promotion_observations(
                con,
                run_id,
                price_result["products"],
            )
        )

        total_created = (
            price_result["created"]
            + promotion_result["created"]
        )

        finish_run(
            con,
            run_id,
            status="completed",
            sources_checked=1,
            findings_created=total_created,
        )

        print("Scan completed successfully.")
        print()
        print("Opalnet price collection:")
        print(
            f"Products parsed: "
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
        print("Opalnet promotion collection:")
        print(
            f"New promotion findings created: "
            f"{promotion_result['created']}"
        )
        print(
            f"Existing promotions skipped: "
            f"{promotion_result['skipped']}"
        )
        print(
            f"Products without qualifying "
            f"promotion evidence: "
            f"{promotion_result['ignored']}"
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