"""Rippling: link shapes, saved form definitions -> shared questions, each widget rule on a saved form.
Facts: app/docs/apply/rippling.md."""
import json
from pathlib import Path

import pytest

from apply import browser, questions, systems
from apply.systems import rippling

FIXTURES = Path(__file__).parent / "fixtures" / "rippling"
ID = "0e4c8300-8a74-4858-9a83-3e9566b708fb"
POSTING = f"https://ats.rippling.com/acme/jobs/{ID}"


def read(tenant: str) -> dict:
    return {q["id"]: q for q in rippling.from_definition(json.loads((FIXTURES / f"tenant-{tenant}.json").read_text()))}


def titled(qs: dict, start: str) -> dict:
    return next(q for q in qs.values() if q["title"].startswith(start))


# --- links ---

@pytest.mark.parametrize("url", [POSTING, f"{POSTING}?utm_source=freehire.me", f"{POSTING}/",
                                 f"{POSTING}/apply?step=application"])
def test_rippling_link_plain_freehire_tail_or_form(url):
    assert rippling.matches(url) and rippling.application_url(url) == f"{POSTING}/apply?step=application"
    assert systems.for_url(url) is rippling


@pytest.mark.parametrize("url", ["https://ats.rippling.com/acme/jobs", "https://ats.rippling.com/acme/jobs/123",
                                 f"https://ats.rippling.com.example.com/acme/jobs/{ID}", f"https://www.example.com/acme/jobs/{ID}"])
def test_not_a_rippling_posting_refused(url):
    assert not rippling.matches(url)
    with pytest.raises(ValueError):
        rippling.application_url(url)


# --- the form, from saved definitions ---

def test_rippling_own_boxes_keys_kinds_required():
    a = read("a")
    assert [a[o]["key"] for o in ("first_name", "last_name", "email", "phone_number", "resume", "cover_letter")] == \
        ["first_name", "last_name", "email", "phone", "resume", "cover_letter"]
    assert (a["location"]["kind"], a["location"]["key"], a["location"]["required"]) == ("location", "city", True)
    assert a["pronouns"]["options"][1] == "He/him/his" and not a["pronouns"]["required"]
    assert read("b")["linkedin_link"]["key"] == "linkedin" and read("b")["linkedin_link"]["required"]


def test_rippling_employer_questions_kinds_options_and_type_kept():
    a, b, c = read("a"), read("b"), read("c")
    permit = titled(a, "Are you authorized to conduct work in the US")
    assert (permit["kind"], permit["native"], permit["options"]) == ("yesno", "KNOCKOUT", ["Yes", "No"])
    assert permit["id"].startswith("customQuestions.") and permit["id"].count(".") == 2
    heard = titled(a, "How did you hear")
    assert heard["kind"] == "multichoice" and "Company Careers Page" in heard["options"]
    assert titled(a, "How many years")["kind"] == "choice"
    assert titled(a, "In 3")["kind"] == "longtext"
    assert titled(b, "Are you located within 25 miles")["options"] == rippling.SCALE
    assert titled(c, "What is your target start date")["kind"] == "date"
    details = titled(c, "If you answered 'yes'")
    assert (details["kind"], details["max_chars"]) == ("longtext", 100)
    assert titled(c, "How many years of relevant")["native"] == "SINGLE_SELECT_DROPDOWN"
    worded = titled(c, "Are you willing to work from the Acme office")  # a knockout needn't be Yes / No
    assert (worded["kind"], worded["native"], len(worded["options"])) == ("choice", "KNOCKOUT", 4)


def test_rippling_one_key_in_two_groups_kept_apart():
    b = read("b")
    keys = [i.rsplit(".", 1)[1] for i in b if i.startswith("customQuestions.")]
    assert len(keys) != len(set(keys))  # the same key in two groups...
    assert len(b) == len(rippling.from_definition(json.loads((FIXTURES / "tenant-b.json").read_text())))  # ...two ids


def test_rippling_eeo_block_only_when_the_posting_draws_it():
    assert [i for i in read("a") if i.startswith("eeoc.")] == list(rippling.EEO)
    assert not [i for i in read("c") if i.startswith("eeoc.")]
    assert not any(q["required"] for i, q in read("a").items() if i.startswith("eeoc."))


def test_rippling_saved_answers_pick_its_own_options():
    a = read("a")
    config = {"self_identification": {"fill_on_forms": True, "gender": "Male", "hispanic_latino": True,
                                      "protected_veteran": False, "armed_forces": False, "pronouns": "He/Him"},
              "home_address": {"city": "Springfield", "state": "New Jersey"}}
    got = {x["id"]: x["answer"] for x in questions.draft(list(a.values()), {}, config=config)}
    assert got["eeoc.gender"] == "Male" and got["eeoc.hispanicOrLatino"] == "Yes"
    assert got["eeoc.veteranStatus"] == "I am not a protected veteran"
    assert got["eeoc.race"] is None  # nothing saved for it: asked
    assert got["pronouns"] == "He/him/his"  # never "He/him/his, they/them/theirs"
    assert got["location"] == "Springfield"  # the town they live in, never the resume's "NYC"
    assert got[titled(a, "How did you hear")["id"]] == ["Company Careers Page"]


def test_rippling_closed_or_formless_posting_said_plainly():
    with pytest.raises(ValueError, match="may have closed"):
        rippling.from_definition({"activeJobApplication": None})
    with pytest.raises(ValueError, match="may have closed"):
        rippling.job_post("<html>no data</html>")


@pytest.mark.parametrize("texts, value, pick", [
    (["Springfield, NJ, USA", "Springfield, Uckfield, UK", "Springfield Township, SD, USA"], "Springfield", "Springfield, NJ, USA"),
    (["Springfield, NJ, USA", "Springfield, IL, USA"], "Springfield", None),  # two US towns: asked
    (["Springfield, NJ, USA", "Springfield, IL, USA"], "Springfield, IL, USA", "Springfield, IL, USA"),
    (["Springfield, Uckfield, UK"], "Springfield", None)])
def test_rippling_place_picked_only_when_one_fits(texts, value, pick):
    assert rippling.town_pick(texts, value) == pick


@pytest.mark.parametrize("value, digits", [("(555) 555-0100", "5555550100"), ("+1 555 555 0100", "5555550100")])
def test_rippling_phone_digits_without_the_country_code(value, digits):
    assert rippling.phone(value) == digits


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


def q(id: str, kind: str, answer, key=None, title=None) -> dict:
    return {"id": id, "title": title or id, "kind": kind, "key": key, "options": [], "native": None,
            "required": True, "answer": answer}


C = "customQuestions."


def test_rippling_fills_each_widget_and_reads_it_back(page):
    filled = [q("first_name", "text", "Test", "first_name"), q("phone_number", "phone", "+1 555 555 0100", "phone"),
              q("pronouns", "choice", "He/him/his"), q("location", "location", "Springfield", "city"),
              q(f"{C}g1.213cf3b2-9260-4e35-b1ed-9533163fd4af", "yesno", "Yes"),
              q(f"{C}g1.ae881a3f-904e-467c-854b-598982f3e1cc", "multichoice", ["Company Careers Page"]),
              q(f"{C}g2.0e4c8300-8a74-4858-9a83-3e9566b708fb", "choice", "8+ years"),
              q(f"{C}g3.8e07d6a6-cab9-45f0-bea7-8b3efbeda46e", "choice", "Strong Yes"),
              q(f"{C}g2.07843e81-2df7-495c-ad06-4131d4be6af1", "longtext", "Their words. " * 60),
              q(f"{C}g4.4e829ddf-b866-48b5-9b00-8673df05c2f4", "date", "2026-11-30"),
              q("eeoc.gender", "choice", "Male")]
    assert [rippling.fill(page, x, None) for x in filled] == ["ok"] * len(filled)
    assert all(rippling.holds(page, x) for x in filled)
    assert page.locator("#field-42").input_value() == "Springfield, NJ, USA"
    assert page.locator("[data-value='Company Careers Page']").get_attribute("aria-checked") == "true"
    assert page.locator("[data-value=LinkedIn]").get_attribute("aria-checked") == "false"


def test_rippling_dropdown_never_picks_an_option_not_offered(page):
    said = rippling.fill(page, q("eeoc.gender", "choice", "Man"), None)
    assert said.startswith("ASK no option 'Man'") and "Male" in said
    assert page.locator("[role=option]").count() == 0  # the list closed again


def test_rippling_resume_shows_its_name_and_other_file_boxes_left(page, tmp_path, monkeypatch):
    monkeypatch.setattr(rippling, "PARSE_MS", 0)
    pdf = tmp_path / "Test_Resume.pdf"
    pdf.write_bytes(b"%PDF-1.4\n%%EOF\n")
    resume = q("resume", "file", True, "resume")
    assert rippling.fill(page, resume, str(pdf)) == "ok" and rippling.holds(page, resume)
    assert rippling.fill(page, q("resume", "file", False, "resume"), str(pdf)) == "skipped - upload not approved"
    assert rippling.fill(page, q("cover_letter", "file", True, "cover_letter"), None).startswith("ASK cover letter box")


def test_rippling_missing_box_failed_and_ids_on_page_from_testids(page):
    assert rippling.fill(page, q(f"{C}g9.none", "text", "x"), None) == "FAIL question not on page"
    ids = rippling.ids_on_page(page)
    assert {"resume", "first_name", "pronouns", "phone_number", "location", "eeoc.gender", "sms_opt_in"} <= set(ids)
    assert f"{C}g3.8e07d6a6-cab9-45f0-bea7-8b3efbeda46e" in ids
    assert "phone_number-code" not in ids and "pronouns_strategy" not in ids
