
Show jsonld · PY
"""Prints a compact summary of the structured data inside the saved Hotpoint
pages, so we can see where names, models and prices live. Read-only."""
import json
import re
import sys
from pathlib import Path
 
RAW = Path(__file__).resolve().parent.parent / "data" / "raw"
PAGES = ["sample_product.html", "fridges_category.html"]
BLOCK = re.compile(r'<script[^>]*application/ld\+json[^>]*>(.*?)</script>', re.S | re.I)
 
 
def short(text, n):
    text = re.sub(r"\s+", " ", text).strip()
    return text if len(text) <= n else text[:n] + " ...[cut]"
 
 
def main():
    for name in PAGES:
        path = RAW / name
        print("\n" + "=" * 70 + f"\n{name}")
        if not path.exists():
            print("  file not found - run inspect_hotpoint.py first")
            continue
        html = path.read_text(encoding="utf-8", errors="replace")
        blocks = BLOCK.findall(html)
        print(f"JSON-LD blocks: {len(blocks)}")
        for i, raw in enumerate(blocks, 1):
            try:
                data = json.loads(raw)
                kind = data.get("@type") if isinstance(data, dict) else "list"
                print(f"\n-- block {i} (type: {kind})")
                print(short(json.dumps(data, ensure_ascii=False), 1800))
            except Exception as e:
                print(f"\n-- block {i} could not be parsed: {e}")
                print(short(raw, 600))
        hits = [m.start() for m in re.finditer(r'"price"', html)]
        print(f"\n'\"price\"' appears {len(hits)} times in the page")
        for pos in hits[:3]:
            print("   ..." + short(html[max(0, pos - 150): pos + 150], 320) + "...")
 
 
if __name__ == "__main__":
    main()
 
