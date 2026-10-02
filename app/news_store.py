import argparse, json, sqlite3
from urllib.parse import urlsplit
from datetime import date
from pathlib import Path

PREVIEW = Path("reports/mika_news_preview/news_intelligence_preview.json")

def evidence_body(rec):
    text = rec.get("evidence_text") or ""
    marker = "Article evidence:"
    if marker in text:
        text = text.split(marker, 1)[1]
    return text.strip()

def pick_competitor(rec, brands):
    names = [str(n).strip() for n in (rec.get("entities") or []) if str(n).strip()]
    headline = (rec.get("headline") or "").lower()
    for n in names:
        if n.lower() in brands and n.lower() in headline:
            return brands[n.lower()]
    for n in names:
        if n.lower() in brands:
            return brands[n.lower()]
    return None

def norm_url(u):
    s = urlsplit((u or "").strip())
    host = s.netloc.lower()
    if host.startswith("www."):
        host = host[4:]
    return host + s.path.rstrip("/")

def already_stored(con, nid, url):
    hit = con.execute(
        "SELECT 1 FROM findings WHERE finding_id=? UNION SELECT 1 FROM market_news WHERE news_id=?",
        (nid, nid)).fetchone()
    if hit:
        return True
    target = norm_url(url)
    if not target:
        return False
    rows = con.execute(
        "SELECT source_url FROM findings WHERE finding_type='news' "
        "UNION SELECT source_url FROM market_news").fetchall()
    return any(norm_url(r[0]) == target for r in rows)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default="data/mika_competitive_intel.db")
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--skip-ids", default="")
    a = ap.parse_args()
    skip_ids = {s.strip() for s in a.skip_ids.split(",") if s.strip()}

    records = json.loads(PREVIEW.read_text(encoding="utf-8"))
    con = sqlite3.connect(a.db)
    con.execute("PRAGMA foreign_keys = ON")
    brands = {r[1].lower(): (r[0], r[1]) for r in
              con.execute("SELECT competitor_id, brand_name FROM competitors")}

    n_find = n_market = n_dupe = n_skip = 0
    for rec in records:
        nid = rec["news_id"]
        if nid in skip_ids:
            print(f"HELD BACK {nid} | {(rec.get('headline') or '')[:55]}")
            n_skip += 1
            continue
        url = rec.get("source_url")
        scope = rec.get("scope_status")
        head = (rec.get("headline") or "")[:55]
        comp = pick_competitor(rec, brands)
        if scope != "IN_SCOPE":
            print(f"SKIP {nid} scope={scope} | {head}")
            n_skip += 1
            continue
        if already_stored(con, nid, url):
            print(f"DUPLICATE {nid} | {head}")
            n_dupe += 1
            continue
        y, w, _ = date.fromisoformat(rec["observed_date"]).isocalendar()
        week = f"{y}-W{w:02d}"
        body = evidence_body(rec) or rec.get("headline") or ""
        conf = (rec.get("confidence") or "").lower()
        conf = conf if conf in ("high", "medium", "low") else None
        news_type = rec.get("news_type") or "INDUSTRY_NEWS"
        label = "WRITE" if a.write else "WOULD WRITE"
        if comp:
            print(f"{label} {nid} -> findings, competitor {comp[0]} ({comp[1]}) | {news_type} | {conf} | {head}")
            if a.write:
                con.execute(
                    "INSERT INTO findings (finding_id, scan_week, competitor_id, brand, category, finding_type, "
                    "summary, source_url, source_type, published_date, observed_date, evidence_text, "
                    "verification_status, confidence) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (nid, week, comp[0], comp[1], rec.get("category") or "Home Appliances & Electronics",
                     "news", body, url, "news media", rec.get("published_date"), rec["observed_date"],
                     body, "VERIFIED", conf))
                con.execute("INSERT INTO news_observations (finding_id, headline, news_type) VALUES (?,?,?)",
                            (nid, rec["headline"], news_type))
            n_find += 1
        else:
            print(f"{label} {nid} -> market_news | {scope} | {news_type} | {conf} | {head}")
            if a.write:
                con.execute(
                    "INSERT INTO market_news (news_id, scan_week, news_category, headline, summary, "
                    "evidence_text, publisher, source_url, published_date, observed_date, scope_status, "
                    "scope_reason, verification_status, confidence) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (nid, week, news_type, rec["headline"], body, body, rec.get("publisher"), url,
                     rec.get("published_date"), rec["observed_date"], scope, rec.get("scope_reason"),
                     "VERIFIED", conf))
            n_market += 1
    if a.write:
        con.commit()
    print(f"\nmode={'WRITE' if a.write else 'DRY RUN'} findings={n_find} market_news={n_market} "
          f"duplicates={n_dupe} skipped={n_skip}")
    con.close()

main()
