"""JazzHR: link shapes, saved forms (anonymised, app/tests/fixtures/jazzhr) -> questions, each widget rule."""
from pathlib import Path

import httpx
import pytest

from apply import questions, systems
from apply.systems import jazzhr

FIXTURES = Path(__file__).parent / "fixtures" / "jazzhr"
LINK = "https://acme.applytojob.com/apply/AbCdE00001/Test-Role"


def form(tenant: str) -> dict:
    return {q["id"]: q for q in jazzhr.from_html((FIXTURES / f"tenant-{tenant}.html").read_text())}


# --- links ---

def test_links_freehire_lists_land_on_the_posting_form():
    assert systems.for_url(LINK + "?utm_source=freehire.me") is jazzhr
    assert jazzhr.application_url(LINK + "?utm_source=freehire.me") == LINK
    assert jazzhr.parse_url(" " + LINK + " ") == ("acme", "AbCdE00001")
    assert jazzhr.application_url("https://acme.applytojob.com/apply/AbCdE00001") == "https://acme.applytojob.com/apply/AbCdE00001"


def test_other_links_refused():
    for url in ("https://jobs.lever.co/acme/1b2c", "https://acme.applytojob.com/apply/jobs",
                "https://acme.applytojob.com/apply/job/AbCdE00001/stage-one", "https://applytojob.com.example.com/apply/AbCdE00001"):
        assert not jazzhr.matches(url), url
    with pytest.raises(ValueError):
        jazzhr.parse_url("https://jobs.lever.co/acme/1b2c")


# --- saved forms -> questions ---

def test_contact_address_resume_read_with_keys_and_required():
    a = form("a")
    got = {id: (q["kind"], q["key"], q["required"]) for id, q in a.items() if q["key"]}
    assert got == {"resumator-firstname-value": ("text", "first_name", True), "resumator-lastname-value": ("text", "last_name", True),
                   "resumator-email-value": ("email", "email", True), "resumator-phone-value": ("phone", "phone", True),
                   "resumator-address-value": ("text", "street", True), "resumator-city-value": ("text", "city", True),
                   "resumator-state-value": ("text", "state", True), "resumator-postal-value": ("text", "zip", True),
                   "resumator-resume-value": ("file", "resume", True)}
    # City / State / Postal have only a placeholder; the paste-in box + script-only box are no questions
    assert [a[f"resumator-{f}-value"]["title"] for f in ("city", "state", "postal")] == ["City", "State/Province", "Postal"]
    assert not {"resumator-resumetext-value", "resumator-xml-value", "resumator-job-value"} & set(a)
    assert all(q.get("page") is None for q in a.values())
    # Address optional on tenant D: its three placeholder boxes follow the one label
    assert not any(form("d")[f"resumator-{f}-value"]["required"] for f in ("address", "city", "state", "postal"))


def test_employer_questions_kinds_and_options_without_the_no_answer_option():
    a = form("a")
    hear = a["resumator-questionnaire-q1437337"]
    assert hear["kind"] == "choice" and hear["required"] and "-- No answer --" not in hear["options"]
    assert a["resumator-questionnaire-q1519771"]["kind"] == "yesno"
    assert a["resumator-questionnaire-q2330229"]["kind"] == "longtext" and not a["resumator-questionnaire-q2330229"]["required"]
    assert a["resumator-salary-value"]["title"] == "Desired salary" and a["resumator-salary-value"]["kind"] == "text"
    # upper-case YES / NO is still a yes/no
    employed = form("b")["resumator-questionnaire-q1474074"]
    assert (employed["kind"], employed["options"]) == ("yesno", ["YES", "NO"])
    # work authorization asked in a free-text box (tenant C)
    assert form("c")["resumator-questionnaire-q2791419"]["kind"] == "longtext"


def test_checkbox_questions_one_each_attestation_left_to_the_applicant():
    b = form("b")
    yn = b["resumator-questionnaire-q1474076"]
    assert (yn["kind"], yn["options"], yn["native"], yn["required"]) == ("yesno", ["YES", "NO"], "jazzhr:checkboxes", True)
    oath = b["resumator-questionnaire-q1474070"]
    assert oath["options"] == ["YES"] and questions.signs(oath["title"])
    assert not any(id.startswith("resumator-checkbox-") for id in b)


def test_system_screening_fields_and_date():
    d = form("d")
    citizen = d["resumator-citizen-value"]
    assert citizen["kind"] == "choice" and citizen["options"][0] == "I am a U.S. Citizen/Permanent Resident"
    assert "No answer" not in citizen["options"]
    assert d["resumator-over18-value"]["kind"] == "yesno"
    start = d["resumator-start-value"]
    assert (start["kind"], start["native"]) == ("date", "jazzhr:date")


def test_eeo_questions_are_voluntary_never_drafted():
    a = form("a")
    drafted = {x["id"]: x for x in questions.draft(list(a.values()), {"name": "Ada Lovelace", "email": "a@example.com"})}
    for id in ("resumator-eeo_gender-value", "resumator-eeo_race-value"):
        assert drafted[id]["answer"] is None and questions.YOURS in drafted[id]["source"]
    assert "Decline to answer" not in a["resumator-eeo_gender-value"]["options"]


# --- closed ---

class Got:
    def __init__(self, status, text=""):
        self.status_code, self.text = status, text

    def raise_for_status(self):
        pass


def test_closed_or_unknown_posting_says_so(monkeypatch):
    # unknown posting id: 404 + the careers page, no form (2026-10-03)
    monkeypatch.setattr(httpx, "get", lambda *a, **k: Got(404))
    with pytest.raises(ValueError, match="closed"):
        jazzhr.questions(LINK)
    monkeypatch.setattr(httpx, "get", lambda *a, **k: Got(200, "<html><h1>Careers</h1></html>"))
    with pytest.raises(ValueError, match="closed"):
        jazzhr.questions(LINK)


# --- widgets, with fakes ---

class Select:
    def __init__(self, options):
        self.options, self.value = options, options[0][0]

    def evaluate(self, js):
        return self.options if "options" in js else self.value

    def select_option(self, value):
        self.value = value


def test_select_by_option_text_any_case_never_the_no_answer():
    field = Select([["resumator_no_selection", "-- No answer --"], ["YES", "YES"], ["NO", "NO"]])
    assert jazzhr.put_select(field, "No", "yesno") == "ok" and field.value == "NO"
    assert jazzhr.put_select(field, "true", "yesno") == "ok" and field.value == "YES"
    field = Select([["0", "No answer"], ["1", "Yes"], ["2", "No"]])
    assert jazzhr.put_select(field, "No answer", "choice").startswith("ASK no option") and field.value == "0"
    assert jazzhr.put_select(field, "Maybe", "choice") == "ASK no option 'Maybe'; offered: Yes, No"


class Box:
    def __init__(self, value):
        self.value, self.checked, self.clicks = value, False, 0

    def get_attribute(self, name):
        return self.value

    def is_checked(self):
        return self.checked

    def evaluate(self, js):
        self.clicks += 1
        self.checked = not self.checked


class Boxes:
    def __init__(self, boxes):
        self.boxes = boxes

    def all(self):
        return self.boxes


class TickPage:
    def __init__(self, values):
        self.boxes = [Box(v) for v in values]

    def locator(self, selector):
        return Boxes(self.boxes)


def test_yes_no_as_two_checkboxes_ticks_one_only():
    page = TickPage(["YES", "NO"])
    q = questions.question("resumator-questionnaire-q1", "Do you live near?", "yesno", True, ["YES", "NO"], native="jazzhr:checkboxes")
    assert jazzhr.put_ticks(page, q | {"answer": "Yes"}) == "ok"
    assert [b.checked for b in page.boxes] == [True, False]
    assert jazzhr.put_ticks(page, q | {"answer": "No"}) == "ok"
    assert [b.checked for b in page.boxes] == [False, True]
    many = questions.question("resumator-questionnaire-q2", "Shifts?", "multichoice", False, ["Days", "Nights"], native="jazzhr:checkboxes")
    page = TickPage(["Days", "Nights"])
    assert jazzhr.put_ticks(page, many | {"answer": ["days", "Nights"]}) == "ok" and all(b.checked for b in page.boxes)
    assert jazzhr.put_ticks(page, many | {"answer": ["Weekends"]}).startswith("ASK no option")


def test_attestation_never_ticked():
    oath = form("b")["resumator-questionnaire-q1474070"] | {"answer": "Yes"}
    assert jazzhr.fill(object(), oath, None).startswith("ASK yours to do on the page")


class Text:
    def __init__(self, shows=None):
        self.value, self.keys, self.shows = "", [], shows

    def fill(self, v):
        self.value = v

    def press(self, key):
        self.keys.append(key)

    def evaluate(self, js):
        pass

    def input_value(self):
        return self.shows if self.shows is not None else self.value


def test_text_read_back_date_shuts_its_picker():
    field = Text()
    assert jazzhr.put_text(field, "2026-11-02", "date") == "ok" and field.keys == ["Escape"]
    assert jazzhr.put_text(Text(shows="(555) 010-0100"), "555-010-0100", "phone") == "ok"
    assert jazzhr.put_text(Text(shows=""), "Test", "text") == "FAIL shows ''"


class FileBox:
    def __init__(self):
        self.visible, self.name = False, ""

    def is_visible(self):
        return self.visible

    def set_input_files(self, path):
        self.name = Path(path).name

    def evaluate(self, js):
        return self.name


class Link:
    def __init__(self, box):
        self.box, self.first, self.clicked = box, self, 0

    def count(self):
        return 1

    def is_visible(self):
        return True

    def click(self):
        self.clicked += 1
        self.box.visible = True


def test_resume_upload_shows_the_attach_box_then_reads_the_file_back(tmp_path):
    box = FileBox()
    link = Link(box)
    page = type("P", (), {"locator": lambda self, s: link})()
    assert jazzhr.put_file(page, box, str(tmp_path / "Test_Resume.pdf")) == "ok"
    assert link.clicked == 1 and box.name == "Test_Resume.pdf"
