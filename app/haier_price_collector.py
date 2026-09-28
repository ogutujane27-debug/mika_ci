import json
import re
import sqlite3
from datetime import date
from html import unescape
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup


BASE_URL = "https://haier.co.ke"
DB_PATH = "data/mika_competitive_intel.db"

CATEGORIES = [
    "ac-heat-pump",
    "built-in-appliances",
    "chest-freezer",
    "cooker",
    "fridge",
    "fridge-freezer",
    "haier",
    "JTC",
    "kitchen-and-small-appliances",
    "tv-audio",
    "washers-dryers",
]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/153.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


def get_connection():
    return sqlite3.connect(DB_PATH)


def fetch_category(category):
    url = f"{BASE_URL}/product-category/{category}/"

    response = requests.get(
        url,
        headers=HEADERS,
        timeout=30,
    )

    response.raise_for_status()

    return response.text


def clean_text(value):
    if value is None:
        return None

    value = unescape(str(value))
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def parse_price(value):
    """
    Convert values such as:
        KSh 359,995
        359,995
        359995
        Ksh 57,996
    into numeric floats.

    Returns None when no usable numeric price exists.
    """
    if value is None:
        return None

    text = clean_text(value)

    if not text:
        return None

    match = re.search(r"(\d[\d,]*(?:\.\d+)?)", text)

    if not match:
        return None

    number = match.group(1).replace(",", "")

    try:
        return float(number)
    except ValueError:
        return None


def extract_sku(card):
    """
    Extract SKU from Haier's embedded pmwDataLayer JavaScript.
    """

    scripts = card.find_all("script")

    for script in scripts:
        script_text = script.string or script.get_text()

        if not script_text:
            continue

        pattern = (
            r"window\.pmwDataLayer\.products\[\d+\]\s*=\s*"
            r"(\{.*?\})\s*;"
        )

        matches = re.findall(
            pattern,
            script_text,
            flags=re.DOTALL,
        )

        for match in matches:
            try:
                data = json.loads(match)

                sku = data.get("sku")

                if sku:
                    sku = clean_text(sku)

                    if sku:
                        return sku

            except (json.JSONDecodeError, TypeError):
                continue

    for element in card.select("[data-product_sku]"):
        sku = element.get("data-product_sku")

        if sku:
            sku = clean_text(sku)

            if sku:
                return sku

    return None


def extract_price_from_element(element):
    if element is None:
        return None

    price = parse_price(
        element.get_text(" ", strip=True)
    )

    if price is not None:
        return price

    for attribute in [
        "data-price",
        "data-product_price",
        "content",
    ]:
        value = element.get(attribute)

        price = parse_price(value)

        if price is not None:
            return price

    return None


def extract_prices(card):
    """
    Extract regular and sale prices from a WooCommerce product card.

    Handles:

        <del> ... </del>  -> regular/original price
        <ins> ... </ins>  -> sale/current price
    """

    regular_price = None
    sale_price = None

    del_element = card.select_one("del")
    ins_element = card.select_one("ins")

    if del_element:
        regular_price = extract_price_from_element(
            del_element
        )

    if ins_element:
        sale_price = extract_price_from_element(
            ins_element
        )

    if regular_price is None and sale_price is None:
        price_container = card.select_one(
            ".price, "
            ".woocommerce-loop-product__link .price, "
            ".c-product-grid__price-wrap"
        )

        if price_container:
            text = price_container.get_text(
                " ",
                strip=True,
            )

            numbers = re.findall(
                r"\d[\d,]*(?:\.\d+)?",
                text,
            )

            parsed = []

            for number in numbers:
                value = parse_price(number)

                if value is not None:
                    parsed.append(value)

            if len(parsed) >= 2:
                regular_price = parsed[0]
                sale_price = parsed[-1]

            elif len(parsed) == 1:
                sale_price = parsed[0]

    if regular_price is None and sale_price is None:
        single_price = card.select_one(
            ".woocommerce-Price-amount"
        )

        if single_price:
            sale_price = extract_price_from_element(
                single_price
            )

    if regular_price is not None and sale_price is None:
        sale_price = regular_price

    return regular_price, sale_price


def extract_products(html, source_category):
    soup = BeautifulSoup(html, "html.parser")

    products = []

    cards = soup.select("li.product")

    for card in cards:
        name_element = card.select_one(
            "h2.woocommerce-loop-product__title"
        )

        if not name_element:
            continue

        product_name = clean_text(
            name_element.get_text(" ", strip=True)
        )

        if not product_name:
            continue

        link_element = card.select_one(
            "a.woocommerce-LoopProduct-link.woocommerce-loop-product__link"
        )

        if not link_element:
            link_element = card.select_one(
                "a.woocommerce-loop-product__link"
            )

        if not link_element:
            link_element = card.select_one(
                "a[href]"
            )

        if not link_element:
            continue

        product_url = link_element.get("href")

        if not product_url:
            continue

        product_url = urljoin(
            BASE_URL,
            product_url,
        )

        sku = extract_sku(card)

        regular_price, sale_price = extract_prices(card)

        discount_percent = None

        if (
            regular_price is not None
            and sale_price is not None
            and regular_price > 0
            and sale_price < regular_price
        ):
            discount_percent = round(
                ((regular_price - sale_price) / regular_price)
                * 100,
                2,
            )

        is_sale = (
            card.select_one(".onsale") is not None
            and regular_price is not None
            and sale_price is not None
            and sale_price < regular_price
        )

        products.append(
            {
                "sku": sku,
                "product_name": product_name,
                "regular_price": regular_price,
                "sale_price": sale_price,
                "discount_percent": discount_percent,
                "observed_date": date.today().isoformat(),
                "url": product_url,
                "source_category": source_category,
                "is_sale": is_sale,
            }
        )

    return products


def deduplicate_products(products):
    """
    The same Haier product can appear in multiple categories.

    Prefer SKU as the identity key, then URL, then product name.
    """

    unique = {}

    for product in products:
        sku = product.get("sku")
        url = product.get("url")
        name = product.get("product_name")

        if sku:
            key = ("sku", sku)
        elif url:
            key = ("url", url)
        else:
            key = ("name", name)

        if key not in unique:
            unique[key] = product
            continue

        existing = unique[key]

        if (
            existing["sale_price"] is None
            and product["sale_price"] is not None
        ):
            existing["regular_price"] = product[
                "regular_price"
            ]
            existing["sale_price"] = product[
                "sale_price"
            ]
            existing["discount_percent"] = product[
                "discount_percent"
            ]

        if product.get("is_sale"):
            existing["is_sale"] = True

        if not existing.get("sku") and sku:
            existing["sku"] = sku

    return list(unique.values())



def save_price_observations(products):
    connection = get_connection()

    cursor = connection.cursor()

    inserted = 0
    skipped = 0

    for product in products:
        existing = cursor.execute(
            """
            SELECT 1
            FROM haier_price_observations
            WHERE url = ?
              AND observed_date = ?
            LIMIT 1
            """,
            (
                product["url"],
                product["observed_date"],
            ),
        ).fetchone()

        if existing:
            skipped += 1
            continue

        cursor.execute(
            """
            INSERT INTO haier_price_observations (
                sku,
                product_name,
                regular_price,
                sale_price,
                discount_percent,
                observed_date,
                url
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                product["sku"],
                product["product_name"],
                product["regular_price"],
                product["sale_price"],
                product["discount_percent"],
                product["observed_date"],
                product["url"],
            ),
        )

        inserted += 1

    connection.commit()
    connection.close()

    return inserted, skipped


def promotion_exists(connection, brand, product_name, observed_date):
    row = connection.execute(
        """
        SELECT 1
        FROM findings f
        WHERE f.brand = ?
          AND f.finding_type = 'promotion'
          AND f.observed_date = ?
          AND f.summary LIKE ?
        LIMIT 1
        """,
        (
            brand,
            observed_date,
            f"%{product_name}%",
        ),
    ).fetchone()

    return row is not None


def next_finding_id(connection, observed_date):
    prefix = f"CI-{observed_date[:7]}-"

    row = connection.execute(
        """
        SELECT finding_id
        FROM findings
        WHERE finding_id LIKE ?
        ORDER BY finding_id DESC
        LIMIT 1
        """,
        (prefix + "%",),
    ).fetchone()

    if not row:
        number = 1
    else:
        match = re.search(
            r"-(\d+)$",
            row[0],
        )

        number = (
            int(match.group(1)) + 1
            if match
            else 1
        )

    return f"{prefix}{number:05d}"


def collect_promotion_observations(products):
    """
    Collect verified product-level sale observations from
    Haier's official WooCommerce catalogue.

    A promotion is recorded only when:

        - the product has an explicit Sale badge
        - an original price exists
        - a current price exists
        - current price is lower than original price

    This does not infer campaign dates or target segments.
    """

    connection = get_connection()

    inserted = 0
    skipped = 0

    observed_date = date.today().isoformat()

    for product in products:
        if not product.get("is_sale"):
            continue

        regular_price = product.get("regular_price")
        sale_price = product.get("sale_price")

        if (
            regular_price is None
            or sale_price is None
            or sale_price >= regular_price
        ):
            continue

        product_name = product["product_name"]

        if promotion_exists(
            connection,
            "Haier",
            product_name,
            observed_date,
        ):
            skipped += 1
            continue

        finding_id = next_finding_id(
            connection,
            observed_date,
        )

        discount = product.get(
            "discount_percent"
        )

        offer_value = (
            f"KSh {regular_price:,.0f} -> "
            f"KSh {sale_price:,.0f} "
            f"({discount:.2f}% off)"
            if discount is not None
            else
            f"KSh {regular_price:,.0f} -> "
            f"KSh {sale_price:,.0f}"
        )

        summary = (
            f"Haier Sale: {product_name} — "
            f"{offer_value}"
        )

        evidence_text = (
            "Official Haier product listing shows an explicit "
            "'Sale!' badge with original and current prices. "
            f"Product: {product_name}; "
            f"Original price: KSh {regular_price:,.0f}; "
            f"Current price: KSh {sale_price:,.0f}; "
            f"Discount: {discount:.2f}%."
            if discount is not None
            else
            "Official Haier product listing shows an explicit "
            "'Sale!' badge with original and current prices. "
            f"Product: {product_name}; "
            f"Original price: KSh {regular_price:,.0f}; "
            f"Current price: KSh {sale_price:,.0f}."
        )

        connection.execute(
            """
            INSERT INTO findings (
                finding_id,
                scan_week,
                run_id,
                competitor_id,
                brand,
                category,
                finding_type,
                summary,
                source_url,
                source_type,
                published_date,
                observed_date,
                evidence_text,
                verification_status,
                confidence
            )
            VALUES (
                ?,
                ?,
                NULL,
                ?,
                ?,
                ?,
                'promotion',
                ?,
                ?,
                'official website',
                NULL,
                ?,
                ?,
                'verified',
                'high'
            )
            """,
            (
                finding_id,
                observed_date[:4] + "-W" + date.today().strftime("%V"),
                5,
                "Haier",
                "Home appliances/electronics",
                summary,
                product["url"],
                observed_date,
                evidence_text,
            ),
        )

        connection.execute(
            """
            INSERT INTO promotion_observations (
                finding_id,
                promotion_type,
                offer_value,
                start_date,
                end_date,
                target_segment
            )
            VALUES (?, ?, ?, NULL, NULL, NULL)
            """,
            (
                finding_id,
                "sale",
                offer_value,
            ),
        )

        inserted += 1

    connection.commit()
    connection.close()

    return inserted, skipped


def main():
    print("=" * 60)
    print("HAIER PRICE + PROMOTION OBSERVATION COLLECTOR")
    print("=" * 60)

    all_products = []

    for category in CATEGORIES:
        print()
        print(f"[SCAN] {category}")

        try:
            html = fetch_category(category)

            products = extract_products(
                html,
                category,
            )

            print(
                f"       Products found: {len(products)}"
            )

            priced = sum(
                1
                for product in products
                if product["sale_price"] is not None
            )

            print(
                f"       Products with price: {priced}"
            )

            all_products.extend(products)

        except requests.RequestException as error:
            print(
                f"       ERROR: Could not fetch category: {error}"
            )

        except Exception as error:
            print(
                f"       ERROR: {error}"
            )

    print()
    print("-" * 60)

    print(
        f"Total category appearances: {len(all_products)}"
    )

    unique_products = deduplicate_products(
        all_products
    )

    print(
        f"Unique products: {len(unique_products)}"
    )

    priced_products = sum(
        1
        for product in unique_products
        if product["sale_price"] is not None
    )

    unpriced_products = (
        len(unique_products) - priced_products
    )

    sale_products = sum(
        1
        for product in unique_products
        if product.get("is_sale")
    )

    print(
        f"Products with price: {priced_products}"
    )

    print(
        f"Products without price: {unpriced_products}"
    )

    print(
        f"Products with verified Sale evidence: {sale_products}"
    )

    print("-" * 60)

    inserted, skipped = save_price_observations(
        unique_products
    )

    print(
        f"New price observations: {inserted}"
    )

    print(
        f"Already recorded: {skipped}"
    )

    promotion_inserted, promotion_skipped = (
        collect_promotion_observations(
            unique_products
        )
    )

    print()
    print(
        "Haier promotion collection:"
    )

    print(
        f"New promotion findings: {promotion_inserted}"
    )

    print(
        f"Existing promotions skipped: {promotion_skipped}"
    )

    print()
    print("=" * 60)
    print("HAIER PRICE + PROMOTION COLLECTION COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()