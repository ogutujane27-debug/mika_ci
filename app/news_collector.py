"""
MIKA CI - NEWS INTELLIGENCE PREVIEW

Read-only News Intelligence collector.

IMPORTANT:
- This module does NOT write to SQLite.
- It discovers and validates Kenya-relevant market news.
- It produces CSV, JSON and TXT preview files only.
- SQLite persistence is handled separately after validation.

Primary correction in this version:
- Clean JSON-LD articleBody extraction
- Preserve legitimate Unicode punctuation
- Repair common UTF-8 / Windows-1252 mojibake
- Remove trailing publisher/footer boilerplate
- Remove duplicate article paragraphs/blocks
- Retain <article>, content-selector and <p> fallbacks
- Avoid page-wide footer contamination
"""

from __future__ import annotations

import csv
import hashlib
import html
import json
import re
import sys
import time
import unicodedata
import xml.etree.ElementTree as ET

from collections import Counter
from datetime import date, datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any
from urllib.parse import quote, urlparse

import requests
from bs4 import BeautifulSoup

try:
    from googlenewsdecoder import gnewsdecoder
except ImportError:
    gnewsdecoder = None


# ============================================================================
# CONFIGURATION
# ============================================================================

WINDOW_DAYS = 7

REQUEST_TIMEOUT = (5, 12)

MAX_RSS_RESULTS_PER_QUERY = 10
MAX_RSS_QUERIES = 80

MAX_RESOLUTION_CANDIDATES = 80
MAX_ACCEPTED_ARTICLES = 250

REQUEST_DELAY = 0.20

PROJECT_ROOT = Path(__file__).resolve().parents[1]

OUTPUT_DIR = PROJECT_ROOT / "reports" / "mika_news_preview"

CSV_OUTPUT = OUTPUT_DIR / "news_intelligence_preview.csv"
JSON_OUTPUT = OUTPUT_DIR / "news_intelligence_preview.json"
SUMMARY_OUTPUT = OUTPUT_DIR / "news_intelligence_preview.txt"


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/154.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-KE,en;q=0.9",
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;"
        "q=0.9,image/avif,image/webp,*/*;q=0.8"
    ),
}

SESSION = requests.Session()
SESSION.headers.update(HEADERS)


# ============================================================================
# TRACKED ENTITY UNIVERSE
# ============================================================================

TRACKED_ENTITIES = [
    "Hotpoint",
    "Ramtons",
    "Hisense",
    "Haier",
    "Armco",
    "Bruhm",
    "K-Elec",
    "Philips",
    "TCL",
    "Samsung",
    "LG",
    "Midea",
    "Moulinex",
    "Tefal",
    "Krups",
    "SCL",
    "Berklays",
    "Hypermart",
    "JTC",
    "Vision Plus",
    "Vitron",
    "Anicuma Traders Limited",
    "Anke Home Appliance",
    "Rebune.ke",
    "Jumia",
    "Kilimall",
    "Carrefour",
]


# ============================================================================
# NEWS CLASSIFICATION
# ============================================================================

NEWS_CATEGORIES = [
    "COMPANY_DEVELOPMENT",
    "PARTNERSHIP",
    "EXPANSION",
    "DISTRIBUTION",
    "MARKET_DEVELOPMENT",
    "INDUSTRY_NEWS",
]


CATEGORY_RULES = {
    "COMPANY_DEVELOPMENT": [
        "launch",
        "launched",
        "launches",
        "new product",
        "new appliance",
        "new range",
        "new generation",
        "assembly",
        "local assembly",
        "manufacturing",
        "factory",
        "investment",
        "invests",
        "investment",
        "business",
        "company",
        "brand",
        "innovation",
        "connected home",
        "smart home",
        "service month",
        "roadshow",
    ],
    "PARTNERSHIP": [
        "partnership",
        "partner",
        "partners",
        "collaboration",
        "collaborate",
        "agreement",
        "deal",
        "joint venture",
        "strategic alliance",
    ],
    "EXPANSION": [
        "expansion",
        "expand",
        "expands",
        "opens",
        "opening",
        "new store",
        "new outlet",
        "outlet",
        "branches",
        "branch",
        "regional expansion",
        "market expansion",
        "enters market",
        "entered market",
    ],
    "DISTRIBUTION": [
        "distribution",
        "distributor",
        "distributors",
        "retailer",
        "retailers",
        "retail",
        "dealer",
        "dealers",
        "stockist",
        "e-commerce",
        "online store",
        "marketplace",
    ],
    "MARKET_DEVELOPMENT": [
        "market",
        "consumer",
        "consumers",
        "demand",
        "sales",
        "pricing",
        "prices",
        "affordability",
        "electrification",
        "rural electrification",
        "households",
        "homes",
        "kenyan homes",
        "kenya",
    ],
    "INDUSTRY_NEWS": [
        "industry",
        "appliance industry",
        "electronics industry",
        "home appliances",
        "consumer electronics",
        "technology",
        "energy",
        "sustainability",
        "regulation",
        "regulatory",
        "sector",
    ],
}


# ============================================================================
# PRODUCT / CATEGORY TERMS
# ============================================================================

PRODUCT_TERMS = {
    "Refrigeration": [
        "refrigerator",
        "refrigerators",
        "fridge",
        "fridges",
        "freezer",
        "freezers",
        "side by side",
        "double door",
        "single door",
        "top mount",
        "bottom mount",
        "chest freezer",
        "upright freezer",
    ],
    "Laundry": [
        "washing machine",
        "washing machines",
        "washer",
        "washers",
        "dryer",
        "dryers",
        "tumble dryer",
        "laundry",
        "washer dryer",
    ],
    "Cooking": [
        "cooker",
        "cookers",
        "oven",
        "ovens",
        "gas cooker",
        "electric cooker",
        "built-in oven",
        "hob",
        "hobs",
        "microwave",
        "microwaves",
        "air fryer",
        "air fryers",
        "cooking",
    ],
    "Small Kitchen Appliances": [
        "blender",
        "blenders",
        "kettle",
        "kettles",
        "toaster",
        "toasters",
        "coffee maker",
        "coffee makers",
        "food processor",
        "food processors",
        "mixer",
        "mixers",
        "juicer",
        "juicers",
        "small appliance",
        "small appliances",
    ],
    "TV & Audio": [
        "television",
        "televisions",
        "tv",
        "tvs",
        "smart tv",
        "smart televisions",
        "qled",
        "oled",
        "neo qled",
        "soundbar",
        "soundbars",
        "audio",
        "home entertainment",
    ],
    "Air & Climate": [
        "air conditioner",
        "air conditioners",
        "air conditioning",
        "ac",
        "fan",
        "fans",
        "air cooler",
        "air coolers",
        "heating",
        "cooling",
    ],
    "Water": [
        "water dispenser",
        "water dispensers",
        "water purifier",
        "water purifiers",
        "water heater",
        "water heaters",
        "hot water",
    ],
    "Home Care": [
        "vacuum cleaner",
        "vacuum cleaners",
        "iron",
        "ironing",
        "steam iron",
        "steam irons",
        "cleaning appliance",
        "home care",
    ],
    "Power & Backup": [
        "inverter",
        "inverters",
        "solar",
        "solar system",
        "solar systems",
        "backup power",
        "power backup",
        "generator",
        "generators",
        "battery",
        "batteries",
    ],
}


KENYA_TERMS = [
    "kenya",
    "kenyan",
    "nairobi",
    "mombasa",
    "kisumu",
    "nakuru",
    "eldoret",
    "thika",
    "machakos",
    "meru",
    "kiambu",
    "kakamega",
    "nyeri",
    "naivasha",
    "kitengela",
    "ruiru",
    "westlands",
    "sarit",
    "lavington",
    "industrial area",
    "east africa",
    "east african",
]


KENYAN_PUBLISHERS = [
    "KBC",
    "KBC Digital",
    "Citizen",
    "Citizen Digital",
    "NTV",
    "Nation",
    "Daily Nation",
    "The Standard",
    "Standard Media",
    "The Star",
    "Business Daily",
    "Business Daily Africa",
    "Capital FM",
    "Capital Business",
    "TechTrendsKE",
    "tech-ish",
    "Tech-ish",
    "Green Building Africa",
]


NOISE_TERMS = [
    "football",
    "soccer",
    "match report",
    "premier league",
    "champions league",
    "transfer news",
    "celebrity",
    "gossip",
    "entertainment",
    "horoscope",
    "weather forecast",
    "crime",
    "obituary",
]


# ============================================================================
# SEARCH QUERIES
# ============================================================================

BASE_QUERIES = [
    "Kenya home appliances",
    "Kenya home appliances market",
    "Kenya electronics market",
    "Kenya consumer electronics",
    "Kenya appliance industry",
    "Kenya refrigerator market",
    "Kenya washing machine market",
    "Kenya cooker market",
    "Kenya television market",
    "Kenya smart home appliances",
    "Kenya retail appliances",
    "Kenya appliance prices",
    "Kenya appliance sales",
    "Kenya electronics retail",
    "Kenya household appliances",
]


ACTIVITY_QUERIES = [
    "Kenya appliance launch",
    "Kenya appliance launches",
    "Kenya appliance expansion",
    "Kenya appliance partnership",
    "Kenya appliance distribution",
    "Kenya appliance investment",
    "Kenya local assembly appliances",
    "Kenya appliance manufacturing",
    "Kenya appliance promotion",
    "Kenya appliance sale",
    "Kenya electronics launch",
    "Kenya electronics expansion",
    "Kenya electronics investment",
    "Kenya smart home launch",
    "Kenya retail electronics expansion",
]


ENTITY_QUERY_TERMS = [
    "Hotpoint Kenya",
    "Ramtons Kenya",
    "Hisense Kenya",
    "Haier Kenya",
    "Armco Kenya",
    "Bruhm Kenya",
    "K-Elec Kenya",
    "Philips Kenya",
    "TCL Kenya",
    "Samsung Kenya",
    "LG Kenya",
    "Midea Kenya",
    "Moulinex Kenya",
    "Tefal Kenya",
    "Krups Kenya",
    "SCL Kenya",
    "Berklays Kenya",
    "Hypermart Kenya appliances",
    "JTC Kenya appliances",
    "Vision Plus Kenya",
    "Vitron Kenya",
    "Anicuma Traders Limited",
    "Anke Home Appliance Kenya",
    "Rebune Kenya",
    "Jumia Kenya appliances",
    "Kilimall Kenya appliances",
    "Carrefour Kenya appliances",
]


# ============================================================================
# TEXT CLEANING
# ============================================================================

def clean_text(value: Any) -> str:
    """
    Clean extracted publisher text while preserving legitimate punctuation
    and Unicode characters.

    Repairs common UTF-8 / Windows-1252 mojibake without converting valid
    punctuation such as curly apostrophes, en dashes, em dashes or ellipses
    into '?'.
    """
    if value is None:
        return ""

    text = str(value)

    if not text.strip():
        return ""

    stripped = text.strip()

    if stripped.lower().startswith(("http://", "https://")):
        return stripped

    text = html.unescape(text)

    # Repair common UTF-8 bytes incorrectly decoded as Windows-1252.
    if any(marker in text for marker in ("\u00e2", "\u00c2", "\u00e3", "\u00c3")):
        try:
            repaired = text.encode("cp1252").decode("utf-8")
            text = repaired
        except (UnicodeEncodeError, UnicodeDecodeError):
            pass

    text = unicodedata.normalize("NFKC", text)

    mojibake_map = {
        "\u00e2\u0080\u0098": "‘",
        "\u00e2\u0080\u0099": "’",
        "\u00e2\u0080\u009c": "“",
        "\u00e2\u0080\u009d": "”",
        "\u00e2\u0080\u0093": "–",
        "\u00e2\u0080\u0094": "—",
        "\u00e2\u0080\u00a6": "…",
        "\u00c2\u00a0": " ",
        "\u00e2\u20ac": "?",
        "??": "",
    }

    for bad, good in mojibake_map.items():
        text = text.replace(bad, good)

    # Publisher extraction occasionally loses spaces around these words.
    fixes = {
        "Vonhome": "Von home",
        "homeappliances": "home appliances",
        "Homeappliances": "Home appliances",
        "schoolsand": "schools and",
        "businessesand": "businesses and",
        "consumersand": "consumers and",
        "productsand": "products and",
        "peopleand": "people and",
        "theaim": "the aim",
        "thecompany": "the company",
        "themarket": "the market",
        "theproject": "the project",
        "theprogramme": "the programme",
        "theprogram": "the program",
        "EuropeanInvestment": "European Investment",
        "fitnessgoal": "fitness goal",
        "How muchwe": "How much we",
        "roadshowends": "roadshow ends",
        "projecttargets": "project targets",
        "assemblyofVon": "assembly of Von",
        "ofVon": "of Von",
    }

    for bad, good in fixes.items():
        text = text.replace(bad, good)

    text = text.replace("\r\n", "\n").replace("\r", "\n")

    lines: list[str] = []

    for line in text.split("\n"):
        line = re.sub(r"[ \t]+", " ", line).strip()

        if line:
            lines.append(line)
        elif lines and lines[-1] != "":
            lines.append("")

    text = "\n".join(lines)
    text = re.sub(r"\n{3,}", "\n\n", text)

    # Repair only common publisher word-boundary joins.
    # Do not attempt broad dictionary-based word splitting.
    boundary_fixes = {
        "assemblyforms": "assembly forms",
        "targetingto": "targeting to",
        "andSouth": "and South",
        "decadesof": "decades of",
        "consumersgenuinely": "consumers genuinely",
        "andconsumer": "and consumer",
        "VONwas": "VON was",
        "localisingof": "localising of",
        "thingbeautifully": "thing beautifully",
        "startinfluencing": "start influencing",
        "holdingit": "holding it",
        "showingoff": "showing off",
        "Zen Gardenhad": "Zen Garden had",
        "aselected": "a selected",
        "auseful": "a useful",
        "whoselivelihoods": "whose livelihoods",
        "butdoes": "but does",
    }

    for bad, good in boundary_fixes.items():
        text = text.replace(bad, good)

    return text.strip()


def normalize_text(value: Any) -> str:
    text = clean_text(value).lower()

    text = (
        text.replace("’", "'")
        .replace("‘", "'")
        .replace("“", '"')
        .replace("”", '"')
        .replace("–", "-")
        .replace("—", "-")
    )

    text = re.sub(r"\s+", " ", text)

    return text.strip()


def is_article_boilerplate(value: Any) -> bool:
    """
    High-confidence standalone boilerplate detector.

    Deliberately conservative so legitimate article paragraphs are not
    discarded merely because they contain common publishing language.
    """
    text = clean_text(value)

    if not text:
        return True

    text_low = text.lower().strip()

    boilerplate_patterns = [
        r"^go to [a-z0-9.-]+\.[a-z]{2,}\s+for more",
        r"^follow us on ",
        r"^subscribe to ",
        r"^sign up for ",
        r"^send tips to ",
        r"^get the latest .*newsletter",
        r"^don't miss out on ",
        r"^our greenshift forum",
        r"^real .* impact doesn.?t happen in panels alone",

        # Comment / reader-form boilerplate.
        r"^anonymous by default\b",
        r"^leave both blank to stay fully anonymous\b",
        r"^prefer to be recognised\b",
        r"^prefer to be recognized\b",
        r"^add a name or email above\b",
        r"^comments are public\b",
        r"^that looks like a phone number or email\b",
    ]

    return any(
        re.search(pattern, text_low)
        for pattern in boilerplate_patterns
    )


def strip_trailing_article_boilerplate(value: Any) -> str:
    """
    Remove obvious footer/publisher contamination appended to an otherwise
    legitimate article paragraph.

    This operates surgically and keeps the legitimate text before the marker.
    """
    text = clean_text(value)

    if not text:
        return ""

    low = text.lower()

    markers = [
        r"real\s+esg\s+impact\s+doesn.?t\s+happen\s+in\s+panels\s+alone",
        r"go\s+to\s+techtrendske\.co\.ke",
        r"follow\s+us\s+on\s+whatsapp",
        r"send\s+tips\s+to\s+[a-z0-9._%+\-]+@[a-z0-9.\-]+\.[a-z]{2,}",
        r"get\s+the\s+latest\s+.*newsletter",

        # Comment / reader-form boilerplate appended after article content.
        r"both\s+optional\s+and\s+your\s+call\b",
        r"anonymous\s+by\s+default\b",
        r"leave\s+both\s+blank\s+to\s+stay\s+fully\s+anonymous\b",
        r"prefer\s+to\s+be\s+(?:recognised|recognized)\b",
        r"add\s+a\s+name\s+or\s+email\s+above\b",
        r"comments\s+are\s+public\b",
        r"that\s+looks\s+like\s+a\s+phone\s+number\s+or\s+email\b",
    ]

    positions: list[int] = []

    for pattern in markers:
        match = re.search(pattern, low)
        if match:
            positions.append(match.start())

    if positions:
        text = text[: min(positions)].rstrip(" \t\n-–—|")

    return clean_text(text)


# ============================================================================
# URL / NETWORK HELPERS
# ============================================================================

def normalize_url(url: Any) -> str:
    if not url:
        return ""

    url = html.unescape(str(url)).strip()

    if not url:
        return ""

    parsed = urlparse(url)

    if not parsed.scheme:
        return url

    scheme = parsed.scheme.lower()
    netloc = parsed.netloc.lower()

    path = parsed.path or "/"

    normalized = f"{scheme}://{netloc}{path}"

    if parsed.query:
        normalized += f"?{parsed.query}"

    return normalized


def fetch(url: str) -> requests.Response | None:
    if not url:
        return None

    try:
        response = SESSION.get(
            url,
            timeout=REQUEST_TIMEOUT,
            allow_redirects=True,
        )

        response.raise_for_status()

        return response

    except requests.RequestException:
        return None


def term_present(text: Any, term: str) -> bool:
    haystack = normalize_text(text)
    needle = normalize_text(term)

    if not haystack or not needle:
        return False

    return needle in haystack


def matching_terms(text: Any, terms: list[str]) -> list[str]:
    haystack = normalize_text(text)

    if not haystack:
        return []

    return [
        term
        for term in terms
        if normalize_text(term) in haystack
    ]



def find_entities(text: Any) -> list[str]:
    """
    Detect tracked entities using word-boundary matching.

    Short entity names such as SCL must not be detected merely because the
    letters appear inside another word or unrelated publisher text.
    """
    haystack = normalize_text(text)

    if not haystack:
        return []

    matches: list[str] = []

    for entity in TRACKED_ENTITIES:
        normalized_entity = normalize_text(entity)

        if not normalized_entity:
            continue

        pattern = rf"(?<!\w){re.escape(normalized_entity)}(?!\w)"

        if re.search(pattern, haystack, flags=re.IGNORECASE):
            matches.append(entity)

    return matches


def find_products(text: Any) -> list[str]:
    """
    Detect explicit appliance/product signals conservatively.

    Generic technology language, generic household language, and contextual
    words such as "fan" in "Fan Edition" must not create appliance categories.
    """

    haystack = normalize_text(text)

    if not haystack:
        return []

    matches: list[str] = []

    explicit_terms = {
        "Refrigeration": [
            "refrigerator",
            "fridge",
            "freezer",
            "deep freezer",
            "chest freezer",
            "fridge freezer",
            "side by side refrigerator",
            "double door refrigerator",
            "single door refrigerator",
            "bottom mount refrigerator",
            "top mount refrigerator",
        ],

        "Laundry": [
            "washing machine",
            "washer dryer",
            "tumble dryer",
            "laundry machine",
            "laundromat",
        ],

        "Cooking": [
            "cooker",
            "cookers",
            "cooking appliance",
            "cooking appliances",
            "built-in oven",
            "oven",
            "hob",
            "cooktop",
            "gas cooker",
            "electric cooker",
            "microwave oven",
            "microwave",
            "air fryer",
            "rice cooker",
        ],

        "Small Kitchen Appliances": [
            "blender",
            "kettle",
            "electric kettle",
            "toaster",
            "sandwich maker",
            "food processor",
            "juicer",
            "coffee maker",
            "coffee machine",
            "hand mixer",
            "stand mixer",
        ],

        "Cookware": [
            "cookware",
            "saucepan",
            "frying pan",
            "pressure cooker",
            "pot set",
            "pan set",
        ],

        "TV & Audio": [
            "television",
            "smart tv",
            "mini led tv",
            "oled tv",
            "qled tv",
            "led tv",
            "soundbar",
            "speaker system",
            "home audio",
            "audio system",
            "headphones",
            "earbuds",
        ],

        "Air & Climate": [
            "air conditioner",
            "air conditioning",
            "ac unit",
            "split ac",
            "portable air conditioner",
            "ceiling fan",
            "air cooler",
            "air purifier",
            "hvac",
        ],

        "Water": [
            "water dispenser",
            "water purifier",
            "water filter",
            "water heater",
            "instant water heater",
            "geyser",
        ],

        "Home Care & Power": [
            "vacuum cleaner",
            "iron",
            "steam iron",
            "generator",
            "inverter",
            "ups",
            "power backup",
            "solar backup",
        ],
    }

    for category, terms in explicit_terms.items():
        for term in terms:
            normalized_term = normalize_text(term)

            if not normalized_term:
                continue

            pattern = rf"(?<!\w){re.escape(normalized_term)}(?!\w)"

            if re.search(pattern, haystack, flags=re.IGNORECASE):
                matches.append(category)
                break

    # "Fan Edition" is a smartphone/product designation, not an
    # Air & Climate signal. A standalone "fan" is intentionally not
    # treated as an appliance category unless it is explicitly described
    # as a ceiling fan above.
    if re.search(r"\bfan\s+edition\b", haystack, flags=re.IGNORECASE):
        matches = [
            category
            for category in matches
            if category != "Air & Climate"
        ]

    return matches

def parse_datetime(value: Any) -> datetime | None:
    if value is None:
        return None

    if isinstance(value, datetime):
        dt = value
    elif isinstance(value, date):
        dt = datetime.combine(value, datetime.min.time())
    else:
        raw = clean_text(value)

        if not raw:
            return None

        # ISO first.
        try:
            dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except ValueError:
            dt = None

        if dt is None:
            try:
                dt = parsedate_to_datetime(raw)
            except (TypeError, ValueError, OverflowError):
                dt = None

        if dt is None:
            formats = [
                "%Y-%m-%d",
                "%Y-%m-%d %H:%M:%S",
                "%Y-%m-%d %H:%M:%S%z",
                "%d %B %Y",
                "%d %b %Y",
                "%B %d, %Y",
                "%b %d, %Y",
            ]

            for fmt in formats:
                try:
                    dt = datetime.strptime(raw, fmt)
                    break
                except ValueError:
                    continue

    if dt is None:
        return None

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    return dt.astimezone(timezone.utc)


def within_window(value: Any, days: int = WINDOW_DAYS) -> bool:
    dt = parse_datetime(value)

    if dt is None:
        return False

    now = datetime.now(timezone.utc)

    minimum = now - timedelta(days=days)

    return minimum <= dt <= now + timedelta(days=1)


# ============================================================================
# GOOGLE NEWS RSS
# ============================================================================

def google_news_url(query: str) -> str:
    return (
        "https://news.google.com/rss/search?"
        f"q={quote(query)}&hl=en-KE&gl=KE&ceid=KE:en"
    )


def xml_local_name(tag: str) -> str:
    if "}" in tag:
        return tag.rsplit("}", 1)[-1]

    return tag


def xml_child_text(element: ET.Element, name: str) -> str:
    for child in element:
        if xml_local_name(child.tag) == name:
            return clean_text(child.text)

    return ""


def xml_child_attribute(
    element: ET.Element,
    child_name: str,
    attribute_name: str,
) -> str:
    for child in element:
        if xml_local_name(child.tag) == child_name:
            return clean_text(child.attrib.get(attribute_name, ""))

    return ""


def search_google_news(query: str) -> list[dict[str, Any]]:
    url = google_news_url(query)

    response = fetch(url)

    if response is None:
        return []

    try:
        root = ET.fromstring(response.content)
    except ET.ParseError:
        return []

    results: list[dict[str, Any]] = []

    for item in root.iter():
        if xml_local_name(item.tag) != "item":
            continue

        title = xml_child_text(item, "title")
        link = xml_child_text(item, "link")
        description = xml_child_text(item, "description")
        pub_date = xml_child_text(item, "pubDate")
        source_name = xml_child_text(item, "source")
        source_url = xml_child_attribute(item, "source", "url")

        if not title or not link:
            continue

        results.append(
            {
                "query": query,
                "rss_title": title,
                "rss_url": normalize_url(link),
                "rss_description": description,
                "rss_published_date": pub_date,
                "rss_source": source_name,
                "rss_source_url": source_url,
            }
        )

        if len(results) >= MAX_RSS_RESULTS_PER_QUERY:
            break

    return results


# ============================================================================
# ARTICLE URL RESOLUTION
# ============================================================================

BLOCKED_DOMAINS = {
    "news.google.com",
    "google.com",
    "googleusercontent.com",
}


def is_external_url(url: str) -> bool:
    if not url:
        return False

    host = urlparse(url).netloc.lower()

    if not host:
        return False

    return host not in BLOCKED_DOMAINS


def looks_like_article_url(url: str) -> bool:
    if not url:
        return False

    parsed = urlparse(url)

    if not parsed.scheme or not parsed.netloc:
        return False

    path = parsed.path.lower()

    if path in ("", "/"):
        return False

    blocked_extensions = (
        ".jpg",
        ".jpeg",
        ".png",
        ".gif",
        ".webp",
        ".svg",
        ".pdf",
        ".mp4",
        ".mp3",
        ".zip",
    )

    if path.endswith(blocked_extensions):
        return False

    return True


def extract_declared_url(soup: BeautifulSoup) -> str:
    # Canonical.
    canonical = soup.find("link", rel=lambda value: value and "canonical" in value)

    if canonical and canonical.get("href"):
        url = normalize_url(canonical.get("href"))

        if looks_like_article_url(url):
            return url

    # OpenGraph.
    og_url = soup.find("meta", attrs={"property": "og:url"})

    if og_url and og_url.get("content"):
        url = normalize_url(og_url.get("content"))

        if looks_like_article_url(url):
            return url

    return ""



# ============================================================================
# ARTICLE EXTRACTION
# ============================================================================

def _jsonld_objects(value: Any) -> list[dict[str, Any]]:
    """
    Flatten JSON-LD structures into dictionaries.

    Supports:
    - single dictionaries
    - arrays
    - @graph
    """
    objects: list[dict[str, Any]] = []

    if isinstance(value, dict):
        objects.append(value)

        graph = value.get("@graph")

        if isinstance(graph, list):
            for item in graph:
                if isinstance(item, dict):
                    objects.append(item)

    elif isinstance(value, list):
        for item in value:
            if isinstance(item, dict):
                objects.append(item)

                graph = item.get("@graph")

                if isinstance(graph, list):
                    for graph_item in graph:
                        if isinstance(graph_item, dict):
                            objects.append(graph_item)

    return objects


def _jsonld_is_article(obj: dict[str, Any]) -> bool:
    article_type = obj.get("@type")

    if isinstance(article_type, list):
        values = article_type
    else:
        values = [article_type]

    accepted = {
        "article",
        "newsarticle",
        "reportage",
        "blogposting",
    }

    return any(
        isinstance(value, str)
        and value.strip().lower() in accepted
        for value in values
    )


def _extract_jsonld_articles(
    soup: BeautifulSoup,
) -> list[dict[str, Any]]:
    objects: list[dict[str, Any]] = []

    for script in soup.find_all(
        "script",
        attrs={"type": re.compile(r"application/ld\+json", re.I)},
    ):
        raw = script.string or script.get_text()

        raw = raw.strip()

        if not raw:
            continue

        raw = re.sub(r"^\s*<!--", "", raw)
        raw = re.sub(r"-->\s*$", "", raw)

        try:
            parsed = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            continue

        objects.extend(_jsonld_objects(parsed))

    return objects


def _boundary_integrity_score(value: Any) -> float:
    """
    Estimate whether extracted prose has normal word boundaries.

    This is deliberately a scoring function, not a word-repair function.
    We never rewrite text here.

    Strong signals of damaged extraction include:
    - lower-case word immediately followed by Upper-case word
    - common English function words fused to another word
    - unusually long lower-case tokens
    """
    text = clean_text(value)

    if not text:
        return -1000.0

    score = 100.0

    # Camel-case boundary loss:
    #   theGalaxy
    #   SamsungTV
    #   Thewellness
    camel = re.findall(
        r"(?<=[a-z])(?=[A-Z])",
        text,
    )

    score -= len(camel) * 12.0

    # Common English words fused to another word.
    #
    # We deliberately exclude very short words such as "a", "an", "to",
    # "of", "in", "on" because they occur naturally inside legitimate
    # English words.
    boundary_words = [
        "and",
        "the",
        "you",
        "your",
        "our",
        "their",
        "these",
        "those",
        "this",
        "that",
        "with",
        "from",
        "into",
        "for",
        "are",
        "can",
        "will",
        "has",
        "have",
        "was",
        "were",
        "not",
        "but",
        "or",
        "how",
        "all",
    ]

    for word in boundary_words:
        # word + another word
        start_pattern = rf"\b{word}[a-z]{{4,}}\b"

        # another word + word
        end_pattern = rf"\b[a-z]{{4,}}{word}\b"

        score -= len(
            re.findall(start_pattern, text, re.I)
        ) * 8.0

        score -= len(
            re.findall(end_pattern, text, re.I)
        ) * 8.0

    # Long lower-case tokens are a weaker signal.
    #
    # We don't reject them because legitimate English words can be long.
    tokens = re.findall(
        r"\b[A-Za-z]{12,}\b",
        text,
    )

    for token in tokens:
        if len(token) >= 18:
            score -= 3.0
        elif len(token) >= 15:
            score -= 1.0

    return score


def _text_quality_score(value: Any) -> float:
    """
    Score extracted article text.

    Boundary integrity is the strongest signal.
    Article length and paragraph structure are secondary signals.
    """
    text = clean_text(value)

    if not text:
        return -1000.0

    score = _boundary_integrity_score(text)

    length = len(text)

    if length >= 200:
        score += 5.0

    if length >= 500:
        score += 2.0

    if length >= 1000:
        score += 2.0

    paragraph_count = len(
        [
            part
            for part in re.split(r"\n\s*\n", text)
            if part.strip()
        ]
    )

    if paragraph_count >= 2:
        score += min(paragraph_count, 10) * 0.5

    contamination_patterns = [
        r"go\s+to\s+techtrendske\.co\.ke",
        r"follow\s+us\s+on\s+whatsapp",
        r"send\s+tips\s+to\s+",
        r"real\s+esg\s+impact\s+doesn.?t\s+happen",
        r"get\s+the\s+latest\s+.*newsletter",
    ]

    for pattern in contamination_patterns:
        if re.search(pattern, text, re.I):
            score -= 25.0

    return score


def _choose_best_text_candidate(
    candidates: list[str],
    minimum_length: int = 200,
) -> str:
    """
    Select the cleanest article candidate.

    Boundary integrity takes priority over raw length.
    This prevents a longer but structurally damaged JSON-LD candidate
    from overriding a cleaner HTML paragraph extraction.
    """
    cleaned_candidates: list[str] = []

    seen: set[str] = set()

    for candidate in candidates:
        candidate = clean_text(candidate)

        if len(candidate) < minimum_length:
            continue

        normalized = normalize_text(candidate)

        if normalized in seen:
            continue

        seen.add(normalized)

        cleaned_candidates.append(candidate)

    if not cleaned_candidates:
        return ""

    ranked = sorted(
        cleaned_candidates,
        key=lambda item: (
            _boundary_integrity_score(item),
            _text_quality_score(item),
            len(item),
        ),
        reverse=True,
    )

    return ranked[0]


def _clean_article_paragraphs(
    paragraphs: list[str],
) -> str:
    """
    Apply common article-level cleanup without attempting to rewrite
    publisher text.
    """
    cleaned: list[str] = []

    for paragraph in paragraphs:
        paragraph = clean_text(paragraph)

        if not paragraph:
            continue

        paragraph = strip_trailing_article_boilerplate(paragraph)

        if not paragraph:
            continue

        if is_article_boilerplate(paragraph):
            break

        if len(paragraph) < 20:
            continue

        if cleaned:
            if normalize_text(cleaned[-1]) == normalize_text(paragraph):
                continue

        cleaned.append(paragraph)

    # Remove duplicated trailing blocks conservatively.
    for block_size in range(
        min(5, len(cleaned) // 2),
        0,
        -1,
    ):
        if len(cleaned) < block_size * 2:
            continue

        first_block = [
            normalize_text(item)
            for item in cleaned[-block_size * 2 : -block_size]
        ]

        second_block = [
            normalize_text(item)
            for item in cleaned[-block_size:]
        ]

        if first_block == second_block:
            del cleaned[-block_size:]
            break

    return "\n\n".join(cleaned).strip()


def _jsonld_article_body(
    soup: BeautifulSoup,
) -> str:
    """
    Extract candidate articleBody values from JSON-LD.

    JSON-LD is treated as one candidate source rather than automatically
    being considered authoritative. Some publishers emit articleBody text
    with damaged word boundaries.
    """
    candidates: list[str] = []

    for obj in _extract_jsonld_articles(soup):
        if not _jsonld_is_article(obj):
            continue

        article_body = obj.get("articleBody")

        if not isinstance(article_body, str):
            continue

        article_body = clean_text(article_body)

        if len(article_body) < 200:
            continue

        raw_parts = re.split(
            r"\n\s*\n|\n",
            article_body,
        )

        cleaned = _clean_article_paragraphs(raw_parts)

        if len(cleaned) >= 200:
            candidates.append(cleaned)

    return _choose_best_text_candidate(candidates)


def _extract_from_article_tag(
    soup: BeautifulSoup,
) -> str:
    article = soup.find("article")

    if not article:
        return ""

    paragraphs: list[str] = []

    for paragraph_tag in article.find_all("p"):
        paragraph = clean_text(
            paragraph_tag.get_text(" ", strip=True)
        )

        if not paragraph:
            continue

        paragraphs.append(paragraph)

    return _clean_article_paragraphs(paragraphs)


def _extract_from_content_selectors(
    soup: BeautifulSoup,
) -> str:
    selectors = [
        "div.entry-content",
        "div.post-content",
        "div.article-content",
        "div.article-body",
        "div.story-body",
        "div.single-post-content",
        "div.td-post-content",
        "div.elementor-widget-theme-post-content",
        "main article",
        "main .entry-content",
        "main .post-content",
    ]

    candidates: list[str] = []

    for selector in selectors:
        container = soup.select_one(selector)

        if not container:
            continue

        paragraphs: list[str] = []

        for paragraph_tag in container.find_all("p"):
            paragraph = clean_text(
                paragraph_tag.get_text(" ", strip=True)
            )

            if not paragraph:
                continue

            paragraphs.append(paragraph)

        body = _clean_article_paragraphs(paragraphs)

        if len(body) >= 200:
            candidates.append(body)

    return _choose_best_text_candidate(candidates)


def _extract_from_page_paragraphs(
    soup: BeautifulSoup,
) -> str:
    """
    Last-resort paragraph extraction.

    It deliberately excludes obvious site chrome and stops when strong
    publisher/footer contamination is encountered.
    """
    paragraphs: list[str] = []

    for paragraph_tag in soup.find_all("p"):
        paragraph = clean_text(
            paragraph_tag.get_text(" ", strip=True)
        )

        if not paragraph:
            continue

        paragraph = strip_trailing_article_boilerplate(paragraph)

        if not paragraph:
            continue

        if is_article_boilerplate(paragraph):
            break

        if len(paragraph) < 30:
            continue

        if paragraphs:
            if normalize_text(paragraphs[-1]) == normalize_text(paragraph):
                continue

        paragraphs.append(paragraph)

        if len(paragraphs) >= 80:
            break

    return _clean_article_paragraphs(paragraphs)


def _title_quality_score(value: Any) -> float:
    """
    Score a title for extraction quality.

    Titles are short, so the scoring is deliberately conservative.
    """
    title = clean_text(value)

    if not title:
        return -1000.0

    score = 0.0

    if 20 <= len(title) <= 180:
        score += 5.0

    camel_boundary_matches = re.findall(
        r"(?<=[a-z])(?=[A-Z])",
        title,
    )

    score -= len(camel_boundary_matches) * 4.0

    suspicious_patterns = [
        r"\b(?:the|a|an|and|or|to|of|in|on|for|with|from|into|that|how|"
        r"is|are|can|will|you|your|our|their)[a-z]{4,}",
    ]

    for pattern in suspicious_patterns:
        score -= len(
            re.findall(pattern, title)
        ) * 2.0

    if "|" in title:
        score -= 1.0

    return score


def _extract_title(
    soup: BeautifulSoup,
) -> str:
    candidates: list[str] = []

    og_title = soup.find(
        "meta",
        attrs={"property": "og:title"},
    )

    if og_title and og_title.get("content"):
        candidates.append(
            clean_text(og_title.get("content"))
        )

    twitter_title = soup.find(
        "meta",
        attrs={"name": "twitter:title"},
    )

    if twitter_title and twitter_title.get("content"):
        candidates.append(
            clean_text(twitter_title.get("content"))
        )

    h1 = soup.find("h1")

    if h1:
        candidates.append(
            clean_text(
                h1.get_text(" ", strip=True)
            )
        )

    if soup.title:
        candidates.append(
            clean_text(
                soup.title.get_text(" ", strip=True)
            )
        )

    candidates = [
        candidate
        for candidate in candidates
        if candidate and len(candidate) >= 5
    ]

    if not candidates:
        return ""

    return max(
        candidates,
        key=lambda item: (
            _title_quality_score(item),
            len(item),
        ),
    )


def _extract_published_date(
    soup: BeautifulSoup,
) -> str:
    candidates: list[str] = []

    meta_names = [
        "article:published_time",
        "datePublished",
        "publishdate",
        "pubdate",
        "date",
        "dc.date",
        "dc.date.issued",
    ]

    for name in meta_names:
        tag = soup.find(
            "meta",
            attrs={"property": name},
        )

        if not tag:
            tag = soup.find(
                "meta",
                attrs={"name": name},
            )

        if tag and tag.get("content"):
            candidates.append(
                tag.get("content")
            )

    for obj in _extract_jsonld_articles(soup):
        value = obj.get("datePublished")

        if isinstance(value, str):
            candidates.append(value)

    for candidate in candidates:
        dt = parse_datetime(candidate)

        if dt:
            return dt.isoformat()

    return ""


def _extract_publisher(
    soup: BeautifulSoup,
    url: str,
) -> str:
    publisher_meta = soup.find(
        "meta",
        attrs={"property": "og:site_name"},
    )

    if publisher_meta and publisher_meta.get("content"):
        return clean_text(
            publisher_meta.get("content")
        )

    publisher_meta = soup.find(
        "meta",
        attrs={"name": "application-name"},
    )

    if publisher_meta and publisher_meta.get("content"):
        return clean_text(
            publisher_meta.get("content")
        )

    host = urlparse(url).netloc.lower()

    if host.startswith("www."):
        host = host[4:]

    return host


def fetch_article(
    url: str,
) -> dict[str, Any]:
    """
    Fetch and extract one publisher article.

    Extraction sources:
        1. JSON-LD articleBody
        2. <article>
        3. known article-content selectors
        4. page <p> fallback

    Unlike the previous implementation, JSON-LD is not automatically
    preferred merely because it is long enough. Candidate quality is
    evaluated so malformed publisher JSON-LD does not override cleaner
    HTML article text.

    JSON-LD is extracted before scripts are removed.
    """
    result: dict[str, Any] = {
        "title": "",
        "body": "",
        "published_date": "",
        "canonical_url": normalize_url(url),
        "publisher": "",
        "error": "",
    }

    if not url:
        result["error"] = "EMPTY_URL"
        return result

    try:
        response = SESSION.get(
            url,
            timeout=REQUEST_TIMEOUT,
            allow_redirects=True,
        )
        response.raise_for_status()

    except requests.exceptions.Timeout:
        result["error"] = "TIMEOUT"
        return result

    except requests.RequestException as exc:
        result["error"] = f"REQUEST_ERROR: {exc}"
        return result

    except Exception as exc:
        result["error"] = f"FETCH_ERROR: {exc}"
        return result

    final_url = normalize_url(response.url)

    if final_url:
        result["canonical_url"] = final_url

    try:
        soup = BeautifulSoup(
            response.content,
            "html.parser",
        )

    except Exception as exc:
        result["error"] = f"HTML_PARSE_ERROR: {exc}"
        return result

    result["publisher"] = _extract_publisher(
        soup,
        final_url or url,
    )

    result["title"] = _extract_title(soup)

    result["published_date"] = _extract_published_date(soup)

    declared_url = extract_declared_url(soup)

    if declared_url:
        result["canonical_url"] = declared_url

    # ---------------------------------------------------------------
    # Extract all article candidates BEFORE destructive page cleanup.
    # ---------------------------------------------------------------

    jsonld_body = _jsonld_article_body(soup)

    article_body = _extract_from_article_tag(soup)

    selector_body = _extract_from_content_selectors(soup)

    paragraph_body = _extract_from_page_paragraphs(soup)

    # ---------------------------------------------------------------
    # Now remove page chrome.
    # ---------------------------------------------------------------

    for tag_name in [
        "style",
        "noscript",
        "svg",
        "nav",
        "footer",
        "header",
        "form",
        "iframe",
        "aside",
    ]:
        for tag in soup.find_all(tag_name):
            tag.decompose()

    for script in soup.find_all("script"):
        script.decompose()

    # ---------------------------------------------------------------
    # Choose the best extraction candidate.
    #
    # HTML candidates are deliberately allowed to compete with JSON-LD.
    # This is the key correction for publishers whose JSON-LD loses
    # word boundaries.
    # ---------------------------------------------------------------

    candidates = [
        jsonld_body,
        article_body,
        selector_body,
        paragraph_body,
    ]

    body = _choose_best_text_candidate(
        candidates,
        minimum_length=200,
    )

    # ---------------------------------------------------------------
    # Final cleanup.
    # ---------------------------------------------------------------

    body_parts: list[str] = []

    for paragraph in body.split("\n\n"):
        paragraph = clean_text(paragraph)

        if not paragraph:
            continue

        paragraph = strip_trailing_article_boilerplate(
            paragraph
        )

        if not paragraph:
            continue

        if is_article_boilerplate(paragraph):
            break

        if len(paragraph) < 20:
            continue

        normalized = normalize_text(paragraph)

        if body_parts:
            if normalize_text(body_parts[-1]) == normalized:
                continue

        body_parts.append(paragraph)

    # Final conservative duplicate-block removal.
    for block_size in range(
        min(5, len(body_parts) // 2),
        0,
        -1,
    ):
        if len(body_parts) < block_size * 2:
            continue

        left = [
            normalize_text(x)
            for x in body_parts[-block_size * 2 : -block_size]
        ]

        right = [
            normalize_text(x)
            for x in body_parts[-block_size:]
        ]

        if left == right:
            del body_parts[-block_size:]
            break

    result["body"] = "\n\n".join(
        body_parts
    ).strip()

    return result


def resolve_google_item(candidate: dict[str, Any]) -> dict[str, Any]:
    rss_url = candidate.get("rss_url", "")

    resolved_url = rss_url

    # google_news RSS normally points to a Google redirect URL.
    if gnewsdecoder is not None and rss_url:
        try:
            decoded = gnewsdecoder(rss_url)

            if isinstance(decoded, dict):
                decoded_url = (
                    decoded.get("decoded_url")
                    or decoded.get("url")
                    or decoded.get("link")
                )

                if decoded_url:
                    resolved_url = normalize_url(decoded_url)

            elif isinstance(decoded, str):
                resolved_url = normalize_url(decoded)

        except Exception:
            pass

    article = fetch_article(resolved_url)

    candidate["resolved_url"] = resolved_url
    candidate["article"] = article

    return candidate


# ============================================================================
# DISCOVERY
# ============================================================================

def build_queries() -> list[str]:
    queries: list[str] = []

    for query in BASE_QUERIES:
        if query not in queries:
            queries.append(query)

    for query in ACTIVITY_QUERIES:
        if query not in queries:
            queries.append(query)

    for query in ENTITY_QUERY_TERMS:
        if query not in queries:
            queries.append(query)

    return queries[:MAX_RSS_QUERIES]


def collect_candidates() -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []

    for index, query in enumerate(build_queries(), start=1):
        print(
            f"[DISCOVERY {index}] Google News query: {query}",
            flush=True,
        )

        results = search_google_news(query)

        candidates.extend(results)

        if REQUEST_DELAY:
            time.sleep(REQUEST_DELAY)

    return candidates


# ============================================================================
# CANDIDATE PRIORITISATION
# ============================================================================

def candidate_kenya_relevance(candidate: dict[str, Any]) -> int:
    text = " ".join(
        [
            candidate.get("rss_title", ""),
            candidate.get("rss_description", ""),
            candidate.get("rss_source", ""),
        ]
    )

    matches = matching_terms(text, KENYA_TERMS)

    return len(matches)


def score_candidate(candidate: dict[str, Any]) -> int:
    title = candidate.get("rss_title", "")
    description = candidate.get("rss_description", "")

    text = " ".join([title, description])

    score = 0

    score += candidate_kenya_relevance(candidate) * 5

    entities = find_entities(text)
    score += len(entities) * 10

    products = find_products(text)
    score += len(products) * 3

    source = normalize_text(candidate.get("rss_source", ""))

    if any(
        normalize_text(publisher) in source
        for publisher in KENYAN_PUBLISHERS
    ):
        score += 8

    if any(
        normalize_text(term) in normalize_text(text)
        for term in [
            "launch",
            "launched",
            "assembly",
            "investment",
            "expansion",
            "partnership",
            "distribution",
            "market",
            "sales",
            "promotion",
        ]
    ):
        score += 5

    published = parse_datetime(
        candidate.get("rss_published_date")
    )

    if published:
        age = (
            datetime.now(timezone.utc) - published
        ).total_seconds() / 86400

        if age <= 2:
            score += 5
        elif age <= 7:
            score += 3

    return score


def prioritize_candidates(
    candidates: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    deduped: dict[str, dict[str, Any]] = {}

    stale = 0

    for candidate in candidates:
        rss_pub = candidate.get("rss_published_date")

        if rss_pub and not within_window(rss_pub, WINDOW_DAYS):
            stale += 1  # DROP[rssdate]
            continue

        url = normalize_url(candidate.get("rss_url", ""))

        if not url:
            continue

        if url not in deduped:
            candidate["priority_score"] = score_candidate(candidate)
            deduped[url] = candidate
        else:
            existing = deduped[url]

            if score_candidate(candidate) > score_candidate(existing):
                candidate["priority_score"] = score_candidate(candidate)
                deduped[url] = candidate

    print(f"PRE-FILTER: {stale} candidates outside window removed before ranking", flush=True)

    ordered = sorted(
        deduped.values(),
        key=lambda item: (
            item.get("priority_score", 0),
            candidate_kenya_relevance(item),
        ),
        reverse=True,
    )

    return ordered[:MAX_RESOLUTION_CANDIDATES]


# ============================================================================
# RELEVANCE / NOISE
# ============================================================================

def kenya_relevance(
    title: str,
    body: str,
    entities: list[str],
) -> tuple[bool, str]:
    text = normalize_text(
        f"{title} {body}"
    )

    kenya_matches = matching_terms(
        text,
        KENYA_TERMS,
    )

    entity_matches = entities

    if kenya_matches:
        return True, "KENYA_MARKET_REFERENCE"

    if entity_matches:
        return True, "TRACKED_ENTITY_WITH_MARKET_ACTIVITY"

    return False, "NO_KENYA_OR_TRACKED_ENTITY_SIGNAL"


def noise_article(title: str, body: str) -> bool:
    text = normalize_text(
        f"{title} {body}"
    )

    matches = matching_terms(
        text,
        NOISE_TERMS,
    )

    if not matches:
        return False

    # A noise word alone should not automatically reject a market article.
    market_signals = (
        find_entities(text)
        or find_products(text)
        or matching_terms(text, KENYA_TERMS)
    )

    return not bool(market_signals)


# ============================================================================
# CLASSIFICATION
# ============================================================================


def classify_news_category(
    title: str,
    body: str,
    entities: list[str],
    products: list[str],
) -> tuple[str, list[str]]:
    """
    Classify News Intelligence using subject-level evidence.

    Product/category assignment is intentionally conservative.

    Strong evidence:
        1. Headline
        2. Opening article text / lead

    Weak evidence:
        - Product mentions deep in the article body

    Deep-body mentions must not automatically create an appliance
    category.

    Return contract remains:
        (news_type, products)
    """

    title_text = normalize_text(title or "")
    body_text = normalize_text(body or "")

    # ---------------------------------------------------------------
    # 1. SUBJECT-LEVEL TEXT
    # ---------------------------------------------------------------

    # Headline is strongest.
    # Only the opening 800 characters are secondary evidence.
    # Deep article content is deliberately excluded from automatic
    # product/category assignment.
    lead_text = body_text[:800]

    subject_text = " ".join(
        part for part in [title_text, lead_text] if part
    ).strip()

    # ---------------------------------------------------------------
    # 2. PRODUCT/CATEGORY SIGNALS
    # ---------------------------------------------------------------

    # Headline evidence is always allowed.
    title_products = find_products(title_text)

    # Lead evidence is only allowed to supplement a tracked-entity
    # story. This prevents generic market/infrastructure stories from
    # becoming appliance-category stories merely because an appliance
    # is mentioned in the opening paragraph.
    lead_products = []

    if entities:
        lead_products = find_products(lead_text)

    subject_products = list(
        dict.fromkeys(
            title_products + lead_products
        )
    )

    ordered_categories = [
        "Refrigeration",
        "Laundry",
        "Cooking",
        "Small Kitchen Appliances",
        "Cookware",
        "TV & Audio",
        "Air & Climate",
        "Water",
        "Home Care & Power",
    ]

    subject_products = [
        category
        for category in ordered_categories
        if category in subject_products
    ]

    # ---------------------------------------------------------------
    # 3. NEWS-TYPE SIGNALS
    # ---------------------------------------------------------------

    company_signals = [
        "launch",
        "launches",
        "launched",
        "introduces",
        "introduced",
        "unveils",
        "unveiled",
        "expands",
        "expansion",
        "partnership",
        "partners",
        "investment",
        "assembly",
        "manufacturing",
        "factory",
        "store",
        "showroom",
        "roadshow",
        "campaign",
        "promotion",
        "sale",
        "discount",
        "price",
        "pricing",
        "service",
        "digital store",
        "direct to consumer",
        "local plant",
        "local assembly",
        "new facility",
        "new outlet",
        "opens",
        "opened",
        "opening",
        "rolls out",
        "rolled out",
        "introducing",
    ]

    market_signals = [
        "market",
        "industry",
        "demand",
        "consumers",
        "consumer demand",
        "retail",
        "sales",
        "homes",
        "households",
        "electrification",
        "investment",
        "manufacturing",
        "technology",
        "adoption",
        "growth",
    ]

    partnership_signals = [
        "partnership",
        "partnerships",
        "partner",
        "partners",
        "collaboration",
        "collaborates",
        "alliance",
        "joint venture",
        "strategic partnership",
    ]

    expansion_signals = [
        "expands",
        "expanded",
        "expansion",
        "new store",
        "new outlet",
        "new showroom",
        "new facility",
        "new plant",
        "factory",
        "assembly plant",
        "local assembly",
        "manufacturing plant",
        "enters",
        "entered",
        "new market",
        "footprint",
    ]

    distribution_signals = [
        "distributor",
        "distribution",
        "retailer",
        "retail partner",
        "marketplace",
        "digital store",
        "online store",
        "e-commerce",
        "ecommerce",
        "direct to consumer",
        "direct-to-consumer",
        "outlet",
        "sales channel",
        "distribution channel",
    ]

    def contains_signal(signals: list[str]) -> bool:
        for signal in signals:
            normalized_signal = normalize_text(signal)

            if not normalized_signal:
                continue

            pattern = rf"(?<!\w){re.escape(normalized_signal)}(?!\w)"

            if re.search(
                pattern,
                subject_text,
                flags=re.IGNORECASE,
            ):
                return True

        return False

    has_partnership_signal = contains_signal(
        partnership_signals
    )

    has_expansion_signal = contains_signal(
        expansion_signals
    )

    has_distribution_signal = contains_signal(
        distribution_signals
    )

    has_company_signal = contains_signal(
        company_signals
    )

    has_market_signal = contains_signal(
        market_signals
    )

    # ---------------------------------------------------------------
    # 4. NEWS-TYPE PRIORITY
    # ---------------------------------------------------------------

    if entities and has_partnership_signal:
        news_type = "PARTNERSHIP"

    elif entities and has_distribution_signal:
        news_type = "DISTRIBUTION"

    elif entities and has_expansion_signal:
        news_type = "EXPANSION"

    elif entities and has_company_signal:
        news_type = "COMPANY_DEVELOPMENT"

    elif has_market_signal:
        news_type = "MARKET_DEVELOPMENT"

    elif entities:
        news_type = "COMPANY_DEVELOPMENT"

    else:
        news_type = "INDUSTRY_NEWS"

    return news_type, subject_products



def assess_mika_scope(
    title: str,
    body: str,
    entities: list[str],
    products: list[str],
    news_type: str,
) -> tuple[str, str]:
    text = normalize_text(
        f"{title} {body}"
    )

    kenya_terms = matching_terms(
        text,
        KENYA_TERMS,
    )

    if entities and (kenya_terms or products):
        return (
            "IN_SCOPE",
            "TRACKED_ENTITY_WITH_MARKET_ACTIVITY",
        )

    if entities:
        return (
            "IN_SCOPE",
            "TRACKED_ENTITY",
        )

    if products and kenya_terms:
        return (
            "IN_SCOPE",
            "KENYA_APPLIANCE_OR_ELECTRONICS_MARKET",
        )

    if news_type == "MARKET_DEVELOPMENT" and kenya_terms:
        return (
            "REVIEW",
            "KENYA_MARKET_NO_APPLIANCE_SIGNAL",
        )

    if kenya_terms:
        return (
            "REVIEW",
            "KENYA_REFERENCE_REQUIRES_MARKET_RELEVANCE_REVIEW",
        )

    return (
        "OUT_OF_SCOPE",
        "NO_RELEVANT_MIKA_MARKET_SIGNAL",
    )


# ============================================================================
# CONFIDENCE
# ============================================================================


def calculate_confidence(
    title: str,
    body: str,
    published_date: str,
    source: str,
    entities: list[str],
    products: list[str],
    scope_status: str,
) -> str:
    """
    Calculate confidence conservatively.

    HIGH requires strong evidence and should not be awarded merely because
    several fields are populated.
    """

    score = 0

    title_clean = clean_text(title)
    body_clean = clean_text(body)
    source_clean = clean_text(source)

    if title_clean:
        score += 1

    body_length = len(body_clean)

    if body_length >= 1000:
        score += 2
    elif body_length >= 500:
        score += 1

    if published_date:
        score += 1

    if source_clean.startswith(("http://", "https://")):
        score += 1

    if entities:
        score += 2

    if products:
        score += 1

    if scope_status == "IN_SCOPE":
        score += 1
    elif scope_status == "REVIEW":
        score -= 1

    # HIGH requires:
    # - substantial body
    # - verified URL
    # - tracked entity or explicit product signal
    # - confirmed in-scope status
    if (
        score >= 9
        and body_length >= 500
        and source_clean.startswith(("http://", "https://"))
        and (entities or products)
        and scope_status == "IN_SCOPE"
    ):
        return "HIGH"

    if score >= 6:
        return "MEDIUM"

    return "LOW"

def build_summary(
    title: str,
    body: str,
    entities: list[str],
    products: list[str],
    news_type: str,
) -> str:
    sentences = re.split(
        r"(?<=[.!?])\s+",
        clean_text(body),
    )

    useful: list[str] = []

    for sentence in sentences:
        sentence = clean_text(sentence)

        if len(sentence) < 30:
            continue

        if is_article_boilerplate(sentence):
            break

        useful.append(sentence)

        if len(" ".join(useful)) >= 500:
            break

    summary_body = " ".join(useful).strip()

    if len(summary_body) > 650:
        summary_body = summary_body[:647].rsplit(" ", 1)[0].rstrip(" ,;:-??") + "..."

    entity_text = ", ".join(entities) if entities else "No tracked entity"

    product_text = ", ".join(products) if products else "General market"

    return (
        f"{news_type}: {title}. "
        f"Tracked entity/entities: {entity_text}. "
        f"Product/category signal: {product_text}. "
        f"{summary_body}"
    ).strip()


def build_evidence_text(
    title: str,
    body: str,
) -> str:
    body = clean_text(body)

    if len(body) > 3000:
        body = body[:2997].rstrip() + "..."

    return (
        f"Headline: {title}\n\n"
        f"Article evidence:\n{body}"
    )


def make_article_record(
    candidate: dict[str, Any],
) -> dict[str, Any] | None:
    article = candidate.get("article") or {}

    title = clean_text(
        article.get("title")
        or candidate.get("rss_title")
    )

    body = clean_text(
        article.get("body")
    )

    published_date = (
        article.get("published_date")
        or candidate.get("rss_published_date")
        or ""
    )

    published_dt = parse_datetime(published_date)

    if published_dt:
        published_date = published_dt.date().isoformat()
    else:
        published_date = ""

    canonical_url = normalize_url(
        article.get("canonical_url")
        or candidate.get("resolved_url")
        or candidate.get("rss_url")
    )

    publisher = clean_text(
        article.get("publisher")
        or candidate.get("rss_source")
    )

    if not title:
        return None

    if not body:
        return None

    entities = find_entities(
        f"{title} {body}"
    )

    # Product categories are determined later by
    # classify_news_category() using headline + article lead.
    #
    # Do not scan the entire article body here because incidental
    # product mentions deep in the article must not become categories.
    products = []

    relevant, relevance_reason = kenya_relevance(
        title,
        body,
        entities,
    )

    if noise_article(title, body):
        return None

    if not relevant:
        return {
            "news_id": hashlib.sha1(
                canonical_url.encode("utf-8")
            ).hexdigest()[:16],
            "scope_status": "OUT_OF_SCOPE",
            "scope_reason": relevance_reason,
            "headline": title,
            "entities": entities,
            "category": "; ".join(products),
            "news_type": "INDUSTRY_NEWS",
            "publisher": publisher,
            "published_date": published_date,
            "observed_date": datetime.now(
                timezone.utc
            ).date().isoformat(),
            "confidence": "LOW",
            "evidence_status": "ARTICLE_FETCHED",
            "source_url": canonical_url,
            "summary": build_summary(
                title,
                body,
                entities,
                products,
                "INDUSTRY_NEWS",
            ),
            "evidence_text": build_evidence_text(
                title,
                body,
            ),
        }

    news_type, products = classify_news_category(
        title,
        body,
        entities,
        products,
    )

    scope_status, scope_reason = assess_mika_scope(
        title,
        body,
        entities,
        products,
        news_type,
    )

    confidence = calculate_confidence(
        title,
        body,
        published_date,
        publisher,
        entities,
        products,
        scope_status,
    )

    news_id_source = (
        canonical_url
        or f"{title}|{publisher}|{published_date}"
    )

    news_id = hashlib.sha1(
        news_id_source.encode("utf-8")
    ).hexdigest()[:16]

    return {
        "news_id": news_id,
        "scope_status": scope_status,
        "scope_reason": scope_reason,
        "headline": title,
        "entities": entities,
        "category": "; ".join(products),
        "news_type": news_type,
        "publisher": publisher,
        "published_date": published_date,
        "observed_date": datetime.now(
            timezone.utc
        ).date().isoformat(),
        "confidence": confidence,
        "evidence_status": "ARTICLE_FETCHED",
        "source_url": canonical_url,
        "summary": build_summary(
            title,
            body,
            entities,
            products,
            news_type,
        ),
        "evidence_text": build_evidence_text(
            title,
            body,
        ),
    }


# ============================================================================
# DEDUPLICATION
# ============================================================================

def deduplicate_records(
    records: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    unique: dict[str, dict[str, Any]] = {}

    for record in records:
        source_url = normalize_url(
            record.get("source_url", "")
        )

        headline = normalize_text(
            record.get("headline", "")
        )

        if source_url:
            key = source_url
        else:
            key = hashlib.sha1(
                headline.encode("utf-8")
            ).hexdigest()

        existing = unique.get(key)

        if existing is None:
            unique[key] = record
            continue

        # Keep the richer evidence record.
        existing_body_length = len(
            existing.get("evidence_text", "")
        )

        current_body_length = len(
            record.get("evidence_text", "")
        )

        if current_body_length > existing_body_length:
            unique[key] = record

    return list(unique.values())


# ============================================================================
# OUTPUT
# ============================================================================

CSV_FIELDS = [
    "news_id",
    "scope_status",
    "scope_reason",
    "headline",
    "entities",
    "category",
    "news_type",
    "publisher",
    "published_date",
    "observed_date",
    "confidence",
    "evidence_status",
    "source_url",
    "summary",
    "evidence_text",
]


def write_csv(records: list[dict[str, Any]]) -> None:
    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    with CSV_OUTPUT.open(
        "w",
        newline="",
        encoding="utf-8-sig",
    ) as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=CSV_FIELDS,
            extrasaction="ignore",
        )

        writer.writeheader()

        for record in records:
            row = dict(record)

            row["entities"] = "; ".join(
                row.get("entities", [])
            )

            writer.writerow(row)


def write_json(records: list[dict[str, Any]]) -> None:
    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    with JSON_OUTPUT.open(
        "w",
        encoding="utf-8",
    ) as handle:
        json.dump(
            records,
            handle,
            indent=2,
            ensure_ascii=False,
        )


def write_summary(records: list[dict[str, Any]]) -> None:
    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    in_scope = [
        record
        for record in records
        if record.get("scope_status") == "IN_SCOPE"
    ]

    review = [
        record
        for record in records
        if record.get("scope_status") == "REVIEW"
    ]

    out_of_scope = [
        record
        for record in records
        if record.get("scope_status") == "OUT_OF_SCOPE"
    ]

    confidence_counts = Counter(
        record.get("confidence", "UNKNOWN")
        for record in records
    )

    category_counts = Counter(
        record.get("news_type", "UNKNOWN")
        for record in records
    )

    lines: list[str] = []

    lines.append("MIKA CI - NEWS INTELLIGENCE PREVIEW")
    lines.append("=" * 78)
    lines.append("")
    lines.append(
        f"Generated: "
        f"{datetime.now(timezone.utc).isoformat()}"
    )
    lines.append(
        f"Window: previous {WINDOW_DAYS} days"
    )
    lines.append(
        "Database writes: DISABLED"
    )
    lines.append("")
    lines.append("RESULTS")
    lines.append("-" * 78)
    lines.append(
        f"Total records: {len(records)}"
    )
    lines.append(
        f"IN_SCOPE: {len(in_scope)}"
    )
    lines.append(
        f"REVIEW: {len(review)}"
    )
    lines.append(
        f"OUT_OF_SCOPE: {len(out_of_scope)}"
    )
    lines.append("")
    lines.append("CONFIDENCE")
    lines.append("-" * 78)

    for key in ("HIGH", "MEDIUM", "LOW"):
        lines.append(
            f"{key}: {confidence_counts.get(key, 0)}"
        )

    lines.append("")
    lines.append("NEWS TYPES")
    lines.append("-" * 78)

    for category, count in category_counts.most_common():
        lines.append(
            f"{category}: {count}"
        )

    lines.append("")
    lines.append("IN-SCOPE NEWS")
    lines.append("-" * 78)

    if not in_scope:
        lines.append("No IN_SCOPE news records.")

    for record in in_scope:
        lines.append(
            f"[{record.get('confidence')}] "
            f"{record.get('published_date') or 'NO DATE'} | "
            f"{record.get('publisher') or 'UNKNOWN'}"
        )
        lines.append(
            record.get("headline", "")
        )
        lines.append(
            f"Entities: "
            f"{', '.join(record.get('entities', [])) or 'None'}"
        )
        lines.append(
            f"Category: "
            f"{record.get('category') or 'General market'}"
        )
        lines.append(
            f"News type: "
            f"{record.get('news_type')}"
        )
        lines.append(
            f"Scope reason: "
            f"{record.get('scope_reason')}"
        )
        lines.append(
            f"Source: "
            f"{record.get('source_url')}"
        )
        lines.append("")

    lines.append("REVIEW")
    lines.append("-" * 78)

    if not review:
        lines.append("No REVIEW records.")

    for record in review:
        lines.append(
            f"{record.get('headline')}"
        )
        lines.append(
            f"Reason: {record.get('scope_reason')}"
        )
        lines.append(
            f"Source: {record.get('source_url')}"
        )
        lines.append("")

    lines.append("END OF PREVIEW")
    lines.append("=" * 78)

    SUMMARY_OUTPUT.write_text(
        "\n".join(lines),
        encoding="utf-8",
    )


# ============================================================================
# MAIN PIPELINE
# ============================================================================

def main() -> int:
    print("=" * 78)
    print("MIKA CI - NEWS INTELLIGENCE PREVIEW")
    print("=" * 78)
    print("")
    print(f"Project root: {PROJECT_ROOT}")
    print(f"Output directory: {OUTPUT_DIR}")
    print(f"Window: previous {WINDOW_DAYS} days")
    print("SQLite writes: DISABLED")
    print("")

    # ------------------------------------------------------------------
    # Discovery
    # ------------------------------------------------------------------
    candidates = collect_candidates()

    print("")
    print(
        f"DISCOVERY COMPLETE: {len(candidates)} raw candidates"
    )

    # ------------------------------------------------------------------
    # Prioritisation
    # ------------------------------------------------------------------
    prioritized = prioritize_candidates(
        candidates
    )

    print(
        f"PRIORITIZED: {len(prioritized)} candidates"
    )

    # ------------------------------------------------------------------
    # Resolve + validate
    # ------------------------------------------------------------------
    records: list[dict[str, Any]] = []

    for index, candidate in enumerate(
        prioritized,
        start=1,
    ):
        title = candidate.get(
            "rss_title",
            "",
        )

        print(
            f"[RESOLVE {index}/{len(prioritized)}] "
            f"{title}",
            flush=True,
        )

        resolved = resolve_google_item(
            candidate
        )

        article = resolved.get("article") or {}

        published = (
            article.get("published_date")
            or candidate.get("rss_published_date")
            or ""
        )

        if published and not within_window(
            published,
            WINDOW_DAYS,
        ):
            print(f"    -> DROP[window] published={published}", flush=True)
            continue

        if not article.get("body"):
            why = resolved.get("error") or article.get("error") or "no body"
            print(f"    -> DROP[nobody] {why}", flush=True)
            continue

        record = make_article_record(
            resolved
        )

        if record is None:
            print("    -> DROP[record] make_article_record returned None", flush=True)
            continue

        print("    -> KEEP", flush=True)

        records.append(record)

        if len(records) >= MAX_ACCEPTED_ARTICLES:
            break

        if REQUEST_DELAY:
            time.sleep(REQUEST_DELAY)

    # ------------------------------------------------------------------
    # Deduplicate
    # ------------------------------------------------------------------
    records = deduplicate_records(
        records
    )

    # ------------------------------------------------------------------
    # Sort
    # ------------------------------------------------------------------
    records.sort(
        key=lambda record: (
            record.get("scope_status") == "IN_SCOPE",
            record.get("published_date") or "",
            record.get("confidence") == "HIGH",
            record.get("confidence") == "MEDIUM",
        ),
        reverse=True,
    )

    records = records[:MAX_ACCEPTED_ARTICLES]

    # ------------------------------------------------------------------
    # Preview outputs
    # ------------------------------------------------------------------
    write_csv(records)
    write_json(records)
    write_summary(records)

    # ------------------------------------------------------------------
    # Console summary
    # ------------------------------------------------------------------
    in_scope = sum(
        1
        for record in records
        if record.get("scope_status") == "IN_SCOPE"
    )

    review = sum(
        1
        for record in records
        if record.get("scope_status") == "REVIEW"
    )

    out_of_scope = sum(
        1
        for record in records
        if record.get("scope_status") == "OUT_OF_SCOPE"
    )

    print("")
    print("=" * 78)
    print("NEWS INTELLIGENCE PREVIEW COMPLETE")
    print("=" * 78)
    print(
        f"Total records : {len(records)}"
    )
    print(
        f"IN_SCOPE      : {in_scope}"
    )
    print(
        f"REVIEW        : {review}"
    )
    print(
        f"OUT_OF_SCOPE  : {out_of_scope}"
    )
    print("")
    print(f"CSV  : {CSV_OUTPUT}")
    print(f"JSON : {JSON_OUTPUT}")
    print(f"TXT  : {SUMMARY_OUTPUT}")
    print("")
    print("SQLite writes: DISABLED")
    print("=" * 78)

    return 0


if __name__ == "__main__":
    sys.exit(main())