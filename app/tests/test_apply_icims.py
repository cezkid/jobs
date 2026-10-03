"""iCIMS: link shapes (careers-<co> and other icims.com hosts, links without a slug), its tab among other
jobs on one site, the start box read off a local page in its own frame (rebuilt from what measure read on
3 tenants), the privacy tick + captcha + Next left to the applicant, a page after Next read generically."""
from pathlib import Path
from urllib.parse import urlsplit

import pytest

from apply import browser, questions, systems
from apply.systems import icims

FIXTURES = Path(__file__).parent / "fixtures" / "icims"
LINK = "https://careers-acme.icims.com/jobs/12345/test-job/job?utm_source=freehire.me"
APP = "https://careers-acme.icims.com/jobs/12345/test-job/login"


def test_links_match_every_icims_host_and_open_the_start_box():
    for url, app in ((LINK, APP),
                     ("https://uscareers-acme.icims.com/jobs/678/test-job/job?lang=en",
                      "https://uscareers-acme.icims.com/jobs/678/test-job/login"),
                     ("https://canada-acmecareers.icims.com/jobs/9/a%2c-b/job", "https://canada-acmecareers.icims.com/jobs/9/a%2c-b/login"),
                     (APP, APP),
                     ("https://careers-acme.icims.com/jobs/12345/job", "https://careers-acme.icims.com/jobs/12345/login"),
                     ("https://careers-acme.icims.com/jobs/12345", "https://careers-acme.icims.com/jobs/12345/login")):
        assert systems.for_url(url) is icims, url
        assert icims.application_url(url) == app
    for url in ("https://careers.acme.example/jobs/30383",  # an employer's own domain: out of scope
                "https://careers-acme.icims.com/jobs/search?ss=1", "https://careers-acme.icims.com/jobs/intro",
                "https://icims.com.acme.example/jobs/1/x/job", "ftp://careers-acme.icims.com/jobs/1/x/job"):
        assert not icims.matches(url), url


def test_tab_is_this_job_never_another_on_the_same_site():
    assert icims.on_tab(LINK, APP)
    assert icims.on_tab(LINK, APP + "?in_iframe=1")
    assert not icims.on_tab(LINK, APP.replace("12345", "123456"))
    assert not icims.on_tab(LINK, APP.replace("careers-acme", "careers-beta"))
    assert not icims.on_tab(LINK, "https://careers-acme.icims.com/jobs/search?ss=1")


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
    """at(name) -> a page showing fixtures/icims/<name>, its frames loaded; nothing reaches the network."""
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
        page.goto(f"https://acme.example/{name}", wait_until="load")
        return page
    yield go
    assert set(asked) <= {"acme.example"}, asked
    context.close()


def test_start_box_read_in_its_frame_tick_captcha_next_left_to_the_applicant(at, capsys):
    qs = icims.read(at("start-box.html"))
    by = {q["title"]: q for q in qs}
    assert set(by) == {"Primary Email Address", "Yes, I agree to Acme Candidate Data Privacy Policy"}
    assert {q["page"] for q in qs} == {icims.START}
    assert by["Primary Email Address"]["key"] == "email"
    out = capsys.readouterr().out
    assert "tick 'Yes, I agree to Acme Candidate Data Privacy Policy' yourself" in out
    assert "security check (captcha) - yours to do" in out
    assert "click Next yourself - your email goes to this employer" in out and "every password and account is yours" in out
    assert icims.UNMEASURED not in out


def test_start_box_email_from_the_resume_tick_left_unticked(at):
    page = at("start-box.html")
    contact = {"name": "Ada Lovelace", "email": "ada@example.com", "phone": "555-0100"}
    drafted = {a["title"]: a for a in questions.draft(icims.read(page), contact)}
    tick = "Yes, I agree to Acme Candidate Data Privacy Policy"
    assert drafted["Primary Email Address"]["answer"] == "ada@example.com"
    assert questions.blank(drafted[tick].get("answer"))
    assert icims.fill(page, drafted["Primary Email Address"] | {"answer": "test@example.com"}, None) == "ok"
    frame = page.frame_locator("#icims_content_iframe")
    assert frame.locator("#email").input_value() == "test@example.com"
    assert icims.fill(page, drafted[tick] | {"answer": "Yes"}, None).startswith("ASK yours to do")
    assert not frame.locator("#accept_gdpr").is_checked()
    assert icims.fill(page, {"id": "#gone", "title": "Gone", "kind": "text", "answer": "x"}, None).startswith(questions.LATER)
    # Next is a button, never a question or a box the file lacks
    assert '[id="enterEmailSubmitButton"]' not in icims.ids_on_page(page)


def test_job_page_opens_the_start_box_by_its_link_never_a_click(at, monkeypatch):
    page = at("job.html")
    with pytest.raises(SystemExit, match="clicks Apply"):
        icims.read(page)
    monkeypatch.setattr(icims, "application_url", lambda url: "https://acme.example/start-box.html")
    icims.recover(page, LINK, wait=10)
    assert urlsplit(page.url).path == "/start-box.html"
    assert icims.start_box(icims.dom.snapshot(page))


def test_page_after_next_read_generically_password_consent_left(at, capsys):
    qs = icims.read(at("next.html"))
    assert [q["title"] for q in qs if q["kind"] != "yesno"] == ["First Name"] and qs[0]["page"] == "Create Your Account"
    out = capsys.readouterr().out
    assert icims.UNMEASURED in out and "password box 'Password' - yours to type" in out
    assert "(agreeing or consenting)" in out and "click Next yourself" not in out
