"""Paylocity: link shapes, the form definition in the apply page -> shared questions, each widget
rule against small fakes, closed off the apply page (plain GET, faked), and every box filled + read back
on a hand-built step in headless Chrome (fixtures/paylocity/form.html). Fixtures = 7 tenants' anonymised
definitions (app/tests/fixtures/paylocity/, measured 2026-10-03); facts in app/docs/apply/paylocity.md."""
import json
from pathlib import Path
from urllib.parse import urlsplit

import httpx
import pytest

from apply import browser, form, questions, systems
from apply.systems import paylocity

FIXTURES = Path(__file__).parent / "fixtures" / "paylocity"
OPTIONS = json.loads((FIXTURES / "options.json").read_text())


def tenant(letter: str) -> dict:
    return json.loads((FIXTURES / f"tenant-{letter}.json").read_text()) | OPTIONS


def by_id(letter: str) -> dict:
    return {q["id"]: q for q in paylocity.from_definition(tenant(letter))}


# --- links ---

def test_posting_form_and_freehire_links_open_the_form():
    form_url = "https://recruiting.paylocity.com/Recruiting/Jobs/Apply/1000001"
    for url in ("https://recruiting.paylocity.com/Recruiting/Jobs/Details/1000001",
                "https://recruiting.paylocity.com/Recruiting/Jobs/Details/1000001?utm_source=freehire.me",
                "https://recruiting.paylocity.com/recruiting/jobs/Apply/1000001/", form_url):
        assert paylocity.matches(url) and paylocity.application_url(url) == form_url
        assert systems.for_url(url) is paylocity


def test_other_links_refused():
    for url in ("https://recruiting.paylocity.com/Recruiting/Jobs/All/abc-123",
                "https://recruiting.paylocity.com/Recruiting/Jobs/Details/10000012x",
                "https://www.example.com/Recruiting/Jobs/Details/1000001",
                "https://job-boards.greenhouse.io/acme/jobs/1234567"):
        assert not paylocity.matches(url)
    with pytest.raises(ValueError):
        paylocity.application_url("https://www.example.com/careers/1000001")


# --- form definition -> questions ---

def test_page_data_read_off_the_apply_page():
    html = '<script>var x = 1; window.pageData = {"jobId": 7, "s": "a};b"}; window.other = {};</script>'
    assert paylocity.page_data(html) == {"jobId": 7, "s": "a};b"}
    assert paylocity.page_data("<html>no form</html>") is None


def test_contact_boxes_name_split_in_four_on_every_tenant():
    for letter in "abcdefg":
        got = by_id(letter)
        assert got["info.firstName"]["key"] == "first_name" and got["info.firstName"]["required"]
        assert got["info.lastName"]["required"] and not got["info.middleName"]["required"]
        assert got["info.email"]["kind"] == "email" and got["info.email"]["key"] == "email"
        assert got["btn-resume"]["key"] == "resume" and got["btn-resume"]["kind"] == "file"
        assert all(q["page"] for q in got.values())


def test_kinds_keys_required_options_and_page():
    a, b = by_id("a"), by_id("b")
    sms = a["info.smsOptedIn"]
    assert (sms["kind"], sms["native"], sms["required"]) == ("yesno", "combo", True)
    assert questions.never_draft(sms["title"]) == questions.SIGNING  # consent: the applicant's own
    hear = a["info.howDidYouHearAboutUs"]
    assert hear["native"] == "radio" and hear["options"][:2] == ["Online Job Board", "Company Website"]
    assert a["public-site-address-us-state"]["options"][0] == "Alabama" and a["public-site-address-zip"]["key"] == "zip"
    dates = [q for x in "abcdefg" for q in by_id(x).values() if q["id"] == "info.dateAvailableToStart"]
    assert all(q["kind"] == "date" and q["title"].endswith("(MM/DD/YYYY)") for q in dates)
    assert b["btn-resume"]["required"]  # requireResume
    assert a["workHistory"]["native"] == "work" and a["workHistory"]["page"] == "workHistory"
    # identity lists show their labels, never the stored codes
    assert a["expandedIdentityQuestions.genderIdentity"]["options"][0] == "Agender"
    assert a["acknowledgements.ofccp.0"]["options"][1] == "I am not a protected veteran"
    assert "" not in a["acknowledgements.eeoGenderEthnicity.0"]["options"]  # the blank row is no choice


def test_sections_left_out_are_not_asked():
    f = by_id("f")  # no work history or education section
    assert "workHistory" not in f and "educationHistory" not in f
    assert "references" not in by_id("a") and by_id("b")["references"]["native"] == "references"


def test_screener_kinds_and_grading_never_read():
    data = tenant("g")
    got = [q for q in paylocity.from_definition(data) if q["page"] == "screener"]
    assert len(got) == len(data["screener"]["questions"])
    assert {q["kind"] for q in got} <= {"yesno", "choice", "text", "longtext", "multichoice"}
    # the answer is the applicant's truth: no option is pre-picked from isCorrect
    assert all(q.get("answer") is None for q in got)


def test_desired_pay_two_shapes():
    data = tenant("b")
    data["customJobApplication"]["desiredSalaryInputType"] = 1
    got = by_id_of(data)
    assert got["info.desiredSalaryType"]["native"] == "combo" and got["info.minimumDesiredSalary"]["kind"] == "number"
    data["customJobApplication"]["desiredSalaryInputType"] = 2
    got = by_id_of(data)
    assert "info.desiredSalaryDescription" in got and "info.minimumDesiredSalary" not in got


def by_id_of(data: dict) -> dict:
    return {q["id"]: q for q in paylocity.from_definition(data)}


def test_closed_wording():
    assert form.CLOSED.search("We're sorry, that job does not exist or is not currently active.")


# --- widgets, with fakes ---

class Options:
    def __init__(self, page, texts):
        self.page, self.texts = page, texts
        self.first = self

    def wait_for(self, timeout=None):
        if not self.texts:
            raise TimeoutError

    def all_inner_texts(self):
        return self.texts

    def nth(self, i):
        page, text = self.page, self.texts[i]

        class Option:
            def click(self):
                page.box.text = text
        return Option()


class ComboPage:
    def __init__(self, texts):
        self.texts, self.box = texts, None

    def locator(self, sel):
        assert sel == '[id="info.smsOptedIn__listbox"] [role=option]'
        return Options(self, self.texts)

    def wait_for_timeout(self, ms):
        pass


class Combo:
    def __init__(self, page, text="", covered=False):
        self.page, self.text, self.pressed, self.covered, self.clicked_by_script = page, text, [], covered, False
        page.box = self

    def inner_text(self):
        return self.text

    def click(self, timeout=None):
        if self.covered:  # a layer over the box takes the click
            raise TimeoutError

    def evaluate(self, js):
        self.clicked_by_script = True

    def get_attribute(self, name):
        return "info.smsOptedIn__listbox"

    def press(self, key):
        self.pressed.append(key)


def test_combo_picks_the_option_and_reads_it_back():
    page = ComboPage(["Yes", "No"])
    box = Combo(page)
    assert paylocity.put_combo(page, box, "no") == "ok" and box.text == "No"
    assert paylocity.put_combo(page, box, "No") == "ok"  # already chosen: not reopened


def test_combo_under_a_layer_opened_on_the_box_itself():
    page = ComboPage(["Yes", "No"])
    box = Combo(page, covered=True)
    assert paylocity.put_combo(page, box, "Yes") == "ok" and box.clicked_by_script


def test_combo_missing_option_or_list_asks():
    page = ComboPage(["Yes", "No"])
    box = Combo(page)
    assert paylocity.put_combo(page, box, "Maybe").startswith("ASK no option 'Maybe'") and box.pressed == ["Escape"]
    empty = ComboPage([])
    assert paylocity.put_combo(empty, Combo(empty), "Yes").startswith("ASK the list didn't open")


def test_work_dates_typed_month_year_or_left():
    assert paylocity.month_year("2023-02") == "02/2023" and paylocity.month_year("2023-02-15") == "02/2023"
    assert paylocity.month_year("2023") is None and paylocity.month_year(None) is None


class FillPage:
    """`present` asks the page which questions show; this one shows `shown`."""
    def __init__(self, shown):
        self.shown = shown

    def evaluate(self, js, qs):
        return [q["id"] for q in qs if q["id"] in self.shown]


def test_fill_box_on_another_step_is_later_and_never_typed():
    q = by_id("b")["acknowledgements.authorizedToWork"] | {"answer": "Yes"}
    assert paylocity.fill(FillPage(set()), q, None).startswith(questions.LATER)


def test_fill_references_files_and_history_rules():
    b = by_id("b")
    page = FillPage(set(b))
    assert paylocity.fill(page, b["references"] | {"answer": "x"}, None).startswith("ASK other people's details")
    assert paylocity.fill(page, b["btn-resume"] | {"answer": False}, "r.pdf") == "skipped - upload not approved"
    other = questions.question("upload", "Portfolio", "file", False, native="file") | {"answer": True}
    assert paylocity.fill(page, other, "r.pdf").startswith("ASK not the resume box")
    assert paylocity.fill(page, b["workHistory"] | {"answer": "No"}, None) == "skipped - user said no"


# --- closed: the apply page, a plain GET ---

APPLY = "https://recruiting.paylocity.com/Recruiting/Jobs/Apply/1000001"


def answer(monkeypatch, status=200, text="", headers=None, error=False):
    def get(url, **kw):
        assert url == APPLY and not kw.get("follow_redirects")  # the redirect itself says JobNotFound
        if error:
            raise httpx.ConnectError("down")
        return httpx.Response(status, text=text, headers=headers or {})
    monkeypatch.setattr(paylocity.httpx, "get", get)


def test_closed_off_paylocitys_own_redirect_or_a_page_without_its_form(monkeypatch):
    answer(monkeypatch, 302, headers={"location": "/Recruiting/Jobs/JobNotFound"})
    assert "does not exist or is not active" in paylocity.closed(APPLY)
    with pytest.raises(ValueError, match="does not exist"):
        paylocity.questions(APPLY)
    answer(monkeypatch, text="<html>no form</html>")
    assert paylocity.closed(APPLY).startswith("no form")


def test_form_present_is_open_else_cant_tell(monkeypatch):
    answer(monkeypatch, text='<script>window.pageData = {"customJobApplication": {"sections": []}};</script>')
    assert paylocity.closed(APPLY) is None and paylocity.questions(APPLY)[0]["id"] == "btn-resume"
    answer(monkeypatch, 500)
    assert paylocity.closed(APPLY).startswith("can't tell")
    answer(monkeypatch, error=True)
    assert paylocity.closed(APPLY).startswith("can't tell")


@pytest.mark.parametrize("text", ["Error uploading Resume File cannot be larger than 5MB.",
                                  "Error attaching Cover Letter Network Error", "File type .exe is not allowed.",
                                  "A maximum of 1 file(s) is allowed."])
def test_upload_error_words(text):
    assert paylocity.UPLOAD_ERRORS.search(text)


def test_resume_attached_but_not_read_is_no_upload_error():
    assert not paylocity.UPLOAD_ERRORS.search("Sorry, we cannot complete the application using your resume. "
                                              "A copy of the resume has been attached to your application.")


# --- the form, in headless Chrome ---

SITE = "recruiting.paylocity.com"


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
def at(chrome):
    """at(query) -> a page showing fixtures/paylocity/form.html as the apply page; nothing reaches the network."""
    context = chrome.new_context()
    asked = []

    def serve(route):
        u = urlsplit(route.request.url)
        asked.append(u.hostname)
        return route.fulfill(path=str(FIXTURES / "form.html")) if u.hostname == SITE else route.abort()

    context.route("**/*", serve)
    page = context.new_page()

    def go(query=""):
        page.goto(APPLY + query, wait_until="load")
        return page
    yield go
    assert set(asked) <= {SITE}, asked
    context.close()


ANSWERS = {"btn-resume": True, "info.firstName": "Test", "info.lastName": "Applicant", "info.email": "test@example.com",
           "info.cellPhone": "555-0100", "public-site-address-country": "United States",
           "public-site-address-address-1": "1 Main St", "public-site-address-city": "Springfield",
           "public-site-address-us-state": "Illinois", "public-site-address-zip": "62701",
           "info.haveYouWorkedWithUsBefore": "No", "info.howDidYouHearAboutUs": "Company Website",
           "info.dateAvailableToStart": "10/15/2026", "info.linkedIn": "https://www.linkedin.com/in/test",
           "info.skills": "Excel, Forklift", "acknowledgements.authorizedToWork": "Yes",
           "acknowledgements.eeoGenderEthnicity.0": "Female", "acknowledgements.eeoGenderEthnicity.1": "I do not wish to self-identify",
           "screener.1": "Yes", "screener.2": "Night", "screener.3": "Two years.\nDay shift."}


def answered(page):
    qs = paylocity.from_definition(page.evaluate("() => window.pageData"))
    for q in qs:
        q["answer"] = ANSWERS.get(q["id"])
    return qs


def resume(tmp_path):
    path = tmp_path / "Test_Applicant_Resume.pdf"
    path.write_bytes(b"%PDF-1.4\n%%EOF\n")
    return str(path)


def test_every_box_filled_and_read_back_off_the_page(at, tmp_path):
    page = at()
    qs = answered(page)
    assert {q["id"] for q in qs} - set(ANSWERS) == {"info.middleName", "info.preferredName", "public-site-address-county"}
    report, extra = form.fill_page(page, paylocity, qs, resume(tmp_path), None)
    assert dict(report) == {id: "ok" for id in ANSWERS}, report
    assert extra == []
    by = {q["id"]: q for q in qs}
    for id in ANSWERS:
        assert paylocity.holds(page, by[id]), id
    # Country shows over its box, the box itself stays empty
    assert page.locator('[id="public-site-address-country"]').input_value() == ""
    # what the page shows changed -> not held
    page.locator('[id="info.linkedIn"]').fill("")
    assert not paylocity.holds(page, by["info.linkedIn"])
    for id, other in (("public-site-address-country", "Canada"), ("info.haveYouWorkedWithUsBefore", "Yes"),
                      ("info.howDidYouHearAboutUs", "Online Job Board"), ("info.dateAvailableToStart", "10/16/2026"),
                      ("info.cellPhone", "555-0199"), ("info.skills", "Excel, Welding"),
                      ("acknowledgements.eeoGenderEthnicity.0", "Male"), ("screener.2", "Day"),
                      ("screener.3", "Three years.")):
        assert not paylocity.holds(page, by[id] | {"answer": other}), id
    assert not paylocity.holds(page, by["screener.1"] | {"title": "Do you have a forklift license?"})  # no such box
    assert not paylocity.holds(page, questions.question("workHistory", "Work", "yesno", False, native="work") | {"answer": "Yes"})


def test_upload_error_in_the_pages_own_words_fails(at, tmp_path):
    page = at("?upload=fail")
    q = next(q for q in answered(page) if q["id"] == "btn-resume")
    assert paylocity.fill(page, q, resume(tmp_path)) == \
        "FAIL the page says 'Error uploading Resume File cannot be larger than 5MB.' - choose the file again on the page"
    assert not paylocity.holds(page, q)


def test_upload_nothing_shown_asks(at, tmp_path, monkeypatch):
    monkeypatch.setattr(paylocity, "SHOWN_WAIT_MS", 1500)
    assert paylocity.put_file(at("?upload=never"), "btn-resume", resume(tmp_path)).startswith("ASK upload not confirmed")


def test_a_box_dropped_after_filling_is_filled_again(at, monkeypatch):
    page = at()
    qs = [q for q in answered(page) if q["id"] == "info.linkedIn"]
    calls = []
    real = paylocity.fill

    def fill_then_drop(page, q, file):
        calls.append(q["id"])
        got = real(page, q, file)
        if len(calls) == 1:  # the page empties it once, as Ashby's did
            page.locator('[id="info.linkedIn"]').fill("")
        return got
    monkeypatch.setattr(paylocity, "fill", fill_then_drop)
    report, _ = form.fill_page(page, paylocity, qs, None, None)
    assert report == [("info.linkedIn", "ok")] and len(calls) == 2
