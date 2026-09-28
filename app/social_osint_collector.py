import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import quote_plus, urlparse


WINDOW_DAYS = 7
MAX_RESULTS_PER_QUERY = 10

SEARCH_QUERIES = {
    "Hotpoint Appliances": [
        'site:facebook.com/hotpointkenya',
        'site:instagram.com/hotpointkenya',
        '"Hotpoint Kenya" appliance promotion',
        '"Hotpoint Kenya" appliance offer',
    ],
    "Ramtons": [
        'site:facebook.com/MyRamtons',
        'site:instagram.com/myramtons',
        '"Ramtons Kenya" appliance promotion',
        '"Ramtons Kenya" appliance offer',
    ],
}


OFFICIAL_DOMAINS = {
    "facebook.com",
    "www.facebook.com",
    "instagram.com",
    "www.instagram.com",
}


BLOCKED_DOMAINS = {
    "youtube.com",
    "www.youtube.com",
    "whatsapp.com",
    "www.whatsapp.com",
    "microsoft.com",
    "www.microsoft.com",
    "bing.com",
    "www.bing.com",
    "zhihu.com",
    "www.zhihu.com",
    "justanswer.com",
    "www.justanswer.com",
}


APPLIANCE_TERMS = {
    "appliance",
    "appliances",
    "fridge",
    "refrigerator",
    "freezer",
    "cooker",
    "oven",
    "microwave",
    "washing machine",
    "washer",
    "dryer",
    "dishwasher",
    "blender",
    "mixer",
    "kettle",
    "air fryer",
    "television",
    "tv",
    "led",
    "electronics",
}


COMMERCIAL_TERMS = {
    "promotion",
    "promo",
    "offer",
    "discount",
    "sale",
    "deal",
    "price",
    "buy",
    "shop",
    "available",
    "launch",
    "new",
    "campaign",
    "giveaway",
}


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 "
        "Chrome/153.0 Safari/537.36"
    )
}


def clean_text(value):
    if not value:
        return ""

    return re.sub(r"\s+", " ", value).strip()


def extract_real_url(url):
    """
    Reject search-engine redirect URLs.

    Only return a real destination URL when it is already
    visible as a normal HTTP(S) URL.
    """
    if not url:
        return None

    url = url.strip()

    parsed = urlparse(url)

    if parsed.scheme not in {"http", "https"}:
        return None

    domain = parsed.netloc.lower().split(":")[0]

    if domain in BLOCKED_DOMAINS:
        return None

    if domain not in OFFICIAL_DOMAINS:
        return None

    return url


def extract_search_results(html):
    soup = BeautifulSoup(html, "html.parser")

    results = []

    for item in soup.select("li.b_algo"):
        link = item.select_one("h2 a")

        if not link:
            continue

        title = clean_text(
            link.get_text(" ", strip=True)
        )

        raw_url = link.get("href", "").strip()

        url = extract_real_url(raw_url)

        if not url:
            continue

        description = item.select_one(".b_caption p")

        snippet = clean_text(
            description.get_text(" ", strip=True)
            if description
            else ""
        )

        if not title:
            continue

        results.append(
            {
                "title": title,
                "url": url,
                "snippet": snippet,
            }
        )

        if len(results) >= MAX_RESULTS_PER_QUERY:
            break

    return results


def search_web(query):
    url = (
        "https://www.bing.com/search"
        f"?q={quote_plus(query)}"
        "&count=10"
        "&setlang=en"
    )

    response = requests.get(
        url,
        headers=HEADERS,
        timeout=20,
    )

    response.raise_for_status()

    return extract_search_results(response.text)


def contains_any(text, terms):
    text = text.lower()

    return any(
        term.lower() in text
        for term in terms
    )


def is_relevant(competitor, title, snippet, url):
    combined = " ".join(
        [
            competitor,
            title,
            snippet,
            url,
        ]
    ).lower()

    competitor_terms = {
        "hotpoint appliances": [
            "hotpoint",
            "hotpointkenya",
        ],
        "ramtons": [
            "ramtons",
            "myramtons",
        ],
    }

    identity_ok = contains_any(
        combined,
        competitor_terms.get(
            competitor,
            [competitor],
        ),
    )

    if not identity_ok:
        return False

    appliance_ok = contains_any(
        combined,
        APPLIANCE_TERMS,
    )

    commercial_ok = contains_any(
        combined,
        COMMERCIAL_TERMS,
    )

    # Official social profile pages are allowed when identity
    # is confirmed, even if the search snippet has little text.
    parsed = urlparse(url)
    domain = parsed.netloc.lower().split(":")[0]

    direct_social_profile = (
        domain in OFFICIAL_DOMAINS
        and identity_ok
    )

    if direct_social_profile:
        return True

    return appliance_ok and commercial_ok


def classify_result(title, snippet):
    text = f"{title} {snippet}".lower()

    if contains_any(
        text,
        {
            "promotion",
            "promo",
            "offer",
            "discount",
            "sale",
            "deal",
            "giveaway",
        },
    ):
        return "promotion"

    if contains_any(
        text,
        {
            "launch",
            "new product",
            "new arrival",
            "introduced",
            "unveiled",
        },
    ):
        return "product"

    return "activity"


def extract_platform(url):
    domain = urlparse(url).netloc.lower()

    if "facebook.com" in domain:
        return "Facebook"

    if "instagram.com" in domain:
        return "Instagram"

    return "Web"


def print_result(
    competitor,
    query,
    result,
):
    title = result["title"]
    url = result["url"]
    snippet = result["snippet"]

    print("-" * 78)
    print(f"Competitor : {competitor}")
    print(f"Platform   : {extract_platform(url)}")
    print(
        f"Type       : "
        f"{classify_result(title, snippet)}"
    )
    print(f"Query      : {query}")
    print(f"Title      : {title}")
    print(f"URL        : {url}")
    print(
        f"Evidence   : "
        f"{snippet or 'NO SNIPPET'}"
    )
    print("Database   : NO WRITE")


def main():
    print("=" * 78)
    print("MIKA CI - SOCIAL INTELLIGENCE")
    print("STRICT PUBLIC WEB OSINT DISCOVERY")
    print("=" * 78)
    print(f"Window  : last {WINDOW_DAYS} days")
    print(
        f"Maximum : "
        f"{MAX_RESULTS_PER_QUERY} results/query"
    )
    print("Writes  : DISABLED")
    print()

    candidates = 0
    rejected = 0
    unique_urls = set()

    for competitor, queries in SEARCH_QUERIES.items():

        print("=" * 78)
        print(competitor)
        print("=" * 78)

        for query in queries:

            print()
            print(f"SEARCH: {query}")

            try:
                results = search_web(query)

            except Exception as exc:
                print(f"SOURCE ERROR: {exc}")
                continue

            if not results:
                print("No qualifying official-domain results.")
                continue

            for result in results:

                url = result["url"]

                if url in unique_urls:
                    continue

                unique_urls.add(url)

                if not is_relevant(
                    competitor,
                    result["title"],
                    result["snippet"],
                    url,
                ):
                    rejected += 1
                    continue

                print_result(
                    competitor,
                    query,
                    result,
                )

                candidates += 1

    print()
    print("=" * 78)
    print("OSINT DISCOVERY SUMMARY")
    print("=" * 78)
    print(f"Candidate results : {candidates}")
    print(f"Rejected results  : {rejected}")
    print(f"Unique URLs       : {len(unique_urls)}")
    print("Database writes   : 0")
    print()
    print("STRICT READ-ONLY TEST COMPLETE.")


if __name__ == "__main__":
    main()