import csv
import re
import sqlite3
from collections import Counter
from datetime import date, datetime
from pathlib import Path

import product_price_movements as price_movements


DB_PATH = Path(__file__).resolve().parent.parent / "data" / "mika_competitive_intel.db"
REPORT_DIR = Path(__file__).resolve().parent.parent / "reports" / "mika_catalogue_preview" / "product_intelligence"

# Existing catalogue baseline. This is deliberately the same baseline
# already used by the existing launch baseline/evidence scripts.
BASELINE_DATE = "2026-09-22"

# We do NOT call a product discontinued merely because it was not observed
# recently. A possible discontinuation requires a historical gap and enough
# observation span to support the signal.
MIN_HISTORY_DAYS_FOR_DISCONTINUATION = 7
DISCONTINUATION_GAP_DAYS = 7

WEAK_MODELS = {
    "",
    "N/A",
    "NA",
    "NONE",
    "UNKNOWN",
    "SAMSUNG",
    "TEFAL",
    "SCL",
    "CLIPSOMINUT",
}


CATALOGUES = [
    {
        "brand": "Bruhm",
        "table": "bruhm_products",
        "identifier": "sku",
        "name": "product_name",
        "category": "category",
        "url": "product_url",
        "first_seen": "first_seen_date",
        "last_seen": "last_seen_date",
        "model": "sku",
    },
    {
        "brand": "Haier",
        "table": "haier_products",
        "identifier": "sku",
        "name": "product_name",
        "category": "category",
        "url": "url",
        "first_seen": "first_seen_date",
        "last_seen": "last_seen_date",
        "model": "sku",
    },
    {
        "brand": "K-Elec",
        "table": "k_elec_products",
        "identifier": "product_key",
        "name": "product_name",
        "category": "category",
        "url": "url",
        "first_seen": "first_seen_date",
        "last_seen": "last_seen_date",
        "model": "model",
    },
]


def normalize_text(value):
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value).strip())


def parse_date(value):
    value = normalize_text(value)

    if not value:
        return None

    try:
        return date.fromisoformat(value[:10])
    except ValueError:
        return None


def model_quality(model):
    value = normalize_text(model)

    if not value:
        return "missing"

    upper = value.upper()

    if upper in WEAK_MODELS:
        return "weak"

    if len(value) < 4:
        return "weak"

    if re.fullmatch(
        r"\d+(\.\d+)?\s*(W|KW|L|KG|CM|MM|INCH|INCHES)?",
        upper,
    ):
        return "weak"

    if re.fullmatch(r"\d+(\.\d+)?\s*(L|KG)", upper):
        return "weak"

    return "reliable"


def safe_identifier(row, config):
    value = normalize_text(row[config["identifier"]])

    if value:
        return value

    # K-Elec has product_key even where model is absent.
    if config["brand"] == "K-Elec":
        return normalize_text(row["product_key"])

    return ""


def product_identity(row, config):
    identifier = safe_identifier(row, config)

    if identifier:
        return (
            f"{config['brand'].upper()} | {identifier.upper()}",
            "identifier",
        )

    name = normalize_text(row[config["name"]])
    category = normalize_text(row[config["category"]])

    return (
        " | ".join(
            part.upper()
            for part in (config["brand"], category, name)
            if part
        ),
        "name_category",
    )


def load_catalogue_rows(con):
    records = []

    for config in CATALOGUES:
        columns = [
            config["identifier"],
            config["name"],
            config["category"],
            config["url"],
            config["first_seen"],
            config["last_seen"],
        ]

        if config["model"] not in columns:
            columns.append(config["model"])

        select_columns = ", ".join(columns)

        rows = con.execute(
            f"""
            SELECT {select_columns}
            FROM {config["table"]}
            ORDER BY {config["first_seen"]}, rowid
            """
        ).fetchall()

        for row in rows:
            records.append(
                {
                    "brand": config["brand"],
                    "table": config["table"],
                    "identifier_field": config["identifier"],
                    "identifier": safe_identifier(row, config),
                    "model": normalize_text(row[config["model"]]),
                    "product_name": normalize_text(row[config["name"]]),
                    "category": normalize_text(row[config["category"]]),
                    "url": normalize_text(row[config["url"]]),
                    "first_seen_date": normalize_text(row[config["first_seen"]]),
                    "last_seen_date": normalize_text(row[config["last_seen"]]),
                }
            )

    return records


def catalogue_date_range(records):
    dates = []

    for record in records:
        for field in ("first_seen_date", "last_seen_date"):
            parsed = parse_date(record[field])
            if parsed:
                dates.append(parsed)

    if not dates:
        return None, None

    return min(dates), max(dates)


def classify_new_product(record):
    first_seen = parse_date(record["first_seen_date"])
    baseline = parse_date(BASELINE_DATE)

    if not first_seen or not baseline:
        return "INSUFFICIENT_HISTORY"

    if first_seen > baseline:
        return "NEW_PRODUCT_CANDIDATE"

    return "BASELINE_PRODUCT"


def classify_new_model(record):
    first_seen = parse_date(record["first_seen_date"])
    baseline = parse_date(BASELINE_DATE)

    model = normalize_text(record["model"])
    quality = model_quality(model)

    if not first_seen or not baseline:
        return "INSUFFICIENT_HISTORY"

    if first_seen <= baseline:
        return "BASELINE_MODEL"

    if quality == "reliable":
        return "NEW_MODEL_CANDIDATE"

    if quality == "weak":
        return "MODEL_IDENTIFIER_WEAK"

    return "MODEL_IDENTIFIER_MISSING"


def specification_status(con):
    count = con.execute(
        "SELECT COUNT(*) FROM product_observations"
    ).fetchone()[0]

    populated = con.execute(
        """
        SELECT COUNT(*)
        FROM product_observations
        WHERE specifications IS NOT NULL
          AND TRIM(specifications) <> ''
        """
    ).fetchone()[0]

    if count == 0:
        return {
            "status": "INSUFFICIENT_HISTORY",
            "observations": 0,
            "specifications_populated": 0,
            "coverage_percent": 0.0,
        }

    coverage = (populated / count) * 100

    return {
        "status": "AVAILABLE",
        "observations": count,
        "specifications_populated": populated,
        "coverage_percent": round(coverage, 2),
    }


def availability_status(records):
    """
    Dedicated catalogue tables contain no availability field.

    Therefore Product Intelligence must not infer stock availability from
    presence alone. Historical presence is reported separately.
    """
    return {
        "status": "NOT_AVAILABLE_AS_FIELD",
        "records_analysed": len(records),
        "explanation": (
            "Catalogue tables contain first_seen_date and last_seen_date "
            "but no explicit availability/stock-status field."
        ),
    }


def historical_presence(records, catalogue_last_date):
    results = []

    if not catalogue_last_date:
        return results

    for record in records:
        last_seen = parse_date(record["last_seen_date"])
        first_seen = parse_date(record["first_seen_date"])

        if not last_seen:
            status = "INSUFFICIENT_HISTORY"
            gap_days = None
        else:
            gap_days = (catalogue_last_date - last_seen).days

            if not first_seen:
                status = "INSUFFICIENT_HISTORY"
            elif (last_seen - first_seen).days < MIN_HISTORY_DAYS_FOR_DISCONTINUATION:
                status = "INSUFFICIENT_HISTORY"
            elif gap_days >= DISCONTINUATION_GAP_DAYS:
                status = "POSSIBLE_DISCONTINUATION"
            else:
                status = "CURRENTLY_OBSERVED"

        results.append(
            {
                "brand": record["brand"],
                "identifier": record["identifier"],
                "product_name": record["product_name"],
                "category": record["category"],
                "first_seen_date": record["first_seen_date"],
                "last_seen_date": record["last_seen_date"],
                "catalogue_last_date": catalogue_last_date.isoformat(),
                "gap_days": gap_days,
                "status": status,
                "url": record["url"],
            }
        )

    return results


def write_csv(path, rows, fieldnames):
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=fieldnames,
            extrasaction="ignore",
        )
        writer.writeheader()
        writer.writerows(rows)


def write_product_status(records):
    rows = []

    for record in records:
        rows.append(
            {
                "brand": record["brand"],
                "identifier": record["identifier"],
                "model": record["model"],
                "product_name": record["product_name"],
                "category": record["category"],
                "first_seen_date": record["first_seen_date"],
                "last_seen_date": record["last_seen_date"],
                "new_product_status": classify_new_product(record),
                "new_model_status": classify_new_model(record),
                "url": record["url"],
            }
        )

    write_csv(
        REPORT_DIR / "product_status.csv",
        rows,
        [
            "brand",
            "identifier",
            "model",
            "product_name",
            "category",
            "first_seen_date",
            "last_seen_date",
            "new_product_status",
            "new_model_status",
            "url",
        ],
    )

    return rows


def write_new_product_candidates(rows):
    candidates = [
        row
        for row in rows
        if row["new_product_status"] == "NEW_PRODUCT_CANDIDATE"
    ]

    write_csv(
        REPORT_DIR / "new_product_candidates.csv",
        candidates,
        [
            "brand",
            "identifier",
            "model",
            "product_name",
            "category",
            "first_seen_date",
            "last_seen_date",
            "new_product_status",
            "new_model_status",
            "url",
        ],
    )

    return candidates


def write_new_model_candidates(rows):
    candidates = [
        row
        for row in rows
        if row["new_model_status"] == "NEW_MODEL_CANDIDATE"
    ]

    write_csv(
        REPORT_DIR / "new_model_candidates.csv",
        candidates,
        [
            "brand",
            "identifier",
            "model",
            "product_name",
            "category",
            "first_seen_date",
            "last_seen_date",
            "new_product_status",
            "new_model_status",
            "url",
        ],
    )

    return candidates


def write_historical_presence(records, catalogue_last_date):
    rows = historical_presence(records, catalogue_last_date)

    write_csv(
        REPORT_DIR / "historical_presence.csv",
        rows,
        [
            "brand",
            "identifier",
            "product_name",
            "category",
            "first_seen_date",
            "last_seen_date",
            "catalogue_last_date",
            "gap_days",
            "status",
            "url",
        ],
    )

    return rows


def print_price_movements():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row

    rows = price_movements.load_price_observations(con)
    identities = price_movements.build_identities(rows)
    movements, ambiguous = price_movements.detect_movements(identities)

    print()
    print("PRICE MOVEMENTS")
    print("-" * 80)
    print(f"Price observations analysed: {len(rows)}")
    print(f"Identities analysed: {len(identities)}")
    print(f"Movement candidates: {len(movements)}")
    print(f"Ambiguous same-day identity cases: {len(ambiguous)}")

    for index, item in enumerate(movements, 1):
        print()
        print(f"{index}. {item['brand']} | {item['model']}")
        print(f"   Product: {item['product_name']}")
        print(f"   Category: {item['category']}")
        print(
            f"   Previous: KSh {item['previous_price']:,.2f} "
            f"({item['previous_date']})"
        )
        print(
            f"   Current:  KSh {item['current_price']:,.2f} "
            f"({item['current_date']})"
        )
        print(
            f"   Change: {item['change']:+,.2f} KSh "
            f"({item['percentage']:+.2f}%)"
        )
        print("   Status: PRICE MOVEMENT CANDIDATE")
        print("   Confidence: HIGH")

    con.close()


def print_summary(
    records,
    product_status_rows,
    new_product_candidates,
    new_model_candidates,
    historical_rows,
    specification,
    availability,
    first_date,
    last_date,
):
    product_status_counts = Counter(
        row["new_product_status"]
        for row in product_status_rows
    )

    model_status_counts = Counter(
        row["new_model_status"]
        for row in product_status_rows
    )

    historical_counts = Counter(
        row["status"]
        for row in historical_rows
    )

    print("=" * 80)
    print("MIKA CI - PRODUCT INTELLIGENCE")
    print("=" * 80)
    print(f"Database: {DB_PATH}")
    print(f"Report directory: {REPORT_DIR}")
    print()

    print("CATALOGUE COVERAGE")
    print("-" * 80)
    print(f"Products analysed: {len(records)}")

    for brand in ("Bruhm", "Haier", "K-Elec"):
        count = sum(1 for row in records if row["brand"] == brand)
        print(f"{brand:10} {count}")

    print()
    print("HISTORICAL WINDOW")
    print("-" * 80)
    print(f"First catalogue date: {first_date or 'N/A'}")
    print(f"Latest catalogue date: {last_date or 'N/A'}")
    print(f"Baseline date:        {BASELINE_DATE}")

    print()
    print("NEW PRODUCTS")
    print("-" * 80)
    print(
        f"New product candidates after baseline: "
        f"{len(new_product_candidates)}"
    )
    for key, value in sorted(product_status_counts.items()):
        print(f"{key:30} {value}")

    print()
    print("NEW MODELS")
    print("-" * 80)
    print(
        f"New model candidates after baseline: "
        f"{len(new_model_candidates)}"
    )
    for key, value in sorted(model_status_counts.items()):
        print(f"{key:30} {value}")

    print()
    print("SPECIFICATIONS")
    print("-" * 80)
    print(f"Status: {specification['status']}")
    print(f"Observations: {specification['observations']}")
    print(
        "Specifications populated: "
        f"{specification['specifications_populated']}"
    )
    print(f"Coverage: {specification['coverage_percent']:.2f}%")

    print()
    print("AVAILABILITY")
    print("-" * 80)
    print(f"Status: {availability['status']}")
    print(f"Records analysed: {availability['records_analysed']}")
    print(f"Note: {availability['explanation']}")

    print()
    print("HISTORICAL PRESENCE / DISCONTINUATION")
    print("-" * 80)
    for key, value in sorted(historical_counts.items()):
        print(f"{key:30} {value}")

    print()
    print("IMPORTANT INTERPRETATION")
    print("-" * 80)
    print(
        "A product being absent from the latest catalogue observation "
        "is NOT automatically treated as discontinued."
    )
    print(
        "POSSIBLE_DISCONTINUATION requires sufficient history and a "
        f"minimum {DISCONTINUATION_GAP_DAYS}-day observation gap."
    )

    print()
    print("REPORTS WRITTEN")
    print("-" * 80)
    print(REPORT_DIR / "product_status.csv")
    print(REPORT_DIR / "new_product_candidates.csv")
    print(REPORT_DIR / "new_model_candidates.csv")
    print(REPORT_DIR / "historical_presence.csv")


def main():
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row

    records = load_catalogue_rows(con)

    first_date, last_date = catalogue_date_range(records)

    product_status_rows = write_product_status(records)
    new_product_candidates = write_new_product_candidates(product_status_rows)
    new_model_candidates = write_new_model_candidates(product_status_rows)

    historical_rows = write_historical_presence(
        records,
        last_date,
    )

    specification = specification_status(con)
    availability = availability_status(records)

    con.close()

    print_summary(
        records=records,
        product_status_rows=product_status_rows,
        new_product_candidates=new_product_candidates,
        new_model_candidates=new_model_candidates,
        historical_rows=historical_rows,
        specification=specification,
        availability=availability,
        first_date=first_date,
        last_date=last_date,
    )

    print()
    print_price_movements()

    print()
    print("=" * 80)
    print("PRODUCT INTELLIGENCE COMPLETE - NO DATABASE WRITES")
    print("=" * 80)


if __name__ == "__main__":
    main()
