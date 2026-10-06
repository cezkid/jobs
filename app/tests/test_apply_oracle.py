"""Oracle Recruiting Cloud: link shapes (pods, the employer's own domain, letters in job ids), its tab
among other jobs on one site, the start box read off a local page (rebuilt from what measure read on 4
tenants), the bot-trap box never touched, the applicant's own steps."""
from pathlib import Path
from urllib.parse import urlsplit

import httpx
import pytest

from apply import browser, dom, questions, systems
from apply.systems import oracle

FIXTURES = Path(__file__).parent / "fixtures" / "oracle"
LINK = "https://acme.fa.us2.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_1/job/12345?utm_source=freehire.me"
APP = "https://acme.fa.us2.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_1/job/12345/apply/email"


def test_links_match_every_host_shape_and_open_the_start_box():
    for url, app in ((LINK, APP),
                     ("https://fa-acme-saasfaprod1.fa.ocs.oraclecloud.com/hcmUI/CandidateExperience/es/sites/jobsearch/job/REQ_123/",
                      "https://fa-acme-saasfaprod1.fa.ocs.oraclecloud.com/hcmUI/CandidateExperience/en/sites/jobsearch/job/REQ_123/apply/email"),
                     ("https://careers.acme.example/hcmUI/CandidateExperience/en/sites/Acme/job/9/apply/email",
                      "https://careers.acme.example/hcmUI/CandidateExperience/en/sites/Acme/job/9/apply/email")):
        assert systems.for_url(url) is oracle, url
        assert oracle.application_url(url) == app
    for url in ("https://acme.fa.us2.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_1/requisitions",
                "https://acme.fa.us2.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_1/job/",
                "https://acme.fa.us2.oraclecloud.com/fscmUI/faces/FuseWelcome", "ftp://acme.example/hcmUI/CandidateExperience/en/sites/A/job/1"):
        assert not oracle.matches(url), url


def test_tab_is_this_job_never_another_on_the_same_site():
    assert oracle.on_tab(LINK, APP)
    assert oracle.on_tab(LINK, APP.replace("/apply/email", "/apply/section/1").replace("/en/", "/es/"))
    assert not oracle.on_tab(LINK, APP.replace("12345", "123456"))
    assert not oracle.on_tab(LINK, APP.replace("CX_1", "CX_2"))
    assert not oracle.on_tab(LINK, APP.replace("acme.", "beta."))
    assert not oracle.on_tab(LINK, "https://acme.fa.us2.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_1/requisitions")


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
    """at(name) -> a page showing fixtures/oracle/<name>; nothing reaches the network."""
    context = chrome.new_context()
    asked = []

    def serve(route):
        u = urlsplit(route.request.url)
        asked.append(u.hostname)
        file = FIXTURES / u.path.lstrip("/")
        return route.fulfill(path=str(file)) if u.hostname == "acme.example" and file.is_file() else route.abort()

    context.route("**/*", serve)
    page = context.new_page()

    def go(name):
        page.goto(f"https://acme.example/{name}")
        return page
    yield go
    assert set(asked) <= {"acme.example"}, asked
    context.close()


def test_start_box_read_email_and_terms_next_left_to_the_applicant(at, capsys):
    qs = oracle.read(at("start-box.html"))
    by = {q["title"]: q for q in qs}
    assert set(by) == {"Email Address", "I agree with the terms and conditions"}
    assert {q["page"] for q in qs} == {oracle.START}
    assert by["Email Address"]["key"] == "email" and by["Email Address"]["required"]
    out = capsys.readouterr().out
    assert "tick 'I agree with the terms and conditions' yourself" in out
    assert "click Next yourself - your email goes to this employer" in out and "e-signature" in out
    assert oracle.UNMEASURED not in out


def test_bot_trap_box_never_a_question_never_filled(at):
    # read as shown on 4 of 4 tenants (2026-10-03): dom alone would ask it
    page = at("start-box.html")
    raw = dom.questions(dom.snapshot(page))
    assert "honeypot" in [q["title"] for q in raw]
    assert "honeypot" not in [q["title"] for q in oracle.read(page)]
    assert not [h for h in oracle.ids_on_page(page) if "honey" in h or "oda-" in h]
    assert oracle.fill(page, {"id": '[id="honey-pot-1"]', "title": "honeypot", "kind": "text", "answer": "x"},
                       None).startswith("FAIL")
    assert page.input_value("#honey-pot-1") == ""
    # the ids swap between employers: a stale email hook naming the trap fails on its label
    stale = {"id": '[id="honey-pot-1"]', "title": "Email Address", "kind": "email", "answer": "test@example.com"}
    assert oracle.fill(page, stale, None).startswith("FAIL")
    assert page.input_value("#honey-pot-1") == ""


def test_start_box_answers_from_the_resume_terms_left_unticked(at):
    page = at("start-box.html")
    contact = {"name": "Ada Lovelace", "email": "ada@example.com", "phone": "555-0100"}
    drafted = {a["title"]: a for a in questions.draft(oracle.read(page), contact)}
    assert drafted["Email Address"]["answer"] == "ada@example.com"
    assert questions.blank(drafted["I agree with the terms and conditions"].get("answer"))
    assert oracle.fill(page, drafted["Email Address"] | {"answer": "test@example.com"}, None) == "ok"
    assert page.input_value("#primary-email-0") == "test@example.com"
    terms = drafted["I agree with the terms and conditions"] | {"answer": "Yes"}
    assert oracle.fill(page, terms, None).startswith("ASK yours to do")
    assert not page.is_checked("#legal-disclaimer-checkbox")
    assert oracle.fill(page, {"id": "#gone", "title": "Gone", "kind": "text", "answer": "x"}, None).startswith(questions.LATER)


def test_job_page_says_click_apply_now_first(at):
    with pytest.raises(SystemExit, match="Apply Now"):
        oracle.read(at("job.html"))


def test_page_after_next_read_generically_password_captcha_consent_left(at, capsys):
    page = at("next.html")
    qs = oracle.read(page)
    assert [q["title"] for q in qs if q["kind"] != "yesno"] == ["First Name"] and qs[0]["page"] == "Contact Information"
    out = capsys.readouterr().out
    assert oracle.UNMEASURED in out and "password box 'Password' - yours to type" in out
    assert "security check (captcha) - yours to do" in out and "(agreeing or consenting)" in out
    assert "click Next yourself" not in out


def test_easy_apply_start_box_read_as_the_start_box_security_check_left(at, capsys):
    # .../apply/email redirected to .../easy-apply/email on 1 tenant (2026-10-06): own label + heading
    qs = oracle.read(at("start-box-easy-apply.html"))
    assert [(q["title"], q["key"], q["page"]) for q in qs if q["kind"] == "email"] == [("What's your email?", "email", oracle.START)]
    assert "honeypot" not in [q["title"] for q in qs]
    out = capsys.readouterr().out
    assert "security check (captcha) - yours to do" in out and "click Next yourself" in out
    assert oracle.on_tab(LINK, APP.replace("/apply/", "/easy-apply/"))


def email(page) -> dict:
    return next(q for q in oracle.read(page) if q["kind"] == "email") | {"answer": "test@example.com"}


@pytest.mark.parametrize("name", ["start-box.html", "start-box-easy-apply.html"])
def test_holds_reads_the_email_box_as_shown_trap_and_terms_never_ours(at, name):
    page = at(name)
    q = email(page)
    assert not oracle.holds(page, q)  # empty box: nothing shows
    assert oracle.fill(page, q, None) == "ok" and oracle.holds(page, q)
    assert not oracle.holds(page, q | {"answer": "Test@example.com"})  # exact, as typed
    page.fill("#primary-email-0", "")
    assert not oracle.holds(page, q)
    # a hook naming the trap is never read as an answer, filled or not
    page.fill("#honey-pot-1", "test@example.com")
    assert not oracle.holds(page, q | {"id": '[id="honey-pot-1"]'})
    assert not oracle.holds(page, q | {"id": '[id="honey-pot-1"]', "title": "honeypot"})
    page.check("#legal-disclaimer-checkbox")
    terms = next(t for t in dom.questions(dom.snapshot(page)) if t["kind"] == "yesno") | {"answer": "Yes"}
    assert not oracle.holds(page, terms)


def test_recheck_fills_a_dropped_email_again_once_then_fails(at, monkeypatch):
    from apply import form
    monkeypatch.setattr(form, "SETTLE_MS", 200)
    page = at("start-box.html")
    q = email(page)
    # the page empties the box once after it changes: filled again, holds
    page.evaluate("""() => { const e = document.querySelector('#primary-email-0'); let n = 0;
        e.addEventListener('change', () => { if (n++ === 0) setTimeout(() => { e.value = ''; }, 50); }); }""")
    assert form.fill_page(page, oracle, [q], None, None)[0] == [(q["id"], "ok")]
    assert page.input_value("#primary-email-0") == "test@example.com"
    # every time: the user fills it by hand
    page = at("start-box.html")
    page.evaluate("""() => { const e = document.querySelector('#primary-email-0');
        e.addEventListener('change', () => setTimeout(() => { e.value = ''; }, 50)); }""")
    assert form.fill_page(page, oracle, [q], None, None)[0] == [(q["id"], "FAIL answer dropped after filling - fill it by hand")]


# --- closed ---

class Got:
    def __init__(self, status, data=None):
        self.status_code, self.data = status, data

    def json(self):
        return self.data


def record(start="2026-09-01T00:00:00+00:00", end=None):
    return Got(200, {"items": [{"Id": "12345", "ExternalPostedStartDate": start, "ExternalPostedEndDate": end}]})


def test_closed_reads_the_postings_record_never_guesses(monkeypatch):
    asked = []
    monkeypatch.setattr(httpx, "get", lambda url, **k: asked.append(url) or record())
    assert oracle.closed(LINK) is None
    assert asked == ['https://acme.fa.us2.oraclecloud.com/hcmRestApi/resources/latest/recruitingCEJobRequisitionDetails'
                     '?expand=all&onlyData=true&finder=ById;Id="12345",siteNumber=CX_1']
    # dropped from Oracle's records: 200 with no items (16 of 42 links, 2026-10-06)
    monkeypatch.setattr(httpx, "get", lambda *a, **k: Got(200, {"items": []}))
    assert oracle.closed(LINK) == "Oracle no longer has the posting on record - it may have closed"
    # on record but never posted (5 of 42, off the job list): can't tell
    for start in (None, "2099-01-01T00:00:00Z"):
        monkeypatch.setattr(httpx, "get", lambda *a, **k: record(start))
        assert oracle.closed(LINK).startswith("can't tell if the posting is open - Oracle has it on record")
    monkeypatch.setattr(httpx, "get", lambda *a, **k: record(end="2026-01-02T00:00:00"))
    assert oracle.closed(LINK) == "Oracle's record says the posting ended on 2026-01-02 - it may have closed"
    monkeypatch.setattr(httpx, "get", lambda *a, **k: record(end="2099-01-02T00:00:00Z"))
    assert oracle.closed(LINK) is None
    monkeypatch.setattr(httpx, "get", lambda *a, **k: Got(503))
    assert oracle.closed(LINK) == "can't tell if the posting is open - Oracle answered 503"

    def down(*a, **k):
        raise httpx.ConnectError("no route")
    monkeypatch.setattr(httpx, "get", down)
    assert oracle.closed(LINK) == "can't tell if the posting is open - Oracle didn't answer (ConnectError)"


def test_closed_page_words_decide_before_the_record(at, monkeypatch):
    from apply import form
    # .../apply/email on a closed posting lands on its job page with these words (2026-10-06)
    page = at("job.html")
    page.set_content("<p>This job is no longer available. You may also VIEW ALL JOBS</p>")
    monkeypatch.setattr(httpx, "get", lambda *a, **k: pytest.fail("the page's words decide"))
    assert "no longer available" in form.closed(page, oracle, LINK)
    # a start box showing = open, whatever Oracle's record says (2 of 4 dropped records still opened one)
    assert form.closed(at("start-box.html"), oracle, LINK) is None
