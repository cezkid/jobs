import httpx

import store
from conftest import make_job
from ingest import freehire

CONFIG = {"api": {"base": "https://api.test", "page_limit": 100},
          "passes": [{"tier": "remote", "params": {"category": ["finance"]}}]}


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
    assert summary["remote"] == {"fetched": 2, "closed": 0, "truncated": True}
    assert "past-ceiling" in {j["public_slug"] for j in store.all_jobs(conn)}


def test_complete_pass_closes_absent(conn):
    store.upsert(conn, [make_job("gone")], "2026-09-15T00:00:00Z")
    with client(1, ["a"]) as c:
        summary = freehire.run(CONFIG, conn, c)
    assert summary["remote"] == {"fetched": 1, "closed": 1, "truncated": False}
