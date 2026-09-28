import sqlite3

from phase3_question_router import route_question
from phase3_evidence_retrieval import connect, get_competitor_master


def main():
    conn = connect()

    try:
        competitor_master = get_competitor_master(conn)

        print("=" * 80)
        print("COMPETITOR MASTER")
        print("=" * 80)

        for row in competitor_master:
            print(dict(row))

        test_questions = [
            "Show me Hotpoint social activity.",
            "Compare Hotpoint and Ramtons.",
            "What has Ramtons been doing recently?",
            "What is happening with JTC?",
        ]

        for question in test_questions:
            route = route_question(question)

            print("\n" + "=" * 80)
            print("QUESTION")
            print("=" * 80)
            print(question)

            print("\nROUTE")
            print("=" * 80)
            print("intent:", route.intent)
            print("confidence:", route.confidence)
            print("competitor:", route.competitor)
            print("brand:", route.brand)

            competitor_ids = []

            if route.competitor:
                target = route.competitor.strip().lower()

                for row in competitor_master:
                    name = str(
                        row.get("competitor_name") or ""
                    ).strip().lower()

                    if name == target:
                        competitor_ids.append(
                            row.get("competitor_id")
                        )

            elif route.brand:
                target = route.brand.strip().lower()

                for row in competitor_master:
                    brand = str(
                        row.get("brand_name")
                        or row.get("brand")
                        or ""
                    ).strip().lower()

                    if brand == target:
                        competitor_ids.append(
                            row.get("competitor_id")
                        )

            print("resolved competitor_ids:", competitor_ids)

        print("\n" + "=" * 80)
        print("READ-ONLY SCOPE DIAGNOSTIC COMPLETE")
        print("NO DATABASE ROWS WERE WRITTEN")
        print("=" * 80)

    finally:
        conn.close()


if __name__ == "__main__":
    main()