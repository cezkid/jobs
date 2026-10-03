"""Lever: link shapes, the saved /apply forms -> shared questions, each widget rule. Facts: app/docs/apply/lever.md."""
from pathlib import Path

import pytest

from apply import form, systems
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
    def __init__(self, boxes, upload="success"):
        self.by_name, self.upload = boxes, upload

    def locator(self, css):
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
