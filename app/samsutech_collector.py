import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

from config import USER_AGENT, REQUEST_TIMEOUT
from database import connect, start_run, finish_run, add_price_finding


HOME_URL = "https://samsutech.net/"
MOULINEX_URL = "https://samsutech.net/product-category/moulinex/"

TARGET_BRANDS = ("Samsung", "Tefal", "SCL", "Moulinex")


def clean_price(text):
    if not text:
        return None

    value = re.sub(r"[^\d.]", "", text)

    if not value:
        return None

    return float(value)


def extract_brand(name):
    upper = name.upper()

    if "SAMSUNG" in upper:
        return "Samsung"

    if "TEFAL" in upper or "CLIPSOMINUT" in upper or "SUPER COOK" in upper:
        return "Tefal"

    if re.search(r"\bSCL\b", upper):
        return "SCL"

    if "MOULINEX" in upper:
        return "Moulinex"

    return None


def extract_model(name, product_id):
    """
    Extract the product model from a Samsutech product title.

    Moulinex titles consistently place the model after a colon,
    e.g.:
        MOULINEX 350W JUICE EXTRACTOR : JU370127

    For Moulinex, prefer that explicit model portion before using
    the existing pattern-based fallbacks.
    """
    upper = name.upper().strip()

    if "MOULINEX" in upper:
        # The Moulinex catalogue places the model after ":".
        if ":" in upper:
            model_part = upper.rsplit(":", 1)[1].strip()

            # Keep only the first token after the colon.
            model_match = re.match(
                r"^(LM|JU|FP|AM|SW|AF|HM|MK|AR|DD|LT|SM|AT|QA)[A-Z0-9-]+$",
                model_part,
            )

            if model_match:
                return model_match.group(0)

        # Fallback for Moulinex if the title format changes.
        match = re.search(
            r"\b(?:LM|JU|FP|AM|SW|AF|HM|MK|AR|DD|LT|SM|AT|QA)"
            r"[A-Z0-9-]+\b",
            upper,
        )

        if match:
            return match.group(0)

    # Existing generic extraction for Samsung, Tefal and SCL.
    match = re.search(
        r"\b(?=[A-Z0-9-]*\d)[A-Z]{1,6}[-/]?[A-Z0-9]{2,20}"
        r"(?:[-/][A-Z0-9]{1,20})*\b",
        upper,
    )

    if match:
        return match.group(0)

    return f"ID-{product_id}" if product_id else None


def extract_category(name, brand):
    upper = name.upper()

    if brand == "Moulinex":
        if "HAND BLENDER" in upper:
            return "Hand Blenders"

        if "BLENDER" in upper:
            return "Blenders"

        if "JUICER" in upper or "JUICE EXTRACTOR" in upper:
            return "Juicers"

        if "FOOD PROCESSOR" in upper:
            return "Food Processors"

        if "FRYER" in upper:
            return "Fryers"

        if "SANDWICH MAKER" in upper:
            return "Sandwich Makers"

        if "HAND MIXER" in upper:
            return "Hand Mixers"

        if "KITCHEN MACHINE" in upper:
            return "Kitchen Machines"

        if "RICE COOKER" in upper:
            return "Rice Cookers"

        if "COFFEE" in upper and "GRINDER" in upper:
            return "Coffee & Spice Grinders"

        if "CHOPPER" in upper:
            return "Choppers"

        if "TOASTER" in upper:
            return "Toasters"

        return "Other Moulinex"

    return "Samsutech"


def get_product_cards(session, url):
    response = session.get(
        url,
        headers={"User-Agent": USER_AGENT},
        timeout=REQUEST_TIMEOUT,
    )

    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    return soup.select("li.product")


def collect_moulinex_cards(session):
    """
    Scan the Moulinex catalogue using the site's own pagination.

    Page 1 and page 2 currently exist. A 404 means there are
    no more catalogue pages, so scanning stops normally.

    Products are deduplicated by product URL.
    """
    cards_by_url = {}
    page = 1

    while True:
        if page == 1:
            url = MOULINEX_URL
        else:
            url = urljoin(
                MOULINEX_URL,
                f"page/{page}/",
            )

        response = session.get(
            url,
            headers={"User-Agent": USER_AGENT},
            timeout=REQUEST_TIMEOUT,
        )

        if response.status_code == 404:
            break

        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")
        cards = soup.select("li.product")

        if not cards:
            break

        new_on_page = 0

        for card in cards:
            link_el = card.select_one(
                ".woocommerce-LoopProduct-link, "
                ".woocommerce-loop-product__link"
            )

            if not link_el:
                continue

            product_url = link_el.get("href")

            if not product_url:
                continue

            product_url = urljoin(
                MOULINEX_URL,
                product_url,
            )

            if product_url not in cards_by_url:
                cards_by_url[product_url] = card
                new_on_page += 1

        if new_on_page == 0:
            break

        page += 1

    return list(cards_by_url.values()), page - 1


def process_card(con, run_id, card, fallback_url):
    name_el = card.select_one(".woocommerce-loop-product__title")

    link_el = card.select_one(
        ".woocommerce-LoopProduct-link, "
        ".woocommerce-loop-product__link"
    )

    if not name_el or not link_el:
        return False, "missing product name/link"

    name = name_el.get_text(" ", strip=True)

    brand = extract_brand(name)

    if brand not in TARGET_BRANDS:
        return False, "target brand not detected"

    product_url = link_el.get("href")

    if product_url:
        product_url = urljoin(
            fallback_url,
            product_url,
        )

    id_el = card.select_one("[data-product_id]")
    product_id = id_el.get("data-product_id") if id_el else None

    current_el = card.select_one(
        "ins .woocommerce-Price-amount"
    )

    if not current_el:
        current_el = card.select_one(
            ".price > .woocommerce-Price-amount"
        )

    if not current_el:
        return False, "price not published"

    current_price = clean_price(
        current_el.get_text(" ", strip=True)
    )

    if current_price is None:
        return False, "invalid price"

    old_el = card.select_one(
        "del .woocommerce-Price-amount"
    )

    old_price = (
        clean_price(old_el.get_text(" ", strip=True))
        if old_el
        else None
    )

    model = extract_model(
        name,
        product_id,
    )

    category = extract_category(
        name,
        brand,
    )

    promotion_note = None

    if old_price is not None:
        promotion_note = (
            f"Previous/list price: KSh {old_price:,.2f}"
        )

    evidence = (
        f"Product: {name}; "
        f"Model: {model}; "
        f"Category: {category}; "
        f"Current price: KSh {current_price:,.2f}; "
        f"Product ID: {product_id}"
    )

    if old_price is not None:
        evidence += (
            f"; Old price: KSh {old_price:,.2f}"
        )

    evidence += (
        f"; Product URL: {product_url}"
    )

    existing = con.execute(
        """
        SELECT 1
        FROM price_observations
        WHERE model = ?
          AND price_kes = ?
          AND observed_date = DATE('now')
        LIMIT 1
        """,
        (
            model,
            current_price,
        ),
    ).fetchone()

    if existing:
        return False, "already recorded today"

    add_price_finding(
        con=con,
        run_id=run_id,
        competitor_brand=brand,
        brand=brand,
        category=category,
        product_name=name,
        model=model,
        price_kes=current_price,
        source_url=product_url or fallback_url,
        evidence_text=evidence,
        promotion_note=promotion_note,
        source_type="retailer website",
        verification_status="verified",
        confidence="high",
    )

    return True, "created"


def collect():
    session = requests.Session()

    session.headers.update(
        {
            "User-Agent": USER_AGENT
        }
    )

    con = connect()
    run_id = start_run(con)

    new_findings = 0
    skipped = 0
    cards_seen = 0
    pages_seen = 0

    try:
        # ---------------------------------------------------------
        # 1. Existing Samsutech homepage collection
        # ---------------------------------------------------------
        home_cards = get_product_cards(
            session,
            HOME_URL,
        )

        cards_seen += len(home_cards)

        for card in home_cards:
            created, _reason = process_card(
                con,
                run_id,
                card,
                HOME_URL,
            )

            if created:
                new_findings += 1
            else:
                skipped += 1

        # ---------------------------------------------------------
        # 2. Moulinex catalogue collection
        # ---------------------------------------------------------
        moulinex_cards, pages_seen = collect_moulinex_cards(
            session
        )

        cards_seen += len(moulinex_cards)

        for card in moulinex_cards:
            created, _reason = process_card(
                con,
                run_id,
                card,
                MOULINEX_URL,
            )

            if created:
                new_findings += 1
            else:
                skipped += 1

        finish_run(
            con,
            run_id,
            "completed",
            cards_seen,
            new_findings,
        )

        print("Scan completed successfully.")
        print(
            f"Homepage product cards parsed: {len(home_cards)}"
        )
        print(
            f"Moulinex catalogue products discovered: "
            f"{len(moulinex_cards)}"
        )
        print(
            f"Moulinex pages scanned: {pages_seen}"
        )
        print(
            f"Total product records examined: {cards_seen}"
        )
        print(
            f"New findings created: {new_findings}"
        )
        print(
            f"Existing/unusable products skipped: {skipped}"
        )

    except Exception as exc:
        finish_run(
            con,
            run_id,
            "failed",
            cards_seen,
            new_findings,
            str(exc),
        )
        raise

    finally:
        con.close()


if __name__ == "__main__":
    collect()