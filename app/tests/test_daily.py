import daily


def test_failure_notifies_through_next_way_when_email_fails():
    got = []

    def email(msg):
        raise OSError("mail server down")

    def boom():
        raise RuntimeError("freehire unreachable")

    assert not daily.guarded(boom, lambda: [(email, "emailed"), (got.append, "notified")])
    assert [m["Subject"] for m in got] == [daily.FAILED]
    assert "freehire unreachable" in got[0].get_content()


def test_broken_settings_still_notify():
    got = []

    def missing_settings():
        raise SystemExit("Search settings.yml missing")

    assert not daily.guarded(missing_settings, lambda: [(got.append, "notified")])
    assert got[0].preview == daily.FAILED_HINT


def test_success_sends_no_failure():
    got = []
    assert daily.guarded(lambda: None, lambda: [(got.append, "notified")])
    assert got == []


def test_desktop_is_last_resort_after_email(monkeypatch):
    monkeypatch.setenv("SMTP_USER", "me@example.com")
    monkeypatch.setenv("SMTP_PASSWORD", "pw")
    assert [label for _, label in daily.senders(daily.cfg.defaults())] == ["emailed to me@example.com", "notified"]
    monkeypatch.delenv("SMTP_PASSWORD")
    assert [label for _, label in daily.senders(daily.cfg.defaults())] == ["notified"]


def test_today_page_rebuilt_after_each_check(monkeypatch):
    # VS Code left open for days showed the page from the day it was opened
    calls = []
    monkeypatch.setattr(daily.cfg, "load", lambda: {"x": 1})
    monkeypatch.setattr(daily, "check", lambda config, send: calls.append("check"))
    monkeypatch.setattr(daily.today, "write", lambda config: calls.append(("today", config)))
    daily.work()
    assert calls == ["check", ("today", {"x": 1})]


def test_today_page_failing_is_not_a_failed_check(monkeypatch):
    # jobs were found and announced: "couldn't check for jobs today" would be untrue
    got = []

    def broken(config):
        raise SystemExit("another chat is updating the Today page - try again in a minute")
    monkeypatch.setattr(daily.cfg, "load", lambda: {})
    monkeypatch.setattr(daily, "check", lambda config, send: None)
    monkeypatch.setattr(daily.today, "write", broken)
    assert daily.guarded(daily.work, lambda: [(got.append, "notified")])
    assert got == []


def test_daily_last_ok_reads_newest_ok_line(tmp_path):
    (tmp_path / "daily.log").write_text(
        "== 2026-01-01T07:00:00\nok 2026-01-01T07:01:00 5 jobs\n"
        "failed 2026-01-03T07:01:00 boom\nok 2026-01-02T07:01:00 6 jobs\n")
    assert daily.last_ok(tmp_path).isoformat() == "2026-01-02T07:01:00"


def test_daily_last_ok_none_without_log_or_store(tmp_path):
    assert daily.last_ok(tmp_path) is None


def test_daily_last_ok_falls_back_to_store(tmp_path):
    import store
    conn = store.connect(tmp_path / "jobs.db")
    cols = [r[1] for r in conn.execute("PRAGMA table_info(jobs)") if r[3] and r[4] is None]
    conn.execute(f"INSERT INTO jobs ({','.join(cols)}) VALUES ({','.join('?' * len(cols))})",
                 ["2026-02-02T08:00:00" if c.endswith("fetched_at") else "x" for c in cols])
    conn.commit()
    conn.close()
    (tmp_path / "daily.log").write_text("failed 2026-02-03T07:00:00 boom\n")
    assert daily.last_ok(tmp_path).isoformat() == "2026-02-02T08:00:00"
