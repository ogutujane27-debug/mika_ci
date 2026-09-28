import requests
import json
from bs4 import BeautifulSoup

URLS = {
    "Citizen": "https://www.citizen.digital/article/ex-marathoner-beatrice-murugi-starts-treatment-at-knh-n390705",
    "NTV": "https://ntvkenya.co.ke/business/jambojet-secures-maintenance-contract-with-ghanas-passionair/",
    "Standard": "https://www.standardmedia.co.ke/business/enterprise/article/2001558479/how-kenyan-businesses-can-turn-tech-into-measurable-gain",
    "K24": "https://k24.digital/news/7-day-weather-forecast-warns-of-rainfall-in-nairobi-mombasa-kisumu-and-other-areas",
}

headers = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0 Safari/537.36"
    )
}

for name, url in URLS.items():
    print()
    print("=" * 78)
    print(name)
    print("=" * 78)

    response = requests.get(
        url,
        headers=headers,
        timeout=30,
    )

    print("HTTP:", response.status_code)

    soup = BeautifulSoup(response.text, "html.parser")

    print()
    print("--- META DATE FIELDS ---")

    found_meta = 0

    for tag in soup.find_all("meta"):
        attrs = tag.attrs

        interesting = (
            attrs.get("property", ""),
            attrs.get("name", ""),
            attrs.get("itemprop", ""),
        )

        if any(
            key in " ".join(interesting).lower()
            for key in [
                "published",
                "date",
                "modified",
                "article",
                "time",
            ]
        ):
            print(attrs)
            found_meta += 1

    print("Meta fields found:", found_meta)

    print()
    print("--- JSON-LD ---")

    found_json = 0

    for script in soup.find_all(
        "script",
        attrs={"type": "application/ld+json"},
    ):
        raw = script.string or script.get_text()

        try:
            data = json.loads(raw)
        except Exception:
            print("JSON-LD: unreadable")
            continue

        items = data if isinstance(data, list) else [data]

        for item in items:
            if isinstance(item, dict):
                print(
                    "TYPE:",
                    item.get("@type"),
                    "| DATE:",
                    item.get("datePublished"),
                    "| MODIFIED:",
                    item.get("dateModified"),
                )
                found_json += 1

    print("JSON-LD objects found:", found_json)
