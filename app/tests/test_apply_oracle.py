"""Oracle Recruiting Cloud: link shapes (pods, the employer's own domain, letters in job ids), its tab
among other jobs on one site, the start box read off a local page (rebuilt from what measure read on 4
tenants), the bot-trap box never touched, the applicant's own steps."""
from pathlib import Path
from urllib.parse import urlsplit

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
