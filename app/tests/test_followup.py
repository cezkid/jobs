import re
from pathlib import Path

import pytest

import followup


@pytest.mark.parametrize("days, said", [(5, "a week"), (7, "a week"), (21, "three weeks"), (24, "three weeks"),
                                        (44, "six weeks"), (45, "two months"), (60, "two months"), (300, "several months")])
def test_elapsed_weeks_then_months(days, said):
    assert followup.elapsed(days) == said


def test_names_role_company_and_asks_by_stage():
    subject, body = followup.draft("Data Analyst", "Acme", 24, "applied", None, "Jane Doe")
    assert subject == "Following up: Data Analyst application"
    assert "I applied for the Data Analyst role at Acme three weeks ago and have not had a reply yet." in body
    assert followup.ASK_APPLIED in body and body.endswith("Jane Doe")
    _, later = followup.draft("Data Analyst", "Acme", 14, "interview", None, "Jane Doe")
    assert "We last spoke about the Data Analyst role at Acme two weeks ago" in later and followup.ASK_LATER in later


def test_strength_line_only_in_their_own_words_or_left_out():
    _, body = followup.draft("Nurse", "Mercy", 21, "applied", "Cut ICU handoff errors 30% with a checklist.", "Jane Doe")
    assert "For context: Cut ICU handoff errors 30% with a checklist." in body
    _, bare = followup.draft("Nurse", "Mercy", 21, "applied", None, "Jane Doe")
    assert "For context" not in bare and "\n\n\n" not in bare


def test_tone_short_direct_no_apology():
    for state in ("applied", "heard_back", "interview"):
        subject, body = followup.draft("Senior Software Engineer, Platform", "Acme Holdings", 30, state,
                                       "Built 14 Python dashboards used by 3 regional teams.", "Jane Doe")
        text = f"{subject}\n{body}".casefold()
        assert "?" in body and len(re.findall(r"\w+", body)) <= 120
        for banned in ("just checking in", "sorry", "apologi", "i know you're busy", "any update", "passionate",
                       "hoping to hear", "touch base"):
            assert banned not in text, banned
        assert followup.draft("Senior Software Engineer, Platform", "Acme Holdings", 30, state, None, "Jane Doe") == \
            followup.draft("Senior Software Engineer, Platform", "Acme Holdings", 30, state, None, "Jane Doe")


def test_command_writes_the_draft_into_the_job_folder(tmp_path, monkeypatch, capsys):
    import status
    import store
    from test_status import make_folder
    jobs_dir = tmp_path / "My Jobs"
    folder = make_folder(jobs_dir / "2 Sent", "Job 1 - Globex - Data Analyst", "https://jobs.lever.co/globex/1",
                         "Globex", "Data Analyst", "g-da")
    config = {"db": str(tmp_path / "jobs.db"), "resume": {"jobs_dir": str(jobs_dir), "master": str(tmp_path / "r.yml")}}
    monkeypatch.setattr(followup.cfg, "load", lambda: config)
    monkeypatch.setattr(followup.cfg, "resume_path", lambda c, key: Path(c["resume"][key]))
    monkeypatch.setattr(followup.schema, "load", lambda path: {"contact": {"name": "Jane Doe"}, "roles": []})
    conn = store.connect(tmp_path / "jobs.db")
    status.set_state(conn, status.resolve(conn, jobs_dir, "https://jobs.lever.co/globex/1"), "applied", "2026-09-01T12:00:00Z")
    conn.close()
    monkeypatch.setattr(followup.sys, "argv", ["follow-up", "https://jobs.lever.co/globex/1"])
    followup.main()
    text = (folder / followup.FILE).read_text(encoding="utf-8")
    assert text.startswith("Subject: Following up: Data Analyst application") and text.rstrip().endswith("Jane Doe")
    assert "nothing is sent for them" in capsys.readouterr().out
