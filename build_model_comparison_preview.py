import csv
import re
from pathlib import Path
from collections import defaultdict


# ============================================================
# MIKA CI
# MODEL / PRODUCT COMPARISON PREVIEW
#
# IMPORTANT:
# - Preview only
# - NO SQLite writes
# - No automatic cross-brand model equivalence
# - Name similarity is supporting evidence only
# ============================================================


BASE = Path(__file__).resolve().parent

MIKA_FILE = (
    BASE
    / "reports"
    / "mika_catalogue_preview"
    / "mika_catalogue_preview.csv"
)

BRUHM_FILE = (
    BASE
    / "reports"
    / "mika_catalogue_preview"
    / "bruhm"
    / "bruhm_catalogue_preview.csv"
)

HAIER_FILE = (
    BASE
    / "reports"
    / "mika_catalogue_preview"
    / "HAIER"
    / "haier_catalogue_preview.csv"
)

OUTPUT_DIR = (
    BASE
    / "reports"
    / "mika_catalogue_preview"
    / "mika_position"
    / "model_comparison"
)

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================
# CSV INPUT
# ============================================================

def read_csv(path):
    if not path.exists():
        raise SystemExit(f"INPUT NOT FOUND: {path}")

    with path.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as f:
        rows = list(csv.DictReader(f))

    if not rows:
        raise SystemExit(f"EMPTY INPUT: {path}")

    return rows


mika_rows = read_csv(MIKA_FILE)
bruhm_rows = read_csv(BRUHM_FILE)
haier_rows = read_csv(HAIER_FILE)


# ============================================================
# NORMALIZE SOURCE RECORDS
# ============================================================

def normalize_mika(row):
    return {
        "brand": "MIKA",
        "item_name": (row.get("item_name") or "").strip(),
        "model_no": (row.get("model_no") or "").strip(),
        "category": (row.get("category") or "").strip(),
        "sub_category": (row.get("sub_category") or "").strip(),
        "product_scope": (row.get("product_scope") or "").strip(),
        "product_url": (row.get("product_url") or "").strip(),
        "source": (row.get("source") or "").strip(),
    }


def normalize_bruhm(row):
    return {
        "brand": "BRUHM",
        "item_name": (row.get("product_name") or "").strip(),
        "model_no": (row.get("sku") or "").strip(),
        "category": (row.get("category") or "").strip(),
        "sub_category": (row.get("sub_category") or "").strip(),
        "product_scope": (row.get("product_scope") or "").strip(),
        "product_url": (row.get("product_url") or "").strip(),
        "source": "BRUHM catalogue preview",
    }


def normalize_haier(row):
    return {
        "brand": "HAIER",
        "item_name": (row.get("product_name") or "").strip(),
        "model_no": (row.get("sku") or "").strip(),
        "category": (row.get("category") or "").strip(),
        "sub_category": (row.get("sub_category") or "").strip(),
        "product_scope": (row.get("product_scope") or "").strip(),
        "product_url": (
            row.get("product_url")
            or row.get("url")
            or ""
        ).strip(),
        "source": "HAIER catalogue preview",
    }


catalogues = {
    "MIKA": [normalize_mika(r) for r in mika_rows],
    "BRUHM": [normalize_bruhm(r) for r in bruhm_rows],
    "HAIER": [normalize_haier(r) for r in haier_rows],
}


# ============================================================
# GENERAL HELPERS
# ============================================================

def has_identifier(row):
    return bool(row["model_no"])


def product_key(row):
    return (
        row["category"].strip().lower(),
        row["sub_category"].strip().lower(),
    )


def safe_name(value):
    value = value or ""
    value = value.lower()

    replacements = {
        "-": " ",
        "_": " ",
        "/": " ",
        ",": " ",
        "(": " ",
        ")": " ",
    }

    for old, new in replacements.items():
        value = value.replace(old, new)

    return " ".join(value.split())


def compact_text(row):
    return " ".join(
        [
            row.get("item_name", ""),
            row.get("category", ""),
            row.get("sub_category", ""),
            row.get("product_scope", ""),
        ]
    )


def similarity_tokens(a, b):
    """
    Token overlap is retained only as a supporting signal.

    It is NEVER sufficient to declare products comparable.
    """

    stop = {
        "mika",
        "bruhm",
        "haier",
        "the",
        "and",
        "with",
        "for",
        "new",
        "model",
        "series",
        "black",
        "white",
        "silver",
        "stainless",
        "steel",
        "appliance",
        "appliances",
    }

    ta = {
        x
        for x in safe_name(a).split()
        if len(x) >= 3 and x not in stop
    }

    tb = {
        x
        for x in safe_name(b).split()
        if len(x) >= 3 and x not in stop
    }

    if not ta or not tb:
        return 0.0

    return len(ta & tb) / len(ta | tb)


# ============================================================
# ATTRIBUTE EXTRACTION
# ============================================================

def extract_btu(text):
    """
    Extract common AC capacity expressions.

    Examples:
    9K
    9000 BTU
    12K BTU
    12000BTU
    18,000 BTU
    24K
    """

    text = safe_name(text)

    patterns = [
        r"\b(9|12|18|24)\s*k\s*(?:btu)?\b",
        r"\b(9000|12000|18000|24000)\s*btu\b",
        r"\b(9|12|18|24)\s*000\s*btu\b",
    ]

    for pattern in patterns:
        match = re.search(pattern, text)

        if not match:
            continue

        value = match.group(1)

        try:
            number = int(value)
        except ValueError:
            continue

        if number in {9, 12, 18, 24}:
            return number * 1000

        if number in {9000, 12000, 18000, 24000}:
            return number

    return None


def extract_capacity_litres(text):
    """
    Extract common refrigerator/freezer capacity values.

    This is deliberately conservative.
    """

    text = safe_name(text)

    patterns = [
        r"\b(\d{2,4})\s*(?:litre|litres|liter|liters|l)\b",
        r"\b(\d{2,4})\s*lt\b",
        r"\b(\d{2,4})l\b",
    ]

    values = []

    for pattern in patterns:
        for match in re.finditer(pattern, text):
            try:
                value = int(match.group(1))
            except ValueError:
                continue

            if 20 <= value <= 1000:
                values.append(value)

    if not values:
        return None

    return max(values)


def extract_burners(text):
    text = safe_name(text)

    patterns = [
        r"\b([2-6])\s*gas\s*burner",
        r"\b([2-6])\s*burners?\b",
        r"\b([2-6])\s*burner\b",
    ]

    for pattern in patterns:
        match = re.search(pattern, text)

        if match:
            return int(match.group(1))

    return None


def extract_inverter(text):
    text = safe_name(text)

    if "non inverter" in text:
        return "NON_INVERTER"

    if re.search(r"\binverter\b", text):
        return "INVERTER"

    return None


def extract_installation(text):
    text = safe_name(text)

    if "built in" in text:
        return "BUILT_IN"

    if "freestanding" in text or "free standing" in text:
        return "FREESTANDING"

    return None


def extract_width_cm(text):
    text = safe_name(text)

    patterns = [
        r"\b(50|55|60|70|75|80|90)\s*cm\b",
        r"\b(50|55|60|70|75|80|90)cm\b",
    ]

    for pattern in patterns:
        match = re.search(pattern, text)

        if match:
            return int(match.group(1))

    return None


def extract_tv_inches(text):
    text = safe_name(text)

    patterns = [
        r"\b(24|32|40|42|43|50|55|58|60|65|70|75|85|86|98)\s*(?:inch|inches|in)\b",
        r"\b(24|32|40|42|43|50|55|58|60|65|70|75|85|86|98)\s*(?:\"|in)\b",
    ]

    for pattern in patterns:
        match = re.search(pattern, text)

        if match:
            return int(match.group(1))

    return None


def extract_features(row):
    text = compact_text(row)

    return {
        "btu": extract_btu(text),
        "litres": extract_capacity_litres(text),
        "burners": extract_burners(text),
        "inverter": extract_inverter(text),
        "installation": extract_installation(text),
        "width_cm": extract_width_cm(text),
        "tv_inches": extract_tv_inches(text),
    }


# ============================================================
# PRODUCT FAMILY / CONFIGURATION SIGNALS
# ============================================================

def product_family(row):
    text = safe_name(
        " ".join(
            [
                row.get("category", ""),
                row.get("sub_category", ""),
                row.get("item_name", ""),
            ]
        )
    )

    rules = [
        (
            "AIR_CONDITIONER",
            [
                "air conditioner",
                "air conditioning",
                "split ac",
                "split air",
                "inverter ac",
            ],
        ),
        (
            "OVEN",
            [
                "oven",
                "built in oven",
            ],
        ),
        (
            "COOKER_STOVE",
            [
                "gas cooker",
                "gas stove",
                "cooker",
                "stove",
                "gas burner",
            ],
        ),
        (
            "REFRIGERATOR",
            [
                "refrigerator",
                "fridge",
                "double door",
                "side by side",
                "top mount",
                "bottom mount",
                "freezer",
            ],
        ),
        (
            "TV",
            [
                "television",
                "smart tv",
                "android tv",
                "qled",
                "oled",
                "led tv",
                "tv ",
            ],
        ),
        (
            "WASHING_MACHINE",
            [
                "washing machine",
                "washer",
                "washer dryer",
            ],
        ),
        (
            "MICROWAVE",
            [
                "microwave",
            ],
        ),
        (
            "BLENDER",
            [
                "blender",
            ],
        ),
        (
            "AIR_FRYER",
            [
                "air fryer",
            ],
        ),
        (
            "KETTLE",
            [
                "kettle",
            ],
        ),
    ]

    for family, terms in rules:
        for term in terms:
            if term in text:
                return family

    return None


# ============================================================
# BRAND / SOURCE INTEGRITY
# ============================================================

KNOWN_BRANDS = {
    "MIKA",
    "BRUHM",
    "HAIER",
    "JTC",
    "HOTPOINT",
    "RAMTONS",
    "HISENSE",
    "SAMSUNG",
    "LG",
    "MIDEA",
    "VITRON",
    "ARMCO",
    "PHILIPS",
    "TCL",
    "MOULINEX",
    "TEFAL",
    "KRUPS",
    "SCL",
    "BERKLAYS",
}


def source_brand_integrity(row):
    """
    Detect cases where the supplied source brand conflicts with
    explicit brand wording in the product record.

    We DO NOT change the source brand.
    We flag the record instead.
    """

    declared_brand = row["brand"].upper().strip()

    text = safe_name(
        " ".join(
            [
                row.get("item_name", ""),
                row.get("product_scope", ""),
            ]
        )
    )

    conflicts = []

    for brand in KNOWN_BRANDS:
        if brand == declared_brand:
            continue

        brand_pattern = r"\b" + re.escape(brand.lower()) + r"\b"

        if re.search(brand_pattern, text):
            conflicts.append(brand)

    if conflicts:
        return (
            "SOURCE_BRAND_CONFLICT",
            ",".join(sorted(conflicts)),
        )

    return "OK", ""


# ============================================================
# FEATURE COMPARISON
# ============================================================

def compare_feature(
    name,
    mika_value,
    competitor_value,
):
    if mika_value is None or competitor_value is None:
        return "UNKNOWN"

    if mika_value == competitor_value:
        return "MATCH"

    return "CONFLICT"


def compare_features(mika, competitor):
    mf = extract_features(mika)
    cf = extract_features(competitor)

    results = {}

    results["btu"] = compare_feature(
        "btu",
        mf["btu"],
        cf["btu"],
    )

    results["litres"] = compare_feature(
        "litres",
        mf["litres"],
        cf["litres"],
    )

    results["burners"] = compare_feature(
        "burners",
        mf["burners"],
        cf["burners"],
    )

    results["inverter"] = compare_feature(
        "inverter",
        mf["inverter"],
        cf["inverter"],
    )

    results["installation"] = compare_feature(
        "installation",
        mf["installation"],
        cf["installation"],
    )

    results["width_cm"] = compare_feature(
        "width_cm",
        mf["width_cm"],
        cf["width_cm"],
    )

    results["tv_inches"] = compare_feature(
        "tv_inches",
        mf["tv_inches"],
        cf["tv_inches"],
    )

    return mf, cf, results


# ============================================================
# HARD CONFLICT RULES
# ============================================================

def hard_conflict_reasons(
    mika,
    competitor,
    feature_results,
):
    reasons = []

    mika_family = product_family(mika)
    competitor_family = product_family(competitor)

    if (
        mika_family
        and competitor_family
        and mika_family != competitor_family
    ):
        reasons.append(
            f"PRODUCT_FAMILY_CONFLICT:{mika_family}!={competitor_family}"
        )

    # AC capacity is a hard compatibility requirement.
    if feature_results["btu"] == "CONFLICT":
        reasons.append("BTU_CAPACITY_CONFLICT")

    # Inverter/non-inverter is a material technical difference.
    if feature_results["inverter"] == "CONFLICT":
        reasons.append(
            "INVERTER_CONFIGURATION_CONFLICT"
        )

    # Burner count is material for cooker/stove comparison.
    if feature_results["burners"] == "CONFLICT":
        reasons.append("BURNER_COUNT_CONFLICT")

    # Installation configuration is material.
    if feature_results["installation"] == "CONFLICT":
        reasons.append(
            "INSTALLATION_CONFIGURATION_CONFLICT"
        )

    # TV screen size conflict.
    if feature_results["tv_inches"] == "CONFLICT":
        reasons.append("TV_SCREEN_SIZE_CONFLICT")

    return reasons


# ============================================================
# MATCH ASSESSMENT
# ============================================================

def assess_candidate(mika, competitor):
    """
    Returns a structured assessment.

    Levels:
      STRONG_COMPARABLE
      COMPARABLE
      TYPE_ONLY
      NO_DEFENSIBLE_MATCH

    No level means model equivalence.
    """

    mika_integrity, mika_conflicts = source_brand_integrity(
        mika
    )

    competitor_integrity, competitor_conflicts = (
        source_brand_integrity(competitor)
    )

    feature_mika, feature_competitor, feature_results = (
        compare_features(
            mika,
            competitor,
        )
    )

    name_score = similarity_tokens(
        mika["item_name"],
        competitor["item_name"],
    )

    hard_conflicts = hard_conflict_reasons(
        mika,
        competitor,
        feature_results,
    )

    reasons = []

    if mika_integrity != "OK":
        reasons.append(
            f"MIKA_SOURCE_BRAND_CONFLICT:{mika_conflicts}"
        )

    if competitor_integrity != "OK":
        reasons.append(
            f"COMPETITOR_SOURCE_BRAND_CONFLICT:{competitor_conflicts}"
        )

    reasons.extend(hard_conflicts)

    mika_family = product_family(mika)
    competitor_family = product_family(competitor)

    if mika_family is None or competitor_family is None:
        reasons.append("PRODUCT_FAMILY_NOT_CONFIRMED")

    if mika_family and competitor_family:
        if mika_family == competitor_family:
            reasons.append("PRODUCT_FAMILY_MATCH")
        else:
            reasons.append("PRODUCT_FAMILY_MISMATCH")

    # --------------------------------------------------------
    # Any hard conflict means this candidate cannot be used as
    # a genuine comparable.
    # --------------------------------------------------------

    if hard_conflicts:
        return {
            "match_level": "NO_DEFENSIBLE_MATCH",
            "confidence": "LOW",
            "name_score": name_score,
            "reasons": reasons,
            "feature_mika": feature_mika,
            "feature_competitor": feature_competitor,
            "feature_results": feature_results,
        }

    # --------------------------------------------------------
    # Source-brand integrity conflict also blocks comparison.
    # We do not silently correct the source.
    # --------------------------------------------------------

    if (
        mika_integrity != "OK"
        or competitor_integrity != "OK"
    ):
        return {
            "match_level": "NO_DEFENSIBLE_MATCH",
            "confidence": "LOW",
            "name_score": name_score,
            "reasons": reasons,
            "feature_mika": feature_mika,
            "feature_competitor": feature_competitor,
            "feature_results": feature_results,
        }

    # --------------------------------------------------------
    # Require same family where family can be established.
    # --------------------------------------------------------

    if (
        mika_family
        and competitor_family
        and mika_family != competitor_family
    ):
        return {
            "match_level": "NO_DEFENSIBLE_MATCH",
            "confidence": "LOW",
            "name_score": name_score,
            "reasons": reasons,
            "feature_mika": feature_mika,
            "feature_competitor": feature_competitor,
            "feature_results": feature_results,
        }

    # --------------------------------------------------------
    # Count positive technical evidence.
    # --------------------------------------------------------

    feature_names = [
        "btu",
        "litres",
        "burners",
        "inverter",
        "installation",
        "width_cm",
        "tv_inches",
    ]

    known_matches = sum(
        feature_results[x] == "MATCH"
        for x in feature_names
    )

    # --------------------------------------------------------
    # Width-only protection for built-in ovens and cooker hoods.
    #
    # Width is useful for catalogue architecture, but by itself
    # it does not establish a sufficiently comparable product.
    # --------------------------------------------------------

    cooking_subcategory = str(
        mika.get("sub_category", "")
    ).strip().lower()

    width_only_categories = {
        "built-in ovens",
        "cooker hoods",
    }

    if cooking_subcategory in width_only_categories:
        non_width_matches = sum(
            feature_results[x] == "MATCH"
            for x in [
                "btu",
                "litres",
                "burners",
                "inverter",
                "installation",
                "tv_inches",
            ]
        )

        if (
            feature_results["width_cm"] == "MATCH"
            and non_width_matches == 0
        ):
            reasons.append(
                "WIDTH_ONLY_TECHNICAL_EVIDENCE"
            )

            return {
                "match_level": "TYPE_ONLY",
                "confidence": "LOW",
                "name_score": name_score,
                "reasons": reasons,
                "feature_mika": feature_mika,
                "feature_competitor": feature_competitor,
                "feature_results": feature_results,
            }

    # --------------------------------------------------------
    # Strong comparable:
    #
    # Same family + at least two matching technical signals.
    #
    # Name similarity is not enough.
    # --------------------------------------------------------

    if known_matches >= 2:
        reasons.append(
            f"TECHNICAL_MATCHES:{known_matches}"
        )

        return {
            "match_level": "STRONG_COMPARABLE",
            "confidence": "HIGH",
            "name_score": name_score,
            "reasons": reasons,
            "feature_mika": feature_mika,
            "feature_competitor": feature_competitor,
            "feature_results": feature_results,
        }

    # --------------------------------------------------------
    # One exact technical match can support COMPARABLE only
    # for product families where that attribute is especially
    # decisive.
    #
    # OVEN is intentionally excluded.
    # --------------------------------------------------------

    decisive_families = {
        "AIR_CONDITIONER",
        "REFRIGERATOR",
        "TV",
        "WASHING_MACHINE",
        "COOKER_STOVE",
    }

    if (
        known_matches >= 1
        and mika_family in decisive_families
    ):
        reasons.append(
            f"TECHNICAL_MATCHES:{known_matches}"
        )

        return {
            "match_level": "COMPARABLE",
            "confidence": "MEDIUM",
            "name_score": name_score,
            "reasons": reasons,
            "feature_mika": feature_mika,
            "feature_competitor": feature_competitor,
            "feature_results": feature_results,
        }

    # --------------------------------------------------------
    # Same product family/type but insufficient specification
    # evidence.
    # --------------------------------------------------------

    if mika_family and competitor_family:
        reasons.append(
            "INSUFFICIENT_TECHNICAL_EVIDENCE"
        )

        return {
            "match_level": "TYPE_ONLY",
            "confidence": "LOW",
            "name_score": name_score,
            "reasons": reasons,
            "feature_mika": feature_mika,
            "feature_competitor": feature_competitor,
            "feature_results": feature_results,
        }

    # --------------------------------------------------------
    # No defensible model/product comparison.
    # --------------------------------------------------------

    return {
        "match_level": "NO_DEFENSIBLE_MATCH",
        "confidence": "LOW",
        "name_score": name_score,
        "reasons": reasons,
        "feature_mika": feature_mika,
        "feature_competitor": feature_competitor,
        "feature_results": feature_results,
    }


# ============================================================
# BUILD INDEX BY NORMALIZED PRODUCT TYPE
# ============================================================

by_type = defaultdict(lambda: defaultdict(list))

for brand, rows in catalogues.items():
    for row in rows:
        by_type[product_key(row)][brand].append(row)


# ============================================================
# PRODUCT-TYPE SUMMARY
# ============================================================

comparison_rows = []

for (
    category,
    subcategory,
), brand_data in sorted(by_type.items()):

    mika_products = brand_data.get("MIKA", [])
    bruhm_products = brand_data.get("BRUHM", [])
    haier_products = brand_data.get("HAIER", [])

    competitor_products = (
        bruhm_products + haier_products
    )

    if not mika_products or not competitor_products:
        continue

    mika_ids = sum(
        has_identifier(p)
        for p in mika_products
    )

    bruhm_ids = sum(
        has_identifier(p)
        for p in bruhm_products
    )

    haier_ids = sum(
        has_identifier(p)
        for p in haier_products
    )

    if len(mika_products) > len(competitor_products):
        breadth_signal = "MIKA_BREADTH_HIGHER"
    elif len(mika_products) < len(competitor_products):
        breadth_signal = "COMPETITOR_BREADTH_HIGHER"
    else:
        breadth_signal = "SIMILAR_BREADTH"

    comparison_rows.append({
        "category": category,
        "sub_category": subcategory,
        "mika_products": len(mika_products),
        "bruhm_products": len(bruhm_products),
        "haier_products": len(haier_products),
        "competitor_products": len(competitor_products),
        "mika_identifiers": mika_ids,
        "bruhm_identifiers": bruhm_ids,
        "haier_identifiers": haier_ids,
        "breadth_signal": breadth_signal,
        "model_match_status": "TYPE_LEVEL_ONLY",
        "assessment_status": (
            "REQUIRES_SPECIFICATION_COMPARISON"
        ),
    })


# ============================================================
# CANDIDATE MATCHING
# ============================================================

comparable_rows = []
validation_rows = []
rejection_rows = []
match_level_counts = defaultdict(int)

for (
    category,
    subcategory,
), brand_data in sorted(by_type.items()):

    mika_products = brand_data.get("MIKA", [])

    competitors = (
        brand_data.get("BRUHM", [])
        + brand_data.get("HAIER", [])
    )

    if not mika_products or not competitors:
        continue

    for mika in mika_products:

        candidate_assessments = []

        for competitor in competitors:

            assessment = assess_candidate(
                mika,
                competitor,
            )

            candidate_assessments.append(
                (
                    competitor,
                    assessment,
                )
            )

            validation_rows.append({
                "category": category,
                "sub_category": subcategory,
                "mika_model_no": mika["model_no"],
                "mika_product_name": mika["item_name"],
                "competitor_brand": competitor["brand"],
                "competitor_model_no": competitor["model_no"],
                "competitor_product_name": competitor["item_name"],
                "name_similarity_score": round(
                    assessment["name_score"],
                    3,
                ),
                "match_level": assessment["match_level"],
                "confidence": assessment["confidence"],
                "mika_family": product_family(mika) or "",
                "competitor_family": (
                    product_family(competitor) or ""
                ),
                "mika_btu": (
                    assessment["feature_mika"]["btu"]
                    or ""
                ),
                "competitor_btu": (
                    assessment["feature_competitor"]["btu"]
                    or ""
                ),
                "mika_litres": (
                    assessment["feature_mika"]["litres"]
                    or ""
                ),
                "competitor_litres": (
                    assessment["feature_competitor"]["litres"]
                    or ""
                ),
                "mika_burners": (
                    assessment["feature_mika"]["burners"]
                    or ""
                ),
                "competitor_burners": (
                    assessment["feature_competitor"]["burners"]
                    or ""
                ),
                "mika_inverter": (
                    assessment["feature_mika"]["inverter"]
                    or ""
                ),
                "competitor_inverter": (
                    assessment["feature_competitor"]["inverter"]
                    or ""
                ),
                "mika_installation": (
                    assessment["feature_mika"]["installation"]
                    or ""
                ),
                "competitor_installation": (
                    assessment["feature_competitor"]["installation"]
                    or ""
                ),
                "feature_btu": (
                    assessment["feature_results"]["btu"]
                ),
                "feature_litres": (
                    assessment["feature_results"]["litres"]
                ),
                "feature_burners": (
                    assessment["feature_results"]["burners"]
                ),
                "feature_inverter": (
                    assessment["feature_results"]["inverter"]
                ),
                "feature_installation": (
                    assessment["feature_results"]["installation"]
                ),
                "feature_width_cm": (
                    assessment["feature_results"]["width_cm"]
                ),
                "feature_tv_inches": (
                    assessment["feature_results"]["tv_inches"]
                ),
                "reason": " | ".join(
                    assessment["reasons"]
                ),
            })

        # ----------------------------------------------------
        # Rank candidates.
        #
        # Priority:
        # STRONG_COMPARABLE
        # COMPARABLE
        # TYPE_ONLY
        # NO_DEFENSIBLE_MATCH
        #
        # Within a level, technical matches beat name score.
        # ----------------------------------------------------

        level_rank = {
            "STRONG_COMPARABLE": 4,
            "COMPARABLE": 3,
            "TYPE_ONLY": 2,
            "NO_DEFENSIBLE_MATCH": 1,
        }

        def candidate_sort_key(item):
            competitor, assessment = item

            feature_results = assessment["feature_results"]

            technical_matches = sum(
                value == "MATCH"
                for value in feature_results.values()
            )

            return (
                level_rank[assessment["match_level"]],
                technical_matches,
                assessment["name_score"],
            )

        candidate_assessments.sort(
            key=candidate_sort_key,
            reverse=True,
        )

        # ----------------------------------------------------
        # Select only candidates that are actually usable for
        # the controlled comparison output.
        #
        # NO_DEFENSIBLE_MATCH candidates remain in the full
        # validation report and rejection report, but they
        # must NEVER appear as the selected competitor.
        # ----------------------------------------------------

        valid_candidates = [
            item
            for item in candidate_assessments
            if item[1]["match_level"]
            != "NO_DEFENSIBLE_MATCH"
        ]

        if valid_candidates:

            best_candidate, best_assessment = (
                valid_candidates[0]
            )

            match_level = best_assessment["match_level"]

            match_level_counts[match_level] += 1

            comparable_rows.append({
                "category": category,
                "sub_category": subcategory,
                "mika_model_no": mika["model_no"],
                "mika_product_name": mika["item_name"],
                "competitor_brand": best_candidate["brand"],
                "competitor_model_no": (
                    best_candidate["model_no"]
                ),
                "competitor_product_name": (
                    best_candidate["item_name"]
                ),
                "name_similarity_score": round(
                    best_assessment["name_score"],
                    3,
                ),
                "match_status": match_level,
                "match_confidence": (
                    best_assessment["confidence"]
                ),
                "mika_family": (
                    product_family(mika) or ""
                ),
                "competitor_family": (
                    product_family(best_candidate) or ""
                ),
                "mika_btu": (
                    best_assessment["feature_mika"]["btu"]
                    or ""
                ),
                "competitor_btu": (
                    best_assessment[
                        "feature_competitor"
                    ]["btu"]
                    or ""
                ),
                "mika_litres": (
                    best_assessment["feature_mika"]["litres"]
                    or ""
                ),
                "competitor_litres": (
                    best_assessment[
                        "feature_competitor"
                    ]["litres"]
                    or ""
                ),
                "mika_burners": (
                    best_assessment["feature_mika"]["burners"]
                    or ""
                ),
                "competitor_burners": (
                    best_assessment[
                        "feature_competitor"
                    ]["burners"]
                    or ""
                ),
                "mika_inverter": (
                    best_assessment["feature_mika"]["inverter"]
                    or ""
                ),
                "competitor_inverter": (
                    best_assessment[
                        "feature_competitor"
                    ]["inverter"]
                    or ""
                ),
                "mika_installation": (
                    best_assessment[
                        "feature_mika"
                    ]["installation"]
                    or ""
                ),
                "competitor_installation": (
                    best_assessment[
                        "feature_competitor"
                    ]["installation"]
                    or ""
                ),
                "match_reason": " | ".join(
                    best_assessment["reasons"]
                ),
                "assessment_status": (
                    "DO_NOT_TREAT_AS_EQUIVALENT"
                ),
            })

        else:

            # ------------------------------------------------
            # No defensible competitor candidate exists.
            #
            # We deliberately leave competitor fields blank.
            # Rejected candidates remain available in:
            #   match_validation_report.csv
            #   match_rejections.csv
            # ------------------------------------------------

            match_level = "NO_DEFENSIBLE_MATCH"

            match_level_counts[match_level] += 1

            comparable_rows.append({
                "category": category,
                "sub_category": subcategory,
                "mika_model_no": mika["model_no"],
                "mika_product_name": mika["item_name"],
                "competitor_brand": "",
                "competitor_model_no": "",
                "competitor_product_name": "",
                "name_similarity_score": "",
                "match_status": "NO_DEFENSIBLE_MATCH",
                "match_confidence": "LOW",
                "mika_family": (
                    product_family(mika) or ""
                ),
                "competitor_family": "",
                "mika_btu": "",
                "competitor_btu": "",
                "mika_litres": "",
                "competitor_litres": "",
                "mika_burners": "",
                "competitor_burners": "",
                "mika_inverter": "",
                "competitor_inverter": "",
                "mika_installation": "",
                "competitor_installation": "",
                "match_reason": (
                    "NO_VALID_COMPETITOR_CANDIDATE"
                ),
                "assessment_status": (
                    "DO_NOT_TREAT_AS_EQUIVALENT"
                ),
            })

        # ----------------------------------------------------
        # Record rejected / weak alternatives.
        #
        # If a valid candidate exists, candidate_assessments[1:]
        # excludes the selected candidate.
        #
        # If no valid candidate exists, all candidates are
        # rejected alternatives and should remain visible.
        # ----------------------------------------------------

        if valid_candidates:
            rejected_candidates = [
                item
                for item in candidate_assessments
                if item != valid_candidates[0]
            ]
        else:
            rejected_candidates = candidate_assessments

        for competitor, assessment in rejected_candidates:

            if assessment["match_level"] in {
                "NO_DEFENSIBLE_MATCH",
                "TYPE_ONLY",
            }:

                rejection_rows.append({
                    "category": category,
                    "sub_category": subcategory,
                    "mika_model_no": mika["model_no"],
                    "mika_product_name": mika["item_name"],
                    "competitor_brand": competitor["brand"],
                    "competitor_model_no": (
                        competitor["model_no"]
                    ),
                    "competitor_product_name": (
                        competitor["item_name"]
                    ),
                    "name_similarity_score": round(
                        assessment["name_score"],
                        3,
                    ),
                    "rejected_match_level": (
                        assessment["match_level"]
                    ),
                    "reason": " | ".join(
                        assessment["reasons"]
                    ),
                })


# ============================================================
# POTENTIAL PRODUCT GAPS
# ============================================================

potential_gap_rows = []

for (
    category,
    subcategory,
), brand_data in sorted(by_type.items()):

    mika_products = brand_data.get("MIKA", [])
    bruhm_products = brand_data.get("BRUHM", [])
    haier_products = brand_data.get("HAIER", [])

    competitors = (
        bruhm_products + haier_products
    )

    if mika_products or not competitors:
        continue

    potential_gap_rows.append({
        "category": category,
        "sub_category": subcategory,
        "mika_products": 0,
        "bruhm_products": len(bruhm_products),
        "haier_products": len(haier_products),
        "competitor_products": len(competitors),
        "gap_signal": (
            "COMPETITOR_CATALOGUE_COVERAGE_NOT_FOUND_IN_MIKA"
        ),
        "validation_required": (
            "CHECK_NAMING_ARCHITECTURE_"
            "SPECIFICATIONS_AVAILABILITY"
        ),
        "status": "UNCONFIRMED",
    })


# ============================================================
# IDENTIFIER LIMITATIONS
# ============================================================

identifier_rows = []

for brand, rows in catalogues.items():

    total = len(rows)

    available = sum(
        has_identifier(r)
        for r in rows
    )

    missing = total - available

    identifier_rows.append({
        "brand": brand,
        "products": total,
        "identifiers_available": available,
        "identifiers_missing": missing,
        "identifier_coverage_pct": round(
            (available / total) * 100,
            1,
        ) if total else 0,
        "limitation": (
            "SOURCE_IDENTIFIER_MISSING"
            if missing
            else "NO_IDENTIFIER_GAP"
        ),
    })


# ============================================================
# WRITE CSV
# ============================================================

def write_csv(filename, rows, fields):

    path = OUTPUT_DIR / filename

    with path.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=fields,
            extrasaction="ignore",
        )

        writer.writeheader()
        writer.writerows(rows)

    return path


# ------------------------------------------------------------
# Existing output: product type comparison
# ------------------------------------------------------------

write_csv(
    "model_comparison_preview.csv",
    comparison_rows,
    [
        "category",
        "sub_category",
        "mika_products",
        "bruhm_products",
        "haier_products",
        "competitor_products",
        "mika_identifiers",
        "bruhm_identifiers",
        "haier_identifiers",
        "breadth_signal",
        "model_match_status",
        "assessment_status",
    ],
)


# ------------------------------------------------------------
# Upgraded candidate comparison
# ------------------------------------------------------------

write_csv(
    "comparable_product_types.csv",
    comparable_rows,
    [
        "category",
        "sub_category",
        "mika_model_no",
        "mika_product_name",
        "competitor_brand",
        "competitor_model_no",
        "competitor_product_name",
        "name_similarity_score",
        "match_status",
        "match_confidence",
        "mika_family",
        "competitor_family",
        "mika_btu",
        "competitor_btu",
        "mika_litres",
        "competitor_litres",
        "mika_burners",
        "competitor_burners",
        "mika_inverter",
        "competitor_inverter",
        "mika_installation",
        "competitor_installation",
        "match_reason",
        "assessment_status",
    ],
)


# ------------------------------------------------------------
# Potential gaps
# ------------------------------------------------------------

write_csv(
    "potential_product_gaps.csv",
    potential_gap_rows,
    [
        "category",
        "sub_category",
        "mika_products",
        "bruhm_products",
        "haier_products",
        "competitor_products",
        "gap_signal",
        "validation_required",
        "status",
    ],
)


# ------------------------------------------------------------
# Identifier limitations
# ------------------------------------------------------------

write_csv(
    "identifier_limitations.csv",
    identifier_rows,
    [
        "brand",
        "products",
        "identifiers_available",
        "identifiers_missing",
        "identifier_coverage_pct",
        "limitation",
    ],
)


# ------------------------------------------------------------
# Full candidate validation report
# ------------------------------------------------------------

write_csv(
    "match_validation_report.csv",
    validation_rows,
    [
        "category",
        "sub_category",
        "mika_model_no",
        "mika_product_name",
        "competitor_brand",
        "competitor_model_no",
        "competitor_product_name",
        "name_similarity_score",
        "match_level",
        "confidence",
        "mika_family",
        "competitor_family",
        "mika_btu",
        "competitor_btu",
        "mika_litres",
        "competitor_litres",
        "mika_burners",
        "competitor_burners",
        "mika_inverter",
        "competitor_inverter",
        "mika_installation",
        "competitor_installation",
        "feature_btu",
        "feature_litres",
        "feature_burners",
        "feature_inverter",
        "feature_installation",
        "feature_width_cm",
        "feature_tv_inches",
        "reason",
    ],
)


# ------------------------------------------------------------
# Rejected / weak alternatives
# ------------------------------------------------------------

write_csv(
    "match_rejections.csv",
    rejection_rows,
    [
        "category",
        "sub_category",
        "mika_model_no",
        "mika_product_name",
        "competitor_brand",
        "competitor_model_no",
        "competitor_product_name",
        "name_similarity_score",
        "rejected_match_level",
        "reason",
    ],
)


# ============================================================
# SUMMARY
# ============================================================

summary_file = (
    OUTPUT_DIR
    / "model_comparison_summary.txt"
)

with summary_file.open(
    "w",
    encoding="utf-8",
) as f:

    f.write(
        "MIKA MODEL / PRODUCT COMPARISON — "
        "CONTROLLED PREVIEW\n"
    )

    f.write("=" * 75 + "\n\n")

    f.write(
        f"Shared product types analysed: "
        f"{len(comparison_rows)}\n"
    )

    f.write(
        "MIKA product records in shared types: "
        f"{sum(r['mika_products'] for r in comparison_rows)}\n"
    )

    f.write(
        "Competitor product records in shared types: "
        f"{sum(r['competitor_products'] for r in comparison_rows)}\n"
    )

    f.write(
        "Potential catalogue coverage signals: "
        f"{len(potential_gap_rows)}\n"
    )

    f.write(
        "MIKA product records assessed against candidates: "
        f"{len(comparable_rows)}\n"
    )

    f.write(
        "Total candidate assessments: "
        f"{len(validation_rows)}\n"
    )

    f.write(
        "Rejected / weak alternative records: "
        f"{len(rejection_rows)}\n\n"
    )

    f.write("MATCH LEVEL DISTRIBUTION\n")
    f.write("-" * 45 + "\n")

    for level in [
        "STRONG_COMPARABLE",
        "COMPARABLE",
        "TYPE_ONLY",
        "NO_DEFENSIBLE_MATCH",
    ]:

        f.write(
            f"{level}: "
            f"{match_level_counts.get(level, 0)}\n"
        )

    f.write("\n")

    f.write("IDENTIFIER COVERAGE\n")
    f.write("-" * 45 + "\n")

    for row in identifier_rows:

        f.write(
            f"{row['brand']}: "
            f"{row['identifiers_available']}/"
            f"{row['products']} "
            f"({row['identifier_coverage_pct']}%) "
            f"available; "
            f"{row['identifiers_missing']} missing\n"
        )

    f.write("\n")

    f.write("CONTROLLED MATCHING RULES\n")
    f.write("-" * 45 + "\n")

    f.write(
        "1. No cross-brand model equivalence is declared.\n"
    )

    f.write(
        "2. Name similarity is supporting evidence only.\n"
    )

    f.write(
        "3. Product family must be compatible where identifiable.\n"
    )

    f.write(
        "4. AC BTU conflicts block comparability.\n"
    )

    f.write(
        "5. Inverter/non-inverter conflicts block comparability.\n"
    )

    f.write(
        "6. Burner-count conflicts block comparability.\n"
    )

    f.write(
        "7. Built-in/freestanding conflicts block comparability.\n"
    )

    f.write(
        "8. TV screen-size conflicts block comparability.\n"
    )

    f.write(
        "9. Source-brand conflicts are flagged, not corrected.\n"
    )

    f.write(
        "10. Missing specifications reduce confidence "
        "rather than being guessed.\n"
    )

    f.write(
        "11. TYPE_ONLY is not a model/product equivalence.\n"
    )

    f.write(
        "12. Potential catalogue gaps remain UNCONFIRMED.\n"
    )

    f.write(
        "13. Price positioning is intentionally excluded.\n"
    )

    f.write(
        "14. SQLite database writes: NONE.\n"
    )


# ============================================================
# CONSOLE OUTPUT
# ============================================================

print("=" * 75)
print("MIKA MODEL / PRODUCT COMPARISON — CONTROLLED PREVIEW")
print("=" * 75)

print(
    f"Shared product types analysed       : "
    f"{len(comparison_rows)}"
)

print(
    "MIKA products in shared types        : "
    f"{sum(r['mika_products'] for r in comparison_rows)}"
)

print(
    "Competitor products in shared types : "
    f"{sum(r['competitor_products'] for r in comparison_rows)}"
)

print(
    "Potential coverage signals           : "
    f"{len(potential_gap_rows)}"
)

print(
    "MIKA records assessed                : "
    f"{len(comparable_rows)}"
)

print(
    "Total candidate assessments          : "
    f"{len(validation_rows)}"
)

print(
    "Rejected / weak alternatives         : "
    f"{len(rejection_rows)}"
)

print()

print("MATCH LEVEL DISTRIBUTION:")

for level in [
    "STRONG_COMPARABLE",
    "COMPARABLE",
    "TYPE_ONLY",
    "NO_DEFENSIBLE_MATCH",
]:

    print(
        f"  {level:<22}: "
        f"{match_level_counts.get(level, 0)}"
    )

print()

print("Identifier coverage:")

for row in identifier_rows:

    print(
        f"  {row['brand']}: "
        f"{row['identifiers_available']}/"
        f"{row['products']} available | "
        f"missing: {row['identifiers_missing']}"
    )

print()

print("OUTPUT FILES:")

print(
    f"  {OUTPUT_DIR / 'model_comparison_preview.csv'}"
)

print(
    f"  {OUTPUT_DIR / 'comparable_product_types.csv'}"
)

print(
    f"  {OUTPUT_DIR / 'potential_product_gaps.csv'}"
)

print(
    f"  {OUTPUT_DIR / 'identifier_limitations.csv'}"
)

print(
    f"  {OUTPUT_DIR / 'match_validation_report.csv'}"
)

print(
    f"  {OUTPUT_DIR / 'match_rejections.csv'}"
)

print(f"  {summary_file}")

print()

print("DATABASE WRITES: NONE")
print("=" * 75)