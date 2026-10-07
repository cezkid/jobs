"""Manatal: link shapes, saved form definitions (anonymised, app/tests/fixtures/manatal) -> questions, each widget rule
on a copy of the page Manatal's template renders (fixtures/manatal/apply.html; nothing reaches the network)."""
import json
from pathlib import Path
from urllib.parse import urlsplit

import httpx
import pytest

from apply import browser, questions, systems
from apply.systems import manatal

FIXTURES = Path(__file__).parent / "fixtures" / "manatal"
LINK = "https://www.careers-page.com/acme/job/AB12CD34"
APPLY = LINK + "/apply"


def form(tenant: str, currencies=()) -> dict:
    return {q["id"]: q for q in manatal.from_definition(json.loads((FIXTURES / f"tenant-{tenant}.json").read_text()), currencies)}


# --- links ---

def test_links_freehire_lists_land_on_the_apply_form():
    assert systems.for_url(LINK + "?utm_source=freehire.me") is manatal
    assert manatal.application_url(LINK + "?utm_source=freehire.me") == APPLY
    assert manatal.application_url(APPLY) == APPLY
    assert manatal.application_url("http://careers-page.com/acme/job/AB12CD34/") == APPLY
    assert manatal.parse_url(" " + LINK + " ") == ("acme", "AB12CD34")


def test_other_links_refused():
    for url in ("https://www.careers-page.com/acme", "https://www.careers-page.com/acme/jobs",
                "https://www.careers-page.com.example.com/acme/job/AB12CD34", "https://jobs.lever.co/acme/1b2c"):
        assert not manatal.matches(url), url
    with pytest.raises(ValueError):
        manatal.parse_url("https://jobs.lever.co/acme/1b2c")


def test_on_tab_the_same_posting_only():
    assert systems.on_tab(manatal, LINK, APPLY + "?x=1")
    assert not systems.on_tab(manatal, LINK, "https://www.careers-page.com/acme/job/ZZ99ZZ99/apply")


# --- saved definitions -> questions ---

def test_standard_boxes_read_with_keys_full_name_never_split():
    a = form("a")
    got = {q["title"]: (q["kind"], q["key"], q["required"]) for q in a.values()}
    assert got == {"Full Name": ("text", "name", True), "Email": ("email", "email", True), "Phone": ("phone", "phone", True),
                   "Cover Letter": ("longtext", None, False), "Resume": ("file", "resume", True),
                   "Linkedin ID": ("url", "linkedin", True), "Current Position": ("text", None, True),
                   "Job Interested In": ("longtext", None, True)}
    assert all(id.isdigit() for id in a) and all(q.get("page") is None for q in a.values())
    # a cover letter is a text box here, never the letter file; phone may be optional (tenant E)
    e = {q["title"]: q for q in form("e").values()}
    assert e["Cover Letter"]["kind"] == "longtext" and not e["Phone"]["required"]
    assert e["Candidate Linkedin Profile"]["key"] == "linkedin" and e["Candidate Reference"]["kind"] == "text"


def test_yes_no_as_text_box_checkboxes_or_a_tick_box():
    b = {q["title"]: q for q in form("b").values()}
    # a "yesorno" field is a plain text box on the page (its one choice "Option 1" never shows)
    assert b["Are you legally able to work for any employer in the U.S?"]["kind"] == "text"
    meets = b["Do you meet all the requirements?"]
    assert (meets["kind"], meets["options"], meets["native"], meets["required"]) == ("yesno", ["Yes", "No"], "manatal:checkbox", True)
    d = [q for q in form("c").values() if q["native"] == "manatal:boolean"]
    assert len(d) == 2 and all(q["kind"] == "yesno" and q["options"] == ["Yes", "No"] and q["required"] for q in d)


def test_pay_box_brings_its_currency_and_frequency_lists():
    c = form("d", ["Barbados dollar", "United States dollar"])
    pay = next(q for q in c.values() if q["title"] == "Your expected compensation per month")
    assert pay["kind"] == "number" and not pay["required"]
    cur, per = c[pay["id"] + ":currency"], c[pay["id"] + ":frequency"]
    assert (cur["kind"], cur["options"], cur["native"]) == ("choice", ["Barbados dollar", "United States dollar"], "manatal:currency:expected")
    assert per["options"] == ["Hourly", "Daily", "Weekly", "Monthly", "Yearly"] and per["native"] == "manatal:frequency:expected"
    # never drafted: the pay you expect is the user's answer
    assert questions.never_draft(pay["title"])


def test_employer_lists_by_field_type():
    fields = [{"id": 1, "label": "Shift", "is_required": True, "field_type": "candidate_field", "client_field_slug": "shift",
               "response_type": "char", "client_field_field_type": "dropdown", "client_field_answer_choices": ["Day", "Night"]},
              {"id": 2, "label": "Tools", "is_required": False, "field_type": "candidate_field", "client_field_slug": "tools",
               "response_type": "array", "client_field_field_type": "multiple_select_dropdown", "client_field_answer_choices": ["A", "B"]},
              {"id": 3, "label": "Relocate?", "is_required": False, "field_type": "candidate_field", "client_field_slug": "relocate",
               "response_type": "char", "client_field_field_type": "multiple_choice", "client_field_answer_choices": ["Yes", "No"]},
              {"id": 4, "label": "Education", "is_required": True, "field_type": "educations"},
              {"id": 5, "label": "Start date", "is_required": False, "field_type": "other", "response_type": "datetime"},
              {"id": 6, "label": "Pronouns (or just my first name)", "is_required": False, "field_type": "other", "response_type": "char"}]
    got = {q["id"]: (q["kind"], q["native"], q["key"]) for q in manatal.from_definition(fields)}
    assert got == {"1": ("choice", "manatal:select", None), "2": ("multichoice", "manatal:multiselect", None),
                   "3": ("yesno", "manatal:radio", None), "4": ("longtext", "manatal:educations", None),
                   "5": ("date", "manatal:date", None), "6": ("text", "manatal:text", None)}


# --- closed + questions over plain HTTP ---

class Got:
    def __init__(self, status=200, text="", data=None, headers=None):
        self.status_code, self.text, self.data, self.headers = status, text, data, headers or {}

    def json(self):
        return self.data

    def raise_for_status(self):
        if self.status_code >= 400:
            raise httpx.HTTPStatusError(str(self.status_code), request=None, response=None)


PAGE = '<script> const selectedJobId = "4242"; const clientSlug = "acme"; </script>'


def test_questions_read_the_definition_by_the_pages_job_id(monkeypatch):
    asked = []

    def get(url, **kw):
        asked.append(url)
        if url == APPLY:
            return Got(text=PAGE)
        if url == manatal.CURRENCIES:
            return Got(data=[{"id": 840, "name": "United States dollar"}])
        return Got(data=json.loads((FIXTURES / "tenant-d.json").read_text()))
    monkeypatch.setattr(httpx, "get", get)
    qs = manatal.questions(LINK + "?utm_source=freehire.me")
    assert asked == [APPLY, manatal.DEFINITION.format(id="4242"), manatal.CURRENCIES]
    assert ["United States dollar"] in [q["options"] for q in qs]


def test_closed_or_unknown_posting_says_so(monkeypatch):
    monkeypatch.setattr(httpx, "get", lambda url, **kw: Got(404, "Manatal 404 The page you requested was not found."))
    with pytest.raises(ValueError, match="may have closed"):
        manatal.questions(LINK)
    assert "may have closed" in manatal.closed(LINK)
    monkeypatch.setattr(httpx, "get", lambda url, **kw: Got(text=PAGE))
    assert manatal.closed(LINK) is None
    monkeypatch.setattr(httpx, "get", lambda url, **kw: Got(503))
    assert manatal.closed(LINK).startswith("can't tell")
    monkeypatch.setattr(httpx, "get", lambda url, **kw: Got(text="<html>no form</html>"))
    assert "may have closed" in manatal.closed(LINK)


def test_browser_check_said_plainly(monkeypatch):
    monkeypatch.setattr(httpx, "get", lambda url, **kw: Got(text=PAGE) if url == APPLY
                        else Got(202, headers={"x-amzn-waf-action": "challenge"}))
    with pytest.raises(ValueError, match="browser check"):
        manatal.questions(LINK)


# --- the page ---

@pytest.fixture(scope="module")
def chrome():
    pw = pytest.importorskip("playwright.sync_api")
    try:
        exe = browser.chrome()
    except SystemExit:
        pytest.skip("Chrome not installed")
    with pw.sync_playwright() as p:
        b = p.chromium.launch(executable_path=exe, headless=True)
        yield b
        b.close()


@pytest.fixture
def page(chrome):
    """The apply page copy; nothing reaches the network."""
    context = chrome.new_context()
    asked = []

    def serve(route):
        u = urlsplit(route.request.url)
        asked.append(u.hostname)
        return route.fulfill(path=str(FIXTURES / "apply.html")) if u.hostname == "acme.example" else route.abort()

    context.route("**/*", serve)
    p = context.new_page()
    p.goto("https://acme.example/apply")
    yield p
    assert set(asked) <= {"acme.example"}, asked
    assert not p.evaluate("window.submitted || false")
    context.close()


def q(id, kind, answer, native="manatal:text", options=(), key=None, title="Question"):
    return {"id": id, "title": title, "kind": kind, "key": key, "native": native, "required": True,
            "options": list(options), "answer": answer}


def test_ids_on_page_name_each_box_pay_lists_apart_terms_left_out(page):
    assert manatal.ids_on_page(page) == ["1001", "1002", "1003", "1004", "1005", "1006", "1007", "1008",
                                         "1008:currency", "1008:frequency", "1009"]


def test_text_boxes_filled_and_read_back(page):
    for item in (q("1001", "text", "Test Applicant"), q("1002", "email", "test@example.com"),
                 q("1003", "phone", "555-0100"), q("1004", "longtext", "Line one\nLine two")):
        assert manatal.fill(page, item, None) == "ok" and manatal.holds(page, item)
    assert page.locator("#field1004").input_value() == "Line one\nLine two"
    assert not manatal.holds(page, q("1001", "text", "Someone Else"))


def test_pay_number_currency_and_frequency(page):
    pay = q("1008", "number", "$85,000", "manatal:number")
    assert manatal.fill(page, pay, None) == "ok" and page.locator("#field1008").input_value() == "85000" and manatal.holds(page, pay)
    cur = q("1008:currency", "choice", "united states dollar", "manatal:currency:expected")
    per = q("1008:frequency", "choice", "Yearly", "manatal:frequency:expected")
    assert manatal.fill(page, cur, None) == "ok" and page.locator("#expected_currency").input_value() == "840"
    assert manatal.fill(page, per, None) == "ok" and page.locator("#expected_frequency").input_value() == "year"
    assert manatal.holds(page, cur) and manatal.holds(page, per)
    assert manatal.fill(page, q("1008:currency", "choice", "Pound", "manatal:currency:expected"), None).startswith("ASK no option 'Pound'")
    assert manatal.fill(page, q("1008", "number", "competitive", "manatal:number"), None).startswith("ASK")


def test_checkboxes_picked_by_value_never_the_repeated_id(page):
    yes = q("1006", "yesno", "Yes", "manatal:checkbox", ["Yes", "No"])
    assert manatal.fill(page, yes, None) == "ok" and manatal.holds(page, yes)
    no = q("1006", "yesno", "No", "manatal:checkbox", ["Yes", "No"])
    assert manatal.fill(page, no, None) == "ok" and manatal.holds(page, no)
    assert page.locator('input[name="1006"]').evaluate_all("bs => bs.map(b => b.checked)") == [False, True]


def test_tick_box_yes_and_no(page):
    yes = q("1007", "yesno", "Yes", "manatal:boolean", ["Yes", "No"])
    assert manatal.fill(page, yes, None) == "ok" and page.locator("#field1007").is_checked() and manatal.holds(page, yes)
    no = q("1007", "yesno", "No", "manatal:boolean", ["Yes", "No"])
    assert manatal.fill(page, no, None) == "ok" and not page.locator("#field1007").is_checked() and manatal.holds(page, no)


def test_dropdown_by_text_never_the_select_one(page):
    item = q("1009", "choice", "contract", "manatal:select", ["Full time", "Contract"])
    assert manatal.fill(page, item, None) == "ok" and manatal.holds(page, item)
    assert not manatal.holds(page, q("1009", "choice", "Select Employment type", "manatal:select"))


def test_terms_never_ticked_and_left_to_the_applicant(page):
    terms = q("terms", "yesno", "Yes", "manatal:boolean", title="I have read and agree to the terms and conditions")
    assert "yours to do on the page" in manatal.fill(page, terms, None)
    assert not page.locator("input[name=terms_and_condition]").is_checked()


def test_resume_chosen_read_back_by_its_label(page, tmp_path):
    pdf = tmp_path / "Test_Resume.pdf"
    pdf.write_bytes(b"%PDF-1.4 test")
    resume = q("1005", "file", True, "manatal:resume", key="resume", title="Resume")
    assert manatal.fill(page, resume, str(pdf)) == "ok" and manatal.holds(page, resume)
    assert manatal.fill(page, resume | {"answer": False}, str(pdf)) == "skipped - upload not approved"


def test_resume_refused_in_the_pages_own_words(page, tmp_path):
    png = tmp_path / "photo.png"
    png.write_bytes(b"\x89PNG")
    resume = q("1005", "file", True, "manatal:resume", key="resume", title="Resume")
    got = manatal.fill(page, resume, str(png))
    assert got.startswith("FAIL the page says 'This file is invalid.") and not manatal.holds(page, resume)


def test_other_files_sections_and_dates_left_to_the_user(page):
    assert manatal.fill(page, q("9", "file", True, "manatal:attachment", title="Portfolio"), "x.pdf").startswith("ASK not the resume box")
    assert manatal.fill(page, q("9", "longtext", "x", "manatal:educations", title="Education"), None).startswith("ASK the Education section")
    assert manatal.fill(page, q("9", "date", "2026-11-01", "manatal:date", title="Start"), None).startswith("ASK date box")
    assert manatal.fill(page, q("9999", "text", "x"), None) == "FAIL question not on page"
