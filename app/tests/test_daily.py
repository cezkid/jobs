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
