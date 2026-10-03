"""
MIKA CI - Phase 3D Evidence-Aware Answer Composer

Purpose:
    Convert routed MIKA CI questions into evidence-aware answers
    using only persisted SQLite evidence.

Mode:
    READ-ONLY

Important rules:
    - No database writes.
    - Do not invent evidence.
    - Do not treat raw price observations as price movements.
    - Do not treat tracked catalogue counts as market-wide product breadth.
    - Do not treat social snapshots as complete social activity.
    - Do not treat concurrent signals as causality.
    - Distinguish competitor scope from brand scope.
    - Preserve evidence gaps rather than guessing.

Phase 3 architecture:

    User question
        ->
    Question router
        ->
    SQLite evidence retrieval
        ->
    Scope resolution
        ->
    Evidence filtering
        ->
    Answer composition
"""

from dataclasses import dataclass

from phase3_question_router import route_question
from phase3_evidence_retrieval import (
    connect,
    get_campaigns,
    get_active_campaigns,
    get_upcoming_campaigns,
    get_price_movements,
    get_strategic_alerts,
    get_market_trends,
    get_social_evidence,
    get_competitor_comparisons,
    get_catalogue_summary,
    get_competitor_master,
)


# =====================================================================
# ANSWER MODEL
# =====================================================================

@dataclass
class Answer:
    question: str
    intent: str
    confidence: str
    answer: str
    evidence: list
    limitations: list


# =====================================================================
# GENERAL HELPERS
# =====================================================================

def format_period(start_date, end_date):
    """
    Format a start/end date pair safely.
    """

    start = str(start_date or "").strip()
    end = str(end_date or "").strip()

    if start and end:
        if start == end:
            return start
        return f"{start} to {end}"

    if start:
        return start

    if end:
        return end

    return "date not recorded"


def rows_to_list(rows):
    """
    Convert retrieval results to a normal list.
    """

    if rows is None:
        return []

    return list(rows)


# =====================================================================
# SCOPE RESOLUTION
# =====================================================================

def resolve_scope(route, competitor_master):
    """
    Resolve the routed competitor/brand to authoritative competitor IDs.

    Important identity rules:

        Hotpoint
            -> brand_name = Hotpoint
            -> competitor_name = Hotpoint Appliances
            -> competitor_id = 1

        Ramtons
            -> brand_name = Ramtons
            -> competitor_name = Ramtons
            -> competitor_id = 2

        JTC
            -> brand_name = JTC
            -> competitor_name = Haier Kenya
            -> competitor_id = 18

    The resolver therefore accepts either the competitor name or its
    registered brand name.

    No database writes occur here.
    """

    competitor_ids = []
    brand = route.brand

    # ---------------------------------------------------------
    # Explicit competitor scope
    # ---------------------------------------------------------

    if route.competitor:
        target = route.competitor.strip().lower()

        for row in competitor_master:
            competitor_name = str(
                row.get("competitor_name") or ""
            ).strip().lower()

            brand_name = str(
                row.get("brand_name")
                or row.get("brand")
                or ""
            ).strip().lower()

            if target == competitor_name or target == brand_name:
                competitor_id = row.get("competitor_id")

                if (
                    competitor_id is not None
                    and competitor_id not in competitor_ids
                ):
                    competitor_ids.append(competitor_id)

        return {
            "competitor_ids": competitor_ids,
            "brand": brand,
        }

    # ---------------------------------------------------------
    # Brand scope
    # ---------------------------------------------------------

    if route.brand:
        target = route.brand.strip().lower()

        for row in competitor_master:
            brand_name = str(
                row.get("brand_name")
                or row.get("brand")
                or ""
            ).strip().lower()

            if brand_name == target:
                competitor_id = row.get("competitor_id")

                if (
                    competitor_id is not None
                    and competitor_id not in competitor_ids
                ):
                    competitor_ids.append(competitor_id)

        return {
            "competitor_ids": competitor_ids,
            "brand": brand,
        }

    # ---------------------------------------------------------
    # No explicit scope
    # ---------------------------------------------------------

    return {
        "competitor_ids": [],
        "brand": brand,
    }


# =====================================================================
# EVIDENCE FILTER
# =====================================================================

def matches_filter(row, route, scope):
    """
    Determine whether an evidence row belongs to the requested scope.

    Competitor scope:
        - Match competitor_id when available.
        - Otherwise match competitor_name.

    Brand scope:
        1. Match explicit brand field.
        2. Match competitor_name when the table stores the brand there.
        3. Fall back to a uniquely resolved competitor_id.

    Important JTC case:

        competitor_name = JTC
        brand = NULL
        competitor_id = NULL

    Therefore exact competitor_name == requested brand is required.
    """

    competitor_ids = scope.get("competitor_ids") or []
    brand = scope.get("brand")

    # ---------------------------------------------------------
    # Competitor / company scope
    # ---------------------------------------------------------

    if route.competitor:
        row_competitor_id = row.get("competitor_id")

        if row_competitor_id in competitor_ids:
            return True

        row_competitor_name = str(
            row.get("competitor_name") or ""
        ).strip().lower()

        requested_competitor = (
            route.competitor.strip().lower()
        )

        if row_competitor_name == requested_competitor:
            return True

        # Known database naming variant:
        # "Hotpoint Appliances" represents the tracked Hotpoint brand.
        if (
            requested_competitor == "hotpoint"
            and row_competitor_name == "hotpoint appliances"
        ):
            return True

        return False

    # ---------------------------------------------------------
    # Brand scope
    # ---------------------------------------------------------

    if route.brand:
        brand_target = brand.strip().lower()

        # Explicit brand field
        row_brand = str(
            row.get("brand") or ""
        ).strip().lower()

        if row_brand:
            return row_brand == brand_target

        # Direct brand identity stored in competitor_name.
        #
        # This preserves the JTC case.
        row_competitor_name = str(
            row.get("competitor_name") or ""
        ).strip().lower()

        if row_competitor_name == brand_target:
            return True

        # Unique competitor resolution fallback.
        row_competitor_id = row.get("competitor_id")

        return (
            len(competitor_ids) == 1
            and row_competitor_id == competitor_ids[0]
        )

    # ---------------------------------------------------------
    # No competitor or brand scope
    # ---------------------------------------------------------

    return True


# =====================================================================
# CAMPAIGNS
# =====================================================================

def compose_campaign_answer(
    question,
    route,
    rows,
    scope,
    upcoming=False,
):
    filtered = [
        row
        for row in rows
        if matches_filter(row, route, scope)
    ]

    label = "upcoming" if upcoming else ""

    if not filtered:
        requested_scope = route.competitor or route.brand

        if requested_scope:
            answer = (
                f"No {label} campaigns were retrieved for "
                f"{requested_scope} in the current evidence set."
            )
        else:
            answer = (
                f"No {label} campaigns were retrieved in the "
                "current evidence set."
            )

        return Answer(
            question=question,
            intent=route.intent,
            confidence=route.confidence,
            answer=answer,
            evidence=[],
            limitations=[
                "This describes the campaigns captured in the current MIKA CI evidence set.",
                "It does not establish that no other campaign activity exists.",
            ],
        )

    lines = []

    for row in filtered:
        period = format_period(
            row.get("start_date"),
            row.get("end_date"),
        )

        offer = row.get("offer_value")
        category = row.get("category")

        line = f"{row.get('campaign_name')} ({period})"

        if offer:
            line += f" - {offer}"

        if category:
            line += f" - category: {category}"

        lines.append(line)

    campaign_label = (
        f"{label} campaign"
        if label
        else f"campaign"
    )
    if len(filtered) != 1:
        campaign_label += "s"

    answer = (
        f"The current evidence set contains {len(filtered)} "
        f"{campaign_label}:\n"
        + "\n".join(
            f"- {line}"
            for line in lines
        )
    )

    evidence = []

    for row in filtered:
        source = row.get("source_url")
        verification = row.get("verification_status")
        confidence = row.get("confidence")

        evidence.append(
            f"{row.get('campaign_name')}: "
            f"verification={verification}, "
            f"confidence={confidence}, "
            f"source={source or 'not recorded'}"
        )

    return Answer(
        question=question,
        intent=route.intent,
        confidence=route.confidence,
        answer=answer,
        evidence=evidence,
        limitations=[
            "Campaigns shown are those persisted in the current MIKA CI evidence set.",
            "Campaign records should not be interpreted as complete market-wide campaign coverage.",
        ],
    )


# =====================================================================
# STRATEGIC ALERTS
# =====================================================================

def compose_alert_answer(
    question,
    route,
    rows,
    scope,
):
    filtered = [
        row
        for row in rows
        if matches_filter(row, route, scope)
    ]

    if not filtered:
        requested_scope = route.competitor or route.brand

        if requested_scope:
            answer = (
                f"No open strategic alerts were retrieved for "
                f"{requested_scope}."
            )
        else:
            answer = "No open strategic alerts were retrieved."

        return Answer(
            question=question,
            intent=route.intent,
            confidence=route.confidence,
            answer=answer,
            evidence=[],
            limitations=[
                "This means no matching OPEN alerts were retrieved from the current alert table.",
                "It does not prove that no unrecorded risk or activity exists.",
            ],
        )

    lines = []

    for row in filtered:
        priority = row.get("priority")
        title = row.get("title")
        alert_type = row.get("alert_type")

        lines.append(
            f"[{priority}] {title} - {alert_type}"
        )

    answer = (
        f"{len(filtered)} open strategic alert"
        f"{'s' if len(filtered) != 1 else ''} were retrieved:\n"
        + "\n".join(
            f"- {line}"
            for line in lines
        )
    )

    evidence = []

    for row in filtered:
        evidence.append(
            f"{row.get('title')}: "
            f"source={row.get('evidence_source')}, "
            f"period={format_period(row.get('period_start'), row.get('period_end'))}, "
            f"confidence={row.get('confidence')}"
        )

    return Answer(
        question=question,
        intent=route.intent,
        confidence=route.confidence,
        answer=answer,
        evidence=evidence,
        limitations=[
            "Priority is the internal MIKA CI alert priority, not a prediction of business impact.",
            "Concurrent price/campaign alerts do not establish causality.",
        ],
    )


# =====================================================================
# MARKET TRENDS
# =====================================================================

def compose_market_trend_answer(
    question,
    route,
    rows,
    scope,
):
    filtered = [
        row
        for row in rows
        if matches_filter(row, route, scope)
    ]

    if not filtered:
        requested_scope = route.competitor or route.brand

        if requested_scope:
            answer = (
                f"No matching market-trend records were retrieved "
                f"for {requested_scope}."
            )
        else:
            answer = (
                "No matching market-trend records were retrieved "
                "from the current evidence set."
            )

        return Answer(
            question=question,
            intent=route.intent,
            confidence=route.confidence,
            answer=answer,
            evidence=[],
            limitations=[
                "The absence of a stored trend signal is not evidence that no market activity occurred.",
            ],
        )

    lines = []

    for row in filtered:
        period = format_period(
            row.get("start_date"),
            row.get("end_date"),
        )

        lines.append(
            f"{row.get('title')} - "
            f"{row.get('signal_type')} - "
            f"{row.get('status')} - "
            f"{period}"
        )

    answer = (
        f"{len(filtered)} market-trend record"
        f"{'s' if len(filtered) != 1 else ''} were retrieved:\n"
        + "\n".join(
            f"- {line}"
            for line in lines
        )
    )

    evidence = [
        f"{row.get('title')}: "
        f"evidence_count={row.get('evidence_count')}, "
        f"confidence={row.get('confidence')}"
        for row in filtered
    ]

    return Answer(
        question=question,
        intent=route.intent,
        confidence=route.confidence,
        answer=answer,
        evidence=evidence,
        limitations=[
            "These are documented MIKA CI signals, not predictions.",
            "Concurrent signals do not establish causality.",
            "Tracked-source coverage is not equivalent to complete market coverage.",
        ],
    )


# =====================================================================
# SOCIAL EVIDENCE
# =====================================================================

def compose_social_answer(
    question,
    route,
    rows,
    scope,
):
    """
    Compose social evidence using social_observations schema.

    social_observations uses competitor_id as the authoritative
    competitor identity.
    """

    competitor_ids = set(
        scope.get("competitor_ids") or []
    )

    if route.competitor or route.brand:
        filtered = [
            row
            for row in rows
            if row.get("competitor_id") in competitor_ids
        ]
    else:
        filtered = list(rows)

    if not filtered:
        requested_scope = route.competitor or route.brand

        answer = (
            "No matching social evidence was retrieved"
            + (
                f" for {requested_scope}."
                if requested_scope
                else "."
            )
        )

        return Answer(
            question=question,
            intent=route.intent,
            confidence=route.confidence,
            answer=answer,
            evidence=[],
            limitations=[
                "Social coverage is limited to verified sources currently registered by MIKA CI.",
                "A missing observation does not establish that no social activity occurred.",
            ],
        )

    lines = []

    for row in filtered:
        text = str(
            row.get("post_text") or ""
        ).strip()

        if len(text) > 180:
            text = text[:177] + "..."

        lines.append(
            f"{row.get('platform')} - "
            f"{row.get('observed_date')} - "
            f"{text or 'post text not captured'}"
        )

    answer = (
        f"{len(filtered)} social observation"
        f"{'s' if len(filtered) != 1 else ''} were retrieved:\n"
        + "\n".join(
            f"- {line}"
            for line in lines[:10]
        )
    )

    if len(filtered) > 10:
        answer += (
            f"\n- ...and {len(filtered) - 10} "
            "additional observations."
        )

    evidence = [
        f"{row.get('platform')} / {row.get('account_name')}: "
        f"published={row.get('published_date')}, "
        f"observed={row.get('observed_date')}, "
        f"verification={row.get('verification_status')}, "
        f"confidence={row.get('confidence')}"
        for row in filtered[:10]
    ]

    return Answer(
        question=question,
        intent=route.intent,
        confidence=route.confidence,
        answer=answer,
        evidence=evidence,
        limitations=[
            "Current social evidence is a tracked-source snapshot rather than a complete social-media record.",
            "The current dataset contains observations from a limited set of verified sources.",
        ],
    )


# =====================================================================
# PRODUCT CATALOGUE
# =====================================================================

def compose_catalogue_answer(
    question,
    route,
    rows,
):
    """
    Catalogue summaries are already normalized by the retrieval layer.

    Expected fields:
        catalogue
        product_count
        first_seen
        last_seen
    """

    filtered = rows

    if route.competitor:
        target = route.competitor.strip().lower()

        filtered = [
            row
            for row in rows
            if str(
                row.get("catalogue") or ""
            ).strip().lower() == target
        ]

    elif route.brand:
        target = route.brand.strip().lower()

        filtered = [
            row
            for row in rows
            if str(
                row.get("catalogue") or ""
            ).strip().lower() == target
        ]

    if not filtered:
        requested_scope = route.competitor or route.brand

        answer = (
            "No matching tracked catalogue summary was retrieved"
            + (
                f" for {requested_scope}."
                if requested_scope
                else "."
            )
        )

        return Answer(
            question=question,
            intent=route.intent,
            confidence=route.confidence,
            answer=answer,
            evidence=[],
            limitations=[
                "Catalogue coverage is limited to the tracked sources represented in MIKA CI.",
                "A missing catalogue record does not establish absence of products in the wider market.",
            ],
        )

    lines = []

    for row in filtered:
        lines.append(
            f"{row.get('catalogue')}: "
            f"{row.get('product_count')} tracked products "
            f"({row.get('first_seen')} to {row.get('last_seen')})"
        )

    answer = (
        "Tracked catalogue coverage:\n"
        + "\n".join(
            f"- {line}"
            for line in lines
        )
    )

    evidence = [
        f"{row.get('catalogue')}: "
        f"{row.get('product_count')} products, "
        f"first_seen={row.get('first_seen')}, "
        f"last_seen={row.get('last_seen')}"
        for row in filtered
    ]

    return Answer(
        question=question,
        intent=route.intent,
        confidence=route.confidence,
        answer=answer,
        evidence=evidence,
        limitations=[
            "Catalogue counts represent tracked-source coverage, not market-wide product breadth.",
            "Catalogue persistence is not by itself proof of a product launch or competitive advantage.",
        ],
    )



# =====================================================================
# COMPETITOR COMPARISON
# =====================================================================


def compose_comparison_answer(
    question,
    route,
    rows,
    scope,
    competitor_master,
):
    """
    Compose evidence-aware competitor comparison answers.

    Comparison evidence is filtered by competitor_id because that is
    the authoritative identity stored in competitor_comparisons.

    Multiple competitors are resolved directly from the question using
    the competitor master table.

    No ranking or overall competitor score is produced.
    """

    question_lower = question.strip().lower()

    requested_ids = []
    requested_names = []

    # ---------------------------------------------------------
    # Resolve all explicitly named competitors / brands
    # ---------------------------------------------------------

    for master_row in competitor_master:
        competitor_id = master_row.get("competitor_id")

        competitor_name = str(
            master_row.get("competitor_name") or ""
        ).strip()

        brand_name = str(
            master_row.get("brand_name")
            or master_row.get("brand")
            or ""
        ).strip()

        if competitor_id is None:
            continue

        matched_name = None

        if (
            competitor_name
            and competitor_name.lower() in question_lower
        ):
            matched_name = competitor_name

        elif (
            brand_name
            and brand_name.lower() in question_lower
        ):
            matched_name = brand_name

        if matched_name:
            if competitor_id not in requested_ids:
                requested_ids.append(competitor_id)
                requested_names.append(matched_name)

    # ---------------------------------------------------------
    # Fall back to normal scope when fewer than two competitors
    # were explicitly detected.
    # ---------------------------------------------------------

    if len(requested_ids) < 2:
        requested_ids = list(
            scope.get("competitor_ids") or []
        )

    # ---------------------------------------------------------
    # Filter persisted comparison evidence
    # ---------------------------------------------------------

    if requested_ids:
        filtered = [
            row
            for row in rows
            if row.get("competitor_id") in requested_ids
        ]
    else:
        filtered = []

    # ---------------------------------------------------------
    # No matching evidence
    # ---------------------------------------------------------

    if not filtered:
        requested_scope = (
            " and ".join(requested_names)
            if requested_names
            else "the requested scope"
        )

        return Answer(
            question=question,
            intent=route.intent,
            confidence=route.confidence,
            answer=(
                "No matching competitor comparison records "
                f"were retrieved for {requested_scope}."
            ),
            evidence=[],
            limitations=[
                "The comparison is limited to persisted MIKA CI comparison records.",
                "A missing comparison record does not establish absence of competitive activity.",
            ],
        )

    # ---------------------------------------------------------
    # Build evidence lines
    # ---------------------------------------------------------

    lines = []
    evidence = []

    for row in filtered:
        competitor_name = (
            row.get("competitor_name")
            or "Unknown competitor"
        )

        brand = row.get("brand")
        dimension = (
            row.get("dimension")
            or "Unknown dimension"
        )

        metric_name = (
            row.get("metric_name")
            or "Unknown metric"
        )

        metric_value = row.get("metric_value")
        observation_count = (
            row.get("observation_count") or 0
        )

        period = format_period(
            row.get("period_start"),
            row.get("period_end"),
        )

        coverage_status = (
            row.get("coverage_status")
            or "not recorded"
        )

        confidence = (
            row.get("confidence")
            or "not recorded"
        )

        brand_text = (
            f" / {brand}"
            if brand
            else ""
        )

        value_text = (
            f" | value={metric_value}"
            if metric_value is not None
            else ""
        )

        lines.append(
            f"{competitor_name}{brand_text} - "
            f"{dimension} - "
            f"{metric_name} - "
            f"observations={observation_count}"
            f"{value_text} - "
            f"period={period} - "
            f"coverage={coverage_status}"
        )

        evidence.append(
            f"{competitor_name}{brand_text}: "
            f"{dimension} / {metric_name}; "
            f"observations={observation_count}; "
            f"period={period}; "
            f"coverage={coverage_status}; "
            f"confidence={confidence}; "
            f"evidence={row.get('evidence_summary')}"
        )

    # ---------------------------------------------------------
    # Determine displayed comparison scope
    # ---------------------------------------------------------

    if len(requested_names) >= 2:
        scope_text = " and ".join(requested_names)
    else:
        scope_text = ", ".join(
            sorted(
                {
                    str(row.get("competitor_name"))
                    for row in filtered
                    if row.get("competitor_name")
                }
            )
        )

    # ---------------------------------------------------------
    # Evidence-aware answer
    # ---------------------------------------------------------

    answer = (
        f"Persisted comparison evidence was retrieved for "
        f"{scope_text}.\n"
        f"{len(filtered)} comparison records were retrieved:\n"
        + "\n".join(
            f"- {line}"
            for line in lines[:20]
        )
    )

    if len(filtered) > 20:
        answer += (
            f"\n- ...and {len(filtered) - 20} "
            "additional comparison records."
        )

    return Answer(
        question=question,
        intent=route.intent,
        confidence=route.confidence,
        answer=answer,
        evidence=evidence[:20],
        limitations=[
            "Comparison results are limited to persisted MIKA CI evidence.",
            "Observation counts indicate tracked evidence coverage, not market share.",
            "Price coverage reflects observed products and sources, not complete market pricing.",
            "Different competitors may have different evidence coverage in the current dataset.",
            "No overall competitor ranking or score is produced.",
        ],
    )


# =====================================================================
# COMPETITOR / BRAND ACTIVITY
# =====================================================================

def compose_competitor_activity_answer(
    question,
    route,
    conn,
    scope,
):
    all_alerts = get_strategic_alerts(conn)
    all_campaigns = get_active_campaigns(conn)
    all_upcoming = get_upcoming_campaigns(conn)
    all_social = get_social_evidence(conn)
    all_trends = get_market_trends(conn)

    alerts = [
        row
        for row in all_alerts
        if matches_filter(row, route, scope)
    ]

    campaigns = [
        row
        for row in all_campaigns
        if matches_filter(row, route, scope)
    ]

    upcoming = [
        row
        for row in all_upcoming
        if matches_filter(row, route, scope)
    ]

    social = [
        row
        for row in all_social
        if matches_filter(row, route, scope)
    ]

    trends = [
        row
        for row in all_trends
        if matches_filter(row, route, scope)
    ]

    requested_scope = route.competitor or route.brand

    if not any(
        [
            alerts,
            campaigns,
            upcoming,
            social,
            trends,
        ]
    ):
        answer = (
            f"No current evidence was retrieved for "
            f"{requested_scope}."
            if requested_scope
            else "No current competitor activity evidence was retrieved."
        )

        return Answer(
            question=question,
            intent=route.intent,
            confidence=route.confidence,
            answer=answer,
            evidence=[],
            limitations=[
                "This is a statement about the current MIKA CI evidence set, not proof of absence of activity.",
            ],
        )

    parts = []

    if campaigns:
        parts.append(
            f"Active campaigns: {len(campaigns)}"
        )

    if upcoming:
        parts.append(
            f"Upcoming campaigns: {len(upcoming)}"
        )

    if alerts:
        parts.append(
            f"Open strategic alerts: {len(alerts)}"
        )

    if social:
        parts.append(
            f"Social observations: {len(social)}"
        )

    if trends:
        parts.append(
            f"Market-trend records involving this scope: {len(trends)}"
        )

    answer = (
        f"Current documented activity for "
        f"{requested_scope or 'the requested scope'}:\n"
        + "\n".join(
            f"- {part}"
            for part in parts
        )
    )

    evidence = []

    for row in campaigns[:5]:
        evidence.append(
            f"Campaign: {row.get('campaign_name')} - "
            f"{format_period(row.get('start_date'), row.get('end_date'))}"
        )

    for row in upcoming[:5]:
        evidence.append(
            f"Upcoming campaign: {row.get('campaign_name')} - "
            f"{format_period(row.get('start_date'), row.get('end_date'))}"
        )

    for row in alerts[:5]:
        evidence.append(
            f"Alert: {row.get('title')} - "
            f"priority={row.get('priority')}"
        )

    for row in social[:5]:
        evidence.append(
            f"Social: {row.get('platform')} - "
            f"observed={row.get('observed_date')}"
        )

    for row in trends[:5]:
        evidence.append(
            f"Trend: {row.get('title')} - "
            f"status={row.get('status')}"
        )

    return Answer(
        question=question,
        intent=route.intent,
        confidence=route.confidence,
        answer=answer,
        evidence=evidence,
        limitations=[
            "Activity is limited to the evidence types currently retrieved by MIKA CI.",
            "The counts are evidence counts, not measures of market share or competitive strength.",
            "Social observations are not equivalent to sustained social trends.",
        ],
    )


# =====================================================================
# MAIN ANSWER COMPOSER
# =====================================================================

def compose_answer(question: str) -> Answer:
    route = route_question(question)

    # ---------------------------------------------------------
    # Unsupported question
    # ---------------------------------------------------------

    if route.intent == "UNSUPPORTED":
        return Answer(
            question=question,
            intent=route.intent,
            confidence=route.confidence,
            answer=(
                "I could not map that question to a supported MIKA CI "
                "evidence category."
            ),
            evidence=[],
            limitations=[
                "The current Phase 3D composer only answers from defined MIKA CI evidence categories.",
            ],
        )

    conn = connect()

    try:
        # -----------------------------------------------------
        # Resolve company / brand identity once.
        # -----------------------------------------------------

        competitor_master = get_competitor_master(conn)

        scope = resolve_scope(
            route,
            competitor_master,
        )

        # -----------------------------------------------------
        # Campaigns / promotions
        # -----------------------------------------------------

        if route.intent == "CAMPAIGNS":
            return compose_campaign_answer(
                question,
                route,
                get_campaigns(conn),
                scope,
                upcoming=False,
            )

        if route.intent == "CAMPAIGNS_ACTIVE":
            return compose_campaign_answer(
                question,
                route,
                get_active_campaigns(conn),
                scope,
                upcoming=False,
            )

        # -----------------------------------------------------
        # Upcoming campaigns
        # -----------------------------------------------------

        if route.intent == "CAMPAIGNS_UPCOMING":
            return compose_campaign_answer(
                question,
                route,
                get_upcoming_campaigns(conn),
                scope,
                upcoming=True,
            )

        # -----------------------------------------------------
        # Strategic alerts
        # -----------------------------------------------------

        if route.intent == "STRATEGIC_ALERTS":
            return compose_alert_answer(
                question,
                route,
                get_strategic_alerts(conn),
                scope,
            )

        # -----------------------------------------------------
        # Market trends
        # -----------------------------------------------------

        if route.intent == "MARKET_TRENDS":
            return compose_market_trend_answer(
                question,
                route,
                get_market_trends(conn),
                scope,
            )

        # -----------------------------------------------------
        # Social evidence
        # -----------------------------------------------------

        if route.intent == "SOCIAL_EVIDENCE":
            return compose_social_answer(
                question,
                route,
                get_social_evidence(conn),
                scope,
            )

        # -----------------------------------------------------
        # Product catalogue
        # -----------------------------------------------------

        if route.intent == "PRODUCT_CATALOGUE":
            return compose_catalogue_answer(
                question,
                route,
                get_catalogue_summary(conn),
            )

        # -----------------------------------------------------
        # Competitor comparison
        # -----------------------------------------------------

        if route.intent == "COMPETITOR_COMPARISON":
            return compose_comparison_answer(
                question,
                route,
                get_competitor_comparisons(conn),
                scope,
                competitor_master,
            )

        # -----------------------------------------------------
        # Competitor / brand activity
        # -----------------------------------------------------

        if route.intent == "COMPETITOR_ACTIVITY":
            return compose_competitor_activity_answer(
                question,
                route,
                conn,
                scope,
            )

        # -----------------------------------------------------
        # Validated price movements
        # -----------------------------------------------------

        if route.intent == "PRICE_MOVEMENTS":
            alerts = [
                row
                for row in get_strategic_alerts(conn)
                if row.get("alert_type") == "PRICE_MOVEMENT"
                and matches_filter(
                    row,
                    route,
                    scope,
                )
            ]

            if not alerts:
                requested_scope = route.competitor or route.brand

                if requested_scope:
                    answer_text = (
                        "No persisted price-movement alerts were "
                        f"retrieved for {requested_scope}."
                    )
                else:
                    answer_text = (
                        "No persisted price-movement alerts were "
                        "retrieved for the requested scope."
                    )

                return Answer(
                    question=question,
                    intent=route.intent,
                    confidence=route.confidence,
                    answer=answer_text,
                    evidence=[],
                    limitations=[
                        "Raw price observations are not treated as price movements unless a validated movement signal has been persisted.",
                    ],
                )

            return compose_alert_answer(
                question,
                route,
                alerts,
                scope,
            )

        # -----------------------------------------------------
        # Fallback
        # -----------------------------------------------------

        return Answer(
            question=question,
            intent=route.intent,
            confidence=route.confidence,
            answer=(
                "No answer composer is currently mapped "
                "to this intent."
            ),
            evidence=[],
            limitations=[],
        )

    finally:
        conn.close()


# =====================================================================
# OUTPUT
# =====================================================================

def print_answer(answer: Answer):
    print()
    print("=" * 78)
    print("QUESTION")
    print("=" * 78)
    print(answer.question)

    print()
    print("INTENT")
    print("=" * 78)
    print(answer.intent)

    print()
    print("ANSWER")
    print("=" * 78)
    print(answer.answer)

    print()
    print("EVIDENCE")
    print("=" * 78)

    if answer.evidence:
        for item in answer.evidence:
            print(f"- {item}")
    else:
        print("No evidence items returned.")

    print()
    print("LIMITATIONS")
    print("=" * 78)

    if answer.limitations:
        for item in answer.limitations:
            print(f"- {item}")
    else:
        print("None recorded.")

    print()


# =====================================================================
# PHASE 3D TEST
# =====================================================================

def main():
    print("=" * 78)
    print("MIKA CI - PHASE 3D EVIDENCE-AWARE ANSWER COMPOSER")
    print("=" * 78)
    print("MODE: READ-ONLY")
    print()

    test_questions = [
        "What campaigns are active?",
        "What campaigns are upcoming?",
        "What price movements have been detected?",
        "What strategic alerts are open?",
        "What market trends are documented?",
        "Show me Hotpoint social activity.",
        "What products does Haier have in the tracked catalogue?",
        "Compare Hotpoint and Ramtons.",
        "What has Ramtons been doing recently?",
        "What is happening with JTC?",
    ]

    for question in test_questions:
        print_answer(
            compose_answer(question)
        )

    print("=" * 78)
    print("PHASE 3D COMPOSER TEST COMPLETE")
    print("NO DATABASE ROWS WERE WRITTEN")
    print("=" * 78)


if __name__ == "__main__":
    main()