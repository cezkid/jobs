"""Gem: link shapes, the saved form reads -> shared questions, each widget rule on a saved form. Facts: app/docs/apply/gem.md."""
import json
from pathlib import Path

import pytest

from apply import browser, systems
from apply.systems import gem

FIXTURES = Path(__file__).parent / "fixtures" / "gem"
ID = "am9icG9zdDqcyLhlgwyA4nm6KGEaTGtc"
POSTING = f"https://jobs.gem.com/acme/{ID}"


def read(tenant: str) -> dict:
    return {q["id"]: q for q in gem.from_read(json.loads((FIXTURES / f"tenant-{tenant}.json").read_text()))}


def titled(qs: dict, start: str) -> dict:
    return next(q for q in qs.values() if q["title"].startswith(start))


# --- links ---

@pytest.mark.parametrize("url", [POSTING, f"{POSTING}?utm_source=freehire.me", f"{POSTING}/"])
def test_gem_link_plain_or_freehire_tail(url):
    assert gem.matches(url) and gem.application_url(url) == POSTING
    assert systems.for_url(url) is gem


@pytest.mark.parametrize("url", ["https://jobs.gem.com/acme", "https://jobs.gem.com/acme/careers",
                                 f"https://jobs.gem.com.example.com/acme/{ID}", f"https://www.example.com/acme/{ID}"])
def test_not_a_gem_posting_refused(url):
    assert not gem.matches(url)
    with pytest.raises(ValueError):
        gem.application_url(url)


# --- the form, from the saved reads ---

def test_gem_own_boxes_keys_kinds_required():
    a, b = read("a"), read("b")
    assert [a[f"field:{t}"]["key"] for t in ("FIRST_NAME", "LAST_NAME", "EMAIL", "LINKEDIN_URL", "PHONE", "RESUME")] == \
        ["first_name", "last_name", "email", "linkedin", "phone", "resume"]
    assert a["field:RESUME"]["kind"] == "file" and a["field:RESUME"]["required"]
    assert a["field:LINKEDIN_URL"]["required"] and not b["field:LINKEDIN_URL"]["required"]
    assert a["field:LOCATION"]["title"] == "Location" and a["field:LOCATION"]["kind"] == "text"  # plain box, no place search


def test_gem_questions_kinds_options_and_widget_kept():
    a, b = read("a"), read("b")
    heard = titled(a, "How did you hear")
    assert (heard["kind"], heard["native"], heard["required"]) == ("choice", "SINGLE_SELECT:DROPDOWN", True)
    assert heard["options"][0] == "Company Website" and "Glassdoor" in heard["options"]  # trailing spaces trimmed
    sponsor = titled(b, "Will you now or in the future require employment sponsorship")
    assert (sponsor["kind"], sponsor["native"]) == ("yesno", "SINGLE_SELECT:RADIO_BUTTON")
    assert titled(b, "Are you currently bound")["kind"] == "choice"  # Yes / No / Not Sure
    assert titled(b, "In 1")["kind"] == "longtext"
    assert titled(a, "By checking this box, you agree to receive text")["kind"] == "multichoice"


def test_gem_bold_marks_left_out_of_titles():
    qs = gem.from_read({"oatsExternalJobPosting": {"isApplicationFormHidden": False},
                        "oatsJobPostFieldsAndQuestions": {"fields": [], "questions": [
                            {"extId": "q1", "answerType": "SHORT_TEXT", "displayType": None, "isRequired": True,
                             "text": "**Do you have experience with frontend security?**", "options": None},
                            {"extId": "q2", "answerType": "DISPLAY_ONLY", "displayType": None, "isRequired": False,
                             "text": "Some words", "options": None}]}})
    assert [(q["id"], q["title"]) for q in qs] == [("q1", "Do you have experience with frontend security?")]


@pytest.mark.parametrize("kind, parts", [("EEO", ["Gender", "Race"]), ("EEOV", ["Gender", "Race", "Veteran status"])])
def test_gem_voluntary_survey_parts_by_its_type(kind, parts):
    qs = gem.from_read({"oatsExternalJobPosting": {"isApplicationFormHidden": False},
                        "oatsJobPostFieldsAndQuestions": {"fields": [], "questions": [],
                                                          "demographicSurvey": {"surveyType": kind, "questions": []}}})
    assert [q["title"] for q in qs] == parts and not any(q["required"] for q in qs)
    assert "Hispanic or Latino" in gem.SURVEY["Race"]


def test_gem_saved_survey_answers_pick_gems_own_options():
    from apply.questions import voluntary_answer
    config = {"self_identification": {"fill_on_forms": True, "gender": "Male", "hispanic_latino": True,
                                      "protected_veteran": False, "armed_forces": False}}
    qs = {q["title"]: q for q in read("a").values() if q["native"] == "survey"}
    assert voluntary_answer(qs["Gender"], config) == "Male"
    assert voluntary_answer(qs["Race"], config) == "Hispanic or Latino"
    assert voluntary_answer(qs["Veteran status"], config) == "I am not a protected veteran"


def test_gem_closed_or_hidden_form_said_plainly():
    with pytest.raises(ValueError, match="may have closed"):
        gem.from_read({"oatsExternalJobPosting": None, "oatsJobPostFieldsAndQuestions": None})
    with pytest.raises(ValueError, match="no application form"):
        gem.from_read({"oatsExternalJobPosting": {"isApplicationFormHidden": True},
                       "oatsJobPostFieldsAndQuestions": {"fields": [], "questions": []}})


@pytest.mark.parametrize("link, ok", [("https://www.linkedin.com/in/test-person", True), ("www.linkedin.com/in/test-person", True),
                                      ("linkedin.com/in/test-person", True), ("https://linkedin.com/in/test-person", False),
                                      ("https://www.linkedin.com/company/acme", False)])
def test_gem_linkedin_check_as_its_own(link, ok):
    assert bool(gem.LINKEDIN.match(link)) is ok


# --- fill on the saved form in real Chrome ---

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
    """The saved form in headless Chrome; every request it makes refused (it loads nothing)."""
    context = chrome.new_context()
    context.route("**/*", lambda route: route.fulfill(status=404, body=""))
    pg = context.new_page()
    pg.set_default_timeout(3000)
    pg.set_content((FIXTURES / "form.html").read_text())
    yield pg
    context.close()


def q(title: str, kind: str, answer, key=None, options=(), native=None) -> dict:
    return {"id": title, "title": title, "kind": kind, "key": key, "options": list(options), "native": native,
            "required": True, "answer": answer}


def test_gem_fills_each_widget_and_reads_it_back(page):
    filled = [q("First name", "text", "Test", "first_name"), q("Email", "email", "test@example.com", "email"),
              q("LinkedIn URL", "url", "https://www.linkedin.com/in/test-person", "linkedin"),
              q("Phone number", "phone", "555-0100", "phone"),
              q("How did you hear about this job?", "choice", "Company Website", native="SINGLE_SELECT:DROPDOWN"),
              q("Will you now or in the future require employment sponsorship to work in the United States?", "yesno", "No",
                native="SINGLE_SELECT:RADIO_BUTTON"),
              q("In 1-2 sentences, what professional accomplishment are you most proud of, and why?", "longtext", "Their words."),
              q("Gender", "choice", "Male", options=gem.SURVEY["Gender"], native="survey")]
    assert [gem.fill(page, x, None) for x in filled] == ["ok"] * len(filled)
    assert all(gem.holds(page, x) for x in filled)
    assert page.locator("#cXVlc29wdDpObw").is_checked() and not page.locator("#cXVlc29wdDpZZXM").is_checked()


def test_gem_dropdown_never_picks_an_option_not_offered(page):
    said = gem.fill(page, q("How did you hear about this job?", "choice", "A friend"), None)
    assert said.startswith("ASK no option 'A friend'") and "Company Website" in said
    assert page.locator("#floating-ui-portal [role=option]").count() == 0  # the list closed again


def test_gem_linkedin_link_it_refuses_never_typed(page):
    said = gem.fill(page, q("LinkedIn URL", "url", "https://linkedin.com/in/test-person", "linkedin"), None)
    assert said.startswith("ASK Gem refuses")
    assert page.locator("input[type=text]").nth(3).input_value() == ""


def test_gem_resume_shows_its_name_and_other_file_boxes_left(page, tmp_path):
    pdf = tmp_path / "Test_Resume.pdf"
    pdf.write_bytes(b"%PDF-1.4\n%%EOF\n")
    resume = q("Resume", "file", True, "resume")
    assert gem.fill(page, resume, str(pdf)) == "ok" and gem.holds(page, resume)
    assert gem.fill(page, q("Resume", "file", False, "resume"), str(pdf)) == "skipped - upload not approved"
    assert gem.fill(page, q("Cover letter", "file", True, "cover_letter"), None).startswith("ASK cover letter box")


def test_gem_text_opt_in_left_for_the_user_and_missing_box_failed(page):
    assert gem.fill(page, q("Not on this form", "text", "x"), None) == "FAIL question not on page"
    agree = q("I agree to the privacy notice", "multichoice", ["I agree"])
    assert gem.fill(page, agree, None).startswith("ASK")


def test_gem_ids_on_page_from_labels(page, monkeypatch):
    known = [{"id": "field:EMAIL", "title": "Email"}, {"id": "q1", "title": "How did you hear about this job?"}]
    monkeypatch.setattr(gem, "questions", lambda url: known)
    ids = gem.ids_on_page(page)
    assert "field:EMAIL" in ids and "q1" in ids and "label:Gender" in ids
    assert not any("government reporting" in i or "Ready to apply" in i or "Powered by" in i for i in ids)
