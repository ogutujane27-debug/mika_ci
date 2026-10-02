"""
MIKA CI - PRICE POSITIONING PREVIEW

Purpose
-------
Build a READ-ONLY price evidence preview for the 18 defensible
MIKA-vs-competitor product comparisons.

IMPORTANT
---------
- SQLite writes: NONE
- Existing comparison logic is NOT modified.
- Price evidence is never invented.
- Official manufacturer evidence is kept separate from retailer evidence.
- Suspicious numeric values are rejected.
- Multiple/conflicting prices are flagged for manual review.
- Exact product/model blocks are preferred over page-wide price scanning.
"""

from __future__ import annotations

import json
import re
import time
from collections import Counter
from datetime import date
from pathlib import Path
from urllib.parse import urlparse

import pandas as pd
import requests
from bs4 import BeautifulSoup


# ============================================================
# PATHS
# ============================================================

ROOT = Path(__file__).resolve().parents[1]

CATALOGUE_DIR = (
    ROOT
    / "reports"
    / "mika_catalogue_preview"
)

MIKA_CATALOGUE = (
    CATALOGUE_DIR
    / "mika_catalogue_preview.csv"
)

BRUHM_CATALOGUE = (
    CATALOGUE_DIR
    / "bruhm"
    / "bruhm_catalogue_preview.csv"
)

HAIER_CATALOGUE = (
    CATALOGUE_DIR
    / "HAIER"
    / "haier_catalogue_preview.csv"
)

COMPARISON_FILE = (
    CATALOGUE_DIR
    / "mika_position"
    / "model_comparison"
    / "comparable_product_types.csv"
)

OUTPUT_DIR = (
    CATALOGUE_DIR
    / "mika_position"
    / "price_positioning"
)

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

EVIDENCE_FILE = (
    OUTPUT_DIR
    / "price_evidence_preview.csv"
)

POSITIONING_FILE = (
    OUTPUT_DIR
    / "price_positioning_preview.csv"
)

MANUAL_FILE = (
    OUTPUT_DIR
    / "price_manual_review.csv"
)

SUMMARY_FILE = (
    OUTPUT_DIR
    / "price_evidence_summary.txt"
)


# ============================================================
# SETTINGS
# ============================================================

TIMEOUT = 20
REQUEST_DELAY = 1.0

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/154.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-KE,en;q=0.9",
}


# ============================================================
# VALID COMPARISON LEVELS
# ============================================================

VALID_MATCH_LEVELS = {
    "STRONG_COMPARABLE",
    "COMPARABLE",
}


# ============================================================
# SOURCE CLASSIFICATION
# ============================================================

OFFICIAL_DOMAINS = {
    "mikaappliances.com": "MIKA_OFFICIAL",
    "bruhm.com": "BRUHM_OFFICIAL",
    "haier.co.ke": "HAIER_OFFICIAL",
}


def classify_source(url: str, brand: str = "") -> str:
    """
    Classify source using the actual URL domain.

    Brand is retained as an argument for compatibility but is not
    used to manufacture source evidence.
    """
    if not url:
        return "SOURCE_UNAVAILABLE"

    host = (
        urlparse(url)
        .netloc
        .lower()
        .replace("www.", "")
    )

    for domain, source_type in OFFICIAL_DOMAINS.items():
        if host == domain or host.endswith("." + domain):
            return source_type

    return "RETAILER_OR_OTHER"


# ============================================================
# GENERAL HELPERS
# ============================================================

def clean_text(value) -> str:
    if value is None:
        return ""

    text = str(value)
    text = re.sub(r"\s+", " ", text)

    return text.strip()


def normalize_model(value) -> str:
    value = clean_text(value)

    if not value:
        return ""

    return value


def today_iso() -> str:
    return date.today().isoformat()


def safe_float(value):
    try:
        return float(value)
    except Exception:
        return None


# ============================================================
# MODEL EXTRACTION
# ============================================================

def extract_model_from_product_name(product_name: str) -> str:
    """
    Extract an explicitly visible model/reference token from a
    competitor product name.

    This does NOT infer a model.

    Example:
        Haier 25L Built-in Microwave – HBMW25LBG
        -> HBMW25LBG

        Haier 34L Built-in Microwave With Grill HBMW34CB
        -> HBMW34CB
    """

    text = clean_text(product_name)

    if not text:
        return ""

    patterns = [
        # Standard appliance references:
        # HBMW25LBG
        # HBMW34CB
        # MAC12SP21V
        r"\b[A-Z]{2,8}\d{1,4}[A-Z0-9-]{1,12}\b",

        # Hyphenated model/reference:
        # BAS-12IC3W
        # BCS-100M
        r"\b[A-Z]{2,8}-[A-Z0-9]{2,15}\b",
    ]

    upper_text = text.upper()

    for pattern in patterns:
        matches = re.findall(
            pattern,
            upper_text,
        )

        for match in matches:
            model = normalize_model(match)

            if model:
                return model

    return ""


# ============================================================
# PRICE PARSING
# ============================================================

def parse_money(value):
    if value is None:
        return None

    text = str(value)

    text = text.replace(",", "")
    text = text.replace(" ", "")

    match = re.search(
        r"([0-9]+(?:\.[0-9]+)?)",
        text,
    )

    if not match:
        return None

    try:
        number = float(match.group(1))
    except Exception:
        return None

    return number


def valid_price(value: float) -> bool:
    """
    Conservative Kenyan appliance/electronics price bounds.

    This prevents:
        384
        388
        73779
        123456
    etc. from being accepted merely because they are numbers.

    Only explicit currency contexts are accepted upstream.
    """

    try:
        value = float(value)
    except (TypeError, ValueError):
        return False

    return 1000 <= value <= 5_000_000


def unique_prices(values: list[float]) -> list[float]:
    """
    Preserve order while removing duplicates.
    """

    result = []

    for value in values:
        if value is None:
            continue

        try:
            value = float(value)
        except (TypeError, ValueError):
            continue

        if not valid_price(value):
            continue

        if value not in result:
            result.append(value)

    return result


def extract_currency_prices(text: str) -> list[float]:
    """
    Extract explicit Kenyan-currency prices only.

    Accepted:
        KSh 24,800
        Ksh 24,800
        KES 24,800
        24,800 KSh
        24,800 KES

    Generic numbers are deliberately ignored.
    """

    if not text:
        return []

    patterns = [
        r"(?:KSh|Ksh|ksh)\s*:?\s*([\d,\s]+(?:\.\d{1,2})?)",
        r"(?:KES|Kes|kes)\s*:?\s*([\d,\s]+(?:\.\d{1,2})?)",
        r"([\d,\s]+(?:\.\d{1,2})?)\s*(?:KSh|Ksh|ksh)",
        r"([\d,\s]+(?:\.\d{1,2})?)\s*(?:KES|Kes|kes)",
    ]

    values = []

    for pattern in patterns:
        for match in re.findall(
            pattern,
            text,
        ):
            parsed = parse_money(match)

            if (
                parsed is not None
                and valid_price(parsed)
            ):
                values.append(parsed)

    return unique_prices(values)


# ============================================================
# PRICE CLASSIFICATION
# ============================================================

def classify_price_type(text: str) -> str:
    """
    Classify price context.

    Returns:
        promotion
        regular
        unspecified
    """

    text = clean_text(text).lower()

    promotional_terms = [
        "sale",
        "offer",
        "discount",
        "discounted",
        "was",
        "now",
        "save",
        "saving",
        "special price",
        "promo",
        "promotion",
        "reduced",
        "deal",
    ]

    regular_terms = [
        "regular price",
        "normal price",
        "original price",
        "retail price",
    ]

    if any(
        term in text
        for term in promotional_terms
    ):
        return "promotion"

    if any(
        term in text
        for term in regular_terms
    ):
        return "regular"

    return "unspecified"


def price_context(
    text: str,
    price: float,
    radius: int = 220,
) -> str:
    """
    Return bounded text around a specific price.
    """

    if not text:
        return ""

    candidates = [
        f"{int(price):,}",
        f"{price:,.2f}",
        str(int(price)),
        str(price),
    ]

    position = -1
    matched_text = ""

    for candidate in candidates:
        position = text.lower().find(
            candidate.lower()
        )

        if position >= 0:
            matched_text = candidate
            break

    if position < 0:
        return ""

    start = max(
        0,
        position - radius,
    )

    end = min(
        len(text),
        position + len(matched_text) + radius,
    )

    return clean_text(
        text[start:end]
    )


# ============================================================
# STRUCTURED PRODUCT DATA
# ============================================================

def recursive_product_nodes(obj):
    """
    Recursively locate Product/ProductGroup JSON-LD objects.
    """

    if isinstance(obj, dict):

        object_type = obj.get(
            "@type",
            "",
        )

        if isinstance(
            object_type,
            list,
        ):
            types = [
                str(x).lower()
                for x in object_type
            ]
        else:
            types = [
                str(object_type).lower()
            ]

        if (
            "product" in types
            or "productgroup" in types
        ):
            yield obj

        for value in obj.values():
            yield from recursive_product_nodes(value)

    elif isinstance(obj, list):

        for item in obj:
            yield from recursive_product_nodes(item)


def product_name_matches(
    target_name: str,
    product_name: str,
) -> bool:
    """
    Conservative product-name matching.

    Exact name match wins.

    Otherwise meaningful token overlap is required.
    """

    target_name = clean_text(
        target_name
    ).lower()

    product_name = clean_text(
        product_name
    ).lower()

    if not target_name or not product_name:
        return False

    if target_name == product_name:
        return True

    target_tokens = {
        token
        for token in re.findall(
            r"[a-z0-9]+",
            target_name,
        )
        if len(token) >= 3
    }

    product_tokens = {
        token
        for token in re.findall(
            r"[a-z0-9]+",
            product_name,
        )
        if len(token) >= 3
    }

    if not target_tokens or not product_tokens:
        return False

    overlap = (
        target_tokens
        & product_tokens
    )

    if not overlap:
        return False

    # For very short product names, one meaningful token can be enough.
    if len(target_tokens) <= 3:
        return len(overlap) >= 1

    # For longer names require at least 2 meaningful shared tokens.
    return len(overlap) >= 2


def extract_jsonld_prices(
    soup: BeautifulSoup,
    target_name: str = "",
) -> list[float]:
    """
    Extract prices only from matching Product JSON-LD blocks.

    This prevents unrelated Product objects from contaminating
    the target price evidence.
    """

    if soup is None:
        return []

    prices = []

    for script in soup.find_all(
        "script",
        type="application/ld+json",
    ):

        raw = (
            script.string
            or script.get_text()
        )

        if not raw:
            continue

        try:
            data = json.loads(raw)
        except Exception:
            continue

        for product in recursive_product_nodes(data):

            product_name = clean_text(
                product.get(
                    "name",
                    "",
                )
            )

            if target_name:
                if not product_name_matches(
                    target_name,
                    product_name,
                ):
                    continue

            offers = product.get(
                "offers",
                {},
            )

            offer_nodes = []

            if isinstance(
                offers,
                dict,
            ):
                offer_nodes.append(offers)

            elif isinstance(
                offers,
                list,
            ):
                offer_nodes.extend(offers)

            for offer in offer_nodes:

                if not isinstance(
                    offer,
                    dict,
                ):
                    continue

                for key in [
                    "price",
                    "lowPrice",
                    "highPrice",
                ]:

                    value = parse_money(
                        offer.get(key)
                    )

                    if (
                        value is not None
                        and valid_price(value)
                    ):
                        prices.append(value)

    return unique_prices(prices)


# ============================================================
# PRICE META / PRODUCT ATTRIBUTES
# ============================================================

def extract_price_meta(
    soup: BeautifulSoup,
) -> list[float]:

    if soup is None:
        return []

    prices = []

    # Explicit meta price fields.
    for tag in soup.find_all("meta"):

        key = " ".join(
            [
                clean_text(
                    tag.get(
                        "property",
                        "",
                    )
                ),
                clean_text(
                    tag.get(
                        "name",
                        "",
                    )
                ),
                clean_text(
                    tag.get(
                        "itemprop",
                        "",
                    )
                ),
            ]
        ).lower()

        if not any(
            token in key
            for token in [
                "price",
                "lowprice",
                "highprice",
            ]
        ):
            continue

        value = (
            tag.get("content")
            or tag.get("value")
            or ""
        )

        parsed = parse_money(value)

        if (
            parsed is not None
            and valid_price(parsed)
        ):
            prices.append(parsed)

    # Explicit itemprop price fields.
    for tag in soup.find_all(
        attrs={
            "itemprop": re.compile(
                r"price|lowPrice|highPrice",
                re.I,
            )
        }
    ):

        value = (
            tag.get("content")
            or tag.get("value")
            or tag.get_text(
                " ",
                strip=True,
            )
        )

        parsed = parse_money(value)

        if (
            parsed is not None
            and valid_price(parsed)
        ):
            prices.append(parsed)

    return unique_prices(prices)


# ============================================================
# VISIBLE PRICE ELEMENTS
# ============================================================

def extract_visible_price_elements(
    soup_or_node,
) -> list[float]:
    """
    Extract prices from conventional product-price elements.

    Works on either:
        BeautifulSoup
        or
        a BeautifulSoup Tag

    It does not scan arbitrary page numbers.
    """

    if soup_or_node is None:
        return []

    prices = []

    selectors = [
        ".price",
        ".woocommerce-Price-amount",
        ".amount",
        "[itemprop='price']",
        "[data-price]",
        "[data-product-price]",
        "[class*='product-price']",
        "[class*='sale-price']",
        "[class*='regular-price']",
    ]

    seen = set()

    for selector in selectors:

        try:
            elements = soup_or_node.select(
                selector
            )
        except Exception:
            continue

        for element in elements:

            identity = id(element)

            if identity in seen:
                continue

            seen.add(identity)

            text = clean_text(
                element.get_text(
                    " ",
                    strip=True,
                )
            )

            if not text:
                continue

            extracted = extract_currency_prices(
                text
            )

            prices.extend(extracted)

            for attr in [
                "data-price",
                "content",
                "value",
            ]:

                value = element.get(attr)

                if not value:
                    continue

                parsed = parse_money(value)

                if (
                    parsed is not None
                    and valid_price(parsed)
                ):
                    prices.append(parsed)

    return unique_prices(prices)


# ============================================================
# PRODUCT-BLOCK DETECTION
# ============================================================

def node_has_target(
    node,
    target_name: str = "",
    target_model: str = "",
) -> bool:
    """
    Determine whether a DOM node contains the requested product.
    """

    text = clean_text(
        node.get_text(
            " ",
            strip=True,
        )
    )

    if not text:
        return False

    text_upper = text.upper()

    # Exact model is strongest evidence.
    if target_model:

        model = normalize_model(
            target_model
        ).upper()

        if (
            model
            and model in text_upper
        ):
            return True

    # Exact product name.
    if target_name:

        target = clean_text(
            target_name
        ).upper()

        if (
            target
            and target in text_upper
        ):
            return True

        # Conservative token overlap.
        tokens = [
            token
            for token in re.findall(
                r"[A-Z0-9]+",
                target,
            )
            if len(token) >= 3
        ]

        if tokens:

            hits = sum(
                1
                for token in tokens
                if token in text_upper
            )

            required = min(
                4,
                len(tokens),
            )

            if hits >= required:
                return True

    return False


def node_price_values(node) -> list[float]:
    """
    Extract prices only from the supplied DOM node.
    """

    prices = []

    try:
        prices.extend(
            extract_visible_price_elements(
                node
            )
        )
    except Exception:
        pass

    try:
        prices.extend(
            extract_currency_prices(
                clean_text(
                    node.get_text(
                        " ",
                        strip=True,
                    )
                )
            )
        )
    except Exception:
        pass

    return unique_prices(prices)


def classify_node_price(node) -> str:
    """
    Determine whether a DOM price element is regular,
    promotional, or unspecified.
    """

    text = clean_text(
        node.get_text(
            " ",
            strip=True,
        )
    ).lower()

    classes = " ".join(
        node.get(
            "class",
            [],
        )
    ).lower()

    combined = (
        f"{classes} {text}"
    )

    if (
        node.name == "del"
        or "regular-price" in combined
        or "old-price" in combined
        or "was-price" in combined
        or "original-price" in combined
    ):
        return "regular"

    if (
        node.name == "ins"
        or "sale-price" in combined
        or "special-price" in combined
        or "promo-price" in combined
        or "discount" in combined
        or "sale" in combined
    ):
        return "promotion"

    return "unspecified"


def extract_target_product_block(
    soup,
    target_name: str = "",
    target_model: str = "",
):
    """
    Locate the smallest useful DOM block belonging to the
    requested product.

    This is the critical protection against collecting
    neighbouring product prices from category pages.
    """

    if soup is None:
        return None

    target_model = normalize_model(
        target_model
    )

    candidates = []

    # --------------------------------------------------------
    # Find target-bearing elements.
    # --------------------------------------------------------

    for element in soup.find_all(
        [
            "h1",
            "h2",
            "h3",
            "h4",
            "h5",
            "a",
            "span",
            "div",
            "p",
        ]
    ):

        try:

            if not node_has_target(
                element,
                target_name=target_name,
                target_model=target_model,
            ):
                continue

            text = clean_text(
                element.get_text(
                    " ",
                    strip=True,
                )
            )

            if not text:
                continue

            # Avoid treating giant page containers as product nodes.
            if len(text) > 2500:
                continue

            candidates.append(element)

        except Exception:
            continue

    if not candidates:
        return None

    # --------------------------------------------------------
    # Walk upward and identify compact product/card container.
    # --------------------------------------------------------

    best = None
    best_score = None

    for element in candidates:

        current = element

        for _ in range(8):

            if current is None:
                break

            try:
                text = clean_text(
                    current.get_text(
                        " ",
                        strip=True,
                    )
                )
            except Exception:
                break

            if not text:
                current = current.parent
                continue

            if len(text) > 4000:
                current = current.parent
                continue

            prices = node_price_values(
                current
            )

            if not prices:
                current = current.parent
                continue

            score = 0

            # Exact model is strongest.
            if (
                target_model
                and target_model.upper()
                in text.upper()
            ):
                score += 150

            # Exact product name.
            if (
                target_name
                and clean_text(target_name).upper()
                in text.upper()
            ):
                score += 100

            classes = " ".join(
                current.get(
                    "class",
                    [],
                )
            ).lower()

            identifiers = [
                "product",
                "woocommerce",
                "item",
                "card",
                "summary",
                "price",
            ]

            for identifier in identifiers:
                if identifier in classes:
                    score += 10

            # Prefer compact containers.
            score -= min(
                len(text) / 100,
                30,
            )

            # Strong penalty for page-level containers.
            if len(text) > 2000:
                score -= 100

            if (
                best_score is None
                or score > best_score
            ):
                best = current
                best_score = score

            current = current.parent

    return best


# ============================================================
# PRODUCT-BLOCK PRICE EXTRACTION
# ============================================================

def extract_target_product_prices(
    soup,
    target_name: str = "",
    target_model: str = "",
):
    """
    Extract prices from the exact target product block.

    Returns:
        prices
        regular_price
        sale_price
        price_status
        price_type
        evidence_text
    """

    block = extract_target_product_block(
        soup,
        target_name=target_name,
        target_model=target_model,
    )

    if block is None:
        return {
            "prices": [],
            "regular_price": None,
            "sale_price": None,
            "price_status": (
                "PRODUCT_BLOCK_NOT_FOUND"
            ),
            "price_type": "unspecified",
            "evidence_text": "",
        }

    regular_prices = []
    sale_prices = []
    unspecified_prices = []

    # --------------------------------------------------------
    # Explicit price elements.
    # --------------------------------------------------------

    for element in block.find_all(
        [
            "del",
            "ins",
            "span",
            "bdi",
            "div",
            "p",
        ]
    ):

        try:

            values = extract_currency_prices(
                clean_text(
                    element.get_text(
                        " ",
                        strip=True,
                    )
                )
            )

            if not values:
                continue

            kind = classify_node_price(
                element
            )

            if kind == "regular":
                regular_prices.extend(
                    values
                )

            elif kind == "promotion":
                sale_prices.extend(
                    values
                )

            else:
                unspecified_prices.extend(
                    values
                )

        except Exception:
            continue

    regular_prices = unique_prices(
        regular_prices
    )

    sale_prices = unique_prices(
        sale_prices
    )

    unspecified_prices = unique_prices(
        unspecified_prices
    )

    # --------------------------------------------------------
    # Fallback to the exact product block.
    # --------------------------------------------------------

    if (
        not regular_prices
        and not sale_prices
    ):

        block_prices = unique_prices(
            node_price_values(block)
        )

        if len(block_prices) == 1:

            unspecified_prices = (
                block_prices
            )

        elif len(block_prices) > 1:

            unspecified_prices = (
                block_prices
            )

    all_prices = unique_prices(
        regular_prices
        + sale_prices
        + unspecified_prices
    )

    regular_price = (
        regular_prices[0]
        if len(regular_prices) == 1
        else None
    )

    sale_price = (
        sale_prices[0]
        if len(sale_prices) == 1
        else None
    )

    # --------------------------------------------------------
    # Classification.
    # --------------------------------------------------------

    if (
        regular_price is not None
        and sale_price is not None
    ):

        status = (
            "VERIFIED_PRODUCT_BLOCK"
        )
        price_type = "promotion"

    elif sale_price is not None:

        status = (
            "VERIFIED_PRODUCT_BLOCK"
        )
        price_type = "promotion"

    elif regular_price is not None:

        status = (
            "VERIFIED_PRODUCT_BLOCK"
        )
        price_type = "regular"

    elif len(unspecified_prices) == 1:

        status = (
            "VERIFIED_PRODUCT_BLOCK"
        )
        price_type = "unspecified"

    elif len(all_prices) > 1:

        status = (
            "MULTIPLE_PRICE_CANDIDATES"
        )
        price_type = "unspecified"

    else:

        status = (
            "PRICE_NOT_FOUND_PRODUCT_BLOCK"
        )
        price_type = "unspecified"

    evidence_text = clean_text(
        block.get_text(
            " ",
            strip=True,
        )
    )[:1200]

    return {
        "prices": all_prices,
        "regular_price": regular_price,
        "sale_price": sale_price,
        "price_status": status,
        "price_type": price_type,
        "evidence_text": evidence_text,
    }


# ============================================================
# PAGE FETCH
# ============================================================

def fetch_page(url: str):
    if not url:
        return (
            None,
            "SOURCE_UNAVAILABLE",
        )

    try:

        response = requests.get(
            url,
            headers=HEADERS,
            timeout=TIMEOUT,
            allow_redirects=True,
        )

        if response.status_code != 200:
            return (
                None,
                f"HTTP_{response.status_code}",
            )

        soup = BeautifulSoup(
            response.text,
            "html.parser",
        )

        return (
            soup,
            "OK",
        )

    except requests.RequestException as exc:

        return (
            None,
            f"REQUEST_ERROR:{type(exc).__name__}",
        )

    except Exception as exc:

        return (
            None,
            f"PARSE_ERROR:{type(exc).__name__}",
        )


# ============================================================
# PAGE PRICE EVIDENCE
# ============================================================

def collect_page_price_evidence(
    url: str,
    brand: str,
    product_name: str,
    model_no: str = "",
):
    """
    Collect defensible price evidence.

    Priority:

    1. Exact target product block
    2. Matching Product JSON-LD
    3. Matching price metadata

    IMPORTANT:
    Official pages are NOT scanned page-wide for currency values.
    This prevents neighbouring product prices from contaminating
    the target evidence.
    """

    source_type = classify_source(
        url,
        brand,
    )

    soup, source_status = fetch_page(
        url
    )

    result = {
        "source_type": source_type,
        "source_status": source_status,

        "price_kes": "",
        "regular_price_kes": "",
        "sale_price_kes": "",

        "price_candidates": "",

        "price_status": "PRICE_NOT_FOUND",
        "price_type": "",

        "evidence_note": "",
        "evidence_context": "",

        "observed_date": today_iso(),
    }

    if soup is None:

        result["price_status"] = (
            "SOURCE_UNAVAILABLE"
        )

        result["evidence_note"] = (
            source_status
        )

        return result

    # ========================================================
    # 1. EXACT PRODUCT BLOCK
    # ========================================================

    product_block = extract_target_product_prices(
        soup,
        target_name=product_name,
        target_model=model_no,
    )

    block_prices = product_block["prices"]

    if block_prices:

        result["price_candidates"] = ";".join(
            (
                str(int(price))
                if float(price).is_integer()
                else str(price)
            )
            for price in block_prices
        )

        result["price_type"] = (
            product_block["price_type"]
        )

        result["evidence_context"] = (
            product_block["evidence_text"]
        )

        if (
            product_block["regular_price"]
            is not None
        ):

            result["regular_price_kes"] = (
                str(
                    int(
                        product_block[
                            "regular_price"
                        ]
                    )
                )
            )

        if (
            product_block["sale_price"]
            is not None
        ):

            result["sale_price_kes"] = (
                str(
                    int(
                        product_block[
                            "sale_price"
                        ]
                    )
                )
            )

        # ----------------------------------------------------
        # Explicit regular + sale:
        # use sale as the current positioning price,
        # while preserving regular price separately.
        # ----------------------------------------------------

        if (
            product_block["regular_price"]
            is not None
            and product_block["sale_price"]
            is not None
        ):

            price = (
                product_block["sale_price"]
            )

            result["price_kes"] = str(
                int(price)
            )

            if source_type.endswith(
                "_OFFICIAL"
            ):
                result["price_status"] = (
                    "VERIFIED_OFFICIAL_SALE"
                )
            else:
                result["price_status"] = (
                    "VERIFIED_RETAIL_PROMOTIONAL_PRICE"
                )

            result["price_type"] = (
                "promotion"
            )

            result["evidence_note"] = (
                "Exact product block found. "
                "Regular and promotional prices "
                "were both preserved; promotional "
                "price selected as current price."
            )

            return result

        # ----------------------------------------------------
        # Single explicit sale price.
        # ----------------------------------------------------

        if (
            product_block["sale_price"]
            is not None
        ):

            price = (
                product_block["sale_price"]
            )

            result["price_kes"] = str(
                int(price)
            )

            if source_type.endswith(
                "_OFFICIAL"
            ):
                result["price_status"] = (
                    "VERIFIED_OFFICIAL_SALE"
                )
            else:
                result["price_status"] = (
                    "VERIFIED_RETAIL_PROMOTIONAL_PRICE"
                )

            result["price_type"] = (
                "promotion"
            )

            result["evidence_note"] = (
                "Exact product block found with "
                "a defensible promotional price."
            )

            return result

        # ----------------------------------------------------
        # Single explicit regular price.
        # ----------------------------------------------------

        if (
            product_block["regular_price"]
            is not None
        ):

            price = (
                product_block["regular_price"]
            )

            result["price_kes"] = str(
                int(price)
            )

            if source_type.endswith(
                "_OFFICIAL"
            ):
                result["price_status"] = (
                    "VERIFIED_OFFICIAL_PRICE"
                )
            else:
                result["price_status"] = (
                    "VERIFIED_RETAIL_PRICE"
                )

            result["price_type"] = (
                "regular"
            )

            result["evidence_note"] = (
                "Exact product block found with "
                "a defensible regular price."
            )

            return result

        # ----------------------------------------------------
        # One unspecified price in exact product block.
        # ----------------------------------------------------

        if len(block_prices) == 1:

            price = block_prices[0]

            result["price_kes"] = str(
                int(price)
            )

            result["price_type"] = (
                "unspecified"
            )

            if source_type.endswith(
                "_OFFICIAL"
            ):
                result["price_status"] = (
                    "VERIFIED_OFFICIAL_PRICE"
                )
            else:
                result["price_status"] = (
                    "VERIFIED_RETAIL_PRICE"
                )

            result["evidence_note"] = (
                "Exact product block found with "
                "one defensible price candidate."
            )

            return result

        # ----------------------------------------------------
        # Multiple prices in exact product block.
        # ----------------------------------------------------

        if len(block_prices) > 1:

            result["price_status"] = (
                "MULTIPLE_PRICE_CANDIDATES"
            )

            result["price_type"] = (
                "unspecified"
            )

            result["price_kes"] = ""

            result["evidence_note"] = (
                "Exact product block found, but "
                "multiple price candidates could "
                "not be safely classified."
            )

            return result

    # ========================================================
    # 2. MATCHING JSON-LD
    # ========================================================

    structured_prices = unique_prices(
        extract_jsonld_prices(
            soup,
            target_name=product_name,
        )
    )

    if len(structured_prices) == 1:

        price = structured_prices[0]

        result["price_candidates"] = str(
            int(price)
        )

        result["price_kes"] = str(
            int(price)
        )

        result["price_type"] = (
            "unspecified"
        )

        if source_type.endswith(
            "_OFFICIAL"
        ):
            result["price_status"] = (
                "VERIFIED_OFFICIAL_PRICE"
            )
        else:
            result["price_status"] = (
                "VERIFIED_RETAIL_PRICE"
            )

        result["evidence_note"] = (
            "Matching Product JSON-LD supplied "
            "one defensible price."
        )

        return result

    if len(structured_prices) > 1:

        result["price_candidates"] = ";".join(
            str(int(x))
            for x in structured_prices
        )

        result["price_status"] = (
            "MULTIPLE_PRICE_CANDIDATES"
        )

        result["price_type"] = (
            "unspecified"
        )

        result["evidence_note"] = (
            "Matching Product JSON-LD supplied "
            "multiple price candidates."
        )

        return result

    # ========================================================
    # 3. MATCHING PRICE META
    # ========================================================

    meta_prices = unique_prices(
        extract_price_meta(soup)
    )

    if len(meta_prices) == 1:

        price = meta_prices[0]

        result["price_candidates"] = str(
            int(price)
        )

        result["price_kes"] = str(
            int(price)
        )

        result["price_type"] = (
            "unspecified"
        )

        if source_type.endswith(
            "_OFFICIAL"
        ):
            result["price_status"] = (
                "VERIFIED_OFFICIAL_PRICE"
            )
        else:
            result["price_status"] = (
                "VERIFIED_RETAIL_PRICE"
            )

        result["evidence_note"] = (
            "Explicit price metadata supplied "
            "one defensible price."
        )

        return result

    if len(meta_prices) > 1:

        result["price_candidates"] = ";".join(
            str(int(x))
            for x in meta_prices
        )

        result["price_status"] = (
            "MULTIPLE_PRICE_CANDIDATES"
        )

        result["price_type"] = (
            "unspecified"
        )

        result["evidence_note"] = (
            "Explicit price metadata supplied "
            "multiple candidates."
        )

        return result

    # ========================================================
    # 4. NO SAFE PRODUCT-SPECIFIC PRICE
    # ========================================================

    if source_type.endswith(
        "_OFFICIAL"
    ):

        result["price_status"] = (
            "PRICE_NOT_EXPOSED_OFFICIAL_SOURCE"
        )

        result["evidence_note"] = (
            "Official source loaded successfully, "
            "but no defensible product-specific "
            "KSh/KES price was exposed."
        )

    else:

        result["price_status"] = (
            "PRICE_NOT_FOUND"
        )

        result["evidence_note"] = (
            "Source loaded successfully, but no "
            "defensible product-specific KSh/KES "
            "price was extracted."
        )

    return result


# ============================================================
# CATALOGUE LOADING
# ============================================================

def load_catalogue(
    path: Path,
    brand: str,
) -> pd.DataFrame:

    if not path.exists():
        raise FileNotFoundError(
            f"Catalogue not found: {path}"
        )

    df = pd.read_csv(
        path,
        dtype=str,
        keep_default_na=False,
    )

    df["brand_normalized"] = brand

    return df


def find_column(
    df: pd.DataFrame,
    candidates: list[str],
):

    lower_map = {
        str(col).lower(): col
        for col in df.columns
    }

    for candidate in candidates:

        if candidate.lower() in lower_map:
            return lower_map[
                candidate.lower()
            ]

    return None


def catalogue_lookup(
    df: pd.DataFrame,
    model_no: str,
    product_name: str,
):
    """
    Resolve competitor catalogue identity.

    Exact model wins.

    If competitor model is blank but the catalogue product name
    explicitly contains a model/reference, that visible reference
    is recovered.

    No model is invented.
    """

    model_no = clean_text(
        model_no
    )

    product_name = clean_text(
        product_name
    )

    model_col = find_column(
        df,
        [
            "model",
            "model_no",
            "model_number",
            "sku",
            "product_code",
        ],
    )

    name_col = find_column(
        df,
        [
            "product_name",
            "name",
            "title",
            "product",
        ],
    )

    url_col = find_column(
        df,
        [
            "url",
            "product_url",
            "source_url",
            "link",
        ],
    )

    # --------------------------------------------------------
    # Exact model match.
    # --------------------------------------------------------

    if model_col and model_no:

        matches = df[
            df[model_col]
            .astype(str)
            .str.strip()
            .str.lower()
            == model_no.lower()
        ]

        if not matches.empty:

            row = matches.iloc[0]

            resolved_name = clean_text(
                row[name_col]
                if name_col
                else product_name
            )

            resolved_model = model_no

            if not resolved_model:
                resolved_model = (
                    extract_model_from_product_name(
                        resolved_name
                    )
                )

            return {
                "model_no": resolved_model,
                "product_name": resolved_name,
                "source_url": clean_text(
                    row[url_col]
                    if url_col
                    else ""
                ),
            }

    # --------------------------------------------------------
    # Exact product-name match.
    # --------------------------------------------------------

    if name_col and product_name:

        target = product_name.lower()

        matches = df[
            df[name_col]
            .astype(str)
            .str.strip()
            .str.lower()
            == target
        ]

        if not matches.empty:

            row = matches.iloc[0]

            resolved_name = clean_text(
                row[name_col]
            )

            resolved_model = clean_text(
                row[model_col]
                if model_col
                else ""
            )

            if not resolved_model:
                resolved_model = (
                    extract_model_from_product_name(
                        resolved_name
                    )
                )

            return {
                "model_no": resolved_model,
                "product_name": resolved_name,
                "source_url": clean_text(
                    row[url_col]
                    if url_col
                    else ""
                ),
            }

    # --------------------------------------------------------
    # No catalogue row.
    # --------------------------------------------------------

    resolved_model = model_no

    if not resolved_model:
        resolved_model = (
            extract_model_from_product_name(
                product_name
            )
        )

    return {
        "model_no": resolved_model,
        "product_name": product_name,
        "source_url": "",
    }


# ============================================================
# MIKA LOOKUP
# ============================================================

def build_mika_lookup(df):

    lookup = {}

    model_col = find_column(
        df,
        [
            "model",
            "model_no",
            "model_number",
            "sku",
            "product_code",
        ],
    )

    name_col = find_column(
        df,
        [
            "product_name",
            "name",
            "title",
            "product",
        ],
    )

    url_col = find_column(
        df,
        [
            "url",
            "product_url",
            "source_url",
            "link",
        ],
    )

    if not model_col:
        return lookup

    for _, row in df.iterrows():

        model = clean_text(
            row[model_col]
        )

        if not model:
            continue

        lookup[model.upper()] = {
            "model_no": model,
            "product_name": clean_text(
                row[name_col]
                if name_col
                else ""
            ),
            "source_url": clean_text(
                row[url_col]
                if url_col
                else ""
            ),
        }

    return lookup


# ============================================================
# COMPARISON FILE
# ============================================================

def load_defensible_comparisons():

    if not COMPARISON_FILE.exists():
        raise FileNotFoundError(
            f"Comparison file not found: "
            f"{COMPARISON_FILE}"
        )

    df = pd.read_csv(
        COMPARISON_FILE,
        dtype=str,
        keep_default_na=False,
    )

    if "match_status" not in df.columns:
        raise RuntimeError(
            "Comparison file has no match_status column."
        )

    df = df[
        df["match_status"].isin(
            VALID_MATCH_LEVELS
        )
    ].copy()

    return df


# ============================================================
# POSITIONING LOGIC
# ============================================================

USABLE_PRICE_STATUSES = {
    "VERIFIED_OFFICIAL_PRICE",
    "VERIFIED_OFFICIAL_SALE",
    "VERIFIED_RETAIL_PRICE",
    "VERIFIED_RETAIL_PROMOTIONAL_PRICE",
}


def calculate_positioning(
    mika_record,
    competitor_record,
):

    result = {
        "comparison_status": (
            "PRICE_COMPARISON_NOT_AVAILABLE"
        ),

        "mika_price_kes": "",
        "competitor_price_kes": "",

        "price_difference_kes": "",
        "mika_premium_discount_pct": "",

        "comparison_basis": "",
        "positioning_note": "",
    }

    mika_status = (
        mika_record["price_status"]
    )

    competitor_status = (
        competitor_record["price_status"]
    )

    if (
        mika_status
        not in USABLE_PRICE_STATUSES
        or competitor_status
        not in USABLE_PRICE_STATUSES
    ):

        result["positioning_note"] = (
            "Both sides require usable price "
            "evidence before a positioning "
            "calculation can be made."
        )

        return result

    if (
        not mika_record["price_kes"]
        or not competitor_record["price_kes"]
    ):

        result["positioning_note"] = (
            "One or both price values are unresolved."
        )

        return result

    mika_price = safe_float(
        mika_record["price_kes"]
    )

    competitor_price = safe_float(
        competitor_record["price_kes"]
    )

    if (
        mika_price is None
        or competitor_price is None
        or mika_price <= 0
        or competitor_price <= 0
    ):

        result["positioning_note"] = (
            "Invalid price values."
        )

        return result

    # --------------------------------------------------------
    # Promotion alignment.
    # --------------------------------------------------------

    mika_promo = (
        "PROMOTIONAL" in mika_status
        or mika_status
        == "VERIFIED_OFFICIAL_SALE"
    )

    competitor_promo = (
        "PROMOTIONAL" in competitor_status
        or competitor_status
        == "VERIFIED_OFFICIAL_SALE"
    )

    if mika_promo != competitor_promo:

        result["comparison_status"] = (
            "PRICE_COMPARISON_REQUIRES_PROMOTION_ALIGNMENT"
        )

        result["mika_price_kes"] = (
            mika_price
        )

        result["competitor_price_kes"] = (
            competitor_price
        )

        result["positioning_note"] = (
            "Regular and promotional prices must "
            "not be directly compared without an "
            "aligned basis."
        )

        return result

    # --------------------------------------------------------
    # Calculation.
    # --------------------------------------------------------

    difference = (
        mika_price
        - competitor_price
    )

    pct = (
        difference
        / competitor_price
        * 100
    )

    result["comparison_status"] = (
        "PRICE_COMPARISON_AVAILABLE"
    )

    result["mika_price_kes"] = (
        mika_price
    )

    result["competitor_price_kes"] = (
        competitor_price
    )

    result["price_difference_kes"] = (
        round(
            difference,
            2,
        )
    )

    result["mika_premium_discount_pct"] = (
        round(
            pct,
            2,
        )
    )

    result["comparison_basis"] = (
        "ALIGNED_PROMOTION_TYPE"
        if mika_promo and competitor_promo
        else "REGULAR_PRICE"
    )

    result["positioning_note"] = (
        "Price difference calculated only because "
        "both sides have usable evidence with aligned "
        "promotion status."
    )

    return result


# ============================================================
# EVIDENCE ROW BUILDER
# ============================================================

def build_evidence_row(
    comparison_id,
    side,
    brand,
    record,
    evidence,
    match_status,
    match_confidence,
):
    """
    Keep evidence-row construction consistent between
    MIKA and competitor records.
    """

    return {
        "comparison_id": comparison_id,
        "side": side,
        "brand": brand,

        "model_no": record["model_no"],
        "product_name": record["product_name"],
        "source_url": record["source_url"],

        "source_type": evidence[
            "source_type"
        ],

        "source_status": evidence[
            "source_status"
        ],

        "observed_date": evidence[
            "observed_date"
        ],

        "price_kes": evidence[
            "price_kes"
        ],

        "regular_price_kes": evidence[
            "regular_price_kes"
        ],

        "sale_price_kes": evidence[
            "sale_price_kes"
        ],

        "price_candidates": evidence[
            "price_candidates"
        ],

        "price_status": evidence[
            "price_status"
        ],

        "price_type": evidence[
            "price_type"
        ],

        "evidence_note": evidence[
            "evidence_note"
        ],

        "evidence_context": evidence[
            "evidence_context"
        ],

        "match_status": match_status,
        "match_confidence": match_confidence,
    }


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 78)
    print(
        "MIKA CI - PRICE POSITIONING PREVIEW"
    )
    print("=" * 78)
    print()

    print("READ-ONLY MODE")
    print("SQLite writes: DISABLED")
    print()

    # --------------------------------------------------------
    # Load comparisons.
    # --------------------------------------------------------

    comparisons = (
        load_defensible_comparisons()
    )

    print(
        f"Defensible comparisons loaded : "
        f"{len(comparisons)}"
    )
    print()

    # --------------------------------------------------------
    # Load catalogues.
    # --------------------------------------------------------

    mika_df = load_catalogue(
        MIKA_CATALOGUE,
        "MIKA",
    )

    bruhm_df = load_catalogue(
        BRUHM_CATALOGUE,
        "BRUHM",
    )

    haier_df = load_catalogue(
        HAIER_CATALOGUE,
        "HAIER",
    )

    mika_lookup = build_mika_lookup(
        mika_df
    )

    # --------------------------------------------------------
    # Output rows.
    # --------------------------------------------------------

    evidence_rows = []
    positioning_rows = []
    manual_rows = []

    # --------------------------------------------------------
    # Process each defensible comparison.
    # --------------------------------------------------------

    for _, comparison in comparisons.iterrows():

        match_status = clean_text(
            comparison.get(
                "match_status",
                "",
            )
        )

        match_confidence = clean_text(
            comparison.get(
                "match_confidence",
                "",
            )
        )

        mika_model = clean_text(
            comparison.get(
                "mika_model_no",
                comparison.get(
                    "model_no",
                    "",
                ),
            )
        )

        if not mika_model:

            mika_model = clean_text(
                comparison.get(
                    "mika_model",
                    "",
                )
            )

        mika_name = clean_text(
            comparison.get(
                "mika_product_name",
                "",
            )
        )

        competitor_brand = clean_text(
            comparison.get(
                "competitor_brand",
                "",
            )
        ).upper()

        competitor_model = clean_text(
            comparison.get(
                "competitor_model_no",
                "",
            )
        )

        competitor_name = clean_text(
            comparison.get(
                "competitor_product_name",
                "",
            )
        )

        comparison_id = (
            f"{mika_model}__"
            f"{competitor_brand or 'UNKNOWN'}__"
            f"{competitor_model or 'SOURCE_REFERENCE'}"
        )

        print(
            f"[{match_status}/{match_confidence}] "
            f"{mika_model} -> "
            f"{competitor_brand} "
            f"{competitor_model or '(model unresolved)'}"
        )

        # ====================================================
        # MIKA SOURCE
        # ====================================================

        mika_record = mika_lookup.get(
            mika_model.upper(),
            {
                "model_no": mika_model,
                "product_name": mika_name,
                "source_url": "",
            },
        )

        # ====================================================
        # COMPETITOR SOURCE
        # ====================================================

        if competitor_brand == "BRUHM":

            competitor_df = bruhm_df

        elif competitor_brand == "HAIER":

            competitor_df = haier_df

        else:

            competitor_df = pd.DataFrame()

        competitor_record = catalogue_lookup(
            competitor_df,
            competitor_model,
            competitor_name,
        )

        # ----------------------------------------------------
        # If comparison supplied a blank competitor model,
        # catalogue_lookup may recover an explicit model from
        # the product name.
        # ----------------------------------------------------

        if (
            not competitor_record["model_no"]
            and competitor_name
        ):

            competitor_record[
                "model_no"
            ] = extract_model_from_product_name(
                competitor_name
            )

        # ====================================================
        # MIKA PRICE EVIDENCE
        # ====================================================

        mika_evidence = (
            collect_page_price_evidence(
                mika_record["source_url"],
                "MIKA",
                mika_record["product_name"],
                mika_record["model_no"],
            )
        )

        evidence_rows.append(
            build_evidence_row(
                comparison_id,
                "MIKA",
                "MIKA",
                mika_record,
                mika_evidence,
                match_status,
                match_confidence,
            )
        )

        time.sleep(
            REQUEST_DELAY
        )

        # ====================================================
        # COMPETITOR PRICE EVIDENCE
        # ====================================================

        competitor_evidence = (
            collect_page_price_evidence(
                competitor_record["source_url"],
                competitor_brand,
                competitor_record["product_name"],
                competitor_record["model_no"],
            )
        )

        evidence_rows.append(
            build_evidence_row(
                comparison_id,
                "COMPETITOR",
                competitor_brand,
                competitor_record,
                competitor_evidence,
                match_status,
                match_confidence,
            )
        )

        time.sleep(
            REQUEST_DELAY
        )

        # ====================================================
        # POSITIONING
        # ====================================================

        positioning = calculate_positioning(
            mika_evidence,
            competitor_evidence,
        )

        positioning_row = {
            "comparison_id": comparison_id,

            "match_status": match_status,
            "match_confidence": match_confidence,

            "mika_model_no": (
                mika_record["model_no"]
            ),

            "mika_product_name": (
                mika_record["product_name"]
            ),

            "mika_source_url": (
                mika_record["source_url"]
            ),

            "competitor_brand": (
                competitor_brand
            ),

            "competitor_model_no": (
                competitor_record["model_no"]
            ),

            "competitor_product_name": (
                competitor_record["product_name"]
            ),

            "competitor_source_url": (
                competitor_record["source_url"]
            ),

            **positioning,
        }

        positioning_rows.append(
            positioning_row
        )

        # ====================================================
        # MANUAL REVIEW
        # ====================================================

        needs_manual = (
            mika_evidence[
                "price_status"
            ]
            not in USABLE_PRICE_STATUSES
            or competitor_evidence[
                "price_status"
            ]
            not in USABLE_PRICE_STATUSES
            or positioning[
                "comparison_status"
            ]
            != "PRICE_COMPARISON_AVAILABLE"
        )

        if needs_manual:

            manual_rows.extend(
                [
                    {
                        "comparison_id": comparison_id,
                        "side": "MIKA",
                        "brand": "MIKA",

                        "model_no": (
                            mika_record[
                                "model_no"
                            ]
                        ),

                        "product_name": (
                            mika_record[
                                "product_name"
                            ]
                        ),

                        "source_url": (
                            mika_record[
                                "source_url"
                            ]
                        ),

                        "source_type": (
                            mika_evidence[
                                "source_type"
                            ]
                        ),

                        "source_status": (
                            mika_evidence[
                                "source_status"
                            ]
                        ),

                        "price_kes": (
                            mika_evidence[
                                "price_kes"
                            ]
                        ),

                        "regular_price_kes": (
                            mika_evidence[
                                "regular_price_kes"
                            ]
                        ),

                        "sale_price_kes": (
                            mika_evidence[
                                "sale_price_kes"
                            ]
                        ),

                        "price_candidates": (
                            mika_evidence[
                                "price_candidates"
                            ]
                        ),

                        "price_status": (
                            mika_evidence[
                                "price_status"
                            ]
                        ),

                        "price_type": (
                            mika_evidence[
                                "price_type"
                            ]
                        ),

                        "observed_date": (
                            mika_evidence[
                                "observed_date"
                            ]
                        ),

                        "evidence_note": (
                            mika_evidence[
                                "evidence_note"
                            ]
                        ),

                        "evidence_context": (
                            mika_evidence[
                                "evidence_context"
                            ]
                        ),

                        "review_reason": (
                            "MIKA_PRICE_EVIDENCE_REQUIRES_REVIEW"
                        ),
                    },
                    {
                        "comparison_id": comparison_id,
                        "side": "COMPETITOR",
                        "brand": competitor_brand,

                        "model_no": (
                            competitor_record[
                                "model_no"
                            ]
                        ),

                        "product_name": (
                            competitor_record[
                                "product_name"
                            ]
                        ),

                        "source_url": (
                            competitor_record[
                                "source_url"
                            ]
                        ),

                        "source_type": (
                            competitor_evidence[
                                "source_type"
                            ]
                        ),

                        "source_status": (
                            competitor_evidence[
                                "source_status"
                            ]
                        ),

                        "price_kes": (
                            competitor_evidence[
                                "price_kes"
                            ]
                        ),

                        "regular_price_kes": (
                            competitor_evidence[
                                "regular_price_kes"
                            ]
                        ),

                        "sale_price_kes": (
                            competitor_evidence[
                                "sale_price_kes"
                            ]
                        ),

                        "price_candidates": (
                            competitor_evidence[
                                "price_candidates"
                            ]
                        ),

                        "price_status": (
                            competitor_evidence[
                                "price_status"
                            ]
                        ),

                        "price_type": (
                            competitor_evidence[
                                "price_type"
                            ]
                        ),

                        "observed_date": (
                            competitor_evidence[
                                "observed_date"
                            ]
                        ),

                        "evidence_note": (
                            competitor_evidence[
                                "evidence_note"
                            ]
                        ),

                        "evidence_context": (
                            competitor_evidence[
                                "evidence_context"
                            ]
                        ),

                        "review_reason": (
                            "COMPETITOR_PRICE_EVIDENCE_REQUIRES_REVIEW"
                        ),
                    },
                ]
            )

        print()

    # ========================================================
    # WRITE PREVIEWS
    # ========================================================

    evidence_df = pd.DataFrame(
        evidence_rows
    )

    positioning_df = pd.DataFrame(
        positioning_rows
    )

    manual_df = pd.DataFrame(
        manual_rows
    )

    evidence_df.to_csv(
        EVIDENCE_FILE,
        index=False,
        encoding="utf-8-sig",
    )

    positioning_df.to_csv(
        POSITIONING_FILE,
        index=False,
        encoding="utf-8-sig",
    )

    manual_df.to_csv(
        MANUAL_FILE,
        index=False,
        encoding="utf-8-sig",
    )

    # ========================================================
    # SUMMARY
    # ========================================================

    status_counts = Counter(
        evidence_df["price_status"]
    )

    price_type_counts = Counter(
        evidence_df["price_type"]
    )

    positioning_counts = Counter(
        positioning_df[
            "comparison_status"
        ]
    )

    summary_lines = [
        "MIKA CI - PRICE POSITIONING PREVIEW",
        "=" * 60,
        "",
        "MODE: READ-ONLY",
        "SQLITE WRITES: DISABLED",
        "",
        f"Defensible comparisons: {len(comparisons)}",
        f"Evidence records: {len(evidence_df)}",
        "",
        "PRICE STATUS DISTRIBUTION",
        "-" * 40,
    ]

    for status, count in sorted(
        status_counts.items()
    ):

        summary_lines.append(
            f"{status}: {count}"
        )

    summary_lines.extend(
        [
            "",
            "PRICE TYPE DISTRIBUTION",
            "-" * 40,
        ]
    )

    for price_type, count in sorted(
        price_type_counts.items()
    ):

        label = (
            price_type
            or "UNSPECIFIED"
        )

        summary_lines.append(
            f"{label}: {count}"
        )

    summary_lines.extend(
        [
            "",
            "COMPARISON STATUS",
            "-" * 40,
        ]
    )

    for status, count in sorted(
        positioning_counts.items()
    ):

        summary_lines.append(
            f"{status}: {count}"
        )

    summary_lines.extend(
        [
            "",
            "IMPORTANT METHODOLOGY NOTES",
            "-" * 40,

            "1. No SQLite writes were performed.",

            "2. Only STRONG_COMPARABLE and "
            "COMPARABLE records are processed.",

            "3. Generic page numbers are not accepted "
            "as prices.",

            "4. Prices must have explicit KSh/KES "
            "context or trusted product-price evidence.",

            "5. Exact product blocks are preferred over "
            "page-wide currency scanning.",

            "6. Official manufacturer prices are kept "
            "separate from retailer prices.",

            "7. Regular and promotional prices are "
            "preserved separately where the source "
            "identifies both.",

            "8. A promotional price is used as the "
            "current positioning price only when the "
            "source explicitly identifies it.",

            "9. Multiple unresolved prices are not "
            "arbitrarily selected.",

            "10. Regular-vs-promotional prices are not "
            "directly compared without aligned "
            "promotion status.",

            "11. Missing official prices do not imply "
            "that no market price exists.",

            "12. Competitor model numbers are recovered "
            "only when explicitly visible in the "
            "catalogue product name.",

            "",
            "OUTPUT FILES",
            "-" * 40,
            str(EVIDENCE_FILE),
            str(POSITIONING_FILE),
            str(MANUAL_FILE),
            str(SUMMARY_FILE),
        ]
    )

    SUMMARY_FILE.write_text(
        "\n".join(summary_lines),
        encoding="utf-8",
    )

    # ========================================================
    # FINAL CONSOLE OUTPUT
    # ========================================================

    print("=" * 78)
    print("PREVIEW COMPLETE")
    print("=" * 78)
    print()

    print("SQLite writes       : NONE")

    print(
        f"Evidence records    : "
        f"{len(evidence_df)}"
    )

    print(
        f"Positioning records : "
        f"{len(positioning_df)}"
    )

    print(
        f"Manual review       : "
        f"{len(manual_df)}"
    )

    print()

    print("OUTPUT:")
    print(EVIDENCE_FILE)
    print(POSITIONING_FILE)
    print(MANUAL_FILE)
    print(SUMMARY_FILE)


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()