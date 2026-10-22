"""Zoho Recruit: links, the posting page's own records, the form definition -> questions (anonymised
fixture: one tenant's form with boxes seen on others added - app/docs/apply/zoho.md)."""
import json
from pathlib import Path

import httpx
import pytest

from apply import form, questions, systems
from apply.systems import zoho

FIXTURE = Path(__file__).parent / "fixtures" / "zoho" / "acme-form.json"
LINK = "https://acme.zohorecruit.com/jobs/Careers/600000000000123456?utm_source=freehire.me"


def definition() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def page(record: dict | None, form_id: str | None = "600000000000534761") -> str:
    """The posting page's two inline scripts as Zoho writes them (single-quoted JSON, \\x22 for quotes)."""
    rows = json.dumps([record] if record else []).replace('"', "\\x22").replace("-", "\\-")
    meta = {"page_name": "Careers", "detail_url": "https:\\/\\/acme.zohorecruit.com\\/jobs\\/Careers\\/1\\/Dev\\-Ops"}
    if form_id:
        meta["webform_id"] = form_id
    return (f"<script>var jobs = JSON.parse('{rows}');\nvar page_id  = '1';\n"
            f"var meta = {json.dumps(meta, separators=(',', ':'))};\n</script>")


OPEN = {"id": "600000000000123456", "Posting_Title": "Dev-Ops Engineer", "Publish": True, "Keep_on_Career_Site": True}


def test_links_match_zoho_recruit_postings_only():
    assert systems.for_url(LINK) is zoho
    assert zoho.link_parts("https://Acme-Two.zohorecruit.com/jobs/Careers/600000000000123456/Dev-Ops?source=CareerSite") == \
        ("acme-two", "Careers", "600000000000123456")
    assert zoho.parse_url(LINK) == ("acme", "600000000000123456")  # the portal page is every tenant's word
    # the form opens on the posting page itself: no tail, no query
    assert zoho.application_url(LINK) == "https://acme.zohorecruit.com/jobs/Careers/600000000000123456"
    for other in ("https://acme.zohorecruit.com/jobs/Careers", "https://acme.zohorecruit.com/jobs/Careers/rss",
                  "https://recruit.zoho.com/recruit/JBApplyAuth.do", "https://acme.zohorecruit.com.evil.io/jobs/Careers/600000000000123456"):
        assert not zoho.matches(other), other


def test_page_records_read_from_the_inline_scripts():
    jobs, form_id, portal = zoho.page_facts(page(OPEN))
    assert jobs == [OPEN] and form_id == "600000000000534761" and portal == "Careers"
    assert zoho.js_string(r"\x22a\x22 – \/ \- \'") == "\"a\" – / - '"


def test_closed_posting_said_in_the_pages_own_words():
    assert zoho.why_closed(OPEN) is None
    assert "No longer accepting applications" in zoho.why_closed(OPEN | {"$read_only_job": True})
    assert "Position filled" in zoho.why_closed(OPEN | {"Publish": False})
    assert "not on the employer's Zoho Recruit careers page" in zoho.why_closed(None)
    # the page's own words match the shared closed check too (form.closed reads them first)
    assert form.CLOSED.search("No longer accepting applications")


def fake_get(pages: dict, asked: list):
    def get(url, params=None, **kw):
        asked.append((url, params))
        status, body = pages[url]
        return httpx.Response(status, text=body if isinstance(body, str) else json.dumps(body),
                              request=httpx.Request("GET", url))
    return get


def test_questions_two_plain_reads_page_then_its_form(monkeypatch):
    asked = []
    pages = {"https://acme.zohorecruit.com/jobs/Careers/600000000000123456": (200, page(OPEN)),
             "https://acme.zohorecruit.com/recruit/v2/public/Job_Openings/600000000000123456/apply/600000000000534761":
                 (200, definition())}
    monkeypatch.setattr(zoho.httpx, "get", fake_get(pages, asked))
    got = zoho.questions(LINK)
    assert [u for u, _ in asked] == list(pages)
    # without pagename the definition answers 400 REQUIRED_PARAM_MISSING (measured)
    assert asked[1][1] == {"pagename": "Careers", "source": "CareerSite"}
    assert {"first_name", "last_name", "email", "phone", "resume"} <= {q["key"] for q in got}
    assert zoho.closed(LINK) is None


def test_gone_posting_never_reads_a_form(monkeypatch):
    asked = []
    url = "https://acme.zohorecruit.com/jobs/Careers/600000000000123456"
    for record, says in ((None, "may have closed"), (OPEN | {"$read_only_job": True}, "No longer accepting")):
        monkeypatch.setattr(zoho.httpx, "get", fake_get({url: (200, page(record))}, asked))
        with pytest.raises(ValueError, match=says):
            zoho.questions(LINK)
        assert says in zoho.closed(LINK)
    monkeypatch.setattr(zoho.httpx, "get", fake_get({url: (200, page(OPEN, form_id=None))}, asked))
    with pytest.raises(ValueError, match="takes applications elsewhere"):
        zoho.questions(LINK)
    monkeypatch.setattr(zoho.httpx, "get", fake_get({url: (404, "")}, asked))
    assert "may have closed" in zoho.closed(LINK)
    assert all(u == url for u, _ in asked)


def by_title(qs: list[dict]) -> dict:
    return {q["title"].split(" - ")[0].split(" (")[0]: q for q in qs}


def test_definition_to_questions_kinds_keys_and_what_is_never_a_question():
    qs = zoho.from_definition(definition())
    t = by_title(qs)
    assert [t[n]["key"] for n in ("First Name", "Last Name", "Email", "Mobile", "Street", "Zip/Postal Code", "City",
                                  "State/Province", "LinkedIn")] == \
        ["first_name", "last_name", "email", "phone", "street", "zip", "city", "state", "linkedin"]
    assert t["Mobile"]["kind"] == "phone" and t["LinkedIn"]["kind"] == "url" and t["Country"]["key"] is None
    assert t["Salutation"]["options"] == ["Mr.", "Mrs.", "Ms."]  # "-None-" is no answer
    assert t["Current Job Title"]["kind"] == "choice" and t["Candidate Skills"]["kind"] == "multichoice"
    assert t["Skill Set"]["native"] == "zoho:skills" and t["Skill Set"]["key"] == "skills"
    assert t["Resume"]["key"] == "resume" and t["Resume"]["required"] and t["Cover Letter"]["key"] == "cover_letter"
    assert zoho.file_limit(t["Resume"]) == 10485760
    # never a photo (AGENTS.md), never the CAPTCHA (the applicant's own; ids_on_page counts it for them)
    assert not [q for q in qs if "photo" in q["title"].casefold() or "captcha" in q["title"].casefold()]
    assert t["Email"]["max_chars"] == 255


def test_terms_and_consent_ticks_are_the_applicants_own():
    qs = zoho.from_definition(definition())
    ticks = [q for q in qs if q["native"] == "zoho:boolean"]
    assert len(ticks) == 4 and all(questions.signs(q["title"]) for q in ticks)
    drafted = questions.draft(ticks, {"name": "Ada Lovelace"})
    assert all(a["answer"] is None and questions.SIGN_ON_PAGE in a["source"] for a in drafted)
    assert not questions.missing(drafted)  # required, yet never blocks fill: ticked on the page
    tick = ticks[0] | {"answer": "Yes"}
    assert zoho.fill(None, tick, None).startswith(f"ASK {questions.SIGN_ON_PAGE}")


def test_screening_questions_by_type():
    t = by_title(zoho.from_definition(definition()))
    assert (t["Do you have reliable transportation to get to and from the workplace?"]["kind"],
            t["Do you have reliable transportation to get to and from the workplace?"]["native"]) == ("yesno", "zoho:radio")
    assert t["Which best describes you?"]["native"] == "zoho:radio" and t["Which best describes you?"]["kind"] == "choice"
    assert t["Which of these do you hold?"]["native"] == "zoho:checks"
    assert t["If you have previous driving experience, please describe below."]["kind"] == "longtext"
    assert t["Are you interested in part-time or full-time work?"]["native"] == "zoho:picklist"
    unknown = zoho.screening({"id": "9", "question": "Rate yourself", "type": 7, "ismandatory": False, "options": []})
    assert unknown["kind"] == "text" and zoho.fill(None, unknown | {"answer": "5"}, None).startswith("ASK")


def test_education_rows_per_school_answered_from_resume_details():
    asked = [q for q in zoho.from_definition(definition(), 2) if q["native"].startswith("zoho:edu:")]
    assert [q["entry"] for q in asked] == [0] * 8 + [1] * 8
    schools = [{"institution": "Acme University", "degree": "BS", "field": "Economics", "start": "2012-09", "end": "2016-05"},
               {"institution": "Acme College", "degree": "MBA", "end": "2020", "hide_year": True}]
    got = {(a["entry"], a["title"].split(": ")[1]): a["answer"] for a in questions.draft(asked, {}, schools=schools)}
    assert got[(0, "School")] == "Acme University" and got[(0, "Degree")] == "Bachelor of Science"
    assert (got[(0, "Start month")], got[(0, "Start year")], got[(0, "End month")], got[(0, "End year")]) == \
        ("September", "2012", "May", "2016")
    # dates the user hid stay off the form; the in-progress tick is never answered for every school at once
    assert got[(1, "End year")] is None and got[(1, "Start year")] is None
    assert got[(0, "still in progress (tick)")] is None and got[(1, "still in progress (tick)")] is None
    assert [zoho.month_number(m) for m in ("September", "May", "12", "sept", "x")] == ["9", "5", "12", "9", None]


def test_experience_is_one_yes_with_the_rows_boxes_named():
    work = next(q for q in zoho.from_definition(definition()) if q["native"].startswith("zoho:work:"))
    section, boxes = zoho.work_boxes(work)
    assert section == "600000000000534580"
    assert {"Occupation_Title", "Company", "Summary", "Work_Duration", "I_currently_work_here", "Reason_for_Leaving"} == set(boxes)
    assert work["kind"] == "yesno" and not work["required"] and work["key"] is None
    assert zoho.fill(None, work | {"answer": "No"}, None) == "skipped - user said no"
    assert [zoho.when(v) for v in ("2023-02", "2016", "present", None)] == \
        [("2", "2023"), (None, "2016"), (None, None), (None, None)]
    role = {"id": "r1", "bullets": [{"claim": "Led a team."}, {"claim": "Cut costs."}]}
    assert zoho.summary(role, {}) == "- Led a team.\n- Cut costs."
    assert zoho.summary(role, {"entries": [{"id": "r1", "bullets": [{"text": "Tailored line."}]}]}) == "- Tailored line."


def test_phone_typed_without_the_boxs_own_plus_one():
    assert [zoho.phone_typed(v) for v in ("555-0100", "(555) 010-0100", "+1 555 010 0100", "1-555-010-0100", "+44 20 7946 0000", "12")] == \
        ["555-0100", "(555) 010-0100", "555 010 0100", "555-010-0100", None, None]


def test_prepare_says_which_boxes_search_as_typed():
    asked = [questions.question("1", "Zip/Postal Code", "text", True, key="zip"),
             questions.question("2", "Skill Set", "text", False, key="skills"), questions.question("3", "Email", "email", True)]
    note = form.typed_note(zoho, asked)
    assert "zip, skills boxes search Zoho Recruit's own list as they're typed" in note
    assert form.typed_note(zoho, asked[2:]) == ""
    assert not getattr(zoho, "FILE_ON_CHOICE", False)  # the resume waits in the page until Submit (zoho.md)
