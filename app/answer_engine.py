"""
MIKA CI - Ask MIKA Answer Engine
"""

from __future__ import annotations

import sys
from pathlib import Path
from dataclasses import asdict
from typing import Any

APP_DIR = Path(__file__).resolve().parent

if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from phase3_answer_composer import compose_answer
from research_gateway import research


def get_internal_answer(question: str) -> dict[str, Any]:
    try:
        result = compose_answer(question)

        if hasattr(result, "__dataclass_fields__"):
            return asdict(result)

        return {
            "question": question,
            "intent": "INTERNAL",
            "confidence": "LOW",
            "answer": str(result),
            "evidence": [],
            "limitations": [],
        }

    except Exception as exc:
        return {
            "question": question,
            "intent": "INTERNAL_ERROR",
            "confidence": "LOW",
            "answer": "",
            "evidence": [],
            "limitations": [
                f"Internal MIKA CI evidence unavailable: {exc}"
            ],
        }


def needs_external_research(
    question: str,
    internal: dict[str, Any],
) -> bool:
    """
    Decide whether external web research is actually required.

    Internal MIKA CI evidence is the default source for known CI intents.
    External research is used when:
      1. the user explicitly asks for web/external research, or
      2. the internal answer is unavailable/unsupported/too weak.

    Ordinary words such as "recent", "latest", "market", "brand",
    or "company" do NOT automatically trigger external research.
    """

    text = question.lower().strip()

    # Explicit external/web research requests.
    explicit_external_signals = (
        "search the web",
        "search online",
        "search the internet",
        "look online",
        "look it up online",
        "check online",
        "check the web",
        "check the internet",
        "web research",
        "external research",
        "online research",
        "what is online",
        "according to the web",
        "according to online sources",
    )

    if any(signal in text for signal in explicit_external_signals):
        return True

    intent = str(
        internal.get("intent", "")
    ).upper().strip()

    confidence = str(
        internal.get("confidence", "")
    ).upper().strip()

    answer = str(
        internal.get("answer") or ""
    ).strip()

    evidence = internal.get("evidence") or []

    # If the internal engine failed or cannot route the question,
    # external research is an appropriate fallback.
    if intent in {
        "",
        "UNKNOWN",
        "UNSUPPORTED",
        "GENERAL",
        "INTERNAL_ERROR",
    }:
        return True

    if not answer:
        return True

    # A known intent with actual evidence should remain internal,
    # even when the question contains words such as "recent",
    # "latest", "market", "brand", etc.
    if evidence:
        return False

    # Medium-confidence answers without evidence may benefit from
    # external verification.
    if confidence in {"LOW", "MEDIUM"}:
        return True

    # High-confidence answer with no evidence is still usable internally.
    return False



def format_external_evidence(
    results: list[dict],
) -> list[dict]:

    return [
        {
            "title": result.get("title", ""),
            "url": result.get("url", ""),
            "source_domain": result.get("source_domain", ""),
            "source_type": result.get("source_type", ""),
            "platform": result.get("platform", ""),
            "relationship": result.get("relationship", ""),
            "kenya_relevance": result.get("kenya_relevance", ""),
            "evidence_quality": result.get("evidence_quality", ""),
            "confidence": result.get("confidence", ""),
            "published_date": result.get("published_date"),
            "evidence_type": result.get("evidence_type", ""),
            "evidence": result.get("evidence", ""),
            "visual_evidence": result.get("visual_evidence", ""),
            "visual_evidence_url": result.get(
                "visual_evidence_url",
                "",
            ),
            "query_lane": result.get("query_lane", ""),
        }
        for result in results
    ]


def build_answer(
    internal: dict[str, Any],
    external: list[dict],
) -> str:

    parts = []

    internal_text = str(
        internal.get("answer") or ""
    ).strip()

    if internal_text:
        parts.append(
            "MIKA CI EVIDENCE\n"
            + internal_text
        )

    if external:
        evidence_lines = []

        for result in external[:8]:
            title = str(
                result.get("title") or "Untitled source"
            ).strip()

            domain = str(
                result.get("source_domain")
                or "unknown source"
            ).strip()

            evidence = str(
                result.get("evidence") or ""
            ).strip()

            published_date = result.get(
                "published_date"
            )

            kenya_relevance = str(
                result.get("kenya_relevance") or ""
            ).strip()

            confidence = str(
                result.get("confidence") or ""
            ).strip()

            if evidence:
                line = f"- {evidence}"
            else:
                line = f"- {title}"

            metadata = [domain]

            if published_date:
                metadata.append(
                    f"date: {published_date}"
                )

            if kenya_relevance:
                metadata.append(
                    f"Kenya relevance: {kenya_relevance}"
                )

            if confidence:
                metadata.append(
                    f"confidence: {confidence}"
                )

            line += " [" + "; ".join(metadata) + "]"

            evidence_lines.append(line)

        external_text = [
            "External research retrieved "
            f"{len(external)} source(s).",
            "",
            "What the retrieved evidence indicates:",
            *evidence_lines,
            "",
            "Sources:"
        ]

        for result in external[:8]:
            title = str(
                result.get("title")
                or "Untitled source"
            ).strip()

            url = str(
                result.get("url") or ""
            ).strip()

            if url:
                external_text.append(
                    f"- {title}: {url}"
                )
            else:
                external_text.append(
                    f"- {title}"
                )

        parts.append(
            "EXTERNAL RESEARCH\n"
            + "\n".join(external_text)
        )

    if not parts:
        return (
            "I could not retrieve sufficient evidence "
            "to answer this question reliably."
        )

    return "\n\n".join(parts)


def answer_question(
    question: str,
    external_limit: int = 10,
    fetch_pages: bool = True,
) -> dict[str, Any]:

    question = str(question or "").strip()

    if not question:
        return {
            "question": "",
            "answer": "Please enter a question.",
            "intent": "EMPTY",
            "confidence": "LOW",
            "mode": "NONE",
            "internal": {},
            "external": [],
            "limitations": ["No question was supplied."],
        }

    internal = get_internal_answer(question)

    use_external = needs_external_research(
        question,
        internal,
    )

    external_raw = []

    if use_external:
        try:
            external_raw = research(
                question,
                limit=external_limit,
                fetch_pages=fetch_pages,
            )
        except Exception as exc:
            internal.setdefault(
                "limitations",
                [],
            ).append(
                f"External research unavailable: {exc}"
            )

    external = format_external_evidence(
        external_raw
    )

    if use_external and external:
        mode = (
            "INTERNAL + EXTERNAL"
            if internal.get("answer")
            else "EXTERNAL"
        )
    else:
        mode = "INTERNAL"

    limitations = list(
        internal.get("limitations") or []
    )

    if use_external and not external:
        limitations.append(
            "External research returned no usable sources."
        )

    return {
        "question": question,
        "answer": build_answer(
            internal,
            external,
        ),
        "intent": internal.get(
            "intent",
            "UNKNOWN",
        ),
        "confidence": internal.get(
            "confidence",
            "LOW",
        ),
        "mode": mode,
        "internal": internal,
        "external": external,
        "limitations": limitations,
    }

