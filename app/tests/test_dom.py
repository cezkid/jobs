"""apply/dom.py in real headless Chrome on local fixture pages: every request is answered from
app/tests/fixtures/dom/ or refused, so nothing reaches the network."""
from pathlib import Path
from urllib.parse import urlsplit

import pytest

from apply import browser, dom, form, questions
from apply.systems import greenhouse

FIXTURES = Path(__file__).parent / "fixtures" / "dom"
HOME = "https://acme.example/form.html"
SERVED = {"acme.example": None, "newassets.hcaptcha.com": "captcha.html"}


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
    context = chrome.new_context()
    asked = []

    def serve(route):
        u = urlsplit(route.request.url)
        asked.append(route.request.url)
        if u.hostname not in SERVED:
            return route.abort()
        file = FIXTURES / (SERVED[u.hostname] or u.path.lstrip("/"))
        return route.fulfill(path=str(file)) if file.is_file() else route.fulfill(status=404, body="")

    context.route("**/*", serve)
    pg = context.new_page()
    pg.goto(HOME)
    pg.wait_for_load_state("load")
    yield pg
    assert all(urlsplit(u).hostname in SERVED for u in asked), asked
    context.close()


@pytest.fixture
def snap(page):
    return dom.snapshot(page)


def by_label(snap, label):
    return next(c for c in snap["controls"] if dom.title(c["label"]) == label)


def q_for(page, label, answer):
    q = next(q for q in dom.questions(dom.snapshot(page)) if q["title"] == label)
    return q | {"answer": answer}


def test_labels_from_for_wrapping_labelledby_shadow_and_frame(snap):
    labels = {dom.title(c["label"]) for c in snap["controls"]}
    assert {"First name", "Last name", "Email address", "Preferred name", "Referral code"} <= labels
    assert by_label(snap, "Preferred name")["in_shadow"]
    assert by_label(snap, "Referral code")["frame"].endswith("/frame.html")


def test_captcha_frame_listed_not_read(snap):
    assert [f["url"] for f in snap["blocked_frames"]] == ["https://newassets.hcaptcha.com/captcha.html"]
    assert "Type the letters" not in {c["label"] for c in snap["controls"]}
    assert "security check (captcha) - yours to do" in dom.user_steps(snap)


def test_closed_shadow_root_reported_not_readable(snap):
    assert any(n["host"] == "div" and "closed shadow root" in n["why"] for n in snap["not_readable"])
    assert "Secret" not in {c["label"] for c in snap["controls"]}


def test_radio_and_checkbox_groups_one_question_each(snap):
    qs = {q["title"]: q for q in dom.questions(snap)}
    assert (qs["Preferred shift"]["kind"], qs["Preferred shift"]["options"]) == ("choice", ["Day", "Night"])
    assert (qs["Languages"]["kind"], qs["Languages"]["options"]) == ("multichoice", ["English", "Spanish", "French"])
    assert qs["I am at least 18 years old"]["kind"] == "yesno"
    assert (qs["Work mode"]["kind"], qs["Work mode"]["options"]) == ("choice", ["Remote", "Hybrid"])
    # role=radiogroup around native radios (Paylocity): one question, named by the group
    assert (qs["How did you hear about us?"]["kind"], qs["How did you hear about us?"]["options"]) == ("choice", ["Job board", "Referral"])


def test_radiogroup_of_native_radios_read_as_radios(snap):
    # BambooHR wraps native radios in role=radiogroup: once crashed the whole read (2026-10-03)
    travel = [q for q in dom.questions(snap) if q["id"] == '[name="travel"]']
    assert [q["kind"] for q in travel] == ["yesno"]


def test_select_placeholder_dropped_and_yes_no(snap):
    qs = {q["title"]: q for q in dom.questions(snap)}
    assert qs["Country"]["options"] == ["Canada", "United States"]
    assert qs["Are you willing to relocate?"]["kind"] == "yesno"


def test_required_by_attr_asterisk_and_word(snap):
    qs = {q["title"]: q for q in dom.questions(snap)}
    assert qs["First name"]["required"] and qs["Email address"]["required"]
    assert qs["Anything else"]["required"]
    assert not qs["Years of experience"]["required"]


def test_generated_ids_fall_back_to_name_data_then_label(snap):
    assert by_label(snap, "First name")["hook"] == '[id="first"]'
    assert by_label(snap, "Last name")["hook"] == '[name="last_name"]'
    assert by_label(snap, "Phone")["hook"] == '[name="phone"]'
    assert by_label(snap, "Website")["hook"] == '[data-qa="website"]'
    assert by_label(snap, "Department")["hook"] == "role=combobox|About the role|Department"


def test_kinds_keys_and_natives(snap):
    qs = {q["title"]: q for q in dom.questions(snap)}
    got = {t: (qs[t]["kind"], qs[t]["key"]) for t in
           ("First name", "Last name", "Email address", "Phone", "Website", "City", "Years of experience",
            "Earliest start date", "Anything else", "Short summary", "Location", "Resume")}
    assert got == {"First name": ("text", "first_name"), "Last name": ("text", "last_name"),
                   "Email address": ("email", None), "Phone": ("phone", None), "Website": ("url", "website"),
                   "City": ("text", "city"), "Years of experience": ("number", None),
                   "Earliest start date": ("date", None), "Anything else": ("longtext", None),
                   "Short summary": ("longtext", None), "Location": ("location", "location"), "Resume": ("file", "resume")}
    assert qs["Email address"]["native"] == "dom:input:email"


def test_password_honeypot_skipped_custom_select_left_shut(snap):
    titles = {q["title"] for q in dom.questions(snap)}
    assert "Create a password" not in titles and "Leave empty" not in titles
    assert "password box 'Create a password' - yours to type" in dom.user_steps(snap)
    assert by_label(snap, "Department")["options_hidden"]


def test_prefilled_value_recorded(snap):
    assert by_label(snap, "City")["value"] == "Springfield"


def test_page_name_on_questions(snap):
    assert {q["page"] for q in dom.questions(snap, page="Step 1")} == {"Step 1"}


@pytest.mark.parametrize("label,answer,read", [
    ("First name", "Test", "#first"),
    ("Phone", "555-0100", "[name=phone]"),
    ("Email address", "test@example.com", "#email"),
    ("Earliest start date", "2026-11-02", "#start"),
    ("Anything else", "Line one", "#note"),
])
def test_fill_text_likes_read_back(page, label, answer, read):
    assert dom.fill(page, q_for(page, label, answer), None) == "ok"
    assert page.input_value(read) == answer


def test_fill_inside_shadow_root_and_frame(page):
    assert dom.fill(page, q_for(page, "Preferred name", "Test"), None) == "ok"
    assert dom.fill(page, q_for(page, "Referral code", "AB12"), None) == "ok"
    assert page.frame_locator("#same").locator("#ref").input_value() == "AB12"
    assert page.locator("acme-field #pref").input_value() == "Test"  # Playwright CSS pierces open shadow roots


def test_fill_editable_select_radio_checkboxes(page):
    assert dom.fill(page, q_for(page, "Short summary", "Hello there"), None) == "ok"
    assert dom.fill(page, q_for(page, "Country", "United States"), None) == "ok"
    assert dom.fill(page, q_for(page, "Are you willing to relocate?", "Yes"), None) == "ok"
    assert dom.fill(page, q_for(page, "Preferred shift", "Night"), None) == "ok"
    assert dom.fill(page, q_for(page, "Languages", ["English", "French"]), None) == "ok"
    assert dom.fill(page, q_for(page, "I am at least 18 years old", "Yes"), None) == "ok"
    assert dom.fill(page, q_for(page, "Work mode", "Hybrid"), None) == "ok"
    assert page.eval_on_selector("#country", "e => e.selectedOptions[0].text") == "United States"
    assert page.is_checked("input[name=shift][value=n]") and not page.is_checked("input[name=shift][value=d]")
    assert [page.is_checked(f"input[name=lang][value={v}]") for v in ("en", "es", "fr")] == [True, False, True]
    assert page.is_checked("#adult")
    assert page.get_attribute("#mode [role=radio]:nth-child(2)", "aria-checked") == "true"


def test_fill_choice_not_offered_asks(page):
    assert dom.fill(page, q_for(page, "Country", "Mexico"), None).startswith("ASK no option 'Mexico'")
    assert dom.fill(page, q_for(page, "Preferred shift", "Evening"), None).startswith("ASK no option")


def test_fill_location_combobox_starts_with(page):
    assert dom.fill(page, q_for(page, "Location", "Salem"), None) == "ok"
    assert page.input_value("#location") == "Salem, Oregon, United States"


def test_fill_file_and_read_back(page, tmp_path):
    pdf = tmp_path / "Test_Resume.pdf"
    pdf.write_bytes(b"%PDF-1.4\n%%EOF\n")
    assert dom.fill(page, q_for(page, "Resume", True), str(pdf)) == "ok"
    assert page.eval_on_selector("#resume", "e => e.files[0].name") == "Test_Resume.pdf"
    assert dom.fill(page, q_for(page, "Resume", False), str(pdf)) == "skipped - upload not approved"


def test_fill_refuses_when_label_changed(page):
    q = q_for(page, "First name", "Test")
    page.eval_on_selector("label[for=first]", "e => e.textContent = 'Company name'")
    assert dom.fill(page, q, None).startswith("FAIL box label changed ('Company name')")
    assert page.input_value("#first") == ""


def test_fill_absent_box_later_for_multi_page_else_fail(page):
    q = {"id": '[id="gone"]', "title": "Middle name", "kind": "text", "answer": "A"}
    assert dom.fill(page, q, None, later=True).startswith("LATER")
    assert dom.fill(page, q, None).startswith("FAIL question not on page")


def test_fill_never_types_password_or_consent(page):
    pw = {"id": '[id="pw"]', "title": "Create a password", "kind": "text", "answer": "x"}
    assert dom.fill(page, pw, None).startswith("FAIL password box")
    terms = {"id": '[id="adult"]', "title": "I agree to the terms and conditions", "kind": "yesno", "answer": "Yes"}
    assert dom.fill(page, terms, None).startswith("ASK yours to do on the page")
    assert page.input_value("#pw") == "" and not page.is_checked("#adult")


def test_greenhouse_select_all_that_apply_drawn_as_checkboxes(page):
    """Greenhouse's multi-select is a dropdown on some forms, a checkbox set on others: ticked by label,
    the rest unticked, one question on the page (FAILed as 'not an <input>' before, 2026-10-05)."""
    page.goto("https://acme.example/greenhouse.html")
    q = {"id": "question_100[]", "title": "Employment Preference", "kind": "multichoice"}
    assert greenhouse.ids_on_page(page) == ["first_name", "question_100[]"]
    assert greenhouse.fill(page, q | {"answer": ["Part Time", "Temporary"]}, None) == "ok"
    ticked = page.eval_on_selector_all('[name="question_100[]"]', "bs => bs.map(b => b.checked)")
    assert ticked == [False, True, True, False]
    assert greenhouse.fill(page, q | {"answer": "Contract"}, None) == "ok"
    assert page.eval_on_selector_all('[name="question_100[]"]:checked', "bs => bs.map(b => b.value)") == ["204"]
    assert greenhouse.fill(page, q | {"answer": ["Seasonal"]}, None).startswith("ASK no option 'Seasonal'; offered: Full Time")


def test_greenhouse_dropdown_the_page_empties_is_filled_again_or_flagged(page, monkeypatch):
    """Chrome path, same fixture as the window's: a pick the page shows, then empties (every dropdown
    empty after an ok fill, plan-29g.20) - read back off the page, filled again; still empty -> FAIL."""
    monkeypatch.setattr(form, "SETTLE_MS", 1500)
    page.goto("https://acme.example/greenhouse-form.html")
    qs = [{"id": "question_5", "title": "Country of residence", "kind": "choice", "answer": "Canada"},
          {"id": "question_6", "title": "Sponsorship", "kind": "yesno", "answer": "No"},
          {"id": "question_7", "title": "How did you hear about this job?", "kind": "choice", "answer": "Referral"}]
    report, _ = form.fill_page(page, greenhouse, qs, None, None)
    assert report[:2] == [("question_5", "ok"), ("question_6", "ok")]
    assert report[2][0] == "question_7" and report[2][1].startswith("FAIL ")  # never ok, whichever read-back saw it
    shown = [greenhouse.picked(greenhouse.by_id(page, f"question_{n}")) for n in (5, 6, 7)]
    assert shown == [["Canada"], ["No"], []]


def test_greenhouse_education_filled_per_school_from_resume_details(page, monkeypatch):
    """Education boxes drafted from Resume details, filled in Chrome (the window runs the same greenhouse.fill,
    plan-29g.26): the school picked off Greenhouse's searched list by its words ("..., Berkeley" = "... -
    Berkeley"), degree + discipline as the list words them, the second school's boxes through the section's own
    Add another (never Employment's); a school not on the list -> the user picks theirs on the page."""
    monkeypatch.setattr(form, "SETTLE_MS", 500)
    page.goto("https://acme.example/greenhouse-education.html")
    lists = {"degree": ["Associate's Degree", "Bachelor's Degree", "Doctor of Philosophy (Ph.D.)", "Master's Degree"],
             "discipline": ["Computer Science", "Economics", "Other"]}
    asked = [questions.question(f"{box}--{i}", f"Education {i + 1}: {title}", "number" if key.endswith("year") else "choice",
                                False, questions.MONTHS if key.endswith("month") else lists.get(key, []), key, "education",
                                entry=i)
             for i in (0, 1) for box, _, title, key in greenhouse.EDUCATION_BOXES if "start" not in box]
    schools = [{"institution": "University of California, Berkeley", "degree": "BA", "field": "Economics", "end": "2016-05"},
               {"institution": "Massachusetts Institute of Technology", "degree": "PhD", "field": "Computer Science",
                "end": "2021"}]
    drafted = questions.draft(asked, {}, schools=schools)
    report, extra = form.fill_page(page, greenhouse, drafted, None, None)
    assert report == [(q["id"], "ok") for q in drafted if q["answer"]] and len(report) == 9
    assert extra == ["first_name"]  # Education boxes never counted as questions the file lacks
    shown = {f"{b}--{i}": greenhouse.picked(greenhouse.by_id(page, f"{b}--{i}")) for i in (0, 1)
             for b in ("school", "degree", "discipline", "end-month")}
    assert shown == {"school--0": ["University of California - Berkeley"], "degree--0": ["Bachelor's Degree"],
                     "discipline--0": ["Economics"], "end-month--0": ["May"],
                     "school--1": ["Massachusetts Institute of Technology"], "degree--1": ["Doctor of Philosophy (Ph.D.)"],
                     "discipline--1": ["Computer Science"], "end-month--1": []}  # a year alone: no month typed
    assert [page.input_value(f"#end-year--{i}") for i in (0, 1)] == ["2016", "2021"]
    assert page.locator(".education--form").count() == 2 and page.locator('[id="company-name--1"]').count() == 0
    monkeypatch.setattr(greenhouse, "LIST_WAIT_MS", 1500)
    school = next(q for q in drafted if q["id"] == "school--0")
    assert greenhouse.fill(page, school | {"answer": "Springfield Community College"}, None) == \
        "ASK school 'Springfield Community College' not on the form's list - the user picks theirs (or Other) on the page"

