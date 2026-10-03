import json
from pathlib import Path

import httpx
import pytest

from apply import form, questions, readahead

BASE = "https://api.test/v1"
FORM = {"found": True, "fetched": "2026-10-01T09:00:00Z", "provider": "greenhouse",
        "basics": ["First Name", "Last Name", "Email", "Resume/CV", "Cover Letter"],
        "questions": [
            {"text": "LinkedIn Profile", "required": False},
            {"text": "How did you hear about this job?", "required": True},
            {"text": "Are you currently authorized to work in the U.S.?", "required": True, "answer": "choose one"},
            {"text": "Will you now or in the future require visa sponsorship?", "required": True, "answer": "yes / no"},
            {"text": "What are your salary expectations?", "required": True},
            {"text": "Why do you want to work here?", "required": False, "answer": "written answer"}]}


def client(status: int, body: dict | None = None) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(status, json=body or {})))


def test_answer_words_map_to_kinds_and_keys():
    asked = readahead.as_questions(FORM)
    basics, own = asked[:5], asked[5:]
    assert [q["kind"] for q in own] == ["text", "text", "choice", "yesno", "text", "longtext"]
    assert own[0]["key"] == "linkedin" and own[0]["options"] == [] and own[0]["id"] == "q1"
    # contact boxes + uploads come first, answered from the resume - the paste page never skips them
    assert [(q["id"], q["kind"], q["key"], q["required"]) for q in basics] == [
        ("b1", "text", "first_name", True), ("b2", "text", "last_name", True), ("b3", "email", "email", True),
        ("b4", "file", "resume", True), ("b5", "file", "cover_letter", False)]


def test_404_is_not_known_ahead_never_asks_nothing():
    with client(404) as c:
        got = readahead.fetch(c, BASE, "x")
    assert got["found"] is False
    assert readahead.summary(got) == ["Not known ahead - its questions show when you apply."]
    with httpx.Client(transport=httpx.MockTransport(lambda r: (_ for _ in ()).throw(httpx.ConnectError("offline")))) as c:
        assert readahead.fetch(c, BASE, "x") is None  # tailoring goes on without it


def test_summary_counts_written_answers_topics_and_letter_box():
    lines = readahead.summary(FORM)
    assert lines[0].startswith("Read ahead from the employer's Greenhouse form on 2026-10-01")
    assert "Beyond your resume and contact details: 6 question(s), 1 written answer(s)." in lines
    assert "Asks about: the pay you expect, permission to work, visa sponsorship, how you heard." in lines
    assert "Has a cover letter box." in lines
    empty = {**FORM, "questions": [], "basics": ["Email"], "provider": "lever"}
    assert readahead.summary(empty)[1:] == ["Asks nothing beyond your resume and contact details.",
                                            "Lever doesn't publish which questions are required."]


def test_pay_never_drafted_and_an_answer_the_user_never_gave_is_refused():
    answers = questions.draft(readahead.as_questions(FORM), {"name": "Jane Doe"})
    pay = next(a for a in answers if "salary" in a["title"])
    assert pay["answer"] is None and pay["source"] == "ask the user - yours to answer: the pay you expect"
    pay["answer"] = "$120,000"
    assert questions.unvouched(answers) == [pay]
    pay["source"] = questions.USER_SAID
    assert questions.unvouched(answers) == []


def test_unsupported_form_read_ahead_becomes_a_page_to_paste(tmp_path, monkeypatch):
    folder = tmp_path / "Job 5 - Acme - Analyst"
    (folder / ".data").mkdir(parents=True)
    readahead.save(folder / ".data", FORM)
    monkeypatch.setattr(form.cfg, "load", lambda: {})
    monkeypatch.setattr(form.cfg, "resume_path", lambda c, k: tmp_path / "r.yml")
    monkeypatch.setattr(form.schema, "load", lambda p: {"contact": {"name": "Jane Doe", "links": ["linkedin.com/in/jane"]}})
    monkeypatch.setattr(form, "job_dir", lambda config, slug: folder)
    form.prepare("5", "https://acme.recruitee.com/o/analyst")
    saved = json.loads((folder / ".data" / questions.FILE).read_text())
    assert saved["system"] == form.PASTE
    with pytest.raises(SystemExit, match="paste"):
        form.fill("5")
    form.paste("5")
    text = (folder / form.ANSWERS_FILE).read_text()
    assert "**LinkedIn Profile**" in text and "linkedin.com/in/jane" in text.casefold()
    assert "**What are your salary expectations?** (required)\n\n(yours to answer on the page)" in text
    assert "**First Name** (required)\n\nJane" in text and "**Last Name** (required)\n\nDoe" in text
    assert text.index("**Email**") < text.index("**LinkedIn Profile**")


@pytest.mark.parametrize("page, closed", [
    ("Sorry, this job is no longer accepting applications.", True),
    ("The position has been filled. Thank you for your interest.", True),
    ("This job post is closed", True),
    ("Apply for this job. We are accepting applications on a rolling basis.", False),
])
def test_closed_posting_page_is_recognised(page, closed):
    assert bool(form.CLOSED.search(page)) is closed
