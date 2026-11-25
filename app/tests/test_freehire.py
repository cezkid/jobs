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


def detail(answers: dict[str, tuple[int, dict]]) -> httpx.Client:
    """GET /jobs/<slug> -> answers[slug] (status, data); anything else fails the request."""
    def handler(request):
        slug = request.url.path.rsplit("/", 1)[-1]
        if slug not in answers:
            return httpx.Response(500)
        status, data = answers[slug]
        return httpx.Response(status, json={"data": data})
    return httpx.Client(transport=httpx.MockTransport(handler))


def test_recheck_closes_older_jobs_the_job_search_closed_or_dropped(conn):
    store.upsert(conn, [make_job(s) for s in ("closed", "gone", "open", "unanswered")], days_ago(5))
    started = days_ago(0)
    store.upsert(conn, [make_job("fetched-now")], started)
    asks = {"closed": (200, {"closed_at": days_ago(1)}), "gone": (404, {}), "open": (200, {"closed_at": None})}
    with detail(asks) as c:
        assert freehire.recheck(conn, c, "https://api.test", since=started) == (3, 2)
    assert {j["public_slug"] for j in store.all_jobs(conn)} == {"open", "unanswered", "fetched-now"}
    # asked rows wait RECHECK_DAYS; the unanswered one is asked again next check
    assert freehire.recheck_due(conn, started, datetime.now(timezone.utc)) == ["unanswered"]


def test_recheck_asks_never_asked_then_most_recently_seen(conn):
    store.upsert(conn, [make_job("old")], days_ago(20))
    store.upsert(conn, [make_job("recent")], days_ago(3))
    store.upsert(conn, [make_job("asked-long-ago")], days_ago(2))
    conn.execute("UPDATE jobs SET checked_at = ? WHERE public_slug = 'asked-long-ago'", (days_ago(9),))
    due = freehire.recheck_due(conn, days_ago(0), datetime.now(timezone.utc))
    assert due == ["recent", "old", "asked-long-ago"]


def test_recheck_failure_never_stops_the_check(conn, capsys):
    store.upsert(conn, [make_job("a")], days_ago(5))
    with httpx.Client(transport=httpx.MockTransport(lambda r: (_ for _ in ()).throw(RuntimeError("boom")))) as c:
        freehire.recheck_quietly(conn, c, "https://api.test", days_ago(0))
    assert "a" in {j["public_slug"] for j in store.all_jobs(conn)}


def test_recheck_stops_asking_at_the_rate_limit(conn):
    store.upsert(conn, [make_job(f"j{i}") for i in range(20)], days_ago(5))
    asked = []
    def handler(request):
        asked.append(request.url.path)
        return httpx.Response(429)
    with httpx.Client(transport=httpx.MockTransport(handler)) as c:
        assert freehire.recheck(conn, c, "https://api.test", since=days_ago(0)) == (0, 0)
    assert len(asked) <= freehire.RECHECK_WORKERS
    assert len(store.all_jobs(conn)) == 20


# --- the job search stopped sending a job's own link (2026-11-23): asked for by its pass-through link ---

def go(answers: dict[str, httpx.Response], asked: list | None = None) -> httpx.Client:
    """HEAD /go/<slug> -> answers[slug]; any other request, or a GET, fails the test."""
    def handler(request):
        assert request.method == "HEAD" and "/go/" in request.url.path, request
        if asked is not None:
            asked.append(request.url.path.rsplit("/", 1)[-1])
        return answers[request.url.path.rsplit("/", 1)[-1]]
    return httpx.Client(transport=httpx.MockTransport(handler))


def to(link: str) -> httpx.Response:
    return httpx.Response(302, headers={"location": link})


def test_a_row_without_a_link_gets_the_employers_own_from_the_pass_through(conn):
    store.upsert(conn, [{**make_job("blank"), "url": ""}, make_job("linked"), {**make_job("closed"), "url": ""}], days_ago(0))
    conn.execute("UPDATE jobs SET closed_at = ? WHERE public_slug = 'closed'", (days_ago(0),))
    asked = []
    with go({"blank": to("https://acme.wd5.myworkdayjobs.com/x/job/Analyst_R1?utm_source=freehire.me")}, asked) as c:
        assert freehire.links(conn, c, "https://api.test") == (1, 1)
    assert asked == ["blank"]  # never a row that has its link, never a closed one
    assert {j["public_slug"]: j["url"] for j in store.all_jobs(conn)}["blank"] == \
        "https://acme.wd5.myworkdayjobs.com/x/job/Analyst_R1?utm_source=freehire.me"


@pytest.mark.parametrize("answer", [httpx.Response(404), httpx.Response(200), httpx.Response(302),
                                    to("https://api.test/jobs/somewhere"), to("javascript:alert(1)"), to("/jobs/x")])
def test_no_employer_link_there_stays_blank_and_waits_before_the_next_ask(conn, answer):
    store.upsert(conn, [{**make_job("blank"), "url": ""}], days_ago(0))
    with go({"blank": answer}) as c:
        assert freehire.links(conn, c, "https://api.test") == (1, 0)
    assert store.all_jobs(conn)[0]["url"] == ""
    now = datetime.now(timezone.utc)
    assert freehire.links_due(conn, now) == []
    assert freehire.links_due(conn, now + timedelta(days=freehire.LINK_RETRY_DAYS, minutes=1)) == ["blank"]


def test_links_stop_asking_at_the_rate_limit_and_ask_again_next_check(conn):
    store.upsert(conn, [{**make_job(f"j{i}"), "url": ""} for i in range(20)], days_ago(0))
    asked = []
    with go({f"j{i}": httpx.Response(429) for i in range(20)}, asked) as c:
        assert freehire.links(conn, c, "https://api.test") == (0, 0)
    assert len(asked) <= freehire.RECHECK_WORKERS
    assert len(freehire.links_due(conn, datetime.now(timezone.utc))) == 20


def test_links_failure_never_stops_the_check(conn):
    store.upsert(conn, [{**make_job("a"), "url": ""}], days_ago(0))
    with httpx.Client(transport=httpx.MockTransport(lambda r: (_ for _ in ()).throw(RuntimeError("boom")))) as c:
        freehire.links_quietly(conn, c, "https://api.test")
    assert store.all_jobs(conn)[0]["url"] == ""


def test_a_refetched_row_keeps_the_link_it_had_when_the_job_search_sends_none(conn):
    store.upsert(conn, [make_job("a")], days_ago(1))
    had = store.all_jobs(conn)[0]["url"]
    store.upsert(conn, [{**make_job("a"), "url": "", "title": "Analyst II"}], days_ago(0))
    assert (store.all_jobs(conn)[0]["url"], store.all_jobs(conn)[0]["title"]) == (had, "Analyst II")
    store.upsert(conn, [{**make_job("a"), "url": "https://x.test/moved"}], days_ago(0))
    assert store.all_jobs(conn)[0]["url"] == "https://x.test/moved"


def test_a_row_the_job_search_sends_without_url_is_stored_blank():
    assert freehire.normalize({"public_slug": "a", "title": "Analyst"}, "t")["url"] == ""
    assert freehire.normalize({"public_slug": "a", "title": "Analyst", "url": None}, "t")["url"] == ""
