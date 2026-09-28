import importlib
import inspect
import pkgutil

import pytest

from apply import questions, systems
from apply.systems import ashby, ukg

CONTACT = {"name": "Ada King Lovelace", "email": "ada@example.com", "phone": "555-0100",
           "links": ["linkedin.com/in/ada", "github.com/ada"]}
CONTRACT = {"NAME": str, "READY": str, "matches": 1, "application_url": 1, "questions": 1, "fill": 3, "ids_on_page": 1}


def q(title, kind="text", key=None, required=True, options=(), id=None):
    return questions.question(id or title, title, kind, required, options, key)


# --- every system: same contract, so adding one never touches the shared code ---

@pytest.mark.parametrize("module", [m.name for m in pkgutil.iter_modules(systems.__path__)])
def test_every_system_module_is_registered_and_keeps_the_contract(module):
    system = importlib.import_module(f"apply.systems.{module}")
    assert system in systems.SYSTEMS, f"{module} not in systems.SYSTEMS"
    for name, want in CONTRACT.items():
        got = getattr(system, name)
        if isinstance(want, type):
            assert isinstance(got, want), name
        else:
            assert len(inspect.signature(got).parameters) == want, name


def test_link_picks_its_system_or_says_where_else():
    assert systems.for_url("https://jobs.ashbyhq.com/acme/45bdb7e5-14a8-494f-8fcb-30e42f0be67a") is ashby
    assert systems.for_url("https://boards.greenhouse.io/acme/jobs/1") is None
    assert "Workday" in systems.elsewhere("https://acme.wd5.myworkdayjobs.com/en-US/careers/job/x")


# --- shared answers: work the same for every system ---

def test_resume_answers_only_what_it_states():
    qs = [q("Name", key="name"), q("First name", key="first_name"), q("Last name", key="last_name"),
          q("Email", "email"), q("Phone", "phone"), q("LinkedIn Profile URL", key="linkedin"),
          q("GitHub", key="github"), q("Location", "location", key="location"), q("Why us?", "longtext")]
    got = {a["title"]: a["answer"] for a in questions.draft(qs, CONTACT)}
    assert got["Name"] == "Ada King Lovelace" and got["First name"] == "Ada" and got["Last name"] == "King Lovelace"
    assert got["Email"] == "ada@example.com" and got["Phone"] == "555-0100"
    assert got["LinkedIn Profile URL"] == "https://www.linkedin.com/in/ada"
    assert got["GitHub"] == "https://www.github.com/ada"
    assert got["Location"] is None and got["Why us?"] is None  # the user's, never guessed


def test_link_questions_recognised_by_title():
    assert questions.key_from_title("LinkedIn Profile URL", "text") == "linkedin"
    assert questions.key_from_title("Portfolio or website", "url") == "website"
    assert questions.key_from_title("Why LinkedIn?", "longtext") is None


def test_earlier_answers_survive_a_second_prepare():
    old = [{"id": "Why us?", "answer": "Their words.", "source": "user"}]
    assert questions.draft([q("Why us?", "longtext")], CONTACT, old)[0]["answer"] == "Their words."


def test_work_permit_only_for_the_same_us_question():
    config = {"work_authorization": {"authorized_us": True, "needs_sponsorship": False}}
    same = [q("Are you legally authorized to work in the U.S. without restriction for any employer?", "yesno"),
            q("Will you now or in the future require immigration sponsorship to work in the U.S.?", "yesno")]
    assert [a["answer"] for a in questions.draft(same, CONTACT, config=config)] == ["Yes", "No"]
    other = [q("Are you authorized to work in Canada?", "yesno"),
             q("Are you legally authorized to work in the U.S. without restriction for any employer?")]
    assert [a["answer"] for a in questions.draft(other, CONTACT, config=config)] == [None, None]
    unset = questions.draft(same, CONTACT, config={"work_authorization": {"authorized_us": None}})
    assert unset[0]["answer"] is None and unset[0]["source"] == questions.ASK


def test_citizen_or_green_card_answered_only_for_the_us():
    config = {"work_authorization": {"citizen_or_permanent_resident": True}}
    us = [q("Are you a US citizen or lawful permanent resident?", "yesno"),
          q("Are you a U.S. citizen or green card holder?", "yesno")]
    assert [a["answer"] for a in questions.draft(us, CONTACT, config=config)] == ["Yes", "Yes"]
    canada = [q("Are you a Canadian citizen or permanent resident?", "yesno")]
    assert questions.draft(canada, CONTACT, config=config)[0]["answer"] is None
    unset = questions.draft(us, CONTACT, config={"work_authorization": {}})
    assert unset[0]["answer"] is None and unset[0]["source"] == questions.ASK


def test_blank_required_questions_are_listed():
    answers = [{**q("A"), "answer": None}, {**q("B", required=False), "answer": None},
               {**q("C", "multichoice"), "answer": []}, {**q("D", "yesno"), "answer": "No"}]
    assert [a["title"] for a in questions.missing(answers)] == ["A", "C"]


def test_unknown_kind_or_key_is_refused():
    with pytest.raises(AssertionError):
        questions.question("x", "X", "dropdown", True)
    with pytest.raises(AssertionError):
        questions.question("x", "X", "text", True, key="salary")


# --- Ashby ---

def test_ashby_link_with_or_without_application_or_tracking_tail():
    base = "https://jobs.ashbyhq.com/acme/45bdb7e5-14a8-494f-8fcb-30e42f0be67a"
    for url in (base, base + "/application", base + "?utm_source=freehire.me"):
        assert ashby.application_url(url) == base + "/application"
    with pytest.raises(ValueError):
        ashby.parse_url("https://acme.myworkdayjobs.com/x")


def test_ashby_form_becomes_shared_questions():
    def entry(path, title, kind, required=True, values=None, off=False):
        f = {"path": path, "title": title, "type": kind, "isDeactivated": off}
        if values:
            f["selectableValues"] = [{"label": v, "isArchived": v.startswith("old")} for v in values]
        return {"isRequired": required, "field": f}
    job = {"applicationForm": {"sections": [{"fieldEntries": [
        entry("_systemfield_name", "Name", "String"), entry("_systemfield_resume", "Resume", "File"),
        entry("abc", "LinkedIn Profile URL", "String"), entry("def", "Years?", "ValueSelect", values=["old", "10+"]),
        entry("ghi", "Authorized?", "Boolean"), entry("gone", "Gone", "String", off=True),
        entry("new", "Rating", "SomeNewType", required=False), {"isRequired": True},
    ]}]}}
    got = {x["id"]: x for x in ashby.from_form(job)}
    assert list(got) == ["_systemfield_name", "_systemfield_resume", "abc", "def", "ghi", "new"]
    assert got["_systemfield_name"]["key"] == "name" and got["_systemfield_resume"]["kind"] == "file"
    assert got["abc"]["key"] == "linkedin" and got["def"]["options"] == ["10+"] and got["ghi"]["kind"] == "yesno"
    assert got["new"]["kind"] == "text" and got["new"]["native"] == "SomeNewType"  # unknown type: typed as text



# --- UKG Pro Recruiting ---

UKG_BASE = "https://recruiting2.ultipro.com/acme1001/JobBoard/0a1b2c3d-0000-4000-8000-00000000b0a4"
UKG_ID = "0a1b2c3d-0000-4000-8000-0000000000f1"
# SNAPSHOT as read off a signed-in form (tenant A, 2026-09), employer renamed, no answers in it
UKG_FORM = {
    "signin": False, "upload": True, "referral": True, "startDate": True,
    "fields": [
        {"id": "Country", "label": "Country", "required": False, "options": ["Canada", "United States"]},
        {"id": "AddressLine1", "label": "Address 1", "required": True, "options": []},
        {"id": "State", "label": "State / Province", "required": True, "options": ["Alabama", "New Jersey"]},
        {"id": "Phone", "label": "Primary Phone", "required": True, "options": []},
        {"id": "ApplicantSource", "label": "How did you hear about this opportunity?", "required": True,
         "options": ["Acme Careers", "LinkedIn", "Other"]}],
    "questions": [
        {"Id": "0a1b2c3d-0000-4000-8000-000000000001", "ResponseType": "MultipleChoice", "Choices": ["Yes", "No"],
         "Question": "Have you ever been employed within the executive or legislative branch of the U.S. Federal\nGovernment?"},
        {"Id": "0a1b2c3d-0000-4000-8000-000000000002", "ResponseType": "Text", "Choices": [],
         "Question": "What state are you currently located in?"},
        {"Id": "11111111-2222-3333-4444-555555555555", "ResponseType": "MultipleChoice",
         "Choices": ["0-2", "3-5", "6+"], "Question": "Years of experience?"},
        {"Id": "66666666-7777-8888-9999-000000000000", "ResponseType": "Numeric", "Choices": [],
         "Question": "Desired salary?"}],
    "eeo": [
        {"id": "Gender", "label": "Gender", "required": True, "options": ["Male", "Female"], "decline": True},
        {"id": "EthnicOrigin", "label": "Race", "required": False, "options": ["White", "Asian"], "decline": True},
        {"id": "USFederalContractor", "label": "Are you a protected veteran?", "required": True,
         "options": ["Yes", "No"], "decline": True}],
}


def test_ukg_link_detail_or_apply_with_or_without_tracking_tail():
    want = f"{UKG_BASE}/OpportunityApply?opportunityId={UKG_ID}"
    for url in (f"{UKG_BASE}/OpportunityDetail?opportunityId={UKG_ID}", want,
                f"{UKG_BASE}/OpportunityDetail?opportunityId={UKG_ID}&utm_source=freehire.me",
                f"{UKG_BASE}/OpportunityDetail?utm_source=freehire.me&opportunityId={UKG_ID}"):
        assert systems.for_url(url) is ukg and ukg.application_url(url) == want
    assert systems.for_url("https://recruiting.ultipro.com/acme1001/JobBoard/list") is None
    with pytest.raises(ValueError):
        ukg.parse_url("https://jobs.ashbyhq.com/acme/45bdb7e5-14a8-494f-8fcb-30e42f0be67a")


def test_ukg_form_becomes_shared_questions():
    got = {x["id"]: x for x in ukg.from_snapshot(UKG_FORM)}
    assert got["Phone"]["key"] == "phone" and got["Phone"]["kind"] == "phone"
    assert got["AddressLine1"]["key"] is None and got["State"]["options"] == ["Alabama", "New Jersey"]
    assert got["resume"]["kind"] == "file" and got["start-date"]["kind"] == "date"
    assert got["employeereferral"]["kind"] == "yesno"
    fed = got["0a1b2c3d-0000-4000-8000-000000000001"]
    assert fed["kind"] == "yesno" and "Federal Government?" in fed["title"]  # line break in the title folded
    assert got["0a1b2c3d-0000-4000-8000-000000000002"]["kind"] == "longtext"
    assert got["11111111-2222-3333-4444-555555555555"]["kind"] == "choice"
    assert got["66666666-7777-8888-9999-000000000000"]["kind"] == "number"
    assert got["Gender"]["options"] == ["Male", "Female", ukg.DECLINE]  # decline is a checkbox beside the list
    assert got["EthnicOrigin"]["required"] is False  # Race shows only after "Not Hispanic/Latino"
    last = list(got.values())[-1]
    assert last["id"] == ukg.PROFILE and last["required"] is False and "as it is added" in last["title"]


def test_ukg_form_questions_asked_not_guessed():
    config = {"work_authorization": {"authorized_us": True, "needs_sponsorship": False}}
    drafted = questions.draft(ukg.from_snapshot(UKG_FORM), CONTACT, config=config)
    answered = {a["id"]: a["answer"] for a in drafted if a["answer"]}
    assert answered == {"Phone": "555-0100"}  # everything else - address, disclosures, sections - asked


def test_ukg_resume_sections_mapping():
    assert [ukg.degree_word(d) for d in ("BA", "B.S.", "AA", "MBA", "MS", "PhD", "Doctor of Medicine", "")] == \
        ["Bachelor", "Bachelor", "Associate", "Master", "Master", "Doctor", "Doctor", None]
    majors = ["Art", "Art Education", "Art History", "Computer Science"]
    assert ukg.major_option("Art Education in School and Community", majors) == "Art Education"
    assert ukg.major_option("computer science", majors) == "Computer Science"
    assert ukg.major_option("Artificial Intelligence", majors) is None  # never a partial word
    assert ukg.month_year("2023-02") == ("Feb", "2023") and ukg.month_year("2016") == ("", "2016")
    assert ukg.month_year("present") is None and ukg.month_year(None) is None
    assert [ukg.link_title(u) for u in ("linkedin.com/in/ada", "https://github.com/ada", "ada.dev")] == \
        ["LinkedIn", "GitHub", "Website"]


def test_ukg_work_description_uses_tailored_lines_first():
    role = {"id": "acme", "bullets": [{"claim": "Master line."}]}
    tailored = {"entries": [{"id": "acme", "bullets": [{"text": "Tailored line one."}, {"text": "Two."}]}]}
    assert ukg.description(role, tailored) == "- Tailored line one.\n- Two."
    assert ukg.description(role, {}) == "- Master line."
    assert len(ukg.description({"id": "x", "bullets": [{"claim": "x" * 3000}]}, {})) == 2000

def test_open_chrome_found_by_its_command_line_when_the_port_file_is_gone(tmp_path, monkeypatch):
    from apply import browser
    monkeypatch.setattr(browser, "PROFILE", tmp_path)
    monkeypatch.setattr(browser, "PORT_FILE", tmp_path / "job-finder-port")
    line = f"/Applications/Google Chrome --remote-debugging-port=55211 --user-data-dir={tmp_path} --no-first-run\n"
    monkeypatch.setattr(browser.subprocess, "run", lambda *a, **k: browser.subprocess.CompletedProcess(a, 0, line, ""))
    monkeypatch.setattr(browser, "answers", lambda port: port == 55211)
    assert browser.live_port() == 55211
    assert (tmp_path / "job-finder-port").read_text() == "55211"
