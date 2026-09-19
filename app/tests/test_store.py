import store
from conftest import make_job

NOW = "2026-09-15T12:00:00Z"
LATER = "2026-09-15T12:30:00Z"


def test_upsert_keys_on_public_slug(conn):
    store.upsert(conn, [make_job("a"), make_job("b")], NOW)
    store.upsert(conn, [make_job("a", title="Renamed")], LATER)
    jobs = {j["public_slug"]: j for j in store.all_jobs(conn)}
    assert len(jobs) == 2
    assert jobs["a"]["title"] == "Renamed"
    assert jobs["a"]["first_fetched_at"] == NOW
    assert jobs["a"]["fetched_at"] == LATER
    assert jobs["a"]["countries"] == ["us"]


def test_close_missing_only_inside_window_and_tier(conn):
    store.upsert(conn, [
        make_job("fresh-gone", posted_at="2026-09-14T00:00:00Z"),
        make_job("old-gone", posted_at="2026-09-01T00:00:00Z"),
        make_job("fresh-kept", posted_at="2026-09-14T00:00:00Z"),
        make_job("other-tier", tier="local", posted_at="2026-09-14T00:00:00Z"),
    ], NOW)
    closed = store.close_missing(conn, "remote", {"fresh-kept"}, "2026-09-12T13:00:00Z", LATER)
    assert closed == 1
    open_slugs = {j["public_slug"] for j in store.all_jobs(conn)}
    assert open_slugs == {"old-gone", "fresh-kept", "other-tier"}


def test_close_missing_without_window_closes_all_absent(conn):
    store.upsert(conn, [make_job("x", tier="local"), make_job("y", tier="local")], NOW)
    assert store.close_missing(conn, "local", {"y"}, None, LATER) == 1


def test_reappearing_row_reopens(conn):
    store.upsert(conn, [make_job("a")], NOW)
    store.close_missing(conn, "remote", set(), None, NOW)
    store.upsert(conn, [make_job("a")], LATER)
    assert [j["public_slug"] for j in store.all_jobs(conn)] == ["a"]


def test_seen_excludes_from_unseen(conn):
    store.upsert(conn, [make_job("a"), make_job("b")], NOW)
    store.mark_seen(conn, ["a"], NOW)
    assert [j["public_slug"] for j in store.unseen_open(conn)] == ["b"]
    store.mark_seen(conn, ["a", "b"], LATER)
    assert store.unseen_open(conn) == []
