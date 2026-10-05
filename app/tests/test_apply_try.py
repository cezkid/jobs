"""apply-form try: synthetic answers by kind (never the user's), the applicant's own steps left,
--next refuses anything that could send; end to end offline on a local form, headless, block +
canary on. Own file: a headless Chrome holds Playwright's loop for its whole module."""
from datetime import date
from types import SimpleNamespace

import pytest

import cfg
from apply import browser, dom, lab, questions, systems, trial


def q(title, kind="text", key=None, options=(), native=None):
    return questions.question(title, title, kind, True, options, key, native)


@pytest.fixture
def no_settings(monkeypatch):
    def refuse(*a, **k):
        raise AssertionError("try read the user's settings")
    monkeypatch.setattr(cfg, "load", refuse)


def test_synthetic_answers_by_key_and_kind(no_settings):
    day = date(2026, 10, 3)
    got = lambda *a, **k: trial.synthetic(q(*a, **k), day)[0]
    assert got("Full name", key="name") == "Test Applicant"
    assert (got("First", key="first_name"), got("Last", key="last_name")) == ("Test", "Applicant")
    assert got("Email", "email") == "test@example.com" and got("Phone", "phone") == "555-0100"
    assert got("LinkedIn", key="linkedin") == "https://www.linkedin.com/in/test"
    assert got("Portfolio", "url") == "https://example.com"
    assert got("Where?", "location", key="location") == "New York"
    assert (got("Street", key="street"), got("Zip", key="zip")) == ("1 Test St", "10001")
    assert got("State", "choice", key="state", options=["New Jersey", "NY"]) == "NY"
    assert got("Years", "number") == "1" and got("Why us?", "longtext") == "Test answer"
    assert got("Start (MM/DD/YYYY)", "date") == "11/02/2026"
    assert got("Start", "date", native="dom:input:date") == "2026-11-02"
    assert got("Sponsorship?", "yesno") == "No"
    assert got("Gender", "choice", options=["Decline to self identify", "Prefer not to say", "Woman"]) == "Woman"
    assert got("Pick", "multichoice", options=["I don't wish to answer", "A", "B"]) == ["A"]
    assert (got("Resume", "file", key="resume"), got("Cover letter", "file", key="cover_letter")) == (True, True)


def test_consent_and_other_files_left_for_the_applicant(no_settings):
    for title in ("I agree to the Terms and Conditions", "Signature", "I consent to receive SMS messages"):
        answer, why = trial.synthetic(q(title, "yesno"))
        assert answer is None and trial.APPLICANT in why
    # measured 2026-10-05 (Greenhouse tenant E): filled [ok] with a test Yes before
    answer, why = trial.synthetic(q("I confirm that my application materials and interview responses reflect my "
                                    "own work and were not generated, edited, or supplemented by AI tools "
                                    "(e.g., ChatGPT, Gemini, Claude, etc.).", "yesno"))
    assert answer is None and why == f"saying whether AI helped - {trial.APPLICANT}"
    answer, why = trial.synthetic(q("Transcript", "file"))
    assert answer is None and trial.APPLICANT in why
    assert trial.synthetic(q("Gender", "choice", options=["Decline", "Prefer not to say"]))[0] is None


def test_next_presses_only_next_or_continue():
    assert all(trial.next_ok(t) for t in ("Next", "Continue", " next  step ", "CONTINUE"))
    assert not any(trial.next_ok(t) for t in ("Save and Continue", "Submit", "Submit Application", "Apply",
                                               "Finish", "Complete", "Send", "Sign and Continue", "Next page"))


FORM = """<!doctype html><title>Job Application at Acme Test Co</title>
<form id=f>
  <label for=first>First Name *</label><input id=first required>
  <label for=email>Email *</label><input id=email type=email required>
  <label for=pw>Create a password</label><input id=pw type=password>
  <label for=cv>Resume</label><input id=cv type=file>
  <label for=auth>Are you authorized?</label>
  <select id=auth><option value="">Pick</option><option>Decline to answer</option><option>Yes</option><option>No</option></select>
  <label><input type=checkbox id=terms> I agree to the Terms and Conditions</label>
  <div class=g-recaptcha></div>
  <button type=button>Save and Continue</button>
  <button type=button id=next onclick="document.getElementById('f').hidden = true; document.getElementById('p2').hidden = false">Next</button>
</form>
<form id=p2 hidden><label for=why>Why us?</label><textarea id=why></textarea></form>
<script>
document.getElementById('email').addEventListener('change', () => fetch('/w/save', {method: 'POST', body: 'x'}).catch(() => {}));
</script>"""


def test_try_end_to_end_offline(tmp_path, monkeypatch, capsys, no_settings):
    pytest.importorskip("playwright.sync_api")
    try:
        browser.chrome()
    except SystemExit:
        pytest.skip("Chrome not installed")
    monkeypatch.setattr(lab, "RUNS", tmp_path / "measure-browser")
    monkeypatch.setattr(lab, "OUT", tmp_path / "measure")
    listener = lab.Listener({"/apply.html": ("text/html", FORM)})
    # a plain-HTML system, as dom.py serves one: read off the page, filled by hook
    local = SimpleNamespace(NAME="Local", READY="#first", application_url=lambda u: u,
                            read=lambda page: dom.questions(dom.snapshot(page)),
                            fill=lambda page, q, f: dom.fill(page, q, f),
                            ids_on_page=lambda page: [x["id"] for x in dom.questions(dom.snapshot(page))])
    monkeypatch.setattr(systems, "for_url", lambda u: local)
    try:
        trial.trial(listener.home + "/apply.html", go_next=True, headless=True)
    finally:
        listener.close()
    out = capsys.readouterr().out
    assert listener.writes == []
    assert "canary ok" in out and "sent: 0 writes" in out
    assert "[ok] First Name" in out and "[ok] Email" in out and "[ok] Resume" in out
    assert "[ok] Are you authorized?" in out  # first option that says something: Yes, not Decline
    assert "I agree to the Terms and Conditions - agreeing, consenting or signing - the applicant's own step" in out
    assert "password box 'Create a password'" in out and "security check (captcha)" in out
    assert "POST 127.0.0.1/w/save while filling 'Email'" in out
    assert "--next: new page" in out and "textarea 1" in out
    assert not (tmp_path / "measure-browser").exists() or not any((tmp_path / "measure-browser").iterdir())


def test_next_covered_says_what_covers_it(monkeypatch, capsys):
    # Paylocity, 2026-10-03: an upload dialog + cookie banner over Next Step - the click timed out
    class Button:
        def inner_text(self):
            return "Next Step"

        def click(self, timeout):
            raise TimeoutError("Locator.click: Timeout 15000ms exceeded")

        def evaluate(self, js):
            return 'div#onetrust-banner-sdk role=dialog "We use cookies"'

    page = SimpleNamespace(get_by_role=lambda role, name=None: SimpleNamespace(
        filter=lambda visible: SimpleNamespace(all=lambda: [Button()])))
    monkeypatch.setattr(dom, "snapshot", lambda page: {"url": "x", "controls": []})
    trial.press_next(page, lab.Block())
    out = capsys.readouterr().out
    assert out == '--next: Next not reachable while blocked: covered by div#onetrust-banner-sdk role=dialog "We use cookies"\n'
