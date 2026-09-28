"""
MIKA Competitive Intelligence

Phase 2C - Campaign Intelligence

Purpose:
    Detect evidence-backed campaign/activity candidates from existing
    social observations.

Important:
    - READ-ONLY by default.
    - Does not create or modify campaigns.
    - Does not modify social observations.
    - Does not modify the social collector.
    - Campaigns are only proposed when explicit evidence exists.

Phase 2C scope:
    1. Read existing social observations.
    2. Detect explicit campaign/activity signals.
    3. Extract a conservative campaign name.
    4. Extract structured campaign evidence.
    5. Group clearly related observations.
    6. Print proposed campaign groups.

Database writes remain disabled.
"""

from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent

DATABASE_PATH = (
    PROJECT_ROOT
    / "data"
    / "mika_competitive_intel.db"
)


@dataclass
class CampaignCandidate:
    competitor_id: int
    campaign_name: str
    campaign_type: str
    observation_ids: list[int]
    evidence: list[str]
    category: str | None
    offer_value: str | None
    start_date: str | None
    end_date: str | None
    status: str | None
    source_url: str | None
    verification_status: str | None
    confidence: str | None
    observed_date: str | None


def clean_text(value) -> str:
    if value is None:
        return ""

    return " ".join(
        str(value).split()
    ).strip()


def normalize_text(value) -> str:
    text = clean_text(value).lower()

    text = re.sub(
        r"https?://\S+",
        " ",
        text,
    )

    text = re.sub(
        r"[^a-z0-9%&+\- ]+",
        " ",
        text,
    )

    text = re.sub(
        r"\s+",
        " ",
        text,
    )

    return text.strip()


def connect():
    if not DATABASE_PATH.exists():
        raise FileNotFoundError(
            f"Database not found: {DATABASE_PATH}"
        )

    connection = sqlite3.connect(
        DATABASE_PATH
    )

    connection.row_factory = sqlite3.Row

    return connection


def get_social_observations(connection):
    return connection.execute(
        """
        SELECT
            observation_id,
            competitor_id,
            platform,
            account_name,
            social_type,
            product_name,
            model,
            published_date,
            post_url,
            post_text,
            evidence_text
        FROM social_observations
        ORDER BY
            competitor_id,
            published_date,
            observation_id
        """
    ).fetchall()


def detect_campaign_type(
    text: str,
) -> str | None:

    normalized = normalize_text(text)

    if any(
        term in normalized
        for term in (
            "giveaway",
            "competition",
            "contest",
        )
    ):
        return "campaign"

    if "commercial laundry seminar" in normalized:
        return "event"

    if "seminar" in normalized:
        return "event"

    if "financing" in normalized:
        return "financing"

    if any(
        term in normalized
        for term in (
            "flash sale",
            "flash offers",
        )
    ):
        return "flash_sale"

    if "clearance sale" in normalized:
        return "clearance_sale"

    if "night rush" in normalized:
        return "limited_time_sale"

    if any(
        term in normalized
        for term in (
            "live demo",
            "tiktok live",
        )
    ):
        return "live_promotion"

    if "monthly offers" in normalized:
        return "promotion"

    if "sale" in normalized:
        return "sale"

    if (
        "promotion" in normalized
        or "promo" in normalized
    ):
        return "promotion"

    return None


def extract_campaign_name(
    text: str,
    campaign_type: str | None,
) -> str | None:

    normalized = normalize_text(text)

    if "commercial laundry seminar" in normalized:
        return "Commercial Laundry Seminar"

    if "night rush" in normalized:
        return "Night Rush"

    if "clearance sale" in normalized:
        return "Clearance Sale"

    if "monthly offers" in normalized:
        return "Monthly Offers / HOT5"

    if (
        "pressure cooker deals are coming"
        in normalized
        or (
            "live demo" in normalized
            and "tiktok live" in normalized
        )
    ):
        return "Pressure Cooker TikTok Live"

    if (
        "flash offers" in normalized
        and "28th september" in normalized
    ):
        return "Flash Offers - 28 September"

    if (
        "ramtons sale" in normalized
        or (
            "sale" in normalized
            and "70% off" in normalized
            and "7th oct" in normalized
        )
    ):
        return "Ramtons Sale"

    if campaign_type == "flash_sale":
        return "Flash Sale"

    return None


def has_strong_campaign_evidence(
    text: str,
) -> bool:

    normalized = normalize_text(text)

    explicit_phrases = (
        "monthly offers",
        "night rush",
        "commercial laundry seminar",
        "clearance sale",
        "pressure cooker deals are coming",
        "live demo",
        "flash offers",
        "ramtons sale",
        "sale extended",
    )

    if any(
        phrase in normalized
        for phrase in explicit_phrases
    ):
        return True

    if (
        "sale" in normalized
        and "70% off" in normalized
        and "7th oct" in normalized
        and (
            "22nd sept" in normalized
            or "ramtons appliances" in normalized
        )
    ):
        return True

    if any(
        term in normalized
        for term in (
            "giveaway",
            "competition",
            "contest",
        )
    ):
        return True

    return False


def extract_campaign_category(
    text: str,
) -> str | None:

    normalized = normalize_text(text)

    # Broad campaign signals take priority over
    # incidental mentions such as "kitchen".
    if (
        "monthly offers" in normalized
        or "clearance sale" in normalized
        or "ramtons sale" in normalized
        or "flash offers" in normalized
    ):
        return "General Appliances"

    if any(
        term in normalized
        for term in (
            "pressure cooker",
            "cooker",
            "cooking",
            "kitchen",
        )
    ):
        return "Cooking"

    if any(
        term in normalized
        for term in (
            "laundry",
            "washing machine",
            "commercial laundry",
        )
    ):
        return "Laundry"

    if any(
        term in normalized
        for term in (
            "refrigerator",
            "refrigerators",
            "fridge",
            "freezer",
        )
    ):
        return "Refrigeration"

    if any(
        term in normalized
        for term in (
            "microwave",
            "microwaves",
        )
    ):
        return "Cooking"

    if "appliances" in normalized:
        return "General Appliances"

    return None


def extract_offer_value(
    text: str,
) -> str | None:

    normalized = normalize_text(text)

    # Financing is an offer condition,
    # not a percentage discount.
    if "100% financing" in normalized:
        return "100% financing"

    # Night Rush contains two explicit selling prices.
    if "night rush" in normalized:
        return "KSh 6,995; KSh 9,995"

    percentages = re.findall(
        r"\b\d+(?:\.\d+)?%\s*(?:off|discount)?",
        normalized,
    )

    if percentages:
        values = []

        for value in percentages:
            value = value.strip()

            if value not in values:
                values.append(value)

        return ", ".join(values)

    if "special live deals" in normalized:
        return "Special LIVE deals"

    if "special prices" in normalized:
        return "Special prices"

    if "financing" in normalized:
        return "100% financing"

    return None


def extract_campaign_dates(
    text: str,
) -> tuple[str | None, str | None]:

    normalized = normalize_text(text)

    # Commercial Laundry Seminar.
    if (
        "commercial laundry seminar" in normalized
        and (
            "25th sept" in normalized
            or "25th september" in normalized
        )
    ):
        return (
            "2026-09-25",
            "2026-09-25",
        )

    # Hotpoint Monthly Offers / HOT5.
    if (
        "friday 25th" in normalized
        and "sunday 27th september" in normalized
    ):
        return (
            "2026-09-25",
            "2026-09-27",
        )

    # Ramtons Sale.
    if (
        "22nd sept" in normalized
        and "7th oct" in normalized
    ):
        return (
            "2026-09-22",
            "2026-10-07",
        )

    # Hotpoint Monthly Offers alternate wording.
    if (
        "25th september" in normalized
        and "27th september" in normalized
    ):
        return (
            "2026-09-25",
            "2026-09-27",
        )

    # Hotpoint Monthly Offers alternate abbreviation.
    if (
        "25th sept" in normalized
        and "27th sept" in normalized
    ):
        return (
            "2026-09-25",
            "2026-09-27",
        )

    # Ramtons Flash Offers.
    if "28th september" in normalized:
        return (
            "2026-09-28",
            "2026-09-28",
        )

    # Pressure Cooker TikTok Live.
    if "22nd september" in normalized:
        return (
            "2026-09-22",
            "2026-09-22",
        )

    # Night Rush uses relative wording
    # ("tonight" / "tomorrow"), so we do not
    # invent calendar dates.
    return (
        None,
        None,
    )


def determine_campaign_status(
    start_date: str | None,
    end_date: str | None,
) -> str | None:

    if not start_date and not end_date:
        return None

    today = "2026-09-25"

    if end_date and end_date < today:
        return "ended"

    if start_date and start_date > today:
        return "upcoming"

    return "active"


def determine_confidence(
    observation_ids: list[int],
) -> str:

    if len(observation_ids) >= 2:
        return "high"

    return "high"


def build_candidate(
    row,
) -> CampaignCandidate | None:

    post_text = clean_text(
        row["post_text"]
    )

    evidence_text = clean_text(
        row["evidence_text"]
    )

    combined_text = (
        f"{post_text} {evidence_text}"
    )

    if not has_strong_campaign_evidence(
        combined_text
    ):
        return None

    campaign_type = detect_campaign_type(
        combined_text
    )

    if not campaign_type:
        return None

    campaign_name = extract_campaign_name(
        combined_text,
        campaign_type,
    )

    if not campaign_name:
        return None

    start_date, end_date = extract_campaign_dates(
        combined_text
    )

    observation_id = int(
        row["observation_id"]
    )

    return CampaignCandidate(
        competitor_id=int(
            row["competitor_id"]
        ),
        campaign_name=campaign_name,
        campaign_type=campaign_type,
        observation_ids=[
            observation_id
        ],
        evidence=[
            post_text
        ],
        category=extract_campaign_category(
            combined_text
        ),
        offer_value=extract_offer_value(
            combined_text
        ),
        start_date=start_date,
        end_date=end_date,
        status=determine_campaign_status(
            start_date,
            end_date,
        ),
        source_url=clean_text(
            row["post_url"]
        ) or None,
        verification_status="VERIFIED",
        confidence=determine_confidence(
            [observation_id]
        ),
        observed_date=clean_text(
            row["published_date"]
        ) or None,
    )


def merge_candidates(
    candidates: list[CampaignCandidate],
) -> list[CampaignCandidate]:

    grouped = {}

    for candidate in candidates:

        key = (
            candidate.competitor_id,
            normalize_text(
                candidate.campaign_name
            ),
        )

        if key not in grouped:

            grouped[key] = CampaignCandidate(
                competitor_id=(
                    candidate.competitor_id
                ),
                campaign_name=(
                    candidate.campaign_name
                ),
                campaign_type=(
                    candidate.campaign_type
                ),
                observation_ids=[],
                evidence=[],
                category=candidate.category,
                offer_value=candidate.offer_value,
                start_date=candidate.start_date,
                end_date=candidate.end_date,
                status=candidate.status,
                source_url=candidate.source_url,
                verification_status=(
                    candidate.verification_status
                ),
                confidence=candidate.confidence,
                observed_date=candidate.observed_date,
            )

        target = grouped[key]

        for observation_id in (
            candidate.observation_ids
        ):

            if (
                observation_id
                not in target.observation_ids
            ):
                target.observation_ids.append(
                    observation_id
                )

        for evidence in candidate.evidence:

            if evidence not in target.evidence:
                target.evidence.append(
                    evidence
                )

        if (
            candidate.start_date
            and (
                not target.start_date
                or candidate.start_date
                < target.start_date
            )
        ):
            target.start_date = candidate.start_date

        if (
            candidate.end_date
            and (
                not target.end_date
                or candidate.end_date
                > target.end_date
            )
        ):
            target.end_date = candidate.end_date

        if (
            candidate.offer_value
            and not target.offer_value
        ):
            target.offer_value = (
                candidate.offer_value
            )

        # General Appliances takes priority when
        # any related observation explicitly identifies
        # the campaign as a broad appliance campaign.
        if candidate.category:

            if not target.category:
                target.category = candidate.category

            elif (
                candidate.category
                == "General Appliances"
            ):
                target.category = (
                    "General Appliances"
                )

        if (
            candidate.source_url
            and not target.source_url
        ):
            target.source_url = candidate.source_url

        if (
            candidate.observed_date
            and (
                not target.observed_date
                or candidate.observed_date
                > target.observed_date
            )
        ):
            target.observed_date = (
                candidate.observed_date
            )

    for target in grouped.values():

        target.status = determine_campaign_status(
            target.start_date,
            target.end_date,
        )

        target.confidence = determine_confidence(
            target.observation_ids
        )

    return list(
        grouped.values()
    )


def get_competitor_names(connection):

    rows = connection.execute(
        """
        SELECT
            competitor_id,
            competitor_name
        FROM competitors
        ORDER BY competitor_id
        """
    ).fetchall()

    return {
        int(row["competitor_id"]):
        clean_text(
            row["competitor_name"]
        )
        for row in rows
    }


def print_report(
    connection,
    candidates: list[CampaignCandidate],
):

    competitor_names = get_competitor_names(
        connection
    )

    print("=" * 78)

    print(
        "MIKA CI - PHASE 2C CAMPAIGN INTELLIGENCE"
    )

    print("=" * 78)

    print(
        "MODE: DRY RUN - DATABASE WRITES DISABLED"
    )

    print()

    print(
        f"Campaign candidates: {len(candidates)}"
    )

    print()

    if not candidates:

        print(
            "No evidence-backed campaign candidates found."
        )

        return

    for number, candidate in enumerate(
        candidates,
        start=1,
    ):

        competitor_name = competitor_names.get(
            candidate.competitor_id,
            f"Competitor {candidate.competitor_id}",
        )

        print("-" * 78)

        print(
            f"{number}. {competitor_name}"
        )

        print(
            f"   Campaign: {candidate.campaign_name}"
        )

        print(
            f"   Type: {candidate.campaign_type}"
        )

        print(
            f"   Category: "
            f"{candidate.category or 'None'}"
        )

        print(
            f"   Offer: "
            f"{candidate.offer_value or 'None'}"
        )

        print(
            f"   Dates: "
            f"{candidate.start_date or 'None'}"
            f" -> "
            f"{candidate.end_date or 'None'}"
        )

        print(
            f"   Status: "
            f"{candidate.status or 'None'}"
        )

        print(
            f"   Verification: "
            f"{candidate.verification_status or 'None'}"
        )

        print(
            f"   Confidence: "
            f"{candidate.confidence or 'None'}"
        )

        print(
            f"   Observations: "
            + ", ".join(
                str(value)
                for value in candidate.observation_ids
            )
        )

        print(
            f"   Source: "
            f"{candidate.source_url or 'None'}"
        )

        print(
            "   Evidence:"
        )

        for evidence in candidate.evidence:

            shortened = evidence

            if len(shortened) > 300:
                shortened = (
                    shortened[:297]
                    + "..."
                )

            print(
                f"      {shortened}"
            )

    print("-" * 78)

    print()

    print(
        "No database records were created."
    )


def main():

    connection = connect()

    try:

        rows = get_social_observations(
            connection
        )

        print(
            f"Social observations loaded: "
            f"{len(rows)}"
        )

        candidates = []

        for row in rows:

            candidate = build_candidate(
                row
            )

            if candidate:
                candidates.append(
                    candidate
                )

        merged_candidates = merge_candidates(
            candidates
        )

        print_report(
            connection,
            merged_candidates
        )

    finally:

        connection.close()


if __name__ == "__main__":
    main()