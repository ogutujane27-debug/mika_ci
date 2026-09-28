"""Small helpers around the SQLite database.

Python does all calculations; nothing here invents a previous price.

Historical price comparisons are source-aware:
    brand + model + market source

A different retailer/source is treated as a different observation,
not automatically as a price change.
"""

import sqlite3
from datetime import datetime, date

from config import DB_PATH


def connect():
    con = sqlite3.connect(DB_PATH)
    con.execute("PRAGMA foreign_keys = ON")
    con.row_factory = sqlite3.Row
    return con


def iso_week(d: date) -> str:
    y, w, _ = d.isocalendar()
    return f"{y}-W{w:02d}"


def start_run(con, status="running"):
    today = date.today()
    cur = con.execute(
        "INSERT INTO scan_runs (scan_week, started_at, status) VALUES (?,?,?)",
        (
            iso_week(today),
            datetime.now().isoformat(timespec="seconds"),
            status,
        ),
    )
    con.commit()
    return cur.lastrowid


def finish_run(
    con,
    run_id,
    status,
    sources_checked,
    findings_created,
    error=None,
):
    con.execute(
        "UPDATE scan_runs SET completed_at=?, status=?, sources_checked=?, "
        "findings_created=?, error_message=? WHERE run_id=?",
        (
            datetime.now().isoformat(timespec="seconds"),
            status,
            sources_checked,
            findings_created,
            error,
            run_id,
        ),
    )
    con.commit()


def next_finding_id(con, d: date | None = None):
    d = d or date.today()
    prefix = f"CI-{d:%Y-%m}-"

    row = con.execute(
        "SELECT finding_id FROM findings "
        "WHERE finding_id LIKE ? "
        "ORDER BY finding_id DESC LIMIT 1",
        (prefix + "%",),
    ).fetchone()

    n = int(row["finding_id"].split("-")[-1]) + 1 if row else 1

    return f"{prefix}{n:05d}"


def competitor_id(con, brand_name):
    row = con.execute(
        "SELECT competitor_id FROM competitors WHERE brand_name=?",
        (brand_name,),
    ).fetchone()

    if not row:
        raise ValueError(f"Unknown competitor brand: {brand_name}")

    return row["competitor_id"]


def add_price_finding(
    con,
    run_id,
    competitor_brand,
    brand,
    category,
    product_name,
    model,
    price_kes,
    source_url,
    evidence_text,
    promotion_note=None,
    source_type="official website",
    verification_status="verified",
    confidence="high",
    published_date=None,
):
    today = date.today()
    fid = next_finding_id(con, today)

    source_competitor_id = competitor_id(con, competitor_brand)

    con.execute(
        """INSERT INTO findings (
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
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            fid,
            iso_week(today),
            run_id,
            source_competitor_id,
            brand,
            category,
            "price",
            f"Price observed: {product_name}",
            source_url,
            source_type,
            published_date,
            today.isoformat(),
            evidence_text,
            verification_status,
            confidence,
        ),
    )

    con.execute(
        """INSERT INTO price_observations (
            finding_id,
            product_name,
            model,
            price_kes,
            promotion_note,
            observed_date
        )
        VALUES (?,?,?,?,?,?)""",
        (
            fid,
            product_name,
            model,
            price_kes,
            promotion_note,
            today.isoformat(),
        ),
    )

    con.commit()

    return fid

def add_promotion_finding(
    con,
    run_id,
    competitor_brand,
    brand,
    category,
    promotion_type,
    offer_value,
    summary,
    source_url,
    evidence_text,
    target_segment=None,
    start_date=None,
    end_date=None,
    source_type="official website",
    verification_status="verified",
    confidence="high",
    published_date=None,
):
    """Create a promotion finding and its linked promotion observation."""

    today = date.today()
    fid = next_finding_id(con, today)

    source_competitor_id = competitor_id(con, competitor_brand)

    con.execute(
        """INSERT INTO findings (
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
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            fid,
            iso_week(today),
            run_id,
            source_competitor_id,
            brand,
            category,
            "promotion",
            summary,
            source_url,
            source_type,
            published_date,
            today.isoformat(),
            evidence_text,
            verification_status,
            confidence,
        ),
    )

    con.execute(
        """INSERT INTO promotion_observations (
            finding_id,
            promotion_type,
            offer_value,
            start_date,
            end_date,
            target_segment
        )
        VALUES (?,?,?,?,?,?)""",
        (
            fid,
            promotion_type,
            offer_value,
            start_date,
            end_date,
            target_segment,
        ),
    )

    con.commit()

    return fid

def previous_price(
    con,
    model,
    before_date,
    competitor_brand=None,
    brand=None,
):
    """Return the latest previous price for a product.

    Historical matching is source-aware when competitor_brand is supplied:

        brand + model + competitor/source

    This prevents a Hotpoint observation from being treated as the
    previous price for a Samsutech observation.

    If competitor_brand is omitted, the function preserves the original
    model-only lookup behavior for backward compatibility.

    Returns:
        (price_kes, observed_date) or None
    """

    if not model:
        return None

    params = [model, before_date]

    sql = """
        SELECT
            p.price_kes,
            p.observed_date
        FROM price_observations p
        JOIN findings f
            ON f.finding_id = p.finding_id
        WHERE p.model = ?
          AND p.observed_date < ?
    """

    if brand:
        sql += " AND f.brand = ?"
        params.append(brand)

    if competitor_brand:
        source_id = competitor_id(con, competitor_brand)
        sql += " AND f.competitor_id = ?"
        params.append(source_id)

    sql += """
        ORDER BY p.observed_date DESC, p.observation_id DESC
        LIMIT 1
    """

    row = con.execute(sql, params).fetchone()

    if not row:
        return None

    return row["price_kes"], row["observed_date"]


def price_change_pct(current, previous):
    """Calculate percentage price change.

    Returns None when there is no valid previous price.
    """
    if previous in (None, 0):
        return None

    return round((current - previous) / previous * 100, 2)


def add_news_finding(
    con,
    run_id,
    competitor_brand,
    brand,
    category,
    headline,
    news_type,
    summary,
    source_url,
    evidence_text,
    source_type="news media",
    verification_status="verified",
    confidence="high",
    published_date=None,
):
    """Create a news finding and its linked news observation."""

    today = date.today()
    fid = next_finding_id(con, today)

    source_competitor_id = competitor_id(con, competitor_brand)

    con.execute(
        """INSERT INTO findings (
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
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            fid,
            iso_week(today),
            run_id,
            source_competitor_id,
            brand,
            category,
            "news",
            summary,
            source_url,
            source_type,
            published_date,
            today.isoformat(),
            evidence_text,
            verification_status,
            confidence,
        ),
    )

    con.execute(
        """INSERT INTO news_observations (
            finding_id,
            headline,
            news_type
        )
        VALUES (?,?,?)""",
        (
            fid,
            headline,
            news_type,
        ),
    )

    con.commit()

    return fid