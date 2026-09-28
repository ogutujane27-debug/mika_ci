from dataclasses import dataclass
import re


@dataclass
class Route:
    intent: str
    confidence: str
    competitor: str | None = None
    brand: str | None = None
    query: str = ""


COMPETITOR_ALIASES = {
    "hotpoint": "Hotpoint",
    "hotpoint appliances": "Hotpoint",
    "ramtons": "Ramtons",
    "hisense": "Hisense",
    "hisense kenya": "Hisense",
    "armco": "Armco",
    "haier": "Haier",
    "haier kenya": "Haier",
    "opalnet": "Opalnet",
    "samsutech": "Samsutech",
    "bruhm": "Bruhm",
    "philips": "Philips",
    "k-elec": "K-Elec",
    "k elec": "K-Elec",
}


BRAND_ALIASES = {
    "hotpoint": "Hotpoint",
    "ramtons": "Ramtons",
    "hisense": "Hisense",
    "armco": "Armco",
    "haier": "Haier",
    "lg": "LG",
    "midea": "Midea",
    "samsung": "Samsung",
    "tcl": "TCL",
    "moulinex": "Moulinex",
    "krups": "Krups",
    "scl": "SCL",
    "tefal": "Tefal",
    "berklays": "Berklays",
    "bruhm": "Bruhm",
    "philips": "Philips",
    "k-elec": "K-Elec",
    "jtc": "JTC",
}


def normalize_question(question: str) -> str:
    return " ".join(question.strip().lower().split())


def find_alias(text: str, aliases: dict[str, str]) -> str | None:
    matches = []

    for alias, canonical in aliases.items():
        pattern = rf"(?<!\w){re.escape(alias)}(?!\w)"

        if re.search(pattern, text):
            matches.append((len(alias), canonical))

    if not matches:
        return None

    matches.sort(reverse=True)
    return matches[0][1]


def route_question(question: str) -> Route:
    normalized = normalize_question(question)

    if not normalized:
        return Route(
            intent="UNSUPPORTED",
            confidence="LOW",
            query=question,
        )

    competitor = find_alias(normalized, COMPETITOR_ALIASES)
    brand = find_alias(normalized, BRAND_ALIASES)

    # ---------------------------------------------------------
    # Campaigns
    # ---------------------------------------------------------
    if (
        "campaign" in normalized
        or "promotion" in normalized
        or "promotions" in normalized
        or "offer" in normalized
        or "offers" in normalized
        or "sale" in normalized
    ):
        if "active" in normalized or "currently running" in normalized:
            intent = "CAMPAIGNS_ACTIVE"
        elif (
            "upcoming" in normalized
            or "next" in normalized
            or "coming" in normalized
        ):
            intent = "CAMPAIGNS_UPCOMING"
        else:
            intent = "CAMPAIGNS"

        return Route(
            intent=intent,
            confidence="HIGH",
            competitor=competitor,
            brand=brand,
            query=question,
        )

    # ---------------------------------------------------------
    # Price movements
    # ---------------------------------------------------------
    if (
        "price movement" in normalized
        or "price movements" in normalized
        or "price change" in normalized
        or "price changes" in normalized
        or "price increase" in normalized
        or "price increases" in normalized
        or "price decrease" in normalized
        or "price decreases" in normalized
        or "price drop" in normalized
        or "price drops" in normalized
        or "prices changed" in normalized
        or "prices change" in normalized
    ):
        return Route(
            intent="PRICE_MOVEMENTS",
            confidence="HIGH",
            competitor=competitor,
            brand=brand,
            query=question,
        )

    # ---------------------------------------------------------
    # Strategic alerts
    # ---------------------------------------------------------
    if (
        "strategic alert" in normalized
        or "strategic alerts" in normalized
        or "alerts" in normalized
        or "alert" in normalized
        or "warning" in normalized
        or "warnings" in normalized
    ):
        return Route(
            intent="STRATEGIC_ALERTS",
            confidence="HIGH",
            competitor=competitor,
            brand=brand,
            query=question,
        )

    # ---------------------------------------------------------
    # Market trends
    # ---------------------------------------------------------
    if (
        "market trend" in normalized
        or "market trends" in normalized
        or "market trend" in normalized
        or "market" in normalized
    ):
        return Route(
            intent="MARKET_TRENDS",
            confidence="MEDIUM",
            competitor=competitor,
            brand=brand,
            query=question,
        )

    # ---------------------------------------------------------
    # Social evidence
    # ---------------------------------------------------------
    if (
        "social" in normalized
        or "facebook" in normalized
        or "instagram" in normalized
        or "social media" in normalized
        or "post" in normalized
        or "posts" in normalized
    ):
        return Route(
            intent="SOCIAL_EVIDENCE",
            confidence="HIGH",
            competitor=competitor,
            brand=brand,
            query=question,
        )

    # ---------------------------------------------------------
    # Product / catalogue evidence
    # ---------------------------------------------------------
    if (
        "catalogue" in normalized
        or "catalog" in normalized
        or "product catalogue" in normalized
        or "products" in normalized
        or "product range" in normalized
        or "product ranges" in normalized
        or "sku" in normalized
        or "skus" in normalized
        or "product launch" in normalized
        or "product launches" in normalized
    ):
        return Route(
            intent="PRODUCT_CATALOGUE",
            confidence="HIGH",
            competitor=competitor,
            brand=brand,
            query=question,
        )

    # ---------------------------------------------------------
    # Competitor comparison
    # ---------------------------------------------------------
    if (
        "compare" in normalized
        or "comparison" in normalized
        or "compared with" in normalized
        or "versus" in normalized
        or " vs " in f" {normalized} "
    ):
        return Route(
            intent="COMPETITOR_COMPARISON",
            confidence="HIGH",
            competitor=competitor,
            brand=brand,
            query=question,
        )

        # ---------------------------------------------------------
    # Competitor / brand activity
    # ---------------------------------------------------------
    if competitor or brand:
        return Route(
            intent="COMPETITOR_ACTIVITY",
            confidence="HIGH" if competitor else "MEDIUM",
            competitor=competitor,
            brand=brand,
            query=question,
        )

    # ---------------------------------------------------------
    # Unsupported / ambiguous
    # ---------------------------------------------------------
    return Route(
        intent="UNSUPPORTED",
        confidence="LOW",
        competitor=competitor,
        brand=brand,
        query=question,
    )


def print_route(question: str):
    route = route_question(question)

    print(f"QUESTION : {question}")
    print(f"INTENT   : {route.intent}")
    print(f"CONFIDENCE: {route.confidence}")
    print(f"COMPETITOR: {route.competitor}")
    print(f"BRAND     : {route.brand}")
    print()


def main():
    print("=" * 78)
    print("MIKA CI - PHASE 3C QUESTION ROUTER")
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
        "Tell me something about the Kenyan appliance market.",
    ]

    for question in test_questions:
        print_route(question)

    print("=" * 78)
    print("PHASE 3C ROUTER TEST COMPLETE")
    print("NO DATABASE ROWS WERE WRITTEN")
    print("=" * 78)


if __name__ == "__main__":
    main()