"""Reads the SAVED fridge page (data/raw/fridges_category.html) and prints the
products it can find. Read-only: nothing is fetched and nothing is written."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "app"))
from source_collector import parse_products  # noqa: E402

PAGE = ROOT / "data" / "raw" / "fridges_category.html"


def main():
    if not PAGE.exists():
        print("Saved page not found. Run scripts/inspect_hotpoint.py first.")
        return
    products = parse_products(PAGE.read_text(encoding="utf-8", errors="replace"))
    print(f"Products found: {len(products)}")
    with_disc = [p for p in products if p["original_price"]]
    fallback = [p for p in products if p["model"] == p["handle"]]
    print(f"With a 'was' price: {len(with_disc)}   Model not detected: {len(fallback)}\n")
    print(f"{'MODEL':<22}{'BRAND':<10}{'PRICE':>10}{'WAS':>10}  NAME")
    for p in products[:25]:
        was = f"{p['original_price']:,.0f}" if p["original_price"] else "-"
        print(f"{str(p['model'])[:21]:<22}{str(p['brand'])[:9]:<10}"
              f"{p['price']:>10,.0f}{was:>10}  {p['name'][:45]}")
    if len(products) > 25:
        print(f"... and {len(products) - 25} more")


if __name__ == "__main__":
    main()
