"""BambooHR: link shapes, saved form definitions (anonymised, app/tests/fixtures/bamboohr) -> questions, each widget rule,
the hand-built form filled in the window as through Playwright."""
import json
from pathlib import Path

import httpx
import pytest
from test_apply_in_window import BAMBOOHR_PATH, both, playwright_chrome, site, tab  # noqa: F401 - fixtures

from apply import form as fill_form  # form() below is a tenant's questions
from apply import questions, systems
from apply.systems import bamboohr

FIXTURES = Path(__file__).parent / "fixtures" / "bamboohr"
LINK = "https://acme.bamboohr.com/careers/101"


def detail(tenant: str) -> dict:
    return json.loads((FIXTURES / f"tenant-{tenant}.json").read_text())


def form(tenant: str) -> dict:
    return {q["id"]: q for q in bamboohr.from_detail(detail(tenant))}


# --- links ---

def test_links_freehire_lists_land_on_the_posting():
    assert systems.for_url(LINK + "?utm_source=freehire.me") is bamboohr
    assert bamboohr.application_url(LINK + "?utm_source=freehire.me") == LINK
    assert bamboohr.parse_url(" " + LINK + "/ ") == ("acme", "101")
    # posting ids are short: job 10's tab is not job 101's
    assert bamboohr.on_tab(LINK, LINK + "?x=1") and not bamboohr.on_tab("https://acme.bamboohr.com/careers/10", LINK)


def test_other_links_refused():
    for url in ("https://jobs.lever.co/acme/1b2c", "https://acme.bamboohr.com/careers", "https://acme.bamboohr.com/careers/101x",
                "https://acme.bamboohr.com/jobs/", "https://bamboohr.com.example.com/careers/101"):
        assert not bamboohr.matches(url), url
    with pytest.raises(ValueError):
        bamboohr.parse_url("https://jobs.lever.co/acme/1b2c")


# --- saved definitions -> questions ---

def test_contact_address_and_files_with_keys_required_and_page_order():
    b = form("b")
    got = {id: (q["kind"], q["key"], q["required"]) for id, q in b.items() if q["key"]}
    assert got == {"firstName": ("text", "first_name", True), "lastName": ("text", "last_name", True),
                   "email": ("email", "email", True), "phone": ("phone", "phone", True),
                   "streetAddress": ("text", "street", True), "city": ("text", "city", True),
                   "state": ("text", "state", True), "zip": ("text", "zip", True),
                   "linkedinUrl": ("url", "linkedin", False), "websiteUrl": ("url", "website", False),
                   "resumeFileId": ("file", "resume", True)}
    # State: a list of full names on the page, not the definition's two-letter codes - typed / picked by name
    assert b["state"]["options"] == []
    # the employer's file question sits after the resume on the page; neither box has a hook but its place
    assert b["resumeFileId"]["native"] == "bamboohr:file 1 of 2"
    assert b["customQuestionAnswers.file_1021"]["native"] == "bamboohr:file 2 of 2"
    a = form("a")
    assert (a["coverLetterFileId"]["key"], a["coverLetterFileId"]["native"]) == ("cover_letter", "bamboohr:file 1 of 2")
    assert a["resumeFileId"]["native"] == "bamboohr:file 2 of 2"
    assert all(q.get("page") is None for q in b.values())


def test_turned_off_fields_are_no_questions():
    e = form("e")
    assert not {"streetAddress", "genderId", "veteranStatusId", "disabilityId"} & set(e)
    assert "disabilityId" not in form("a")


def test_employer_questions_by_page_name_kinds_and_options():
    b = form("b")
    yn = b["customQuestionAnswers.yes_no_1019"]
    assert (yn["kind"], yn["options"], yn["required"], yn["native"]) == ("yesno", ["Yes", "No"], True, "bamboohr:yes_no")
    assert b["customQuestionAnswers.short_1018"]["kind"] == "text"
    long = next(q for q in form("e").values() if q["native"] == "bamboohr:long")
    assert long["kind"] == "longtext"
    multi = next(q for q in form("e").values() if q["native"] == "bamboohr:multi")
    assert multi["kind"] == "choice" and multi["options"] and all(multi["options"])


def test_choices_country_education_and_voluntary_never_drafted():
    a = form("a")
    assert "United States" in a["countryId"]["options"] and a["countryId"]["kind"] == "choice"
    assert len(a["educationLevelId"]["options"]) == 14
    # Veteran Status: the page's 3 radios, not required there (4 of 4), whatever the definition lists
    vet = a["veteranStatusId"]
    assert (vet["options"], vet["required"]) == (bamboohr.VETERAN_OPTIONS, False)
    drafted = {x["id"]: x for x in questions.draft(list(a.values()), {"name": "Ada Lovelace", "email": "a@example.com"})}
    for id in ("genderId", "ethnicityId", "veteranStatusId"):
        assert drafted[id]["answer"] is None, id
    pay = {x["id"]: x for x in questions.draft(list(form("b").values()), {"name": "Ada Lovelace"})}["desiredPay"]
    assert pay["answer"] is None


def test_attestation_left_to_the_applicant():
    oath = next(q for q in form("e").values() if "affirm" in q["title"].casefold())
    assert questions.signs(oath["title"])
    assert bamboohr.fill(object(), oath | {"answer": "Yes"}, None).startswith("ASK yours to do on the page")


# --- closed ---

class Got:
    def __init__(self, status, data=None):
        self.status_code, self.data = status, data

    def raise_for_status(self):
        pass

    def json(self):
        return self.data


def board(listed: bool, status=200):
    """/detail answers 404; the employer's job list lists the posting or not."""
    return lambda url, **k: (Got(status, {"result": [{"id": "7"}] + ([{"id": 101}] if listed else [])})
                             if url.endswith("/careers/list") else Got(404))


def test_closed_or_unknown_posting_says_so(monkeypatch):
    # taken down or unknown: 404 {"type": "not_found"} either way (2026-10-06) - the job list tells which
    monkeypatch.setattr(httpx, "get", board(listed=False))
    with pytest.raises(ValueError, match="no longer on the employer's BambooHR job list - it may have closed"):
        bamboohr.questions(LINK)
    monkeypatch.setattr(httpx, "get", board(listed=True))
    with pytest.raises(ValueError, match="can't tell if the posting is open - it is on the employer's BambooHR job list"):
        bamboohr.questions(LINK)
    monkeypatch.setattr(httpx, "get", board(listed=False, status=503))
    with pytest.raises(ValueError, match="can't tell .* job list answered 503"):
        bamboohr.questions(LINK)
    shut = detail("a")
    shut["result"]["jobOpening"]["jobOpeningStatus"] = "Closed"
    monkeypatch.setattr(httpx, "get", lambda *a, **k: Got(200, shut))
    with pytest.raises(ValueError, match="closed"):
        bamboohr.questions(LINK)
    asked = []
    monkeypatch.setattr(httpx, "get", lambda url, **k: asked.append(url) or Got(200, detail("a")))
    assert bamboohr.questions(LINK + "?utm_source=freehire.me") and asked == [LINK + "/detail"]


def test_closed_reads_the_definition_then_the_job_list_never_guesses(monkeypatch):
    monkeypatch.setattr(httpx, "get", lambda *a, **k: Got(200, detail("a")))
    assert bamboohr.closed(LINK) is None
    shut = detail("a")
    shut["result"]["jobOpening"]["jobOpeningStatus"] = "Filled"
    monkeypatch.setattr(httpx, "get", lambda *a, **k: Got(200, shut))
    assert bamboohr.closed(LINK) == "BambooHR lists the posting as 'Filled' - it may have closed"
    monkeypatch.setattr(httpx, "get", board(listed=False))
    assert bamboohr.closed(LINK).startswith("the posting is no longer on the employer's BambooHR job list")
    monkeypatch.setattr(httpx, "get", board(listed=True))
    assert bamboohr.closed(LINK).startswith("can't tell")
    monkeypatch.setattr(httpx, "get", lambda *a, **k: Got(500))
    assert bamboohr.closed(LINK) == "can't tell if the posting is open - BambooHR answered 500"

    def down(*a, **k):
        raise httpx.ConnectError("no route")
    monkeypatch.setattr(httpx, "get", down)
    assert bamboohr.closed(LINK) == "can't tell if the posting is open - BambooHR didn't answer (ConnectError)"


def test_upload_error_words_are_bamboohrs_own():
    for said in ("Upload failed", "Request failed with status code 500", "Network Error",
                 "Whoa, this is a big file (a little too big). The maximum file size you can upload is 20 MB.",
                 "Whoops, something on our side prevented your file from uploading."):
        assert bamboohr.UPLOAD_ERRORS.search(f"x {said} y").group() == said, said
    assert not bamboohr.UPLOAD_ERRORS.search("Resume.pdf 120 KB")


# --- widgets, with fakes ---

class Text:
    def __init__(self, shows=None):
        self.value, self.keys, self.shows = "", [], shows

    def fill(self, v):
        self.value = v

    def press(self, key):
        self.keys.append(key)

    def blur(self):
        pass

    def input_value(self):
        return self.shows if self.shows is not None else self.value


def test_text_read_back_date_shuts_its_picker():
    field = Text()
    assert bamboohr.put_text(field, "11/02/2026", "date") == "ok" and field.keys == ["Escape"]
    assert bamboohr.put_text(Text(shows="(555) 010-0100"), "555-010-0100", "phone") == "ok"
    assert bamboohr.put_text(Text(shows=""), "Test", "text") == "FAIL shows ''"


class Items:
    """A Fabric menu's items; clicking one makes the button show it."""

    def __init__(self, toggle, texts):
        self.toggle, self.texts, self.at = toggle, texts, None

    @property
    def first(self):
        return self

    def wait_for(self, timeout=None):
        pass

    def all_inner_texts(self):
        return self.texts

    def nth(self, i):
        self.at = i
        return self

    def scroll_into_view_if_needed(self):
        pass

    def click(self):
        self.toggle.chosen = self.texts[self.at]


class Toggle:
    def __init__(self, chosen=""):
        self.chosen, self.opened, self.keys = chosen, 0, []

    def count(self):
        return 1

    @property
    def first(self):
        return self

    def locator(self, selector):
        return type("Shown", (), {"all_inner_texts": lambda _: [self.chosen] if self.chosen else []})()

    def click(self):
        self.opened += 1

    def press(self, key):
        self.keys.append(key)

    def get_attribute(self, name):
        return "fab-menu1"


class SelectPage:
    def __init__(self, toggle, texts):
        self.items = Items(toggle, texts)

    def locator(self, selector):
        assert selector == '[id="fab-menu1"] [role=menuitem]'
        return self.items


def test_select_opens_the_menu_and_picks_by_text_never_the_first(monkeypatch):
    toggle = Toggle()
    monkeypatch.setattr(bamboohr, "toggle_of", lambda field: toggle)
    page = SelectPage(toggle, ["Alabama", "Alaska", "New York"])
    assert bamboohr.put_select(page, None, "new york") == "ok" and toggle.chosen == "New York"
    assert bamboohr.put_select(page, None, "Ontario").startswith("ASK no option 'Ontario'") and toggle.keys == ["Escape"]
    # Country preset to United States on the page: nothing opened
    preset = Toggle("United States")
    monkeypatch.setattr(bamboohr, "toggle_of", lambda field: preset)
    assert bamboohr.put_select(SelectPage(preset, []), None, "United States") == "ok" and preset.opened == 0


class Radios:
    def __init__(self, page, labels):
        self.page, self.labels, self.ticked, self.at = page, labels, None, None

    def count(self):
        return len(self.labels)

    def nth(self, i):
        self.at = i
        return self

    def check(self, force=False):
        self.ticked = self.at

    def is_checked(self):
        return self.ticked == self.at


class RadioPage:
    def __init__(self, labels):
        self.radios, self.seen = Radios(self, labels), []

    def eval_on_selector_all(self, selector, js):
        self.seen.append(selector)
        return self.radios.labels

    def locator(self, selector):
        self.seen.append(selector)
        return self.radios


def test_yes_no_ticks_the_radio_by_its_label_in_that_question_only():
    page = RadioPage(["Yes", "No"])
    q = form("b")["customQuestionAnswers.yes_no_1019"]
    assert bamboohr.fill(page, q | {"answer": "true"}, None) == "ok" and page.radios.ticked == 0
    assert all('name="customQuestionAnswers.yes_no_1019"' in s for s in page.seen)
    assert bamboohr.put_radio(RadioPage(["Decline to Answer", "Not a Veteran", "Veteran"]), bamboohr.VETERAN_RADIOS, "Maybe") \
        == "ASK no option 'Maybe'; offered: Decline to Answer, Not a Veteran, Veteran"


def test_files_only_the_resume_or_letter_and_only_after_yes():
    b = form("b")
    project = b["customQuestionAnswers.file_1021"] | {"answer": True}
    assert bamboohr.fill(object(), project, "/tmp/r.pdf").startswith("ASK not the resume box")
    assert bamboohr.fill(object(), b["resumeFileId"] | {"answer": None}, "/tmp/r.pdf") == "skipped - upload not approved"
    letter = form("a")["coverLetterFileId"] | {"answer": True}
    assert bamboohr.fill(object(), letter, None).startswith("ASK cover letter box")


# --- in the window: the same fill through window.Page as through Playwright ---

def asked(id, title, kind, answer, key=None, options=(), native=None):
    return questions.question(id, title, kind, True, options, key, native) | {"answer": answer}


# the hand-built form's questions (fixtures/dom/bamboohr-form.html), each kind answered once: boxes by id, by
# name + by label, Fabric lists, the employer's radios + Veteran Status's, the resume (the cover letter left)
WINDOW_ANSWERS = [
    asked("firstName", "First Name", "text", "Ada", key="first_name"),
    asked("lastName", "Last Name", "text", "Lovelace", key="last_name"),
    asked("email", "Email", "email", "ada@example.com", key="email"),
    asked("phone", "Phone", "phone", "555-0100", key="phone"),
    asked("streetAddress", "Address", "text", "1 Main St", key="street"),
    asked("city", "City", "text", "Austin", key="city"),
    asked("state", "State", "text", "New York", key="state"),
    asked("zip", "ZIP", "text", "78701", key="zip"),
    asked("countryId", "Country", "choice", "United States", options=["Canada", "United States"]),
    asked("coverLetterFileId", "Cover Letter", "file", None, key="cover_letter", native="bamboohr:file 1 of 2"),
    asked("resumeFileId", "Resume", "file", True, key="resume", native="bamboohr:file 2 of 2"),
    asked("dateAvailable", "Date Available", "date", "11/02/2026"),
    asked("desiredPay", "Desired Pay", "text", "90000"),
    asked("linkedinUrl", "LinkedIn Profile URL", "url", "https://www.linkedin.com/in/example", key="linkedin"),
    asked("educationLevelId", "Highest Education Obtained", "choice", "Bachelor's Degree"),
    asked("references", "References", "longtext", "On request."),
    asked("customQuestionAnswers.short_1018", "Salary range", "text", "90000-100000", native="bamboohr:short"),
    asked("customQuestionAnswers.long_761", "Why Acme?", "longtext", "Their own words.", native="bamboohr:long"),
    asked("customQuestionAnswers.yes_no_1019", "Will you now or in the future require sponsorship?", "yesno", "No",
          options=["Yes", "No"], native="bamboohr:yes_no"),
    asked("veteranStatusId", "Veteran Status", "choice", "Not a Veteran", options=bamboohr.VETERAN_OPTIONS)]
# each box's value or tick, each Fabric list's shown pick, each upload block's words - read off the page
WINDOW_SHOWN = ("es => es.map(e => e.type === 'radio' ? e.checked : e.value)"
                ".concat([...document.querySelectorAll('.fab-SelectToggle__content, [data-fabric-component=FileUploadList]')]"
                ".map(e => e.innerText.trim()))")
WINDOW_BOXES = "form input:not([type=file]):not([name=nickname_hpcsaf]), form textarea:not([aria-hidden])"


def test_in_window_fills_bamboohr_as_playwright_does(tab, site, playwright_chrome, tmp_path, monkeypatch):
    # bamboohr.fill + holds + form.fill_page through each: same report, same page after, every answer read
    # back, a second fill changes nothing (plan-k8n.10)
    monkeypatch.setattr(fill_form, "SETTLE_MS", 300)
    monkeypatch.setattr(bamboohr, "ERROR_WAIT_MS", 500)
    resume = tmp_path / "Ada_Lovelace_Resume.pdf"
    resume.write_bytes(b"%PDF-1.4\n%%EOF\n")
    answered = [q for q in WINDOW_ANSWERS if q["answer"] is not None]
    again = [q for q in answered if q["kind"] != "file"]
    reports, pages = {}, {}
    with both(tab, playwright_chrome, site.replace("/acme/jobs/1", BAMBOOHR_PATH)) as tabs:
        for name, page in tabs.items():
            assert fill_form.closed(page, bamboohr) is None
            bamboohr.recover(page, LINK)  # the form is up: no button clicked
            report, extra = fill_form.fill_page(page, bamboohr, WINDOW_ANSWERS, str(resume), None)
            reports[name] = dict(report)
            assert extra == []
            once = page.eval_on_selector_all(WINDOW_BOXES, WINDOW_SHOWN)
            assert [bamboohr.fill(page, q, None) for q in again] == ["ok"] * len(again)
            page.wait_for_timeout(300)
            assert page.eval_on_selector_all(WINDOW_BOXES, WINDOW_SHOWN) == once
            pages[name] = once
            assert [q["id"] for q in answered if not bamboohr.holds(page, q)] == []
    assert reports["window"] == reports["playwright"]
    assert reports["window"] == {q["id"]: "ok" for q in answered}
    assert pages["window"] == pages["playwright"]
    # what shows, empty boxes + clear ticks left out: contact, address, the date, pay, profile, references,
    # both employer answers, No, Not a Veteran, State + Country, the resume in its block (not the letter's), education
    assert [v for v in pages["window"] if v not in ("", False)] == [
        "Ada", "Lovelace", "ada@example.com", "555-0100", "1 Main St", "Austin", "78701", "11/02/2026", "90000",
        "https://www.linkedin.com/in/example", "On request.", "90000-100000", "Their own words.", True, True,
        "New York", "United States", resume.name, "Bachelor's Degree"]
