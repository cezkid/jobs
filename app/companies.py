"""Company links on the Today page: each company's own website, from the job search's company
record (`GET /companies/<its listing id>` -> `data.company.company_info.website`); none on record
=> plain name, no link (owner 2026-10-03: no web-search fallback). Asked once per company at the job check, cached 30 days, never at click time
(app/docs/jobs/freehire.md#companies). No about-us page in the data: main website only, never a
guessed path, never a link built from the slug. The same record says whether it is a nonprofit or a
staffing firm (rank.posting_says, rank.staffing).
"""
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from urllib.parse import quote, urlsplit

import httpx

import store

MAX_AGE_DAYS = 30
# this many per check, the rest wait for the next one: a first check's whole list in one go (595
# employers of 1,000 project / program manager rows, 2026-10-13: 13.7 s at WORKERS, 0 failures;
# the job search allows 600 a second) - a staffing firm unasked is a staffing firm unmarked
BATCH = 1000
WORKERS = 8


def website(value) -> str | None:
    """A link the browser may open: http(s), a host, no space, quote or angle bracket. Else None."""
    if not isinstance(value, str):
        return None
    url = value.strip()
    if not url or len(url) > 500 or any(ch in url for ch in " \t\r\n\"'<>\\`"):
        return None
    try:
        parts = urlsplit(url)
    except ValueError:
        return None
    return url if parts.scheme in ("http", "https") and parts.hostname else None


def due(conn, now: datetime, limit: int = BATCH) -> list[str]:
    """Companies on the open list w/ no answer yet, or one older than MAX_AGE_DAYS."""
    old = (now - timedelta(days=MAX_AGE_DAYS)).strftime(store.ISO)
    return [r[0] for r in conn.execute(
        "SELECT DISTINCT j.company_slug FROM jobs j LEFT JOIN companies c ON c.slug = j.company_slug"
        " WHERE j.closed_at IS NULL AND j.company_slug IS NOT NULL AND j.company_slug != ''"
        " AND (c.fetched_at IS NULL OR c.fetched_at < ? OR c.nonprofit IS NULL OR c.staffing IS NULL)"
        " ORDER BY j.company_slug LIMIT ?",
        (old, limit))]


def nonprofit(company: dict) -> bool:
    """The record calls the employer a nonprofit: organization_type "Non-Profit" or industry
    "nonprofit". 2026-10-09, 250 random employers of US HR-titled jobs: 20 so (the posting's own
    words said it on 6); set on about half of records, so "no" here says little."""
    industries = company.get("industries")
    return company.get("organization_type") == "Non-Profit" or (isinstance(industries, list) and "nonprofit" in industries)


# industries a staffing firm's record names: its own trade, or its clients' (IT staffing reads
# it-services). Any other (healthcare, defense, logistics) = an employer that also staffs out
STAFFING_INDUSTRIES = {"recruitment", "staffing", "hr-tech", "it-services", "technology-consulting", "software-development",
                       "enterprise-software", "data-analytics", "ai", "financial-services"}


def staffing(company: dict) -> bool:
    """The record calls it a staffing firm: `outstaff` among company_types (a union over its postings'
    tags), not a government contractor, no industry outside staffing's own. 2026-10-13, every employer
    of 1,000 project / program manager rows + 502 Adzuna ones: outstaff on 37 + 132; the government
    type took out Peraton, CACI, Clarity Innovations, Jooble, Openkyber, the industry rule Tekni-Plex
    (packaging), ATALNT, SIERTEK. Left: 165, read by hand all staffing or IT contracting firms but
    DCS Corporation (defense engineering), Capgemini Engineering, 3cloud (consultancies)."""
    types, industries = company.get("company_types"), company.get("industries")
    types = set(types) if isinstance(types, list) else set()
    industries = set(industries) if isinstance(industries, list) else set()
    return "outstaff" in types and "government" not in types and not industries - STAFFING_INDUSTRIES


def ask(client: httpx.Client, base: str, slug: str) -> tuple[bool, str | None, bool, bool]:
    """(answered, website, nonprofit, staffing). 404 = no record => answered, none. Any other
    failure => not answered: try again next check."""
    try:
        resp = client.get(f"{base}/companies/{quote(slug, safe='')}")
        if resp.status_code == 404:
            return True, None, False, False
        resp.raise_for_status()
        company = ((resp.json() or {}).get("data") or {}).get("company") or {}
        info = company.get("company_info") or {}
        np, staff = nonprofit(company), staffing(company)
    except (httpx.HTTPError, ValueError, AttributeError):
        return False, None, False, False
    return True, website(info.get("website") if isinstance(info, dict) else None), np, staff


def refresh(conn, client: httpx.Client, base: str, now: datetime | None = None, limit: int = BATCH) -> int:
    """Asks for each due company, WORKERS at a time; stored here, one thread. Companies answered."""
    now = now or datetime.now(timezone.utc)
    stamp = now.strftime(store.ISO)
    slugs = due(conn, now, limit)
    with ThreadPoolExecutor(WORKERS) as pool:
        answers = list(pool.map(lambda slug: ask(client, base, slug), slugs))
    answered = [(slug, site, stamp, int(np), int(staff)) for slug, (ok, site, np, staff) in zip(slugs, answers) if ok]
    with conn:
        conn.executemany("INSERT INTO companies (slug, website, fetched_at, nonprofit, staffing) VALUES (?, ?, ?, ?, ?)"
                         " ON CONFLICT (slug) DO UPDATE SET website = excluded.website, fetched_at = excluded.fetched_at,"
                         " nonprofit = excluded.nonprofit, staffing = excluded.staffing", answered)
    return len(answered)


def refresh_quietly(conn, client: httpx.Client, base: str) -> None:
    """At the job check: jobs were found either way, so a failure here is logged, never raised."""
    try:
        n = refresh(conn, client, base)
        if n:
            print(f"company websites: {n} looked up")
    except Exception as exc:  # noqa: BLE001 - never stops the job check
        print(f"company websites: skipped ({exc})", file=sys.stderr)


def slug_of(conn, row: dict) -> str | None:
    """A row's company record id: its own, else its listed job's (an application row has none)."""
    if row.get("company_slug"):
        return row["company_slug"]
    found = None
    if row.get("public_slug"):
        found = conn.execute("SELECT company_slug FROM jobs WHERE public_slug = ?", (row["public_slug"],)).fetchone()
    if found is None and row.get("url"):
        found = store.jobs_by_link(conn, row["url"])
        found = (found["company_slug"],) if found else None
    return found[0] if found else None


def link(conn, row: dict) -> str | None:
    """The company's website on record, else None: name shows as plain words, no link."""
    if not (row.get("company") or "").strip():
        return None
    slug = slug_of(conn, row)
    found = conn.execute("SELECT website FROM companies WHERE slug = ?", (slug,)).fetchone() if slug else None
    return website(found[0]) if found else None
