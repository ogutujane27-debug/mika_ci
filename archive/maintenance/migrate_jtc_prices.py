
import sqlite3
import re
from datetime import date

DB = "data/mika_competitive_intel.db"
JTC_COMPETITOR_ID = 18

CATEGORY_MAP = {
    "TA01115-GS": "Toasters",
    "BLT1011-CB": "Blenders",
    "BL2033AG-CB": "Blenders",
}

def extract_model(product_name):
    patterns = [
        r"\((GSSP-2GB013)\)",
        r"\((GSSP-2GB072)\)",
        r"\((GSSP-2GB203)\)",
        r"\((TA01115-GS)\)",
        r"\((BLT1011-CB)\)",
        r"\((ECI1012-GS)\)",
        r"\((BL2033AG-CB)\)",
        r"-(KEX1001-GS)\b",
        r"\b(KEP-0301-GS)\b",
        r"\b(KEP-0306-GS)\b",
        r"\b(KEC-3001)\b",
        r"-S106\s+(5500W|7500W|9000W)\b",
        r"\((EC11009-GS)\)",
    ]

    for pattern in patterns:
        match = re.search(pattern, product_name, re.IGNORECASE)
        if match:
            value = match.group(1)
            if value.startswith(("5500W", "7500W", "9000W")):
                return f"S106-{value}"
            return value

    return None


def category_for(product_name, model):
    if model in CATEGORY_MAP:
        return CATEGORY_MAP[model]

    if "toaster" in product_name.lower():
        return "Toasters"

    if "blender" in product_name.lower():
        return "Blenders"

    return "Home appliances"


def next_finding_id(con, observed_date):
    prefix = f"CI-{observed_date[:7].replace('-', '-')}-"

    rows = con.execute(
        """
        SELECT finding_id
        FROM findings
        WHERE finding_id LIKE ?
        """,
        (prefix + "%",),
    ).fetchall()

    numbers = []

    for row in rows:
        match = re.search(r"-(\d+)$", row["finding_id"])
        if match:
            numbers.append(int(match.group(1)))

    next_number = max(numbers, default=0) + 1

    return f"{prefix}{next_number:05d}"


def main():
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row

    try:
        con.execute("BEGIN")

        competitor = con.execute(
            """
            SELECT competitor_id, competitor_name, brand_name
            FROM competitors
            WHERE competitor_id = ?
            """,
            (JTC_COMPETITOR_ID,),
        ).fetchone()

        if not competitor:
            raise RuntimeError("JTC competitor ID 18 does not exist.")

        if competitor["brand_name"] != "JTC":
            raise RuntimeError(
                f"Competitor ID 18 is not JTC; it is {competitor['brand_name']}."
            )

        source_rows = con.execute(
            """
            SELECT
                product_name,
                sku,
                regular_price,
                sale_price,
                observed_date,
                url
            FROM haier_price_observations
            WHERE product_name LIKE 'JTC%'
            ORDER BY observed_date, product_name
            """
        ).fetchall()

        if len(source_rows) != 30:
            raise RuntimeError(
                f"Expected exactly 30 JTC legacy observations; found {len(source_rows)}."
            )

        existing = con.execute(
            """
            SELECT COUNT(*)
            FROM price_observations p
            JOIN findings f
                ON f.finding_id = p.finding_id
            WHERE f.competitor_id = ?
              AND f.brand = 'JTC'
            """,
            (JTC_COMPETITOR_ID,),
        ).fetchone()[0]

        if existing:
            raise RuntimeError(
                f"Canonical JTC price observations already exist: {existing}. "
                "Migration stopped to prevent duplicates."
            )

        inserted = 0

        for row in source_rows:
            product_name = row["product_name"]
            model = extract_model(product_name)
            category = category_for(product_name, model)

            current_price = (
                row["sale_price"]
                if row["sale_price"] is not None
                else row["regular_price"]
            )

            if current_price is None:
                raise RuntimeError(
                    f"No usable price for JTC product: {product_name}"
                )

            promotion_note = None

            if (
                row["regular_price"] is not None
                and row["sale_price"] is not None
                and row["sale_price"] < row["regular_price"]
            ):
                promotion_note = (
                    f"Was KSh {row['regular_price']:,.0f}; "
                    f"current KSh {row['sale_price']:,.0f}"
                )

            finding_id = next_finding_id(con, row["observed_date"])

            evidence = (
                f"Product: {product_name}; "
                f"Model/SKU: {model or row['sku'] or 'Not published'}; "
                f"Current price: KSh {current_price:,.0f}"
            )

            if promotion_note:
                evidence += f"; {promotion_note}"

            con.execute(
                """
                INSERT INTO findings (
                    finding_id,
                    scan_week,
                    run_id,
                    competitor_id,
                    brand,
                    category,
                    finding_type,
                    summary,
                    source_url,
                    source_type,
                    published_date,
                    observed_date,
                    evidence_text,
                    verification_status,
                    confidence
                )
                VALUES (
                    ?,
                    ?,
                    NULL,
                    ?,
                    'JTC',
                    ?,
                    'price',
                    ?,
                    ?,
                    'official website',
                    NULL,
                    ?,
                    ?,
                    'verified',
                    'high'
                )
                """,
                (
                    finding_id,
                    f"{row['observed_date'][:4]}-W{date.fromisoformat(row['observed_date']).isocalendar().week:02d}",
                    JTC_COMPETITOR_ID,
                    category,
                    f"Price observed: {product_name}",
                    row["url"],
                    row["observed_date"],
                    evidence,
                ),
            )

            con.execute(
                """
                INSERT INTO price_observations (
                    finding_id,
                    product_name,
                    model,
                    price_kes,
                    promotion_note,
                    observed_date
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    finding_id,
                    product_name,
                    model,
                    current_price,
                    promotion_note,
                    row["observed_date"],
                ),
            )

            inserted += 1

        con.commit()

        print("JTC canonical price migration completed successfully.")
        print(f"Legacy source observations checked: {len(source_rows)}")
        print(f"Canonical price observations created: {inserted}")
        print("Legacy haier_price_observations table was not modified.")

    except Exception:
        con.rollback()
        raise

    finally:
        con.close()


if __name__ == "__main__":
    main()
