import argparse
import re
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from urllib.parse import quote

import httpx

import cfg
import companies
import paytext
import store

API_OFFSET_CEILING = 10000
# same filters + rows as /jobs/search, description whole (5,855 chars vs 986 per row, 2026-10-09; same
# speed): the pay range + "About us" sit at the end, past the ~1,000 chars /jobs/search keeps - pay in
# the first 1,000 on 71 of 1,000 HR-titled rows, in the whole text on 279 (paytext)
SEARCH = "/agent/jobs/search"
# posted_at compared against local clock; margin keeps window-edge rows from false close
WINDOW_EDGE_MARGIN = timedelta(hours=1)
# Listed jobs this check didn't return, asked about one by one (recheck): close_missing only sees
# rows posted inside the fetch window, so a job filled after it aged out stayed on the list looking
# open until rank.stale_days. 2026-10-27, real list: 83 of 219 open rows outside the window marked
# closed or gone by the job search; 8 of the first 70 shown, their links 404 or "position closed".
# Asked again every RECHECK_DAYS. The job search allows 600 asks a minute, search + company records
# included (x-ratelimit-reset 50 s; 81 of 300 detail asks at 8 at once answered 429, 2026-10-27):
# RECHECK_BATCH leaves room for the rest, a 429 leaves what's left for the next check
RECHECK_DAYS = 2
RECHECK_BATCH = 400
RECHECK_WORKERS = 8


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
        resp = client.get(f"{base}{SEARCH}", params={**query_params(params), "limit": limit, "offset": offset})
        resp.raise_for_status()
        body = understood(resp.json())
        rows += body["data"]
        offset += limit
        total = body["meta"]["total"]
        if total > API_OFFSET_CEILING:
            print(f"warning: total {total} exceeds API offset ceiling, truncated", file=sys.stderr)
        if not body["data"] or offset >= min(total, API_OFFSET_CEILING):
            return rows, total > API_OFFSET_CEILING


def pay(raw: dict) -> dict:
    """Pay fields: the range the posting states in its own words (paytext), else the job search's
    own field. The words win when both are there: of 38 HR-titled rows where they differed
    (2026-10-09), the field was a stale or other band on every one read by hand ($22k-32k on a
    posting saying $80,000-$82,000)."""
    e = raw.get("enrichment") or {}
    if said := paytext.stated(raw.get("description")):
        return {"salary_min": said[0], "salary_max": said[1], "salary_currency": "USD", "salary_period": said[2]}
    currency = e.get("salary_currency")
    return {"salary_min": e.get("salary_min"), "salary_max": e.get("salary_max"),
            "salary_currency": currency.upper() if currency else None, "salary_period": e.get("salary_period")}


# pay or hours said in a title ("Server Assistant - $20.25/hr", "$24.65*/HR - Shift Manager", "36 hrs./wk."):
# the job search matches its "hr" to a title search for HR - 184 of the 1,000 newest US "HR" titles,
# 2026-10-09 ("Payroll/HR Specialist" keeps its HR: no number before it)
# ("2027 HR Intern" keeps it: a year is no rate or shift length)
HOURS_IN_TITLE = re.compile(r"(?:\$\s?\d[\d.,]*|\b\d{1,3}(?:\.\d+)?)\s*[*+]?\s*(?:/|per|an?)?\s*(?:hrs?|hours?)\b\.?", re.I)


# a job board's tag on the end of the title, not the employer's words: "Software Developer III with Security
# Clearance" (adzuna). 814 of the 5,347 US titles a "security" search found in 30 days, 2026-10-09 - 734 of
# them not security work - and 379 of the 745 a "security engineer" search added; the job search's own
# clearance flag was on 279 of the 814
CLEARANCE_TAG = re.compile(r"\s*[-–,]?\s*with (?:a |an )?(?:active )?security clearance\s*$", re.I)


def pay_word_only(title: str, params: dict) -> bool:
    """A title search's word found in this title only as a pay or hours unit, or in a job board's
    "with Security Clearance" tag - not the job searched for."""
    q = (params.get("q") or "").strip('" ').lower().split()
    found = lambda text, w: re.search(rf"(?<!\w){re.escape(w)}", text, re.I)
    stripped = CLEARANCE_TAG.sub(" ", HOURS_IN_TITLE.sub(" ", title))
    return any(found(title, w) and not found(stripped, w) for w in q)


def normalize(raw: dict, tier: str) -> dict:
    e = raw.get("enrichment") or {}
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
        **pay(raw),
        "posted_at": raw.get("posted_at"),
        "created_at": raw.get("created_at"),
        "last_seen_at": raw.get("last_seen_at"),
        "closed_at": raw.get("closed_at"),
        "description": raw.get("description"),
        "enrichment": e,
        "reality": raw.get("reality") or {},
        # true or absent, never false: absent = no clearance wording found, not "none needed"
        # ... or the board's own title tag says one is needed (535 of 814 tagged rows lacked the flag)
        "requires_clearance": True if raw.get("requires_clearance") or CLEARANCE_TAG.search(raw["title"]) else None,
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
        rows = [normalize(r, p["tier"]) for r in raw if not pay_word_only(r["title"], p["params"])]
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


def recheck_due(conn, since: str, now: datetime, limit: int = RECHECK_BATCH) -> list[str]:
    """Open rows no fetch since `since` returned, not asked in RECHECK_DAYS: never asked first,
    most recently seen of them first (still near the top of the list), then longest since asked."""
    asked = (now - timedelta(days=RECHECK_DAYS)).strftime(store.ISO)
    return [r[0] for r in conn.execute(
        "SELECT public_slug FROM jobs WHERE closed_at IS NULL AND fetched_at < ?"
        " AND (checked_at IS NULL OR checked_at < ?)"
        " ORDER BY COALESCE(checked_at, ''), fetched_at DESC LIMIT ?", (since, asked, limit))]


def listed_open(client: httpx.Client, base: str, slug: str, limited: threading.Event) -> bool | None:
    """The job search's word on one listed job, by its listing id - nothing about the user, never
    the employer's page (as status.ask_job_search). False = marked closed, or gone (404); True =
    open; None = no answer, asked again next check."""
    if limited.is_set():
        return None
    try:
        resp = client.get(f"{base}/jobs/{quote(slug, safe='')}")
        if resp.status_code == 429:
            limited.set()
            return None
        if resp.status_code == 404:
            return False
        resp.raise_for_status()
        data = resp.json().get("data")
    except (httpx.HTTPError, ValueError, AttributeError):
        return None
    return not data.get("closed_at") if isinstance(data, dict) else None


def recheck(conn, client: httpx.Client, base: str, since: str, now: datetime | None = None) -> tuple[int, int]:
    """Closes listed jobs the job search says are closed or gone. (asked, closed)."""
    now = now or datetime.now(timezone.utc)
    stamp = now.strftime(store.ISO)
    slugs, limited = recheck_due(conn, since, now), threading.Event()
    with ThreadPoolExecutor(RECHECK_WORKERS) as pool:
        answers = list(pool.map(lambda slug: listed_open(client, base, slug, limited), slugs))
    asked = [(stamp, s) for s, ok in zip(slugs, answers) if ok is not None]
    gone = [(stamp, s) for s, ok in zip(slugs, answers) if ok is False]
    with conn:
        conn.executemany("UPDATE jobs SET checked_at = ? WHERE public_slug = ?", asked)
        conn.executemany("UPDATE jobs SET closed_at = ? WHERE public_slug = ? AND closed_at IS NULL", gone)
    return len(asked), len(gone)


def recheck_quietly(conn, client: httpx.Client, base: str, since: str) -> None:
    """At the job check: jobs were found either way, so a failure here is logged, never raised.
    Then drops jobs closed DROP_CLOSED_DAYS ago the user never acted on (store.drop_closed)."""
    try:
        asked, closed = recheck(conn, client, base, since)
        before = (datetime.now(timezone.utc) - timedelta(days=store.DROP_CLOSED_DAYS)).strftime(store.ISO)
        with conn:
            removed = store.drop_closed(conn, before)
        if asked or removed:
            print(f"older jobs: {asked} asked, {closed} closed, {removed} long closed removed")
    except Exception as exc:  # noqa: BLE001 - never stops the job check
        print(f"older jobs: skipped ({exc})", file=sys.stderr)


def main() -> None:
    ap = argparse.ArgumentParser(description="Poll freehire API into SQLite")
    ap.add_argument("--db", help="override config db path")
    args = ap.parse_args()
    config = cfg.load()
    conn = store.connect(args.db or cfg.db_path(config))
    with httpx.Client(timeout=config["api"]["timeout_s"]) as client:
        started = store.utc_now()
        summary = run(config, conn, client)
        recheck_quietly(conn, client, config["api"]["base"], started)
        companies.refresh_quietly(conn, client, config["api"]["base"])
    for tier, s in summary.items():
        print(f"{tier}: fetched {s['fetched']} ({s['days']} days), closed {s['closed']}")


if __name__ == "__main__":
    main()
