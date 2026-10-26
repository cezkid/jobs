"""Loxo: link shapes, saved forms (anonymised, app/tests/fixtures/loxo) -> questions, the resume box's
shadow-root upload and each widget rule in real headless Chrome (fixtures/dom/loxo-form.html)."""
from pathlib import Path
from urllib.parse import urlsplit

import httpx
import pytest

from apply import browser, questions, systems
from apply.systems import loxo

FIXTURES = Path(__file__).parent / "fixtures"
ID = "MTIzNDUtYWJjZGVmZ2hpamtsbW5vcA=="
LINK = f"https://app.loxo.co/job/{ID}"
FORM_URL = f"{LINK}/form?source_type=app"


def form(tenant: str) -> dict:
    return {q["id"]: q for q in loxo.from_html((FIXTURES / "loxo" / f"tenant-{tenant}.html").read_text())}


def answered(q: dict, answer) -> dict:
    return q | {"answer": answer}


# --- links ---

def test_links_freehire_lists_land_on_the_form_page():
    assert systems.for_url(LINK + "?utm_source=freehire.me") is loxo
    assert loxo.application_url(LINK + "?utm_source=freehire.me") == FORM_URL
    assert loxo.application_url(FORM_URL) == FORM_URL
    # a firm's own label before the shared host; padding written %3D in a copied link
    assert loxo.parse_url(f"https://acme.app.loxo.co/job/{ID}/form") == ("acme.app.loxo.co", ID)
    assert loxo.parse_url(f" {LINK.replace('==', '%3D%3D')} ") == ("app.loxo.co", ID)
    # no padding: a 4-digit agency number gives a 28-letter id (1 of 6 postings, 2026-10-26)
    assert loxo.matches("https://app.loxo.co/job/NTc5NC1hYmNkZWZnaGlqa2xtbm9w?utm_source=freehire.me")


def test_other_links_refused():
    for url in ("https://loxo.co/job/" + ID, "https://app.loxo.co/jobs", f"https://app.loxo.co/job/{ID}/finish",
                f"https://app.loxo.co.example.com/job/{ID}", "https://jobs.lever.co/acme/1b2c"):
        assert not loxo.matches(url), url
    with pytest.raises(ValueError):
        loxo.parse_url("https://jobs.lever.co/acme/1b2c")


def test_this_applications_tab_by_posting_id():
    match = systems.tab_match(loxo, LINK + "?utm_source=freehire.me")
    assert match(FORM_URL) and match(f"{LINK}/finish?source_type=app")
    assert not match("https://app.loxo.co/job/OTk5OTktenp6enp6enp6enp6enp6eg==/form?source_type=app")


# --- saved forms -> questions ---

def test_contact_resume_and_opt_in_on_every_form():
    for tenant in "abcd":
        got = form(tenant)
        assert [(q["id"], q["kind"], q["key"]) for q in list(got.values())[:4]] == [
            ("name", "text", "name"), ("email", "email", "email"), ("phone", "phone", "phone"),
            ("resume_uploaded_file[]", "file", "resume")]
        # full name in one box, never split; no required mark on the contact boxes; the resume box's own *
        assert got["name"]["title"] == "Your Full Name" and not got["email"]["required"]
        assert got["resume_uploaded_file[]"]["required"] and got["resume_uploaded_file[]"]["title"] == "Resume/CV"
        # the opt-in under every form: its fine print (texts, Terms of Service) is what it agrees to
        opt = got[loxo.CONSENT]
        assert not opt["required"] and opt["native"] == "loxo:consent" and questions.signs(opt["title"])
        assert questions.texts_off(opt, {"text_messages": False})
        assert opt["title"].startswith("Yes, Acme Recruiting can contact me")
        # hidden boxes are no questions
        assert not {"authenticity_token", "utf8", "source_type_id", "form_template_id", "resume_source_type_id"} & set(got)
    assert list(form("d")) == ["name", "email", "phone", "resume_uploaded_file[]", loxo.CONSENT]


def test_employer_questions_kinds_options_and_required_mark():
    a = form("a")
    assert (a["custom_question_1932"]["kind"], a["custom_question_1932"]["options"]) == (
        "choice", ["Yes", "No - Open to Relocate", "No"])
    assert a["custom_question_1933"]["kind"] == "yesno" and a["custom_question_1933"]["native"] == "loxo:radio"
    # the asterisk inside the label (a number box inside it too) is no part of the question's words
    years = a["custom_question_1935"]
    assert (years["kind"], years["required"], years["title"]) == (
        "number", True, "How many years have you worked with React and Typescript?")
    assert a["custom_question_1936"]["kind"] == "longtext" and a["custom_question_1936"]["required"]
    assert a["custom_question_1939"]["kind"] == "longtext" and not a["custom_question_1939"]["required"]
    b = form("b")
    assert b["custom_question_868593"]["key"] == "linkedin" and b["custom_question_868593"]["required"]
    heard = b["custom_question_868596"]
    assert (heard["kind"], heard["native"], heard["required"]) == ("multichoice", "loxo:checkbox", False)
    assert heard["options"][:2] == ["LinkedIn", "Indeed"] and len(heard["options"]) == 8


def test_text_message_question_marked_only_by_its_asterisk_is_left_to_the_applicant():
    sms = form("c")["custom_question_664721"]
    assert (sms["kind"], sms["options"], sms["required"]) == ("yesno", ["No", "Yes"], True)
    assert questions.signs(sms["title"])
    drafted = questions.draft([sms], {"name": "Ada Lovelace"}, config={"text_messages": False})[0]
    assert drafted["answer"] is None  # required: theirs on the page, not silently left unticked


def test_no_form_or_unknown_posting_says_it_may_have_closed(monkeypatch):
    class Got:
        def __init__(self, status, text=""):
            self.status_code, self.text = status, text

        def raise_for_status(self):
            pass
    # unknown id: 404 + "Page not found" (2026-10-26)
    monkeypatch.setattr(httpx, "get", lambda *a, **k: Got(404, "<h1>Page not found</h1>"))
    with pytest.raises(ValueError, match="may have closed"):
        loxo.questions(LINK)
    assert loxo.closed(LINK).endswith("may have closed")
    monkeypatch.setattr(httpx, "get", lambda *a, **k: Got(200, "<html><h1>Jobs</h1></html>"))
    with pytest.raises(ValueError, match="may have closed"):
        loxo.questions(LINK)
    monkeypatch.setattr(httpx, "get", lambda url, **k: Got(200, (FIXTURES / "loxo" / "tenant-d.html").read_text())
                        if url == FORM_URL else Got(500))
    assert loxo.closed(LINK + "?utm_source=freehire.me") is None
    monkeypatch.setattr(httpx, "get", lambda *a, **k: Got(503))
    assert loxo.closed(LINK).startswith("can't tell")

    def down(*a, **k):
        raise httpx.ConnectError("no route")
    monkeypatch.setattr(httpx, "get", down)
    assert loxo.closed(LINK).startswith("can't tell")


# --- in real headless Chrome ---

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
def page(chrome):
    """fixtures/dom/loxo-form.html in headless Chrome; every other request refused."""
    context = chrome.new_context()
    context.route("**/*", lambda route: route.fulfill(path=str(FIXTURES / "dom" / "loxo-form.html"))
                  if urlsplit(route.request.url).hostname == "acme.example" else route.fulfill(status=404, body=""))
    pg = context.new_page()
    pg.goto("https://acme.example/loxo-form.html")
    yield pg
    context.close()


@pytest.fixture
def resume(tmp_path):
    f = tmp_path / "Ada_Lovelace_Resume.pdf"
    f.write_bytes(b"%PDF-1.4 test")
    return str(f)


def resume_q() -> dict:
    return form("d")["resume_uploaded_file[]"] | {"answer": True}


def host(page):
    return page.locator(f"{loxo.FORM} {loxo.FILE_HOST}").first


def test_resume_goes_in_the_shadow_box_shows_its_chip_and_would_go_once(page, resume):
    """The bug a user caught (2026-10-26): set on the hidden light-DOM input, the file would go at
    Submit but the box kept saying "Upload File". Set in the shadow root, the box shows its chip."""
    assert loxo.ids_on_page(page)[:4] == ["name", "email", "phone", "resume_uploaded_file[]"]
    assert not loxo.holds(page, resume_q())
    assert loxo.fill(page, resume_q(), resume) == "ok"
    assert loxo.file_state(host(page)) == {"chips": ["Ada_Lovelace_Resume.pdf"], "sent": ["Ada_Lovelace_Resume.pdf"],
                                           "shadow": True}
    assert page.locator(f"{loxo.FORM} {loxo.FILE_HOST} > input[type=file]").evaluate("e => e.files.length") == 0
    assert loxo.holds(page, resume_q())
    # filled again: the chip kept, never a second copy
    assert loxo.fill(page, resume_q(), resume) == "ok" and loxo.file_state(host(page))["chips"] == ["Ada_Lovelace_Resume.pdf"]
    assert loxo.fill(page, resume_q() | {"answer": None}, resume) == "skipped - upload not approved"


def test_resume_already_set_on_the_hidden_input_is_never_sent_twice(page, resume, tmp_path):
    page.locator(f"{loxo.FORM} {loxo.FILE_HOST} > input[type=file]").set_input_files(resume)
    assert loxo.file_state(host(page)) == {"chips": [], "sent": ["Ada_Lovelace_Resume.pdf"], "shadow": True}
    assert not loxo.holds(page, resume_q())  # the box shows nothing the form would send
    got = loxo.fill(page, resume_q(), resume)
    assert got.startswith("ASK the form would send 2 files") and "reload the page" in got
    # another file already in the box: one chip each, the user removes the extra
    page.reload()
    other = tmp_path / "Old_Resume.pdf"
    other.write_bytes(b"%PDF-1.4 old")
    host(page).evaluate_handle("h => h.shadowRoot.querySelector('input[type=file]')").as_element().set_input_files(str(other))
    got = loxo.fill(page, resume_q(), resume)
    assert got.startswith("ASK the resume box shows 2 files") and not loxo.holds(page, resume_q())


def test_each_widget_filled_and_read_back(page):
    a, b, c = form("a"), form("b"), form("c")
    rows = [
        (form("d")["name"], "Ada Lovelace"), (form("d")["phone"], "555-0100"),
        (b["custom_question_868593"], "https://linkedin.com/in/ada"),
        (b["custom_question_868594"], "No"),
        (b["custom_question_868596"] | {"options": ["LinkedIn", "Indeed", "Other"]}, ["indeed", "Other"]),
        (a["custom_question_1935"], "5"),
        (questions.question("custom_question_1936", "Link", "longtext", True, native="loxo:textarea"), "Their own words."),
    ]
    for q, answer in rows:
        assert loxo.fill(page, answered(q, answer), None) == "ok", q["id"]
        assert loxo.holds(page, answered(q, answer)), q["id"]
    ticks = page.locator('input[name="custom_question_868596[]"]').evaluate_all("es => es.map(e => e.checked)")
    assert ticks == [False, True, True]
    # radio changed: the other one unticked, read back as the page shows it
    assert loxo.fill(page, answered(b["custom_question_868594"], "Yes"), None) == "ok"
    assert not loxo.holds(page, answered(b["custom_question_868594"], "No"))
    assert loxo.fill(page, answered(b["custom_question_868594"] | {"kind": "choice"}, "Maybe"), None) == \
        "ASK no option 'maybe'; offered: Yes, No"
    # the text-message question + the opt-in box: the applicant's own tick, never ours
    assert loxo.fill(page, answered(c["custom_question_664721"], "Yes"), None).startswith("ASK yours to do on the page")
    assert loxo.fill(page, answered(c[loxo.CONSENT], "Yes"), None).startswith("ASK yours to do on the page")
    assert page.locator("#contact-consent-box").is_checked() is False
    assert loxo.fill(page, answered(questions.question("custom_question_9", "Gone", "text", False), "x"), None) == \
        "FAIL question not on page"
