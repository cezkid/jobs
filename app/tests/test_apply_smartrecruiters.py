"""SmartRecruiters: link shapes, the contact + resume page read off a saved snapshot (tenant A,
anonymised), the Spark widget rules with fakes, closed from the posting record, and every box filled +
read back on a hand-built page in headless Chrome (fixtures/smartrecruiters/form.html). Facts: app/docs/apply/smartrecruiters.md."""
import json
from pathlib import Path
from urllib.parse import urlsplit

import pytest

from apply import browser, form, questions, systems
from apply.systems import smartrecruiters as sr

FIXTURES = Path(__file__).parent / "fixtures" / "smartrecruiters"
POSTING = "https://jobs.smartrecruiters.com/acme/744000000000001-example-job?utm_source=freehire.me"
UUID = "00000000-0000-4000-a000-000000000001"
FORM = f"https://jobs.smartrecruiters.com/oneclick-ui/company/acme/publication/{UUID}?dcr_ci=acme"
SITE = "jobs.smartrecruiters.com"


def snapshot(name: str) -> dict:
    """A saved snapshot, trimmed to what was measured: the rest of dom.snapshot's fields defaulted."""
    snap = json.loads((FIXTURES / name).read_text())
    base = {"password": False, "autocomplete": "", "options": [], "tag": "input"}
    return {"captcha": [], "blocked_frames": [], "not_readable": [], **snap,
            "controls": [{**base, **c} for c in snap["controls"]]}


@pytest.mark.parametrize("link", [POSTING, "https://jobs.smartrecruiters.com/acme/744000000000001",
                                  "https://jobs.smartrecruiters.com/acme/744000000000001-example-job/", FORM])
def test_posting_and_form_links_are_smartrecruiters(link):
    assert systems.for_url(link) is sr


@pytest.mark.parametrize("link", ["https://boards.greenhouse.io/acme/jobs/123",
                                  "https://jobs.smartrecruiters.com/acme",
                                  "https://www.smartrecruiters.com/acme/744000000000001"])
def test_other_links_refused(link):
    assert not sr.matches(link)


def test_application_url_is_the_posting_with_oga_and_the_form_app_as_is():
    assert sr.application_url(POSTING) == "https://jobs.smartrecruiters.com/acme/744000000000001?oga=true"
    assert sr.application_url(FORM) == FORM
    assert sr.parse_url(FORM) == ("acme", UUID)


def test_tab_found_by_posting_id_or_its_form_app(monkeypatch):
    monkeypatch.setattr(sr, "record", lambda url: {"uuid": UUID, "active": True})
    assert sr.on_tab(POSTING, "https://jobs.smartrecruiters.com/acme/744000000000001?oga=true")
    assert sr.on_tab(POSTING, FORM)
    other = "https://jobs.smartrecruiters.com/oneclick-ui/company/acme/publication/00000000-0000-4000-a000-000000000002"
    assert not sr.on_tab(POSTING, other)
    assert not sr.on_tab(POSTING, "https://boards.greenhouse.io/acme/jobs/744000000000001")


def test_inactive_posting_is_closed_before_any_browser(monkeypatch):
    monkeypatch.setattr(sr, "record", lambda url: {"uuid": UUID, "active": False})
    with pytest.raises(ValueError, match="closed"):
        sr.questions(POSTING)
    assert not sr.is_closed(FORM)  # the form app link alone carries no record


def test_page_one_read_off_the_snapshot():
    got = sr.from_snapshot(snapshot("page1-tenant-a.json"))
    by = {q["title"]: q for q in got}
    assert got[0]["id"] == sr.RESUME and got[0]["kind"] == "file" and got[0]["key"] == "resume"
    assert {q["page"] for q in got} == {sr.PAGE_ONE}
    # no photo slot, no parsing upload, no phone-country search box
    assert not [t for t in by if "profile image" in t.casefold() or "choose a file" in t.casefold()]
    assert "Search by country/region or code" not in by
    assert by["City"]["kind"] == "location" and by["City"]["key"] == "location" and by["City"]["required"]
    country = next(q for q in got if q["id"] == sr.COUNTRY)
    assert country["kind"] == "choice"
    assert by["Email"]["kind"] == "email" and by["Phone number"]["kind"] == "phone"
    assert by["Let the company know about your interest working there"]["kind"] == "longtext"
    assert by["First name"]["required"] and not by["LinkedIn"]["required"]
    assert set(q["kind"] for q in got) <= set(questions.KINDS)


def test_a_later_step_is_named_screening():
    snap = snapshot("page1-tenant-a.json")
    snap["controls"] = [c for c in snap["controls"] if c["id"] != "first-name-input"]
    got = sr.from_snapshot(snap)
    assert sr.RESUME not in [q["id"] for q in got]
    assert {q["page"] for q in got} == {sr.PAGE_LATER}


class Page:
    def __init__(self, button=None, first_name=True):
        self.button, self.first_name = button, first_name

    def wait_for_timeout(self, ms):
        pass

    def get_by_role(self, role, name):
        return Found(self.button)

    def evaluate_handle(self, js):
        return Handle()

    def locator(self, selector):
        return Found(self if self.first_name else None)


class Found:
    def __init__(self, el):
        self.el = el
        self.first = el or self  # an empty locator still answers count()

    def count(self):
        return int(self.el is not None)


class Handle:
    def as_element(self):
        return None


class Widget:
    """A Spark list: its options, the pick, every option clicked."""
    def __init__(self, options, value=""):
        self.options, self.value, self.clicked, self.opened = options, value, [], False

    def count(self):
        return 1

    def evaluate(self, js, pick):
        if pick is not None:
            self.clicked.append(pick)
            self.value = self.options[pick]["value"]
        return {"value": self.value, "options": self.options}

    def focus(self):
        self.opened = True


PLACES = [{"value": "US_NJ_CITY_newark", "label": "Newark, NJ, US"},
          {"value": "US_NY_CITY_new_york_city", "label": "New York, NY, US"}]


def test_choose_picks_the_option_by_its_label_never_the_first():
    box = Widget(PLACES)
    assert sr.choose(Page(), box, "New York") == ("New York, NY, US", [p["label"] for p in PLACES])
    assert box.clicked == [1]


def test_choose_picks_nothing_when_no_label_fits():
    box = Widget(PLACES)
    assert sr.choose(Page(), box, "Boston")[0] is None and box.clicked == []


def test_phone_country_already_set_is_left_as_it_is():
    button = Widget([{"value": "CA", "label": "Canada"}, {"value": "US", "label": "United States"}], value="US")
    assert sr.put_country(Page(button), "United States") == "ok"
    assert not button.opened and button.clicked == []


def test_boxes_off_this_step_are_later():
    assert sr.put_country(Page(None), "United States").startswith(questions.LATER)
    assert sr.put_file(Page(first_name=False), "/tmp/r.pdf").startswith(questions.LATER)
    assert sr.put_file(Page(), "/tmp/r.pdf").startswith("ASK")


def test_resume_never_uploaded_without_the_users_yes():
    q = {"id": sr.RESUME, "kind": "file", "answer": None}
    assert sr.fill(Page(), q, "/tmp/r.pdf") == "skipped - upload not approved"


def test_closed_from_the_record_or_cant_tell(monkeypatch):
    monkeypatch.setattr(sr, "record", lambda url: {"uuid": UUID, "active": False})
    assert "expired" in sr.closed(POSTING)
    monkeypatch.setattr(sr, "record", lambda url: {"uuid": UUID, "active": True})
    assert sr.closed(POSTING) is None
    monkeypatch.setattr(sr, "record", lambda url: None)
    assert sr.closed(POSTING).startswith("can't tell")
    assert sr.closed(FORM).startswith("can't tell")  # no posting id, no record


@pytest.mark.parametrize("text", ["Sorry, this job has expired", "This job ad has expired Find more job offers at"])
def test_expired_words_read_closed(text):
    assert form.CLOSED.search(text)


@pytest.mark.parametrize("text", ["Due to inactivity, the form has been closed to protect your data.",
                                  "Your authentication code expired. Please click the button below"])
def test_timed_out_session_and_code_are_not_a_closed_posting(text):
    assert not form.CLOSED.search(text)


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
    """at(query) -> a page showing fixtures/smartrecruiters/form.html as the form app; nothing reaches the network."""
    context = chrome.new_context()
    asked = []

    def serve(route):
        u = urlsplit(route.request.url)
        asked.append(u.hostname)
        return route.fulfill(path=str(FIXTURES / "form.html")) if u.hostname == SITE else route.abort()

    context.route("**/*", serve)
    page = context.new_page()

    def go(query=""):
        page.goto(f"https://{SITE}/oneclick-ui/company/acme/publication/{UUID}{query}", wait_until="load")
        return page
    yield go
    assert set(asked) <= {SITE}, asked
    context.close()


ANSWERS = {"First name": "Test", "Last name": "Applicant", "Email": "test@example.com",
           "Confirm your email": "test@example.com", "City": "New York, NY, US", "Phone number": "5550100",
           "LinkedIn": "https://www.linkedin.com/in/test", "Website": "https://example.com",
           "Let the company know about your interest working there": "Hello.\nTwo lines."}


def answered(page, country="Canada"):
    qs = sr.read(page)
    for q in qs:
        q["answer"] = True if q["id"] == sr.RESUME else country if q["id"] == sr.COUNTRY else ANSWERS[q["title"]]
    return qs


def resume(tmp_path):
    path = tmp_path / "Test_Applicant_Resume.pdf"
    path.write_bytes(b"%PDF-1.4\n%%EOF\n")
    return str(path)


def test_every_box_filled_and_read_back_off_the_page(at, tmp_path):
    page = at()
    qs = answered(page)
    report, extra = form.fill_page(page, sr, qs, resume(tmp_path), None)
    assert dict(report) == {q["id"]: "ok" for q in qs}, report
    assert extra == []
    by = {q["title"]: q for q in qs}
    for q in qs:
        assert sr.holds(page, q), q["title"]
    # the resume went to the field, never the parsing box above the name (it fills the boxes itself)
    assert page.evaluate("() => document.getElementById('parsing').shadowRoot.getElementById('file-input').files.length") == 0
    assert sr.country_shown(page.get_by_role("combobox", name="Country code").first) == "Canada"
    assert page.locator("#spl-form-element_10").input_value() == "New York, NY, US"
    # what the page shows changed -> not held
    page.locator("#linkedin-input").fill("")
    assert not sr.holds(page, by["LinkedIn"])
    assert not sr.holds(page, by["City"] | {"answer": "Newark, NJ, US"})
    assert not sr.holds(page, next(q for q in qs if q["id"] == sr.COUNTRY) | {"answer": "Mexico"})
    assert not sr.holds(page, by["Email"] | {"title": "Personal email"})  # another question under that box


def test_country_already_shown_is_left_and_held(at):
    page = at()
    q = next(q for q in sr.read(page) if q["id"] == sr.COUNTRY) | {"answer": "United States"}
    assert sr.fill(page, q, None) == "ok" and sr.holds(page, q)


def test_upload_error_in_the_pages_own_words_fails(at, tmp_path):
    page = at("?upload=fail")
    got = sr.put_file(page, resume(tmp_path))
    assert got == "FAIL the page says 'Cannot upload resume. Please try again in a while.' - choose the file again " \
                  "on the page, or check the Resume box"
    assert not sr.holds(page, {"id": sr.RESUME, "kind": "file", "answer": True})


def test_upload_nothing_shown_asks(at, tmp_path, monkeypatch):
    monkeypatch.setattr(sr, "SHOWN_WAIT_MS", 1500)
    assert sr.put_file(at("?upload=never"), resume(tmp_path)).startswith("ASK upload not confirmed")


def test_a_box_dropped_after_filling_is_filled_again(at, tmp_path, monkeypatch):
    page = at()
    qs = [q for q in answered(page) if q["title"] == "LinkedIn"]
    calls = []
    real = sr.fill

    def fill_then_drop(page, q, file):
        calls.append(q["id"])
        got = real(page, q, file)
        if len(calls) == 1:  # the page empties it once, as Ashby's did
            page.locator("#linkedin-input").fill("")
        return got
    monkeypatch.setattr(sr, "fill", fill_then_drop)
    report, _ = form.fill_page(page, sr, qs, None, None)
    assert report == [(qs[0]["id"], "ok")] and len(calls) == 2
