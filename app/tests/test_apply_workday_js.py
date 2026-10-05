"""apply/workday.js in real headless Chrome on a local model of Workday's My Experience step: a value
counts only once focus leaves the box, and a re-render clears some answers after they showed.
Every request is answered from app/tests/fixtures/workday/ or refused."""
import json
from pathlib import Path
from urllib.parse import urlsplit

import pytest

from apply import browser, profile

FIXTURES = Path(__file__).parent / "fixtures" / "workday"
HOME = "https://acme.wd5.myworkdayjobs.example/form.html"
DATA = {
    "work": [{"title": "Analyst", "company": "Acme", "location": "Springfield", "current": True,
              "start": "2020-03", "end": "", "description": "• Built the monthly report"}],
    "education": [{"school": "State University", "degree": ["Bachelor of Arts", "B.A."], "field": [], "end": ""}],
    "skills": ["Excel", "SQL"], "languages": [],
}


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


@pytest.fixture(scope="module")
def filled(chrome):
    """One fill + verify on the model page (about 10 s: two 2.5 s settles); the page and report after."""
    context = chrome.new_context()
    asked = []

    def serve(route):
        u = urlsplit(route.request.url)
        asked.append(route.request.url)
        if u.hostname != urlsplit(HOME).hostname:
            return route.abort()
        file = FIXTURES / u.path.lstrip("/")
        return route.fulfill(path=str(file)) if file.is_file() else route.fulfill(status=404, body="")

    context.route("**/*", serve)
    page = context.new_page()
    page.goto(HOME)
    page.evaluate(profile.FILLER.read_text(encoding="utf-8") + "\n0")
    page.evaluate(f"window.__jf.run({json.dumps(DATA)})")
    yield page, json.loads(page.evaluate("window.__jf.status()")), page.evaluate("window.__jf.S.report")
    assert all(urlsplit(u).hostname == urlsplit(HOME).hostname for u in asked), asked
    context.close()


def line(report, prefix):
    return next(r for r in report if r.startswith(prefix))


def refilled(report, field):
    return any(r.startswith(f"OK {field}: ") and r.endswith("refilled once - kept") for r in report)


def test_fill_ends_after_verify(filled):
    page, status, report = filled
    assert status["done"] and status["step"] == "done"
    assert page.evaluate("window.renders") >= 2  # the page re-rendered after the fill and after the refill
    assert line(report, "OK Verify > answers").endswith("5 dropped")


def test_box_cleared_once_is_refilled_and_kept(filled):
    page, _, report = filled
    assert refilled(report, "Work 1 > Company")
    assert page.input_value("#company") == "Acme"
    assert refilled(report, "Work 1 > I currently work here")
    assert page.is_checked("[data-key=current]")


def test_menu_cleared_once_is_chosen_again(filled):
    page, _, report = filled
    assert refilled(report, "Education 1 > Degree")
    assert page.text_content("#degree") == "B.A. - Bachelor of Arts"


def test_box_cleared_on_every_render_fails_answer_dropped(filled):
    page, status, _ = filled
    assert "FAIL Work 1 > Location: answer dropped - refilled once, still not kept; fill by hand" in status["problems"]
    assert page.input_value("#location") == ""


def test_dropped_pill_asks_never_picked_again(filled):
    page, status, _ = filled
    assert any(p.startswith("ASK Skills > Excel: answer dropped") for p in status["problems"])
    # pick() presses Enter, which could move the step: verify never types into the box again
    assert page.evaluate("window.enters") == {"Excel": 1, "SQL": 1}


def test_answers_kept_on_focus_out_stay_put(filled):
    page, status, _ = filled
    for box, value in [("#title", "Analyst"), ("#desc", "• Built the monthly report"), ("#school", "State University"),
                       ("[data-key=fromMonth]", "03"), ("[data-key=fromYear]", "2020")]:
        assert page.input_value(box) == value, box
    assert len(status["problems"]) == 2, status["problems"]


@pytest.fixture(scope="module")
def posting(chrome):
    """closed() on a saved posting page (anonymised, drawn ~1.5 s after load like the live one)."""
    context = chrome.new_context()

    def serve(route):
        u = urlsplit(route.request.url)
        file = FIXTURES / u.path.lstrip("/")
        if u.hostname != urlsplit(HOME).hostname or not file.is_file():
            return route.abort()
        return route.fulfill(path=str(file))

    context.route("**/*", serve)

    def closed(name):
        page = context.new_page()
        page.goto(f"https://{urlsplit(HOME).hostname}/{name}")
        page.evaluate(profile.FILLER.read_text(encoding="utf-8") + "\n0")
        try:
            return page.evaluate("window.__jf.closed()")
        finally:
            page.close()

    yield closed
    context.close()


@pytest.mark.parametrize("name", ["posting-closed-b.html", "posting-closed-c.html"])
def test_closed_posting_read_closed(posting, name):
    assert posting(name) is True


@pytest.mark.parametrize("name", ["posting-open-d.html", "posting-open-e.html",
                                  # Apply shows => open, whatever closed words its text holds
                                  "posting-open-says-closed.html"])
def test_open_posting_never_read_closed(posting, name):
    assert posting(name) is False


@pytest.fixture(scope="module")
def upload(chrome):
    """uploaded() on the Resume/CV box model: choose a file (as the extension's upload does), then wait."""
    context = chrome.new_context()

    def serve(route):
        u = urlsplit(route.request.url)
        file = FIXTURES / u.path.lstrip("/")
        if u.hostname != urlsplit(HOME).hostname or not file.is_file():
            return route.abort()
        return route.fulfill(path=str(file))

    context.route("**/*", serve)

    def run(name, box="#resume", page_name="upload.html", ms=5000):
        page = context.new_page()
        page.goto(f"https://{urlsplit(HOME).hostname}/{page_name}")
        page.evaluate(profile.FILLER.read_text(encoding="utf-8") + "\n0")
        try:
            if box:
                page.set_input_files(box, files=[{"name": name, "mimeType": "application/pdf", "buffer": b"%PDF-1.4"}])
            return page.evaluate(f"window.__jf.uploaded({json.dumps(name)}, {ms})")
        finally:
            page.close()

    yield run
    context.close()


def test_upload_name_shown_is_ok(upload):
    # the Job Title "required" error elsewhere on the step is not the upload's
    assert upload("First_Last_Resume.pdf") == "ok"


def test_upload_error_is_workdays_own_words(upload):
    assert upload("First_Last_Resume.docx") == "This file type is not allowed."


def test_upload_error_after_name_wins(upload):
    assert upload("late.pdf") == "This file could not be read."


def test_upload_nothing_shown_is_not_confirmed(upload):
    assert upload("silent.pdf", ms=2000) == "not confirmed"


def test_upload_to_cover_letter_box_is_not_the_resume(upload):
    assert upload("First_Last_Resume.pdf", box="#letter", ms=2000) == "not confirmed"


def test_upload_step_without_resume_box(upload):
    assert upload("First_Last_Resume.pdf", box=None, page_name="form.html", ms=500) == "no Resume/CV box on this page"


# what an applicant typed or picked: none of it may reach a snapshot (it becomes a committed fixture)
TYPED = {"#title": "Zanzibar Quillfeather", "#company": "Quokka Lantern Works", "#location": "Ottervale",
         "#desc": "Wrangled forty spreadsheets", "#school": "Mossbank Polytechnic",
         "[data-key=fromMonth]": "07", "[data-key=fromYear]": "2017"}


@pytest.fixture(scope="module")
def snapshot(chrome):
    """snapshot() of the model step after an applicant filled it: boxes typed, a value attribute set, the
    box ticked, a Degree chosen, a skill picked."""
    context = chrome.new_context()

    def serve(route):
        u = urlsplit(route.request.url)
        file = FIXTURES / u.path.lstrip("/")
        if u.hostname != urlsplit(HOME).hostname or not file.is_file():
            return route.abort()
        return route.fulfill(path=str(file))

    context.route("**/*", serve)
    page = context.new_page()
    page.goto(HOME)
    for box, value in TYPED.items():
        page.fill(box, value)
    page.evaluate("document.querySelector('#location').setAttribute('value', 'Ottervale')")
    page.click("[data-key=current]")
    page.click("#degree")
    page.click("text=B.S. - Bachelor of Science")
    page.fill("#skills", "Pyth")
    page.press("#skills", "Enter")
    page.click("[data-automation-id=promptOption]")
    page.evaluate(profile.FILLER.read_text(encoding="utf-8") + "\n0")
    raw = page.evaluate("window.__jf.snapshot()")
    assert isinstance(raw, str)  # the extension's tool hands back a string as is
    yield raw, json.loads(raw)
    context.close()


def test_snapshot_holds_no_answer(snapshot):
    raw, snap = snapshot
    for value in [*TYPED.values(), "Pyth", "Python"]:
        assert value not in raw, value
    keys = set()
    for f in snap["fields"]:
        keys |= set(f)
    assert keys <= {"label", "kind", "id", "controls", "required", "options"}, keys


def test_snapshot_reads_labels_kinds_hooks_required(snapshot):
    _, snap = snapshot
    fields = {f["label"]: f for f in snap["fields"]}
    assert snap["step"] == "My Experience"
    assert fields["Job Title"] == {"label": "Job Title", "kind": "text", "id": "formField-jobTitle", "controls": [],
                                   "required": True}
    assert fields["Location"]["required"] is False
    assert fields["Role Description"]["kind"] == "textarea"
    assert fields["I currently work here"]["kind"] == "checkbox"
    assert fields["From"]["kind"] == "date"
    assert fields["From"]["controls"] == ["dateSectionMonth-input", "dateSectionYear-input"]
    assert fields["Degree"]["kind"] == "menu" and fields["Degree"]["required"]
    assert fields["Type to Add Skills"]["kind"] == "search-pick"  # a picked pill marks it
    assert [b["text"] for b in snap["buttons"]] == ["Add Another", "Add Another"]
    assert snap["page"]["host"] == urlsplit(HOME).hostname


def test_snapshot_keeps_menu_options_never_search_ones(snapshot):
    _, snap = snapshot
    assert snap["listboxes"] == [{"id": "", "options": ["H.S. - High School", "B.A. - Bachelor of Arts",
                                                        "B.S. - Bachelor of Science"]}]


def write_fixture(tmp_path, monkeypatch, snap):
    from apply import lab, workday_fixture
    monkeypatch.setattr(lab, "OUT", tmp_path / "measure")
    monkeypatch.setattr(workday_fixture, "FIXTURES", tmp_path / "fixtures")
    src = tmp_path / "snap.json"
    src.write_text(json.dumps(snap), encoding="utf-8")
    return workday_fixture.fixture(src)


def test_fixture_names_become_acme_and_go_to_tenants(tmp_path, monkeypatch):
    snap = {"step": "Application Questions", "headings": ["Questions from Globex Corporation"],
            "fields": [{"label": "Have you worked for Globex before?", "kind": "radio", "id": "formField-q1",
                        "controls": [], "required": True, "options": ["Yes", "No"]}],
            "listboxes": [], "buttons": [{"text": "Save and Continue", "id": "bottom-navigation-next-button"}],
            "page": {"host": "globex.wd1.myworkdayjobs.com", "title": "Careers at Globex Corporation", "site": "Workday"}}
    # the extension's tool returns snapshot()'s string; saved as is it is JSON inside JSON
    out = write_fixture(tmp_path, monkeypatch, json.dumps(snap))
    assert out == tmp_path / "fixtures" / "application-questions.json"
    text = out.read_text()
    assert "globex" not in text.lower() and "page" not in json.loads(text)
    assert json.loads(text)["fields"][0]["label"] == "Have you worked for Acme before?"
    assert json.loads(text)["headings"] == ["Questions from Acme"]
    tenants = (tmp_path / "measure" / "tenants.txt").read_text().splitlines()
    assert {"Globex Corporation", "globex"} <= set(tenants) and "Workday" not in tenants


@pytest.mark.parametrize("leak", ["jane.doe@example.com", "(555) 123-4567"])
def test_fixture_refuses_contact_details(tmp_path, monkeypatch, leak):
    snap = {"step": "My Information", "fields": [{"label": leak, "kind": "text"}], "page": {"host": "acme.wd5.myworkdayjobs.com"}}
    with pytest.raises(SystemExit, match="refused"):
        write_fixture(tmp_path, monkeypatch, snap)
    assert not (tmp_path / "fixtures").exists()


def test_snapshot_round_trips_to_a_fixture(snapshot, tmp_path, monkeypatch):
    raw, snap = snapshot
    fixture = json.loads(write_fixture(tmp_path, monkeypatch, raw).read_text())
    assert "page" not in fixture
    assert fixture == {k: v for k, v in snap.items() if k != "page"}  # the model's host names no label
