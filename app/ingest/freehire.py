import argparse
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

import httpx

import cfg
import companies
import store

API_OFFSET_CEILING = 10000
# posted_at compared against local clock; margin keeps window-edge rows from false close
WINDOW_EDGE_MARGIN = timedelta(hours=1)


def query_params(params: dict) -> dict:
    out = {k: ",".join(v) if isinstance(v, list) else v for k, v in params.items()}
    if out.get("q"):
        out["q"] = phrase(out["q"])
    return out


def phrase(words: str) -> str:
    """Title words as one exact phrase. Unquoted (2026-10-01): "nurse" also matched "Nursery ..."
    titles (35 of the first 100), "staff accountant" matched any title w/ either word (12,818,
    mostly Staff ... Engineer)."""
    words = words.strip()
    return words if len(words) > 1 and words[0] == words[-1] == '"' else f'"{words}"'


def ignored(body: dict) -> list[str]:
    """Filters the job search did not understand. It answers them with every job, never an error
    (2026-09-30: bogus_param=1 -> 798,143 US rows, meta.ignored_params [{"param": "bogus_param"}])."""
    return [p.get("param", "?") if isinstance(p, dict) else str(p)
            for p in (body.get("meta") or {}).get("ignored_params") or []]


def understood(body: dict) -> dict:
    """Stop before a misspelled filter floods the list w/ the whole catalogue."""
    if bad := ignored(body):
        total = (body.get("meta") or {}).get("total")
        raise SystemExit(f"search settings name a filter the job search doesn't know ({', '.join(bad)}) - it "
                         f"answered with every job{f' ({total:,})' if total else ''}. Nothing saved.")
    return body


def fetch_pass(client: httpx.Client, base: str, params: dict, page_limit: int) -> tuple[list[dict], bool]:
    """Rows + whether the API ceiling cut the pass short (rows past it were never seen)."""
    rows, offset = [], 0
    while True:
        limit = min(page_limit, API_OFFSET_CEILING - offset)
        resp = client.get(f"{base}/jobs/search", params={**query_params(params), "limit": limit, "offset": offset})
        resp.raise_for_status()
        body = understood(resp.json())
        rows += body["data"]
        offset += limit
        total = body["meta"]["total"]
        if total > API_OFFSET_CEILING:
            print(f"warning: total {total} exceeds API offset ceiling, truncated", file=sys.stderr)
        if not body["data"] or offset >= min(total, API_OFFSET_CEILING):
            return rows, total > API_OFFSET_CEILING


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
        # true or absent, never false: absent = no clearance wording found, not "none needed"
        "requires_clearance": True if raw.get("requires_clearance") else None,
    }


def windows(params: dict, window: dict) -> list[int]:
    """Days to try in order: pass's own or default start, then each wider step."""
    start = params.get("posted_within_days", window["days"])
    return [start] + [d for d in window["widen_to"] if d > start]


def fetch_widening(client: httpx.Client, base: str, params: dict, page_limit: int, window: dict) -> tuple[list[dict], bool, int]:
    """Narrowest window returning min_jobs rows, else the widest. Rows, truncated, days used."""
    for days in windows(params, window):
        rows, truncated = fetch_pass(client, base, {**params, "posted_within_days": days}, page_limit)
        if len(rows) >= window["min_jobs"]:
            break
    return rows, truncated, days


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
    passes = config["passes"]
    # passes fetched at once (network is the whole wait); db writes stay on this thread, in order
    with ThreadPoolExecutor(max_workers=len(passes) or 1) as pool:
        fetched = list(pool.map(
            lambda p: fetch_widening(client, api["base"], p["params"], api["page_limit"], config["window"]), passes))
    tiers = {}
    for p, (raw, truncated, days) in zip(passes, fetched):
        rows = [normalize(r, p["tier"]) for r in raw]
        with conn:
            store.upsert(conn, rows, now)
        t = tiers.setdefault(p["tier"], {"slugs": set(), "truncated": False, "days": []})
        t["slugs"] |= {r["public_slug"] for r in rows}
        t["truncated"] |= truncated
        t["days"].append(days)
    # a tier filled by several passes (an internship search: one per tag) closes only what none of
    # them returned, inside the window all of them fetched. Closed per pass, the second closed every
    # row only the first found - 40 of 214 open internships on one fresh check (2026-10-08).
    # A truncated pass never saw rows past the ceiling => absence proves nothing
    for tier, t in tiers.items():
        with conn:
            closed = 0 if t["truncated"] else store.close_missing(
                conn, tier, t["slugs"], posted_since({"posted_within_days": min(t["days"])}, now_dt), now)
        summary[tier] = {"fetched": len(t["slugs"]), "closed": closed, "truncated": t["truncated"], "days": max(t["days"])}
    return summary


def main() -> None:
    ap = argparse.ArgumentParser(description="Poll freehire API into SQLite")
    ap.add_argument("--db", help="override config db path")
    args = ap.parse_args()
    config = cfg.load()
    conn = store.connect(args.db or cfg.db_path(config))
    with httpx.Client(timeout=config["api"]["timeout_s"]) as client:
        summary = run(config, conn, client)
        companies.refresh_quietly(conn, client, config["api"]["base"])
    for tier, s in summary.items():
        print(f"{tier}: fetched {s['fetched']} ({s['days']} days), closed {s['closed']}")


if __name__ == "__main__":
    main()
