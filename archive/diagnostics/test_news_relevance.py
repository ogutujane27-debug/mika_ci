import sys
import re
from datetime import datetime, timezone

sys.path.insert(0, r"C:\Users\User\Desktop\mika_ci\app")
import news_collector as n

tests = [
    (
        "K24 Granola",
        "https://k24.digital/lifestyle/food-and-culinary/how-to-make-a-homemade-granola-bar-using-local-ingredients",
        "How to make a homemade granola bar using local ingredients",
    ),
    (
        "K24 Desserts",
        "https://k24.digital/lifestyle/food-and-culinary/5-desserts-you-can-make-at-home-without-a-fancy-oven",
        "5 desserts you can make at home without a fancy oven",
    ),
]

strong_product_terms = [
    "refrigerator", "refrigerators", "fridge", "fridges",
    "freezer", "freezers", "chest freezer", "display fridge",
    "side by side refrigerator", "bottom mount refrigerator",
    "top mount refrigerator", "washing machine", "washing machines",
    "washer", "washers", "tumble dryer", "clothes dryer", "dryer",
    "cooker", "cookers", "built-in oven", "electric oven", "gas oven",
    "microwave oven", "microwave", "air fryer", "gas burner",
    "gas cooker", "blender", "coffee maker", "food processor",
    "vacuum cleaner", "electric iron", "water dispenser",
    "air conditioner", "soundbar", "home theatre", "home theater",
    "smart tv", "smart television", "television", "televisions",
    "consumer electronics", "home appliances", "home appliance",
]

commercial_terms = [
    "retailer", "retailers", "retail", "manufacturer", "manufacturers",
    "distributor", "distributors", "showroom", "shop", "stores", "store",
    "product", "products", "pricing", "price", "prices", "discount",
    "promotion", "offer", "cashback", "financing", "warranty", "launch",
    "launched", "unveiled", "introduced", "new model", "new product",
    "market", "sales", "demand", "distribution", "manufacturing",
]

source = {"name": "K24"}
now = datetime.now(timezone.utc)

for label, url, listing_title in tests:
    candidate = {
        "url": url,
        "listing_title": listing_title,
    }

    article = n.fetch_article(source, candidate, now)
    combined = (article["title"] + " " + article["text"]).lower()

    print()
    print("=" * 70)
    print(label)
    print("=" * 70)
    print("TITLE:", article["title"])
    print("DATE:", article["published_date"])
    print("BRANDS:", article["brands"])
    print("CATEGORIES:", article["categories"])
    print("SIGNALS:", article["signals"])
    print("NEWS TYPE:", article["news_type"])
    print("CRIME:", n.has_crime_context(combined))
    print("CI RELEVANT:", n.is_ci_relevant(article))

    product_matches = [
        term for term in strong_product_terms
        if re.search(r"\b" + re.escape(term) + r"\b", combined)
    ]

    commercial_matches = [
        term for term in commercial_terms
        if re.search(r"\b" + re.escape(term) + r"\b", combined)
    ]

    print("STRONG PRODUCT MATCHES:", product_matches)
    print("COMMERCIAL MATCHES:", commercial_matches)
