from phase3_evidence_retrieval import (
    connect,
    get_active_campaigns,
    get_upcoming_campaigns,
    get_strategic_alerts,
    get_market_trends,
    get_social_evidence,
    get_competitor_comparisons,
    get_catalogue_summary,
)


def show_keys(label, rows):
    print(f"{label}:")
    if rows:
        print(list(rows[0].keys()))
    else:
        print("NO ROWS")
    print()


def main():
    print("=" * 78)
    print("MIKA CI - PHASE 3D RETRIEVAL FIELD CHECK")
    print("=" * 78)
    print("MODE: READ-ONLY")
    print()

    conn = connect()

    show_keys("ACTIVE CAMPAIGNS", get_active_campaigns(conn))
    show_keys("UPCOMING CAMPAIGNS", get_upcoming_campaigns(conn))
    show_keys("STRATEGIC ALERTS", get_strategic_alerts(conn))
    show_keys("MARKET TRENDS", get_market_trends(conn))
    show_keys("SOCIAL EVIDENCE", get_social_evidence(conn))
    show_keys(
        "COMPETITOR COMPARISONS",
        get_competitor_comparisons(conn),
    )
    show_keys("CATALOGUE SUMMARY", get_catalogue_summary(conn))

    conn.close()

    print("=" * 78)
    print("PHASE 3D FIELD CHECK COMPLETE")
    print("NO DATABASE ROWS WERE WRITTEN")
    print("=" * 78)


if __name__ == "__main__":
    main()