import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path

import pytest

import cfg
import locks
import status
import store
import today
from conftest import make_job
from test_status import make_folder

CONFIG = cfg.load(cfg.PROFILES / "example.yml")
CHECK = "2026-09-29T12:00:00Z"
NOW = datetime(2026, 9, 29, 13, 0, tzinfo=timezone.utc)
ROOT = Path(__file__).resolve().parents[2]


def page(conn, jobs_dir, todo=()) -> str:
    return today.build(conn, CONFIG, jobs_dir, NOW, list(todo))


def job(slug, **over):
    return make_job(slug, posted_at="2026-09-28T10:00:00Z", **over)


def applied(conn, slug, on):
    status.set_state(conn, status.resolve(conn, Path("/nowhere"), slug), "applied", on)


SNAPSHOT = """# Today

Tuesday, September 29. So far: 1 sent.

## Waiting on you

- **Job 1** - Data Analyst, Globex
  - Resume made 5 days ago
  - https://jobs.lever.co/globex/1
  - Say: "apply to job 1" - or "I sent job 1" if you already did

## Follow up

No reply for a while. A short note asking where things stand is common practice - about 3 weeks after applying, about 2 weeks once you've talked with them - if you have someone to write to. Many employers never write back.

- **Job 2** - Senior Vue Engineer old, Acme
  - Applied 29 days ago, no reply yet
  - https://boards.greenhouse.io/acme/jobs/old
  - Say: "write a follow-up for job 2" - or "I heard back from job 2", "job 2 is closed"

## New since last check

- **Job 3** - Senior Vue Engineer paid, Acme
  - remote · $150k-190k (meets your pay) · added to your list today
  - https://boards.greenhouse.io/acme/jobs/paid
  - Say: "resume for job 3"
- **Job 4** - Senior Vue Engineer plain, Acme
  - remote · pay not listed · added to your list today
  - https://boards.greenhouse.io/acme/jobs/plain
  - Say: "resume for job 4"

## Not finished

- The morning job check is off. Say: "turn on the morning job check"

## What you can say

- "find new jobs"
- "resume for job 12"
- "I sent job 12 / I heard back from job 12"
- "is job 12 still open?"
- "change what I'm looking for"

Guides:

- [What you can ask](Guides/What%20you%20can%20ask.md)
- [Who sees what](Guides/Who%20sees%20what.md)
- [What makes a good resume](Guides/What%20makes%20a%20good%20resume.md)
- [Keep your chats out of AI training](Guides/Keep%20your%20chats%20out%20of%20AI%20training.md)
"""


def test_page_in_plain_words(conn, tmp_path):
    make_folder(tmp_path, "Globex - Data Analyst", "https://jobs.lever.co/globex/1", "Globex", "Data Analyst", None)
    status.backfill(conn, tmp_path)
    conn.execute("UPDATE applications SET state_at = '2026-09-24T12:00:00Z'")
    conn.commit()
    store.upsert(conn, [job("old")], "2026-08-01T12:00:00Z")
    applied(conn, "old", "2026-08-31T12:00:00Z")
    store.upsert(conn, [job("plain"), job("paid", salary_min=150000, salary_max=190000,
                                           salary_currency="USD", salary_period="year")], CHECK)
    assert page(conn, tmp_path, ["The morning job check is off. Say: \"turn on the morning job check\""]) == SNAPSHOT


def test_every_section_hides_when_empty(conn, tmp_path):
    text = page(conn, tmp_path)
    assert "##" not in text.split("## What you can say")[0]
    assert 'Nothing new since the last check. Say: "find new jobs"' in text
    assert "So far" not in text


def test_lists_never_a_table_or_numbered_list(conn, tmp_path):
    store.upsert(conn, [job(f"j{i}") for i in range(3)], CHECK)
    lines = page(conn, tmp_path).splitlines()
    assert not any(line.lstrip().startswith("|") for line in lines)
    assert not any(line.lstrip()[:1].isdigit() for line in lines)


def test_new_is_last_check_or_unannounced_only(conn, tmp_path):
    # announced in an earlier check => old news; announced in this one or never => new
    store.upsert(conn, [job("earlier"), job("latest"), job("never")], CHECK)
    store.mark_seen(conn, ["earlier"], "2026-09-28T12:00:05Z")
    store.mark_seen(conn, ["latest"], "2026-09-29T12:00:05Z")
    # likely filled: never new
    store.upsert(conn, [job("stale")], "2026-09-01T12:00:00Z")
    conn.execute("UPDATE jobs SET fetched_at = ? WHERE public_slug != 'stale'", (CHECK,))
    assert [j["public_slug"] for j in today.new_jobs(conn, CONFIG, NOW)] == ["latest", "never"]


def test_new_job_age_agrees_with_new(conn, tmp_path):
    # reposted posting freehire first saw 66 days ago, reaching the list in this check (real install)
    store.upsert(conn, [job("repost", reality={"age_days": 66}), job("fresh", reality={"age_days": 3})], CHECK)
    lines = {j: next(line for line in page(conn, tmp_path).split(f"/jobs/{j}")[0].splitlines()[::-1] if "·" in line)
             for j in ("repost", "fresh")}
    assert lines["repost"].endswith("added to your list today · posting first seen 66 days ago")
    assert lines["fresh"].endswith("added to your list today")
    assert "first seen 66d" not in page(conn, tmp_path)
    # still unannounced from an earlier check: its own day on the list, never freehire's
    store.upsert(conn, [job("waited", reality={"age_days": 40})], "2026-09-26T12:00:00Z")
    conn.execute("UPDATE jobs SET fetched_at = ?", (CHECK,))
    assert "added to your list 3 days ago · posting first seen 40 days ago" in page(conn, tmp_path)


def test_new_leaves_out_jobs_already_in_progress(conn, tmp_path):
    store.upsert(conn, [job("a"), job("b")], CHECK)
    applied(conn, "a", CHECK)
    assert [j["public_slug"] for j in today.new_jobs(conn, CONFIG, NOW)] == ["b"]


def test_new_capped_with_rest_in_the_chat(conn, tmp_path, monkeypatch):
    monkeypatch.setattr(today, "NEW_MAX", 2)
    store.upsert(conn, [job(f"j{i}") for i in range(5)], CHECK)
    text = page(conn, tmp_path)
    assert text.count('Say: "resume for job') == 2
    assert '- 3 more - ask the chat. Say: "show me more new jobs"' in text


def test_same_number_as_the_chat_list(conn, tmp_path):
    store.upsert(conn, [job("a"), job("b")], CHECK)
    first = store.numbered(conn, [dict(store.all_jobs(conn)[1], duplicates=[])])[0]
    assert f"**Job {first['num']}** - {first['title']}" in page(conn, tmp_path)


def test_waiting_never_counts_what_is_left(conn, tmp_path, monkeypatch):
    monkeypatch.setattr(today, "WAITING_MAX", 1)
    for i in range(3):
        make_folder(tmp_path, f"Globex - Role {i}", f"https://jobs.lever.co/globex/{i}", "Globex", f"Role {i}", None)
    text = page(conn, tmp_path)
    assert text.count("Resume made") == 1
    assert '- More in the chat. Say: "what is waiting on me"' in text
    assert not any(ch.isdigit() for ch in text.split("More in the chat")[1].splitlines()[0])


def test_follow_up_after_three_weeks_only(conn, tmp_path):
    store.upsert(conn, [job("recent"), job("old")], CHECK)
    applied(conn, "recent", "2026-09-20T12:00:00Z")
    applied(conn, "old", "2026-09-01T12:00:00Z")
    text = page(conn, tmp_path)
    assert "Senior Vue Engineer old" in text.split("## Follow up")[1]
    assert "Senior Vue Engineer recent" not in text
    assert "So far: 2 sent." in text


def test_progress_counts_interviews_and_offers(conn, tmp_path):
    store.upsert(conn, [job("a"), job("b"), job("c")], CHECK)
    for slug, state in (("a", "interview"), ("b", "offer"), ("c", "no")):
        status.set_state(conn, status.resolve(conn, tmp_path, slug), state, CHECK)
    assert "So far: 3 sent, 1 interview, 1 offer." in page(conn, tmp_path)


def test_closed_after_sending_still_counts_as_sent(conn, tmp_path):
    # closing a job after it was sent never un-sends it; one never sent was never progress
    store.upsert(conn, [job("a"), job("b")], CHECK)
    applied(conn, "a", "2026-09-01T12:00:00Z")
    status.set_state(conn, status.resolve(conn, tmp_path, "b"), "resume_made", "2026-09-20T12:00:00Z")
    for slug in ("a", "b"):
        status.set_state(conn, status.resolve(conn, tmp_path, slug), "closed", CHECK)
    text = page(conn, tmp_path)
    assert "So far: 1 sent." in text and "## Follow up" not in text and "## Waiting on you" not in text


def test_not_finished_only_when_true(tmp_path, monkeypatch):
    resume = tmp_path / "Resume details.yml"
    config = cfg.merge(CONFIG, {"resume": {"master": str(resume)}})
    monkeypatch.setattr(cfg, "ROOT", Path("/"))
    todo = today.unfinished(config, tmp_path, morning_check_on=False)
    assert [t.split(".")[0] for t in todo] == ["Your resume isn't in yet", "The morning job check is off"]
    resume.write_text("x", encoding="utf-8")
    assert "own numbers" in today.unfinished(config, tmp_path, morning_check_on=True)[0]
    (tmp_path / "gaps.json").write_text("{}", encoding="utf-8")
    assert today.unfinished(config, tmp_path, morning_check_on=True) == []
    # email is optional: never set up = nothing to finish; started, no password = half done
    (tmp_path / "email.env").write_text("SMTP_USER=a@b.c\n", encoding="utf-8")
    assert today.unfinished(config, tmp_path, morning_check_on=True) == [
        'Email alerts are half set up. Say: "finish setting up email"']
    (tmp_path / "email.env").write_text("SMTP_USER=a@b.c\nSMTP_PASSWORD=x\n", encoding="utf-8")
    assert today.unfinished(config, tmp_path, morning_check_on=True) == []


def test_builds_under_a_second_on_a_full_list(conn, tmp_path):
    # real install 2026-09-29: 1343 rows, 8 job folders
    store.upsert(conn, [job(f"j{i}", title=f"Engineer {i}", company=f"Co {i % 300}",
                            salary_min=100000 + i, salary_max=150000 + i, salary_currency="USD",
                            reality={"age_days": i % 120, "repost_count": i % 4}) for i in range(1400)], CHECK)
    # 1000 announced by an earlier check, 400 new in this one, 8 of those already in progress
    store.mark_seen(conn, [f"j{i}" for i in range(1000)], "2026-09-28T12:00:05Z")
    for i in range(8):
        make_folder(tmp_path, f"Co {i} - Engineer {i}", f"https://x.test/{i}", f"Co {i}", f"Engineer {i}", f"j{1000 + i}")
    start = time.perf_counter()
    text = page(conn, tmp_path)
    assert time.perf_counter() - start < 1
    assert "382 more - ask the chat" in text


def test_write_is_whole_and_locked(conn, tmp_path, monkeypatch):
    monkeypatch.setattr(cfg, "DATA", tmp_path / ".data")
    monkeypatch.setattr(cfg, "ROOT", tmp_path)
    monkeypatch.setattr(today, "unfinished", lambda config: [])
    config = cfg.merge(CONFIG, {"db": ".data/jobs.db"})
    out = today.write(config, tmp_path / "Today.md", NOW)
    assert out.read_text(encoding="utf-8").startswith("# Today\n")
    assert not (tmp_path / ".data" / "today.lock").exists()
    # another chat holding the lock past the wait => plain "another chat" line, page untouched
    monkeypatch.setattr(today, "lock", lambda: locks.held(cfg.DATA / "today.lock", "another chat is updating", wait_s=0))
    with locks.held(cfg.DATA / "today.lock", "busy"):
        with pytest.raises(SystemExit, match="another chat"):
            today.write(config, tmp_path / "Today.md", NOW)


def test_page_is_private():
    assert "Today.md" in (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
    gate = (ROOT / "app/skills/report-defect.md").read_text(encoding="utf-8")
    assert "`Today.md`" in gate


BRIEF = """Job Finder today (same as their Today page). If the user only greets you or asks what's next, answer with this in plain words, each job written "**Job 12** - title, company", never a 1. 2. 3. list; otherwise use it only when it helps. Never say how many resumes are unsent.
- Waiting on you (resume made, not sent): Job 1 - Data Analyst, Globex, resume made 5 days ago
- Follow up (no reply for a while): Job 2 - Senior Vue Engineer old, Acme, applied 29 days ago
- New since last check: 2. Top: Job 3 - Senior Vue Engineer paid, Acme; Job 4 - Senior Vue Engineer plain, Acme
- Not finished: The morning job check is off."""


def test_chat_brief_matches_the_page(conn, tmp_path):
    make_folder(tmp_path, "Globex - Data Analyst", "https://jobs.lever.co/globex/1", "Globex", "Data Analyst", None)
    status.backfill(conn, tmp_path)
    conn.execute("UPDATE applications SET state_at = '2026-09-24T12:00:00Z'")
    conn.commit()
    store.upsert(conn, [job("old")], "2026-08-01T12:00:00Z")
    applied(conn, "old", "2026-08-31T12:00:00Z")
    store.upsert(conn, [job("plain"), job("paid", salary_min=150000, salary_max=190000,
                                           salary_currency="USD", salary_period="year")], CHECK)
    todo = ["The morning job check is off. Say: \"turn on the morning job check\""]
    assert today.brief(conn, CONFIG, tmp_path, NOW, todo) == BRIEF
    # same numbers as the page, whichever is built first
    assert "**Job 3** - Senior Vue Engineer paid" in page(conn, tmp_path, todo)


def test_chat_brief_stays_short_on_a_full_list(conn, tmp_path):
    # hook output lands in every new chat's context: a few hundred tokens at most
    store.upsert(conn, [job(f"j{i}", title=f"Senior Staff Platform Engineer {i}", company=f"Company Name {i}")
                        for i in range(400)], CHECK)
    for i in range(20):
        make_folder(tmp_path, f"Company Name {i} - Role {i}", f"https://x.test/{i}", f"Company Name {i}", f"Role {i}", None)
    for i in range(20, 40):
        applied(conn, f"j{i}", "2026-08-01T12:00:00Z")
    text = today.brief(conn, CONFIG, tmp_path, NOW, ["a", "b"])
    assert len(text) < 1400
    assert len(re.findall(r"Job \d+ -", text)) == 9
    assert "Waiting on you" in text and "20" not in text.split("Follow up")[0]


def test_chat_brief_never_reads_resume_or_settings(conn, tmp_path):
    source = (ROOT / "app" / "today.py").read_text(encoding="utf-8")
    body = source.split("def brief(")[1].split("\ndef lock(")[0]
    assert "resume_path(config, \"master\")" not in body and "read_text" not in body and "yaml" not in body
    assert "Nothing new since the last check." in today.brief(conn, CONFIG, tmp_path, NOW, [])


def test_chat_brief_silent_before_setup_or_on_failure(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(cfg, "config_path", lambda: tmp_path / "missing.yml")
    today.print_brief()
    (tmp_path / "missing.yml").write_text("{", encoding="utf-8")
    today.print_brief()
    assert capsys.readouterr() == ("", "")


def test_claude_hook_runs_the_brief_other_ais_keep_the_page():
    settings = json.loads((ROOT / ".claude" / "settings.json").read_text(encoding="utf-8"))
    [entry] = settings["hooks"]["SessionStart"]
    assert entry["matcher"] == "startup|clear"
    assert [h["command"] for h in entry["hooks"]] == ["uv run app/jobs.py today --brief"]
    assert "today" not in (ROOT / ".codex" / "config.toml").read_text(encoding="utf-8")


def test_follow_up_days_per_stage(conn, tmp_path):
    """Applied waits 21 days, heard back 15, interview 12 (settings follow_up)."""
    store.upsert(conn, [job("a"), job("h"), job("i")], CHECK)
    for slug, state in (("a", "applied"), ("h", "heard_back"), ("i", "interview")):
        status.set_state(conn, status.resolve(conn, Path("/nowhere"), slug), state, "2026-09-15T12:00:00Z")  # 14 days
    quiet = [r["public_slug"] for r in today.follow_up_rows(conn, "2026-09-29T12:00:00Z", CONFIG["follow_up"])]
    assert quiet == ["i"]
    quiet = [r["public_slug"] for r in today.follow_up_rows(conn, "2026-09-30T12:00:00Z", CONFIG["follow_up"])]
    assert sorted(quiet) == ["h", "i"]


def test_follow_up_quiet_one_stretch_after_logged_then_suggests_closing(conn, tmp_path):
    store.upsert(conn, [job("old")], CHECK)
    applied(conn, "old", "2026-08-01T12:00:00Z")
    key = status.resolve(conn, Path("/nowhere"), "old")["key"]
    status.log_event(conn, key, "followed_up", "2026-09-20T12:00:00Z")
    assert today.follow_up_rows(conn, "2026-09-29T12:00:00Z", CONFIG["follow_up"]) == []
    rows = today.follow_up_rows(conn, "2026-10-12T12:00:00Z", CONFIG["follow_up"])
    assert rows[0]["chased"] == "2026-09-20T12:00:00Z"
    text = "\n".join(today.follow_up(conn, "2026-10-12T12:00:00Z", CONFIG["follow_up"]))
    assert "You followed up 22 days ago, still no reply" in text and 'Say: "job 1 is closed"' in text
    assert status.get(conn, key)["state"] == "applied"  # a follow-up is never a status
