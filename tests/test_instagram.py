import re
import requests
from bs4 import BeautifulSoup
from bs4 import BeautifulSoup

url = "https://www.instagram.com/hotpointkenya/"

headers = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 "
        "Chrome/153.0 Safari/537.36"
    )
}

response = requests.get(
    url,
    headers=headers,
    timeout=20,
)

html = response.text
lower_html = html.lower()

soup = BeautifulSoup(
    html,
    "html.parser",
)

title = (
    soup.title.get_text(strip=True)
    if soup.title
    else "NONE"
)

post_links = re.findall(
    r'https://www\.instagram\.com/(?:p|reel)/[^"?]+',
    html,
)

keywords = [
    "promotion",
    "offer",
    "sale",
    "discount",
    "fridge",
    "cooker",
    "washing machine",
    "blender",
]

caption_words = [
    word
    for word in keywords
    if word in lower_html
]

print("=" * 60)
print("INSTAGRAM HTML INSPECTION")
print("=" * 60)
print("STATUS:", response.status_code)
print("HTML:", len(html))
print("POST LINKS:", len(post_links))
print("CAPTION WORDS:", caption_words)
print("HOTPOINT:", "hotpoint" in lower_html)
print("KENYA:", "kenya" in lower_html)
print("TITLE:", title)
print("=" * 60)