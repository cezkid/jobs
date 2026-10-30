"""Recruiterflow: link shapes, saved form definitions -> shared questions, each widget rule on a stand-in page.
Facts: app/docs/apply/recruiterflow.md."""
import json
from pathlib import Path

import pytest

from apply import browser, systems
from apply.systems import recruiterflow

FIXTURES = Path(__file__).parent / "fixtures" / "recruiterflow"
POSTING = "https://recruiterflow.com/acme/jobs/5992"


def data(tenant: str) -> dict:
    return json.loads((FIXTURES / f"tenant-{tenant}.json").read_text())


def read(tenant: str) -> dict:
    return {q["id"]: q for q in recruiterflow.from_definition(data(tenant))}


def titled(qs: dict, start: str) -> dict:
    return next(q for q in qs.values() if q["title"].startswith(start))


# --- links ---

@pytest.mark.parametrize("url", [POSTING, f"{POSTING}?utm_source=freehire.me", f"{POSTING}/",
                                 "https://www.recruiterflow.com/acme/jobs/5992"])
def test_recruiterflow_link_plain_or_freehire_tail(url):
    assert recruiterflow.matches(url) and recruiterflow.application_url(url) == POSTING
    assert systems.for_url(url) is recruiterflow


@pytest.mark.parametrize("url", ["https://recruiterflow.com/acme/jobs", "https://recruiterflow.com/acme/jobs/abc",
                                 "https://recruiterflow.com.example.com/acme/jobs/5992",
                                 "https://www.example.com/acme/jobs/5992"])
def test_not_a_recruiterflow_posting_refused(url):
    assert not recruiterflow.matches(url)
    with pytest.raises(ValueError):
        recruiterflow.application_url(url)


# --- the form, from saved definitions ---

def test_recruiterflow_own_boxes_keys_kinds_required():
    a = read("a")
    keys = {i: a[i]["key"] for i in a if i.startswith("personal_info.")}
    assert keys == {"personal_info.first_name": "first_name", "personal_info.last_name": "last_name",
                    "personal_info.email": "email", "personal_info.phone": "phone",
                    "personal_info.location.city": "city", "personal_info.location.state": "state",
                    "personal_info.location.postal_code": "zip", "personal_info.location.country": None,
                    "personal_info.linkedin_profile": "linkedin"}
    assert all(a[i]["required"] for i in keys)
    assert (a["resume"]["kind"], a["resume"]["key"], a["resume"]["required"]) == ("file", "resume", True)
    assert "cover_letter" not in a  # off on tenant A
    assert read("b")["cover_letter"]["key"] == "cover_letter" and not read("b")["cover_letter"]["required"]
    assert list(a)[0] == "resume"  # the file first, as on the page


def test_recruiterflow_parts_turned_off_left_out():
    c = read("c")
    assert not [i for i in c if i.startswith("personal_info.location.")] and "personal_info.linkedin_profile" not in c
    assert not c["personal_info.phone"]["required"]
    assert c["candidate_profile.experience"]["required"] and "candidate_profile.education" not in c


def test_recruiterflow_employer_questions_kinds_options():
    a = read("a")
    pay = [q for q in a.values() if q["title"].startswith("What is the base compensation range")]
    assert [(q["id"].rsplit(".", 1)[1], q["kind"], q["key"]) for q in pay] == [("min", "number", None), ("max", "number", None)]
    assert all(q["required"] for q in pay)
    permit = titled(a, "Are you legally authorized")
    assert (permit["kind"], permit["options"], permit["id"]) == ("yesno", ["Yes", "No"], "q115976")
    assert titled(a, "Where are you in your job search")["kind"] == "choice"
    sizes = titled(a, "Would you like to work at companies")
    assert sizes["kind"] == "multichoice" and "" not in sizes["options"] and len(sizes["options"]) == 7
    assert titled(a, "Do you have anything else")["kind"] == "longtext"


def test_recruiterflow_a_link_in_a_list_never_offered():
    office = titled(read("a"), "What is your ideal office setting")
    assert office["options"] == ["Remote", "In Office", "Hybrid", "N/A"]


def test_recruiterflow_closed_or_formless_posting_said_plainly():
    closed = data("a") | {"job_visibility_id": 6}
    with pytest.raises(ValueError, match="closed"):
        recruiterflow.from_definition(closed)
    with pytest.raises(ValueError, match="no application form"):
        recruiterflow.from_definition(data("a") | {"application_form": {"is_empty": True}})
    with pytest.raises(ValueError, match="no application form"):
        recruiterflow.page_data("<html><body>gone</body></html>")


def test_recruiterflow_definition_read_out_of_the_page():
    html = f"<script>var convertedToJSON = {json.dumps(data('a'))};window.applyJobData = convertedToJSON;</script>"
    assert recruiterflow.page_data(html)["application_form"] == data("a")["application_form"]


@pytest.mark.parametrize("value,digits", [("+1 (555) 555-0100", "5555550100"), ("555-555-0100", "5555550100")])
def test_recruiterflow_phone_digits_without_the_country_code(value, digits):
    assert recruiterflow.phone(value) == digits


# --- widgets, on the stand-in page ---

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
    """The stand-in form in headless Chrome; every request it makes refused (it loads nothing)."""
    context = chrome.new_context()
    context.route("**/*", lambda route: route.fulfill(status=404, body=""))
    pg = context.new_page()
    pg.set_default_timeout(3000)
    pg.set_content((FIXTURES / "form.html").read_text())
    yield pg
    context.close()


def by(tenant: str, id: str, answer) -> dict:
    return read(tenant)[id] | {"answer": answer}


def test_recruiterflow_fills_each_widget_and_reads_it_back(page):
    a = read("a")
    pay = [i for i in a if i.endswith((".min", ".max"))]
    filled = [by("a", "personal_info.first_name", "Test"), by("a", "personal_info.phone", "+1 555 555 0100"),
              by("a", "personal_info.location.city", "Springfield"),
              by("a", "personal_info.location.country", "United States"),
              by("a", pay[0], "180000"), by("a", pay[1], "225000"),
              by("a", "candidate_profile.summary", "Their words."),
              by("a", "q115975", "Just need to give 2 weeks notice"), by("a", "q115976", "Yes"),
              by("a", "q115978", ["Very Large (501 - 1000 employees)", "Very Very Large (1001 - 10000 employees)"]),
              by("a", "q115981", "Nothing else.")]
    assert [recruiterflow.fill(page, x, None) for x in filled] == ["ok"] * len(filled)
    assert all(recruiterflow.holds(page, x) for x in filled)
    assert page.locator('input[placeholder="Min"]').input_value() == "180,000"
    assert "selected" in page.locator("button.yes-input").get_attribute("class")
    assert page.locator(".menu").count() == 0  # every list closed again


def test_recruiterflow_list_never_picks_an_option_not_offered(page):
    said = recruiterflow.fill(page, by("a", "q115975", "Within a week"), None)
    assert said.startswith("ASK no option 'Within a week'") and "Within 30 Days" in said
    assert page.locator(".menu").count() == 0


def test_recruiterflow_a_changed_pick_replaces_the_old(page):
    assert recruiterflow.fill(page, by("a", "q115975", "Within 30 Days"), None) == "ok"
    q = by("a", "q115975", "Just need to give 2 weeks notice")
    assert recruiterflow.fill(page, q, None) == "ok" and recruiterflow.holds(page, q)


def test_recruiterflow_resume_first_then_names_over_its_read(page, tmp_path):
    pdf = tmp_path / "Test_Applicant_Resume.pdf"
    pdf.write_bytes(b"%PDF-1.4\n%%EOF\n")
    resume = by("a", "resume", True)
    assert recruiterflow.fill(page, resume, str(pdf)) == "ok" and recruiterflow.holds(page, resume)
    assert page.locator('[name="personal_info.first_name"]').input_value() == "Wcag"  # the read came first...
    first = by("a", "personal_info.first_name", "Test")
    assert recruiterflow.fill(page, first, None) == "ok" and recruiterflow.holds(page, first)  # ...then the answer
    assert recruiterflow.fill(page, by("a", "resume", False), str(pdf)) == "skipped - upload not approved"


def test_recruiterflow_sections_and_missing_boxes(page):
    assert recruiterflow.fill(page, by("c", "candidate_profile.experience", "x"), None).startswith("ASK Experience")
    gone = by("a", "q115984", "Wearing a lot of hats. Assignments often require employees to figure it out on their own.")
    assert recruiterflow.fill(page, gone, None) == "FAIL question not on page"


def test_recruiterflow_ids_on_page_from_its_own_definition(page):
    page.evaluate("d => { window.applyJobData = d; }", data("a"))
    assert recruiterflow.ids_on_page(page) == list(read("a"))
