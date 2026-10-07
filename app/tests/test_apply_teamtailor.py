"""Teamtailor: link shapes (any host, the path is the tell), saved form frames (anonymised,
app/tests/fixtures/teamtailor) -> questions, each widget rule on those forms with a copy of the parts of
Teamtailor's own scripts the filler reads (fixtures/teamtailor/page.js; nothing reaches the network)."""
from pathlib import Path
from urllib.parse import urlsplit

import httpx
import pytest

from apply import browser, questions, systems
from apply.systems import teamtailor

FIXTURES = Path(__file__).parent / "fixtures" / "teamtailor"
LINK = "https://acme.na.teamtailor.com/jobs/700001-software-engineer"
APPLY = LINK + "/applications/new"
OWN = "https://jobs.acme.com/jobs/8400001-data-analyst"


def frame(tenant: str) -> str:
    return (FIXTURES / f"tenant-{tenant}.html").read_text()


def form(tenant: str) -> dict:
    return {q["id"]: q for q in teamtailor.read_form(frame(tenant))}


def answer(n: int, field: str) -> str:
    return f"candidate[answers_attributes][{n}][{field}]"


# --- links ---

def test_links_freehire_lists_land_on_the_application_form():
    assert systems.for_url(LINK + "?utm_source=freehire.me") is teamtailor
    assert systems.for_url(OWN) is teamtailor  # the employer's own domain: the path is the tell
    assert teamtailor.application_url(LINK + "?utm_source=freehire.me") == APPLY
    assert teamtailor.application_url(APPLY) == APPLY
    assert teamtailor.application_url("http://ACME.na.teamtailor.com/jobs/700001-software-engineer/") == APPLY
    assert teamtailor.parse_url(" " + OWN + " ") == ("https://jobs.acme.com", "8400001", "data-analyst")


def test_other_links_refused():
    for url in ("https://acme.teamtailor.com/jobs", "https://acme.teamtailor.com/jobs/123-x",
                "https://acme.teamtailor.com/careers/jobs/700001-x", "https://acme.teamtailor.com/jobs/700001-x/extra",
                "https://job-boards.greenhouse.io/acme/jobs/1234567", "https://jobs.smartrecruiters.com/Acme/744000012345-x"):
        assert not teamtailor.matches(url), url
    with pytest.raises(ValueError):
        teamtailor.parse_url("https://jobs.lever.co/acme/1b2c")


def test_on_tab_the_same_posting_even_after_a_new_slug():
    assert systems.on_tab(teamtailor, LINK, APPLY + "?x=1")
    assert systems.on_tab(teamtailor, LINK, "https://acme.na.teamtailor.com/jobs/700001-senior-software-engineer")
    assert not systems.on_tab(teamtailor, LINK, "https://acme.na.teamtailor.com/jobs/700002-other/applications/new")
    assert not systems.on_tab(teamtailor, LINK, "https://other.na.teamtailor.com/jobs/700001-software-engineer")


# --- saved form frames -> questions ---

def test_standard_boxes_by_their_page_names():
    a = form("a")
    got = {id: (a[id]["kind"], a[id]["key"], a[id]["required"]) for id in teamtailor.STANDARD}
    assert got == {"candidate[first_name]": ("text", "first_name", True), "candidate[last_name]": ("text", "last_name", True),
                   "candidate[email]": ("email", "email", True), "candidate[phone]": ("phone", "phone", True),
                   "candidate[location][query]": ("location", "location", True)}
    assert a["candidate[first_name]"]["title"] == "First name"  # no asterisk, no screen-reader "Required"
    assert not form("c")["candidate[phone]"]["required"]
    assert "candidate[location][query]" not in form("b")


def test_files_by_their_link_box_never_the_preview_template_or_hidden_boxes():
    a = form("a")
    resume, more = a[teamtailor.RESUME], a["candidate[file_remote_url]"]
    assert (resume["kind"], resume["key"], resume["required"]) == ("file", "resume", True)
    assert (more["kind"], more["required"]) == ("file", False) and more["key"] != "resume"
    ids = [q["id"] for q in teamtailor.read_form(frame("a"))]
    assert ids.count(teamtailor.RESUME) == 1
    assert not [i for i in ids if i.startswith("candidate[location][") and i != "candidate[location][query]"]
    assert "authenticity_token" not in ids and "candidate[linkedin_url]" not in ids


def test_employer_questions_by_type_with_the_line_under_the_label():
    a = form("a")
    work = a[answer(0, "boolean")]
    assert (work["kind"], work["native"], work["required"], work["options"]) == ("yesno", "teamtailor:qualifying", True, ["Yes", "No"])
    assert work["title"].startswith("Work Eligibility for Canada - Are you currently legally eligible")
    assert a[answer(2, "text")]["key"] == "linkedin"  # LinkedIn = the employer's own text question
    assert (a[answer(3, "number")]["kind"], a[answer(3, "number")]["native"]) == ("number", "teamtailor:number")
    assert not a[answer(4, "text")]["required"]
    b = form("b")
    pay = b[answer(1, "range")]
    assert (pay["kind"], pay["native"]) == ("number", "teamtailor:range")
    assert pay["title"].endswith("(0 to 10000 USD, steps of 50)")
    english = b[answer(2, "choice")]
    assert (english["kind"], english["native"], english["options"]) == (
        "choice", "teamtailor:choice", ["Basic - B2", "Advanced - C1", "Native - C2"])
    assert b[answer(3, "boolean")]["native"] == "teamtailor:boolean"
    c = form("c")
    offices = c["candidate[location_ids][]"]
    assert (offices["kind"], offices["native"], offices["options"]) == (
        "multichoice", "teamtailor:choices", ["Shelbyville, IL", "Springfield, IL"])
    assert c["candidate[job_applications_attributes][0][cover_letter]"]["kind"] == "longtext"


def test_consent_boxes_are_the_applicants_own():
    for tenant, id in (("a", "candidate[consent_given]"), ("a", "candidate[consent_given_future_jobs]"),
                       ("c", "candidate[consent_given_sms]")):
        q = form(tenant)[id]
        assert q["native"] == "teamtailor:consent"
        assert "yours to do on the page" in teamtailor.fill(None, q | {"answer": "Yes"}, None)


# --- questions + closed over plain HTTP ---

class Got:
    def __init__(self, status=200, text=""):
        self.status_code, self.text = status, text

    def raise_for_status(self):
        if self.status_code >= 400:
            raise httpx.HTTPStatusError(str(self.status_code), request=None, response=type("R", (), {"status_code": self.status_code})())


POSTING = '<html><link href="https://assets-aws.teamtailor-cdn.com/x.css">{}</html>'
CLOSED_PAGE = POSTING.format("<h1>Software Engineer</h1><p>This job is no longer active.</p>")


def test_questions_asked_for_as_the_posting_frame(monkeypatch):
    asked = []
    monkeypatch.setattr(httpx, "get", lambda url, **kw: asked.append((url, kw["headers"])) or Got(text=frame("b")))
    qs = teamtailor.questions(LINK + "?utm_source=freehire.me")
    assert asked == [(APPLY, {"Turbo-Frame": "application_form"})] and "candidate[first_name]" in [q["id"] for q in qs]


def test_closed_or_unknown_posting_says_so(monkeypatch):
    monkeypatch.setattr(httpx, "get", lambda url, **kw: Got(text=CLOSED_PAGE))
    with pytest.raises(ValueError, match="no longer active"):
        teamtailor.questions(LINK)
    assert teamtailor.closed(LINK).startswith("posting closed on Teamtailor")
    monkeypatch.setattr(httpx, "get", lambda url, **kw: Got(404))
    assert "may have closed" in teamtailor.closed(LINK)
    monkeypatch.setattr(httpx, "get", lambda url, **kw: Got(text=frame("a")))
    assert teamtailor.closed(LINK) is None
    monkeypatch.setattr(httpx, "get", lambda url, **kw: Got(503))
    assert teamtailor.closed(LINK).startswith("can't tell")
    monkeypatch.setattr(httpx, "get", lambda url, **kw: Got(text=POSTING.format("<h1>Software Engineer</h1>")))
    assert "may have closed" in teamtailor.closed(LINK)
    # an own-domain page with the right path but nothing of Teamtailor's
    monkeypatch.setattr(httpx, "get", lambda url, **kw: Got(text="<html><h1>Our jobs</h1></html>"))
    with pytest.raises(ValueError, match="not a Teamtailor form"):
        teamtailor.questions(OWN)


# --- the page ---

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


def open_form(chrome, tenant: str):
    """The saved form + page.js on acme.example; nothing reaches the network."""
    context = chrome.new_context()
    asked = []
    body = ('<html><head><style>.hidden{display:none}</style></head><body>' + frame(tenant)
            + '<script src="/page.js"></script></body></html>')

    def serve(route):
        u = urlsplit(route.request.url)
        asked.append(u.hostname)
        if u.hostname != "acme.example":
            return route.abort()
        if u.path == "/page.js":
            return route.fulfill(path=str(FIXTURES / "page.js"), content_type="text/javascript")
        return route.fulfill(body=body, content_type="text/html")

    context.route("**/*", serve)
    p = context.new_page()
    p.goto(f"https://acme.example/{tenant}")
    return context, p, asked


@pytest.fixture(params=["a", "b", "c"])
def any_page(chrome, request):
    context, p, asked = open_form(chrome, request.param)
    yield request.param, p
    context.close()


def tenant_page(tenant):
    @pytest.fixture
    def fixture(chrome):
        context, p, asked = open_form(chrome, tenant)
        yield p
        assert set(asked) <= {"acme.example"}, asked
        assert not p.evaluate("window.submitted || false")
        assert not p.locator('input[name^="candidate[consent_given"]').evaluate_all("bs => bs.some(b => b.checked)")
        context.close()
    return fixture


page_a, page_b, page_c = tenant_page("a"), tenant_page("b"), tenant_page("c")


def q(id, kind, answer, native="teamtailor:text", options=(), key=None, title="Question"):
    return {"id": id, "title": title, "kind": kind, "key": key, "native": native, "required": True,
            "options": list(options), "answer": answer}


def test_ids_on_page_are_the_questions_read_off_the_saved_form(any_page):
    tenant, p = any_page
    p.wait_for_selector(f"{teamtailor.RESUME_BOX} input[type=file]", state="attached")
    assert teamtailor.ids_on_page(p) == [q["id"] for q in teamtailor.read_form(frame(tenant))]


def test_text_number_and_letter_filled_and_read_back(page_a):
    for item in (q("candidate[first_name]", "text", "Test", "teamtailor:standard", key="first_name"),
                 q("candidate[email]", "email", "test@example.com", "teamtailor:standard", key="email"),
                 q(answer(1, "text"), "text", "Springfield, IL"),
                 q(answer(3, "number"), "number", "$85,000", "teamtailor:number"),
                 q("candidate[job_applications_attributes][0][cover_letter]", "longtext", "Line one\nLine two")):
        assert teamtailor.fill(page_a, item, None) == "ok" and teamtailor.holds(page_a, item), item["id"]
    assert page_a.locator(f'[name="{answer(3, "number")}"]').input_value() == "85000"
    assert not teamtailor.holds(page_a, q("candidate[first_name]", "text", "Someone", "teamtailor:standard"))
    assert teamtailor.fill(page_a, q(answer(3, "number"), "number", "competitive", "teamtailor:number"), None).startswith("ASK")


def test_phone_kept_in_international_form(page_a):
    phone = q("candidate[phone]", "phone", "(555) 010-0100", "teamtailor:standard", key="phone")
    assert teamtailor.fill(page_a, phone, None) == "ok" and teamtailor.holds(page_a, phone)
    assert page_a.locator('[name="candidate[phone]"]').input_value() == "+15550100100"
    assert "country code" in teamtailor.fill(page_a, phone | {"answer": "0100 1234"}, None)
    assert teamtailor.fill(page_a, phone | {"answer": "+44 12"}, None).startswith("ASK")


def test_address_picked_from_teamtailors_places_and_read_back(page_a):
    where = q("candidate[location][query]", "location", "Springfield, MO", "teamtailor:standard", key="location")
    assert teamtailor.fill(page_a, where, None) == "ok" and teamtailor.holds(page_a, where)
    assert page_a.locator('[name="candidate[location][query]"]').input_value() == "Springfield, MO, USA"
    assert teamtailor.fill(page_a, where | {"answer": "Springfield"}, None).startswith("ASK no place matches 'Springfield' alone")
    assert teamtailor.fill(page_a, where | {"answer": "Chicago, IL"}, None).startswith("ASK no place matched")
    assert not teamtailor.holds(page_a, where)
    page_a.evaluate("window.PLACES_DOWN = true")
    assert "the page says 'Unable to fetch address suggestions. Please try again.'" in teamtailor.fill(page_a, where, None)


def test_typed_in_while_the_cookie_notice_holds_the_keyboard(page_a):
    """A takeover cookie notice traps focus (2 of 10 postings live): typing lands nowhere, the value still goes in
    with the box's own events - and the notice is never clicked."""
    page_a.evaluate("""() => { const a = document.createElement('a'); a.id = 'cookie'; a.href = '#'; a.textContent = 'Accept all';
        document.body.append(a); window.accepted = false; a.addEventListener('click', () => window.accepted = true);
        document.addEventListener('focusin', e => { if (e.target !== a) a.focus(); }, true); }""")
    where = q("candidate[location][query]", "location", "Springfield, MO", "teamtailor:standard", key="location")
    for item in (q("candidate[first_name]", "text", "Test", "teamtailor:standard", key="first_name"),
                 q("candidate[phone]", "phone", "(555) 010-0100", "teamtailor:standard", key="phone"), where):
        assert teamtailor.fill(page_a, item, None) == "ok" and teamtailor.holds(page_a, item), item["id"]
    assert page_a.locator('[name="candidate[phone]"]').input_value() == "+15550100100"
    assert page_a.evaluate("document.activeElement.id") == "cookie" and not page_a.evaluate("window.accepted")


def test_requirement_answered_no_shows_the_forms_message_and_the_answer_stays(page_a):
    work = q(answer(0, "boolean"), "yesno", "No", "teamtailor:qualifying", ["Yes", "No"])
    got = teamtailor.fill(page_a, work, None)
    assert got.startswith("ASK the form says") and "never changed" in got
    assert teamtailor.holds(page_a, work)  # still No: the user's answer, never changed to get past
    yes = work | {"answer": "Yes"}
    assert teamtailor.fill(page_a, yes, None) == "ok" and teamtailor.holds(page_a, yes) and not teamtailor.holds(page_a, work)


def test_yes_no_radios_by_value_choices_by_their_words(page_b):
    llm = q(answer(6, "boolean"), "yesno", "Yes", "teamtailor:boolean", ["Yes", "No"])
    assert teamtailor.fill(page_b, llm, None) == "ok" and teamtailor.holds(page_b, llm)
    assert page_b.locator(f'[name="{answer(6, "boolean")}"][value=true]').is_checked()
    english = q(answer(2, "choice"), "choice", "advanced - c1", "teamtailor:choice")
    assert teamtailor.fill(page_b, english, None) == "ok" and teamtailor.holds(page_b, english)
    assert teamtailor.fill(page_b, english | {"answer": "Fluent"}, None).startswith("ASK no option 'fluent'")
    assert not teamtailor.holds(page_b, english | {"answer": "Native - C2"})


def test_the_forms_own_office_ticks(page_c):
    offices = q("candidate[location_ids][]", "multichoice", ["Springfield, IL"], "teamtailor:choices")
    assert teamtailor.fill(page_c, offices, None) == "ok" and teamtailor.holds(page_c, offices)
    both = offices | {"answer": ["Springfield, IL", "Shelbyville, IL"]}
    assert teamtailor.fill(page_c, both, None) == "ok" and teamtailor.holds(page_c, both) and not teamtailor.holds(page_c, offices)
    assert teamtailor.fill(page_c, offices, None) == "ok" and teamtailor.holds(page_c, offices)


def test_slider_set_through_its_own_number_box(page_b):
    pay = q(answer(1, "range"), "number", "5000", "teamtailor:range")
    assert teamtailor.fill(page_b, pay, None) == "ok" and teamtailor.holds(page_b, pay)
    off_step = teamtailor.fill(page_b, pay | {"answer": "5025"}, None)
    assert off_step.startswith("ASK the slider runs 0 to 10000 in steps of 50")
    assert not teamtailor.holds(page_b, pay | {"answer": "5025"})


def test_consent_never_ticked(page_a):
    for id in ("candidate[consent_given]", "candidate[consent_given_future_jobs]"):
        got = teamtailor.fill(page_a, q(id, "yesno", "Yes", "teamtailor:consent", ["Yes", "No"], title="I agree"), None)
        assert "yours to do on the page" in got


def test_resume_chosen_read_back_by_the_name_and_link_the_box_shows(page_a, tmp_path):
    pdf = tmp_path / "Test_Resume.pdf"
    pdf.write_bytes(b"%PDF-1.4 test")
    resume = q(teamtailor.RESUME, "file", True, "teamtailor:upload", key="resume", title="Upload resume")
    assert not teamtailor.holds(page_a, resume)
    assert teamtailor.fill(page_a, resume | {"answer": False}, str(pdf)) == "skipped - upload not approved"
    assert teamtailor.fill(page_a, resume, str(pdf)) == "ok" and teamtailor.holds(page_a, resume)


def test_resume_refused_in_the_pages_own_words(page_a, tmp_path):
    page_a.evaluate("window.CAP = 4")
    pdf = tmp_path / "Big_Resume.pdf"
    pdf.write_bytes(b"%PDF-1.4 too big")
    resume = q(teamtailor.RESUME, "file", True, "teamtailor:upload", key="resume", title="Upload resume")
    got = teamtailor.fill(page_a, resume, str(pdf))
    assert got.startswith("FAIL the page says 'File is too big (max 1MB)'") and not teamtailor.holds(page_a, resume)


def test_other_files_and_unknown_boxes_left_to_the_user(page_a):
    more = q("candidate[file_remote_url]", "file", True, "teamtailor:upload", title="Additional files")
    assert teamtailor.fill(page_a, more, "x.pdf").startswith("ASK not the resume box")
    assert teamtailor.fill(page_a, q("candidate[mystery]", "text", "x", "teamtailor:other"), None).startswith("ASK a box")
    assert teamtailor.fill(page_a, q("candidate[nope]", "text", "x"), None) == "FAIL question not on page"


def test_what_leaves_before_submit_is_named():
    from apply import form as apply_form
    where = questions.question("candidate[location][query]", "Address", "location", True, (), "location")
    assert "search Teamtailor's own list as they're typed" in apply_form.typed_note(teamtailor, [where])
    resume = questions.question(teamtailor.RESUME, "Upload resume", "file", True, (), "resume")
    assert "as soon as it is chosen" in apply_form.upload_note(teamtailor, [resume])
