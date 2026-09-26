from datetime import datetime, timedelta, timezone

import httpx

import store
from conftest import make_job
from ingest import freehire

WINDOW = {"days": 7, "min_jobs": 0, "widen_to": [14, 30]}
CONFIG = {"api": {"base": "https://api.test", "page_limit": 100}, "window": WINDOW,
          "passes": [{"tier": "remote", "params": {"category": ["finance"]}}]}


def days_ago(n: int) -> str:
    return (datetime.now(timezone.utc) - timedelta(days=n)).strftime(store.ISO)


def raw(slug: str) -> dict:
    return {"public_slug": slug, "title": "Analyst", "url": f"https://x.test/{slug}"}


def client(total: int, slugs: list[str]) -> httpx.Client:
    def handler(request):
        offset = int(request.url.params["offset"])
        page = [raw(s) for s in slugs[offset:offset + int(request.url.params["limit"])]]
        return httpx.Response(200, json={"data": page, "meta": {"total": total}})
    return httpx.Client(transport=httpx.MockTransport(handler))


def test_truncated_pass_closes_nothing(conn, monkeypatch):
    monkeypatch.setattr(freehire, "API_OFFSET_CEILING", 2)
    store.upsert(conn, [make_job("past-ceiling")], "2026-09-15T00:00:00Z")
    with client(5, ["a", "b", "c"]) as c:
        summary = freehire.run(CONFIG, conn, c)
    assert summary["remote"] == {"fetched": 2, "closed": 0, "truncated": True, "days": 7}
    assert "past-ceiling" in {j["public_slug"] for j in store.all_jobs(conn)}


def test_complete_pass_closes_absent(conn):
    store.upsert(conn, [make_job("gone", posted_at=days_ago(1))], "2026-09-15T00:00:00Z")
    with client(1, ["a"]) as c:
        summary = freehire.run(CONFIG, conn, c)
    assert summary["remote"] == {"fetched": 1, "closed": 1, "truncated": False, "days": 7}


def test_passes_fetched_together_land_in_own_tier(conn):
    config = {**CONFIG, "passes": [{"tier": "remote", "params": {"cities": ["a"]}},
                                   {"tier": "local", "params": {"cities": ["b"]}}]}

    def handler(request):
        slug = request.url.params["cities"]
        return httpx.Response(200, json={"data": [raw(slug)], "meta": {"total": 1}})
    with httpx.Client(transport=httpx.MockTransport(handler)) as c:
        summary = freehire.run(config, conn, c)
    assert list(summary) == ["remote", "local"]
    assert {j["public_slug"]: j["tier"] for j in store.all_jobs(conn)} == {"a": "remote", "b": "local"}


def by_days(counts: dict[int, int]) -> httpx.Client:
    """Fake API answering `counts[days]` rows per posted_within_days; records days asked."""
    asked = []

    def handler(request):
        days = int(request.url.params["posted_within_days"])
        asked.append(days)
        page = [raw(f"{days}-{i}") for i in range(counts[days])]
        return httpx.Response(200, json={"data": page, "meta": {"total": len(page)}})
    c = httpx.Client(transport=httpx.MockTransport(handler))
    c.asked = asked
    return c


def test_busy_search_stays_at_seven_days(conn):
    config = {**CONFIG, "window": {**WINDOW, "min_jobs": 3}}
    with by_days({7: 5, 14: 9, 30: 20}) as c:
        summary = freehire.run(config, conn, c)
    assert c.asked == [7]
    assert summary["remote"]["days"] == 7


def test_thin_search_widens_until_enough(conn):
    config = {**CONFIG, "window": {**WINDOW, "min_jobs": 3}}
    with by_days({7: 1, 14: 3, 30: 20}) as c:
        summary = freehire.run(config, conn, c)
    assert c.asked == [7, 14]
    assert summary["remote"] == {"fetched": 3, "closed": 0, "truncated": False, "days": 14}


def test_widest_window_kept_when_never_enough(conn):
    config = {**CONFIG, "window": {**WINDOW, "min_jobs": 50}}
    with by_days({7: 1, 14: 2, 30: 4}) as c:
        summary = freehire.run(config, conn, c)
    assert c.asked == [7, 14, 30]
    assert summary["remote"]["fetched"] == 4


def test_pass_own_window_is_the_start():
    assert freehire.windows({"posted_within_days": 20}, WINDOW) == [20, 30]
    assert freehire.windows({}, WINDOW) == [7, 14, 30]


def test_close_uses_window_actually_fetched(conn):
    # row posted 20 days ago: outside 7, inside 30 => closed only once the pass widened to 30
    store.upsert(conn, [make_job("gone", posted_at=days_ago(20))], "2026-09-15T00:00:00Z")
    with by_days({7: 0}) as c:
        assert freehire.run(CONFIG, conn, c)["remote"]["closed"] == 0
    config = {**CONFIG, "window": {**WINDOW, "min_jobs": 3}}
    with by_days({7: 0, 14: 0, 30: 1}) as c:
        assert freehire.run(config, conn, c)["remote"]["closed"] == 1
