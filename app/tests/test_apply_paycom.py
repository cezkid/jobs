"""Paycom: link shapes, its tab among other employers' on one host, the start box read off a local
page (rebuilt from its labels - it doesn't open while writes are blocked), the applicant's own steps."""
from pathlib import Path
from urllib.parse import urlsplit

import httpx
import pytest

from apply import browser, dom, form, questions, systems
from apply.systems import paycom

FIXTURES = Path(__file__).parent / "fixtures" / "paycom"
PORTAL = "https://www.paycomonline.net/v4/ats/web.php/portal/acme0000000000000000000000000000/jobs/123456"
OLD = "https://www.paycomonline.net/v4/ats/web.php/jobs/ViewJobDetails?job=123456&clientkey=ACME0000000000000000000000000000"
OTHER = "https://www.paycomonline.net/v4/ats/web.php/portal/beta0000000000000000000000000000/jobs/123456"


def test_links_match_and_open_the_portal_page():
    for url in (PORTAL, PORTAL + "?utm_source=freehire.me", OLD, "http://paycomonline.net/v4/ats/web.php/portal/ACME0000000000000000000000000000/jobs/123456"):
        assert systems.for_url(url) is paycom, url
        assert paycom.application_url(url) == PORTAL
    for url in ("https://www.paycomonline.net/v4/ats/web.php/portal/acme0000000000000000000000000000/jobs",
                "https://www.paycomonline.net/v4/ats/web.php/jobs/ViewJobDetails?job=123456",
                "https://paycomonline.net.evil.example/v4/ats/web.php/portal/acme/jobs/1"):
        assert not paycom.matches(url), url


def test_tab_is_this_employers_job_never_another_on_the_same_host():
    # two employers' newest postings shared one job id (2026-10-03): the key decides
    assert paycom.on_tab(PORTAL, PORTAL + "?utm_source=x#top")
    assert paycom.on_tab(OLD, PORTAL)
    assert paycom.on_tab(PORTAL, "https://www.paycomonline.net/v4/ats/web.php/portal/acme0000000000000000000000000000/applications")
    assert not paycom.on_tab(PORTAL, OTHER)
    assert not paycom.on_tab(PORTAL, PORTAL.replace("123456", "123457"))
    assert not paycom.on_tab(PORTAL, "https://www.example.com/v4/ats/web.php/portal/acme0000000000000000000000000000/jobs/123456")


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
    """at(name) -> a page showing fixtures/paycom/<name>; nothing reaches the network."""
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


def test_start_box_read_as_contact_boxes_consent_left_to_the_applicant(at, capsys):
    qs = paycom.read(at("start-box.html"))
    by = {q["title"]: q for q in qs}
    assert {q["page"] for q in qs} == {paycom.START}
    assert by["Legal First Name"]["key"] == "legal_first" and by["Legal Last Name"]["key"] == "legal_last"
    assert by["Email"]["kind"] == by["Confirm Email"]["kind"] == "email"
    assert by["Primary Phone"]["kind"] == "phone"
    sms = next(q for q in qs if "(SMS)" in q["title"])
    assert questions.signs(sms["title"])
    out = capsys.readouterr().out
    assert "Continue To Application yourself" in out and "security check (captcha) - yours to do" in out
    assert "(agreeing or consenting)" in out and paycom.UNMEASURED not in out


def test_start_box_answers_from_the_resume_never_the_sms_consent(at):
    contact = {"name": "Ada Lovelace", "email": "ada@example.com", "phone": "555-0100",
               "legal_first": "Ada", "legal_last": "Lovelace"}
    got = {a["title"]: a["answer"] for a in questions.draft(paycom.read(at("start-box.html")), contact)}
    assert got["Email"] == got["Confirm Email"] == "ada@example.com" and got["Primary Phone"] == "555-0100"
    assert questions.blank(next(v for t, v in got.items() if "(SMS)" in t))


def test_fill_types_contact_boxes_refuses_consent(at):
    page = at("start-box.html")
    qs = {q["title"]: q for q in paycom.read(page)}
    assert paycom.fill(page, qs["Email"] | {"answer": "test@example.com"}, None) == "ok"
    assert paycom.fill(page, qs["Primary Phone"] | {"answer": "555-0100"}, None) == "ok"
    sms = next(q for t, q in qs.items() if "(SMS)" in t)
    assert paycom.fill(page, sms | {"answer": "Yes"}, None).startswith("ASK yours to do")
    assert not page.locator("input[name=primaryPhoneOptIn]:checked").count()
    assert paycom.fill(page, {"id": "#gone", "title": "Gone", "kind": "text", "answer": "x"}, None).startswith(questions.LATER)


def test_job_page_says_click_apply_first(at):
    with pytest.raises(SystemExit, match="clicks Apply"):
        paycom.read(at("job.html"))


def test_page_after_continue_read_generically_marked_unmeasured(at, capsys):
    page = at("next.html")
    qs = paycom.read(page)
    assert [q["title"] for q in qs] == ["Employer"] and qs[0]["page"] == "Work History"
    out = capsys.readouterr().out
    assert paycom.UNMEASURED in out and "password box 'Password' - yours to type" in out
    assert "Password" not in [dom.title(c["label"]) for c in dom.snapshot(page)["controls"] if c["hook"] in paycom.ids_on_page(page)]


def test_holds_reads_what_the_box_shows_never_the_sms_consent(at):
    page = at("start-box.html")
    qs = {q["title"]: q for q in paycom.read(page)}
    email, phone = qs["Confirm Email"] | {"answer": "test@example.com"}, qs["Primary Phone"] | {"answer": "555-0100"}
    assert not paycom.holds(page, email)  # nothing typed yet
    assert paycom.fill(page, email, None) == "ok" and paycom.fill(page, phone, None) == "ok"
    assert paycom.holds(page, email) and paycom.holds(page, phone)
    assert not paycom.holds(page, email | {"answer": "other@example.com"})
    page.fill("#confirmEmailAddress", "")
    assert not paycom.holds(page, email)
    page.evaluate("document.querySelector('#primaryPhoneNumber').remove()")
    assert not paycom.holds(page, phone)  # box gone
    sms = next(q for t, q in qs.items() if "(SMS)" in t)
    page.evaluate("document.querySelectorAll('input[name=primaryPhoneOptIn]').forEach(e => e.checked = true)")
    assert not paycom.holds(page, sms | {"answer": "Yes"})


def job_page(monkeypatch, status=200, text="", error=None):
    asked = []

    def get(url, **kw):
        asked.append(url)
        if error:
            raise error
        return httpx.Response(status, text=text, request=httpx.Request("GET", url))
    monkeypatch.setattr(paycom.httpx, "get", get)
    return asked


def test_closed_reads_the_job_page_for_its_posting(monkeypatch):
    open_page = ('<html><head><script type="application/ld+json" id="google-job-json-ld">'
                 '{"@context": "https://schema.org", "@type": "JobPosting", "title": "Test Job"}</script></head></html>')
    asked = job_page(monkeypatch, text=open_page)
    assert paycom.closed(OLD) is None and asked == [PORTAL]
    # a job id Paycom doesn't have: the same page without the posting, then "We Couldn't Find This Job"
    job_page(monkeypatch, text="<html><head><title>Careers</title></head><body><div id=app></div></body></html>")
    assert paycom.closed(PORTAL).startswith("Paycom can't find this job")
    with pytest.raises(ValueError, match="can't find this job"):
        paycom.questions(PORTAL)  # before any browser
    for kw in ({"status": 503, "text": "<html>busy</html>"}, {"text": "not a page"}, {"error": httpx.ConnectError("down")}):
        job_page(monkeypatch, **kw)
        assert paycom.closed(PORTAL).startswith("can't tell"), kw


def test_closed_words_on_the_page_match():
    assert form.CLOSED.search("We Couldn't Find This Job") and form.CLOSED.search("We couldn’t find this job")
