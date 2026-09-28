import re
import sqlite3
from datetime import date
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from config import DB_PATH


BASE_URL = "https://k-elec.co.ke"
PRODUCTS_URL = f"{BASE_URL}/products"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/153.0 Safari/537.36"
    )
}


def get_connection():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    return con


def ensure_table(con):
    con.execute("""
        CREATE TABLE IF NOT EXISTS k_elec_products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_key TEXT UNIQUE,
            product_name TEXT NOT NULL,
            model TEXT,
            category TEXT,
            url TEXT NOT NULL,
            first_seen_date TEXT NOT NULL,
            last_seen_date TEXT NOT NULL,
            price_status TEXT NOT NULL DEFAULT 'not_published'
        )
    """)
    con.commit()


def clean_text(value):
    if not value:
        return None

    value = re.sub(r"\s+", " ", value).strip()
    value = value.strip("* ").strip()

    return value or None


def extract_model(product_name):
    """
    Extract an identifiable model from the product name.

    If no reliable model is visible, return None.
    Never invent a model for a product.
    """

    if not product_name:
        return None

    text = product_name.upper()

    patterns = [
        r"\bKC\d+(?:-[A-Z0-9]+){0,3}\b",
        r"\b\d{2,3}UL\d+[A-Z0-9-]*\b",
        r"\bUL\d+[A-Z0-9-]*\b",
        r"\bQLED\d+[A-Z0-9-]*\b",
    ]

    for pattern in patterns:
        match = re.search(pattern, text)

        if match:
            return match.group(0)

    return None


def infer_category(product_name):
    """
    Conservative category inference from the product title.
    Returns None when the title does not provide enough evidence.
    """

    text = product_name.lower()

    if any(
        word in text
        for word in [
            "tv",
            "television",
            "smart tv",
            "google tv",
        ]
    ):
        return "TVs"

    if any(
        word in text
        for word in [
            "freezer",
            "fridge",
            "refrigerator",
        ]
    ):
        return "Refrigeration"

    if any(
        word in text
        for word in [
            "washing machine",
            "washer",
            "dryer",
        ]
    ):
        return "Laundry"

    if any(
        word in text
        for word in [
            "air conditioner",
            "air conditioner",
            "ac ",
        ]
    ):
        return "Air Conditioning"

    if any(
        word in text
        for word in [
            "cooker",
            "oven",
            "microwave",
            "kettle",
            "blender",
            "air fryer",
            "pressure cooker",
        ]
    ):
        return "Cooking & Small Appliances"

    if "retro series" in text:
        return "Small Appliances"

    return None


def extract_products(html):
    soup = BeautifulSoup(html, "html.parser")

    products = []
    seen_urls = set()

    for h3 in soup.find_all("h3"):
        product_name = clean_text(
            h3.get_text(" ", strip=True)
        )

        if not product_name:
            continue

        # Only collect actual K-Elec products.
        if "k-elec" not in product_name.lower():
            continue

        # Find the enclosing product card.
        card = h3

        for _ in range(5):
            if card.parent is None:
                break

            card = card.parent

            link = card.select_one(
                "a[href*='/products/']"
            )

            if link:
                break
        else:
            link = None

        if not link:
            continue

        href = link.get("href")

        if not href:
            continue

        url = urljoin(BASE_URL, href).rstrip("/")

        if not url.startswith(f"{BASE_URL}/products/"):
            continue

        if url.lower() in seen_urls:
            continue

        seen_urls.add(url.lower())

        model = extract_model(product_name)
        category = infer_category(product_name)

        products.append({
            "product_name": product_name,
            "model": model,
            "category": category,
            "url": url,
        })

    return products


def deduplicate(products):
    result = {}

    for product in products:
        key = product["url"].lower()

        if key not in result:
            result[key] = product

    return list(result.values())


def collect():
    today = date.today().isoformat()

    print("=" * 60)
    print("K-ELEC PRODUCT COLLECTOR")
    print("=" * 60)
    print(f"Source: {PRODUCTS_URL}")
    print(f"Observed: {today}")
    print()

    response = requests.get(
        PRODUCTS_URL,
        headers=HEADERS,
        timeout=30,
    )

    response.raise_for_status()

    products = extract_products(response.text)
    products = deduplicate(products)

    print(f"K-Elec products discovered: {len(products)}")
    print()

    for product in products:
        print(
            f"- {product['product_name']}"
            f" | Model: {product['model'] or 'NULL'}"
            f" | Category: {product['category'] or 'NULL'}"
        )

    con = get_connection()

    try:
        ensure_table(con)

        new_count = 0
        updated_count = 0

        for product in products:
            key = product["url"].lower()

            existing = con.execute(
                """
                SELECT id
                FROM k_elec_products
                WHERE product_key=?
                """,
                (key,),
            ).fetchone()

            if existing:
                con.execute(
                    """
                    UPDATE k_elec_products
                    SET product_name=?,
                        model=?,
                        category=?,
                        url=?,
                        last_seen_date=?,
                        price_status='not_published'
                    WHERE id=?
                    """,
                    (
                        product["product_name"],
                        product["model"],
                        product["category"],
                        product["url"],
                        today,
                        existing["id"],
                    ),
                )

                updated_count += 1

            else:
                con.execute(
                    """
                    INSERT INTO k_elec_products (
                        product_key,
                        product_name,
                        model,
                        category,
                        url,
                        first_seen_date,
                        last_seen_date,
                        price_status
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        key,
                        product["product_name"],
                        product["model"],
                        product["category"],
                        product["url"],
                        today,
                        today,
                        "not_published",
                    ),
                )

                new_count += 1

        con.commit()

        total = con.execute(
            """
            SELECT COUNT(*)
            FROM k_elec_products
            """
        ).fetchone()[0]

        print()
        print("=" * 60)
        print("RESULT")
        print("=" * 60)
        print(f"New products: {new_count}")
        print(f"Updated products: {updated_count}")
        print(f"Total stored K-Elec products: {total}")
        print()
        print("Price status: not published")
        print("Price observations created: 0")

    finally:
        con.close()


if __name__ == "__main__":
    collect()