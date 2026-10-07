"""UKG: closed from the posting page (plain GET, faked), and every box filled + read back on a hand-built
signed-in page in headless Chrome (fixtures/ukg/form.html). Link shapes + the snapshot -> questions rules:
test_apply_form.py. Facts: app/docs/apply/ukg.md."""
from pathlib import Path
from urllib.parse import urlsplit

import httpx
import pytest

from apply import browser, form
from apply.systems import ukg

FIXTURES = Path(__file__).parent / "fixtures" / "ukg"
SITE = "recruiting.ultipro.com"
BOARD, OPPORTUNITY = "0f6e1a2b-3c4d-4e5f-8a9b-0c1d2e3f4a5b", "1a2b3c4d-5e6f-4a7b-8c9d-0e1f2a3b4c5d"
POSTING = f"https://{SITE}/ACM1000ACME/JobBoard/{BOARD}/OpportunityDetail?opportunityId={OPPORTUNITY}"
APPLY = f"https://{SITE}/ACM1000ACME/JobBoard/{BOARD}/OpportunityApply?opportunityId={OPPORTUNITY}"
MC, SHIFT, TEXT, NUMBER = (f"00000000-0000-4000-a000-0000000000a{i}" for i in range(1, 5))


# --- closed: the posting page, a plain GET ---

def answer(monkeypatch, status=200, text="", error=False):
    asked = []

    def get(url, **kw):
        asked.append(url)
        if error:
            raise httpx.ConnectError("down")
        return httpx.Response(status, text=text)
    monkeypatch.setattr(ukg.httpx, "get", get)
    return asked


def test_gone_opportunity_reads_closed_off_ukgs_own_block(monkeypatch):
    asked = answer(monkeypatch, text=f'<div {ukg.GONE} data-automation="opportunity-internal-only-message"></div>')
    assert "not available" in ukg.closed(APPLY)
    assert asked == [POSTING]  # the posting page, never the apply page (that one wants a sign-in)


def test_open_posting_or_cant_tell(monkeypatch):
    answer(monkeypatch, text=f"<script>new {ukg.OPEN}{{}})</script>")
    assert ukg.closed(POSTING) is None
    answer(monkeypatch, text="<html>something else</html>")
    assert ukg.closed(POSTING).startswith("can't tell")
    answer(monkeypatch, status=503)
    assert ukg.closed(POSTING).startswith("can't tell")
    answer(monkeypatch, error=True)
    assert ukg.closed(POSTING).startswith("can't tell")


def test_gone_posting_raises_before_any_browser(monkeypatch):
    answer(monkeypatch, text=ukg.GONE)
    monkeypatch.setattr(browser, "page_at", lambda url: pytest.fail("browser opened for a gone posting"))
    with pytest.raises(ValueError, match="not available"):
        ukg.questions(POSTING)


@pytest.mark.parametrize("text", ["This opportunity is currently not available.", "Sorry, this opportunity is not available."])
def test_ukg_words_read_closed(text):
    assert form.CLOSED.search(text)


@pytest.mark.parametrize("text", ["Visa sponsorship is not available for this role.",
                                  "This is an internal opportunity.", "Sorry, this opportunity is only available for acme employees."])
def test_other_not_available_text_is_not_closed(text):
    assert not form.CLOSED.search(text)


# --- the form, in headless Chrome ---

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
    """at(query) -> a page showing fixtures/ukg/form.html as the signed-in apply page; nothing reaches the network."""
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


ANSWERS = {"Country": "United States", "AddressLine1": "1 Main St", "City": "Springfield", "State": "Illinois",
           "PostalCode": "62701", "Phone": "555-0100", "ApplicantSource": "Job Board", "resume": True,
           "employeereferral": "No", "start-date": "10/15/2026", MC: "Yes", SHIFT: "Night",
           TEXT: "Five years.\nTwo lines.", NUMBER: "5", "Gender": "Female", "HispanicOrigin": ukg.DECLINE,
           "EthnicOrigin": "White", ukg.PROFILE: "No"}


def answered(page):
    qs = ukg.read(page)
    for q in qs:
        q["answer"] = ANSWERS[q["id"]]
    return qs


def resume(tmp_path):
    path = tmp_path / "Test_Applicant_Resume.pdf"
    path.write_bytes(b"%PDF-1.4\n%%EOF\n")
    return str(path)


def test_form_read_off_the_page(at):
    by = {q["id"]: q for q in ukg.read(at())}
    assert set(by) == set(ANSWERS)
    assert by[MC]["kind"] == "yesno" and by[SHIFT]["options"] == ["Day", "Night", "Either"]
    assert by[TEXT]["title"] == "Describe your experience with inventory." and by[NUMBER]["kind"] == "number"
    assert by["Country"]["required"] and by["Phone"]["kind"] == "phone" and by["resume"]["kind"] == "file"
    assert by["Gender"]["options"] == ["Male", "Female", ukg.DECLINE]


def test_every_box_filled_and_read_back_off_the_page(at, tmp_path):
    page = at()
    qs = answered(page)
    report, extra = form.fill_page(page, ukg, qs, resume(tmp_path), None)
    skipped = {"EthnicOrigin": "skipped - not shown for the other answers", ukg.PROFILE: "skipped - user said no"}
    assert dict(report) == {q["id"]: skipped.get(q["id"], "ok") for q in qs}, report
    assert extra == []
    by = {q["id"]: q for q in qs}
    for q in qs:
        if q["id"] not in skipped:
            assert ukg.holds(page, q), q["id"]
    # hidden template copies in each block left alone: only the shown box took the answer
    assert page.locator("[data-automation=text-response]").evaluate_all("es => es.map(e => e.value)").count("") == 4
    # what the page shows changed -> not held
    page.locator("#City").fill("")
    assert not ukg.holds(page, by["City"])
    assert not ukg.holds(page, by["Country"] | {"answer": "Canada"})
    assert not ukg.holds(page, by["Phone"] | {"answer": "555-0199"})
    assert not ukg.holds(page, by["employeereferral"] | {"answer": "Yes"})
    assert not ukg.holds(page, by["start-date"] | {"answer": "10/16/2026"})
    assert not ukg.holds(page, by[SHIFT] | {"answer": "Day"})
    assert not ukg.holds(page, by[NUMBER] | {"answer": "6"})
    assert not ukg.holds(page, by["Gender"] | {"answer": ukg.DECLINE})
    assert not ukg.holds(page, by[MC] | {"id": "00000000-0000-4000-a000-0000000000ff"})  # no such block
    assert not ukg.holds(page, by["EthnicOrigin"])  # hidden list: nothing shown to read


def test_resume_sections_held_once_no_editor_is_open(at):
    page = at()
    q = {"id": ukg.PROFILE, "kind": "yesno", "native": "profile", "answer": "Yes"}
    assert ukg.holds(page, q)
    page.evaluate("""() => document.querySelector('[data-automation=skills-panel]')
        .insertAdjacentHTML('beforeend', '<button data-automation=save-button>Save</button>')""")
    assert not ukg.holds(page, q)  # an entry left unsaved


def test_upload_error_in_the_pages_own_words_fails(at, tmp_path):
    page = at("&upload=fail")
    got = ukg.put_file(page, resume(tmp_path))
    assert got == "FAIL the page says 'We're sorry, that file type is not supported.' - choose the file again " \
                  "on the page, or check the Documents box"
    assert not ukg.holds(page, {"id": "resume", "kind": "file", "native": "document", "answer": True})


def test_upload_nothing_shown_asks(at, tmp_path, monkeypatch):
    monkeypatch.setattr(ukg, "SHOWN_WAIT_MS", 1500)
    assert ukg.put_file(at("&upload=never"), resume(tmp_path)).startswith("ASK upload not confirmed")


def test_a_box_dropped_after_filling_is_filled_again(at, monkeypatch):
    page = at()
    qs = [q for q in answered(page) if q["id"] == "City"]
    calls = []
    real = ukg.fill

    def fill_then_drop(page, q, file):
        calls.append(q["id"])
        got = real(page, q, file)
        if len(calls) == 1:  # the page empties it once, as Ashby's did
            page.locator("#City").fill("")
        return got
    monkeypatch.setattr(ukg, "fill", fill_then_drop)
    report, _ = form.fill_page(page, ukg, qs, None, None)
    assert report == [("City", "ok")] and len(calls) == 2
