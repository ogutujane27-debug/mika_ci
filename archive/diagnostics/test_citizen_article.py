import requests
from bs4 import BeautifulSoup

url = "https://www.citizen.digital/business/haier-steps-up-kenya-expansion-with-new-retail-partnerships-n356978"

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

print()
print("--- TITLE ---")

title = soup.find("h1")

if title:
    print(title.get_text(" ", strip=True))
else:
    print("NO H1")

print()
print("--- ARTICLE TEXT SAMPLE ---")

article = soup.find("article")

if article:
    text = article.get_text(" ", strip=True)
    print(text[:3000])
else:
    print("NO ARTICLE TAG")

print()
print("--- BRAND CHECK ---")

page_text = soup.get_text(" ", strip=True).lower()

for brand in [
    "haier",
    "hisense",
    "hotpoint",
    "ramtons",
    "armco",
    "midea",
    "lg",
    "samsung",
    "tcl",
    "jtc",
    "k-elec",
    "bruhm",
]:
    if brand in page_text:
        print("FOUND:", brand)
