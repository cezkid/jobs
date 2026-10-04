"""Company links on the Today page: each company's own website, from the job search's company
record (`GET /companies/<its listing id>` -> `data.company.company_info.website`), else a web search
for its name. Asked once per company at the job check, cached 30 days, never at click time
(app/docs/jobs/freehire.md#companies). No about-us page in the data: main website only, never a
guessed path, never a link built from the slug.
"""
import sys
from datetime import datetime, timedelta, timezone
from urllib.parse import quote, quote_plus, urlsplit

import httpx

import store

MAX_AGE_DAYS = 30
# asked one after another, this many per check: the rest wait for the next one
BATCH = 50
SEARCH = "https://duckduckgo.com/?q="


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
        " AND (c.fetched_at IS NULL OR c.fetched_at < ?) ORDER BY j.company_slug LIMIT ?", (old, limit))]


def ask(client: httpx.Client, base: str, slug: str) -> tuple[bool, str | None]:
    """(answered, website). 404 = no record => answered, none. Any other failure => not answered:
    try again next check."""
    try:
        resp = client.get(f"{base}/companies/{quote(slug, safe='')}")
        if resp.status_code == 404:
            return True, None
        resp.raise_for_status()
        info = (((resp.json() or {}).get("data") or {}).get("company") or {}).get("company_info") or {}
    except (httpx.HTTPError, ValueError, AttributeError):
        return False, None
    return True, website(info.get("website") if isinstance(info, dict) else None)


def refresh(conn, client: httpx.Client, base: str, now: datetime | None = None, limit: int = BATCH) -> int:
    """Asks for each due company, sequentially. Companies answered."""
    now = now or datetime.now(timezone.utc)
    stamp = now.strftime(store.ISO)
    answered = 0
    for slug in due(conn, now, limit):
        ok, site = ask(client, base, slug)
        if not ok:
            continue
        with conn:
            conn.execute("INSERT INTO companies (slug, website, fetched_at) VALUES (?, ?, ?) ON CONFLICT (slug)"
                         " DO UPDATE SET website = excluded.website, fetched_at = excluded.fetched_at",
                         (slug, site, stamp))
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


def link(conn, row: dict) -> dict | None:
    """{url, website}: the company's website on record (website True), else a web search for its
    name. No company name => None."""
    name = (row.get("company") or "").strip()
    if not name:
        return None
    slug = slug_of(conn, row)
    found = conn.execute("SELECT website FROM companies WHERE slug = ?", (slug,)).fetchone() if slug else None
    site = website(found[0]) if found else None
    return {"url": site, "website": True} if site else {"url": SEARCH + quote_plus(name), "website": False}
