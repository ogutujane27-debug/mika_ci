import requests
import re
from bs4 import BeautifulSoup

url = "https://www.standardmedia.co.ke/business/enterprise/article/2001558479/how-kenyan-businesses-can-turn-tech-into-measurable-gain"

headers = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0 Safari/537.36"
    )
}

response = requests.get(
    url,
    headers=headers,
    timeout=30,
)

print("HTTP:", response.status_code)

soup = BeautifulSoup(response.text, "html.parser")

text = soup.get_text(" ", strip=True)

patterns = [
    r"\d+\s+(?:mins?|minutes?|hours?|hrs?|days?)\s+ago",
    r"\d{1,2}\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4}",
    r"(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},\s+\d{4}",
    r"\d{4}-\d{2}-\d{2}",
]

print()
print("--- DATE-LIKE TEXT ---")

matches = set()

for pattern in patterns:
    for match in re.findall(pattern, text, re.I):
        matches.add(match)

for match in sorted(matches):
    print(match)

print()
print("--- ARTICLE HEADER TEXT ---")

title = soup.find("h1")

if title:
    print(title.parent.get_text(" ", strip=True)[:2000])
else:
    print("No H1 found.")
