import os
import re
import sqlite3
from datetime import date, datetime, timedelta
from pathlib import Path

import requests


# =============================================================================
# CONFIGURATION
# =============================================================================

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "data" / "mika_competitive_intel.db"

WINDOW_DAYS = 7

SOCIALAPIS_API_KEY = os.getenv("SOCIALAPIS_API_KEY")
SOCIALAPIS_BASE_URL = "https://api.socialapis.io"
SOCIALAPIS_POSTS_URL = f"{SOCIALAPIS_BASE_URL}/facebook/pages/posts"

# SocialAPIs currently accepts a maximum of 9 for this endpoint.
SOCIALAPIS_LIMIT = 9

REQUEST_TIMEOUT = 30

BING_API_KEY = os.getenv("BING_SEARCH_API_KEY")

SOCIAL_DOMAINS = {
    "facebook.com",
    "www.facebook.com",
    "instagram.com",
    "www.instagram.com",
}

# Toggle this off once the URL-shape issue is diagnosed and fixed.
DEBUG_SOCIAL_URLS = True


# =============================================================================
# VALIDATION TERMS
# =============================================================================

APPLIANCE_TERMS = [
    "appliance",
    "appliances",
    "fridge",
    "fridges",
    "refrigerator",
    "refrigerators",
    "freezer",
    "freezers",
    "washing machine",
    "washing machines",
    "washer",
    "washers",
    "dryer",
    "dryers",
    "laundry",
    "laundry machine",
    "laundry machines",
    "dishwasher",
    "dishwashers",
    "cooker",
    "cookers",
    "oven",
    "ovens",
    "microwave",
    "microwaves",
    "kettle",
    "kettles",
    "blender",
    "blenders",
    "television",
    "televisions",
    "tv",
    "tvs",
    "smart tv",
    "smart tvs",
    "air conditioner",
    "air conditioners",
    "fan",
    "fans",
    "iron",
    "irons",
    "home electronics",
    "electronics",
]

COMMERCIAL_TERMS = [
    "sale",
    "sales",
    "discount",
    "discounts",
    "offer",
    "offers",
    "promotion",
    "promotions",
    "promo",
    "price",
    "prices",
    "deal",
    "deals",
    "save",
    "saving",
    "savings",
    "off",
    "buy",
    "shop",
    "shopping",
    "purchase",
    "available",
    "availability",
    "showroom",
    "showrooms",
    "visit",
    "financing",
    "finance",
    "business",
    "seminar",
    "event",
    "events",
    "rsvp",
    "upgrade",
    "upgrades",
    "launch",
    "launched",
    "new",
    "limited",
    "campaign",
    "competition",
    "giveaway",
]


SOCIAL_TYPE_TERMS = {
    "promotion": [
        "sale",
        "discount",
        "offer",
        "promotion",
        "promo",
        "deal",
        "save",
        "saving",
        "off",
    ],
    "product": [
        "new product",
        "new model",
        "launch",
        "launched",
        "available",
        "fridge",
        "refrigerator",
        "freezer",
        "cooker",
        "oven",
        "microwave",
        "washing machine",
        "washer",
        "dryer",
        "television",
        "smart tv",
        "air conditioner",
        "electronics",
    ],
    "event": [
        "event",
        "seminar",
        "webinar",
        "expo",
        "rsvp",
        "workshop",
    ],
    "campaign": [
        "campaign",
        "giveaway",
        "competition",
        "contest",
        "financing",
    ],
}


# =============================================================================
# GENERAL HELPERS
# =============================================================================

def clean_text(value):
    if value is None:
        return ""

    text = str(value)
    text = text.replace("\r", " ").replace("\n", " ")
    text = re.sub(r"\s+", " ", text)

    return text.strip()


def clean_metric(value):
    if value is None:
        return None

    if isinstance(value, bool):
        return int(value)

    if isinstance(value, (int, float)):
        return int(value)

    text = clean_text(value)

    if not text:
        return None

    text = text.replace(",", "")

    match = re.search(r"-?\d+", text)

    if not match:
        return None

    try:
        return int(match.group(0))
    except ValueError:
        return None


def current_scan_week():
    return date.today().strftime("%G-W%V")


def parse_date(value):
    if value is None:
        return None

    text = clean_text(value)

    if not text:
        return None

    try:
        normalized = text.replace("Z", "+00:00")
        parsed = datetime.fromisoformat(normalized)

        return parsed.date().isoformat()

    except ValueError:
        pass

    match = re.search(r"\d{4}-\d{2}-\d{2}", text)

    if match:
        return match.group(0)

    return None


def is_within_window(published_date):
    if not published_date:
        return False

    try:
        published = date.fromisoformat(published_date)
    except ValueError:
        return False

    minimum_date = date.today() - timedelta(days=WINDOW_DAYS)

    return published >= minimum_date


def domain_allowed(url):
    if not url:
        return False

    url_lower = url.lower()

    return any(
        domain in url_lower
        for domain in SOCIAL_DOMAINS
    )


def contains_any(text, terms):
    text_lower = clean_text(text).lower()

    return any(
        term.lower() in text_lower
        for term in terms
    )


def classify_social_type(text):
    text_lower = clean_text(text).lower()

    for social_type, terms in SOCIAL_TYPE_TERMS.items():

        if any(
            term.lower() in text_lower
            for term in terms
        ):
            return social_type

    return "activity"


def classify_social_product_focus(text):
    """
    Identify a product/category focus from social evidence.

    Conservative by design:
    - returns a CI category only when the post text contains
      a recognizable product/category signal
    - returns None when the evidence is too generic
    """
    text_lower = clean_text(text).lower()

    category_terms = {
        "Refrigeration": [
            "fridge",
            "refrigerator",
            "freezer",
            "double door",
            "side by side",
            "chest freezer",
            "upright freezer",
        ],
        "Laundry": [
            "washing machine",
            "washer",
            "dryer",
            "twin tub",
            "front load",
            "top load",
        ],
        "Cooking": [
            "cooker",
            "oven",
            "gas cooker",
            "gas stove",
            "electric cooker",
            "microwave",
            "pressure cooker",
            "air fryer",
            "hot plate",
        ],
        "Small Kitchen Appliances": [
            "blender",
            "kettle",
            "toaster",
            "sandwich maker",
            "coffee maker",
            "juicer",
            "food processor",
            "mixer",
        ],
        "TV & Audio": [
            "television",
            "tv",
            "smart tv",
            "qled",
            "oled",
            "soundbar",
            "speaker",
            "home theatre",
        ],
        "Air & Climate": [
            "air conditioner",
            "air conditioning",
            "ac unit",
            "fan",
            "air cooler",
        ],
        "Water": [
            "water heater",
            "water dispenser",
            "water purifier",
        ],
        "Home Care & Power": [
            "vacuum cleaner",
            "iron",
            "generator",
            "power backup",
            "inverter",
        ],
        "Cookware": [
            "cookware",
            "frying pan",
            "saucepan",
            "pot set",
        ],
    }

    for category, terms in category_terms.items():
        if any(term in text_lower for term in terms):
            return category

    return None


def extract_social_model(text):
    """
    Extract a model/identifier only when the surrounding text
    explicitly identifies it as a model or SKU.

    This avoids treating promo codes, prices, dates, phone numbers,
    percentages or ordinary words followed by numbers as models.
    """
    text = clean_text(text)

    if not text:
        return None

    patterns = [
        r"(?i)\bmodel(?:\s*(?:no|number|#))?\s*[:\-]?\s*([A-Z0-9][A-Z0-9./_-]{2,30})\b",
        r"(?i)\bsku\s*[:\-]?\s*([A-Z0-9][A-Z0-9./_-]{2,30})\b",
        r"(?i)\bproduct\s+(?:code|number)\s*[:\-]?\s*([A-Z0-9][A-Z0-9./_-]{2,30})\b",
    ]

    for pattern in patterns:
        match = re.search(pattern, text)

        if not match:
            continue

        value = clean_text(match.group(1))

        if not value:
            continue

        if not re.search(r"[A-Z]", value, re.I):
            continue

        if not re.search(r"\d", value):
            continue

        return value

    return None



def extract_social_product_name(text, product_focus=None):
    """
    Extract a conservative product phrase only when the text
    contains an explicit recognized product term.

    Generic words such as 'Friday', 'today', campaign names,
    promotional codes and other surrounding text are not treated
    as product names.
    """
    text = clean_text(text)

    if not text or not product_focus:
        return None

    product_terms = [
        "side by side refrigerator",
        "double door refrigerator",
        "refrigerator",
        "fridge",
        "chest freezer",
        "upright freezer",
        "freezer",
        "washing machine",
        "washer",
        "dryer",
        "twin tub",
        "gas cooker",
        "electric cooker",
        "cooker",
        "oven",
        "gas stove",
        "stove",
        "microwave",
        "pressure cooker",
        "air fryer",
        "hot plate",
        "blender",
        "kettle",
        "toaster",
        "sandwich maker",
        "coffee maker",
        "juicer",
        "food processor",
        "mixer",
        "smart tv",
        "television",
        "tv",
        "soundbar",
        "speaker",
        "air conditioner",
        "fan",
        "water heater",
        "water dispenser",
        "water purifier",
        "vacuum cleaner",
        "iron",
        "generator",
        "inverter",
    ]

    text_lower = text.lower()

    matches = []

    for term in product_terms:
        position = text_lower.find(term)

        if position >= 0:
            matches.append((position, term))

    if not matches:
        return None

    position, term = min(matches, key=lambda item: item[0])

    start = max(0, position - 45)
    prefix = text[start:position].strip(" -??:,.()")

    # Keep only the final short descriptive phrase before the
    # product term. This prevents promotional sentences from
    # becoming product names.
    words = prefix.split()

    if len(words) > 6:
        words = words[-6:]

    candidate = " ".join(words + [text[position:position + len(term)]])

    candidate = clean_text(candidate).strip(" -??:,.()")

    if len(candidate) < 3 or len(candidate) > 100:
        return term

    return candidate





def truncate_text(text, length=1000):
    text = clean_text(text)

    if len(text) <= length:
        return text

    return text[:length - 3] + "..."


# =============================================================================
# DATABASE
# =============================================================================

def connect_db():
    connection = sqlite3.connect(DB_PATH)

    connection.execute("PRAGMA foreign_keys = ON")

    return connection


def get_table_columns(connection, table_name):
    """
    Read the real SQLite schema.

    This is read-only. It does not modify the database.
    """
    rows = connection.execute(
        f'PRAGMA table_info("{table_name}")'
    ).fetchall()

    return [row[1] for row in rows]


def ensure_social_table(connection):
    """
    Only creates social_observations if it does not already exist.

    Existing tables are never replaced.
    """

    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS social_observations (
            observation_id INTEGER PRIMARY KEY AUTOINCREMENT,
            finding_id TEXT NOT NULL,
            competitor_id INTEGER NOT NULL,
            platform TEXT NOT NULL,
            account_name TEXT,
            post_url TEXT,
            post_text TEXT,
            social_type TEXT,
            product_name TEXT,
            model TEXT,
            published_date TEXT,
            observed_date TEXT NOT NULL,
            likes INTEGER,
            comments INTEGER,
            shares INTEGER,
            views INTEGER,
            verification_status TEXT,
            confidence TEXT,
            evidence_text TEXT
        )
        """
    )

    connection.commit()


def get_competitors(connection):
    columns = get_table_columns(
        connection,
        "competitors",
    )

    required = {
        "competitor_id",
        "competitor_name",
        "brand_name",
    }

    missing = required - set(columns)

    if missing:
        raise RuntimeError(
            "competitors table is missing expected columns: "
            + ", ".join(sorted(missing))
        )

    return connection.execute(
        """
        SELECT competitor_id, competitor_name, brand_name
        FROM competitors
        ORDER BY competitor_name
        """
    ).fetchall()


def get_verified_social_sources(
    connection,
    competitor_name,
):
    """
    IMPORTANT:
    social_sources does not necessarily have an 'id' column.

    We only request columns confirmed by the existing project schema.
    """

    columns = get_table_columns(
        connection,
        "social_sources",
    )

    required = {
        "competitor_name",
        "platform",
        "account_name",
        "source_url",
        "verification_status",
    }

    missing = required - set(columns)

    if missing:
        raise RuntimeError(
            "social_sources table is missing expected columns: "
            + ", ".join(sorted(missing))
        )

    # status exists in the current project, but we handle it safely if absent.
    has_status = "status" in columns

    if has_status:
        sql = """
            SELECT
                competitor_name,
                platform,
                account_name,
                source_url,
                verification_status,
                status
            FROM social_sources
            WHERE competitor_name = ?
              AND verification_status = 'VERIFIED'
              AND (
                    status = 'active'
                    OR status IS NULL
                  )
            ORDER BY platform, account_name
        """
    else:
        sql = """
            SELECT
                competitor_name,
                platform,
                account_name,
                source_url,
                verification_status
            FROM social_sources
            WHERE competitor_name = ?
              AND verification_status = 'VERIFIED'
            ORDER BY platform, account_name
        """

    rows = connection.execute(
        sql,
        (competitor_name,),
    ).fetchall()

    sources = []

    for row in rows:

        if has_status:
            (
                row_competitor,
                platform,
                account_name,
                source_url,
                verification_status,
                status,
            ) = row
        else:
            (
                row_competitor,
                platform,
                account_name,
                source_url,
                verification_status,
            ) = row

            status = "active"

        sources.append(
            {
                "competitor_name": row_competitor,
                "platform": platform,
                "account_name": account_name,
                "source_url": source_url,
                "verification_status": verification_status,
                "status": status,
            }
        )

    return sources


def social_observation_exists(
    connection,
    post_url,
):
    if not post_url:
        return False

    columns = get_table_columns(
        connection,
        "social_observations",
    )

    if "post_url" not in columns:
        raise RuntimeError(
            "social_observations table is missing post_url"
        )

    row = connection.execute(
        """
        SELECT 1
        FROM social_observations
        WHERE post_url = ?
        LIMIT 1
        """,
        (post_url,),
    ).fetchone()

    return row is not None


# =============================================================================
# SOCIALAPIS
# =============================================================================

def extract_posts_from_socialapis(payload):

    if not isinstance(payload, dict):
        return []

    possible_containers = [
        payload.get("data"),
        payload.get("posts"),
        payload.get("results"),
    ]

    for container in possible_containers:

        if isinstance(container, list):
            return container

        if isinstance(container, dict):

            for key in (
                "posts",
                "data",
                "results",
                "items",
            ):

                value = container.get(key)

                if isinstance(value, list):
                    return value

    return []


def normalize_socialapis_post(
    post,
    source,
):

    if not isinstance(post, dict):
        return None

    account_name = source["account_name"]
    competitor_name = source["competitor_name"]
    platform = clean_text(
        source["platform"]
    ).lower()

    # SocialAPIs nests the real fields under 'details', 'values' and
    # 'reactions' sub-dicts rather than putting them at the top level
    # of each post. Confirmed from a live payload on 2026-09-25.
    details = (
        post.get("details")
        if isinstance(post.get("details"), dict)
        else {}
    )

    values = (
        post.get("values")
        if isinstance(post.get("values"), dict)
        else {}
    )

    reactions = (
        post.get("reactions")
        if isinstance(post.get("reactions"), dict)
        else {}
    )

    post_url = (
        details.get("post_link")
        or values.get("post_link")
        or post.get("post_link")
        or post.get("post_url")
        or post.get("permalink_url")
        or post.get("permalink")
        or ""
    )

    post_url = clean_text(post_url)

    if DEBUG_SOCIAL_URLS:
        print(
            f"    DEBUG RESOLVED POST_URL: "
            f"{post_url!r}"
        )

    post_text = (
        values.get("text")
        or post.get("text")
        or post.get("message")
        or post.get("caption")
        or post.get("description")
        or ""
    )

    post_text = clean_text(post_text)

    published_date = parse_date(
        values.get("publish_time")
        or post.get("publish_time")
        or post.get("published_time")
        or post.get("created_time")
        or post.get("published_at")
    )

    post_id = clean_text(
        details.get("post_id")
        or values.get("post_id")
        or post.get("post_id")
        or post.get("id")
    )

    likes = clean_metric(
        reactions.get("total_reaction_count")
        or reactions.get("total")
        or reactions.get("count")
    )

    if likes is None:

        likes = clean_metric(
            post.get("likes_count")
            or post.get("like_count")
            or post.get("likes")
        )

    comments = clean_metric(
        details.get("comments_count")
        or post.get("comments_count")
        or post.get("comment_count")
        or post.get("comments")
    )

    shares = clean_metric(
        details.get("share_count")
        or post.get("share_count")
        or post.get("shares_count")
        or post.get("shares")
    )

    views = clean_metric(
        details.get("play_count")
        or post.get("views_count")
        or post.get("view_count")
        or post.get("views")
    )

    evidence_text = post_text

    if not evidence_text:

        evidence_text = (
            f"Social post published by "
            f"{account_name}"
        )

    product_focus = classify_social_product_focus(
        post_text
    )

    product_name = extract_social_product_name(
        post_text,
        product_focus,
    )

    model = extract_social_model(
        post_text
    )

    return {
        "competitor": competitor_name,
        "platform": platform,
        "account_name": account_name,
        "post_url": post_url,
        "post_id": post_id,
        "post_text": post_text,
        "social_type": classify_social_type(
            post_text
        ),
        "product_name": product_name,
        "model": model,
        "published_date": published_date,
        "likes": likes,
        "comments": comments,
        "shares": shares,
        "views": views,
        "evidence_text": evidence_text,
    }


def fetch_socialapis_posts(source):

    account_name = source["account_name"]
    source_url = clean_text(source.get("source_url"))

    print(
        f"  PROVIDER REQUEST: "
        f"{account_name}"
    )

    if not SOCIALAPIS_API_KEY:
        print(
            "  PROVIDER SKIPPED: "
            "SOCIALAPIS_API_KEY not configured"
        )
        return []

    # SocialAPIs requires a page link or profile_id.
    # Never invent a profile_id. Use the verified source URL.
    if not source_url:
        print(
            f"  PROVIDER SKIPPED: "
            f"{account_name} has no source URL"
        )
        return []

    headers = {
        "x-api-token": SOCIALAPIS_API_KEY,
        "Accept": "application/json",
    }

    params = {
        "link": source_url,
        "limit": SOCIALAPIS_LIMIT,
    }

    try:
        response = requests.get(
            SOCIALAPIS_POSTS_URL,
            headers=headers,
            params=params,
            timeout=REQUEST_TIMEOUT,
        )

    except requests.RequestException as exc:
        print(
            f"  PROVIDER REQUEST ERROR: "
            f"{clean_text(exc)}"
        )
        return []

    print(
        f"  PROVIDER HTTP: "
        f"{response.status_code}"
    )

    try:
        payload = response.json()

    except ValueError:
        print(
            "  PROVIDER ERROR: "
            "response was not valid JSON"
        )
        print(
            f"  RESPONSE: "
            f"{response.text[:500]}"
        )
        return []

    if isinstance(payload, dict):

        if (
            payload.get("success") is False
            or payload.get("error_code")
        ):

            error_code = payload.get(
                "error_code",
                "UNKNOWN_ERROR",
            )

            message = payload.get(
                "message",
                "",
            )

            detail = payload.get(
                "detail",
                "",
            )

            print(
                f"  PROVIDER API ERROR: "
                f"{error_code}"
            )

            if message:
                print(
                    f"  MESSAGE: "
                    f"{clean_text(message)}"
                )

            if detail:
                print(
                    f"  DETAIL: "
                    f"{clean_text(detail)[:500]}"
                )

            return []

    posts = extract_posts_from_socialapis(
        payload
    )

    print(
        f"  PROVIDER POSTS: "
        f"{len(posts)}"
    )

    candidates = []

    for post in posts:

        normalized = normalize_socialapis_post(
            post,
            source,
        )

        if normalized:
            candidates.append(normalized)

    return candidates


# =============================================================================
# SOURCE CHECK
# =============================================================================

def check_source_url(source):

    source_url = source["source_url"]
    account_name = source["account_name"]

    if not source_url:

        print(
            f"  SOURCE CHECK SKIPPED: "
            f"{account_name} has no URL"
        )

        return False

    try:

        response = requests.get(
            source_url,
            timeout=REQUEST_TIMEOUT,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 "
                    "(Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 "
                    "Chrome/153.0 Safari/537.36"
                )
            },
        )

        if response.status_code == 200:

            print(
                f"  SOURCE CHECK: "
                f"{account_name} "
                f"HTTP {response.status_code}"
            )

            return True

        print(
            f"  SOURCE CHECK FAILED: "
            f"{account_name} "
            f"{response.status_code}"
        )

        return False

    except requests.RequestException as exc:

        print(
            f"  SOURCE CHECK FAILED: "
            f"{account_name} "
            f"{clean_text(exc)}"
        )

        return False


# =============================================================================
# BING FALLBACK
# =============================================================================

def bing_search(
    query,
    count=10,
):

    if not BING_API_KEY:
        return []

    url = (
        "https://api.bing.microsoft.com/"
        "v7.0/search"
    )

    headers = {
        "Ocp-Apim-Subscription-Key":
            BING_API_KEY,
    }

    params = {
        "q": query,
        "count": count,
        "responseFilter": "Webpages",
        "textDecorations": False,
        "textFormat": "Raw",
    }

    try:

        response = requests.get(
            url,
            headers=headers,
            params=params,
            timeout=REQUEST_TIMEOUT,
        )

        if response.status_code != 200:
            return []

        payload = response.json()

    except (
        requests.RequestException,
        ValueError,
    ):

        return []

    webpages = (
        payload
        .get("webPages", {})
        .get("value", [])
    )

    if isinstance(webpages, list):
        return webpages

    return []


def fetch_bing_candidates(
    competitor_name,
    sources,
):

    if not BING_API_KEY:
        return []

    candidates = []

    for source in sources:

        platform = clean_text(
            source["platform"]
        ).lower()

        account_name = clean_text(
            source["account_name"]
        )

        query = (
            f'"{account_name}" '
            f"{competitor_name} "
            f"{platform} "
            f"(sale OR promotion OR "
            f"appliance OR product)"
        )

        results = bing_search(
            query,
            count=10,
        )

        for result in results:

            url = clean_text(
                result.get("url")
            )

            if not domain_allowed(url):
                continue

            name = clean_text(
                result.get("name")
            )

            snippet = clean_text(
                result.get("snippet")
            )

            text = (
                f"{name} {snippet}"
            )

            candidates.append(
                {
                    "competitor":
                        competitor_name,
                    "platform":
                        platform,
                    "account_name":
                        account_name,
                    "post_url":
                        url,
                    "post_id":
                        "",
                    "post_text":
                        text,
                    "social_type":
                        classify_social_type(
                            text
                        ),
                    "product_name":
                        None,
                    "model":
                        None,
                    "published_date":
                        None,
                    "likes":
                        None,
                    "comments":
                        None,
                    "shares":
                        None,
                    "views":
                        None,
                    "evidence_text":
                        text,
                }
            )

    return candidates


# =============================================================================
# VALIDATION
# =============================================================================

def validate_candidate(candidate):

    post_url = clean_text(
        candidate.get("post_url")
    )

    post_text = clean_text(
        candidate.get("post_text")
    )

    evidence_text = clean_text(
        candidate.get("evidence_text")
    )

    combined_text = " ".join(
        part
        for part in [
            post_text,
            evidence_text,
            clean_text(
                candidate.get("product_name")
            ),
            clean_text(
                candidate.get("model")
            ),
        ]
        if part
    )

    if not domain_allowed(post_url):

        return (
            False,
            "non-approved social domain",
        )

    published_date = candidate.get(
        "published_date"
    )

    if (
        published_date
        and not is_within_window(
            published_date
        )
    ):

        return (
            False,
            "outside 7-day window",
        )

    if not contains_any(
        combined_text,
        APPLIANCE_TERMS,
    ):

        return (
            False,
            "no appliance/electronics evidence",
        )

    if not contains_any(
        combined_text,
        COMMERCIAL_TERMS,
    ):

        return (
            False,
            "no commercial/activity evidence",
        )

    return True, None


# =============================================================================
# FINDINGS WRITE
# =============================================================================

def next_finding_id(connection, d=None):
    """
    Mirrors database.py's next_finding_id() exactly (same CI-YYYY-MM-NNNNN
    format, same per-month counter against the findings table), but reads
    the result by tuple index rather than row["finding_id"], because this
    connection does not set row_factory = sqlite3.Row.
    """

    d = d or date.today()

    prefix = f"CI-{d:%Y-%m}-"

    row = connection.execute(
        "SELECT finding_id FROM findings "
        "WHERE finding_id LIKE ? "
        "ORDER BY finding_id DESC LIMIT 1",
        (prefix + "%",),
    ).fetchone()

    n = int(row[0].split("-")[-1]) + 1 if row else 1

    return f"{prefix}{n:05d}"


def create_finding(
    connection,
    competitor_id,
    candidate,
):

    findings_columns = get_table_columns(
        connection,
        "findings",
    )

    required_columns = {
        "finding_id",
        "competitor_id",
        "brand",
        "category",
        "finding_type",
        "summary",
        "source_url",
        "source_type",
        "published_date",
        "observed_date",
        "scan_week",
        "evidence_text",
        "verification_status",
        "confidence",
    }

    missing = (
        required_columns
        - set(findings_columns)
    )

    if missing:

        raise RuntimeError(
            "findings table is missing expected "
            "columns: "
            + ", ".join(sorted(missing))
        )

    summary = truncate_text(
        candidate.get("post_text")
        or candidate.get("evidence_text")
        or (
            f"{candidate.get('social_type', 'activity')}"
            " activity"
        )
    )

    evidence_text = truncate_text(
        candidate.get("evidence_text")
        or candidate.get("post_text")
        or summary
    )

    published_date = candidate.get(
        "published_date"
    )

    observed_date = date.today().isoformat()

    scan_week = current_scan_week()

    finding_id = next_finding_id(
        connection,
        date.today(),
    )

    connection.execute(
        """
        INSERT INTO findings (
            finding_id,
            competitor_id,
            brand,
            category,
            finding_type,
            summary,
            source_url,
            source_type,
            published_date,
            observed_date,
            scan_week,
            evidence_text,
            verification_status,
            confidence
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            finding_id,
            competitor_id,
            candidate.get("competitor"),
            "Home Appliances & Electronics",
            "social",
            summary,
            candidate.get("post_url"),
            "social media",
            published_date,
            observed_date,
            scan_week,
            evidence_text,
            "VERIFIED",
            "medium",
        ),
    )

    return finding_id


# =============================================================================
# SOCIAL OBSERVATION WRITE
# =============================================================================

def create_social_observation(
    connection,
    finding_id,
    competitor_id,
    candidate,
):

    # Matches the real deployed schema (confirmed via PRAGMA table_info
    # on 2026-09-25): observation_id, finding_id, competitor_id,
    # platform, ..., observed_date (NOT NULL), verification_status,
    # confidence, evidence_text. There is no 'competitor' text column
    # and no plain 'id' column.

    observed_date = date.today().isoformat()

    cursor = connection.execute(
        """
        INSERT INTO social_observations (
            finding_id,
            competitor_id,
            platform,
            account_name,
            post_url,
            post_text,
            social_type,
            product_name,
            model,
            published_date,
            observed_date,
            likes,
            comments,
            shares,
            views,
            verification_status,
            confidence,
            evidence_text
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            finding_id,
            competitor_id,
            candidate.get("platform"),
            candidate.get("account_name"),
            candidate.get("post_url"),
            candidate.get("post_text"),
            candidate.get("social_type"),
            candidate.get("product_name"),
            candidate.get("model"),
            candidate.get("published_date"),
            observed_date,
            candidate.get("likes"),
            candidate.get("comments"),
            candidate.get("shares"),
            candidate.get("views"),
            "VERIFIED",
            "medium",
            candidate.get("evidence_text"),
        ),
    )



    return cursor.lastrowid
def write_social_observation(
    connection,
    competitor_id,
    candidate,
):

    post_url = clean_text(
        candidate.get("post_url")
    )

    is_duplicate = social_observation_exists(
        connection,
        post_url,
    )

    if is_duplicate:

        try:

            history_result = record_social_engagement_history(
                connection,
                competitor_id,
                candidate,
            )

            connection.commit()

            return "duplicate"

        except (
            sqlite3.Error,
            RuntimeError,
        ) as exc:

            connection.rollback()

            print(
                f"    HISTORY WRITE ERROR: "
                f"{clean_text(exc)}"
            )

            return "error"

    try:

        finding_id = create_finding(
            connection,
            competitor_id,
            candidate,
        )

        create_social_observation(
            connection,
            finding_id,
            competitor_id,
            candidate,
        )

        record_social_engagement_history(
            connection,
            competitor_id,
            candidate,
        )

        connection.commit()

        return "created"

    except sqlite3.IntegrityError as exc:

        connection.rollback()

        error_text = clean_text(exc)

        if (
            "UNIQUE constraint failed"
            in error_text
        ):

            return "duplicate"

        print(
            f"    WRITE ERROR: "
            f"{error_text}"
        )

        return "error"

    except (
        sqlite3.Error,
        RuntimeError,
    ) as exc:

        connection.rollback()

        print(
            f"    WRITE ERROR: "
            f"{clean_text(exc)}"
        )

        return "error"


# =============================================================================
# SOCIAL ENGAGEMENT HISTORY
# =============================================================================


def record_social_engagement_history(
    connection,
    competitor_id,
    candidate,
):

    post_url = clean_text(
        candidate.get("post_url")
    )

    if not post_url:
        return "skipped"

    observed_date = date.today().isoformat()

    existing = connection.execute(
        """
        SELECT 1
        FROM social_engagement_history
        WHERE post_url = ?
          AND observed_date = ?
        LIMIT 1
        """,
        (
            post_url,
            observed_date,
        ),
    ).fetchone()

    if existing:
        return "duplicate"

    observation = connection.execute(
        """
        SELECT
            observation_id,
            platform,
            account_name,
            published_date
        FROM social_observations
        WHERE post_url = ?
        LIMIT 1
        """,
        (post_url,),
    ).fetchone()

    if not observation:
        return "skipped"

    observation_id, platform, account_name, published_date = observation

    connection.execute(
        """
        INSERT INTO social_engagement_history (
            observation_id,
            competitor_id,
            platform,
            account_name,
            post_url,
            published_date,
            observed_date,
            likes,
            comments,
            shares,
            views
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            observation_id,
            competitor_id,
            platform,
            account_name,
            post_url,
            published_date,
            observed_date,
            candidate.get("likes"),
            candidate.get("comments"),
            candidate.get("shares"),
            candidate.get("views"),
        ),
    )

    return "created"


# =============================================================================
# DEDUPLICATION
# =============================================================================

def deduplicate_candidates(
    candidates,
):

    unique = []
    seen = set()

    for candidate in candidates:

        post_url = clean_text(
            candidate.get("post_url")
        )

        evidence_text = clean_text(
            candidate.get("evidence_text")
        )

        key = (
            post_url.lower(),
            evidence_text.lower(),
        )

        if key in seen:
            continue

        seen.add(key)

        unique.append(candidate)

    return unique


# =============================================================================
# MAIN
# =============================================================================

def main():

    print("=" * 78)
    print("MIKA CI - SOCIAL EVIDENCE COLLECTION")
    print("=" * 78)

    print(
        f"Window: last {WINDOW_DAYS} days"
    )

    print(
        "Primary acquisition: SocialAPIs"
    )

    print(
        "Fallback acquisition: Bing"
    )

    print(
        f"Database: {DB_PATH}"
    )

    print()

    print("Architecture:")
    print("social_sources")
    print("    ↓")
    print("SocialAPIs / Bing fallback")
    print("    ↓")
    print("normalized evidence")
    print("    ↓")
    print("validation")
    print("    ↓")
    print(
        "social_observations + findings"
    )

    print("=" * 78)

    if SOCIALAPIS_API_KEY:
        print(
            "SocialAPIs API key: CONFIGURED"
        )
    else:
        print(
            "SocialAPIs API key: "
            "NOT CONFIGURED"
        )

    print("=" * 78)

    connection = connect_db()

    try:

        ensure_social_table(
            connection
        )

        competitors = get_competitors(
            connection
        )

        # The competitors table has one row per BRAND (e.g. Samsutech has
        # 7 rows: Samsung, TCL, Moulinex, Krups, SCL, Tefal, Berklays;
        # Opalnet has 2: LG, Midea), but social accounts are tracked once
        # per COMPANY in social_sources, keyed on competitor_name. Looping
        # over every brand row re-runs the identical social lookup once
        # per brand (confirmed via direct query on 2026-09-25: Samsutech
        # printed 7 identical "0 verified sources" blocks, Opalnet 2).
        # Deduplicate to one representative competitor_id per distinct
        # competitor_name, preserving the alphabetical order already
        # returned by get_competitors().
        seen_competitor_names = set()
        deduplicated_competitors = []

        for (
            row_competitor_id,
            row_competitor_name,
            row_brand_name,
        ) in competitors:

            if row_competitor_name in seen_competitor_names:
                continue

            seen_competitor_names.add(row_competitor_name)

            deduplicated_competitors.append(
                (
                    row_competitor_id,
                    row_competitor_name,
                    row_brand_name,
                )
            )

        competitors = deduplicated_competitors

        total_provider = 0
        total_bing = 0
        total_created = 0
        total_duplicates = 0
        total_rejected = 0
        total_errors = 0

        for (
            competitor_id,
            competitor_name,
            brand_name,
        ) in competitors:

            print()
            print("=" * 78)
            print(
                f"COMPETITOR: "
                f"{competitor_name}"
            )
            print("=" * 78)

            sources = (
                get_verified_social_sources(
                    connection,
                    competitor_name,
                )
            )

            print(
                f"VERIFIED SOURCES: "
                f"{len(sources)}"
            )

            if not sources:

                print(
                    "  No verified social sources."
                )

                print(
                    "SUMMARY: skipped"
                )

                continue

            # -----------------------------------------------------------------
            # SOURCE CHECKS
            # -----------------------------------------------------------------

            for source in sources:

                check_source_url(
                    source
                )

            # -----------------------------------------------------------------
            # SOCIALAPIS
            # -----------------------------------------------------------------

            provider_candidates = []

            for source in sources:

                platform = clean_text(
                    source["platform"]
                ).lower()

                if platform != "facebook":
                    continue

                provider_candidates.extend(
                    fetch_socialapis_posts(
                        source
                    )
                )

            print(
                f"PROVIDER CANDIDATES: "
                f"{len(provider_candidates)}"
            )

            total_provider += (
                len(provider_candidates)
            )

            # -----------------------------------------------------------------
            # BING FALLBACK
            # -----------------------------------------------------------------

            if provider_candidates:

                print(
                    "BING FALLBACK: "
                    "not required."
                )

                bing_candidates = []

            else:

                print(
                    "BING FALLBACK: "
                    "activated."
                )

                bing_candidates = (
                    fetch_bing_candidates(
                        competitor_name,
                        sources,
                    )
                )

            print(
                f"BING CANDIDATES: "
                f"{len(bing_candidates)}"
            )

            total_bing += (
                len(bing_candidates)
            )

            # -----------------------------------------------------------------
            # DEDUPLICATE
            # -----------------------------------------------------------------

            all_candidates = (
                provider_candidates
                + bing_candidates
            )

            unique_candidates = (
                deduplicate_candidates(
                    all_candidates
                )
            )

            print(
                f"UNIQUE CANDIDATES: "
                f"{len(unique_candidates)}"
            )

            created = 0
            duplicates = 0
            rejected = 0
            errors = 0

            # -----------------------------------------------------------------
            # VALIDATE + WRITE
            # -----------------------------------------------------------------

            for candidate in unique_candidates:

                valid, reason = (
                    validate_candidate(
                        candidate
                    )
                )

                if not valid:

                    print(
                        f"    REJECTED: "
                        f"{reason}"
                    )

                    rejected += 1

                    continue

                result = (
                    write_social_observation(
                        connection,
                        competitor_id,
                        candidate,
                    )
                )

                if result == "created":

                    created += 1

                elif result == "duplicate":

                    print(
                        "    DUPLICATE: "
                        "already stored"
                    )

                    duplicates += 1

                else:

                    errors += 1

            total_created += created
            total_duplicates += duplicates
            total_rejected += rejected
            total_errors += errors

            print()
            print(
                f"SUMMARY: "
                f"{competitor_name}"
            )

            print(
                f"  Provider candidates : "
                f"{len(provider_candidates)}"
            )

            print(
                f"  Bing candidates     : "
                f"{len(bing_candidates)}"
            )

            print(
                f"  Created             : "
                f"{created}"
            )

            print(
                f"  Duplicates          : "
                f"{duplicates}"
            )

            print(
                f"  Rejected            : "
                f"{rejected}"
            )

            print(
                f"  Errors              : "
                f"{errors}"
            )

        # ---------------------------------------------------------------------
        # FINAL COUNT
        # ---------------------------------------------------------------------

        social_count = connection.execute(
            """
            SELECT COUNT(*)
            FROM social_observations
            """
        ).fetchone()[0]

        print()
        print("=" * 78)
        print(
            "FINAL SOCIAL COLLECTION SUMMARY"
        )
        print("=" * 78)

        print(
            f"Provider candidates : "
            f"{total_provider}"
        )

        print(
            f"Bing candidates     : "
            f"{total_bing}"
        )

        print(
            f"Created             : "
            f"{total_created}"
        )

        print(
            f"Duplicates          : "
            f"{total_duplicates}"
        )

        print(
            f"Rejected            : "
            f"{total_rejected}"
        )

        print(
            f"Errors              : "
            f"{total_errors}"
        )

        print("=" * 78)

        print(
            f"Total social observations "
            f"in DB: {social_count}"
        )

        print("=" * 78)

    finally:

        connection.close()


if __name__ == "__main__":
    main()
