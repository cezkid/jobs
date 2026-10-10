from datetime import datetime, timedelta, timezone

import httpx
import pytest

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


def test_two_passes_in_one_tier_close_only_what_neither_returned(conn):
    # internship search: one pass per tag, same tier. Closed per pass, the second pass closed
    # every row only the first found (40 of 214 on one fresh check, 2026-10-08)
    config = {**CONFIG, "passes": [{"tier": "local", "params": {"seniority": ["intern"]}},
                                   {"tier": "local", "params": {"employment_type": ["internship"]}}]}
    store.upsert(conn, [make_job("gone", tier="local", posted_at=days_ago(1))], "2026-09-15T00:00:00Z")

    def handler(request):
        slugs = ["tag-a", "both"] if "seniority" in request.url.params else ["tag-b", "both"]
        return httpx.Response(200, json={"data": [raw(s) for s in slugs], "meta": {"total": 2}})
    with httpx.Client(transport=httpx.MockTransport(handler)) as c:
        summary = freehire.run(config, conn, c)
    assert summary["local"] == {"fetched": 3, "closed": 1, "truncated": False, "days": 7}
    assert {j["public_slug"] for j in store.all_jobs(conn)} == {"tag-a", "tag-b", "both"}


def test_ignored_filter_stops_before_anything_is_stored(conn):
    """The job search answers a filter it doesn't know w/ every job, flagged only in meta."""
    def handler(request):
        return httpx.Response(200, json={"data": [raw("flood")], "meta": {
            "total": 798143, "ignored_params": [{"param": "categry"}]}})
    with httpx.Client(transport=httpx.MockTransport(handler)) as c, pytest.raises(SystemExit) as stop:
        freehire.run(CONFIG, conn, c)
    assert "categry" in str(stop.value) and "798,143" in str(stop.value)
    assert store.all_jobs(conn) == []


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


def test_title_words_sent_as_one_exact_phrase():
    """Unquoted, "nurse" matched Nursery titles; already-quoted words are left alone."""
    assert freehire.query_params({"q": "registered nurse", "q_fields": "title"})["q"] == '"registered nurse"'
    assert freehire.query_params({"q": '"RN"'})["q"] == '"RN"'
    assert "q" not in freehire.query_params({"category": ["healthcare"]})


def test_clearance_flag_kept_true_or_none():
    """The job search sends true or nothing - nothing is not 'no clearance needed'."""
    assert freehire.normalize({**raw("a"), "requires_clearance": True}, "remote")["requires_clearance"] is True
    assert freehire.normalize(raw("b"), "remote")["requires_clearance"] is None


def test_work_permit_and_student_answers_never_reach_the_job_search():
    # privacy table: search filters only - not the resume, not the work-permit answer
    sent = []

    def handler(request):
        sent.append(dict(request.url.params))
        return httpx.Response(200, json={"data": [], "meta": {"total": 0}})
    config = {**CONFIG, "work_authorization": {"student_visa": True, "needs_sponsorship": True},
              "rank": {"career_level": "entry", "salary_floor_usd": 45760, "salary_floor_unit": "hour"}}
    conn = store.connect(":memory:")
    freehire.run(config, conn, httpx.Client(transport=httpx.MockTransport(handler)))
    assert sent and all(set(p) <= {"category", "limit", "offset", "posted_within_days"} for p in sent), sent


# an "HR" title search brought "Server Assistant - $20.25/hr" and "Staff RN - 12 Hr" (184 of 1,000 newest,
# 2026-10-09): the HR there is a rate or a shift, never the job searched for
def test_hr_title_search_drops_pay_and_shift_hours_titles(conn):
    titles = {"a": "Server Assistant - $20.25/hr", "b": "Staff RN 12 Hr - Obstetrics", "c": "Payroll/HR Specialist",
              "d": "2027 HR Intern - Garland, TX", "e": "VP, HR", "f": "Costco Sales Rep | 26/hr to start"}

    def handler(request):
        return httpx.Response(200, json={"data": [{**raw(s), "title": t} for s, t in titles.items()], "meta": {"total": 6}})
    config = {**CONFIG, "passes": [{"tier": "remote", "params": {"q": "HR", "q_fields": "title"}}]}
    with httpx.Client(transport=httpx.MockTransport(handler)) as c:
        freehire.run(config, conn, c)
    assert {j["public_slug"] for j in store.all_jobs(conn)} == {"c", "d", "e"}
    assert not freehire.pay_word_only("Server Assistant - $20.25/hr", {"category": ["hr"]})


# pay sits at the end of a posting, past the ~1,000 characters /jobs/search keeps: the search asks the
# endpoint w/ whole descriptions, and the range the posting states wins over the job search's field
def test_pay_read_from_the_posting_wins_over_the_field():
    sent = []

    def handler(request):
        sent.append(request.url.path)
        return httpx.Response(200, json={"data": [], "meta": {"total": 0}})
    freehire.run(CONFIG, store.connect(":memory:"), httpx.Client(transport=httpx.MockTransport(handler)))
    assert sent and set(sent) == {"/agent/jobs/search"}
    row = {**raw("a"), "description": "<p>Annual Salary Range $80,000—$82,000 USD</p>",
           "enrichment": {"salary_min": 22000, "salary_max": 32000, "salary_currency": "usd", "salary_period": "year"}}
    got = freehire.normalize(row, "remote")
    assert (got["salary_min"], got["salary_max"], got["salary_currency"], got["salary_period"]) == (80000, 82000, "USD", "year")
    plain = freehire.normalize({**row, "description": "<p>No pay here.</p>"}, "remote")
    assert (plain["salary_min"], plain["salary_currency"]) == (22000, "USD")


# a job board tags any cleared job "... with Security Clearance": 814 of 5,347 US "security" titles in 30 days
# (2026-10-09), 734 of them not security work; the job search's own flag was on 279
def test_security_title_search_drops_the_boards_clearance_tag_and_keeps_its_flag(conn):
    titles = {"a": "Senior Cloud Developer with Security Clearance", "b": "Security Engineer with Security Clearance",
              "c": "Information Security Manager", "d": "Business Analyst - with an Active Security Clearance"}

    def handler(request):
        return httpx.Response(200, json={"data": [{**raw(s), "title": t} for s, t in titles.items()], "meta": {"total": 4}})
    config = {**CONFIG, "passes": [{"tier": "remote", "params": {"q": "security", "q_fields": "title"}}]}
    with httpx.Client(transport=httpx.MockTransport(handler)) as c:
        freehire.run(config, conn, c)
    assert {j["public_slug"] for j in store.all_jobs(conn)} == {"b", "c"}
    assert freehire.pay_word_only("Software Engineer with Security Clearance", {"q": "security engineer"})
    assert freehire.normalize({**raw("x"), "title": "Software Developer III with Security Clearance"}, "remote")[
        "requires_clearance"] is True
