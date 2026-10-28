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


def test_daily_ok_line_survives_count_failure(monkeypatch, capsys):
    monkeypatch.setattr(daily.cfg, "load", lambda: {})
    monkeypatch.setattr(daily, "check", lambda config, send: None)
    monkeypatch.setattr(daily, "refresh_today", lambda config: None)
    daily.work()
    out = capsys.readouterr().out
    assert out.startswith("ok ") and "jobs" not in out


def test_daily_last_ok_reads_newest_ok_line(tmp_path):
    (tmp_path / "daily.log").write_text(
        "== 2026-01-01T07:00:00\nok 2026-01-01T07:01:00 5 jobs\n"
        "failed 2026-01-03T07:01:00 boom\nok 2026-01-02T07:01:00 6 jobs\n")
    got = daily.last_ok(tmp_path)
    assert got.utcoffset().total_seconds() == 0
    assert got.astimezone().replace(tzinfo=None).isoformat() == "2026-01-02T07:01:00"


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
    assert daily.last_ok(tmp_path).isoformat() == "2026-02-02T08:00:00+00:00"


def test_daily_last_ok_store_fallback_with_z(tmp_path):
    import store
    conn = store.connect(tmp_path / "jobs.db")
    cols = [r[1] for r in conn.execute("PRAGMA table_info(jobs)") if r[3] and r[4] is None]
    conn.execute(f"INSERT INTO jobs ({','.join(cols)}) VALUES ({','.join('?' * len(cols))})",
                 ["2026-02-02T08:00:00Z" if c.endswith("fetched_at") else "x" for c in cols])
    conn.commit()
    conn.close()
    got = daily.last_ok(tmp_path)
    assert got.isoformat() == "2026-02-02T08:00:00+00:00"
    (tmp_path / "daily.log").write_text("ok 2026-02-03T07:00:00 1 jobs\n")
    assert daily.last_ok(tmp_path) > got  # log and store compare like with like


def log(tmp_path, *lines: str):
    (tmp_path / "daily.log").write_text("\n".join(lines) + "\n", encoding="utf-8")


def test_ran_today_reads_only_todays_lines(tmp_path):
    from datetime import datetime
    now = datetime(2026, 10, 27, 14, 0)
    assert not daily.ran_today(tmp_path, "ok", now)
    log(tmp_path, "ok 2026-10-26T08:00:05 3269 jobs", "failed 2026-10-27T08:00:05 offline")
    assert not daily.ran_today(tmp_path, "ok", now)
    assert daily.ran_today(tmp_path, "failed", now)
    log(tmp_path, "ok 2026-10-27T08:00:05 3368 jobs")
    assert daily.ran_today(tmp_path, "ok", now)


def test_only_the_days_first_check_sends(tmp_path, monkeypatch):
    # every 2 hours, one message a day: later checks fill the list + Today, the jobs stay unseen
    sent = []
    monkeypatch.setattr(daily.cfg, "DATA", tmp_path)
    monkeypatch.setattr(daily.cfg, "load", lambda: {})
    monkeypatch.setattr(daily, "senders", lambda config: [("email", "emailed")])
    monkeypatch.setattr(daily, "check", lambda config, send: sent.append(send))
    monkeypatch.setattr(daily, "refresh_today", lambda config: None)
    daily.work()
    log(tmp_path, f"ok {daily.stamp()} 10 jobs")
    daily.work()
    assert sent == [("email", "emailed"), None]


def test_later_check_fetches_but_sends_nothing(monkeypatch, capsys):
    import httpx
    monkeypatch.setattr(daily.store, "connect", lambda path: None)
    monkeypatch.setattr(daily.cfg, "db_path", lambda config: "x.db")
    monkeypatch.setattr(daily.freehire, "run", lambda config, conn, client: {})
    monkeypatch.setattr(daily.freehire, "recheck_quietly", lambda *a: None)
    monkeypatch.setattr(daily.companies, "refresh_quietly", lambda *a: None)
    monkeypatch.setattr(daily.alert, "run", lambda *a: (_ for _ in ()).throw(AssertionError("sent")))
    daily.check({"api": {"timeout_s": 5, "base": "x"}}, None)
    assert capsys.readouterr().out.strip() == "later check, nothing sent"


def test_failure_reported_once_a_day(tmp_path, monkeypatch):
    # offline all day = one "couldn't check" message, not one per check
    got = []
    monkeypatch.setattr(daily.cfg, "DATA", tmp_path)
    monkeypatch.setattr(daily.cfg, "DAILY_LOG", tmp_path / "daily.log")
    monkeypatch.setattr(daily, "load_dotenv", lambda path: None)
    monkeypatch.setattr(daily, "senders", lambda config: [(got.append, "notified")])
    monkeypatch.setattr(daily, "work", lambda: (_ for _ in ()).throw(RuntimeError("offline")))
    # main() points stdout at the log, as the scheduled run does
    monkeypatch.setattr(daily.sys, "stdout", daily.sys.stdout)
    monkeypatch.setattr(daily.sys, "stderr", daily.sys.stderr)
    for _ in range(2):
        try:
            daily.main()
        except SystemExit:
            pass
        daily.sys.stdout.close()
    assert len(got) == 1
