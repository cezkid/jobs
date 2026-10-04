from datetime import datetime, timedelta, timezone

import httpx
import pytest

import companies
import store
from conftest import make_job

BASE = "https://api.test"
NOW = datetime(2026, 10, 3, 12, tzinfo=timezone.utc)


def stamp(days: int) -> str:
    return (NOW - timedelta(days=days)).strftime(store.ISO)


def client(answers: dict, asked: list | None = None) -> httpx.Client:
    def handler(request):
        slug = request.url.path.rsplit("/", 1)[-1]
        if asked is not None:
            asked.append(slug)
        got = answers.get(slug, 404)
        if isinstance(got, Exception):
            raise got
        if isinstance(got, int):
            return httpx.Response(got)
        return httpx.Response(200, json={"data": {"company": {"company_info": {"website": got}}}})
    return httpx.Client(transport=httpx.MockTransport(handler))


def listed(conn, *slugs):
    store.upsert(conn, [make_job(f"j-{s}", company=s.title(), company_slug=s) for s in slugs], stamp(0))


def cached(conn, slug):
    found = conn.execute("SELECT website, fetched_at FROM companies WHERE slug = ?", (slug,)).fetchone()
    return tuple(found) if found else None


# a company's website shows on Today after one morning check, from its job search record
def test_website_stored_once_answered(conn):
    listed(conn, "notion")
    assert companies.refresh(conn, client({"notion": "https://notion.so"}), BASE, NOW) == 1
    assert cached(conn, "notion") == ("https://notion.so", stamp(0))


# the job search asked about each company once a month, not at every check
def test_fresh_answer_not_asked_again_old_one_is(conn):
    listed(conn, "notion", "figma")
    conn.execute("INSERT INTO companies VALUES ('notion', 'https://notion.so', ?)", (stamp(5),))
    conn.execute("INSERT INTO companies VALUES ('figma', NULL, ?)", (stamp(31),))
    asked = []
    companies.refresh(conn, client({"figma": "https://figma.com"}, asked), BASE, NOW)
    assert asked == ["figma"]
    assert cached(conn, "figma")[0] == "https://figma.com"


# no record on the job search = a web search link, and not asked again for a month
def test_no_record_stored_as_none(conn):
    listed(conn, "muse")
    companies.refresh(conn, client({}), BASE, NOW)
    assert cached(conn, "muse") == (None, stamp(0))


# a hiccup at the job search doesn't leave a company without its website for a month
@pytest.mark.parametrize("failure", [500, httpx.ConnectError("down")])
def test_failed_request_retried_next_check(conn, failure):
    listed(conn, "notion")
    assert companies.refresh(conn, client({"notion": failure}), BASE, NOW) == 0
    assert cached(conn, "notion") is None
    assert companies.due(conn, NOW) == ["notion"]


# a website value the browser shouldn't open never becomes a link on Today
@pytest.mark.parametrize("bad", ["javascript:alert(1)", "ftp://x.test", "https://x.test/a b",
                                 'https://x.test/"onclick', "notion.so", "", None])
def test_unsafe_website_dropped(conn, bad):
    listed(conn, "notion")
    companies.refresh(conn, client({"notion": bad}), BASE, NOW)
    assert cached(conn, "notion") == (None, stamp(0))


# a long job list asks politely: a small batch per check, the rest next time
def test_batch_per_check(conn):
    listed(conn, *[f"c{i:02}" for i in range(5)])
    asked = []
    companies.refresh(conn, client({}, asked), BASE, NOW, limit=3)
    assert len(asked) == 3 and len(companies.due(conn, NOW)) == 2


# a broken company lookup never stops the morning job check
def test_refresh_quietly_never_raises(conn, monkeypatch):
    listed(conn, "notion")
    monkeypatch.setattr(companies, "refresh", lambda *a, **k: 1 / 0)
    companies.refresh_quietly(conn, client({}), BASE)


# a company without a website on record shows as plain words: no web search, no link from its id
def test_link_none_without_a_website(conn):
    listed(conn, "sample")
    assert companies.link(conn, {"company": "Sample & Co", "company_slug": "sample"}) is None
    assert companies.link(conn, {"company": ""}) is None


# live: the job search still answers with a website for a well-known company (Notion, 2026-10-03)
def test_live_companies_endpoint_has_a_website():
    with httpx.Client(timeout=30) as c:
        ok, site = companies.ask(c, "https://freehire.me/api/v1", "notion")
    assert ok and site and site.startswith("http"), site
