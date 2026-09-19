import argparse
import sys
from datetime import datetime, timedelta, timezone

import httpx

import cfg
import store

API_OFFSET_CEILING = 10000
# posted_at compared against local clock; margin keeps window-edge rows from false close
WINDOW_EDGE_MARGIN = timedelta(hours=1)


def query_params(params: dict) -> dict:
    return {k: ",".join(v) if isinstance(v, list) else v for k, v in params.items()}


def fetch_pass(client: httpx.Client, base: str, params: dict, page_limit: int) -> list[dict]:
    rows, offset = [], 0
    while True:
        limit = min(page_limit, API_OFFSET_CEILING - offset)
        resp = client.get(f"{base}/jobs/search", params={**query_params(params), "limit": limit, "offset": offset})
        resp.raise_for_status()
        body = resp.json()
        rows += body["data"]
        offset += limit
        total = body["meta"]["total"]
        if total > API_OFFSET_CEILING:
            print(f"warning: total {total} exceeds API offset ceiling, truncated", file=sys.stderr)
        if not body["data"] or offset >= min(total, API_OFFSET_CEILING):
            return rows


def normalize(raw: dict, tier: str) -> dict:
    e = raw.get("enrichment") or {}
    currency = e.get("salary_currency")
    return {
        "public_slug": raw["public_slug"],
        "tier": tier,
        "title": raw["title"].strip(),
        "company": (raw.get("company") or "").strip(),
        "company_slug": raw.get("company_slug"),
        "url": raw["url"],
        "source": raw.get("source"),
        "location": raw.get("location"),
        "cities": raw.get("cities") or [],
        "countries": raw.get("countries") or [],
        "regions": raw.get("regions") or [],
        "work_mode": raw.get("work_mode"),
        "skills": raw.get("skills") or [],
        "collections": raw.get("collections") or [],
        "employment_type": e.get("employment_type"),
        "seniority": e.get("seniority"),
        "category": e.get("category"),
        "salary_min": e.get("salary_min"),
        "salary_max": e.get("salary_max"),
        "salary_currency": currency.upper() if currency else None,
        "salary_period": e.get("salary_period"),
        "posted_at": raw.get("posted_at"),
        "created_at": raw.get("created_at"),
        "last_seen_at": raw.get("last_seen_at"),
        "closed_at": raw.get("closed_at"),
        "description": raw.get("description"),
        "enrichment": e,
        "reality": raw.get("reality") or {},
    }


def posted_since(params: dict, now: datetime) -> str | None:
    days = params.get("posted_within_days")
    if days is None:
        return None
    return (now - timedelta(days=days) + WINDOW_EDGE_MARGIN).strftime(store.ISO)


def run(config: dict, conn, client: httpx.Client) -> dict[str, dict]:
    now_dt = datetime.now(timezone.utc)
    now = now_dt.strftime(store.ISO)
    api = config["api"]
    summary = {}
    for p in config["passes"]:
        rows = [normalize(r, p["tier"]) for r in fetch_pass(client, api["base"], p["params"], api["page_limit"])]
        with conn:
            store.upsert(conn, rows, now)
            closed = store.close_missing(
                conn, p["tier"], {r["public_slug"] for r in rows}, posted_since(p["params"], now_dt), now
            )
        summary[p["tier"]] = {"fetched": len(rows), "closed": closed}
    return summary


def main() -> None:
    ap = argparse.ArgumentParser(description="Poll freehire API into SQLite")
    ap.add_argument("--db", help="override config db path")
    args = ap.parse_args()
    config = cfg.load()
    conn = store.connect(args.db or cfg.db_path(config))
    with httpx.Client(timeout=config["api"]["timeout_s"]) as client:
        summary = run(config, conn, client)
    for tier, s in summary.items():
        print(f"{tier}: fetched {s['fetched']}, closed {s['closed']}")


if __name__ == "__main__":
    main()
