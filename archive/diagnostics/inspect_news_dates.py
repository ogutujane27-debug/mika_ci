import sys
import re
import requests
from bs4 import BeautifulSoup

sys.path.insert(0, ".\app")

import news_collector as n

headers = {"User-Agent": n.USER_AGENT}

for source in n.NEWS_SOURCES:
    print()
    print("=" * 78)
    print(source["name"])
    print("=" * 78)

    response = requests.get(
        source["url"],
        headers=headers,
        timeout=30,
    )

    print("HTTP:", response.status_code)

    soup = BeautifulSoup(response.text, "html.parser")

    found = 0

    for tag in soup.find_all(["time", "meta"]):
        value = (
            tag.get("datetime")
            or tag.get("content")
            or tag.get_text(" ", strip=True)
        )

        value = " ".join(str(value).split())

        if re.search(
            r"2026|2025|January|February|March|April|May|June|July|August|September|October|November|December|hours ago|mins ago|day ago",
            value,
            re.I,
        ):
            print(tag.name, tag.attrs, value[:250])
            found += 1

            if found >= 20:
                break

    print("Date-like elements found:", found)
