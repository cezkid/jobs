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
SITE = "careers-acme.icims.com"  # fixtures served as iCIMS: a page off icims.com reads as the employer's own site


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
        return route.fulfill(path=str(file)) if u.hostname == SITE and file.is_file() else route.abort()

    context.route("**/*", serve)
    page = context.new_page()

    def go(name):
        page.goto(f"https://{SITE}/{name}", wait_until="load")
        return page
    yield go
    assert set(asked) <= {SITE}, asked
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
    monkeypatch.setattr(icims, "application_url", lambda url: f"https://{SITE}/start-box.html")
    icims.recover(page, LINK, wait=10)
    assert urlsplit(page.url).path == "/start-box.html"
    assert icims.start_box(icims.dom.snapshot(page))


def test_page_after_next_read_generically_password_consent_left(at, capsys):
    qs = icims.read(at("next.html"))
    assert [q["title"] for q in qs if q["kind"] != "yesno"] == ["First Name"] and qs[0]["page"] == "Create Your Account"
    out = capsys.readouterr().out
    assert icims.UNMEASURED in out and "password box 'Password' - yours to type" in out
    assert "(agreeing or consenting)" in out and "click Next yourself" not in out


# --- read back ---

def test_holds_reads_the_email_box_as_shown_in_its_frame_tick_never_ours(at):
    page = at("start-box.html")
    by = {q["title"]: q for q in icims.read(page)}
    q = by["Primary Email Address"] | {"answer": "test@example.com"}
    assert not icims.holds(page, q)  # empty box: nothing shows
    assert icims.fill(page, q, None) == "ok" and icims.holds(page, q)
    assert not icims.holds(page, q | {"answer": "Test@example.com"})  # exact, as typed
    frame = page.frame_locator("#icims_content_iframe")
    frame.locator("#email").fill("")
    assert not icims.holds(page, q)
    frame.locator("#accept_gdpr").check()
    assert not icims.holds(page, by["Yes, I agree to Acme Candidate Data Privacy Policy"] | {"answer": "Yes"})


# --- closed ---

def test_gone_page_says_closed_in_its_own_words_before_its_boxes(at):
    from apply import form
    # iCIMS's job search shows boxes in place of a gone posting's start box: never read as the form
    page = at("gone.html")
    said = form.closed(page, icims, LINK)
    assert said == "the posting says it's closed (\"The job that you were looking for either does not exist or is no longer open\")"
    icims.recover(page, LINK, wait=10)
    assert urlsplit(page.url).path == "/gone.html"  # left as is, no start box opened
    with pytest.raises(SystemExit, match=r"no longer open\"\) - nothing to read; ask the user"):
        icims.read(page)
    # marked not found, words unseen: still gone
    page.frame_locator("#icims_content_iframe").locator("p").evaluate("p => p.remove()")
    assert icims.gone_now(page).startswith("iCIMS shows its job search marked 'not found'")
    # a start box showing = open
    assert form.closed(at("start-box.html"), icims, LINK) is None


def test_link_landing_on_the_employers_own_site_may_have_closed(at):
    page = at("start-box.html")
    page.route("https://careers.acme.example/**", lambda r: r.fulfill(body="<input id=q>", content_type="text/html"))
    page.goto("https://careers.acme.example/all-jobs", wait_until="load")
    assert icims.gone(page, LINK).startswith("the posting's link now leads to the employer's own careers site")
    with pytest.raises(SystemExit, match="employer's own careers site"):
        icims.read(page)


class Got:
    def __init__(self, status):
        self.status_code = status


def test_closed_reads_the_job_page_answer_never_guesses(monkeypatch):
    import httpx
    asked = []
    monkeypatch.setattr(httpx, "get", lambda url, **k: asked.append(url) or Got(200))
    assert icims.closed(LINK) is None
    assert asked == ["https://careers-acme.icims.com/jobs/12345/test-job/job?in_iframe=1"]
    # taken down: 410 (3 of 19 links, 2026-10-06)
    monkeypatch.setattr(httpx, "get", lambda *a, **k: Got(410))
    assert icims.closed(LINK) == "iCIMS says the job either does not exist or is no longer open - it may have closed"
    monkeypatch.setattr(httpx, "get", lambda *a, **k: Got(503))
    assert icims.closed(LINK) == "can't tell if the posting is open - iCIMS answered 503"

    def down(*a, **k):
        raise httpx.ConnectError("no route")
    monkeypatch.setattr(httpx, "get", down)
    assert icims.closed(LINK) == "can't tell if the posting is open - iCIMS didn't answer (ConnectError)"
