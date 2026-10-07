"""Breezy: link shapes, saved definitions (anonymised, app/tests/fixtures/breezy) drawn into both page builds ->
questions, each widget rule on a copy of the form Breezy's Angular template draws (fixtures/breezy/apply.html;
nothing reaches the network), the same copy filled in the window as through Playwright."""
import html
import json
from pathlib import Path
from urllib.parse import urlsplit

import httpx
import pytest
from test_apply_in_window import BREEZY_PATH, both, playwright_chrome, site, tab  # noqa: F401 - fixtures

from apply import questions, systems
from apply import form as fill_form
from apply.systems import breezy

FIXTURES = Path(__file__).parent / "fixtures" / "breezy"
LINK = "https://acme.breezy.hr/p/0a1b2c3d4e5f-software-engineer"
APPLY = LINK + "/apply"


def page_of(tenant: str) -> str:
    """The apply page as Breezy serves it, from a saved definition: React keeps it in a script, Angular in
    an attribute + a hidden box (left out when the posting asks no questions of its own)."""
    d = json.loads((FIXTURES / f"tenant-{tenant}.json").read_text())
    if d["build"] == "react":
        data = {"position": d["position"], "questions": d["questions"]} | d.get("flags", {})
        return f'<html><script id="portal-data" type="application/json">{json.dumps({"data": data})}</script></html>'
    box = f'<input type="hidden" id="questions" value="{html.escape(json.dumps(d["questions"]))}">' if d["questions"] else ""
    return (f'<div ng-controller="PositionApplyViewCtrl" data-position="{html.escape(json.dumps(d["position"]))}" '
            f'data-show-sms-consent="true"></div><form name="form">{box}</form>')


def form(tenant: str) -> dict:
    return {q["id"]: q for q in breezy.from_definition(*breezy.definition(page_of(tenant)))}


# --- links ---

def test_links_freehire_lists_land_on_the_apply_form():
    assert systems.for_url(LINK + "?utm_source=freehire.me") is breezy
    assert breezy.application_url(LINK + "?utm_source=freehire.me") == APPLY
    assert breezy.application_url(APPLY) == APPLY
    assert breezy.application_url("http://acme.breezy.hr/p/0a1b2c3d4e5f-software-engineer/") == APPLY
    assert breezy.parse_url(" " + LINK + " ") == ("acme", "0a1b2c3d4e5f-software-engineer")


def test_other_links_refused():
    for url in ("https://acme.breezy.hr/", "https://acme.breezy.hr/p/", "https://acme.breezy.hr/p/0a1b2c3d4e5f-x/apply/extra",
                "https://acme.breezy.hr.example.com/p/0a1b2c3d4e5f-x", "https://jobs.lever.co/acme/1b2c"):
        assert not breezy.matches(url), url
    with pytest.raises(ValueError):
        breezy.parse_url("https://jobs.lever.co/acme/1b2c")


def test_on_tab_the_same_posting_only():
    assert systems.on_tab(breezy, LINK, APPLY + "?x=1")
    assert not systems.on_tab(breezy, LINK, "https://acme.breezy.hr/p/ffffffffffff-other/apply")


# --- saved definitions -> questions ---

def test_both_builds_read_alike_standard_boxes_by_their_page_names():
    a = form("a")
    assert list(a)[:5] == ["cResume", "cName", "cEmail", "cPhoneNumber", "cAddress"]
    got = {q["id"]: (q["kind"], q["key"], q["required"]) for q in list(a.values())[:5]}
    assert got == {"cResume": ("file", "resume", True), "cName": ("text", "name", True), "cEmail": ("email", "email", True),
                   "cPhoneNumber": ("phone", "phone", True), "cAddress": ("location", "location", True)}
    # one full-name box, never split; hidden boxes never asked (tenant B hides address, summary, letter)
    b = form("b")
    assert "cAddress" not in b and "cSummary" not in b and "cCoverLetter" not in b and "cLocation" not in b
    c = form("c")
    assert not c["cResume"]["required"] and not c["cPhoneNumber"]["required"]


def test_pay_brings_its_per_list_and_a_currency_list_only_when_there_are_several():
    a = form("a")
    pay = a["cSalary"]
    assert (pay["kind"], pay["required"], pay["native"]) == ("number", True, "breezy:salary")
    assert questions.never_draft(pay["title"])
    # no currencies on the posting = Breezy's whole list, not in the page: matched by text on the page
    assert a["salaryCurrency"]["options"] == [] and a[breezy.PER]["options"] == breezy.PERIODS
    # one currency = shown as words, no list to pick
    b = form("b")
    assert "salaryCurrency" not in b and breezy.PER in b
    assert "cSalary" not in form("c")


def test_location_list_text_boxes_and_repeaters():
    a = form("a")
    assert a["cLocation"]["options"] == ["VA, US", "FL, US", "TX, US", "MD, US"] and a["cLocation"]["required"]
    assert a["cSummary"]["kind"] == "longtext" and a["cCoverLetter"]["kind"] == "longtext"
    assert (a["work_history"]["native"], a["education"]["native"]) == ("breezy:repeater", "breezy:repeater")


def test_employer_questions_by_type():
    a = form("a")
    assert a["section_1000_question_0"]["kind"] == "text"
    cit = a["section_1000_question_1"]
    assert (cit["kind"], cit["options"], cit["native"], cit["required"]) == ("yesno", ["Yes", "No"], "breezy:radio", True)
    b = form("b")
    auth = b["section_2000_question_1"]
    assert (auth["kind"], auth["options"], auth["native"]) == ("yesno", ["No", "Yes"], "breezy:select")
    c = form("c")
    assert (c["section_3000_question_0"]["kind"], c["section_3000_question_0"]["native"]) == ("yesno", "breezy:checkbox")
    more = [{"text": "Tools", "type": {"id": "checkboxes"}, "options": [{"text": "A"}, {"text": "B"}, {"text": "C"}]},
            {"text": "Shift", "type": {"id": "dropdown"}, "options": [{"text": "Day"}, {"text": "Night"}]},
            {"text": "Why us?", "type": {"id": "paragraph"}, "required": True},
            {"text": "Start", "type": {"id": "date"}},
            {"text": "Upload your resume", "type": {"id": "file"}},
            {"text": "A reference", "type": {"id": "referencecheck"}},
            {"text": "Code we emailed", "type": {"id": "verification_code"}},
            {"text": "I agree to receive texts", "type": {"id": "checkboxes"}, "options": [{"text": "I agree"}]}]
    got = {q["title"]: (q["kind"], q["native"]) for q in breezy.from_definition({}, [{"_id": 9, "questions": more}])}
    assert got == {"Tools": ("multichoice", "breezy:checkbox"), "Shift": ("choice", "breezy:select"),
                   "Why us?": ("longtext", "breezy:paragraph"), "Start": ("date", "breezy:date"),
                   "Upload your resume": ("file", "breezy:file"), "A reference": ("text", "breezy:referencecheck"),
                   "Code we emailed": ("text", "breezy:verification_code"),
                   "I agree to receive texts": ("yesno", "breezy:checkbox")}


def test_eeo_voluntary_and_ccpa_left_to_the_applicant():
    for tenant in ("a", "b"):  # React's own flags or Angular's form keys
        f = form(tenant)
        assert all(not f[id]["required"] for id in ("race_ethnicity", "gender", "eeoc.veteran_status"))
        assert "voluntary questions about you" in questions.topics(f["gender"]["title"])
        assert questions.signs(f["ccpaAgreement"]["title"])
    c = form("c")
    assert "gender" not in c and "ccpaAgreement" not in c


def test_angular_page_without_questions_has_none():
    d = json.loads((FIXTURES / "tenant-c.json").read_text())
    page = f'<div data-position="{html.escape(json.dumps(d["position"]))}"></div>'
    position, sections = breezy.definition(page)
    assert sections == [] and position["application_form"]["name"] == "required"


# --- closed + questions over plain HTTP ---

class Got:
    def __init__(self, status=200, text=""):
        self.status_code, self.text = status, text

    def raise_for_status(self):
        if self.status_code >= 400:
            raise httpx.HTTPStatusError(str(self.status_code), request=None, response=type("R", (), {"status_code": self.status_code})())


CLOSED_PAGE = "<html><h1>Position Closed</h1><p>This position is no longer open.</p></html>"


def test_questions_read_off_the_apply_page(monkeypatch):
    asked = []
    monkeypatch.setattr(httpx, "get", lambda url, **kw: asked.append(url) or Got(text=page_of("b")))
    qs = breezy.questions(LINK + "?utm_source=freehire.me")
    assert asked == [APPLY] and "cName" in [q["id"] for q in qs]


def test_closed_or_unknown_posting_says_so(monkeypatch):
    # a taken-down posting answers 200 with "Position Closed": read the words, never the status
    monkeypatch.setattr(httpx, "get", lambda url, **kw: Got(text=CLOSED_PAGE))
    with pytest.raises(ValueError, match="Position Closed"):
        breezy.questions(LINK)
    assert "closed" in breezy.closed(LINK)
    monkeypatch.setattr(httpx, "get", lambda url, **kw: Got(404))
    assert "may have closed" in breezy.closed(LINK)
    monkeypatch.setattr(httpx, "get", lambda url, **kw: Got(text=page_of("a")))
    assert breezy.closed(LINK) is None
    monkeypatch.setattr(httpx, "get", lambda url, **kw: Got(503))
    assert breezy.closed(LINK).startswith("can't tell")
    monkeypatch.setattr(httpx, "get", lambda url, **kw: Got(text="<html>no form</html>"))
    assert "may have closed" in breezy.closed(LINK)


# --- the page ---

@pytest.fixture(scope="module")
def chrome(playwright_chrome):
    """The in-window test's own Playwright Chrome: a second sync Playwright in one module fails its setup."""
    return playwright_chrome


@pytest.fixture
def page(chrome):
    """The apply form copy; nothing reaches the network."""
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
    assert not p.evaluate("window.submitted || false")
    assert p.locator("input[name=hp_7f2b]").input_value() == "" and not p.locator("input[name=smsConsent]").is_checked()
    context.close()


def q(id, kind, answer, native="breezy:text", options=(), key=None, title="Question"):
    return {"id": id, "title": title, "kind": kind, "key": key, "native": native, "required": True,
            "options": list(options), "answer": answer}


def test_ids_on_page_by_name_per_list_after_pay_never_the_trap_sms_or_reference_boxes(page):
    assert breezy.ids_on_page(page) == [
        "cResume", "cName", "cEmail", "cPhoneNumber", "cAddress", "salaryCurrency", "cSalary", breezy.PER, "cLocation",
        "cSummary", "cCoverLetter"] + [f"section_1000_question_{i}" for i in range(7)] + [
        "race_ethnicity", "gender", "eeoc.veteran_status", "ccpaAgreement"]


def test_text_boxes_filled_and_read_back(page):
    for item in (q("cName", "text", "Test Applicant"), q("cEmail", "email", "test@example.com"),
                 q("cPhoneNumber", "phone", "555-0100"), q("cSummary", "longtext", "Line one\nLine two"),
                 q("section_1000_question_0", "text", "Two weeks")):
        assert breezy.fill(page, item, None) == "ok" and breezy.holds(page, item)
    assert page.locator("[name=cSummary]").input_value() == "Line one\nLine two"
    assert not breezy.holds(page, q("cName", "text", "Someone Else"))


def test_address_typed_never_a_suggestion_picked(page):
    item = q("cAddress", "location", "Springfield, IL", "breezy:address", key="location")
    assert breezy.fill(page, item, None) == "ok" and breezy.holds(page, item)


def test_pay_number_currency_and_per_list(page):
    pay = q("cSalary", "number", "$85,000", "breezy:salary")
    assert breezy.fill(page, pay, None) == "ok" and page.locator("[name=cSalary]").input_value() == "85000" and breezy.holds(page, pay)
    cur = q("salaryCurrency", "choice", "canadian dollar ($)", "breezy:select")
    per = q(breezy.PER, "choice", "Yearly", "breezy:select", breezy.PERIODS)
    assert breezy.fill(page, cur, None) == "ok" and page.locator("[name=salaryCurrency]").input_value() == "CAD"
    assert breezy.fill(page, per, None) == "ok" and breezy.per_box(page).input_value() == "3"
    assert breezy.holds(page, cur) and breezy.holds(page, per)
    assert breezy.fill(page, q("salaryCurrency", "choice", "Pound", "breezy:select"), None).startswith("ASK no option 'Pound'")
    assert breezy.fill(page, q("cSalary", "number", "competitive", "breezy:salary"), None).startswith("ASK")


def test_per_list_found_away_from_the_pay_box_by_its_yearly_option(page):
    page.evaluate("""() => { const s = document.querySelector('[name=cSalary] ~ select');
                             const w = document.createElement('span'); s.replaceWith(w); w.appendChild(s); }""")
    assert breezy.PER in breezy.ids_on_page(page)
    per = q(breezy.PER, "choice", "Monthly", "breezy:select", breezy.PERIODS)
    assert breezy.fill(page, per, None) == "ok" and breezy.holds(page, per)


def test_lists_by_text_never_the_empty_one(page):
    loc = q("cLocation", "choice", "fl, us", "breezy:select", ["VA, US", "FL, US"])
    assert breezy.fill(page, loc, None) == "ok" and breezy.holds(page, loc)
    w2 = q("section_1000_question_1", "yesno", "Yes", "breezy:select", ["Yes", "No"])
    assert breezy.fill(page, w2, None) == "ok" and breezy.holds(page, w2)
    assert not breezy.holds(page, q("section_1000_question_1", "yesno", "No", "breezy:select", ["Yes", "No"]))
    assert not breezy.holds(page, q("salaryCurrency", "choice", "", "breezy:select") | {"id": breezy.PER})


def test_radios_in_labels_and_eeo_by_label_for(page):
    yes = q("section_1000_question_2", "yesno", "No", "breezy:radio", ["Yes", "No"])
    assert breezy.fill(page, yes, None) == "ok" and breezy.holds(page, yes)
    gender = q("gender", "choice", "I don't wish to answer", "breezy:radio")
    assert breezy.fill(page, gender, None) == "ok" and breezy.holds(page, gender)
    assert page.locator("#gender_no").is_checked()
    vet = q("eeoc.veteran_status", "choice", "I am not a protected veteran", "breezy:radio")
    assert breezy.fill(page, vet, None) == "ok" and page.locator("#vet_no").is_checked()
    assert breezy.fill(page, q("gender", "choice", "Other", "breezy:radio"), None).startswith("ASK no option 'other'")


def test_ticks_by_the_words_beside_them(page):
    tools = q("section_1000_question_3", "multichoice", ["Python", "Excel"], "breezy:checkbox")
    assert breezy.fill(page, tools, None) == "ok" and breezy.holds(page, tools)
    assert page.locator("[name=section_1000_question_3]").evaluate_all("bs => bs.map(b => b.checked)") == [True, False, True]
    fewer = tools | {"answer": ["SQL"]}
    assert breezy.fill(page, fewer, None) == "ok" and breezy.holds(page, fewer) and not breezy.holds(page, tools)


def test_consent_never_ticked_and_left_to_the_applicant(page):
    ccpa = q(breezy.CCPA[0], "yesno", "Yes", "breezy:tick", ["Yes", "No"], title=breezy.CCPA[1])
    assert "yours to do on the page" in breezy.fill(page, ccpa, None)
    assert not page.locator("input[name=ccpaAgreement]").is_checked()


def test_resume_chosen_read_back_by_the_name_the_box_shows(page, tmp_path):
    pdf = tmp_path / "Test_Resume.pdf"
    pdf.write_bytes(b"%PDF-1.4 test")
    resume = q("cResume", "file", True, "breezy:resume", key="resume", title="Resume")
    assert not breezy.holds(page, resume)
    assert breezy.fill(page, resume, str(pdf)) == "ok" and breezy.holds(page, resume)
    assert breezy.fill(page, resume | {"answer": False}, str(pdf)) == "skipped - upload not approved"


def test_resume_refused_in_the_pages_own_words(page, tmp_path):
    page.evaluate("window.CAP = 4")
    pdf = tmp_path / "Big_Resume.pdf"
    pdf.write_bytes(b"%PDF-1.4 too big")
    resume = q("cResume", "file", True, "breezy:resume", key="resume", title="Resume")
    got = breezy.fill(page, resume, str(pdf))
    assert got.startswith("FAIL the page says 'The file attachment is limited to 50MB'") and not breezy.holds(page, resume)


def test_other_files_sections_dates_and_references_left_to_the_user(page):
    assert breezy.fill(page, q("section_1000_question_5", "file", True, "breezy:file", title="Portfolio"), "x.pdf").startswith("ASK not the resume box")
    assert breezy.fill(page, q("education", "longtext", "x", "breezy:repeater", title="Education"), None).startswith("ASK the Education section")
    assert breezy.fill(page, q("section_1000_question_6", "text", "x", "breezy:referencecheck", title="A reference"), None).startswith("ASK referencecheck")
    assert breezy.fill(page, q("section_1000_question_4", "date", "next month", "breezy:date", title="Start"), None).startswith("ASK date box")
    start = q("section_1000_question_4", "date", "2026-11-02", "breezy:date", title="Start")
    assert breezy.fill(page, start, None) == "ok" and breezy.holds(page, start)
    assert breezy.fill(page, q("cNope", "text", "x"), None) == "FAIL question not on page"


def test_address_letters_named_as_going_to_google():
    from apply import form as apply_form
    where = questions.question("cAddress", "Address", "location", True, (), "location")
    assert "search Google's list as they're typed - those words reach Google" in apply_form.typed_note(breezy, [where])
    assert "as soon as it is chosen" in apply_form.upload_note(breezy, [questions.question("cResume", "Resume", "file", True, (), "resume")])


# --- in the window: the same fill through window.Page as through Playwright ---

# the page copy's questions, each kind answered once: resume, contact, address, pay + its two lists, location,
# summary + letter, the employer's text / list / radios / ticks / date, two EEO radios (CCPA left: the applicant's own)
WINDOW_ANSWERS = [
    q("cResume", "file", True, "breezy:resume", key="resume", title="Resume"),
    q("cName", "text", "Test Applicant", key="name", title="Full Name"),
    q("cEmail", "email", "test@example.com", key="email", title="Email Address"),
    q("cPhoneNumber", "phone", "555-0100", key="phone", title="Phone Number"),
    q("cAddress", "location", "Springfield, IL", "breezy:address", key="location", title="Address"),
    q("salaryCurrency", "choice", "canadian dollar ($)", "breezy:select", title="Currency"),
    q("cSalary", "number", "$85,000", "breezy:salary", title="Desired Salary"),
    q(breezy.PER, "choice", "Yearly", "breezy:select", breezy.PERIODS, title="Per"),
    q("cLocation", "choice", "FL, US", "breezy:select", ["VA, US", "FL, US"], title="Preferred Location"),
    q("cSummary", "longtext", "Line one\nLine two", title="Summary"),
    q("cCoverLetter", "longtext", "Dear Acme,\nThanks.", title="Cover Letter"),
    q("section_1000_question_0", "text", "Two weeks"),
    q("section_1000_question_1", "yesno", "Yes", "breezy:select", ["Yes", "No"]),
    q("section_1000_question_2", "yesno", "No", "breezy:radio", ["Yes", "No"]),
    q("section_1000_question_3", "multichoice", ["Python", "Excel"], "breezy:checkbox"),
    q("section_1000_question_4", "date", "2026-11-02", "breezy:date", title="Start"),
    q("gender", "choice", "I don't wish to answer", "breezy:radio", title="Gender"),
    q("eeoc.veteran_status", "choice", "I am not a protected veteran", "breezy:radio", title="Veteran status")]
# each box's value or tick, each list's pick, the resume header's file name + error words - read off the page
WINDOW_SHOWN = ("es => es.map(e => ['checkbox', 'radio'].includes(e.type) ? e.checked : e.value)"
                ".concat([...document.querySelectorAll('.section-header .file-input-container a.bzyLinkColor,"
                " .error-container:not(.ng-hide) span.error')].map(e => e.innerText.trim()))")
WINDOW_BOXES = "form[name=form] input:not([type=file]):not([type=hidden]), form[name=form] textarea, form[name=form] select"


def test_in_window_fills_breezy_as_playwright_does(tab, site, playwright_chrome, tmp_path, monkeypatch):
    # breezy.fill + holds + form.fill_page through each: same report, same page after, every answer read
    # back, a second fill changes nothing; honeypot + SMS consent + CCPA untouched (plan-k8n.35)
    monkeypatch.setattr(fill_form, "SETTLE_MS", 300)
    monkeypatch.setattr(breezy, "IDLE_WAIT_MS", 500)
    resume = tmp_path / "Test_Resume.pdf"
    resume.write_bytes(b"%PDF-1.4\n%%EOF\n")
    again = [a for a in WINDOW_ANSWERS if a["kind"] != "file"]
    reports, pages = {}, {}
    with both(tab, playwright_chrome, site.replace("/acme/jobs/1", BREEZY_PATH)) as tabs:
        for name, page in tabs.items():
            assert fill_form.closed(page, breezy) is None
            report, extra = fill_form.fill_page(page, breezy, WINDOW_ANSWERS, str(resume), None)
            reports[name] = dict(report)
            # left unanswered here: the question file, the reference check, race (voluntary), CCPA (the applicant's own)
            assert extra == ["section_1000_question_5", "section_1000_question_6", "race_ethnicity", "ccpaAgreement"]
            once = page.eval_on_selector_all(WINDOW_BOXES, WINDOW_SHOWN)
            assert (name, [breezy.fill(page, a, None) for a in again]) == (name, ["ok"] * len(again))
            page.wait_for_timeout(300)
            assert page.eval_on_selector_all(WINDOW_BOXES, WINDOW_SHOWN) == once
            pages[name] = once
            assert [a["id"] for a in WINDOW_ANSWERS if not breezy.holds(page, a)] == []
            assert not page.evaluate("window.submitted || false")
            assert page.evaluate("""() => [document.querySelector('[name=hp_7f2b]').value,
                document.querySelector('[name=smsConsent]').checked, document.querySelector('[name=ccpaAgreement]').checked]""") == ["", False, False]
    assert reports["window"] == reports["playwright"]
    assert reports["window"] == {a["id"]: "ok" for a in WINDOW_ANSWERS}
    assert pages["window"] == pages["playwright"]
    assert resume.name in pages["window"]
