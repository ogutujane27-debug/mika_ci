"""Step 1 of collection: look at what Hotpoint's pages actually deliver to a
plain HTTP request, so we know which collection method will work.
Nothing is written to the database. Raw HTML is saved to data/raw/."""
import json
import re
import sys
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "app"))
from config import USER_AGENT, REQUEST_TIMEOUT, RAW_DIR  # noqa: E402

PAGES = {
    "offers_extra5": "https://www.hotpoint.co.ke/offers/enjoy-extra-5-off-von-and-hisense/",
    "fridges_category": "https://www.hotpoint.co.ke/catalogue/category/fridges-freezers/",
    "sample_product": "https://www.hotpoint.co.ke/catalogue/hisense-rd-27dr4sa-top-mount-freezer-205l-silver/",
}


def analyze(html: str) -> dict:
    return {
        "length": len(html),
        "ksh_mentions": len(re.findall(r"Ksh\s?[\d,]+", html, flags=re.I)),
        "has_next_data": "__NEXT_DATA__" in html,
        "json_ld_blocks": len(re.findall(r'application/ld\+json', html)),
        "product_links": len(set(re.findall(r'/catalogue/[a-z0-9\-]+/', html))),
        "api_hints": sorted(set(re.findall(r'https?://[^"\s]*(?:api|graphql|products\.json)[^"\s]*', html)))[:10],
    }


def main():
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    session = requests.Session()
    session.headers["User-Agent"] = USER_AGENT
    report = {}
    for name, url in PAGES.items():
        try:
            r = session.get(url, timeout=REQUEST_TIMEOUT)
            (RAW_DIR / f"{name}.html").write_text(r.text, encoding="utf-8")
            info = analyze(r.text)
            info["status"] = r.status_code
        except Exception as e:  # report, do not crash
            info = {"error": str(e)}
        report[name] = info
        print(f"\n== {name}\n{json.dumps(info, indent=2)}")
    (RAW_DIR / "inspect_report.json").write_text(json.dumps(report, indent=2))
    print("\nSaved raw pages and inspect_report.json in data/raw/")


if __name__ == "__main__":
    main()
