"""ADP Workforce Now: link shapes (params in any order), its tab among other employers' on one host,
the start box read off a local page (rebuilt from what measure read on one tenant), the applicant's
own steps."""
from pathlib import Path
from urllib.parse import urlsplit

import pytest

from apply import browser, dom, questions, systems
from apply.systems import adp

FIXTURES = Path(__file__).parent / "fixtures" / "adp"
BASE = "https://workforcenow.adp.com/mascsr/default/mdf/recruitment/recruitment.html"
CID = "00000000-acme-0000-0000-000000000000"
LINK = f"{BASE}?ccId=19000101_000001&cid={CID}&jobId=9200000000001_1&lang=en_US&utm_source=freehire.me"
APP = f"{BASE}?cid={CID}&ccId=19000101_000001&jobId=9200000000001_1&lang=en_US"
OTHER = LINK.replace("acme", "beta")


def test_links_match_in_any_order_and_open_one_canonical_page():
    for url in (LINK, f"{BASE}?jobId=9200000000001_1&cid={CID.upper()}&ccId=19000101_000001",
                f"{BASE}?selectedMenuKey=CareerCenter&ccId=19000101_000001&cid={CID}&jobId=9200000000001_1&lang=es_US"):
        assert systems.for_url(url) is adp, url
        assert adp.application_url(url) == APP
    assert adp.application_url(f"{BASE}?cid={CID}&jobId=9200000000001_1") == f"{BASE}?cid={CID}&jobId=9200000000001_1&lang=en_US"
    for url in (f"{BASE}?cid={CID}", f"{BASE}?jobId=9200000000001_1",
                "https://workforcenow.adp.com.evil.example/mascsr/default/mdf/recruitment/recruitment.html?cid=a&jobId=1",
                f"https://myjobs.adp.com/acme/cx/job-details?reqId={CID}"):
        assert not adp.matches(url), url


def test_tab_is_this_employers_job_never_another_on_the_same_host():
    # one job id was listed under two employers' cids (2026-10-03): the cid decides
    assert adp.on_tab(LINK, APP + "#top")
    assert adp.on_tab(LINK, f"https://workforcenow.adp.com/mascsr/default/mdf/recruitment/next.html?cid={CID}")
    assert not adp.on_tab(LINK, OTHER)
    assert not adp.on_tab(LINK, LINK.replace("_1&", "_2&"))
    assert not adp.on_tab(LINK, f"https://www.example.com/mascsr/default/mdf/recruitment/next.html?cid={CID}")


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
    """at(name) -> a page showing fixtures/adp/<name>; nothing reaches the network."""
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


def test_start_box_read_as_contact_boxes_continue_left_to_the_applicant(at, capsys):
    qs = adp.read(at("start-box.html"))
    by = {q["title"]: q for q in qs}
    assert set(by) == {"First Name", "Last Name", "Email", "Mobile Number"}
    assert {q["page"] for q in qs} == {adp.START}
    assert by["First Name"]["key"] == "first_name" and by["Last Name"]["key"] == "last_name"
    assert by["Email"]["kind"] == "email" and by["Mobile Number"]["kind"] == "phone"
    assert by["Mobile Number"]["required"]  # the employer's setting, not the box (3 of 3 tenants)
    out = capsys.readouterr().out
    assert "click Continue yourself" in out and "sign in with LinkedIn, Google or Facebook yourself" in out
    assert "verification" in out and adp.UNMEASURED not in out


def test_start_box_answers_from_the_resume(at):
    contact = {"name": "Ada Lovelace", "email": "ada@example.com", "phone": "555-0100"}
    got = {a["title"]: a["answer"] for a in questions.draft(adp.read(at("start-box.html")), contact)}
    assert got == {"First Name": "Ada", "Last Name": "Lovelace", "Email": "ada@example.com", "Mobile Number": "555-0100"}


def test_fill_types_contact_boxes_later_for_other_pages(at):
    page = at("start-box.html")
    qs = {q["title"]: q for q in adp.read(page)}
    assert adp.fill(page, qs["Email"] | {"answer": "test@example.com"}, None) == "ok"
    assert adp.fill(page, qs["First Name"] | {"answer": "Test"}, None) == "ok"
    assert page.input_value("#guestEmail") == "test@example.com"
    # the box keeps its +1 in front (live, 2026-10-03): a number without a code gets the box's own
    assert adp.fill(page, qs["Mobile Number"] | {"answer": "555-0100"}, None) == "ok"
    assert page.input_value("#login_view_phone") == "+1 555-0100"
    assert adp.fill(page, qs["Mobile Number"] | {"answer": "+44 20 7946 0000"}, None) == "ok"
    assert adp.fill(page, {"id": "#gone", "title": "Gone", "kind": "text", "answer": "x"}, None).startswith(questions.LATER)


def test_job_page_says_click_apply_first_and_recover_clicks_only_apply(at):
    page = at("job.html")
    with pytest.raises(SystemExit, match="clicks Apply"):
        adp.read(page)
    clicked = []
    page.expose_function("clicked", lambda name: clicked.append(name))
    page.evaluate("document.querySelectorAll('button').forEach(b => b.onclick = () => window.clicked(b.innerText))")
    adp.recover(page, LINK)
    assert clicked == ["Apply"]
    clicked.clear()
    page = at("start-box.html")  # box already open: nothing clicked (Continue never)
    page.evaluate("document.querySelectorAll('button').forEach(b => b.onclick = () => window.clicked(b.innerText))")
    adp.recover(page, LINK)
    assert clicked == []


def test_cookie_panel_never_a_question_never_ticked(at):
    # try read + ticked the hidden cookie choices on a live tenant before page_only (2026-10-03)
    for name in ("start-box.html", "next.html"):
        page = at(name)
        titles = [q["title"] for q in adp.read(page)]
        assert not {"Analytics", "checkbox label", "Cookie list search"} & set(titles), titles
        assert not [h for h in adp.ids_on_page(page) if "chkbox" in h or "select-all" in h]
    hidden = {"id": '[id="chkbox-id"]', "title": "checkbox label", "kind": "yesno", "answer": "Yes"}
    assert adp.fill(page, hidden, None).startswith("ASK")
    assert adp.fill(page, {"id": "role=checkbox|Analytics|Analytics", "title": "Analytics", "kind": "yesno",
                           "answer": "Yes"}, None).startswith("ASK")
    assert not page.is_checked("#chkbox-id")


def test_page_after_continue_read_generically_consent_and_password_left(at, capsys):
    page = at("next.html")
    qs = adp.read(page)
    assert "Employer" in [q["title"] for q in qs] and qs[0]["page"] == "Work History"
    terms = next(q for q in qs if "Terms" in q["title"])
    assert adp.fill(page, terms | {"answer": "Yes"}, None).startswith("ASK yours to do")
    assert not page.is_checked("#terms")
    out = capsys.readouterr().out
    assert adp.UNMEASURED in out and "password box 'Password' - yours to type" in out
    assert "(agreeing or consenting)" in out
    assert "Password" not in [dom.title(c["label"]) for c in dom.snapshot(page)["controls"] if c["hook"] in adp.ids_on_page(page)]
