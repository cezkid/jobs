"""Company links on the Today page: each company's own website, from the job search's company
record (`GET /companies/<its listing id>` -> `data.company.company_info.website`); none on record
=> plain name, no link (owner 2026-10-03: no web-search fallback). Asked once per company at the job check, cached 30 days, never at click time
(app/docs/jobs/freehire.md#companies). No about-us page in the data: main website only, never a
guessed path, never a link built from the slug.
"""
import sys
from datetime import datetime, timedelta, timezone
from urllib.parse import quote, urlsplit

import httpx

import store

MAX_AGE_DAYS = 30
# asked one after another, this many per check: the rest wait for the next one
BATCH = 50


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
        " AND (c.fetched_at IS NULL OR c.fetched_at < ? OR c.nonprofit IS NULL) ORDER BY j.company_slug LIMIT ?",
        (old, limit))]


def nonprofit(company: dict) -> bool:
    """The record calls the employer a nonprofit: organization_type "Non-Profit" or industry
    "nonprofit". 2026-10-09, 250 random employers of US HR-titled jobs: 20 so (the posting's own
    words said it on 6); set on about half of records, so "no" here says little."""
    industries = company.get("industries")
    return company.get("organization_type") == "Non-Profit" or (isinstance(industries, list) and "nonprofit" in industries)


def ask(client: httpx.Client, base: str, slug: str) -> tuple[bool, str | None, bool]:
    """(answered, website, nonprofit). 404 = no record => answered, none. Any other failure => not
    answered: try again next check."""
    try:
        resp = client.get(f"{base}/companies/{quote(slug, safe='')}")
        if resp.status_code == 404:
            return True, None, False
        resp.raise_for_status()
        company = ((resp.json() or {}).get("data") or {}).get("company") or {}
        info = company.get("company_info") or {}
        np = nonprofit(company)
    except (httpx.HTTPError, ValueError, AttributeError):
        return False, None, False
    return True, website(info.get("website") if isinstance(info, dict) else None), np


def refresh(conn, client: httpx.Client, base: str, now: datetime | None = None, limit: int = BATCH) -> int:
    """Asks for each due company, sequentially. Companies answered."""
    now = now or datetime.now(timezone.utc)
    stamp = now.strftime(store.ISO)
    answered = 0
    for slug in due(conn, now, limit):
        ok, site, np = ask(client, base, slug)
        if not ok:
            continue
        with conn:
            conn.execute("INSERT INTO companies (slug, website, fetched_at, nonprofit) VALUES (?, ?, ?, ?) ON CONFLICT (slug)"
                         " DO UPDATE SET website = excluded.website, fetched_at = excluded.fetched_at,"
                         " nonprofit = excluded.nonprofit", (slug, site, stamp, int(np)))
        answered += 1
    return answered


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
