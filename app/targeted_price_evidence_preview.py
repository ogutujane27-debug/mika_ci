from __future__ import annotations

import csv
import html
import re
import time
from datetime import date
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

import requests
from bs4 import BeautifulSoup


# ============================================================
# MIKA CI
# TARGETED PRICE EVIDENCE PREVIEW
# ============================================================
#
# PURPOSE
# -------
# Targeted price evidence for the 18 validated MIKA
# comparable products.
#
# RULES
# -----
# - Preview only
# - NO SQLite writes
# - Search results are discovery only
# - Actual product pages are evidence
# - Exact model required on retailer pages
# - Known MIKA URLs are references, not assumed price evidence
# - Regular and sale prices remain separate
# - Multiple unresolved prices are never arbitrarily selected
#
# ============================================================


BASE_DIR = Path(__file__).resolve().parents[1]

COMPARISON_FILE = (
    BASE_DIR
    / "reports"
    / "mika_catalogue_preview"
    / "mika_position"
    / "model_comparison"
    / "comparable_product_types.csv"
)

OUTPUT_DIR = (
    BASE_DIR
    / "reports"
    / "mika_catalogue_preview"
    / "mika_position"
    / "price_positioning"
)

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

PRICE_EVIDENCE_FILE = OUTPUT_DIR / "price_evidence_preview.csv"
POSITIONING_FILE = OUTPUT_DIR / "price_positioning_preview.csv"
MANUAL_REVIEW_FILE = OUTPUT_DIR / "price_manual_review.csv"
SUMMARY_FILE = OUTPUT_DIR / "price_evidence_summary.txt"

REQUEST_DELAY = 0.8
TIMEOUT = 20
MAX_SEARCH_RESULTS = 20
MAX_SOURCES_PER_TARGET = 8

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/154.0 Safari/537.36"
    ),
    "Accept-Language": "en-KE,en;q=0.9",
}

SESSION = requests.Session()
SESSION.headers.update(HEADERS)


# ============================================================
# THE 18 VALIDATED COMPARISONS
# ============================================================

KNOWN_COMPARISONS = {
    "MAC12SP21V": {
        "brand": "BRUHM",
        "model": "BAS-12IC3W",
        "product": "Bruhm 12K Inverter Split Air Conditioner",
    },
    "MAC12SP11": {
        "brand": "BRUHM",
        "model": "BAS-12ICQB",
        "product": "Bruhm 12000 BTU Air Conditioner",
    },
    "MAC18SP11": {
        "brand": "BRUHM",
        "model": "BAS-18ICQB",
        "product": "Bruhm 18000 BTU Air Conditioner",
    },
    "MAC24SP11": {
        "brand": "BRUHM",
        "model": "BAS-24ICQB",
        "product": "Bruhm 24000 BTU Air Conditioner",
    },
    "MMWDGBB251BXBI": {
        "brand": "HAIER",
        "model": "HBMW25LBG",
        "product": "Haier 25L Built In Microwave",
    },
    "MMWDGTA252BBI": {
        "brand": "HAIER",
        "model": "HBMW25LBG",
        "product": "Haier 25L Built In Microwave",
    },
    "MMWDGBB341BBI": {
        "brand": "HAIER",
        "model": "HBMW34CB",
        "product": "Haier 34L Built In Microwave",
    },
    "MCF200SG": {
        "brand": "BRUHM",
        "model": "BCS-210EI/BCS-250EI",
        "product": "Bruhm 200L Chest Freezer",
    },
    "MCF102W": {
        "brand": "BRUHM",
        "model": "BCS-100M",
        "product": "Bruhm 100L Single Door Chest Freezer",
    },
    "MCF200W": {
        "brand": "BRUHM",
        "model": "BCS-210EI/BCS-250EI",
        "product": "Bruhm 200L Chest Freezer",
    },
    "MCF102SG": {
        "brand": "BRUHM",
        "model": "BCS-100M",
        "product": "Bruhm 100L Single Door Chest Freezer",
    },
    "MCF300W": {
        "brand": "BRUHM",
        "model": "BCS-310MX",
        "product": "Bruhm 282L Single Door Chest Freezer",
    },
    "MCF142WSG": {
        "brand": "BRUHM",
        "model": "BCS-160EI/BCS-170EI",
        "product": "Bruhm 142L Chest Freezer",
    },
    "MRDCD70SBR": {
        "brand": "BRUHM",
        "model": "BFD-135MD",
        "product": "Bruhm 118L Top Mount Refrigerator",
    },
    "MRDCD70XSF": {
        "brand": "BRUHM",
        "model": "BFD-135MD",
        "product": "Bruhm 118L Top Mount Refrigerator",
    },
    "MRDCD70XLB": {
        "brand": "BRUHM",
        "model": "BFD-135MD",
        "product": "Bruhm 118L Top Mount Refrigerator",
    },
    "MRDCD70LSD": {
        "brand": "BRUHM",
        "model": "BFD-135MD",
        "product": "Bruhm 118L Top Mount Refrigerator",
    },
    "MRDCD70XDM": {
        "brand": "BRUHM",
        "model": "BFD-135MD",
        "product": "Bruhm 118L Top Mount Refrigerator",
    },
}


# ============================================================
# KNOWN MIKA PRODUCT URLS
# ============================================================

KNOWN_MIKA_URLS = {
    "MAC12SP21V":
        "https://mikaappliances.com/product/air-conditioner-12000btu-inverter-white/",

    "MAC12SP11":
        "https://mikaappliances.com/product/air-conditioner-12000btu-white/",

    "MAC18SP11":
        "https://mikaappliances.com/product/air-conditioner-18000btu-white/",

    "MAC24SP11":
        "https://mikaappliances.com/product/air-conditioner-18000btu-white/",

    "MMWDGBB251BXBI":
        "https://mikaappliances.com/product/built-in-microwave-25l-black-ss/",

    "MMWDGTA252BBI":
        "https://mikaappliances.com/product/built-in-microwave-25l-touch-control-black/",

    "MMWDGBB341BBI":
        "https://mikaappliances.com/?post_type=product&p=73779",

    "MCF200SG":
        "https://mikaappliances.com/product/freezer-200l-silver/",

    "MCF102W":
        "https://mikaappliances.com/product/freezer-100l-white/",

    "MCF200W":
        "https://mikaappliances.com/product/freezer-200l-white/",

    "MCF102SG":
        "https://mikaappliances.com/product/freezer-100l-silver-grey/",

    "MCF300W":
        "https://mikaappliances.com/product/freezer-282l-white/",

    "MCF142WSG":
        "https://mikaappliances.com/product/freezer-142l-silver-grey/",

    "MRDCD70SBR":
        "https://mikaappliances.com/product/refrigerator-118l-direct-cool-double-door-silver-brush/",

    "MRDCD70XSF":
        "https://mikaappliances.com/product/refrigerator-118l-direct-cool-double-door-black-brush/",

    "MRDCD70XLB":
        "https://mikaappliances.com/product/refrigerator-118l-direct-cool-double-door-dark-silver/",

    "MRDCD70LSD":
        "https://mikaappliances.com/product/refrigerator-118l-direct-cool-double-door-line-silver-dark/",

    "MRDCD70XDM":
        "https://mikaappliances.com/product/refrigerator-118l-direct-cool-double-door-dark-matt-ss/",
}


# ============================================================
# KNOWN COMMERCIAL URL ALREADY VERIFIED
# ============================================================
#
# These are not invented prices.
# They are exact product-page URLs already encountered during
# our investigation.
#
# More URLs can be discovered automatically.
# ============================================================

KNOWN_RETAILER_URLS = {
    "MAC12SP11": [
        "https://www.kenyatronics.com/view-product/mika-air-conditioner-12000btu-white",
        "https://www.urbanappliances.co.ke/mika-air-conditioner-12000btu-white-mac12sp11/",
        "https://nairobihomeappliances.com/product/mika-air-conditioner-12000btu-white-mac12sp11/",
        "https://www.kitchen.co.ke/product/mika-air-conditioner-12000btu-mac12sp11/",
    ],

    "MMWDGBB251BXBI": [
        "https://nairobihomeappliances.com/",
    ],

    "MMWDGTA252BBI": [
        "https://nairobihomeappliances.com/",
    ],

    "MMWDGBB341BBI": [
        "https://nairobihomeappliances.com/",
    ],

    "MCF102W": [
        "https://www.leviticuselectronics.co.ke/",
    ],

    "MCF200W": [
        "https://www.kenyatronics.com/",
    ],

    "MCF200SG": [
        "https://patabay.com/",
    ],

    "MRDCD70SBR": [
        "https://www.kenyatronics.com/",
    ],
}


# ============================================================
# DOMAIN FILTERS
# ============================================================

BLOCKED_DOMAINS = {
    "youtube.com",
    "music.youtube.com",
    "movies.youtube.com",
    "tv.youtube.com",
    "youtubekids.com",
    "google.com",
    "googleusercontent.com",
    "googleapis.com",
    "googlevideo.com",
    "googleadservices.com",
    "play.google.com",
    "photos.google.com",
    "drive.google.com",
    "zhihu.com",
    "baidu.com",
    "microsoft.com",
    "microsoftonline.com",
    "office.com",
    "classroom.google.com",
    "claude.ai",
    "facebook.com",
    "instagram.com",
    "tiktok.com",
    "twitter.com",
    "x.com",
    "reddit.com",
    "pinterest.com",
    "wikipedia.org",
}


PREFERRED_DOMAIN_TERMS = (
    ".co.ke",
    ".ke",
    "kenyatronics",
    "nairobihomeappliances",
    "urbanappliances",
    "pafekto",
    "leviticuselectronics",
    "kitchen.co.ke",
    "al-yassin",
    "alyassin",
    "businessclaud",
    "quest",
    "patabay",
    "jumia",
    "kilimall",
    "carrefour",
)


# ============================================================
# HELPERS
# ============================================================

def clean_text(value: str | None) -> str:
    if not value:
        return ""

    value = html.unescape(str(value))
    value = re.sub(r"\s+", " ", value)

    return value.strip()


def normalize_url(url: str | None) -> str:
    if not url:
        return ""

    url = html.unescape(url.strip())

    if url.startswith("//"):
        url = "https:" + url

    if not url.startswith(("http://", "https://")):
        return ""

    return url


def domain_of(url: str) -> str:
    try:
        return urlparse(url).netloc.lower().replace("www.", "")
    except Exception:
        return ""


def is_blocked_domain(url: str) -> bool:
    domain = domain_of(url)

    if not domain:
        return True

    for blocked in BLOCKED_DOMAINS:
        if (
            domain == blocked
            or domain.endswith("." + blocked)
        ):
            return True

    return False


def domain_score(url: str) -> int:
    domain = domain_of(url)

    if is_blocked_domain(url):
        return -100

    if any(
        term in domain
        for term in PREFERRED_DOMAIN_TERMS
    ):
        return 100

    return 10


def model_tokens(model_no: str) -> list[str]:
    model_no = clean_text(model_no).upper()

    if not model_no:
        return []

    parts = re.split(
        r"[/,;|]+",
        model_no,
    )

    tokens = [
        clean_text(x).upper()
        for x in parts
        if clean_text(x)
    ]

    if model_no not in tokens:
        tokens.append(model_no)

    return list(dict.fromkeys(tokens))


def model_present(
    text: str,
    model_no: str,
) -> bool:

    text = clean_text(text).upper()

    if not text:
        return False

    return any(
        token in text
        for token in model_tokens(model_no)
    )


def product_name_score(
    text: str,
    product_name: str,
) -> float:

    text = clean_text(text).lower()

    words = re.findall(
        r"[a-z0-9]{3,}",
        clean_text(product_name).lower(),
    )

    ignored = {
        "mika",
        "bruhm",
        "haier",
        "the",
        "and",
        "with",
        "for",
        "white",
        "black",
        "silver",
        "grey",
        "gray",
    }

    words = [
        x
        for x in words
        if x not in ignored
    ]

    if not words:
        return 0.0

    hits = sum(
        1
        for word in words
        if word in text
    )

    return hits / len(words)


# ============================================================
# BING REDIRECT
# ============================================================

def decode_bing_url(url: str) -> str:

    url = normalize_url(url)

    if not url:
        return ""

    try:
        parsed = urlparse(url)

        if "bing.com" not in parsed.netloc.lower():
            return url

        query = parse_qs(parsed.query)

        for key in ("u", "url"):

            values = query.get(key)

            if not values:
                continue

            destination = unquote(
                unquote(values[0])
            )

            if destination.startswith(
                ("http://", "https://")
            ):
                return destination

    except Exception:
        pass

    return url


# ============================================================
# SEARCH
# ============================================================

def search_bing(
    query: str,
    max_results: int = MAX_SEARCH_RESULTS,
    required_model: str | None = None,
) -> list[dict]:

    try:

        response = SESSION.get(
            "https://www.bing.com/search",
            params={
                "q": query,
                "count": max_results,
                "setlang": "en-KE",
            },
            timeout=TIMEOUT,
        )

        response.raise_for_status()

    except Exception:

        return []

    soup = BeautifulSoup(
        response.text,
        "html.parser",
    )

    results = []

    for block in soup.select("li.b_algo"):

        anchor = block.select_one("h2 a")

        if not anchor:
            continue

        url = decode_bing_url(
            anchor.get("href", "")
        )

        if not url:
            continue

        if is_blocked_domain(url):
            continue

        title = clean_text(
            anchor.get_text(
                " ",
                strip=True,
            )
        )

        snippet_el = block.select_one(
            ".b_caption p"
        )

        snippet = clean_text(
            snippet_el.get_text(
                " ",
                strip=True,
            )
            if snippet_el
            else block.get_text(
                " ",
                strip=True,
            )
        )

        combined = " ".join(
            [
                title,
                url,
                snippet,
            ]
        )

        # Exact model filtering.
        if required_model:
            if not model_present(
                combined,
                required_model,
            ):
                continue

        results.append(
            {
                "title": title,
                "url": url,
                "snippet": snippet,
                "domain_score": domain_score(url),
            }
        )

    results.sort(
        key=lambda x: x["domain_score"],
        reverse=True,
    )

    return results[:max_results]


# ============================================================
# SEARCH QUERY GENERATION
# ============================================================

def search_queries(
    model_no: str,
    product_name: str,
) -> list[str]:

    model = clean_text(model_no)
    name = clean_text(product_name)

    return [
        f"{model} Kenya KSh",
        f"{model} Kenya price",
        f"{model} Kenya appliance",
        f"{model} Kenya",
        f"{model} {name} Kenya",
        f"{model} site:.co.ke",
        f"{model} price site:.co.ke",
        f"{model} KSh site:.co.ke",
    ]


# ============================================================
# SOURCE DISCOVERY
# ============================================================

def discover_sources(
    brand: str,
    model_no: str,
    product_name: str,
    official_url: str | None = None,
) -> list[str]:

    accepted = []

    # --------------------------------------------------------
    # IMPORTANT:
    # Official MIKA URL is retained as a reference, but it is
    # NOT allowed to stop retailer discovery.
    # --------------------------------------------------------

    if official_url:
        url = normalize_url(official_url)

        if url:
            accepted.append(url)

    # --------------------------------------------------------
    # Add already-known commercial URLs.
    # --------------------------------------------------------

    for url in KNOWN_RETAILER_URLS.get(
        model_no.upper(),
        [],
    ):

        url = normalize_url(url)

        if not url:
            continue

        if url in accepted:
            continue

        accepted.append(url)

    # --------------------------------------------------------
    # Search.
    # --------------------------------------------------------

    for query in search_queries(
        model_no,
        product_name,
    ):

        results = search_bing(
            query,
            MAX_SEARCH_RESULTS,
            required_model=model_no,
        )

        for result in results:

            url = normalize_url(
                result["url"]
            )

            if not url:
                continue

            if is_blocked_domain(url):
                continue

            # Never accept a search result unless the result
            # itself contains the required model.
            combined = " ".join(
                [
                    result["title"],
                    result["url"],
                    result["snippet"],
                ]
            )

            if not model_present(
                combined,
                model_no,
            ):
                continue

            if url in accepted:
                continue

            accepted.append(url)

            if len(accepted) >= MAX_SOURCES_PER_TARGET:
                return accepted

        time.sleep(REQUEST_DELAY)

    return accepted[:MAX_SOURCES_PER_TARGET]


# ============================================================
# FETCH
# ============================================================

def fetch_page(
    url: str,
) -> tuple[str, int, str]:

    try:

        response = SESSION.get(
            url,
            headers=HEADERS,
            timeout=TIMEOUT,
            allow_redirects=True,
        )

        if response.status_code >= 400:
            return (
                "",
                response.status_code,
                response.url or url,
            )

        return (
            response.text,
            response.status_code,
            response.url or url,
        )

    except Exception:

        return (
            "",
            0,
            url,
        )


# ============================================================
# PRODUCT BLOCKS
# ============================================================

def find_product_blocks(
    soup: BeautifulSoup,
    model_no: str,
    product_name: str,
    allow_name_fallback: bool,
) -> list[dict]:

    candidates = []
    seen = set()

    selectors = [
        "div.product[id^='product-']",
        "article.product",
        "article.type-product",
        "div.product",
        ".summary.entry-summary",
        ".woocommerce-product-details__short-description",
        ".product-summary",
        ".single-product",
    ]

    for selector in selectors:

        for block in soup.select(selector):

            identity = id(block)

            if identity in seen:
                continue

            seen.add(identity)

            text = clean_text(
                block.get_text(
                    " ",
                    strip=True,
                )
            )

            if not text:
                continue

            if model_present(
                text,
                model_no,
            ):

                candidates.append(
                    {
                        "block": block,
                        "match_status": "EXACT_MODEL_VISIBLE",
                        "score": 100,
                    }
                )

                continue

            if allow_name_fallback:

                score = product_name_score(
                    text,
                    product_name,
                )

                if score >= 0.55:

                    candidates.append(
                        {
                            "block": block,
                            "match_status":
                                "KNOWN_EXACT_URL_PRODUCT_NAME",
                            "score": int(score * 100),
                        }
                    )

    candidates.sort(
        key=lambda x: x["score"],
        reverse=True,
    )

    return candidates


# ============================================================
# PRICE EXTRACTION
# ============================================================

def parse_kes_values(
    text: str,
) -> list[int]:

    text = clean_text(text)

    if not text:
        return []

    patterns = [
        r"(?:KSh|Ksh|KSH|KES|Kes|kes|Sh)\s*"
        r"([0-9]{1,3}(?:,[0-9]{3})+(?:\.\d{1,2})?)",

        r"(?:KSh|Ksh|KSH|KES|Kes|kes|Sh)\s*"
        r"([0-9]+(?:\.\d{1,2})?)",
    ]

    values = []

    for pattern in patterns:

        for match in re.findall(
            pattern,
            text,
        ):

            try:

                value = int(
                    round(
                        float(
                            match.replace(",", "")
                        )
                    )
                )

                if 100 <= value <= 2_000_000:
                    values.append(value)

            except Exception:
                pass

    return list(
        dict.fromkeys(values)
    )


def extract_prices(
    block,
) -> tuple[list[int], list[int], list[int]]:

    regular = []
    sale = []

    # WooCommerce.
    for element in block.select("del"):

        regular.extend(
            parse_kes_values(
                element.get_text(
                    " ",
                    strip=True,
                )
            )
        )

    for element in block.select("ins"):

        sale.extend(
            parse_kes_values(
                element.get_text(
                    " ",
                    strip=True,
                )
            )
        )

    # Generic price structures.
    if not regular and not sale:

        selectors = [
            ".price",
            ".woocommerce-Price-amount",
            ".product-price",
            ".sale-price",
            ".regular-price",
            "[class*='price']",
        ]

        for selector in selectors:

            for element in block.select(
                selector
            ):

                text = clean_text(
                    element.get_text(
                        " ",
                        strip=True,
                    )
                )

                values = parse_kes_values(text)

                if not values:
                    continue

                classes = " ".join(
                    element.get(
                        "class",
                        [],
                    )
                ).lower()

                if (
                    "sale" in classes
                    or "offer" in classes
                    or "discount" in classes
                ):
                    sale.extend(values)

                elif "regular" in classes:
                    regular.extend(values)

                else:
                    regular.extend(values)

    regular = list(
        dict.fromkeys(regular)
    )

    sale = list(
        dict.fromkeys(sale)
    )

    all_values = list(
        dict.fromkeys(
            regular + sale
        )
    )

    return (
        all_values,
        regular,
        sale,
    )


# ============================================================
# INSPECT SOURCE
# ============================================================

def inspect_source(
    url: str,
    brand: str,
    model_no: str,
    product_name: str,
    target_id: str,
) -> dict:

    result = {
        "target_id": target_id,
        "brand": brand,
        "model_no": model_no,
        "product_name": product_name,
        "source_url": url,
        "source_domain": domain_of(url),
        "price_status": "SOURCE_FETCH_FAILED",
        "price_kes": "",
        "regular_price_kes": "",
        "sale_price_kes": "",
        "price_candidates": "",
        "match_status": "TARGET_NOT_FOUND",
        "evidence_context": "",
        "observed_date": date.today().isoformat(),
        "notes": "",
    }

    page_html, status, final_url = fetch_page(url)

    if not page_html:

        result["notes"] = (
            f"HTTP fetch failed. status={status}"
        )

        return result

    soup = BeautifulSoup(
        page_html,
        "html.parser",
    )

    known_official = (
        brand.upper() == "MIKA"
        and model_no.upper()
        in KNOWN_MIKA_URLS
        and (
            url.rstrip("/")
            == KNOWN_MIKA_URLS[
                model_no.upper()
            ].rstrip("/")
            or final_url.rstrip("/")
            == KNOWN_MIKA_URLS[
                model_no.upper()
            ].rstrip("/")
        )
    )

    blocks = find_product_blocks(
        soup,
        model_no,
        product_name,
        allow_name_fallback=known_official,
    )

    if not blocks:

        result["price_status"] = (
            "TARGET_NOT_FOUND"
        )

        result["notes"] = (
            "No validated product block found. "
            "The source may be JS-rendered, blocked, "
            "or not expose the product in server HTML."
        )

        return result

    best = blocks[0]

    block = best["block"]

    price_values, regular, sale = extract_prices(
        block
    )

    if not price_values:

        price_status = "PRICE_NOT_EXPOSED"
        selected_price = ""

    elif regular and sale:

        if len(sale) == 1:

            price_status = (
                "VERIFIED_RETAIL_PROMOTIONAL_PRICE"
            )

            selected_price = sale[0]

        else:

            price_status = (
                "MULTIPLE_PRICE_CANDIDATES"
            )

            selected_price = ""

    elif len(price_values) == 1:

        price_status = (
            "VERIFIED_RETAIL_PRICE"
        )

        selected_price = price_values[0]

    else:

        price_status = (
            "MULTIPLE_PRICE_CANDIDATES"
        )

        selected_price = ""

    context = clean_text(
        block.get_text(
            " ",
            strip=True,
        )
    )

    if len(context) > 3000:
        context = context[:3000] + " ..."

    result.update(
        {
            "price_status": price_status,
            "price_kes": selected_price,
            "regular_price_kes": (
                regular[0]
                if len(regular) == 1
                else ""
            ),
            "sale_price_kes": (
                sale[0]
                if len(sale) == 1
                else ""
            ),
            "price_candidates": ";".join(
                str(x)
                for x in price_values
            ),
            "match_status": best[
                "match_status"
            ],
            "evidence_context": context,
        }
    )

    if known_official:

        result["notes"] = (
            "Known exact MIKA URL. "
            "Product-name fallback allowed."
        )

    return result


# ============================================================
# LOAD MIKA PRODUCT DETAILS
# ============================================================

def load_mika_details() -> dict:

    details = {}

    if COMPARISON_FILE.exists():

        with COMPARISON_FILE.open(
            "r",
            encoding="utf-8-sig",
            newline="",
        ) as f:

            rows = list(
                csv.DictReader(f)
            )

        for row in rows:

            model = clean_text(
                row.get("mika_model_no")
            ).upper()

            if not model:
                continue

            status = clean_text(
                row.get("match_status")
            ).upper()

            if status not in {
                "STRONG_COMPARABLE",
                "COMPARABLE",
            }:
                continue

            if model not in KNOWN_COMPARISONS:
                continue

            details[model] = {
                "category": clean_text(
                    row.get("category")
                ),
                "sub_category": clean_text(
                    row.get("sub_category")
                ),
                "product_name": clean_text(
                    row.get("mika_product_name")
                ),
                "match_status": status,
                "match_confidence": clean_text(
                    row.get("match_confidence")
                ),
            }

    # --------------------------------------------------------
    # Fill any missing known validated comparisons.
    #
    # This guarantees that the collector cannot silently
    # drop validated products because the CSV changed.
    # --------------------------------------------------------

    for model, comparison in KNOWN_COMPARISONS.items():

        if model not in details:

            details[model] = {
                "category": "",
                "sub_category": "",
                "product_name": "",
                "match_status": (
                    "STRONG_COMPARABLE"
                    if model
                    in {
                        "MAC12SP21V",
                        "MMWDGBB251BXBI",
                        "MMWDGTA252BBI",
                        "MMWDGBB341BBI",
                    }
                    else "COMPARABLE"
                ),
                "match_confidence": "",
            }

    # --------------------------------------------------------
    # Fill missing product names from the known comparison
    # data only where the catalogue CSV did not supply one.
    # --------------------------------------------------------

    for model in details:

        if not details[model]["product_name"]:

            if model in KNOWN_COMPARISONS:

                details[model][
                    "product_name"
                ] = KNOWN_COMPARISONS[
                    model
                ]["product"]

    return details


# ============================================================
# COLLECT ONE TARGET
# ============================================================

def collect_target(
    model_no: str,
    details: dict,
) -> list[dict]:

    comparison = KNOWN_COMPARISONS[
        model_no
    ]

    product_name = details[
        "product_name"
    ]

    official_url = KNOWN_MIKA_URLS.get(
        model_no
    )

    print()
    print("=" * 78)
    print(
        f"{model_no} | {product_name}"
    )
    print(
        f"Competitor: "
        f"{comparison['brand']} "
        f"{comparison['model']}"
    )
    print("=" * 78)

    sources = discover_sources(
        "MIKA",
        model_no,
        product_name,
        official_url,
    )

    print(
        f"DISCOVERED SOURCES: {len(sources)}"
    )

    rows = []

    for index, source in enumerate(
        sources,
        start=1,
    ):

        print(
            f"[{index}/{len(sources)}] {source}"
        )

        row = inspect_source(
            source,
            "MIKA",
            model_no,
            product_name,
            model_no,
        )

        row.update(
            {
                "category": details[
                    "category"
                ],
                "sub_category": details[
                    "sub_category"
                ],
                "competitor_brand":
                    comparison["brand"],
                "competitor_model_no":
                    comparison["model"],
                "competitor_product_name":
                    comparison["product"],
                "comparison_match_status":
                    details["match_status"],
                "comparison_match_confidence":
                    details[
                        "match_confidence"
                    ],
            }
        )

        rows.append(row)

        print(
            "    ",
            row["price_status"],
            "|",
            row["match_status"],
            "|",
            row["price_kes"] or "-",
        )

        time.sleep(
            REQUEST_DELAY
        )

    return rows


# ============================================================
# POSITIONING
# ============================================================

def build_positioning(
    evidence_rows: list[dict],
) -> list[dict]:

    output = []

    models = sorted(
        set(
            row["target_id"]
            for row in evidence_rows
        )
    )

    for model in models:

        rows = [
            row
            for row in evidence_rows
            if row["target_id"] == model
        ]

        verified = []

        for row in rows:

            if row["price_kes"] in (
                "",
                None,
            ):
                continue

            try:

                price = int(
                    row["price_kes"]
                )

            except Exception:

                continue

            verified.append(
                (price, row)
            )

        if not verified:

            row = rows[0]

            output.append(
                {
                    "target_id": model,
                    "brand": "MIKA",
                    "model_no": model,
                    "product_name":
                        row["product_name"],
                    "source_url": "",
                    "price_kes": "",
                    "price_status":
                        "PRICE_COMPARISON_NOT_AVAILABLE",
                    "regular_price_kes": "",
                    "sale_price_kes": "",
                    "comparison_note":
                        "No single verified MIKA price available.",
                }
            )

            continue

        prices = sorted(
            set(
                price
                for price, _ in verified
            )
        )

        if len(prices) > 1:

            row = rows[0]

            output.append(
                {
                    "target_id": model,
                    "brand": "MIKA",
                    "model_no": model,
                    "product_name":
                        row["product_name"],
                    "source_url": "",
                    "price_kes": "",
                    "price_status":
                        "MULTIPLE_PRICE_CANDIDATES",
                    "regular_price_kes": "",
                    "sale_price_kes": "",
                    "comparison_note":
                        "Multiple verified-source prices exist; "
                        "no arbitrary price selected.",
                }
            )

            continue

        price, row = verified[0]

        output.append(
            {
                "target_id": model,
                "brand": "MIKA",
                "model_no": model,
                "product_name":
                    row["product_name"],
                "source_url":
                    row["source_url"],
                "price_kes": price,
                "price_status":
                    row["price_status"],
                "regular_price_kes":
                    row["regular_price_kes"],
                "sale_price_kes":
                    row["sale_price_kes"],
                "comparison_note":
                    "Single verified price candidate.",
            }
        )

    return output


# ============================================================
# WRITE CSV
# ============================================================

def write_csv(
    path: Path,
    rows: list[dict],
) -> None:

    if not rows:

        path.write_text(
            "",
            encoding="utf-8",
        )

        return

    fields = []

    for row in rows:

        for key in row:

            if key not in fields:
                fields.append(key)

    with path.open(
        "w",
        encoding="utf-8-sig",
        newline="",
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=fields,
            extrasaction="ignore",
        )

        writer.writeheader()
        writer.writerows(rows)


# ============================================================
# SUMMARY
# ============================================================

def write_summary(
    details: dict,
    evidence: list[dict],
    positioning: list[dict],
) -> None:

    from collections import Counter

    statuses = Counter(
        row["price_status"]
        for row in evidence
    )

    matches = Counter(
        row["match_status"]
        for row in evidence
    )

    verified_models = set(
        row["target_id"]
        for row in evidence
        if row["price_status"]
        in {
            "VERIFIED_RETAIL_PRICE",
            "VERIFIED_RETAIL_PROMOTIONAL_PRICE",
        }
    )

    manual_models = set(
        row["target_id"]
        for row in evidence
        if row["price_status"]
        == "MULTIPLE_PRICE_CANDIDATES"
    )

    lines = [
        "MIKA CI - TARGETED PRICE EVIDENCE PREVIEW",
        "=" * 60,
        "",
        "PREVIEW ONLY - NO SQLITE WRITES",
        f"Run date: {date.today().isoformat()}",
        "",
        f"Validated target models: {len(KNOWN_COMPARISONS)}",
        f"Loaded target details: {len(details)}",
        f"Evidence records: {len(evidence)}",
        f"Positioning records: {len(positioning)}",
        f"Models with verified prices: {len(verified_models)}",
        f"Models requiring manual review: {len(manual_models)}",
        "",
        "PRICE STATUS",
        "-" * 60,
    ]

    for key, value in statuses.most_common():

        lines.append(
            f"{key}: {value}"
        )

    lines.extend(
        [
            "",
            "MATCH STATUS",
            "-" * 60,
        ]
    )

    for key, value in matches.most_common():

        lines.append(
            f"{key}: {value}"
        )

    lines.extend(
        [
            "",
            "VALIDATED TARGETS",
            "-" * 60,
        ]
    )

    for model in KNOWN_COMPARISONS:

        lines.append(
            f"{model} -> "
            f"{KNOWN_COMPARISONS[model]['brand']} "
            f"{KNOWN_COMPARISONS[model]['model']}"
        )

    lines.extend(
        [
            "",
            "OUTPUTS",
            "-" * 60,
            str(PRICE_EVIDENCE_FILE),
            str(POSITIONING_FILE),
            str(MANUAL_REVIEW_FILE),
            str(SUMMARY_FILE),
            "",
            "EVIDENCE RULES",
            "-" * 60,
            "Search snippets are discovery only.",
            "Actual product-page content is required for price evidence.",
            "Retailer pages require exact model validation.",
            "Known MIKA URLs are references and may be JS/blocking shells.",
            "Regular and sale prices remain separate.",
            "Multiple prices are never arbitrarily selected.",
            "SQLite writes: NONE.",
        ]
    )

    SUMMARY_FILE.write_text(
        "\n".join(lines),
        encoding="utf-8",
    )


# ============================================================
# MAIN
# ============================================================

def main() -> None:

    print()
    print("=" * 78)
    print("MIKA CI - TARGETED PRICE EVIDENCE PREVIEW")
    print("=" * 78)
    print()
    print("PREVIEW ONLY")
    print("SQLite writes: DISABLED")
    print()

    details = load_mika_details()

    print(
        "Validated comparison targets:",
        len(KNOWN_COMPARISONS),
    )

    print(
        "Target details loaded:",
        len(details),
    )

    if len(details) != 18:

        raise SystemExit(
            "ERROR: Expected 18 validated targets."
        )

    evidence = []

    for model in KNOWN_COMPARISONS:

        evidence.extend(
            collect_target(
                model,
                details[model],
            )
        )

    positioning = build_positioning(
        evidence
    )

    manual_review = [
        row
        for row in evidence
        if row["price_status"]
        in {
            "TARGET_NOT_FOUND",
            "SOURCE_FETCH_FAILED",
            "MULTIPLE_PRICE_CANDIDATES",
        }
    ]

    write_csv(
        PRICE_EVIDENCE_FILE,
        evidence,
    )

    write_csv(
        POSITIONING_FILE,
        positioning,
    )

    write_csv(
        MANUAL_REVIEW_FILE,
        manual_review,
    )

    write_summary(
        details,
        evidence,
        positioning,
    )

    print()
    print("=" * 78)
    print("COMPLETE")
    print("=" * 78)
    print()
    print(
        f"Validated targets: {len(KNOWN_COMPARISONS)}"
    )
    print(
        f"Evidence records:  {len(evidence)}"
    )
    print(
        f"Positioning rows:  {len(positioning)}"
    )
    print(
        f"Manual review:     {len(manual_review)}"
    )
    print()
    print(
        f"Evidence:    {PRICE_EVIDENCE_FILE}"
    )
    print(
        f"Positioning: {POSITIONING_FILE}"
    )
    print(
        f"Review:      {MANUAL_REVIEW_FILE}"
    )
    print(
        f"Summary:     {SUMMARY_FILE}"
    )
    print()
    print("SQLite writes: NONE")
    print()


if __name__ == "__main__":
    main()