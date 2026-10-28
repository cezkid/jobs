"""Dover: link shapes, saved form definitions (anonymised, app/tests/fixtures/dover) -> questions, each widget rule
on a copy of the page Dover's script renders (fixtures/dover/apply.html; nothing reaches the network)."""
import json
from pathlib import Path
from urllib.parse import urlsplit

import httpx
import pytest
from test_apply_in_window import playwright_chrome  # noqa: F401 - fixture

from apply import systems
from apply.systems import dover

FIXTURES = Path(__file__).parent / "fixtures" / "dover"
JOB = "00000000-0000-4000-8000-000000000001"
LINK = f"https://app.dover.com/apply/acme/{JOB}"


def form(tenant: str) -> list[dict]:
    return dover.from_definition(json.loads((FIXTURES / f"tenant-{tenant}.json").read_text()))


# --- links ---

def test_links_from_freehire_and_job_boards_land_on_the_form():
    for url in (LINK + "?utm_source=freehire.me", LINK + "/?utm_source=adzuna&utm_medium=adzuna", " " + LINK + " ",
                LINK.replace(JOB, JOB.upper())):
        assert systems.for_url(url) is dover, url
        assert dover.application_url(url) == LINK
    # the employer part keeps its case: the page is the same either way, the link stays as given
    assert dover.parse_url(f"https://app.dover.com/apply/Acme/{JOB}") == ("Acme", JOB)


def test_other_dover_pages_refused():
    for url in ("https://app.dover.com/apply/acme", "https://app.dover.com/acme/careers/00000000-0000-4000-9000-000000000001",
                f"https://app.dover.com/apply/acme/{JOB}/extra", "https://app.dover.com/apply/acme/12345",
                f"https://app.dover.com.example.com/apply/acme/{JOB}", "https://jobs.lever.co/acme/1b2c"):
        assert not dover.matches(url), url
    with pytest.raises(ValueError):
        dover.parse_url("https://jobs.lever.co/acme/1b2c")


def test_on_tab_the_same_posting_only():
    assert systems.on_tab(dover, LINK, LINK + "?utm_source=freehire.me")
    assert not systems.on_tab(dover, LINK, "https://app.dover.com/apply/acme/00000000-0000-4000-8000-000000000002")


# --- saved definitions -> questions ---

def test_fixed_boxes_then_dovers_own_then_the_employers_resume_last():
    a = form("a")
    assert [(q["id"], q["kind"], q["key"], q["required"]) for q in a[:5]] == [
        ("firstName", "text", "first_name", True), ("lastName", "text", "last_name", True), ("email", "email", "email", True),
        ("linkedinUrl", "url", "linkedin", True), ("phoneNumber", "phone", "phone", True)]
    assert (a[-1]["id"], a[-1]["kind"], a[-1]["key"], a[-1]["required"], a[-1]["title"]) == ("resume", "file", "resume", True, "Resume")
    custom = a[5:-1]
    assert [q["kind"] for q in custom] == ["longtext", "longtext", "text", "choice"]
    assert all(q["id"].startswith("00000000-") and q["key"] is None for q in custom)
    heard = custom[-1]
    assert heard["native"] == "dover:radio" and heard["options"][:2] == ["Recruiter", "LinkedIn"]


def test_yes_no_radios_tick_lists_and_links_by_title():
    b = {q["title"]: q for q in form("b")}
    office = next(q for t, q in b.items() if t.startswith("This role is full-time"))
    assert (office["kind"], office["options"], office["native"]) == ("yesno", ["Yes", "No"], "dover:radio")
    layers = next(q for t, q in b.items() if t.startswith("Which layers"))
    assert layers["kind"] == "multichoice" and layers["native"] == "dover:checkbox" and len(layers["options"]) == 6
    assert b["GitHub / portfolio URL"]["key"] == "github"
    assert not b["LinkedIn Profile URL"]["required"] and not b["Phone Number"]["required"]


def test_hidden_question_never_asked_resume_may_be_optional():
    c = {q["id"]: q for q in form("c")}
    assert "phoneNumber" not in c  # hidden in the definition: the page draws no box
    assert c["linkedinUrl"]["required"] and not c["resume"]["required"]


def test_linkedin_required_by_the_posting_flag_and_empty_lists_skipped():
    data = json.loads((FIXTURES / "tenant-b.json").read_text())
    data["require_linkedin_profile_url"] = True
    data["application_questions"].append({"id": "x", "question": "Pick one", "input_type": "MULTIPLE_CHOICE", "required": True,
                                          "question_type": "CUSTOM", "multiple_choice_options": [], "hidden": False,
                                          "order_index": 99})
    got = {q["id"]: q for q in dover.from_definition(data)}
    assert got["linkedinUrl"]["required"] and "x" not in got


class Answer:
    def __init__(self, status: int, body: dict):
        self.status_code, self.body = status, body

    def json(self):
        return self.body

    def raise_for_status(self):
        if self.status_code >= 400:
            raise httpx.HTTPStatusError("x", request=None, response=None)


def test_questions_read_by_the_job_id_closed_said_plainly(monkeypatch):
    asked = []
    data = json.loads((FIXTURES / "tenant-a.json").read_text())
    monkeypatch.setattr(dover.httpx, "get", lambda url, **kw: asked.append(url) or Answer(200, data))
    assert [q["id"] for q in dover.questions(LINK + "?utm_source=freehire.me")][:3] == ["firstName", "lastName", "email"]
    assert asked == [f"https://app.dover.com/api/v1/inbound/application-portal-job/{JOB}"]
    assert dover.closed(LINK) is None
    monkeypatch.setattr(dover.httpx, "get", lambda url, **kw: Answer(404, {"detail": "Not found."}))
    with pytest.raises(ValueError, match="filled or deactivated"):
        dover.questions(LINK)
    assert "filled or deactivated" in dover.closed(LINK)
    monkeypatch.setattr(dover.httpx, "get", lambda url, **kw: Answer(200, data | {"active": False}))
    assert "no longer active" in dover.closed(LINK)
    monkeypatch.setattr(dover.httpx, "get", lambda url, **kw: Answer(503, {}))
    assert dover.closed(LINK).startswith("can't tell")


def test_phone_typed_as_the_pages_check_takes_it():
    assert dover.phone_typed("555-0100") == "555-0100"
    assert dover.phone_typed("(555) 010-0100") == "(555) 010-0100"
    assert dover.phone_typed("+1 (555) 010-0100") == "+1 555 010 0100"
    assert dover.phone_typed("555-0100 ext. 12") is None


# --- the page copy ---

@pytest.fixture(scope="module")
def chrome(playwright_chrome):  # noqa: F811
    return playwright_chrome


@pytest.fixture
def page(chrome):
    """The apply page copy; nothing reaches the network."""
    context = chrome.new_context()
    asked = []

    def serve(route):
        u = urlsplit(route.request.url)
        asked.append(u.hostname)
        return route.fulfill(path=str(FIXTURES / "apply.html")) if u.hostname == "acme.example" else route.abort()

    context.route("**/*", serve)
    p = context.new_page()
    p.goto("https://acme.example/apply")
    yield p
    assert set(asked) <= {"acme.example"}, asked
    assert not p.evaluate("window.submitted || window.autofilled || false")
    context.close()


OWN = ("firstName", "lastName", "email", "linkedinUrl", "phoneNumber")


def q(id, kind, answer, native=None, options=(), key=None, title="Question"):
    native = native or (f"dover:{id}" if id in OWN else "dover:text")
    return {"id": id, "title": title, "kind": kind, "key": key, "native": native, "required": True,
            "options": list(options), "answer": answer}


ROLE = "00000000-0000-4000-a000-000000000003"
HEARD = "00000000-0000-4000-a000-000000000006"
LAYERS = "Which layers of the stack have you personally shipped working code in? Select all that apply."


def test_ids_on_page(page):
    assert dover.ids_on_page(page) == ["firstName", "lastName", "email", "linkedinUrl", "phoneNumber", ROLE, HEARD, "resume"]


def test_text_boxes_filled_and_read_back(page):
    for item in (q("firstName", "text", "Test"), q("email", "email", "test@example.com"),
                 q("linkedinUrl", "url", "https://www.linkedin.com/in/test"), q("phoneNumber", "phone", "+1 (555) 010-0100"),
                 q(ROLE, "longtext", "Line one\nLine two")):
        assert dover.fill(page, item, None) == "ok", item["id"]
        assert dover.holds(page, item), item["id"]
    assert page.locator('[name="phoneNumber"]').input_value() == "+1 555 010 0100"
    assert not dover.holds(page, q("firstName", "text", "Someone"))
    assert dover.fill(page, q("phoneNumber", "phone", "555-0100 x12"), None).startswith("ASK")


def test_radio_by_its_value(page):
    item = q(HEARD, "choice", "LinkedIn", "dover:radio", ["Recruiter", "LinkedIn", "Other"])
    assert dover.fill(page, item, None) == "ok" and dover.holds(page, item)
    assert dover.fill(page, q(HEARD, "choice", "Newspaper", "dover:radio"), None).startswith("ASK no option 'Newspaper'")


def test_tick_list_found_under_its_words(page):
    item = q("layers", "multichoice", ["Web frontend", "Backend / API"], "dover:checkbox", title=LAYERS)
    assert dover.fill(page, item, None) == "ok" and dover.holds(page, item)
    item["answer"] = ["Backend / API"]
    assert dover.fill(page, item, None) == "ok" and dover.holds(page, item)
    assert page.locator("form input[type=checkbox]:checked").count() == 1
    assert dover.fill(page, q("gone", "multichoice", ["x"], "dover:checkbox", title="Not here"), None) == "FAIL question not on page"


def test_resume_in_its_own_box_never_the_autofill_one(page, tmp_path):
    pdf = tmp_path / "Test_Applicant_Resume.pdf"
    pdf.write_bytes(b"%PDF-1.4\n%%EOF\n")
    item = q("resume", "file", True, "dover:resume", key="resume")
    assert not dover.holds(page, item)
    assert dover.fill(page, item, str(pdf)) == "ok" and dover.holds(page, item)
    assert page.evaluate("window.autofillChosen || 0") == 0
    assert dover.fill(page, {**item, "answer": False}, str(pdf)) == "skipped - upload not approved"


def test_long_file_name_read_back_as_the_page_cuts_it():
    assert dover.shown_name("a" * 40 + ".pdf") == "a" * 35 + "...pdf"
    assert dover.shown_name("Test_Applicant_Resume.pdf") == "Test_Applicant_Resume.pdf"


def test_a_file_already_shown_is_kept_or_replaced_never_a_dead_end(page, tmp_path):
    first, second = tmp_path / "Old_Resume.pdf", tmp_path / "Test_Applicant_Resume.pdf"
    for f in (first, second):
        f.write_bytes(b"%PDF-1.4\n%%EOF\n")
    item = q("resume", "file", True, "dover:resume", key="resume")
    assert dover.fill(page, item, str(first)) == "ok"
    assert dover.resume_box(page) is None  # the box gives way to "Resume: <name>" + Remove
    assert dover.fill(page, item, str(first)) == "ok"  # same file: left as it is
    assert dover.fill(page, item, str(second)) == "ok"
    assert "Resume: Test_Applicant_Resume.pdf" in dover.resume_says(page) and "Old_Resume" not in dover.resume_says(page)


def test_prepare_says_the_page_records_what_is_typed():
    from apply import form as apply_form
    note = apply_form.recorded_note(dover)
    assert note.startswith("Dover: the page records the visit for PostHog") and "before Submit" in note
    assert apply_form.recorded_note(systems.for_url("https://jobs.lever.co/acme/1b2c")) == ""
    assert apply_form.recorded_note(None) == ""
