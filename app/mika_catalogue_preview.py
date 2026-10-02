"""
MIKA Catalogue Preview Collector
--------------------------------
READ-ONLY ONLY.

Purpose:
    Discover MIKA catalogue products from public category pages and
    individual product pages.

IMPORTANT:
    This script DOES NOT write to SQLite.
    It only produces a preview CSV and prints validation summaries.
"""

from __future__ import annotations

import csv
import re
import sys
import time
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup


BASE_URL = "https://www.mikaappliances.com"

# Known public MIKA category pages.
# We can expand this list after the first preview.
CATEGORY_URLS = [
    "/category/FREEZERS",
    "/category/built-in-ovens",
    "/category/fans",
    "/category/irons",
    "/category/built-in-microwaves",
    "/category/garment-steamer",
    "/category/top-load-auto-washers",
    "/category/2-door-top-mount-freezer%2C-inverter",
]

OUTPUT_DIR = Path("reports") / "mika_catalogue_preview"
OUTPUT_CSV = OUTPUT_DIR / "mika_catalogue_preview.csv"

TIMEOUT = 30
REQUEST_DELAY = 0.5

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/154.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}


@dataclass
class Product:
    source_category: str = ""
    raw_category: str = ""

    product_name: str = ""
    model: str = ""

    regular_price: str = ""
    sale_price: str = ""
    current_price: str = ""

    availability: str = ""

    product_url: str = ""
    image_url: str = ""

    description: str = ""
    features: str = ""
    specifications: str = ""

    category: str = ""
    sub_category: str = ""
    mapping_status: str = ""
    mapping_confidence: str = ""

    source: str = BASE_URL
    observed_at: str = ""


def clean(value: str | None) -> str:
    if not value:
        return ""

    return re.sub(r"\s+", " ", value).strip()


def price_value(value: str) -> str:
    """
    Preserve displayed price as text.
    Example:
        Ksh 99,995 -> 99995
    """
    if not value:
        return ""

    match = re.search(r"[\d,]+", value)

    if not match:
        return clean(value)

    return match.group(0).replace(",", "")


def get_soup(session: requests.Session, url: str) -> BeautifulSoup:
    print(f"FETCH: {url}")

    response = session.get(
        url,
        headers=HEADERS,
        timeout=TIMEOUT,
    )

    response.raise_for_status()

    return BeautifulSoup(response.text, "html.parser")


def category_from_url(url: str) -> str:
    value = url.rstrip("/").split("/")[-1]

    value = value.replace("%2C", ",")
    value = value.replace("-", " ")

    return clean(value).title()


def extract_links(soup: BeautifulSoup, category_url: str) -> list[str]:
    """
    DIAGNOSTIC ONLY.

    We currently know that the MIKA category page returns HTML,
    but product links are not exposed as normal /product/ anchors.

    This function inspects the returned HTML for possible product
    URLs and embedded catalogue data.

    NO DATABASE WRITES.
    """

    found = []

    # ------------------------------------------------------------
    # 1. Normal anchors
    # ------------------------------------------------------------
    for anchor in soup.find_all("a", href=True):
        href = anchor.get("href", "").strip()

        if "/product/" in href.lower():
            full_url = urljoin(BASE_URL, href)

            if full_url not in found:
                found.append(full_url)

    # ------------------------------------------------------------
    # 2. Search the complete HTML source
    # ------------------------------------------------------------
    html = str(soup)

    product_patterns = [
        r'https?://[^"\']+/product/[^"\']+',
        r'["\'](/product/[^"\']+)["\']',
        r'["\'](product/[^"\']+)["\']',
    ]

    for pattern in product_patterns:
        matches = re.findall(
            pattern,
            html,
            flags=re.IGNORECASE,
        )

        for match in matches:
            full_url = urljoin(BASE_URL, match)

            if full_url not in found:
                found.append(full_url)

    # ------------------------------------------------------------
    # 3. Diagnostic information
    # ------------------------------------------------------------
    print()
    print("  DIAGNOSTIC")
    print(f"    HTML length       : {len(html):,}")
    print(f"    Anchor count      : {len(soup.find_all('a'))}")
    print(f"    Script count      : {len(soup.find_all('script'))}")
    print(f"    Product URLs      : {len(found)}")

    # Look for useful catalogue/API indicators.
    indicators = [
        "meteor",
        "ddp",
        "linesman",
        "product",
        "catalog",
        "category",
        "graphql",
        "api/",
        "_next",
        "__data",
        "__initial",
    ]

    lower_html = html.lower()

    print("    Embedded indicators:")

    for indicator in indicators:
        count = lower_html.count(indicator)

        if count:
            print(f"      {indicator}: {count}")

    # ------------------------------------------------------------
    # 4. Save the raw HTML for inspection
    # ------------------------------------------------------------
    diagnostic_dir = OUTPUT_DIR / "diagnostic"
    diagnostic_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    category_name = category_from_url(category_url)

    safe_name = re.sub(
        r"[^a-zA-Z0-9_-]+",
        "_",
        category_name,
    ).strip("_").lower()

    html_path = diagnostic_dir / f"{safe_name}.html"

    html_path.write_text(
        html,
        encoding="utf-8",
    )

    print(f"    Raw HTML saved    : {html_path}")

    return found


def text_from_soup(soup: BeautifulSoup) -> str:
    return clean(soup.get_text(" ", strip=True))


def extract_model(soup: BeautifulSoup, page_text: str) -> str:
    """
    MIKA product pages normally expose a model code such as MCF420W.

    First look for common model-code patterns in visible text.
    """

    # Prefer known MIKA-style model codes.
    patterns = [
        r"\bM[A-Z]{1,5}\d{2,5}[A-Z0-9]{0,8}\b",
        r"\b[A-Z]{2,8}\d{2,5}[A-Z0-9]{0,8}\b",
    ]

    candidates = []

    for pattern in patterns:
        candidates.extend(re.findall(pattern, page_text.upper()))

    # Remove obvious non-model words / false positives.
    excluded = {
        "MIKA",
        "KSH",
        "R600",
        "R600A",
        "HTTP",
        "HTTPS",
    }

    for candidate in candidates:
        if candidate in excluded:
            continue

        if candidate.startswith("M") and any(ch.isdigit() for ch in candidate):
            return candidate

    return ""


def extract_prices(soup: BeautifulSoup, page_text: str) -> tuple[str, str, str]:
    """
    Extract price information conservatively.

    The page often contains:
        Ksh 99,995
        Ksh 83,995

    If two prices are found, the first is treated as regular
    and the second as sale/current.
    """

    prices = []

    # Visible currency strings.
    for match in re.findall(
        r"Ksh\s*[\d,]+",
        page_text,
        flags=re.IGNORECASE,
    ):
        value = price_value(match)

        if value and value not in prices:
            prices.append(value)

    if len(prices) >= 2:
        regular = prices[0]
        sale = prices[1]
        current = sale
        return regular, sale, current

    if len(prices) == 1:
        return prices[0], "", prices[0]

    return "", "", ""


def extract_availability(page_text: str) -> str:
    lower = page_text.lower()

    if "out of stock" in lower:
        return "Out of Stock"

    if "in stock" in lower:
        return "In Stock"

    return ""


def extract_title(soup: BeautifulSoup) -> str:
    # H1 is preferred.
    h1 = soup.find("h1")

    if h1:
        title = clean(h1.get_text(" ", strip=True))

        if title:
            return title

    # Fall back to page title.
    if soup.title:
        return clean(soup.title.get_text(" ", strip=True))

    return ""


def extract_image(soup: BeautifulSoup) -> str:
    # Prefer product images containing media.mikaappliances.com.
    for img in soup.find_all("img", src=True):
        src = img.get("src", "").strip()

        if "media.mikaappliances.com" in src:
            return urljoin(BASE_URL, src)

    # General fallback.
    img = soup.find("img", src=True)

    if img:
        return urljoin(BASE_URL, img.get("src", "").strip())

    return ""


def extract_sections(soup: BeautifulSoup) -> tuple[str, str]:
    """
    Attempt to separate feature/specification text without assuming
    a specific frontend framework.
    """

    text = text_from_soup(soup)

    feature_parts = []
    specification_parts = []

    for heading in soup.find_all(
        ["h2", "h3", "h4", "strong", "b"]
    ):
        heading_text = clean(
            heading.get_text(" ", strip=True)
        ).lower()

        if "special features" in heading_text or "general features" in heading_text:
            parent = heading.parent

            if parent:
                value = clean(parent.get_text(" ", strip=True))

                if value:
                    feature_parts.append(value)

        if "specification" in heading_text:
            parent = heading.parent

            if parent:
                value = clean(parent.get_text(" ", strip=True))

                if value:
                    specification_parts.append(value)

    # If section extraction doesn't work, retain a useful text body.
    if not feature_parts:
        feature_parts = [text[:5000]]

    return (
        " | ".join(dict.fromkeys(feature_parts)),
        " | ".join(dict.fromkeys(specification_parts)),
    )


def normalize_category(raw_category: str, product_name: str) -> tuple[str, str, str, str]:
    """
    Conservative taxonomy mapping.

    IMPORTANT:
        Ambiguous products are REVIEW.
        No forced mapping.
    """

    raw = clean(raw_category).lower()
    name = clean(product_name).lower()

    # Refrigeration
    if any(
        term in raw
        for term in [
            "freezer",
            "refrigerator",
            "fridge",
            "2 door top mount",
            "bottom mount",
            "side by side",
        ]
    ):
        if "chest" in name:
            sub = "Chest Freezer"
        elif "upright" in name:
            sub = "Upright Freezer"
        elif "side by side" in name:
            sub = "Side by Side Refrigerator"
        elif "freezer" in name:
            sub = "Freezer"
        else:
            sub = "Refrigerator"

        return "Refrigeration", sub, "mapped", "high"

    # Cooking
    if any(
        term in raw
        for term in [
            "oven",
            "cooker",
            "cooking",
            "hob",
            "stove",
        ]
    ):
        if "built in oven" in raw:
            sub = "Built-in Oven"
        elif "oven" in name:
            sub = "Oven"
        elif "cooker" in name:
            sub = "Cooker"
        elif "hob" in name:
            sub = "Hob"
        else:
            sub = "Cooking"

        return "Cooking", sub, "mapped", "high"

    # Laundry
    if any(
        term in raw
        for term in [
            "washer",
            "washing",
            "dryer",
            "laundry",
        ]
    ) or any(
        term in name
        for term in [
            "washing machine",
            "washer",
            "dryer",
        ]
    ):
        if "top load" in name or "top load" in raw:
            sub = "Top Load Washing Machine"
        elif "front load" in name or "front load" in raw:
            sub = "Front Load Washing Machine"
        elif "dryer" in name:
            sub = "Dryer"
        else:
            sub = "Laundry"

        return "Laundry", sub, "mapped", "high"

    # Air & Climate
    if any(
        term in raw
        for term in [
            "fan",
            "air conditioner",
            "air conditioner",
            "air conditioning",
        ]
    ):
        if "fan" in name:
            if "stand fan" in name:
                sub = "Stand Fan"
            elif "wall fan" in name:
                sub = "Wall Fan"
            elif "box fan" in name:
                sub = "Box Fan"
            else:
                sub = "Fan"
        else:
            sub = "Air Conditioning"

        return "Air & Climate", sub, "mapped", "high"

    # Home Care & Power
    if any(
        term in raw
        for term in [
            "iron",
            "vacuum",
            "cleaning",
            "garment steamer",
        ]
    ):
        if "iron" in name:
            sub = "Iron"
        elif "steamer" in name:
            sub = "Garment Steamer"
        elif "vacuum" in name:
            sub = "Vacuum Cleaner"
        else:
            sub = "Home Care"

        return "Home Care & Power", sub, "mapped", "high"

    # REVIEW rather than guessing.
    return "REVIEW", "REVIEW", "review", "low"


def parse_product(
    session: requests.Session,
    url: str,
    raw_category: str,
) -> Product | None:

    try:
        soup = get_soup(session, url)
    except Exception as exc:
        print(f"PRODUCT ERROR: {url} -> {exc}")
        return None

    page_text = text_from_soup(soup)

    name = extract_title(soup)
    model = extract_model(soup, page_text)

    regular_price, sale_price, current_price = extract_prices(
        soup,
        page_text,
    )

    availability = extract_availability(page_text)

    image_url = extract_image(soup)

    features, specifications = extract_sections(soup)

    category, sub_category, mapping_status, confidence = normalize_category(
        raw_category,
        name,
    )

    return Product(
        source_category=raw_category,
        raw_category=raw_category,
        product_name=name,
        model=model,
        regular_price=regular_price,
        sale_price=sale_price,
        current_price=current_price,
        availability=availability,
        product_url=url,
        image_url=image_url,
        description="",
        features=features,
        specifications=specifications,
        category=category,
        sub_category=sub_category,
        mapping_status=mapping_status,
        mapping_confidence=confidence,
        source=BASE_URL,
        observed_at=datetime.now(timezone.utc).isoformat(),
    )


def save_csv(products: list[Product]) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    rows = [asdict(product) for product in products]

    if not rows:
        return

    with OUTPUT_CSV.open(
        "w",
        newline="",
        encoding="utf-8-sig",
    ) as handle:

        writer = csv.DictWriter(
            handle,
            fieldnames=list(rows[0].keys()),
        )

        writer.writeheader()
        writer.writerows(rows)


def print_summary(products: list[Product]) -> None:
    print()
    print("=" * 80)
    print("MIKA CATALOGUE READ-ONLY PREVIEW")
    print("=" * 80)

    print(f"Products collected : {len(products)}")

    models = {
        p.model
        for p in products
        if p.model
    }

    print(f"Models identified   : {len(models)}")

    in_stock = sum(
        1 for p in products
        if p.availability.lower() == "in stock"
    )

    out_stock = sum(
        1 for p in products
        if p.availability.lower() == "out of stock"
    )

    review = sum(
        1 for p in products
        if p.mapping_status == "review"
    )

    print(f"In Stock            : {in_stock}")
    print(f"Out of Stock        : {out_stock}")
    print(f"REVIEW mappings     : {review}")

    print()
    print("CATEGORY DISTRIBUTION")

    category_counts = {}

    for product in products:
        category = product.category or "UNKNOWN"

        category_counts[category] = (
            category_counts.get(category, 0) + 1
        )

    for category, count in sorted(
        category_counts.items(),
        key=lambda x: (-x[1], x[0]),
    ):
        print(f"  {category}: {count}")

    print()
    print("SUBCATEGORY DISTRIBUTION")

    subcategory_counts = {}

    for product in products:
        sub = product.sub_category or "UNKNOWN"

        subcategory_counts[sub] = (
            subcategory_counts.get(sub, 0) + 1
        )

    for sub, count in sorted(
        subcategory_counts.items(),
        key=lambda x: (-x[1], x[0]),
    ):
        print(f"  {sub}: {count}")

    print()
    print("REVIEW ROWS")

    for product in products:
        if product.mapping_status == "review":
            print(
                f"  {product.model or '[NO MODEL]'} | "
                f"{product.product_name} | "
                f"{product.raw_category}"
            )

    print()
    print("PREVIEW FILE")
    print(f"  {OUTPUT_CSV}")

    print()
    print("DATABASE WRITES: DISABLED")
    print("=" * 80)


def main() -> int:
    print("=" * 80)
    print("MIKA CI - CATALOGUE DISCOVERY")
    print("READ-ONLY PREVIEW")
    print("=" * 80)
    print()
    print("Database writes: DISABLED")
    print(f"Categories: {len(CATEGORY_URLS)}")
    print()

    session = requests.Session()

    all_products: list[Product] = []

    seen_urls: set[str] = set()

    for category_path in CATEGORY_URLS:

        category_url = urljoin(
            BASE_URL,
            category_path,
        )

        raw_category = category_from_url(category_url)

        try:
            soup = get_soup(
                session,
                category_url,
            )

            links = extract_links(
                soup,
                category_url,
            )

        except Exception as exc:
            print(
                f"CATEGORY ERROR: "
                f"{category_url} -> {exc}"
            )
            continue

        print(
            f"  CATEGORY: {raw_category} | "
            f"products found: {len(links)}"
        )

        for product_url in links:

            if product_url in seen_urls:
                continue

            seen_urls.add(product_url)

            product = parse_product(
                session,
                product_url,
                raw_category,
            )

            if product:
                all_products.append(product)

            time.sleep(REQUEST_DELAY)

    save_csv(all_products)

    print_summary(all_products)

    return 0


if __name__ == "__main__":
    sys.exit(main())