import pytest

from apply import ashby

CONTACT = {"name": "Ada Lovelace", "email": "ada@example.com", "phone": "555-0100",
           "links": ["linkedin.com/in/ada", "github.com/ada"]}


def field(title, kind="String", path=None, required=True, options=()):
    return {"path": path or title, "title": title, "type": kind, "required": required, "options": list(options)}


def test_posting_link_with_or_without_application_or_tracking_tail():
    base = "https://jobs.ashbyhq.com/acme/45bdb7e5-14a8-494f-8fcb-30e42f0be67a"
    for url in (base, base + "/application", base + "?utm_source=freehire.me"):
        assert ashby.application_url(url) == base + "/application"
    with pytest.raises(ValueError):
        ashby.parse_url("https://acme.myworkdayjobs.com/x")


def test_resume_answers_only_what_it_states():
    fields = [field("Name", path="_systemfield_name"), field("Email", "Email", "_systemfield_email"),
              field("Phone Number", "Phone"), field("LinkedIn Profile URL"), field("GitHub"),
              field("Location", "Location", "_systemfield_location"), field("Why us?", "LongText")]
    got = {a["title"]: a["answer"] for a in ashby.draft(fields, CONTACT)}
    assert got["Name"] == "Ada Lovelace" and got["Email"] == "ada@example.com" and got["Phone Number"] == "555-0100"
    assert got["LinkedIn Profile URL"] == "https://www.linkedin.com/in/ada"
    assert got["GitHub"] == "https://www.github.com/ada"
    assert got["Location"] is None and got["Why us?"] is None  # the user's, never guessed


def test_earlier_answers_survive_a_second_prepare():
    fields = [field("Why us?", "LongText")]
    old = [{"path": "Why us?", "answer": "Their words.", "source": "user"}]
    assert ashby.draft(fields, CONTACT, old)[0]["answer"] == "Their words."


def test_work_permit_only_for_the_same_us_question():
    config = {"work_authorization": {"authorized_us": True, "needs_sponsorship": False}}
    same = [field("Are you legally authorized to work in the U.S. without restriction for any employer?", "Boolean"),
            field("Will you now or in the future require immigration sponsorship to work in the U.S.?", "Boolean")]
    assert [a["answer"] for a in ashby.draft(same, CONTACT, config=config)] == ["Yes", "No"]
    other = [field("Are you authorized to work in Canada?", "Boolean"),
             field("Are you legally authorized to work in the U.S. without restriction for any employer?", "String")]
    assert [a["answer"] for a in ashby.draft(other, CONTACT, config=config)] == [None, None]
    unset = ashby.draft(same, CONTACT, config={"work_authorization": {"authorized_us": None}})
    assert unset[0]["answer"] is None and unset[0]["source"] == ashby.ASK


def test_blank_required_questions_are_listed():
    answers = [{**field("A"), "answer": None}, {**field("B", required=False), "answer": None},
               {**field("C", "MultiValueSelect"), "answer": []}, {**field("D", "Boolean"), "answer": "No"}]
    assert [a["title"] for a in ashby.missing(answers)] == ["A", "C"]
