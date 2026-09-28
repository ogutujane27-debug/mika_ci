from datetime import datetime, timedelta, timezone
from urllib.parse import urljoin
import json
import re

import requests
from bs4 import BeautifulSoup


# ============================================================================
# CONFIGURATION
# ============================================================================

NEWS_WINDOW_DAYS = 7
MAX_ARTICLES_PER_SOURCE = 10

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0 Safari/537.36"
    )
}

REQUEST_TIMEOUT = 30


NEWS_SOURCES = [
    {
        "name": "Citizen Digital",
        "url": "https://www.citizen.digital/",
        "type": "digital news",
    },
    {
        "name": "NTV Kenya",
        "url": "https://ntvkenya.co.ke/business/",
        "type": "business news",
    },
    {
        "name": "Standard Business",
        "url": "https://www.standardmedia.co.ke/business",
        "type": "business news",
    },
    {
        "name": "K24",
        "url": "https://k24.digital/",
        "type": "digital news",
    },
]


TRACKED_BRANDS = [
    "Hotpoint",
    "Ramtons",
    "Hisense",
    "Armco",
    "Haier",
    "LG",
    "Midea",
    "Samsung",
    "TCL",
    "Moulinex",
    "Krups",
    "SCL",
    "Tefal",
    "Berklays",
    "Bruhm",
    "Philips",
    "K-Elec",
    "JTC",
]


CATEGORIES = {
    "Refrigeration": [
        "refrigerator",
        "refrigerators",
        "fridge",
        "fridges",
        "freezer",
        "freezers",
        "chest freezer",
        "display fridge",
        "side by side",
        "bottom mount",
        "top mount",
    ],
    "Cooking": [
        "cooker",
        "cookers",
        "oven",
        "ovens",
        "microwave",
        "microwaves",
        "air fryer",
        "air fryers",
        "stove",
        "stoves",
        "gas burner",
        "gas burners",
        "cooking",
    ],
    "Small Domestic Appliances": [
        "blender",
        "blenders",
        "kettle",
        "kettles",
        "coffee maker",
        "coffee makers",
        "food processor",
        "food processors",
        "iron",
        "irons",
        "vacuum cleaner",
        "vacuum cleaners",
        "fan",
        "fans",
        "heater",
        "heaters",
    ],
    "Laundry": [
        "washing machine",
        "washing machines",
        "washer",
        "washers",
        "dryer",
        "dryers",
    ],
    "Entertainment": [
        "television",
        "televisions",
        "tv",
        "tvs",
        "smart tv",
        "smart tvs",
        "soundbar",
        "soundbars",
        "home theatre",
        "home theater",
    ],
    "Water & Cooling": [
        "water dispenser",
        "water dispensers",
        "air conditioner",
        "air conditioners",
        "cooling appliance",
        "cooling appliances",
    ],
}


MARKET_SIGNALS = [
    "discount",
    "sale",
    "black friday",
    "cashback",
    "warranty",
    "financing",
    "lipa later",
    "instalment",
    "installment",
    "free delivery",
    "bundle",
    "showroom",
    "retailer",
    "retailers",
    "distributor",
    "distributors",
    "new branch",
    "launch",
    "launched",
    "partnership",
    "sponsorship",
    "promotion",
    "offer",
    "campaign",
    "pricing",
    "prices",
    "price",
    "demand",
    "manufacturing",
]


# ============================================================================
# HTTP
# ============================================================================

def fetch(url):
    response = requests.get(
        url,
        headers=HEADERS,
        timeout=(10, 15),
        allow_redirects=True,
    )

    response.raise_for_status()

    return response


# ============================================================================
# TEXT HELPERS
# ============================================================================

def clean_text(node):
    return re.sub(
        r"\s+",
        " ",
        node.get_text(" ", strip=True),
    ).strip()


def normalise_url(base_url, href):
    if not href:
        return None

    href = href.strip()

    if href.startswith("#"):
        return None

    if href.startswith("javascript:"):
        return None

    return urljoin(base_url, href)


# ============================================================================
# URL FILTERING
# ============================================================================

def is_blocked_url(url):
    if not url:
        return True

    lower = url.lower()

    blocked = [
        "/tag/",
        "/tags/",
        "/category/",
        "/categories/",
        "/author/",
        "/authors/",
        "/search",
        "/page/",
        "/feed",
        "/login",
        "/register",
        "/contact",
        "/about",
        "/privacy",
        "/terms",
        "/advertise",
        "/careers",
        "/jobs",
    ]

    return any(
        item in lower
        for item in blocked
    )


def looks_like_article_url(source_name, url):
    if is_blocked_url(url):
        return False

    lower = url.lower()

    if source_name == "Citizen Digital":
        return "/article/" in lower

    if source_name == "NTV Kenya":
        return (
            "/news/" in lower
            or "/business/" in lower
            or "/shows/" in lower
            or "/podcast/" in lower
        )

    if source_name == "Standard Business":
        return "/business/" in lower and "/article/" in lower

    if source_name == "K24":
        return any(
            part in lower
            for part in [
                "/news/",
                "/business/",
                "/lifestyle/",
                "/technology/",
                "/entertainment/",
            ]
        )

    return False


# ============================================================================
# LISTING PAGE
# ============================================================================

def extract_candidate_urls(source_name, listing_url, soup):
    urls = []
    seen = set()

    for link in soup.find_all("a", href=True):
        url = normalise_url(
            listing_url,
            link.get("href"),
        )

        if not url:
            continue

        if url in seen:
            continue

        if not looks_like_article_url(
            source_name,
            url,
        ):
            continue

        title = clean_text(link)

        if len(title) < 20:
            continue

        generic_titles = {
            "business",
            "news",
            "latest news",
            "read more",
            "watch now",
            "share",
            "home",
            "our brands",
            "lifestyle & entertainment",
            "auto news",
            "for sale",
            "for hire",
            "career tips",
        }

        if title.lower() in generic_titles:
            continue

        urls.append(
            {
                "url": url,
                "listing_title": title,
            }
        )

        seen.add(url)

        if len(urls) >= MAX_ARTICLES_PER_SOURCE:
            break

    return urls


# ============================================================================
# JSON-LD
# ============================================================================

def jsonld_objects(soup):
    objects = []

    for script in soup.find_all(
        "script",
        attrs={"type": "application/ld+json"},
    ):
        raw = script.string or script.get_text()

        if not raw:
            continue

        try:
            data = json.loads(raw)
        except Exception:
            continue

        if isinstance(data, list):
            objects.extend(data)
        else:
            objects.append(data)

    return [
        item
        for item in objects
        if isinstance(item, dict)
    ]


def parse_datetime(value):
    if not value:
        return None

    value = str(value).strip()

    if value.endswith("Z"):
        value = value[:-1] + "+00:00"

    try:
        parsed = datetime.fromisoformat(value)

        if parsed.tzinfo is None:
            parsed = parsed.replace(
                tzinfo=timezone.utc
            )

        return parsed

    except ValueError:
        return None


# ============================================================================
# ARTICLE DATE EXTRACTION
# ============================================================================

def extract_published_date(
    source_name,
    soup,
    reference_time,
):
    # ------------------------------------------------------------------------
    # Citizen
    # ------------------------------------------------------------------------

    if source_name == "Citizen Digital":
        tag = soup.find(
            "meta",
            attrs={
                "property": "article:published_time"
            },
        )

        if tag:
            parsed = parse_datetime(
                tag.get("content")
            )

            if parsed:
                return parsed

    # ------------------------------------------------------------------------
    # JSON-LD: NTV / K24 / fallback
    # ------------------------------------------------------------------------

    for item in jsonld_objects(soup):
        parsed = parse_datetime(
            item.get("datePublished")
        )

        if parsed:
            return parsed

    # ------------------------------------------------------------------------
    # Standard visible relative time
    # ------------------------------------------------------------------------

    if source_name == "Standard Business":
        text = clean_text(soup)

        patterns = [
            (
                r"(\d+)\s*m(?:in)?s?\s+ago",
                "minutes",
            ),
            (
                r"(\d+)\s*mins?\s+ago",
                "minutes",
            ),
            (
                r"(\d+)\s*h(?:r|our)s?\s+ago",
                "hours",
            ),
            (
                r"(\d+)\s*hrs?\s+ago",
                "hours",
            ),
            (
                r"(\d+)\s*days?\s+ago",
                "days",
            ),
        ]

        for pattern, unit in patterns:
            match = re.search(
                pattern,
                text,
                re.IGNORECASE,
            )

            if not match:
                continue

            amount = int(match.group(1))

            if unit == "minutes":
                return reference_time - timedelta(
                    minutes=amount
                )

            if unit == "hours":
                return reference_time - timedelta(
                    hours=amount
                )

            if unit == "days":
                return reference_time - timedelta(
                    days=amount
                )

    return None


# ============================================================================
# ARTICLE TITLE
# ============================================================================

def extract_title(soup):
    h1 = soup.find("h1")

    if h1:
        title = clean_text(h1)

        if len(title) >= 5:
            return title

    for item in jsonld_objects(soup):
        headline = item.get("headline")

        if headline:
            return str(headline).strip()

    meta = soup.find(
        "meta",
        attrs={"property": "og:title"},
    )

    if meta:
        content = meta.get("content")

        if content:
            return content.strip()

    return None


# ============================================================================
# ARTICLE BODY
# ============================================================================


def extract_article_text(soup):
    """
    Extract meaningful article text while avoiding navigation,
    footer, related stories, recommendations, ads, and other
    page-wide content.
    """

    # Remove elements that commonly contaminate article text.
    for selector in [
        "script",
        "style",
        "noscript",
        "svg",
        "nav",
        "header",
        "footer",
        "aside",
        "form",
        ".related",
        ".related-articles",
        ".recommended",
        ".recommendations",
        ".sidebar",
        ".comments",
        ".comment-section",
        ".advert",
        ".advertisement",
        ".ads",
        ".social-share",
        ".share-buttons",
    ]:
        for node in soup.select(selector):
            node.decompose()

    # 1. Prefer semantic <article>.
    article = soup.find("article")

    if article:
        text = clean_text(article)

        if len(text) >= 300:
            return text

    # 2. Try known article-content containers.
    selectors = [
        "[class*='article-body']",
        "[class*='article-content']",
        "[class*='article__body']",
        "[class*='article__content']",
        "[class*='entry-content']",
        "[class*='post-content']",
        "[class*='story-body']",
        "[class*='story-content']",
        "[class*='story__body']",
        "[class*='story__content']",
        "[id*='article-body']",
        "[id*='article-content']",
        "[id*='story-body']",
        "[id*='story-content']",
    ]

    candidates = []

    for selector in selectors:
        for node in soup.select(selector):
            text = clean_text(node)

            if len(text) >= 300:
                candidates.append(text)

    if candidates:
        # Prefer the largest substantial article container.
        return max(candidates, key=len)

    # 3. Paragraph-based fallback.
    #
    # This is deliberately NOT clean_text(soup), because that would
    # reintroduce navigation, footer, related stories, etc.
    paragraphs = []

    for paragraph in soup.find_all("p"):
        text = clean_text(paragraph)

        if len(text) >= 40:
            paragraphs.append(text)

    if paragraphs:
        return " ".join(paragraphs)

    return ""


# ============================================================================
# ARTICLE PAGE
# ============================================================================

def fetch_article(source, candidate, reference_time):
    try:
        response = fetch(candidate["url"])

        soup = BeautifulSoup(
            response.text,
            "html.parser",
        )

        title = extract_title(soup)

        if not title:
            title = candidate["listing_title"]

        body = extract_article_text(soup)

        published_date = extract_published_date(
            source["name"],
            soup,
            reference_time,
        )

        combined_text = (
            title
            + " "
            + body
        )

        return {
            "title": title,
            "url": candidate["url"],
            "text": body,
            "published_date": published_date,
            "brands": find_tracked_brands(
                combined_text
            ),
            "categories": find_categories(
                combined_text
            ),
            "signals": find_market_signals(
                combined_text
            ),
            "news_type": classify_news_type(
                combined_text
            ),
        }

    except requests.exceptions.Timeout:
        print(
            f"  TIMEOUT: {candidate['url']}"
        )
        return None

    except requests.exceptions.RequestException as exc:
        print(
            f"  REQUEST ERROR: "
            f"{candidate['url']} -> {exc}"
        )
        return None

    except Exception as exc:
        print(
            f"  ARTICLE ERROR: "
            f"{candidate['url']} -> {exc}"
        )
        return None


# ============================================================================
# DETECTION
# ============================================================================

def find_tracked_brands(text):
    """
    Find tracked competitor/brand names using word boundaries.

    This prevents short/common strings from matching inside unrelated words.
    """
    lower = text.lower()

    found = []

    for brand in TRACKED_BRANDS:
        pattern = r"\b" + re.escape(brand.lower()) + r"\b"

        if re.search(pattern, lower):
            found.append(brand)

    return found


def find_categories(text):
    """
    Detect appliance/electronics categories using word-boundary matching.

    Category detection alone does NOT establish CI relevance.
    """
    lower = text.lower()

    found = []

    for category, keywords in CATEGORIES.items():
        for keyword in keywords:
            pattern = r"\b" + re.escape(keyword.lower()) + r"\b"

            if re.search(pattern, lower):
                found.append(category)
                break

    return found


def find_market_signals(text):
    """
    Detect commercial/market signals with word boundaries.
    """
    lower = text.lower()

    found = []

    for signal in MARKET_SIGNALS:
        pattern = r"\b" + re.escape(signal.lower()) + r"\b"

        if re.search(pattern, lower):
            found.append(signal)

    return found


def classify_news_type(text):
    """
    Classify an article only after it has meaningful market context.
    """

    lower = text.lower()

    if any(
        re.search(
            r"\b" + re.escape(term) + r"\b",
            lower,
        )
        for term in [
            "black friday",
            "discount",
            "sale",
            "promotion",
            "offer",
            "cashback",
        ]
    ):
        return "promotion"

    if any(
        re.search(
            r"\b" + re.escape(term) + r"\b",
            lower,
        )
        for term in [
            "launched",
            "launches",
            "launch",
            "unveiled",
            "introduces",
            "introduced",
            "new product",
        ]
    ):
        return "product launch"

    if any(
        re.search(
            r"\b" + re.escape(term) + r"\b",
            lower,
        )
        for term in [
            "partnership",
            "partnered",
            "agreement",
            "deal",
        ]
    ):
        return "partnership"

    if any(
        re.search(
            r"\b" + re.escape(term) + r"\b",
            lower,
        )
        for term in [
            "branch",
            "showroom",
            "retailer",
            "retail",
            "distributor",
            "distribution",
        ]
    ):
        return "distribution"

    if any(
        re.search(
            r"\b" + re.escape(term) + r"\b",
            lower,
        )
        for term in [
            "manufacturing",
            "factory",
            "production",
        ]
    ):
        return "manufacturing"

    if any(
        re.search(
            r"\b" + re.escape(term) + r"\b",
            lower,
        )
        for term in [
            "price",
            "prices",
            "pricing",
            "cost",
        ]
    ):
        return "pricing"

    return "market development"


def is_ci_relevant(article):
    """
    Determine whether an article contains enough evidence to be treated
    as MIKA competitive intelligence.

    Relevance requires actual market context. Generic words such as
    'sale', 'offer', 'launch', or 'price' are not sufficient on their own.
    """

    title = article.get("title") or ""
    body = article.get("text") or ""

    combined = f"{title} {body}".strip()

    if not combined:
        return False

    brands = article.get("brands") or []
    categories = article.get("categories") or []
    signals = article.get("signals") or []

    # Strong evidence:
    # A tracked competitor/brand is explicitly mentioned.
    if brands:
        return True

    # Category + commercial signal is meaningful market context.
    if categories and signals:
        return True

    # Category + explicit business/product language.
    lower = combined.lower()

    product_context = [
        "appliance",
        "appliances",
        "electronics",
        "television",
        "tv",
        "refrigerator",
        "fridge",
        "freezer",
        "washing machine",
        "microwave",
        "oven",
        "cooker",
        "air conditioner",
        "air conditioner",
        "soundbar",
        "home appliance",
        "consumer electronics",
    ]

    commercial_context = [
        "retailer",
        "retail",
        "manufacturer",
        "distributor",
        "customer",
        "consumer",
        "product",
        "products",
        "market",
        "brand",
        "brands",
    ]

    has_product_context = any(
        re.search(
            r"\b" + re.escape(term) + r"\b",
            lower,
        )
        for term in product_context
    )

    has_commercial_context = any(
        re.search(
            r"\b" + re.escape(term) + r"\b",
            lower,
        )
        for term in commercial_context
    )

    return (
        has_product_context
        and has_commercial_context
    )
    lower = text.lower()

    if any(
        term in lower
        for term in [
            "black friday",
            "discount",
            "sale",
            "promotion",
            "offer",
            "cashback",
        ]
    ):
        return "promotion"

    if any(
        term in lower
        for term in [
            "launched",
            "launches",
            "launch",
            "unveiled",
            "introduces",
            "introduced",
            "new product",
        ]
    ):
        return "product launch"

    if any(
        term in lower
        for term in [
            "partnership",
            "partnered",
            "agreement",
            "deal",
        ]
    ):
        return "partnership"

    if any(
        term in lower
        for term in [
            "branch",
            "showroom",
            "retailer",
            "retail",
            "distributor",
            "distribution",
        ]
    ):
        return "distribution"

    if any(
        term in lower
        for term in [
            "manufacturing",
            "factory",
            "production",
        ]
    ):
        return "manufacturing"

    if any(
        term in lower
        for term in [
            "price",
            "prices",
            "pricing",
            "cost",
        ]
    ):
        return "pricing"

    return "market development"


# ============================================================================
# RECENCY
# ============================================================================

def is_recent(published_date, reference_time):
    if not published_date:
        return False

    cutoff = (
        reference_time
        - timedelta(days=NEWS_WINDOW_DAYS)
    )

    return published_date >= cutoff


# ============================================================================
# SOURCE COLLECTION
# ============================================================================

def collect_source(source):
    reference_time = datetime.now(timezone.utc)

    listing_response = fetch(
        source["url"]
    )

    listing_soup = BeautifulSoup(
        listing_response.text,
        "html.parser",
    )

    candidates = extract_candidate_urls(
        source["name"],
        source["url"],
        listing_soup,
    )

    articles = []

    for candidate in candidates:
        article = fetch_article(
            source,
            candidate,
            reference_time,
        )

        if not article:
            continue

        print()
        print("----- ARTICLE DIAGNOSTIC -----")
        print("Title:", article["title"])
        print("Published:", format_date(article["published_date"]))
        print("Brands:", article["brands"])
        print("Categories:", article["categories"])
        print("Signals:", article["signals"])
        print("News type:", article["news_type"])
        print("CI relevant:", is_ci_relevant(article))
        print(
            "Recent:",
            is_recent(
                article["published_date"],
                reference_time,
            ),
        )
        print("Body characters:", len(article["text"]))

        if not is_ci_relevant(article):
            continue

        if not is_recent(
            article["published_date"],
            reference_time,
        ):
            continue

        articles.append(article)

    return {
        "source": source,
        "candidate_count": len(candidates),
        "article_count": len(articles),
        "articles": articles,
    }


# ============================================================================
# OUTPUT
# ============================================================================

def format_date(value):
    if not value:
        return "UNKNOWN"

    return value.astimezone(
        timezone.utc
    ).strftime(
        "%Y-%m-%d %H:%M UTC"
    )


def print_result(result):
    source = result["source"]

    print()
    print("=" * 78)
    print(source["name"])
    print("=" * 78)

    print(
        "Article URLs found:",
        result["candidate_count"],
    )

    print(
        "Recent CI articles:",
        result["article_count"],
    )

    if not result["articles"]:
        print()
        print("No recent relevant articles found.")
        return

    for number, article in enumerate(
        result["articles"],
        start=1,
    ):
        print()
        print(f"[{number}] {article['title']}")
        print(
            "Published:",
            format_date(
                article["published_date"]
            ),
        )
        print(
            "Brands:",
            ", ".join(article["brands"])
            if article["brands"]
            else "None",
        )
        print(
            "Categories:",
            ", ".join(article["categories"])
            if article["categories"]
            else "None",
        )
        print(
            "Signals:",
            ", ".join(article["signals"])
            if article["signals"]
            else "None",
        )
        print(
            "News type:",
            article["news_type"],
        )
        print(
            "URL:",
            article["url"],
        )


# ============================================================================
# MAIN
# ============================================================================

def main():
    print("=" * 78)
    print(
        "MIKA CI - KENYAN ARTICLE-LEVEL "
        "READ-ONLY EXTRACTION"
    )
    print("=" * 78)

    print(
        f"Window: last {NEWS_WINDOW_DAYS} days"
    )

    print(
        f"Maximum article URLs/source: "
        f"{MAX_ARTICLES_PER_SOURCE}"
    )

    print("Database writes: DISABLED")

    successful = 0

    for source in NEWS_SOURCES:
        try:
            result = collect_source(source)

            print_result(result)

            successful += 1

        except Exception as exc:
            print()
            print("=" * 78)
            print(source["name"])
            print("=" * 78)
            print(
                "SOURCE ERROR:",
                repr(exc),
            )

    print()
    print("=" * 78)
    print("EXTRACTION TEST COMPLETE")
    print("=" * 78)

    print(
        f"Sources successfully fetched: "
        f"{successful}/{len(NEWS_SOURCES)}"
    )

    print("No SQLite findings were created.")


if __name__ == "__main__":
    main()

