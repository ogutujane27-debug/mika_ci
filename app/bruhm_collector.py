import time
import sqlite3
import requests
from bs4 import BeautifulSoup

BASE_URL = "https://bruhm.com/shop/"
HEADERS = {"User-Agent": "Mozilla/5.0"}
DB_PATH = "data/mika_competitive_intel.db"

def collect():
    all_cards = []
    page = 1

    while True:
        url = BASE_URL if page == 1 else f"{BASE_URL}page/{page}/"
        r = requests.get(url, headers=HEADERS)
        if r.status_code != 200:
            break

        soup = BeautifulSoup(r.text, "html.parser")
        cards = soup.select(".c-product-grid__item")
        if not cards:
            break

        all_cards.extend(cards)
        page += 1
        time.sleep(1)

    return all_cards

def parse_card(card):
    name_el = card.select_one(".woocommerce-loop-product__title")
    sku_el = card.select_one(".sku")
    link_el = card.select_one("a.woocommerce-loop-product__link")
    classes = card.get("class", [])
    categories = [c.replace("product_cat-", "") for c in classes if c.startswith("product_cat-")]

    return {
        "name": name_el.get_text(strip=True) if name_el else None,
        "sku": sku_el.get_text(strip=True) if sku_el else None,
        "categories": categories,
        "url": link_el.get("href") if link_el else None,
    }

def upsert_product(con, product):
    existing = con.execute(
        "SELECT 1 FROM bruhm_products WHERE sku = ?",
        (product["sku"],),
    ).fetchone()

    if existing:
        con.execute(
            "UPDATE bruhm_products SET last_seen_date = DATE('now') WHERE sku = ?",
            (product["sku"],),
        )
        return "updated"
    else:
        con.execute(
            """
            INSERT INTO bruhm_products
                (competitor, sku, product_name, category, product_url, first_seen_date, last_seen_date)
            VALUES
                (?, ?, ?, ?, ?, DATE('now'), DATE('now'))
            """,
            (
                "Bruhm",
                product["sku"],
                product["name"],
                ",".join(product["categories"]),
                product["url"],
            ),
        )
        return "new"


if __name__ == "__main__":
    cards = collect()
    print(f"Total cards collected: {len(cards)}")

    products = [parse_card(c) for c in cards]
    missing_sku = [p for p in products if not p["sku"]]
    missing_name = [p for p in products if not p["name"]]

    print(f"Products with missing SKU: {len(missing_sku)}")
    print(f"Products with missing name: {len(missing_name)}")

    con = sqlite3.connect(DB_PATH)
    new_count = 0
    updated_count = 0

    for product in products:
        if not product["sku"]:
            continue
        result = upsert_product(con, product)
        if result == "new":
            new_count += 1
        else:
            updated_count += 1

    con.commit()
    print(f"New products: {new_count}")
    print(f"Updated (already seen): {updated_count}")