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
    # taken down: 410 + the posting's own words (16 of 16, 2026-10-06) - said, never a crash
    monkeypatch.setattr(httpx, "get", lambda *a, **k: Got(410, "<h2>This position is no longer available.</h2>"))
    with pytest.raises(ValueError, match="no longer available"):
        jazzhr.questions(LINK)


def test_closed_reads_jazzhrs_own_answer_never_guesses(monkeypatch):
    answers = {LINK: Got(410, "<p>Hiring for this position has been put on hold at this time.</p>")}
    monkeypatch.setattr(httpx, "get", lambda url, **k: answers[url])
    assert "put on hold" in jazzhr.closed(LINK + "?utm_source=freehire.me")
    answers[LINK] = Got(200, (FIXTURES / "tenant-a.html").read_text())
    assert jazzhr.closed(LINK) is None
    answers[LINK] = Got(200, "<html><h1>Careers</h1></html>")
    assert jazzhr.closed(LINK).endswith("it may have closed")
    answers[LINK] = Got(503)
    assert jazzhr.closed(LINK).startswith("can't tell")

    def down(url, **k):
        raise httpx.ConnectError("no route")
    monkeypatch.setattr(httpx, "get", down)
    assert jazzhr.closed(LINK).startswith("can't tell")


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


class Words:
    def __init__(self, texts):
        self.texts = texts

    def all_inner_texts(self):
        return self.texts


class UploadPage:
    def __init__(self, link, error=(), limit="Attach resume as .pdf, .doc, .docx (limit 5MB) or Paste resume"):
        self.link, self.words = link, {jazzhr.PAGE_ERROR: list(error), jazzhr.UPLOAD_TEXT: [limit]}

    def wait_for_load_state(self, state, timeout):
        raise TimeoutError("still polling")  # never idle: the read decides

    def locator(self, selector):
        return self.link if selector == jazzhr.ATTACH else Words(self.words[selector])


def test_resume_upload_shows_the_attach_box_then_reads_the_file_back(tmp_path):
    resume = tmp_path / "Test_Resume.pdf"
    resume.write_bytes(b"%PDF-1.4 test")
    box = FileBox()
    link = Link(box)
    assert jazzhr.put_file(UploadPage(link), box, str(resume)) == "ok"
    assert link.clicked == 1 and box.name == "Test_Resume.pdf"
    # the box never took the file: the user checks it
    box.set_input_files = lambda path: None
    box.name = ""
    assert jazzhr.put_file(UploadPage(Link(box)), box, str(resume)).startswith("ASK upload not confirmed")


def test_resume_upload_fails_on_the_pages_own_words(tmp_path):
    resume, big = tmp_path / "Test_Resume.pdf", tmp_path / "Big_Resume.pdf"
    resume.write_bytes(b"%PDF-1.4 test")
    big.write_bytes(b"0" * (5 * 1024 * 1024 + 1))
    box = FileBox()
    said = jazzhr.put_file(UploadPage(Link(box), error=["Resume is required"]), box, str(resume))
    assert said == "FAIL the page says 'Resume is required' - check the resume box"
    assert "limit 5MB" in jazzhr.put_file(UploadPage(Link(box)), box, str(big))
    # no limit stated: nothing to hold the file to before Submit
    assert jazzhr.put_file(UploadPage(Link(box), limit="Attach resume"), box, str(big)) == "ok"


class Shown:
    """One box on a page for holds(): its value, the option text a dropdown shows, the file it holds."""
    def __init__(self, value="", text="", file=""):
        self.value, self.text, self.file = value, text, file

    def count(self):
        return 1

    def input_value(self):
        return self.value

    def evaluate(self, js):
        return self.file if "files" in js else [self.value, self.text]


class Ticks:
    def __init__(self, ticks):
        self.ticks = ticks

    def evaluate_all(self, js):
        return self.ticks


class HoldPage:
    def __init__(self, field, ticks=()):
        self.field, self.ticks = field, list(ticks)

    def locator(self, selector):
        return Ticks(self.ticks) if "checkbox" in selector else self

    @property
    def first(self):
        return self.field


def test_holds_reads_each_kind_as_the_page_shows_it():
    yn = questions.question("q", "Employed here?", "yesno", True, ["YES", "NO"], native="jazzhr:select") | {"answer": "No"}
    assert jazzhr.holds(HoldPage(Shown("NO", "NO")), yn)
    assert not jazzhr.holds(HoldPage(Shown("resumator_no_selection", "-- No answer --")), yn | {"answer": "No answer"})
    assert not jazzhr.holds(HoldPage(Shown("0", "No answer")), yn | {"answer": "No answer"})
    ticks = yn | {"native": "jazzhr:checkboxes", "answer": "Yes"}
    assert jazzhr.holds(HoldPage(Shown(), [["YES", True], ["NO", False]]), ticks)
    assert not jazzhr.holds(HoldPage(Shown(), [["YES", True], ["NO", True]]), ticks)
    assert not jazzhr.holds(HoldPage(Shown(), []), ticks)
    # a lone attestation-style box: ticked = yes, unticked = no
    lone = ticks | {"options": ["YES"]}
    assert jazzhr.holds(HoldPage(Shown(), [["YES", False]]), lone | {"answer": "No"})
    phone = questions.question("p", "Phone", "phone", True) | {"answer": "555-010-0100"}
    assert jazzhr.holds(HoldPage(Shown("(555) 010-0100")), phone)
    resume = questions.question("r", "Resume", "file", True) | {"answer": True}
    assert jazzhr.holds(HoldPage(Shown(file="A_Resume.pdf")), resume)
    assert not jazzhr.holds(HoldPage(Shown(file="")), resume)
