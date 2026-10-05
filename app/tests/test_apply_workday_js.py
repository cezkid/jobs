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
