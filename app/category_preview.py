"""
MIKA CI - category / sub-category mapping PREVIEW (READ ONLY).

Nothing in the database is changed. The database is opened read-only.
Two CSV files are written to reports/category_preview/ for review:
    all_mappings.csv      every row with its proposed mapping
    review_needed.csv     only the rows that need a human decision

Run from the mika_ci folder:
    python category_preview.py
"""

import csv
import re
import sqlite3
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "data" / "mika_competitive_intel.db"
OUT_DIR = ROOT / "reports" / "category_preview"

# ---------------------------------------------------------------------------
# Category names
# ---------------------------------------------------------------------------
REFRIG = "Refrigeration"
LAUNDRY = "Laundry & Dishwashing"
COOKING = "Cooking"
SMALL = "Small Kitchen Appliances"
COOKWARE = "Cookware"
TV = "TV & Audio"
AIR = "Air & Climate"
WATER = "Water"
HOME = "Home Care"
POWER = "Power & Backup"
MULTI = "Multi-category"

# ---------------------------------------------------------------------------
# Name rules: (category, sub_category, priority, regex)
# Higher priority wins inside the same category.
# A match in two different categories is sent to review (conflict).
# ---------------------------------------------------------------------------
NAME_RULES = [
    # Refrigeration
    (REFRIG, "Side by Side", 90, r"side[ -]?by[ -]?side|\bsbs\b"),
    (REFRIG, "Multi-door / French", 85, r"\b[34][ -]?door\b|four door|three door|french (door|type)|multi[ -]?door"),
    (REFRIG, "Bottom Mount", 80, r"bottom[ -]?mount|combination (fridge|refrigerator)"),
    (REFRIG, "Double Door (Top Mount)", 78, r"top[ -]?mount|double[ -]?door|two door|\b2[ -]?door\b"),
    (REFRIG, "Single Door", 76, r"single[ -]?door|one door|\b1[ -]?door\b"),
    (REFRIG, "Chest Freezer", 92, r"\bchest\b"),
    (REFRIG, "Upright Freezer", 91, r"upright (freezer|chiller|fridge)"),
    (REFRIG, "Wine Coolers", 70, r"\bwine\b"),
    (REFRIG, "Showcase & Glass-door", 68, r"showcase|display (cooler|chiller|fridge)|glass door.*(cooler|chiller|fridge)"),
    (REFRIG, "Beverage / Vertical Coolers", 66, r"beverage|vertical (cooler|chiller)|bottle cooler"),
    (REFRIG, "Mini", 64, r"mini ?bar|bar fridge|mini (fridge|refrigerator)"),
    (REFRIG, "Refrigeration - other", 10, r"fridge|refrigerator|freezer|(?<!water )(?<!air )\bcoolers?\b"),
    # Laundry & Dishwashing
    (LAUNDRY, "Dishwashers", 90, r"dish ?washer"),
    (LAUNDRY, "Washer-Dryer", 85, r"wash ?[+&/] ?dry|washer ?[/ -]? ?dryer|washing machine.*dryer"),
    (LAUNDRY, "Dryers", 80, r"\bdryers?\b|tumble"),
    (LAUNDRY, "Front Load", 78, r"front[ -]?load"),
    (LAUNDRY, "Top Load", 76, r"top[ -]?load"),
    (LAUNDRY, "Twin Tub / Semi-automatic", 74, r"twin[ -]?tub|single tub|semi[ -]?automatic|wash only"),
    (LAUNDRY, "Laundry - other", 10, r"washing machine|\bwasher\b|laundry"),
    # Cooking
    (COOKING, "Microwaves", 90, r"microwave"),
    (COOKING, "Pressure Cookers", 88, r"pressure cooker"),
    (COOKING, "Portable Cookers", 86, r"portable cooker|induction cooker|table ?top cooker"),
    (COOKING, "Gas Cookers", 84, r"gas cooker|standing cooker|free[ -]?standing cooker|cooker with oven|\d ?gas\b|\bgas\b.{0,40}burner"),
    (COOKING, "Hobs", 80, r"\bhobs?\b|cooktop"),
    (COOKING, "Cooker Hoods", 78, r"cooker hood|kitchen hood|\bhood\b|chimney"),
    (COOKING, "Ovens & Built-in", 70, r"\boven\b|built[ -]?in (oven|cooker)"),
    (COOKING, "Cooking - other", 10, r"(?<!rice )(?<!slow )(?<!multi )cooker\b|\bgas (stove|burner)|\bstoves?\b"),
    # Small kitchen
    (SMALL, "Air Fryers", 90, r"(?<!with )air ?fryer|deep fryer|\bfryer\b"),
    (SMALL, "Milk Frothers", 88, r"milk ?frother|frother"),
    (SMALL, "Salad Makers", 86, r"salad maker"),
    (SMALL, "Rice Cookers", 84, r"rice cooker"),
    (SMALL, "Kettles", 82, r"\bkettles?\b"),
    (SMALL, "Toasters & Sandwich Makers", 80, r"toaster|sandwich maker|sandwich press|waffle"),
    (SMALL, "Coffee & Grinders", 78, r"coffee|espresso|spice grinder"),
    (SMALL, "Juicers", 76, r"juicer|juice extractor"),
    (SMALL, "Blenders", 74, r"blender|smoothie"),
    (SMALL, "Mixers", 72, r"mixer"),
    (SMALL, "Food Processors", 70, r"food processor|kitchen machine|food preparer|chopper|slicer|mincer|meat grinder"),
    (SMALL, "Small Kitchen - other", 5, r"egg boiler|food steamer|\bsteamer\b"),
    # Cookware
    (COOKWARE, "Cookware Sets", 60, r"cookware|pan set|frying pan|fry pan|saucepan|stock ?pot|wok pan|wok set|non-stick pan|casserole"),
    # TV & Audio
    (TV, "TVs", 80, r"\btvs?\b|television|qled|\boled\b|\buhd\b"),
    (TV, "Soundbars & Home Theatre", 78, r"sound ?bar|home theat|subwoofer|\bspeakers?\b|hi-?fi"),
    (TV, "Set-top Boxes", 76, r"set[ -]?top|decoder|dvb"),
    # Air & Climate
    (AIR, "Air Conditioners", 90, r"air[ -]?condition|split (unit|ac|inverter)|\bbtu\b|\d+ ?btu"),
    (AIR, "Air Curtains", 85, r"air curtain"),
    (AIR, "Heaters", 80, r"(?<!water )heater|radiator|fireplace"),
    (AIR, "Fans", 70, r"(?<!assisted )(?<!forced )\bfans?\b"),
    (AIR, "Humidity & Air Quality", 75, r"dehumidif|humidifier|purifier"),
    # Water
    (WATER, "Water Dispensers", 90, r"water dispenser|water cooler"),
    (WATER, "Water Heaters", 88, r"water heater|geyser|instant water"),
    # Home care
    (HOME, "Garment Steamers", 90, r"garment steamer|clothes steamer|nano[ -]?ionic steamer"),
    (HOME, "Vacuum Cleaners", 85, r"vacuum cleaner|vacuum(?! glass)(?! insulated)"),
    (HOME, "Irons", 80, r"(?<!cast )\birons?\b|ironing|steam iron"),
    # Power & Backup
    (POWER, "Generators", 90, r"generator|gasoline set|diesel set"),
    (POWER, "Voltage Regulators", 85, r"voltage regulator|stabili[sz]er|\bavr\b"),
    (POWER, "Power Protection Devices", 80, r"\bups\b|surge|power protection"),
]
# Weak name rules: dropped when a stronger rule matches (e.g. a "fan" or a
# "water dispenser" inside a fridge description), promoted when alone.
WEAK_NAME_SUBS = {"Fans", "Ovens & Built-in", "Water Dispensers", "Vacuum Cleaners"}
NAME_RULES_C = [(c, s, p, re.compile(rx, re.I)) for c, s, p, rx in NAME_RULES]

# Offers that cover many categories and name no product.
MULTI_RX = re.compile(
    r"up to \d+% off|clearance sale|selected appliances|everything you need|"
    r"flash offers?|monthly offers?|big discounts|sale extended|hot ?5|"
    r"extra \d+% off|night rush",
    re.I,
)

# ---------------------------------------------------------------------------
# Raw category values already used by the collectors (findings.category)
# level: 'specific' = sub-category known, 'category' = only category known
# ---------------------------------------------------------------------------
RAW_MAP = {
    "double door (top mount freezer)": (REFRIG, "Double Door (Top Mount)", "specific"),
    "side by side": (REFRIG, "Side by Side", "specific"),
    "chest": (REFRIG, "Chest Freezer", "specific"),
    "combination (bottom mount freezer)": (REFRIG, "Bottom Mount", "specific"),
    "single door": (REFRIG, "Single Door", "specific"),
    "upright": (REFRIG, "Upright Freezer", "specific"),
    "vertical coolers": (REFRIG, "Beverage / Vertical Coolers", "specific"),
    "mini": (REFRIG, "Mini", "specific"),
    "4 door": (REFRIG, "Multi-door / French", "specific"),
    "wine coolers": (REFRIG, "Wine Coolers", "specific"),
    "instaview": (REFRIG, "Refrigeration - other", "category"),
    "refrigeration": (REFRIG, "Refrigeration - other", "category"),
    "blenders": (SMALL, "Blenders", "specific"),
    "hand blenders": (SMALL, "Blenders", "specific"),
    "juicers": (SMALL, "Juicers", "specific"),
    "fryers": (SMALL, "Air Fryers", "specific"),
    "hand mixers": (SMALL, "Mixers", "specific"),
    "sandwich makers": (SMALL, "Toasters & Sandwich Makers", "specific"),
    "toasters": (SMALL, "Toasters & Sandwich Makers", "specific"),
    "rice cookers": (SMALL, "Rice Cookers", "specific"),
    "choppers": (SMALL, "Food Processors", "specific"),
    "coffee & spice grinders": (SMALL, "Coffee & Grinders", "specific"),
    "food processors": (SMALL, "Food Processors", "specific"),
    "kitchen machines": (SMALL, "Food Processors", "specific"),
    "television": (TV, "TVs", "specific"),
    "tvs": (TV, "TVs", "specific"),
}

# ---------------------------------------------------------------------------
# Web-shop slug tokens (Bruhm / Haier categories)
# ---------------------------------------------------------------------------
SLUG_MAP = {
    "split-inverter-ac": (AIR, "Air Conditioners", "specific"),
    "split-ac": (AIR, "Air Conditioners", "specific"),
    "floor-standing-ac": (AIR, "Air Conditioners", "specific"),
    "air-conditioners": (AIR, "Air Conditioners", "specific"),
    "ac-heat-pump": (AIR, "Air & Climate - other", "category"),
    "air-curtain": (AIR, "Air Curtains", "specific"),
    "standing-fan": (AIR, "Fans", "specific"),
    "single-door": (REFRIG, "Single Door", "specific"),
    "defrost-single-door": (REFRIG, "Single Door", "specific"),
    "double-door": (REFRIG, "Double Door (Top Mount)", "specific"),
    "defrost-top-mount": (REFRIG, "Double Door (Top Mount)", "specific"),
    "no-frost-top-mount": (REFRIG, "Double Door (Top Mount)", "specific"),
    "no-frost-sbs": (REFRIG, "Side by Side", "specific"),
    "no-frost-multi-door": (REFRIG, "Multi-door / French", "specific"),
    "defrost-bottom-mount": (REFRIG, "Bottom Mount", "specific"),
    "no-frost-bottom-mount": (REFRIG, "Bottom Mount", "specific"),
    "beverage-cooler": (REFRIG, "Beverage / Vertical Coolers", "specific"),
    "glass-door": (REFRIG, "Showcase & Glass-door", "specific"),
    "show-case": (REFRIG, "Showcase & Glass-door", "specific"),
    "upright-freezer": (REFRIG, "Upright Freezer", "specific"),
    "chest-freezer": (REFRIG, "Chest Freezer", "specific"),
    "freezers": (REFRIG, "Refrigeration - other", "category"),
    "refrigerator": (REFRIG, "Refrigeration - other", "category"),
    "fridge": (REFRIG, "Refrigeration - other", "category"),
    "fridge-freezer": (REFRIG, "Refrigeration - other", "category"),
    "water-dispenser": (WATER, "Water Dispensers", "specific"),
    "water-heater": (WATER, "Water Heaters", "specific"),
    "television": (TV, "TVs", "specific"),
    "ultra-high-definition": (TV, "TVs", "specific"),
    "full-high-definition": (TV, "TVs", "specific"),
    "high-definition": (TV, "TVs", "specific"),
    "tv-audio": (TV, "TV & Audio - other", "category"),
    "gas-cooker": (COOKING, "Gas Cookers", "specific"),
    "hob": (COOKING, "Hobs", "specific"),
    "hood": (COOKING, "Cooker Hoods", "specific"),
    "microwaves": (COOKING, "Microwaves", "specific"),
    "cooker": (COOKING, "Cooking - other", "category"),
    "built-in-appliances": (COOKING, "Ovens & Built-in", "category"),
    "top-load-washer": (LAUNDRY, "Top Load", "specific"),
    "front-load-washer": (LAUNDRY, "Front Load", "specific"),
    "twin-tub-washer": (LAUNDRY, "Twin Tub / Semi-automatic", "specific"),
    "washers-dryers": (LAUNDRY, "Laundry - other", "category"),
    "laundry": (LAUNDRY, "Laundry - other", "category"),
    "kettle": (SMALL, "Kettles", "specific"),
    "blender": (SMALL, "Blenders", "specific"),
    "air-fryer": (SMALL, "Air Fryers", "specific"),
    "sandwich-maker": (SMALL, "Toasters & Sandwich Makers", "specific"),
    "rice-cooker": (SMALL, "Rice Cookers", "specific"),
    "toaster": (SMALL, "Toasters & Sandwich Makers", "specific"),
    "iron": (HOME, "Irons", "specific"),
    "generator": (POWER, "Generators", "specific"),
    "gasoline": (POWER, "Generators", "specific"),
    "diesel": (POWER, "Generators", "specific"),
    "automatic-voltage-regulator": (POWER, "Voltage Regulators", "specific"),
}
# Tokens that carry no category meaning (brand tags, umbrella labels, modifiers).
IGNORED_TOKENS = {
    "haier", "jtc", "bruhm-black", "small-appliances",
    "kitchen-and-small-appliances", "grill", "solo", "convection",
    "60-x-60", "50-x-50", "80-x-60", "90-x-60", "60-x-60-gas-hob",
    "90-x-60-gas-hob",
}


def slug_hits(raw):
    hits = []
    for token in (raw or "").lower().split(","):
        token = token.strip()
        if token in SLUG_MAP:
            hits.append(SLUG_MAP[token] + ("slug",))
        elif token.endswith("-gas-hob"):
            hits.append((COOKING, "Hobs", "specific", "slug"))
    return hits


def classify(text, raw_value="", use_slug=False):
    """Return (category, sub_category, confidence, status, method, reason)."""
    hits = []  # (category, sub, level, source, priority)
    text = text or ""

    for cat, sub, prio, rx in NAME_RULES_C:
        if rx.search(text):
            if sub.endswith("- other"):
                level = "category"
            elif sub in WEAK_NAME_SUBS:
                level = "weak"
            else:
                level = "specific"
            hits.append((cat, sub, level, "name", prio))

    raw_key = (raw_value or "").strip().lower()
    if use_slug:
        for cat, sub, level, src in slug_hits(raw_value):
            hits.append((cat, sub, level, src, 50 if level == "specific" else 5))
    elif raw_key in RAW_MAP:
        cat, sub, level = RAW_MAP[raw_key]
        hits.append((cat, sub, level, "raw", 50 if level == "specific" else 5))

    if not hits:
        if MULTI_RX.search(text) or raw_key in ("multiple", "general appliances"):
            return (MULTI, "", "low", "review", "text_pattern",
                    "offer spans many categories, no product named")
        return ("", "", "", "review", "none", "no rule matched")

    specific = [h for h in hits if h[2] == "specific"]
    weak = [h for h in hits if h[2] == "weak"]
    category_only = [h for h in hits if h[2] == "category"]

    # Weak hits are ignored when a specific one exists, promoted otherwise.
    strong = specific if specific else weak

    if strong:
        cats = {h[0] for h in strong}
        if len(cats) >= 3:
            return (MULTI, "", "low", "review", "multi_category",
                    "names products in several categories: " + ", ".join(sorted(cats)))
        if len(cats) > 1:
            detail = "; ".join(sorted({f"{h[0]} / {h[1]} ({h[3]})" for h in strong}))
            return ("", "", "", "review", "conflict", "conflict: " + detail)
        cat = next(iter(cats))
        best = max(strong, key=lambda h: h[4])
        sources = "+".join(sorted({h[3] for h in strong if h[1] == best[1]}))
        return (cat, best[1], "high", "mapped", sources, "")

    cats = {h[0] for h in category_only}
    if len(cats) > 1:
        detail = "; ".join(sorted({f"{h[0]} ({h[3]})" for h in category_only}))
        return ("", "", "", "review", "conflict", "conflict: " + detail)
    best = max(category_only, key=lambda h: h[4])
    sources = "+".join(sorted({h[3] for h in category_only}))
    return (best[0], best[1], "medium", "mapped", sources, "")


# ---------------------------------------------------------------------------
# Load rows from every table that carries a category
# ---------------------------------------------------------------------------
def load_rows(cur):
    rows = []  # dict(source, key, brand, name, raw, text, use_slug)

    for fid, ftype, brand, raw, summary, evidence, pname in cur.execute(
        """
        SELECT f.finding_id, f.finding_type, f.brand, f.category,
               f.summary, f.evidence_text, p.product_name
        FROM findings f
        LEFT JOIN price_observations p ON p.finding_id = f.finding_id
        ORDER BY f.finding_id
        """
    ):
        if ftype == "price":
            text = f"{pname or ''} {summary or ''}"
        else:
            text = f"{summary or ''} {(evidence or '')[:300]}"
        name = (pname or summary or "")[:90]
        rows.append(dict(source=f"findings ({ftype})", key=fid, brand=brand or "",
                         name=name, raw=raw or "", text=text, use_slug=False))

    for id_, name, raw in cur.execute(
        "SELECT sku, product_name, category FROM bruhm_products"
    ):
        rows.append(dict(source="bruhm_products", key=id_, brand="Bruhm",
                         name=name or "", raw=raw or "", text=name or "", use_slug=True))

    for id_, name, raw in cur.execute(
        "SELECT sku, product_name, category FROM haier_products"
    ):
        rows.append(dict(source="haier_products", key=id_, brand="Haier",
                         name=name or "", raw=raw or "", text=name or "", use_slug=True))

    for id_, name, raw in cur.execute(
        "SELECT product_key, product_name, category FROM k_elec_products"
    ):
        rows.append(dict(source="k_elec_products", key=id_, brand="K-Elec",
                         name=name or "", raw=raw or "", text=name or "", use_slug=False))
    return rows



def main():
    if not DB_PATH.exists():
        print(f"Database not found: {DB_PATH}")
        return

    conn = sqlite3.connect(f"file:{DB_PATH.as_posix()}?mode=ro", uri=True)
    cur = conn.cursor()
    rows = load_rows(cur)
    conn.close()

    results = []
    for r in rows:
        cat, sub, conf, status, method, reason = classify(
            r["text"], r["raw"], r["use_slug"]
        )
        results.append({**r, "category": cat, "sub_category": sub,
                        "confidence": conf, "status": status,
                        "method": method, "reason": reason})

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    fields = ["source", "key", "brand", "name", "raw", "category", "sub_category",
              "confidence", "status", "method", "reason"]
    with open(OUT_DIR / "all_mappings.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(results)
    review = [r for r in results if r["status"] == "review"]
    with open(OUT_DIR / "review_needed.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(review)

    total = len(results)
    print("MIKA CI - CATEGORY PREVIEW (read only, nothing written to the database)")
    print("=" * 74)
    print(f"Rows examined: {total}\n")

    # 1. Status by source
    print("1. STATUS BY SOURCE")
    print(f"   {'source':<26}{'rows':>6}{'high':>7}{'medium':>8}{'review':>8}")
    by_source = defaultdict(Counter)
    for r in results:
        by_source[r["source"]]["rows"] += 1
        if r["status"] == "review":
            by_source[r["source"]]["review"] += 1
        else:
            by_source[r["source"]][r["confidence"]] += 1
    for s in sorted(by_source):
        c = by_source[s]
        print(f"   {s:<26}{c['rows']:>6}{c['high']:>7}{c['medium']:>8}{c['review']:>8}")
    mapped = sum(1 for r in results if r["status"] == "mapped")
    print(f"\n   Mapped: {mapped}   Needs review: {len(review)}   "
          f"({mapped / total:.0%} mapped)\n")

    # 2. Category distribution
    print("2. CATEGORY DISTRIBUTION (mapped rows)")
    cat_count = Counter(r["category"] for r in results if r["status"] == "mapped")
    for cat, n in cat_count.most_common():
        print(f"   {n:>5}  {cat}")
    print(f"   {len(review):>5}  REVIEW\n")

    # 3. Sub-category distribution
    print("3. SUB-CATEGORY DISTRIBUTION")
    sub_count = defaultdict(Counter)
    for r in results:
        if r["status"] == "mapped":
            sub_count[r["category"]][r["sub_category"]] += 1
    for cat, _ in cat_count.most_common():
        print(f"   {cat}")
        for sub, n in sub_count[cat].most_common():
            print(f"       {n:>5}  {sub}")
    print()

    # 4. Review list
    print("4. NEEDS REVIEW (first 40; full list in review_needed.csv)")
    reasons = Counter(r["reason"].split(":")[0] if r["reason"].startswith("conflict")
                      else r["reason"] for r in review)
    for reason, n in reasons.most_common():
        print(f"   {n:>5}  {reason}")
    print()
    for r in review[:40]:
        print(f"   [{r['source']}] {r['brand']} | {r['name'][:60]}")
        print(f"        raw: {r['raw'][:40]} | {r['reason'][:110]}")
    print()

    # 5. Medium confidence
    medium = [r for r in results if r["status"] == "mapped" and r["confidence"] == "medium"]
    print(f"5. MEDIUM CONFIDENCE ({len(medium)} rows: category known, sub-category not)")
    med_count = Counter(f"{r['category']} / {r['sub_category']}" for r in medium)
    for label, n in med_count.most_common(10):
        print(f"   {n:>5}  {label}")
    print("\nFiles written:")
    print(f"   {OUT_DIR / 'all_mappings.csv'}")
    print(f"   {OUT_DIR / 'review_needed.csv'}")


if __name__ == "__main__":
    main()
