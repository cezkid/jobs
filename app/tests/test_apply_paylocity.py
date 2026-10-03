"""Paylocity: link shapes, the form definition in the apply page -> shared questions, each widget
rule against small fakes. Fixtures = 7 tenants' anonymised definitions (app/tests/fixtures/paylocity/,
measured 2026-10-03); facts in app/docs/apply/paylocity.md."""
import json
from pathlib import Path

import pytest

from apply import form, questions, systems
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
