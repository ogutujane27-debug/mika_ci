"""Reads product data out of Hotpoint pages. Read-only: no database writes here.

Hotpoint's pages carry their product list as JSON inside the page's data
script (not in the visible HTML), e.g.
  "handle":"von-vrb-247nrak-...","name":"VON VRB-247NRAK ...","price":77995,
  "originalPrice":"$undefined" or 84995,"brand":"Von","subCategory":"..."
"""
import re

HANDLE_SPLIT = '"handle":"'
UNIT_LIKE = re.compile(r"^\d+[A-Za-z]{1,4}$")          # 205L, 1400RPM, 10KG
HYPHEN_CODE = re.compile(r"^[A-Za-z0-9]+(?:[-/][A-Za-z0-9]+)+$")
PLAIN_CODE = re.compile(r"^[A-Za-z0-9]{5,}$")


def _has_letter_and_digit(tok):
    return any(c.isalpha() for c in tok) and any(c.isdigit() for c in tok)


def guess_model(name, handle=None):
    """Best-effort model code from a product name; falls back to the URL handle
    so every product still has a stable key."""
    tokens = [t.strip("(),;:") for t in name.split()]
    for tok in tokens:                                   # e.g. RD-27DR4SA
        if HYPHEN_CODE.match(tok) and _has_letter_and_digit(tok) and len(tok) >= 5:
            return tok.upper()
    for tok in tokens:                                   # e.g. WT3K9022UB, 43A6Q
        if PLAIN_CODE.match(tok) and _has_letter_and_digit(tok) and not UNIT_LIKE.match(tok):
            return tok.upper()
    return handle


def _first(pattern, chunk):
    m = re.search(pattern, chunk)
    return m.group(1) if m else None


def parse_products(html):
    """Return a list of dicts: handle, name, model, brand, sub_category,
    price, original_price (None when no discount shown)."""
    text = html.replace('\\"', '"')                      # data is JSON-in-a-string
    parts = text.split(HANDLE_SPLIT)[1:]
    seen, products = set(), []
    for part in parts:
        handle = part.split('"', 1)[0]
        if handle in seen:
            continue
        chunk = part[:4000]                              # stays within this product
        name = _first(r'"name":"([^"]*)"', chunk)
        price = _first(r'"price":(\d+(?:\.\d+)?)', chunk)
        if not name or price is None:
            continue
        orig = _first(r'"originalPrice":(\d+(?:\.\d+)?)', chunk)
        seen.add(handle)
        products.append({
            "handle": handle,
            "name": name.replace("\\u0026", "&"),
            "model": guess_model(name, handle),
            "brand": _first(r'"brand":"([^"]*)"', chunk),
            "sub_category": _first(r'"subCategory":"([^"]*)"', chunk),
            "price": float(price),
            "original_price": float(orig) if orig else None,
        })
    return products
