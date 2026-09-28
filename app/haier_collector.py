import json
import re
import sqlite3
from datetime import date
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup


# ============================================================
# HAIER COMPETITIVE INTELLIGENCE COLLECTOR
# ============================================================

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
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/153.0.0.0 Safari/537.36"
}


# ============================================================
# DATABASE
# ============================================================

def get_connection():
    return sqlite3.connect(DB_PATH)


# ============================================================
# HAIER PAGE REQUEST
# ============================================================

def fetch_category(category):
    url = f"{BASE_URL}/product-category/{category}/"

    response = requests.get(
        url,
        headers=HEADERS,
        timeout=30,
    )

    response.raise_for_status()

    return response.text


# ============================================================
# SKU EXTRACTION
# ============================================================

def extract_sku(card):
    """
    Extract SKU from Haier's embedded pmwDataLayer JSON.

    Example:

    window.pmwDataLayer.products[10626] =
        {"id":"10626","sku":"HAFRI000015-1-1-1", ...};
    """

    html = str(card)

    pattern = (
        r"window\.pmwDataLayer\.products\[\d+\]"
        r"\s*=\s*(\{.*?\});"
    )

    matches = re.findall(pattern, html, re.DOTALL)

    for raw_json in matches:
        try:
            data = json.loads(raw_json)
        except json.JSONDecodeError:
            continue

        sku = data.get("sku")

        if sku:
            sku = str(sku).strip()

            if sku:
                return sku

    # Fallback: WooCommerce data-product_sku
    sku_element = card.select_one("[data-product_sku]")

    if sku_element:
        sku = sku_element.get("data-product_sku")

        if sku:
            sku = str(sku).strip()

            if sku:
                return sku

    return None


# ============================================================
# PRODUCT EXTRACTION
# ============================================================

def extract_products(html, category):
    soup = BeautifulSoup(html, "html.parser")

    cards = soup.select("li.product")

    products = []

    for card in cards:

        # ----------------------------------------------------
        # Product name
        # ----------------------------------------------------

        name_element = card.select_one(
            "h2.woocommerce-loop-product__title"
        )

        if not name_element:
            continue

        product_name = name_element.get_text(
            " ",
            strip=True,
        )

        if not product_name:
            continue

        # ----------------------------------------------------
        # Product URL
        # ----------------------------------------------------

        link_element = card.select_one(
            "a.woocommerce-LoopProduct-link"
        )

        if not link_element:
            link_element = card.select_one(
                "a.woocommerce-loop-product__link"
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

        # ----------------------------------------------------
        # SKU
        # ----------------------------------------------------

        sku = extract_sku(card)

        # ----------------------------------------------------
        # Store raw category slug for now.
        # Multiple categories will be merged later.
        # ----------------------------------------------------

        products.append(
            {
                "sku": sku,
                "product_name": product_name,
                "category": category,
                "url": product_url,
            }
        )

    return products


# ============================================================
# DEDUPLICATION
# ============================================================

def deduplicate_products(products):
    """
    Deduplicate products across Haier categories.

    Priority:
        1. SKU
        2. Product URL
        3. Product name

    Categories are merged when the same product appears
    in multiple category pages.
    """

    unique = {}

    for product in products:

        sku = product["sku"]
        url = product["url"]
        name = product["product_name"]

        if sku:
            key = f"SKU:{sku}"
        elif url:
            key = f"URL:{url}"
        else:
            key = f"NAME:{name.lower()}"

        if key not in unique:

            unique[key] = {
                "sku": sku,
                "product_name": name,
                "category": product["category"],
                "url": url,
            }

        else:

            existing = unique[key]

            categories = set(
                existing["category"].split(",")
            )

            categories.add(product["category"])

            existing["category"] = ",".join(
                sorted(categories)
            )

            # If the first occurrence had no SKU and a
            # later occurrence does, preserve the SKU.
            if not existing["sku"] and sku:
                existing["sku"] = sku

    return list(unique.values())


# ============================================================
# DATABASE UPSERT
# ============================================================

def save_products(products):
    today = date.today().isoformat()

    connection = get_connection()
    cursor = connection.cursor()

    new_products = 0
    updated_products = 0

    for product in products:

        sku = product["sku"]
        product_name = product["product_name"]
        category = product["category"]
        url = product["url"]

        existing = None

        # ----------------------------------------------------
        # First try SKU
        # ----------------------------------------------------

        if sku:
            existing = cursor.execute(
                """
                SELECT id
                FROM haier_products
                WHERE sku = ?
                """,
                (sku,),
            ).fetchone()

        # ----------------------------------------------------
        # If no SKU, use URL
        # ----------------------------------------------------

        if existing is None and url:
            existing = cursor.execute(
                """
                SELECT id
                FROM haier_products
                WHERE url = ?
                """,
                (url,),
            ).fetchone()

        # ----------------------------------------------------
        # Update existing
        # ----------------------------------------------------

        if existing:

            cursor.execute(
                """
                UPDATE haier_products
                SET
                    sku = COALESCE(?, sku),
                    product_name = ?,
                    category = ?,
                    url = ?,
                    last_seen_date = ?
                WHERE id = ?
                """,
                (
                    sku,
                    product_name,
                    category,
                    url,
                    today,
                    existing[0],
                ),
            )

            updated_products += 1

        # ----------------------------------------------------
        # Insert new
        # ----------------------------------------------------

        else:

            cursor.execute(
                """
                INSERT INTO haier_products
                (
                    sku,
                    product_name,
                    category,
                    url,
                    first_seen_date,
                    last_seen_date
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    sku,
                    product_name,
                    category,
                    url,
                    today,
                    today,
                ),
            )

            new_products += 1

    connection.commit()
    connection.close()

    return new_products, updated_products


# ============================================================
# MAIN COLLECTOR
# ============================================================

def main():

    print("=" * 60)
    print("HAIER COMPETITIVE INTELLIGENCE COLLECTOR")
    print("=" * 60)
    print()

    all_products = []

    category_results = []

    # --------------------------------------------------------
    # Crawl categories
    # --------------------------------------------------------

    for category in CATEGORIES:

        print(f"[SCAN] {category}")

        try:

            html = fetch_category(category)

            products = extract_products(
                html,
                category,
            )

            category_results.append(
                (category, len(products))
            )

            all_products.extend(products)

            print(
                f"       Products found: {len(products)}"
            )

        except requests.RequestException as error:

            print(
                f"       ERROR: {error}"
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

    # --------------------------------------------------------
    # Deduplicate
    # --------------------------------------------------------

    unique_products = deduplicate_products(
        all_products
    )

    print(
        f"Unique Haier products: {len(unique_products)}"
    )

    sku_count = sum(
        1
        for product in unique_products
        if product["sku"]
    )

    no_sku_count = len(unique_products) - sku_count

    print(
        f"Products with SKU: {sku_count}"
    )

    print(
        f"Products without SKU: {no_sku_count}"
    )

    # --------------------------------------------------------
    # Save
    # --------------------------------------------------------

    new_products, updated_products = save_products(
        unique_products
    )

    print()
    print("-" * 60)

    print(
        f"New products: {new_products}"
    )

    print(
        f"Updated products: {updated_products}"
    )

    print()
    print("=" * 60)
    print("HAIER COLLECTION COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()

