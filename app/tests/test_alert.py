import pytest

import alert
import cfg
import store
from conftest import make_job

CONFIG = cfg.load(cfg.PROFILES / "example.yml")
# fetch time = now: rank hides rows no fetch returned lately (rank.stale_days)
NOW = store.utc_now()


def plain(msg) -> str:
    return msg.get_body(("plain",)).get_content()


def markup(msg) -> str:
    return msg.get_body(("html",)).get_content()


def test_second_run_alerts_on_zero_rows(conn):
    store.upsert(conn, [make_job("a"), make_job("b", tier="local"), make_job("blocked", company_slug="jobgether")], NOW)
    sent = []
    assert alert.run(conn, CONFIG, sent.append) == 2
    assert alert.run(conn, CONFIG, sent.append) == 0
    assert len(sent) == 1


def test_new_row_after_digest_alerts_alone(conn):
    store.upsert(conn, [make_job("a")], NOW)
    alert.run(conn, CONFIG, lambda m: None)
    store.upsert(conn, [make_job("a"), make_job("c")], NOW)
    sent = []
    assert alert.run(conn, CONFIG, sent.append) == 1
    assert "jobs/c" in plain(sent[0])
    assert "jobs/a" not in plain(sent[0])


def test_failed_send_marks_nothing_seen(conn):
    store.upsert(conn, [make_job("a")], NOW)

    def boom(msg):
        raise RuntimeError("smtp down")

    with pytest.raises(RuntimeError):
        alert.run(conn, CONFIG, boom)
    assert len(store.unseen_open(conn)) == 1


def test_digest_caps_at_top_25_and_counts_the_rest():
    ranked = [make_job(f"r{i}") for i in range(30)] + [make_job("n0", tier="local")]
    msg = alert.build_message(ranked, CONFIG)
    assert msg["Subject"] == "31 new finance jobs (30 Remote US, 1 Springfield area)"
    body = plain(msg)
    assert body.count("https://boards.greenhouse.io/") == 25
    assert "6 more - ask the chat to see them" in body
    assert "== Springfield area ==" not in body
    assert "6 more" in markup(msg)


def test_short_digest_lists_every_row_grouped_by_tier():
    msg = alert.build_message([make_job("r0"), make_job("n0", tier="local")], CONFIG)
    body = plain(msg)
    assert body.count("https://boards.greenhouse.io/") == 2
    assert body.index("== Remote US ==") < body.index("== Springfield area ==")
    assert "more - ask" not in body


def test_popup_preview_names_top_three_titles():
    ranked = [make_job(s, title=t) for s, t in [("a", "Payroll Clerk"), ("b", "Auditor"), ("c", "Controller"), ("d", "Teller")]]
    assert alert.build_message(ranked, CONFIG).preview == "Payroll Clerk; Auditor; Controller"


def test_all_seen_run_marks_every_row_seen(conn):
    store.upsert(conn, [make_job(f"r{i}", title=f"Analyst {i}") for i in range(30)], NOW)
    assert alert.run(conn, CONFIG, lambda m: None) == 30
    assert store.unseen_open(conn) == []


def test_repost_of_sent_job_is_not_new(conn):
    store.upsert(conn, [make_job("a", title="Clerk")], NOW)
    alert.run(conn, CONFIG, lambda m: None)
    store.upsert(conn, [make_job("a-again", title="Clerk", salary_min=50000, salary_currency="USD")], NOW)
    assert alert.run(conn, CONFIG, lambda m: None) == 0


def test_html_escapes_title_and_url():
    job = make_job("x", title="Sr <UI> & Eng", url='https://x.io/a?b=1&c="2"', collections=["yc", "us-h1b-sponsor"],
                   salary_min=150000, salary_currency="USD")
    msg = alert.build_message([job], CONFIG)
    assert '<a href="https://x.io/a?b=1&amp;c=&quot;2&quot;">Sr &lt;UI&gt; &amp; Eng</a>' in markup(msg)
    assert "Sr <UI> & Eng - Acme | remote · $150k (meets your pay) · first seen" in plain(msg)


class FakeSMTP:
    def __init__(self, host, port, timeout=None):
        self.host, self.port, self.timeout = host, port, timeout
        FakeSMTP.calls = []

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def login(self, user, password):
        FakeSMTP.calls.append((self.host, self.port, user, password))
        if password != "good":
            raise RuntimeError("Username and Password not accepted")


def test_check_login_signs_in_with_configured_host():
    alert.check_login(CONFIG, "me@gmail.com", "good", connect=FakeSMTP)
    assert FakeSMTP.calls == [("smtp.gmail.com", 465, "me@gmail.com", "good")]


def test_check_login_raises_on_bad_password():
    with pytest.raises(RuntimeError, match="not accepted"):
        alert.check_login(CONFIG, "me@gmail.com", "typo", connect=FakeSMTP)
