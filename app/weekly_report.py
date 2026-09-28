import sqlite3
from datetime import datetime
from pathlib import Path

DB = Path("data/mika_competitive_intel.db")
REPORT_DIR = Path("reports")
REPORT_DIR.mkdir(exist_ok=True)


def get_current_week(con):
    row = con.execute(
        """
        SELECT scan_week
        FROM scan_runs
        WHERE status = 'completed'
        ORDER BY run_id DESC
        LIMIT 1
        """
    ).fetchone()

    if not row:
        raise RuntimeError("No completed scan run found.")

    return row[0]


def fetch_summary(con, week):
    return con.execute(
        """
        SELECT finding_type, COUNT(*) AS total
        FROM findings
        WHERE scan_week = ?
        GROUP BY finding_type
        ORDER BY finding_type
        """,
        (week,),
    ).fetchall()


def fetch_brand_summary(con, week):
    return con.execute(
        """
        SELECT
            brand,
            finding_type,
            COUNT(*) AS total
        FROM findings
        WHERE scan_week = ?
        GROUP BY brand, finding_type
        ORDER BY brand, finding_type
        """,
        (week,),
    ).fetchall()


def fetch_prices(con, week):
    return con.execute(
        """
        SELECT
            f.brand,
            f.category,
            p.product_name,
            p.model,
            p.price_kes,
            p.promotion_note,
            p.observed_date,
            f.source_url
        FROM price_observations p
        JOIN findings f
            ON f.finding_id = p.finding_id
        WHERE f.scan_week = ?
        ORDER BY f.brand, p.product_name
        """,
        (week,),
    ).fetchall()


def fetch_promotions(con, week):
    return con.execute(
        """
        SELECT
            f.brand,
            f.category,
            p.promotion_type,
            p.offer_value,
            p.start_date,
            p.end_date,
            p.target_segment,
            f.observed_date,
            f.source_url
        FROM promotion_observations p
        JOIN findings f
            ON f.finding_id = p.finding_id
        WHERE f.scan_week = ?
        ORDER BY f.brand, p.offer_value
        """,
        (week,),
    ).fetchall()


def fetch_news(con, week):
    return con.execute(
        """
        SELECT
            f.brand,
            f.category,
            n.headline,
            n.news_type,
            f.published_date,
            f.observed_date,
            f.source_url
        FROM news_observations n
        JOIN findings f
            ON f.finding_id = n.finding_id
        WHERE f.scan_week = ?
        ORDER BY f.brand, f.observed_date DESC
        """,
        (week,),
    ).fetchall()


def generate_report(con, week):
    summary = fetch_summary(con, week)
    brand_summary = fetch_brand_summary(con, week)
    prices = fetch_prices(con, week)
    promotions = fetch_promotions(con, week)
    news = fetch_news(con, week)

    summary_map = {
        row["finding_type"]: row["total"]
        for row in summary
    }

    total_findings = sum(summary_map.values())

    lines = []

    lines.append("# MIKA Competitive Intelligence Report")
    lines.append("")
    lines.append(f"**Reporting week:** {week}")
    lines.append(
        f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    )
    lines.append("")

    lines.append("## 1. Executive Summary")
    lines.append("")
    lines.append(
        f"Total current-week findings: **{total_findings}**"
    )
    lines.append(
        f"- Price observations: **{summary_map.get('price', 0)}**"
    )
    lines.append(
        f"- Promotion observations: **{summary_map.get('promotion', 0)}**"
    )
    lines.append(
        f"- News observations: **{summary_map.get('news', 0)}**"
    )
    lines.append("")

    lines.append("## 2. Findings by Competitor")
    lines.append("")
    lines.append("| Brand | Type | Findings |")
    lines.append("|---|---|---:|")

    for row in brand_summary:
        lines.append(
            f"| {row['brand']} | "
            f"{row['finding_type']} | "
            f"{row['total']} |"
        )

    lines.append("")

    lines.append("## 3. Price Observations")
    lines.append("")
    lines.append("| Brand | Category | Product | Model | Price (KSh) | Promotion Note |")
    lines.append("|---|---|---|---|---:|---|")

    for row in prices:
        product = (row["product_name"] or "").replace("|", "/")
        category = (row["category"] or "").replace("|", "/")
        model = row["model"] or ""
        note = row["promotion_note"] or ""

        lines.append(
            f"| {row['brand']} | "
            f"{category} | "
            f"{product} | "
            f"{model} | "
            f"{row['price_kes']:,.2f} | "
            f"{note} |"
        )

    lines.append("")

    lines.append("## 4. Promotions")
    lines.append("")
    lines.append(
        "| Brand | Category | Type | Offer | Start | End | Target |"
    )
    lines.append("|---|---|---|---|---|---|---|")

    for row in promotions:
        category = (row["category"] or "").replace("|", "/")
        offer = (row["offer_value"] or "").replace("|", "/")
        target = (row["target_segment"] or "").replace("|", "/")

        lines.append(
            f"| {row['brand']} | "
            f"{category} | "
            f"{row['promotion_type']} | "
            f"{offer} | "
            f"{row['start_date'] or ''} | "
            f"{row['end_date'] or ''} | "
            f"{target} |"
        )

    lines.append("")

    lines.append("## 5. News and Market Signals")
    lines.append("")

    if news:
        lines.append(
            "| Brand | Category | Headline | News Type | Published | Source |"
        )
        lines.append("|---|---|---|---|---|---|")

        for row in news:
            headline = (row["headline"] or "").replace("|", "/")
            category = (row["category"] or "").replace("|", "/")

            lines.append(
                f"| {row['brand']} | "
                f"{category} | "
                f"{headline} | "
                f"{row['news_type']} | "
                f"{row['published_date'] or ''} | "
                f"{row['source_url'] or ''} |"
            )
    else:
        lines.append("No qualifying news observations were recorded.")

    lines.append("")

    lines.append("## 6. Data Coverage")
    lines.append("")
    lines.append(
        "This report contains only findings assigned to the reporting week."
    )
    lines.append(
        "Historical findings remain in the database and are not included "
        "in the weekly totals above."
    )
    lines.append("")

    return "\n".join(lines)


def main():
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row

    try:
        week = get_current_week(con)
        report = generate_report(con, week)

        output = REPORT_DIR / f"MIKA_CI_{week}.md"
        output.write_text(report, encoding="utf-8")

        print("REPORT GENERATED")
        print("=" * 70)
        print(f"Week: {week}")
        print(f"File: {output}")
        print()

        print(report[:3000])

    finally:
        con.close()


if __name__ == "__main__":
    main()