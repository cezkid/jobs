"""Lever: link shapes, the saved /apply forms -> shared questions, each widget rule. Facts: app/docs/apply/lever.md."""
from pathlib import Path

import pytest

from apply import browser, form, systems
from apply.questions import left_on_page
from apply.systems import lever

FIXTURES = Path(__file__).parent / "fixtures" / "lever"
ID = "1b2c3d4e-5f60-4718-9a0b-1c2d3e4f5a6b"
APPLY = f"https://jobs.lever.co/acme/{ID}/apply"


def read(tenant: str) -> dict:
    return {q["id"]: q for q in lever.from_page((FIXTURES / f"tenant-{tenant}.html").read_text())}


def card(qs: dict, title: str) -> dict:
    return next(q for q in qs.values() if q["title"].startswith(title))


# --- links ---

@pytest.mark.parametrize("url", [f"https://jobs.lever.co/acme/{ID}", f"https://jobs.lever.co/acme/{ID}?utm_source=freehire.me",
                                 f"https://jobs.lever.co/acme/{ID}/apply", f"https://jobs.lever.co/acme/{ID}/",
                                 f"https://jobs.lever.co/acme/{ID}/apply?lever-source=LinkedIn"])
def test_lever_link_plain_freehire_tail_or_form(url):
    assert lever.matches(url) and lever.application_url(url) == APPLY
    assert systems.for_url(url) is lever


def test_lever_eu_host_keeps_its_host():
    assert lever.application_url(f"https://jobs.eu.lever.co/acme/{ID}") == f"https://jobs.eu.lever.co/acme/{ID}/apply"


@pytest.mark.parametrize("url", ["https://jobs.lever.co/acme", "https://jobs.lever.co/acme/1b2c",
                                 f"https://www.example.com/careers/{ID}", f"https://jobs.lever.co.example.com/acme/{ID}"])
def test_not_a_lever_posting_refused(url):
    assert not lever.matches(url)
    with pytest.raises(ValueError):
        lever.application_url(url)


# --- the form, read off the saved pages ---

def test_lever_standard_boxes_keys_and_required_per_tenant():
    a, b = read("a"), read("b")
    assert (a["resume"]["kind"], a["resume"]["key"], a["resume"]["required"]) == ("file", "resume", True)
    assert (a["name"]["key"], a["email"]["kind"], a["location"]["kind"]) == ("name", "email", "location")
    assert not a["phone"]["required"] and b["phone"]["required"]  # Phone optional on tenant A only
    assert read("c")["location"]["required"] and not a["location"]["required"]
    assert [a[f"urls[{n}]"]["key"] for n in ("LinkedIn", "GitHub", "Portfolio", "Twitter", "Other")] == \
        ["linkedin", "github", "website", None, None]
    assert a["org"]["key"] is None
    assert "selectedLocation" not in a and "h-captcha-response" not in a  # Lever's own, the captcha


def test_lever_card_questions_from_their_json_not_the_page():
    a = read("a")
    legal = card(a, "Please state your full legal name")
    # the page labels a text card only "Type your response": the title comes from the card
    assert (legal["kind"], legal["key"], legal["required"]) == ("text", "legal_name", True)
    assert legal["id"].startswith("cards[") and legal["id"].endswith("][field0]")
    assert card(a, "Are you authorized to work")["kind"] == "yesno"
    assert card(a, "How did you hear")["kind"] == "choice" and "Referral" in card(a, "How did you hear")["options"]
    assert card(a, "Are you local to or willing to relocate")["native"] == "cards:dropdown"
    offices = card(a, "What office(s)")
    assert offices["kind"] == "multichoice" and not offices["required"] and len(offices["options"]) == 7
    assert card(a, "What full time job")["kind"] == "longtext"


def test_lever_home_address_cards_keyed_for_saved_address():
    c = read("c")
    assert [card(c, t)["key"] for t in ("Current Address (Line 1)", "City", "State", "Zip Code", "Address (Line2)")] == \
        ["street", "city", "state", "zip", None]
    assert card(c, "Preferred Name")["key"] == "preferred_name"


def test_lever_voluntary_questions_eeo_and_employer_survey():
    a, c = read("a"), read("c")
    assert a["eeo[gender]"]["kind"] == "choice" and a["eeo[race]"]["options"][0] == "Hispanic or Latino"
    assert not any(a[f"eeo[{n}]"]["required"] for n in ("gender", "race", "veteran", "disability"))
    # "I do not want to answer " on the page: options compared trimmed
    assert a["eeo[disability]"]["options"][-1] == "I do not want to answer"
    race = card(c, "I identify my race")
    assert race["kind"] == "multichoice" and race["native"] == "surveysResponses:multiple-select" and not race["required"]


def test_lever_signature_and_consent_are_the_applicants():
    a, d = read("a"), read("d")
    # the disability form's signature box is labelled plain "Name": never a name to fill
    assert a["eeo[disabilitySignature]"]["key"] is None and "signature" in a["eeo[disabilitySignature]"]["title"]
    assert d["consent[marketing]"]["title"] == lever.CONSENT and not d["consent[marketing]"]["required"]
    privacy = card(d, "Acme and its affiliates respect your privacy")
    assert privacy["required"] and privacy["options"] == ["I Accept"]
    for q in (a["eeo[disabilitySignature]"], d["consent[marketing]"], privacy):
        assert lever.fill(None, q | {"answer": "x"}, None).startswith("ASK yours to do on the page")


def test_lever_file_upload_card_is_a_file_box_never_the_resume():
    """1 of 21 open forms, 2026-10-05: lever.md "Kinds on real forms"."""
    got = lever.from_page((FIXTURES / "card-file.html").read_text())
    certs = next(q for q in got if q["native"] == "cards:file-upload")
    assert (certs["kind"], certs["key"], certs["required"]) == ("file", None, False)
    assert certs["id"].endswith("[field1]") and certs["title"].startswith("Please upload a copy of your certification")

    class Page:
        locator = lambda self, selector: type("Box", (), {"count": lambda self: 1, "first": None})()
    assert lever.fill(Page(), certs | {"answer": True}, "/tmp/Jane_Doe_Resume.pdf").startswith("ASK not the resume box")


def test_lever_broken_card_json_falls_back_to_the_page():
    page = (FIXTURES / "tenant-b.html").read_text().replace("Salary Expectations&quot;", "Salary Expectations")
    got = lever.from_page(page)
    salary = next(q for q in got if q["id"].startswith("cards[") and q["native"] == "text")
    # the label div above the box holds the question; its accessible name is only the placeholder
    assert (salary["title"], salary["required"]) == ("What are your salary expectations?", True)


def test_closed_lever_posting_is_recognised():
    said = "Sorry, we couldn't find anything here The job posting you're looking for might have closed, or it has been removed."
    assert form.CLOSED.search(said) and form.CLOSED.search(said.replace("'", "’"))


# --- widgets, with fakes ---

class Box:
    """One <input> / <select> / <textarea>, as Playwright shows it."""
    def __init__(self, type="text", value="", options=(), checked=False):
        self.type, self.value, self.options, self.checked, self.files = type, value, list(options), checked, []

    def get_attribute(self, name):
        return self.value if name == "value" else None

    def evaluate(self, js, *args):
        if "tagName" in js:
            return self.type
        if "files[0]" in js:
            return self.files[0] if self.files else ""
        if "e.click()" in js:
            for other in self.group if self.type == "radio" else [self]:
                other.checked = other is self if self.type == "radio" else not other.checked
            return None
        if "e.checked" in js:
            return self.checked
        if "selectedOptions" in js:
            return [self.value] if self.value else []
        if "e.options" in js:
            return ["Select ...", *self.options]
        return None  # change + blur

    def fill(self, v):
        self.value = v

    def input_value(self):
        return self.value

    def select_option(self, label):
        self.value = label[0]

    def scroll_into_view_if_needed(self):
        pass

    def set_input_files(self, path):
        self.files = [Path(path).name]


class Boxes:
    def __init__(self, members):
        self.members = members
        self.first = members[0] if members else None

    def count(self):
        return len(self.members)

    def all(self):
        return self.members


class Shown:
    def __init__(self, n):
        self.n = n

    def filter(self, visible=None):
        return self

    def count(self):
        return self.n

    @property
    def first(self):
        return self

    def wait_for(self, timeout=None):
        if not self.n:
            raise TimeoutError


class Page:
    def __init__(self, boxes, upload="success", picked=""):
        self.by_name, self.upload, self.picked = boxes, upload, picked

    def locator(self, css):
        if css == "#selected-location":
            return Box("hidden", self.picked)
        if "resume-upload-success" in css:
            return Shown(int(self.upload in ("success", "failure")))
        if "resume-upload-failure" in css:
            return Shown(int(self.upload == "failure"))
        name = css.split('[name="', 1)[1].split('"]', 1)[0]
        return Boxes(self.by_name.get(name, []))


def radios(*values, type="radio"):
    group = [Box(type, v) for v in values]
    for b in group:
        b.group = group
    return group


def q(id, kind, answer, options=(), key=None, title="Question"):
    return {"id": id, "title": title, "kind": kind, "key": key, "answer": answer, "options": list(options), "native": None}


def test_lever_text_select_and_yes_no_dropdown():
    name, sel = Box(), Box("select", options=["Yes", "No"])
    page = Page({"name": [name], "cards[x][field0]": [sel]})
    assert lever.fill(page, q("name", "text", "Test Applicant", key="name"), None) == "ok" and name.value == "Test Applicant"
    assert lever.fill(page, q("cards[x][field0]", "yesno", True), None) == "ok" and sel.value == "Yes"
    assert lever.fill(page, q("cards[x][field0]", "choice", "Maybe"), None).startswith("ASK no option 'Maybe'")


def test_lever_radio_picks_exact_value_and_checkboxes_tick_each():
    group = radios("Yes", "No", "Other ")
    ticks = radios("Boston, MA", "Dallas, Texas", "International", type="checkbox")
    page = Page({"r": group, "c": ticks})
    assert lever.fill(page, q("r", "choice", "Other"), None) == "ok"  # page value "Other " trimmed
    assert [b.checked for b in group] == [False, False, True]
    assert lever.fill(page, q("c", "multichoice", ["Boston, MA", "International"]), None) == "ok"
    assert [b.checked for b in ticks] == [True, False, True]
    assert lever.fill(page, q("r", "choice", "Perhaps"), None).startswith("ASK no option 'Perhaps'")


def test_lever_resume_upload_waits_for_its_verdict():
    for state, want in (("success", "ok"), ("failure", "ASK Lever says it couldn't take the resume"),
                        ("none", "ASK upload not confirmed")):
        box = Box("file")
        got = lever.fill(Page({"resume": [box]}, upload=state), q("resume", "file", True, key="resume"), "/tmp/Test_Resume.pdf")
        assert got.startswith(want), state
    assert lever.fill(Page({"resume": [Box("file")]}), q("resume", "file", False, key="resume"), "/tmp/x.pdf") == \
        "skipped - upload not approved"


def test_lever_box_missing_from_page():
    page = Page({})
    assert lever.fill(page, q("cards[x][field3]", "text", "a"), None) == "FAIL question not on page"
    # the disability signature shows only once Disability status is chosen
    assert lever.fill(page, q("eeo[veteran]", "choice", "a"), None).startswith("skipped")


# --- read-back: the answer as the page shows it, never the filler's word ---

def test_lever_holds_reads_each_kind_off_the_box():
    name, phone, sel = Box(value="Test Applicant"), Box(value="(555) 010-0"), Box("select", value="Yes", options=["Yes", "No"])
    page = Page({"name": [name], "phone": [phone], "s": [sel]})
    assert lever.holds(page, q("name", "text", "Test Applicant"))
    assert not lever.holds(page, q("name", "text", "Someone Else"))
    assert lever.holds(page, q("phone", "phone", "555-0100"))  # by digits: the page may format it
    assert lever.holds(page, q("s", "yesno", True)) and not lever.holds(page, q("s", "yesno", "No"))
    assert not lever.holds(page, q("gone", "text", "a"))  # a box gone = not shown


def test_lever_holds_ticks_by_each_options_checked_state():
    group, ticks = radios("Yes", "No"), radios("Boston, MA", "Dallas, Texas", "International", type="checkbox")
    page = Page({"r": group, "c": ticks})
    assert not lever.holds(page, q("r", "choice", "No"))  # nothing ticked
    group[1].checked = True
    assert lever.holds(page, q("r", "choice", "No")) and not lever.holds(page, q("r", "choice", "Yes"))
    ticks[0].checked = ticks[2].checked = True
    assert lever.holds(page, q("c", "multichoice", ["Boston, MA", "International"]))
    assert not lever.holds(page, q("c", "multichoice", ["Boston, MA"]))  # an extra tick is not this answer


def test_lever_location_holds_only_with_lever_own_pick_and_the_town_shown():
    box = Box(value="Springfield, Illinois, United States")
    answer = q("location", "location", "Springfield, IL")
    assert lever.holds(Page({"location": [box]}, picked='{"name": "Springfield"}'), answer)
    assert not lever.holds(Page({"location": [box]}, picked=""), answer)  # typed, never picked
    assert not lever.holds(Page({"location": [Box(value="Dallas, Texas")]}, picked="x"), answer)


# --- fill twice on the saved pages in real Chrome: a refill never unticks, every answer reads back ---

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
def saved_page(chrome):
    """A saved tenant page in headless Chrome; every request it makes refused (the pages load nothing)."""
    context = chrome.new_context()
    context.route("**/*", lambda route: route.fulfill(status=404, body=""))
    pg = context.new_page()
    pg.set_default_timeout(3000)  # a box the filler can't reach fails fast

    def at(tenant):
        pg.set_content((FIXTURES / f"tenant-{tenant}.html").read_text())
        return pg
    yield at
    context.close()


def shown(page) -> list:
    return page.eval_on_selector_all(
        "#application-form input:not([type=hidden]), #application-form textarea, #application-form select",
        "es => es.map(e => e.matches('input[type=radio], input[type=checkbox]') ? e.checked : e.value)")


def synthetic(question: dict) -> dict:
    o = question["options"]
    answer = {"email": "test@example.com", "phone": "555-0100", "url": "https://example.com/test",
              "longtext": "Their own words.", "yesno": "Yes", "choice": o[0] if o else None, "multichoice": o[:2]}
    return question | {"answer": answer.get(question["kind"], "Test Applicant")}


@pytest.mark.parametrize("tenant", "abcd")
def test_lever_fill_twice_same_state_and_every_answer_reads_back(saved_page, tenant):
    page = saved_page(tenant)
    qs = [synthetic(x) for x in read(tenant).values() if x["kind"] not in ("file", "location")]
    first = [lever.fill(page, x, None) for x in qs]
    filled = [x for x, got in zip(qs, first) if got == "ok"]
    assert [got for got in first if got != "ok"] == [left_on_page(x) for x, got in zip(qs, first) if got != "ok"]
    assert {x["kind"] for x in filled} >= {"text", "yesno"}
    once = shown(page)
    assert [lever.fill(page, x, None) for x in qs] == first
    assert shown(page) == once
    assert [x["id"] for x in filled if not lever.holds(page, x)] == []


def test_lever_dropped_answers_read_as_dropped_on_a_saved_page(saved_page):
    page = saved_page("a")
    qs = {x["kind"]: synthetic(x) for x in reversed(read("a").values()) if x["kind"] in ("text", "yesno", "multichoice")}
    assert [lever.fill(page, x, None) for x in qs.values()] == ["ok"] * 3
    page.evaluate("""() => document.querySelectorAll('#application-form input, #application-form select').forEach(e => {
        if (e.type === 'checkbox' || e.type === 'radio') e.checked = false; else if (e.type !== 'hidden') e.value = ''; })""")
    assert [x["kind"] for x in qs.values() if lever.holds(page, x)] == []


def test_lever_location_on_a_saved_page_needs_lever_own_pick(saved_page):
    page = saved_page("a")
    answer = synthetic(read("a")["location"]) | {"answer": "Springfield, IL"}
    page.fill("#location-input", "Springfield, Illinois, United States")
    assert not lever.holds(page, answer)  # typed, no place picked from Lever's list
    page.evaluate("() => { document.getElementById('selected-location').value = '{\"name\": \"Springfield\"}'; }")
    assert lever.holds(page, answer)
