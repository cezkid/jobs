import importlib
import inspect
import json
import pkgutil
from datetime import date
from pathlib import Path
from urllib.parse import urlsplit

import pytest

from apply import browser, form, questions, systems
from apply.systems import ashby, bamboohr, greenhouse, icims, jazzhr, lever, oracle, smartrecruiters, ukg, workable

CONTACT = {"name": "Ada King Lovelace", "email": "ada@example.com", "phone": "555-0100",
           "links": ["linkedin.com/in/ada", "github.com/ada"]}
CONTRACT = {"NAME": str, "READY": str, "SOURCES": tuple, "EXAMPLES": tuple,
            "matches": 1, "application_url": 1, "questions": 1, "fill": 3, "ids_on_page": 1}


def q(title, kind="text", key=None, required=True, options=(), id=None):
    return questions.question(id or title, title, kind, required, options, key)


# --- every system: same contract, so adding one never touches the shared code ---

@pytest.mark.parametrize("module", [m.name for m in pkgutil.iter_modules(systems.__path__)])
def test_every_system_module_is_found_and_keeps_the_contract(module):
    system = importlib.import_module(f"apply.systems.{module}")
    assert system in systems.SYSTEMS, f"{module} not found by systems.discover()"
    for name, want in CONTRACT.items():
        got = getattr(system, name)
        if isinstance(want, type):
            assert isinstance(got, want), name
        else:
            # a defaulted parameter is the system's own extra (Greenhouse: questions(url, schools=1))
            assert sum(p.default is p.empty for p in inspect.signature(got).parameters.values()) == want, name
    assert system.SOURCES and system.EXAMPLES and all(isinstance(x, str) for x in system.SOURCES + system.EXAMPLES)


# systems whose answers form.recheck reads back off the page (shown value, never the filler's word);
# the other systems are left as filled until they join this list
IN_SCOPE = [greenhouse, ashby, lever, jazzhr, workable, bamboohr, oracle, icims, smartrecruiters]


@pytest.mark.parametrize("system", IN_SCOPE, ids=lambda s: s.__name__.rsplit(".", 1)[-1])
def test_read_back_systems_define_holds(system):
    assert sum(p.default is p.empty for p in inspect.signature(system.holds).parameters.values()) == 2


def test_systems_found_in_name_order_no_hand_list():
    names = [m.__name__.rsplit(".", 1)[-1] for m in systems.SYSTEMS]
    assert names == sorted(m.name for m in pkgutil.iter_modules(systems.__path__))


@pytest.mark.parametrize("system", systems.SYSTEMS, ids=lambda s: s.__name__.rsplit(".", 1)[-1])
def test_each_example_link_matches_exactly_one_system(system):
    for link in system.EXAMPLES:
        assert [s for s in systems.SYSTEMS if s.matches(link)] == [system], link
        assert system.matches(system.application_url(link)), link
        assert "acme" in link.casefold(), "example links stay anonymised"


def test_link_picks_its_system_or_says_where_else():
    assert systems.for_url("https://jobs.ashbyhq.com/acme/45bdb7e5-14a8-494f-8fcb-30e42f0be67a") is ashby
    assert systems.for_url("https://boards.greenhouse.io/acme/jobs/1") is greenhouse
    assert systems.for_url("https://acme.recruitee.com/o/analyst") is None
    assert "Workday" in systems.elsewhere("https://acme.wd5.myworkdayjobs.com/en-US/careers/job/x")


# --- shared answers: work the same for every system ---

def test_resume_answers_only_what_it_states():
    qs = [q("Name", key="name"), q("First name", key="first_name"), q("Last name", key="last_name"),
          q("Email", "email"), q("Phone", "phone"), q("LinkedIn Profile URL", key="linkedin"),
          q("GitHub", key="github"), q("Location", "location", key="location"), q("Why us?", "longtext")]
    got = {a["title"]: a["answer"] for a in questions.draft(qs, CONTACT)}
    assert got["Name"] == "Ada King Lovelace"
    assert got["First name"] is None and got["Last name"] is None  # Ada King / Lovelace or Ada / King Lovelace
    assert got["Email"] == "ada@example.com" and got["Phone"] == "555-0100"
    assert got["LinkedIn Profile URL"] == "https://www.linkedin.com/in/ada"
    assert got["GitHub"] == "https://www.github.com/ada"
    assert got["Location"] is None and got["Why us?"] is None  # the user's, never guessed


def test_link_questions_recognised_by_title():
    assert questions.key_from_title("LinkedIn Profile URL", "text") == "linkedin"
    assert questions.key_from_title("Portfolio or website", "url") == "website"
    assert questions.key_from_title("Why LinkedIn?", "longtext") is None


NAME_BOXES = [q("Name", key="name"), q("First name", key="first_name"), q("Last name", key="last_name")]


def name_answers(contact, boxes=NAME_BOXES):
    return {a["title"]: (a["answer"], a["source"]) for a in questions.draft(boxes, contact)}


@pytest.mark.parametrize("name, first, last", [
    ("Ada Lovelace", "Ada", "Lovelace"),        # two words: said outright
    ("Mary Ann Smith", None, None),             # Mary Ann / Smith or Mary / Ann Smith: never guessed
    ("J. Smith", None, None),                   # an initial on the page is not what a form wants
    ("Ada L", None, None),
    ("Sukarno", "Sukarno", None),               # a mononym has no last name to give
])
def test_first_and_last_only_when_the_name_says_it_outright(name, first, last):
    got = name_answers({"name": name})
    assert got["Name"][0] == name
    assert (got["First name"][0], got["Last name"][0]) == (first, last)
    assert all(source == questions.ASK for answer, source in got.values() if answer is None)


def test_name_boxes_recognised_by_title():
    want = {"Legal first name": "legal_first", "Full legal name": "legal_name", "Name for background check": "legal_name",
            "Preferred name": "preferred_name", "Preferred first name": "preferred_first",
            "What name do you go by?": "preferred_name", "Other names used": "other_names", "Maiden name": "other_names",
            "Surname": "last_name", "Middle name": "middle_name", "Full name": "name",
            "Referrer name": None, "Hiring manager name": None, "Name of school": None, "Username": None}
    assert {t: questions.key_from_title(t, "text") for t in want} == want


LEGAL = {"name": "J. Doe", "legal_first": "Jane", "legal_middle": "Quinn", "legal_last": "Doe",
         "other_names": ["Jane Roe"]}


def test_legal_box_gets_legal_name_and_preferred_box_the_page_name():
    boxes = [q(t, key=questions.key_from_title(t, "text")) for t in
             ("Legal first name", "Legal last name", "Full legal name", "Preferred name", "Other names used")]
    got = name_answers(LEGAL, boxes)
    assert got["Legal first name"][0] == "Jane" and got["Legal last name"][0] == "Doe"
    assert got["Full legal name"][0] == "Jane Quinn Doe"
    assert got["Preferred name"][0] == "J. Doe"
    assert got["Other names used"][0] == "Jane Roe"
    assert name_answers({"name": "J. Doe"}, boxes)["Full legal name"] == (None, questions.ASK)  # no legal fields


def test_plain_name_box_asks_once_when_page_and_legal_differ_then_reuses_the_answer():
    got = name_answers(LEGAL)
    assert got["Name"] == got["First name"] == got["Last name"] == (None, questions.ASK_FORM_NAME)
    legal = name_answers({**LEGAL, "form_name": "legal"})
    assert [legal[t][0] for t in ("Name", "First name", "Last name")] == ["Jane Quinn Doe", "Jane", "Doe"]
    page = name_answers({**LEGAL, "form_name": "page"})
    assert [page[t][0] for t in ("Name", "First name", "Last name")] == ["J. Doe", "J.", "Doe"]


@pytest.mark.parametrize("page", ["José García", "jose garcia", "JOSÉ  GARCÍA", "José Luis García"])
def test_accents_case_spacing_and_a_left_out_middle_name_are_no_mismatch(page):
    got = name_answers({"name": page, "legal_first": "José", "legal_middle": "Luis", "legal_last": "García"})
    assert got["Name"][0] == page
    assert (got["First name"][0], got["Last name"][0]) == ("José", "García")


def test_earlier_answers_survive_a_second_prepare():
    old = [{"id": "Why us?", "title": "Why us?", "answer": "Their words.", "source": "user"}]
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


SENSITIVE = [
    ("Date of birth", "date", "date of birth"),
    ("Birthdate (MM/DD/YYYY)", "text", "date of birth"),
    ("DOB", "date", "date of birth"),
    ("Graduation date", "date", "graduation date"),
    ("What year did you graduate from high school?", "number", "graduation date"),
    ("Year of graduation", "number", "graduation date"),
    ("When did you graduate?", "text", "graduation date"),
    ("Have you ever been convicted of a felony?", "yesno", "criminal history"),
    ("Do you have any criminal convictions in the last 7 years?", "yesno", "criminal history"),
    ("Have you ever been arrested or pleaded guilty to a misdemeanor?", "yesno", "criminal history"),
    ("Please explain any gaps in your employment history", "longtext", "work break"),
    ("Why were you unemployed between jobs?", "longtext", "work break"),
    ("Tell us about any career break longer than six months", "longtext", "work break"),
    ("Do you have a disability or medical condition we should know about?", "yesno", "disability or health"),
    ("Voluntary Self-Identification of Disability", "choice", "disability or health"),
    ("Will you need a reasonable accommodation to complete the interview?", "yesno", "disability or health"),
    ("Other names used", "text", "other names"),
    ("Have you ever been known by any other names?", "text", "other names"),
]
NEAR_MISSES = ["Are you at least 18 years of age?", "Does your date of birth make you 18 or older?", "Post-graduation plans",
               "Do you hold a graduate degree?", "Experience in a recording studio", "Degree in criminal justice?",
               "Years of experience with criminal defense cases", "BLS certification for cardiac arrest",
               "Describe a gap analysis you led", "Are you available over spring break?",
               "Experience with medical devices", "Tell us about your health and safety training",
               "Previous employer name", "Why us?"]


@pytest.mark.parametrize("title, kind, want", SENSITIVE)
def test_sensitive_questions_tagged_and_left_for_the_user(title, kind, want):
    (a,) = questions.draft([q(title, kind, key=questions.key_from_title(title, kind))], CONTACT)
    assert questions.sensitive(a, CONTACT) == want
    assert a["answer"] is None and a["source"] == f"{questions.ASK} - sensitive: {want}"


@pytest.mark.parametrize("title", NEAR_MISSES)
def test_near_miss_titles_not_tagged(title):
    kind = "yesno" if title.endswith("?") else "text"
    assert questions.sensitive(q(title, kind, key=questions.key_from_title(title, kind)), CONTACT) is None


def test_sensitive_question_stays_blank_even_when_a_saved_answer_fits():
    config = {"work_authorization": {"authorized_us": True}}
    both = q("Are you authorized to work in the U.S. without restriction, and have you ever been convicted of a "
             "crime?", "yesno")
    assert questions.draft([both], CONTACT, config=config)[0]["answer"] is None
    # a program-filled answer from before the tag is dropped; the user's own answer survives
    auto = [{"id": both["id"], "title": both["title"], "answer": "Yes", "source": "search settings - name it to the user"}]
    assert questions.draft([both], CONTACT, auto, config)[0]["answer"] is None
    theirs = [{"id": both["id"], "title": both["title"], "answer": "No", "source": "user"}]
    assert questions.draft([both], CONTACT, theirs, config)[0]["answer"] == "No"
    # other names saved in resume details are theirs to give: no tag, answer filled
    other = q("Other names used", key="other_names")
    assert questions.draft([other], LEGAL)[0]["answer"] == "Jane Roe"
    assert questions.draft([other], CONTACT, [{"id": other["id"], "title": other["title"], "answer": "Jane Roe", "source": "resume"}])[0][
        "answer"] is None


CONSENT = ["I agree to the Terms and Conditions", "I have read the Privacy Notice", "Privacy policy consent",
           "SMS consent", "I consent to receive text messages about my application",
           "Would you like to receive SMS updates about your application?", "May we text you?",
           "Electronic Signature", "Signature (type your full name)", "E-sign: type your legal name",
           "Type your full name to sign", "I certify that the information above is true and complete",
           "I acknowledge that I have read the above statement", "Opt in to automated calls",
           "Terms of Use", "Do you give us permission to text you?"]
CONSENT_NEAR_MISSES = ["Do you hold a Series 7 license?", "Describe a project you signed off",
                       "Privacy engineering experience?", "Experience obtaining informed consent in clinical trials?",
                       "Do you hold a professional certification?", "Experience with digital signature algorithms",
                       "Are you authorized to work in the United States?", "Why us?"]


@pytest.mark.parametrize("title", CONSENT)
def test_consent_terms_and_signature_left_for_the_user_on_the_page(title):
    kind = "yesno" if title.endswith("?") or title.startswith(("I ", "SMS", "Opt", "Privacy")) else "text"
    (a,) = questions.draft([q(title, kind, key=questions.key_from_title(title, kind))], CONTACT)
    assert questions.never_draft(title) == "agreeing, consenting or signing"
    assert a["answer"] is None and a["source"] == f"{questions.ASK} - {questions.SIGN_ON_PAGE}: {questions.SIGNING}"
    assert "(yours to do on the page: agreeing, consenting or signing)" in form.line(a)


@pytest.mark.parametrize("title", CONSENT_NEAR_MISSES)
def test_consent_near_misses_not_tagged(title):
    assert questions.never_draft(title) != questions.SIGNING


# measured 2026-10-05, Greenhouse tenant E (employer's own page), a required question
AI_ATTESTATION = ("I confirm that my application materials and interview responses reflect my own work and were not "
                  "generated, edited, or supplemented by AI tools (e.g., ChatGPT, Gemini, Claude, etc.).")
AI_USE = [AI_ATTESTATION, "Did you use AI tools such as ChatGPT to write or edit your resume or cover letter?",
          "I certify that my responses to this application were not written by artificial intelligence.",
          "Was any part of your application generated using AI?"]
AI_NEAR_MISSES = ["Do you have experience with AI tools such as ChatGPT or Copilot?",
                  "Describe how you have used generative AI in your work.",
                  "Tell us about a time you used AI to draft responses to customers.",
                  "How would you use LLMs to help our recruiting team review applications?",
                  "Please confirm your email address"]


@pytest.mark.parametrize("title", AI_USE)
def test_ai_use_attestation_left_for_the_user_on_the_page(title):
    (a,) = questions.draft([q(title, "yesno")], CONTACT)
    assert questions.never_draft(title) == questions.AI_USE and questions.signs(title)
    assert a["answer"] is None and a["source"] == f"{questions.ASK} - {questions.SIGN_ON_PAGE}: {questions.AI_USE}"
    assert "(yours to do on the page: saying whether AI helped)" in form.line(a)
    # a Yes the AI wrote, or the user's own "you said": never kept, never typed, not counted missing
    said = {**a, "answer": "Yes", "source": questions.USER_SAID}
    assert questions.draft([q(title, "yesno")], CONTACT, [said])[0]["answer"] is None
    assert questions.missing([a]) == [] and questions.on_page([said])
    with pytest.raises(SystemExit, match="ticks or signs these on the page"):
        form.refuse([said])
    assert questions.left_on_page(a) == "ASK yours to do on the page - saying whether AI helped"
    assert "tailored with AI help" in form.ai_note([a]) and form.ai_note([q("Why us?", "longtext")]) == ""


@pytest.mark.parametrize("title", AI_NEAR_MISSES)
def test_ai_use_near_misses_not_tagged(title):
    assert questions.never_draft(title) != questions.AI_USE and not questions.signs(title)


def test_signature_box_never_answered_from_the_resume():
    for title in ("Signature (type your full name)", "Electronic signature - legal name", "Full name (signature)"):
        assert questions.key_from_title(title, "text") is None, title
        (a,) = questions.draft([q(title, key=questions.key_from_title(title, "text"))], CONTACT)
        assert a["answer"] is None, title
    # a system's own name field id on a signing box: still not the resume's name
    (a,) = questions.draft([q("Signature (type your full name)", key="name")], CONTACT)
    assert a["answer"] is None


def test_consent_answer_never_kept_never_typed_and_not_counted_missing():
    terms = q("I agree to the Terms and Conditions", "yesno")
    # even the user's own "you said" from an earlier prepare is dropped: they tick it on the page
    old = [{**terms, "answer": "Yes", "source": questions.USER_SAID}]
    (a,) = questions.draft([terms], CONTACT, old)
    assert a["answer"] is None and a["source"].startswith(questions.ASK)
    assert questions.missing([a]) == []
    assert questions.on_page([{**a, "answer": "Yes", "source": questions.USER_SAID}])
    with pytest.raises(SystemExit, match="ticks or signs these on the page"):
        form.refuse([{**a, "answer": True, "source": questions.USER_SAID}])


def test_old_answer_kept_only_for_the_same_id_and_title():
    old = [{"id": "rc_select_4", "title": "Please tell us: why us?", "answer": "Their words.", "source": questions.USER_SAID}]
    # same question, polite wording and case folded away: kept
    assert questions.draft([q("Why us?", "longtext", id="rc_select_4")], CONTACT, old)[0]["answer"] == "Their words."
    # a generated id naming another question on the next load: drafted fresh
    (a,) = questions.draft([q("Anything else we should know?", "longtext", id="rc_select_4")], CONTACT, old)
    assert a["answer"] is None and a["source"] == questions.ASK
    # an id that held a "you said" answer now on a consent box: blank, the user's on the page
    (a,) = questions.draft([q("SMS consent", "yesno", id="rc_select_4")], CONTACT, old)
    assert a["answer"] is None and a["source"].startswith(questions.ASK)


def test_fill_report_by_id_when_two_questions_share_a_title(tmp_path, monkeypatch, capsys):
    import contextlib

    from resume import tailor
    folder = tmp_path / "7 - Acme - Analyst"
    phones = [{**q("Phone", "phone", id="p1"), "answer": "555-0100"}, {**q("Phone", "phone", id="p2"), "answer": "555-0100"}]
    questions.save(folder / tailor.JOB_DATA / questions.FILE,
                   {"system": "Fake", "url": "https://jobs.example/1", "questions": phones})
    monkeypatch.setattr(form.cfg, "load", lambda: {})
    monkeypatch.setattr(form, "job_dir", lambda config, slug: folder)
    monkeypatch.setattr(form, "resume_for", lambda config, folder: None)

    class Fake:
        NAME, READY = "Fake", "form"

        def fill(page, q, resume_file):
            return "ok" if q["id"] == "p1" else "FAIL box not found"

        def ids_on_page(page):
            return ["p1", "p2"]

    class Page:
        first = property(lambda self: self)
        locator = lambda self, selector: self
        wait_for = lambda self, timeout: None
        inner_text = lambda self, timeout: ""
    monkeypatch.setattr(form, "system_for", lambda url: Fake)
    monkeypatch.setattr(form.browser, "page_at", lambda url, match=None: contextlib.nullcontext(Page()))
    form.fill("7")
    out = capsys.readouterr().out
    assert "  [ok] Phone\n  [FAIL box not found] Phone\n" in out
    assert "required answered 1 of 2 - still to do on the page: Phone" in out


def test_prepare_line_names_the_sensitive_kind():
    (a,) = questions.draft([q("Date of birth", "date")], CONTACT)
    assert form.line(a) == "  [NEEDED] date: Date of birth (sensitive: date of birth)"
    (plain,) = questions.draft([q("Why us?", "longtext", required=False)], CONTACT)
    assert form.line(plain) == "  [optional] longtext: Why us?"


BREAKS = [{"reason": "Caring for a family member", "start": "2021-02", "end": "2023-01",
           "explain": "I cared for a family member full time and kept my skills current."},
          {"reason": "Travel", "start": "2012", "end": "2013", "explain": "I travelled for a year."}]
TODAY = date(2026, 9, 29)


def test_work_break_question_answered_from_the_users_saved_words():
    newest = q("Explain any gaps in employment", "longtext")
    (a,) = questions.draft([newest], CONTACT, breaks=BREAKS[:1])
    assert a["answer"] == BREAKS[0]["explain"]
    assert a["source"] == "resume - sensitive: work break - read it before Submit"
    assert form.line(a) == "  [ok] longtext: Explain any gaps in employment (sensitive: work break - read it before Submit)"
    # a window the question names: the 2012 break is outside the last 5 years
    last5 = q("Explain any gaps in employment in the last 5 years", "longtext")
    assert questions.break_answer(last5, BREAKS, TODAY) == BREAKS[0]["explain"]
    # no window: every break, each after its dates, newest first
    every = questions.break_answer(q("Please explain any gaps in your employment history", "longtext"), BREAKS, TODAY)
    assert every == f"Feb 2021 - Jan 2023: {BREAKS[0]['explain']}\n2012 - 2013: {BREAKS[1]['explain']}"
    assert questions.break_answer(q("Employment gaps since 2020", "text"), BREAKS, TODAY) == BREAKS[0]["explain"]
    assert questions.break_answer(q("Explain gaps in employment in the past ten years"), BREAKS, TODAY) \
        == BREAKS[0]["explain"]
    # a re-prepare refreshes the program's answer from the latest saved words; the user's own edit stays
    later = [{**BREAKS[0], "explain": "Reworded."}]
    assert questions.draft([newest], CONTACT, [a], breaks=later)[0]["answer"] == "Reworded."
    theirs = [{"id": newest["id"], "title": newest["title"], "answer": "Their words.", "source": "user"}]
    assert questions.draft([newest], CONTACT, theirs, breaks=later)[0]["answer"] == "Their words."


def test_work_break_question_stays_needed_without_saved_words_for_every_break_it_asks_about():
    gaps = q("Please explain any gaps in your employment history", "longtext")
    unexplained = [BREAKS[0], {k: v for k, v in BREAKS[1].items() if k != "explain"}]
    for breaks in (None, [], unexplained):  # part of the story would read as the whole of it
        (a,) = questions.draft([gaps], CONTACT, breaks=breaks)
        assert a["answer"] is None and a["source"] == "ask the user - sensitive: work break"
    last_year = q("Any gaps in employment in the last 1 year? Explain.", "text")
    assert questions.break_answer(last_year, BREAKS, TODAY) is None  # no break in the window: theirs to say
    assert questions.break_answer(q("Do you have gaps in your employment?", "yesno"), BREAKS, TODAY) is None


@pytest.mark.parametrize("title, kind", [("Date of birth", "date"), ("Have you ever been convicted of a crime?", "text"),
                                         ("Do you need a reasonable accommodation?", "longtext"),
                                         ("What year did you graduate?", "text")])
def test_saved_break_words_never_answer_another_sensitive_kind(title, kind):
    (a,) = questions.draft([q(title, kind)], CONTACT, breaks=BREAKS)
    assert a["answer"] is None and a["source"].startswith("ask the user - sensitive: ")


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


def test_ashby_org_with_a_space_read_as_ashby_names_it():
    """Measured 2026-10-05: a link spelling the org "acme%20corp" - question read null under that
    spelling, the posting's 9 questions under "acme corp"; prepare stopped on an open posting."""
    url = "https://jobs.ashbyhq.com/acme%20corp/45bdb7e5-14a8-494f-8fcb-30e42f0be67a?utm_source=freehire.me"
    assert ashby.parse_url(url) == ("acme corp", "45bdb7e5-14a8-494f-8fcb-30e42f0be67a")
    assert ashby.application_url(url) == \
        "https://jobs.ashbyhq.com/acme%20corp/45bdb7e5-14a8-494f-8fcb-30e42f0be67a/application"


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


def test_ashby_types_from_real_forms_url_and_education_history():
    """Url (31 of 111 open forms) + EducationHistory (2), 2026-10-05: ashby.md "Kinds on real forms"."""
    job = json.loads((Path(__file__).parent / "fixtures" / "ashby" / "survey-kinds.json").read_text())
    got = {q["title"]: q for q in ashby.from_form(job)}
    assert {q["native"] for q in got.values()} <= set(ashby.KIND)
    assert (got["LinkedIn Profile"]["kind"], got["LinkedIn Profile"]["key"]) == ("url", "linkedin")
    samples = next(q for t, q in got.items() if t.startswith("Please provide relevant work samples"))
    assert (samples["kind"], samples["key"], samples["required"]) == ("url", None, False)
    # one block of boxes per school, never one answer: school required, start dates left out (not on a resume)
    boxes = [(q["id"], q["kind"], q["required"]) for q in ashby.from_form(job, 2) if q["native"] == "EducationHistory"]
    path = ashby.EDUCATION_PATH
    assert boxes == [(f"{path}--{key}--{i}", kind, key == "school") for i in (0, 1)
                     for key, kind in (("school", "choice"), ("degree", "text"), ("discipline", "text"),
                                       ("school_end_month", "choice"), ("school_end_year", "number"))]
    assert "Education History" not in got and got["Education 1: School"]["entry"] == 0


def test_ashby_education_filled_per_school_from_resume_details(fixture_page, monkeypatch):
    """Education History (2 employers, 2026-10-05) drafted from Resume details: the school picked off the
    search by its exact words, degree spelled out + field as written in the free-text boxes, graduation
    month + year in the end date's selects; school 2 through the page's own "+ Add Education" (same ids
    in each block); holds() reads each back. A school the list doesn't offer -> the user picks theirs."""
    job = json.loads((Path(__file__).parent / "fixtures" / "ashby" / "survey-kinds.json").read_text())
    asked = [q for q in ashby.from_form(job, 2) if q["native"] == "EducationHistory"]
    schools = [{"institution": "University of California, Berkeley", "degree": "BA", "field": "Economics", "end": "2016-05"},
               {"institution": "Massachusetts Institute of Technology", "degree": "PhD", "field": "Computer Science",
                "end": "2021"}]
    drafted = questions.draft(asked, {}, schools=schools)
    monkeypatch.setattr(form, "SETTLE_MS", 500)
    page = fixture_page("ashby-education.html")
    report, extra = form.fill_page(page, ashby, drafted, None, None)
    assert report == [(q["id"], "ok") for q in drafted if q["answer"]] and len(report) == 9
    assert extra == ["_systemfield_name"]  # the Education History wrapper is never a question the file lacks
    assert all(ashby.holds(page, q) for q in drafted if q["answer"])
    assert page.locator('[id="_systemfield_education_history-degree"]').evaluate_all("es => es.map(e => e.value)") == \
        ["Bachelor of Arts", "Doctor of Philosophy"]
    assert page.locator("input[role=combobox]").evaluate_all("es => es.map(e => e.value)") == \
        ["University of California, Berkeley", "Massachusetts Institute of Technology"]
    ends = page.locator('[id="_systemfield_education_history-endDate"] select').evaluate_all(
        "es => es.map(e => e.value ? e.selectedOptions[0].text : '')")
    assert ends == ["May", "2016", "", "2021"]  # a year alone: no month chosen
    assert page.locator(".block").count() == 2
    assert [ashby.fill(page, q, None) for q in drafted if q["answer"]] == ["ok"] * 9  # again: nothing changes
    assert page.locator(".block").count() == 2
    monkeypatch.setattr(ashby, "LIST_WAIT_MS", 1000)
    school = drafted[0] | {"answer": "Springfield Community College"}
    assert ashby.fill(page, school, None) == \
        "ASK school 'Springfield Community College' not on the form's list - the user picks theirs on the page"
    assert not ashby.holds(page, school)
    month = next(q for q in drafted if q["key"] == "school_end_month") | {"answer": "Smarch"}
    assert ashby.fill(page, month, None) == "ASK no option 'Smarch' - the user picks it on the page"


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
    assert got["AddressLine1"]["key"] == "street" and got["State"]["options"] == ["Alabama", "New Jersey"]
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


def test_ukg_address_from_saved_home_address_only():
    config = {"home_address": {"street": "1 Main St", "city": "Springfield", "state": "Ohio", "zip": "04501"}}
    drafted = {a["id"]: a for a in questions.draft(ukg.from_snapshot(UKG_FORM), CONTACT, config=config)}
    got = {i: drafted[i]["answer"] for i in ("AddressLine1", "City", "State", "PostalCode") if i in drafted}
    assert got == {i: v for i, v in {"AddressLine1": "1 Main St", "City": "Springfield", "State": "Ohio",
                                     "PostalCode": "04501"}.items() if i in drafted}
    assert all(drafted[i]["source"].startswith("search settings") for i in got)


class FakeBox:
    def __init__(self, visible): self.visible, self.checked = visible, False
    def is_visible(self): return self.visible
    def is_checked(self): return self.checked
    def check(self):
        assert self.visible, "ticked a hidden box"  # Playwright waits 30s, then fails
        self.checked = True
    @property
    def first(self): return self


class FakeSelfIdPage:
    def __init__(self, visible): self.box = FakeBox(visible)
    def locator(self, selector): return self.box


def test_ukg_decline_skipped_when_race_is_hidden():
    q = {"id": "EthnicOrigin", "answer": ukg.DECLINE}
    assert ukg.put_self_id(FakeSelfIdPage(visible=False), q).startswith("skipped")  # Hispanic/Latino hides Race
    assert ukg.put_self_id(FakeSelfIdPage(visible=True), q) == "ok"


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


def test_port_file_naming_a_closed_chrome_falls_back_to_the_open_one(tmp_path, monkeypatch):
    # two chats started Chrome at once: the second handed its link over, its port never answers
    from apply import browser
    monkeypatch.setattr(browser, "PROFILE", tmp_path)
    monkeypatch.setattr(browser, "PORT_FILE", tmp_path / "job-finder-port")
    (tmp_path / "job-finder-port").write_text("40001")
    line = f"/Applications/Google Chrome --remote-debugging-port=55211 --user-data-dir={tmp_path}\n"
    monkeypatch.setattr(browser.subprocess, "run", lambda *a, **k: browser.subprocess.CompletedProcess(a, 0, line, ""))
    monkeypatch.setattr(browser, "answers", lambda port: port == 55211)
    assert browser.live_port() == 55211
    assert (tmp_path / "job-finder-port").read_text() == "55211"


def test_fill_uploads_the_pdf_from_where_its_folder_is_now(tmp_path, monkeypatch):
    # job folders move with their status (sent, heard back ...): a path saved at prepare went
    # stale - Ashby's upload failed, UKG typed the untailored resume's lines with no error
    import contextlib

    from apply import form
    from resume import render, tailor
    folder = tmp_path / "My Jobs" / "2 Applied" / "7 - Acme - Analyst"
    (folder / tailor.JOB_DATA).mkdir(parents=True)
    pdf = folder / render.file_name({"contact": CONTACT})
    pdf.write_bytes(b"%PDF-1.7")
    questions.save(folder / tailor.JOB_DATA / questions.FILE, {
        "system": "Fake", "url": "https://jobs.example/1",
        "resume_file": str(tmp_path / "My Jobs" / "Acme - Analyst" / pdf.name),  # where it was
        "questions": [{**q("Resume", "file", "resume"), "answer": True}]})
    monkeypatch.setattr(form.cfg, "load", lambda: {"resume": {"master": "Resume details.yml"}})
    monkeypatch.setattr(form.schema, "load", lambda path: {"contact": CONTACT})
    monkeypatch.setattr(form, "job_dir", lambda config, slug: folder)
    uploaded = []

    class Fake:
        NAME, READY = "Fake", "form"

        def fill(page, q, resume_file):
            uploaded.append(resume_file)
            return "ok"

        def ids_on_page(page):
            return []

    class Page:
        first = property(lambda self: self)

        def locator(self, selector):
            return self

        def wait_for(self, timeout):
            pass
    monkeypatch.setattr(form, "system_for", lambda url: Fake)
    monkeypatch.setattr(form.browser, "page_at", lambda url, match=None: contextlib.nullcontext(Page()))
    form.fill("7")
    assert uploaded == [str(pdf)]
    pdf.unlink()
    form.fill("7")
    assert uploaded[-1] is None  # no PDF there => nothing uploaded, never a stale one


class FakeUkgBox:
    """Any UKG locator: records what is typed or picked, by the data-automation name."""
    def __init__(self, log, name=""):
        self.log, self.name = log, name

    def locator(self, selector):
        return FakeUkgBox(self.log, selector.split("=")[-1].split("]")[0])

    first = property(lambda self: self)
    inner_text = lambda self: ""
    evaluate = lambda self, script: []
    select_option = lambda self, label: self.log.append((self.name, label))


def education_filled(monkeypatch, school: dict) -> list:
    log = []
    monkeypatch.setattr(ukg, "panel", lambda page, name: FakeUkgBox(log))
    monkeypatch.setattr(ukg, "open_entry", lambda p, probe: None)
    monkeypatch.setattr(ukg, "pick_typeahead", lambda page, box, typed, starts: typed)
    monkeypatch.setattr(ukg, "save_entry", lambda page, p: "ok")
    monkeypatch.setattr(ukg, "put_text", lambda box, value: log.append((box.name, value)) or "ok")
    assert ukg.add_education(None, [school]) == ["Acme State University: ok"]
    return log


def test_ukg_education_leaves_a_hidden_graduation_year_blank(monkeypatch):
    school = {"institution": "Acme State University", "degree": "BA", "end": "1998-05"}
    assert ("to-year-textbox", "1998") in education_filled(monkeypatch, dict(school))
    filled = education_filled(monkeypatch, dict(school, hide_year=True))
    assert not [f for f in filled if f[0].startswith("to-")]  # neither month nor year


# --- old jobs left off the tailored page: same on the form unless the user or the form says all ---

def jobs(form_jobs=None) -> dict:
    roles = [{"id": i, "title": "Clerk", "company": i.title(), "start": "2000-01", "end": "2001-01", "bullets": []}
             for i in ("acme", "globex", "initech", "hooli")]
    return {"contact": {"name": "Jane Doe"} | ({"form_jobs": form_jobs} if form_jobs else {}), "roles": roles}


PAGE = {"entries": [{"id": "acme"}, {"id": "globex"}, {"id": "project-x"}]}  # oldest two left off


def ids(roles):
    return [r["id"] for r in roles]


def test_form_jobs_same_as_page_all_or_asked_never_guessed():
    roles, note = questions.form_roles(jobs(), PAGE)
    assert roles == [] and note.startswith("ASK") and "same 2 jobs as your resume, or all 4 jobs" in note
    assert "15+ years ago" in note and "contact.form_jobs" in note
    assert (ids(questions.form_roles(jobs("page"), PAGE)[0]), questions.form_roles(jobs("page"), PAGE)[1]) == (
        ["acme", "globex"], None)
    assert questions.form_roles(jobs("all"), PAGE) == (jobs()["roles"], None)
    # nothing left off the page, or no tailored page: every job, nothing to ask
    assert questions.form_roles(jobs(), {"entries": [{"id": i} for i in ids(jobs()["roles"])]}) == (jobs()["roles"], None)
    assert questions.form_roles(jobs(), None) == (jobs()["roles"], None)


def test_form_asking_for_complete_history_gets_every_job_whatever_they_chose():
    for choice in (None, "page"):
        roles, note = questions.form_roles(jobs(choice), PAGE, complete=True)
        assert ids(roles) == ["acme", "globex", "initech", "hooli"] and "complete work history" in note
        assert not note.startswith("ASK")


@pytest.mark.parametrize("text, complete", [
    ("Please list your complete employment history.", True),
    ("Enter your full work history, starting with the most recent.", True),
    ("Give a complete history of your employment", True),
    ("List all previous employers for the last 10 years", True),
    ("Include every employer since high school", True),
    ("Work Experience\nAdd your most recent jobs", False),
    ("Acme is an equal opportunity employer. All employment decisions are made without regard to race.", False),
    ("View all jobs | Search all positions", False),
])
def test_complete_history_read_off_the_form(text, complete):
    assert questions.asks_complete_history(text) is complete


class FakePage:
    def __init__(self, text=""):
        self.text = text

    def locator(self, selector):
        return type("Body", (), {"inner_text": lambda _: self.text})()


def ukg_profile(monkeypatch, master, tailored, text="") -> tuple[str, list]:
    added = []
    monkeypatch.setattr(ukg, "resume_facts", lambda resume_file: (master, tailored))
    monkeypatch.setattr(ukg, "add_work", lambda page, roles, t: added.extend(ids(roles)) or [f"{r['id']}: ok" for r in roles])
    monkeypatch.setattr(ukg, "add_education", lambda page, schools: [])
    monkeypatch.setattr(ukg, "add_skills", lambda page, items: ["skills: ok"])
    monkeypatch.setattr(ukg, "add_links", lambda page, links: ["links: ok"])
    return ukg.put_profile(FakePage(text), "resume.pdf"), added


def test_ukg_work_history_takes_the_same_jobs_as_the_page(monkeypatch):
    result, added = ukg_profile(monkeypatch, jobs(), PAGE)
    assert added == [] and result.startswith("ASK") and "same 2 jobs" in result
    assert ukg_profile(monkeypatch, jobs("page"), PAGE)[1] == ["acme", "globex"]
    result, added = ukg_profile(monkeypatch, jobs("page"), PAGE, "Work Experience - list your complete work history")
    assert added == ["acme", "globex", "initech", "hooli"] and result.startswith("ok") and "complete work history" in result


def test_resume_found_after_the_page_name_changed(tmp_path, monkeypatch):
    """Tailored as Jane_Doe_Resume.pdf, page name since changed to initials: the folder's one
    resume PDF is the one; two of them -> none, never a guess."""
    from apply import form
    monkeypatch.setattr(form.cfg, "resume_path", lambda config, key: tmp_path / "details.yml")
    monkeypatch.setattr(form.schema, "load", lambda path: {"contact": {"name": "J. Doe"}})
    folder = tmp_path / "Job 3 - Acme - Clerk"
    folder.mkdir()
    (folder / "Jane_Doe_Resume.pdf").write_bytes(b"%PDF-1.7")
    assert form.resume_for({}, folder) == str(folder / "Jane_Doe_Resume.pdf")
    (folder / "Other_Resume.pdf").write_bytes(b"%PDF-1.7")
    assert form.resume_for({}, folder) is None
    (folder / "J_Doe_Resume.pdf").write_bytes(b"%PDF-1.7")
    assert form.resume_for({}, folder) == str(folder / "J_Doe_Resume.pdf")


def test_resume_goes_in_the_resume_box_only():
    """A cover letter upload box marked yes still never gets the resume."""
    from apply.systems import ashby

    class Box:
        first = property(lambda self: self)
        count = lambda self: 1
        scroll_into_view_if_needed = lambda self: None

    class Page:
        locator = lambda self, selector: Box()
    letter = {"id": "f1", "title": "Cover Letter", "kind": "file", "answer": True,
              "key": questions.key_from_title("Cover Letter", "file")}
    assert letter["key"] == "cover_letter"
    assert [questions.key_from_title(t, "file") for t in ("Resume/CV", "Upload your CV", "Portfolio")] == \
        ["resume", "resume", None]
    assert ashby.fill(Page(), letter, None).startswith("ASK cover letter box - no letter made")
    other = {**letter, "title": "Portfolio", "key": None}
    assert ashby.fill(Page(), other, "/tmp/Jane_Doe_Resume.pdf").startswith("ASK not the resume box")


# --- a file that leaves when chosen ---

def test_file_on_choice_systems_say_so_in_prepare_and_the_privacy_table():
    """Greenhouse's resume POSTs to its storage on choosing it (3 of 3 employers, 2026-10-05): prepare
    tells the AI to say so in the upload yes, and AGENTS.md's row says "as soon as" - only for
    systems measured so, never "once you click Submit" for a file that leaves sooner."""
    import re

    import cfg
    asked = [q("Resume/CV", "file", "resume"), q("First Name")]
    assert "as soon as it is chosen" in form.upload_note(greenhouse, asked)
    assert form.upload_note(greenhouse, asked[1:]) == "" and form.upload_note(ukg, asked) == ""
    assert "Ashby: a file goes to the employer's site as soon as it is chosen" in form.upload_note(ashby, asked)
    table = (cfg.ROOT / "AGENTS.md").read_text(encoding="utf-8").splitlines()
    for system in systems.SYSTEMS:
        rows = [r for r in table if f"that employer's {system.NAME} site" in r]
        early = any(re.search(r"\b(?:choose|chosen|pick)", r.split("|")[3]) for r in rows)
        assert early == getattr(system, "FILE_ON_CHOICE", False), system.NAME


# --- Greenhouse ---

def test_greenhouse_link_plain_eu_embed_or_tracking_tail():
    base = "https://job-boards.greenhouse.io/acme/jobs/1234567"
    for url in (base, base + "?utm_source=freehire.me", "https://boards.greenhouse.io/acme/jobs/1234567",
                "https://boards.greenhouse.io/embed/job_app?for=acme&token=1234567",
                "https://job-boards.greenhouse.io/embed/job_app?token=1234567&for=acme"):
        assert greenhouse.matches(url) and greenhouse.application_url(url) == base
    assert greenhouse.application_url("https://job-boards.eu.greenhouse.io/acme/jobs/7") == "https://job-boards.eu.greenhouse.io/acme/jobs/7"


# employer's own careers page w/ the form embedded (?gh_jid=) - "not supported" for 1 in 5 Greenhouse links (2026-10)
def test_greenhouse_employer_site_link_finds_its_board(monkeypatch):
    class Reply:
        def __init__(self, to): self.is_redirect, self.headers = bool(to), {"location": to}
    asked = []
    def get(url, **kw):
        asked.append(url)
        return Reply("https://job-boards.greenhouse.io/embed/job_app?for=acme&token=7654321" if "7654321" in url else "")
    monkeypatch.setattr(greenhouse.httpx, "get", get)
    greenhouse.board_for.cache_clear()
    for url in ("https://www.example.com/careers?gh_jid=7654321",
                "https://careers.example.com/jobs/7654321?gh_jid=7654321&utm_source=freehire.me",
                "https://example.com/careers/?utm_source=x&gh_jid=7654321"):
        assert systems.for_url(url) is greenhouse
        assert greenhouse.application_url(url) == "https://job-boards.greenhouse.io/acme/jobs/7654321"
    assert asked == ["https://boards.greenhouse.io/embed/job_app?token=7654321"]  # listing id only, once
    assert not greenhouse.matches("https://www.example.com/careers?jid=7654321")
    with pytest.raises(ValueError, match="may have closed"):
        greenhouse.parse_url("https://www.example.com/careers?gh_jid=1")


# job board answer, anonymised from a live posting (2026-10-02)
GH_JOB = {
    "questions": [
        {"label": "First Name", "required": True, "fields": [{"name": "first_name", "type": "input_text", "values": []}]},
        {"label": "Email", "required": True, "fields": [{"name": "email", "type": "input_text", "values": []}]},
        {"label": "Phone", "required": True, "fields": [{"name": "phone", "type": "input_text", "values": []}]},
        {"label": "Resume/CV", "required": True, "fields": [{"name": "resume", "type": "input_file", "values": []},
                                                              {"name": "resume_text", "type": "textarea", "values": []}]},
        {"label": "LinkedIn Profile", "required": True, "fields": [{"name": "question_1", "type": "input_text", "values": []}]},
        {"label": "Are you legally authorized to work in the United States for Acme?", "required": True,
         "fields": [{"name": "question_2", "type": "multi_value_single_select", "values": [{"label": "Yes", "value": 1}, {"label": "No", "value": 0}]}]},
        {"label": "Do you now, or will you in the future, require sponsorship?", "required": True,
         "fields": [{"name": "question_3", "type": "multi_value_single_select",
                     "values": [{"label": "No, I do not require sponsorship.", "value": 1}, {"label": "Yes, I require sponsorship.", "value": 2}]}]}],
    "location_questions": [{"label": "Latitude", "required": True, "fields": [{"name": "latitude", "type": "input_hidden", "values": []}]},
                           {"label": "Location", "required": True, "fields": [{"name": "location", "type": "input_text", "values": []}]}],
    "demographic_questions": {"questions": [
        {"id": 401, "label": "How would you describe your gender identity? (mark all that apply)", "required": False,
         "type": "multi_value_multi_select", "answer_options": [{"id": 1, "label": "Man", "free_form": False},
                                                                {"id": 2, "label": "I prefer to self-describe", "free_form": True}]}]},
    "compliance": [{"type": "eeoc", "questions": [
        {"label": "VeteranStatus", "required": False, "fields": [{"name": "veteran_status", "type": "multi_value_single_select",
                                                                   "values": [{"label": "I am not a protected veteran", "value": "1"}]}]},
        {"label": "Race", "required": False, "fields": [{"name": "race", "type": "multi_value_single_select",
                                                          "values": [{"label": "Hispanic or Latino", "value": "4"}]}]}]}]}


def test_greenhouse_board_that_redirects_to_employer_site_opens_embedded_form():
    class Page:
        def __init__(self, url): self.url, self.went = url, None
        def goto(self, url): self.went = url
        def wait_for_load_state(self, state=None): pass
    link = "https://job-boards.greenhouse.io/acme/jobs/1234567"
    away = Page("https://careers.example.com/jobs?gh_jid=1234567")
    greenhouse.recover(away, link)
    assert away.went == ("https://job-boards.greenhouse.io/embed/job_app?for=acme&token=1234567"
                         "&b=https%3A%2F%2Fcareers.example.com")
    home = Page(link)
    greenhouse.recover(home, link)
    assert home.went is None


def test_greenhouse_form_becomes_shared_questions():
    got = {x["id"]: x for x in greenhouse.from_board(GH_JOB)}
    assert (got["first_name"]["key"], got["email"]["kind"], got["phone"]["kind"]) == ("first_name", "email", "phone")
    assert (got["resume"]["kind"], got["resume"]["key"]) == ("file", "resume") and "resume_text" not in got
    assert got["question_1"]["key"] == "linkedin"
    assert got["question_2"]["kind"] == "yesno"  # a Yes / No list
    assert got["question_3"]["kind"] == "choice" and got["question_3"]["options"][0].startswith("No, I do not")
    # boxes the page shows that the board lists elsewhere or not at all
    assert got[greenhouse.COUNTRY]["required"] and got[greenhouse.LOCATION]["kind"] == "location"
    assert "latitude" not in got
    assert got["401"]["kind"] == "multichoice" and got["401"]["options"] == ["Man"]  # self-describe is a free box
    assert got["veteran_status"]["title"] == "Veteran Status" and not got["veteran_status"]["required"]
    ids = list(got)
    assert ids.index("hispanic_ethnicity") == ids.index("race") - 1  # Hispanic/Latino first: it decides if Race shows


def test_greenhouse_board_without_a_survey():
    # "demographic_questions": null on a live posting (2026-10-03) crashed the read
    got = greenhouse.from_board(GH_JOB | {"demographic_questions": None, "compliance": None})
    assert "first_name" in {x["id"] for x in got} and "401" not in {x["id"] for x in got}


# the Education section as Greenhouse gives it (anonymised from live answers, 2026-10-05): the job board says only
# whether there is one; the form page carries which boxes show (+ the lists' host), the lists come 100 a page
GH_EMBED = ('<script>window.ENV = {"JBEN_URL":"https://boards.example"};</script><script>window.__remixContext = '
            '{"jobPost":{"education_config":{"id":7,"school_name":"optional","degree":"required","discipline":"optional",'
            '"start_month":"hidden","start_year":"required","end_month":"optional","end_year":"optional"},"x":1}};</script>')
GH_LISTS = {"degrees": ["Associate's Degree", "Bachelor's Degree", "Doctor of Philosophy (Ph.D.)", "High School",
                        "Juris Doctor (J.D.)", "Master of Business Administration (M.B.A.)", "Master's Degree", "Other"],
            "disciplines": ["Business Administration", "Computer Science", "Economics", "Other", "Discipline Unknown"]}


def gh_get(asked, embed=GH_EMBED, education="education_optional", per_page=100):
    class Reply:
        def __init__(self, data=None, text=""):
            self.data, self.text, self.status_code = data, text, 200

        def json(self):
            return self.data

        def raise_for_status(self):
            pass

    def get(url, params=None, **kw):
        asked.append((url, params))
        if "/jobs/" in url:
            return Reply({"questions": GH_JOB["questions"][:1], "education": education})
        if "/embed/job_app" in url:
            if embed is None:
                raise greenhouse.httpx.ConnectError("down")
            return Reply(text=embed)
        kind = url.rsplit("/", 1)[1]
        page = GH_LISTS[kind][(params["page"] - 1) * per_page:params["page"] * per_page]
        return Reply({"items": [{"id": i, "text": t} for i, t in enumerate(page)],
                      "meta": {"total_count": len(GH_LISTS[kind]), "per_page": per_page}})
    return get


def test_greenhouse_education_boxes_per_school_as_the_form_page_sets_them(monkeypatch):
    """The job board says only "education_optional"; which boxes show and which are required come with the
    form page (6 of 6 boards differed, plan-29g.26): one set per school on the resume, start dates only when
    required (the resume has none), the degree + discipline lists from the host the page names. Only the
    board + job ids go out."""
    asked = []
    monkeypatch.setattr(greenhouse.httpx, "get", gh_get(asked, per_page=3))
    got = greenhouse.questions("https://job-boards.greenhouse.io/acme/jobs/4001234005", 2)
    edu = [x for x in got if x["native"] == "education"]
    assert [x["id"] for x in edu] == [f"{b}--{i}" for i in (0, 1)
                                      for b in ("school", "degree", "discipline", "start-year", "end-month", "end-year")]
    by = {x["id"]: x for x in edu}
    assert by["degree--1"]["required"] and by["start-year--0"]["required"] and not by["school--0"]["required"]
    assert by["degree--0"]["options"] == GH_LISTS["degrees"]  # 3 a page here: every page read
    assert by["end-month--0"]["options"][0] == "January" and by["end-year--1"]["kind"] == "number"
    assert (by["school--1"]["title"], by["school--1"]["entry"], by["school--1"]["options"]) == ("Education 2: School", 1, [])
    assert ("https://job-boards.greenhouse.io/embed/job_app", {"for": "acme", "token": "4001234005"}) in asked
    assert all(u.startswith("https://boards.example/v1/boards/acme/education/") for u, _ in asked
               if "/education/" in u)
    # no Education section on the form: nothing more fetched; one school by default
    asked.clear()
    monkeypatch.setattr(greenhouse.httpx, "get", gh_get(asked, education=None))
    assert all(x["native"] != "education" for x in greenhouse.questions("https://job-boards.greenhouse.io/acme/jobs/1"))
    assert len(asked) == 1
    # form page unreadable: the boxes every board seen shows, required as the job board says
    monkeypatch.setattr(greenhouse.httpx, "get", gh_get([], embed=None, education="education_required"))
    got = {x["id"]: x["required"] for x in greenhouse.questions("https://job-boards.greenhouse.io/acme/jobs/1")
           if x["native"] == "education"}
    assert got == {"school--0": True, "degree--0": True, "discipline--0": False}


def test_education_answers_from_resume_details_in_the_forms_words():
    """Each school's boxes from Resume details: degree as the list words it (BA -> Bachelor's Degree, named to
    the user), discipline exact or the longest option it starts with, the graduation date only as the page
    shows it - hidden by the user's choice -> blank, or asked as sensitive when required. Not on the resume ->
    blank, asked when required."""
    edu = lambda key, entry=0, required=False, options=(): questions.question(
        f"{key}--{entry}", f"Education {entry + 1}: {key}", "number" if key.endswith("year") else "choice",
        required, options or (GH_LISTS["degrees"] if key == "degree" else GH_LISTS["disciplines"]
                              if key == "discipline" else questions.MONTHS if key.endswith("month") else []),
        key, "education", entry=entry)
    schools = [{"institution": "University of California, Berkeley", "degree": "BA", "field": "Economics in Asia",
                "end": "2016-05"},
               {"institution": "Acme Institute", "degree": "PhD", "field": "Astrophysics", "end": "2004", "hide_year": True},
               {"institution": "Acme Law School", "degree": "J.D.", "end": "2021"}]
    asked = [edu(k, i) for i in range(3) for k in ("school", "degree", "discipline", "school_end_month", "school_end_year")]
    asked += [edu("school_end_year", 1, required=True) | {"id": "x"}, edu("school_start_year", 0, required=True),
              edu("school", 3, required=True), edu("degree", 3)]
    got = [(a["answer"], a["source"]) for a in questions.draft(asked, CONTACT, schools=schools)]
    named = "as the form's nearest option - name it to the user"
    assert got[:5] == [("University of California, Berkeley", "resume"),
                       ("Bachelor's Degree", f"resume - 'BA' {named}"), ("Economics", f"resume - 'Economics in Asia' {named}"),
                       ("May", "resume"), ("2016", "resume")]
    assert got[5:10] == [("Acme Institute", "resume"), ("Doctor of Philosophy (Ph.D.)", f"resume - 'PhD' {named}"),
                         (None, f"{questions.ASK} - 'Astrophysics' isn't on the form's list: the nearest option is theirs to pick"),
                         (None, "left off your resume (your choice) - left blank"),
                         (None, "left off your resume (your choice) - left blank")]
    assert got[10:15] == [("Acme Law School", "resume"), ("Juris Doctor (J.D.)", f"resume - 'J.D.' {named}"),
                          (None, "not on your resume - left blank"), (None, "not on your resume - left blank"),
                          ("2021", "resume")]
    assert got[15:] == [(None, f"{questions.ASK} - sensitive: graduation date"), (None, f"{questions.ASK} - not on your resume"),
                        (None, f"{questions.ASK} - not on your resume"), (None, "not on your resume - left blank")]
    degrees = GH_LISTS["degrees"]
    assert [questions.degree_option(d, degrees) for d in ("MBA", "AA", "MS", "Bachelor's degree", "High School Diploma",
                                                           "EdD", "Master of Science in Nursing")] == \
        ["Master of Business Administration (M.B.A.)", "Associate's Degree", "Master's Degree", "Bachelor's Degree",
         "High School", None, "Master's Degree"]
    assert questions.major_option("Discipline", GH_LISTS["disciplines"]) is None  # never a catch-all by a shared word


def test_greenhouse_says_school_boxes_search_its_list_as_typed():
    """School, degree, discipline search Greenhouse's own list with each keystroke (measured, plan-29g.26): those
    words reach its site before Submit - prepare tells the AI, AGENTS.md's privacy table has the row."""
    import cfg
    asked = [q("Education 1: School", "choice", "school"), q("Education 1: Degree", "choice", "degree"), q("First Name")]
    assert "school, degree boxes search Greenhouse's own list as they're typed" in form.typed_note(greenhouse, asked)
    assert form.typed_note(greenhouse, asked[2:]) == "" and form.typed_note(ashby, asked[2:]) == ""
    # Ashby's school box searches its school list as typed too (plan-nko.24); its degree is a plain box
    assert "Ashby: the school boxes search Ashby's own list as they're typed" in form.typed_note(ashby, asked)
    where = questions.question("q9", "Where are you based?", "location", True)  # an employer's own Location box: no key
    assert where["key"] is None and "location boxes search Ashby's own list" in form.typed_note(ashby, [where])
    table = (cfg.ROOT / "AGENTS.md").read_text(encoding="utf-8").splitlines()
    for system in systems.SYSTEMS:
        typed = any("typed" in r.split("|")[3] for r in table if f"that employer's {system.NAME} site" in r)
        assert typed == bool(getattr(system, "SEARCHED_AS_TYPED", ())), system.NAME


class GhPage:
    """The page's own name fill lands a moment after a box's first focus."""
    def __init__(self):
        self.pending = None

    def wait_for_timeout(self, ms):
        if self.pending:
            field, self.pending = self.pending, None
            field.value = field.autofill


class GhField:
    def __init__(self, page, autofill=""):
        self.page, self.value, self.autofill, self.focused = page, "", autofill, False

    def focus(self):
        if not self.focused and self.autofill:
            self.page.pending = self
        self.focused = True

    def fill(self, v):
        late = self.page.pending is self  # typed before the page's fill landed: they run together
        self.page.pending = None
        self.value = (self.autofill if late else "") + v

    def blur(self):
        pass

    def input_value(self):
        return self.value


def test_greenhouse_text_waits_out_the_pages_own_name_fill():
    field = GhField(GhPage(), autofill="Jane")
    assert greenhouse.put_text(field, "Ada", "text") == "ok" and field.input_value() == "Ada"
    assert greenhouse.put_text(GhField(GhPage()), "(555) 010-0100", "phone") == "ok"


def test_ashby_closed_reads_the_employers_board_once_never_guesses(monkeypatch):
    """jobPosting null = closed or a wrong link (ashby.md "Closed posting"): the public board tells which."""
    import httpx
    url = "https://jobs.ashbyhq.com/acme/45bdb7e5-14a8-494f-8fcb-30e42f0be67a"
    boards = []

    def board(where, timeout):
        boards.append(where)
        return httpx.Response(state["board"], json={"jobs": [{"id": state["listed"]}]},
                              request=httpx.Request("GET", where))
    state = {"posting": None, "board": 200, "listed": "11111111-2222-3333-4444-555555555555"}
    monkeypatch.setattr(ashby, "job_posting", lambda org, posting: state["posting"])
    monkeypatch.setattr(ashby.httpx, "get", board)
    assert ashby.closed(url).endswith("no longer on the employer's Ashby board - it may have closed")
    assert boards == ["https://api.ashbyhq.com/posting-api/job-board/acme"]
    state["board"] = 404
    assert ashby.closed(url).startswith("can't tell") and "board moved?" in ashby.closed(url)
    state.update(board=200, listed="45bdb7e5-14a8-494f-8fcb-30e42f0be67a")
    assert ashby.closed(url).startswith("can't tell")
    with pytest.raises(ValueError, match="can't tell"):
        ashby.questions(url)
    state["posting"] = {"title": "Engineer"}
    boards.clear()
    assert ashby.closed(url) is None and boards == []
    state["posting"] = None
    ashby.closed("https://jobs.ashbyhq.com/acme%20corp/45bdb7e5-14a8-494f-8fcb-30e42f0be67a")
    assert boards == ["https://api.ashbyhq.com/posting-api/job-board/acme%20corp"]


def test_ashby_voluntary_survey_listed_beside_the_form():
    """Gender, race, veteran come as surveyForms - left out, they sat blank on the page (2026-10)."""
    field = lambda path, title, values: {"isRequired": False, "field": {
        "path": path, "title": title, "type": "ValueSelect", "selectableValues": [{"label": v} for v in values]}}
    job = {"applicationForm": {"sections": [{"fieldEntries": [field("q", "Years?", ["1", "2"])]}]},
           "surveyForms": [{"sections": [{"fieldEntries": [
               field("_systemfield_eeoc_gender", "Gender", ["Male", "Female", "Decline to self-identify"])]}]}]}
    assert [q["id"] for q in ashby.from_form(job)] == ["q", "_systemfield_eeoc_gender"]


def test_ashby_untitled_consent_left_for_the_applicant():
    """Measured 2026-10-05 (tenant D): an "I agree" tick, title "", its consent words in the entry's
    description - the try run ticked it. Read as its title; a box with no words at all is theirs too."""
    job = json.loads((Path(__file__).parent / "fixtures" / "ashby" / "consent-untitled.json").read_text())
    got = {q["id"]: q for q in ashby.from_form(job)}
    assert got["_systemfield_name"]["title"] == "Name"  # a titled box keeps its title, not its hint
    consent, blank = got["_systemfield_data_consent_ack"], got["untitled"]
    assert consent["title"].startswith("I consent to my data being retained beyond one year")
    assert blank["title"] == "" and all(questions.signs(q["title"]) for q in (consent, blank))
    drafted = {a["id"]: a for a in questions.draft(list(got.values()), CONTACT)}  # prepare
    for id, why in (("_systemfield_data_consent_ack", questions.SIGNING), ("untitled", questions.UNTITLED)):
        assert drafted[id]["answer"] is None
        assert drafted[id]["source"] == f"{questions.ASK} - {questions.SIGN_ON_PAGE}: {why}"
    assert drafted["_systemfield_name"]["answer"] == CONTACT["name"]
    assert questions.missing(list(drafted.values())) == []  # required, but theirs on the page: not asked for
    for id in ("_systemfield_data_consent_ack", "untitled"):  # fill: an answer there is refused, never ticked
        with pytest.raises(SystemExit, match="ticks or signs"):
            form.refuse([{**drafted[id], "answer": ["I agree"], "source": questions.USER_SAID}])


VETERAN = ["I identify as one or more of the classifications of protected veteran listed above",
           "I am not a protected veteran", "I decline to self-identify for protected veteran status"]
RACE = ["Hispanic or Latino", "White (Not Hispanic or Latino)", "Decline to self-identify"]


def test_saved_voluntary_answers_fill_only_after_the_users_yes():
    selfid = {"gender": "Male", "hispanic_latino": True, "protected_veteran": False}
    asked = [questions.question("g", "Gender", "choice", False, ["Male", "Female", "Decline to self-identify"]),
             questions.question("r", "Race", "choice", False, RACE),
             questions.question("v", "Veteran Status", "choice", False, VETERAN)]
    for consent in (None, False):  # not asked yet, or said no: asked on the form as before
        got = questions.draft(asked, {}, config={"self_identification": {**selfid, "fill_on_forms": consent}})
        assert all(a["answer"] is None and questions.YOURS in a["source"] for a in got)
    got = questions.draft(asked, {}, config={"self_identification": {**selfid, "fill_on_forms": True}})
    assert [a["answer"] for a in got] == ["Male", "Hispanic or Latino", "I am not a protected veteran"]
    assert all(questions.VOLUNTARY_SAVED in a["source"] for a in got) and not questions.unvouched(got)
    # nothing saved for race beyond "not Hispanic": asked, never guessed
    got = questions.draft(asked[1:2], {}, config={"self_identification": {"hispanic_latino": False, "fill_on_forms": True}})
    assert got[0]["answer"] is None


def test_saved_voluntary_answers_match_other_wordings():
    config = {"self_identification": {"gender": "Male", "hispanic_latino": True, "fill_on_forms": True}}
    asked = [questions.question("g", "Gender Identity", "choice", False, ["Man", "Woman", "Non-Binary"]),
             questions.question("r", "Race/Ethnicity (Select all that apply)", "multichoice", False,
                                ["Asian", "Hispanic, Latinx, or Spanish Origin", "White"])]
    got = questions.draft(asked, {}, config=config)
    assert [a["answer"] for a in got] == ["Man", ["Hispanic, Latinx, or Spanish Origin"]]


# Greenhouse's own demographic survey (tenant G's 3 tag lists + Yes/No lists, one more board 2026-10-05:
# "I prefer to self-describe" is a free box, left out by from_board)
SURVEY_DISABILITY = ("Do you have a disability or chronic condition (physical, visual, auditory, cognitive, mental, "
                     "emotional, other) that substantially limits one or more of your major life activities, including "
                     "mobility, communication (seeing, hearing, speaking), & learning")
SURVEY = [questions.question("o", "How would you describe your sexual orientation? (mark all that apply)", "multichoice",
                             False, ["Asexual", "Bisexual and/or pansexual", "Gay", "Heterosexual", "Lesbian", "Queer",
                                     "I don't wish to answer"]),
          questions.question("t", "Do you identify as transgender?", "choice", False, ["Yes", "No", "I don't wish to answer"]),
          questions.question("d", SURVEY_DISABILITY, "choice", False, ["Yes", "No", "I don't wish to answer"]),
          questions.question("a", "Are you a veteran or active member of the United States Armed Forces?", "choice", False,
                             ["Yes, I am a veteran or active member", "No, I am not a veteran or active member",
                              "I don't wish to answer"]),
          questions.question("v", "Veteran Status", "choice", False, VETERAN)]
SELF_ID = {"gender": "Male", "hispanic_latino": True, "protected_veteran": False, "disability": False,
           "sexual_orientation": "Queer", "transgender": False, "armed_forces": False}


def test_saved_orientation_transgender_disability_armed_forces_fill_the_survey():
    got = questions.draft(SURVEY, {}, config={"self_identification": {**SELF_ID, "fill_on_forms": True}})
    assert [a["answer"] for a in got] == [["Queer"], "No", "No", "No, I am not a veteran or active member",
                                          "I am not a protected veteran"]
    assert all(questions.VOLUNTARY_SAVED in a["source"] for a in got) and not questions.unvouched(got)
    # disability stays a sensitive kind: named as one, its wording read back before Submit
    assert "sensitive: disability or health" in got[2]["source"] and questions.READ_FIRST in got[2]["source"]
    assert "disability or health" in form.line(got[2])
    for consent in (None, False):  # asked on the form as before, disability as a sensitive question
        got = questions.draft(SURVEY, {}, config={"self_identification": {**SELF_ID, "fill_on_forms": consent}})
        assert all(a["answer"] is None and a["source"].startswith(questions.ASK) for a in got)
    assert questions.asks_voluntary([SURVEY[2]])  # a form asking only about disability still gets the ask-once


def test_saved_armed_forces_and_protected_veteran_kept_apart():
    """Both titles say "veteran": a protected veteran is one kind of veteran, never answered from the other."""
    only_armed = {"armed_forces": False, "fill_on_forms": True}
    got = questions.draft(SURVEY[3:], {}, config={"self_identification": only_armed})
    assert [a["answer"] for a in got] == ["No, I am not a veteran or active member", None]
    only_eeoc = {"protected_veteran": False, "fill_on_forms": True}
    got = questions.draft(SURVEY[3:], {}, config={"self_identification": only_eeoc})
    assert [a["answer"] for a in got] == [None, "I am not a protected veteran"]
    yes = questions.draft(SURVEY[3:4], {}, config={"self_identification": {"armed_forces": True, "fill_on_forms": True}})
    assert yes[0]["answer"] == "Yes, I am a veteran or active member"
    # the EEOC list decides, whatever armed-forces words its text carries
    long = questions.question("v", "Protected veteran status (disabled veteran, recently separated veteran, active duty "
                                   "wartime or campaign badge veteran, Armed Forces service medal veteran)", "choice",
                              False, VETERAN)
    assert questions.voluntary_kind(long) == "protected_veteran"
    assert questions.voluntary_answer(long, {"self_identification": {**only_eeoc, "armed_forces": True}}) == \
        "I am not a protected veteran"


def test_saved_voluntary_answers_match_other_survey_wordings():
    """Option lists seen on four more Greenhouse boards (2026-10-05)."""
    config = {"self_identification": {**SELF_ID, "fill_on_forms": True}}
    q = questions.question
    asked = [
        q("o", "What sexual orientation do you most closely identify with? ", "choice", False,
          ["Asexual", "Bisexual", "Gay", "Heterosexual", "Lesbian", "Pansexual", "Queer", "Not listed",
           "I don't wish to answer"]),
        q("t", "Are you a person of transgender experience? ", "choice", False, ["Yes", "No", "I don't wish to answer"]),
        q("d1", "Do you live with a disability (as outlined by the ADA)?", "choice", False,
          ["Yes, I have a disability, or have a history/record of having a disability",
           "No, I do not have a disability, or have a history/record of having a disability", "I don't wish to answer"]),
        q("d2", "What is your disability status?", "choice", False,
          ["Yes, I have a disability", "No, I don't have a disability", "I don't wish to answer"]),
        q("d3", "Disability Status", "choice", False,
          ["I do not want to answer", "No, I do not have a disability and have not had one in the past",
           "Yes, I have a disability, or have had one in the past"]),
        q("a1", "What is your military status?", "choice", False,
          ["I am on active duty", "I am part of the national guard or on reserve", "I have never served in the military",
           "I identify as a protected veteran", "I identify as a non-protected veteran",
           "I identify in multiple military status categories", "I don't wish to answer"]),
        q("a2", "Are you a veteran/have you served in the military? ", "choice", False,
          ["Active Reserve", "Inactive Reserve", "Other Protected Veteran", "Retired", "Unspecified Veteran",
           "Vietnam Era Veteran", "Vietnam Veteran and Other Protected Veteran", "No military service",
           "I don't wish to answer"]),
        q("a3", "Are you a veteran or active member of the United States Armed Forces?", "choice", False,
          ["I am a veteran or active member", "No, I am not a veteran or active member", "I don't wish to answer"])]
    got = questions.draft(asked, {}, config=config)
    assert [a["answer"] for a in got] == [
        "Queer", "No", "No, I do not have a disability, or have a history/record of having a disability",
        "No, I don't have a disability", "No, I do not have a disability and have not had one in the past",
        "I have never served in the military", "No military service", "No, I am not a veteran or active member"]
    straight = {"self_identification": {"sexual_orientation": "Straight", "fill_on_forms": True}}
    assert questions.voluntary_answer(q("o", "Sexual Orientation", "choice", False, ["Gay", "Straight/Heterosexual"]),
                                      straight) == "Straight/Heterosexual"
    assert questions.voluntary_answer(q("o", "Sexual Orientation", "choice", False, ["Gay", "Heterosexual"]),
                                      straight) == "Heterosexual"


def test_saved_voluntary_answers_never_stretched_to_another_question():
    config = {"self_identification": {**SELF_ID, "fill_on_forms": True}}
    q = questions.question
    asked = [q("r", "Will you require a reasonable accommodation due to a disability during the interview?", "yesno",
               False, ["Yes", "No"]),
             q("l", "Do you identify as part of the LGBTQ+ community?", "choice", False,
               ["Yes", "No", "Questioning", "I don't wish to answer"]),
             q("b", "Veteran and disability status", "choice", False, ["Yes", "No"])]  # two kinds in one
    got = questions.draft(asked, {}, config=config)
    assert all(a["answer"] is None and a["source"].startswith(questions.ASK) for a in got)
    assert "sensitive: disability or health" in got[0]["source"]
    assert f"{questions.YOURS}: {questions.VOLUNTARY}" in got[1]["source"]  # never drafted, not even unsaved


def test_answer_dropped_after_filling_is_filled_again_then_flagged():
    class System:
        def __init__(self, sticks): self.sticks, self.fills = sticks, 0
        def holds(self, page, q): return self.fills >= self.sticks
        def fill(self, page, q, resume): self.fills += 1; return "ok"
    class Page:
        def wait_for_timeout(self, ms): pass
    qs = [{"id": "q1", "title": "Preferred First Name", "kind": "text", "answer": "Jane"}]
    assert form.recheck(Page(), System(1), qs, [("q1", "ok")], None) == [("q1", "ok")]
    assert form.recheck(Page(), System(9), qs, [("q1", "ok")], None)[0][1].startswith("FAIL answer dropped")
class FakeRadio:
    """Ashby radio: a label click toggles it (a second click clears it) and the page shows the
    change only after `lag` polls."""
    def __init__(self, checked=False, lag=0):
        self.state = self.shown = checked
        self.lag, self.polls, self.clicks = lag, 0, 0
        self.page = self

    def click(self):
        self.clicks += 1
        self.state, self.polls = not self.state, self.lag

    def is_checked(self):
        if self.polls:
            self.polls -= 1
        else:
            self.shown = self.state
        return self.shown

    def wait_for_timeout(self, ms):
        pass

    def get_attribute(self, name):
        return "radio-0"


class FakeList:
    def __init__(self, item):
        self.item = item
        self.first = item

    def count(self):
        return 1


class FakeChoiceBox:
    def __init__(self, radio):
        self.radio = radio

    def locator(self, selector, has_text=None):
        return FakeList(self.radio)


def test_ashby_choice_already_picked_is_not_clicked_again():
    radio = FakeRadio(checked=True)
    assert ashby.put_choice(FakeChoiceBox(radio), "Frontend only") == "ok"
    assert radio.clicks == 0 and radio.state


def test_ashby_choice_marked_a_moment_after_the_click_is_ok():
    radio = FakeRadio(lag=3)
    assert ashby.put_choice(FakeChoiceBox(radio), "8+") == "ok"
    assert radio.clicks == 1


def test_no_message_piece_prints_its_placeholder_raw():
    # a plain "..." piece inside an f-string message printed "{slug}" to the AI as is
    import ast
    tree = ast.parse(inspect.getsource(form))
    pieces = [s for call in ast.walk(tree) if isinstance(call, ast.Call)
              and getattr(call.func, "id", None) in ("print", "exit")
              for s in ast.walk(call) if isinstance(s, ast.Constant) and isinstance(s.value, str)]
    assert not [s.value for s in pieces if "{slug}" in s.value or "{'fill'" in s.value]


def test_website_box_gets_the_resumes_own_site_never_a_profile():
    q = {"key": "website", "kind": "text"}
    contact = {"links": ["linkedin.com/in/your-name", "github.com/your-name", "example.com"]}
    assert questions.from_resume(q, contact) == "https://www.example.com"
    assert questions.from_resume(q, {"links": ["https://portfolio.example.org/work"]}) == "https://portfolio.example.org/work"
    assert questions.from_resume(q, {"links": ["linkedin.com/in/your-name"]}) == ""


# --- fill twice = same state: recheck refills a dropped answer once, so a refill must never untick ---

FIXTURES = Path(__file__).parent / "fixtures" / "dom"


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
def fixture_page(chrome):
    """A page from fixtures/dom/ in real headless Chrome; every other request refused."""
    context = chrome.new_context()
    asked = []

    def serve(route):
        u = urlsplit(route.request.url)
        asked.append(route.request.url)
        file = FIXTURES / u.path.lstrip("/")
        if u.hostname != "acme.example" or not file.is_file():
            return route.fulfill(status=404, body="")
        return route.fulfill(path=str(file))

    context.route("**/*", serve)
    pg = context.new_page()

    def at(name):
        pg.goto(f"https://acme.example/{name}")
        pg.wait_for_load_state("load")
        return pg
    yield at
    assert all(urlsplit(u).hostname == "acme.example" for u in asked), asked
    context.close()


def shown(page) -> list:
    """Everything the form shows: each box's value or tick, pressed buttons, chosen dropdown values."""
    return page.eval_on_selector_all(
        "form input, form textarea, form select, form button, form [class*=single-value], form [class*=multi-value__label]",
        "es => es.map(e => e.matches('input[type=radio], input[type=checkbox]') ? e.checked"
        " : e.matches('button') ? e.getAttribute('aria-pressed') : 'value' in e ? e.value : e.innerText)")


def answered(id, kind, answer, options=(), title="Question"):
    return questions.question(id, title, kind, True, options) | {"answer": answer}


READ_BACK_FORMS = {
    "greenhouse": ("greenhouse-form.html", [
        answered("first_name", "text", "Ada"), answered("email", "email", "ada@example.com"),
        answered("question_5", "choice", "United States"),
        answered("question_100[]", "multichoice", ["Part Time", "Contract"])]),
    "ashby": ("ashby-form.html", [
        answered("_systemfield_name", "text", "Ada Lovelace"), answered("_systemfield_email", "email", "ada@example.com"),
        answered("q_phone", "phone", "555-0100"), answered("q_why", "longtext", "Their own words."),
        answered("q_sponsor", "yesno", "No"), answered("q_years", "choice", "8+"),
        answered("q_stack", "multichoice", ["Python", "SQL"]), answered("q_country", "choice", "United States")]),
    "lever": ("lever-form.html", [
        answered("name", "text", "Ada Lovelace"), answered("phone", "phone", "555-0100"),
        answered("cards[acme][field0]", "longtext", "Their own words."),
        answered("cards[acme][field1]", "yesno", "Yes"), answered("cards[acme][field2]", "choice", "3-5"),
        answered("cards[acme][field3]", "multichoice", ["Python", "Excel"])]),
    "jazzhr": ("jazzhr-form.html", [
        answered("resumator-firstname-value", "text", "Ada"), answered("resumator-email-value", "email", "ada@example.com"),
        answered("resumator-phone-value", "phone", "555-0100"),
        answered("resumator-questionnaire-q1474074", "yesno", "No", ["YES", "NO"]) | {"native": "jazzhr:select"},
        answered("resumator-citizen-value", "choice", "I am a U.S. Citizen/Permanent Resident") | {"native": "jazzhr:select"},
        answered("resumator-questionnaire-q1586173", "choice", "3-5") | {"native": "jazzhr:select"},
        answered("resumator-start-value", "date", "11/02/2026") | {"native": "jazzhr:date"},
        answered("resumator-questionnaire-q1474076", "yesno", "No", ["YES", "NO"]) | {"native": "jazzhr:checkboxes"}]),
    "workable": ("workable-form.html", [
        answered("firstname", "text", "Ada"), answered("email", "email", "ada@example.com"),
        answered("phone", "phone", "555-0100"), answered("address", "location", "Boston, MA"),
        answered("QA_1", "longtext", "Their own words."), answered("QA_2", "number", "90000"),
        answered("QA_3", "yesno", "Yes", ["Yes", "No"]),
        answered("QA_4", "choice", "No", ["Yes - please add details below", "No"]),
        answered("CA_9", "multichoice", ["Weekends", "Holiday"], ["Weekends", "Evenings", "Holiday"])
        | {"native": "CA:multiple:152176,152177,152178"},
        answered("CA_1", "choice", "Associate", ["High School/GED", "Associate", "Bachelor's"]),
        answered("CA_2", "yesno", "No", ["Yes", "No"])]),
    "bamboohr": ("bamboohr-form.html", [
        answered("firstName", "text", "Ada"), answered("email", "email", "ada@example.com"),
        answered("phone", "phone", "555-0100"), answered("streetAddress", "text", "1 Main St"),
        answered("state", "text", "New York"), answered("countryId", "choice", "United States"),
        answered("dateAvailable", "date", "11/02/2026", title="Date Available"),
        answered("educationLevelId", "choice", "Bachelor's Degree"),
        answered("customQuestionAnswers.short_1018", "text", "90000"),
        answered("customQuestionAnswers.long_761", "longtext", "Their own words."),
        answered("customQuestionAnswers.yes_no_1019", "yesno", "No", ["Yes", "No"]) | {"native": "bamboohr:yes_no"},
        answered("veteranStatusId", "choice", "Not a Veteran", bamboohr.VETERAN_OPTIONS)]),
}


@pytest.mark.parametrize("name", list(READ_BACK_FORMS))
def test_fill_twice_leaves_every_kind_as_the_first_fill_did(fixture_page, name):
    system = importlib.import_module(f"apply.systems.{name}")
    file, qs = READ_BACK_FORMS[name]
    page = fixture_page(file)
    assert [system.fill(page, q, None) for q in qs] == ["ok"] * len(qs)
    page.wait_for_timeout(300)  # the page marks a click a moment later
    once = shown(page)
    assert [system.fill(page, q, None) for q in qs] == ["ok"] * len(qs)
    page.wait_for_timeout(300)
    assert shown(page) == once
    if hasattr(system, "holds"):
        assert [q["id"] for q in qs if not system.holds(page, q)] == []


def test_ashby_long_list_choice_the_page_empties_reads_as_dropped(fixture_page):
    page = fixture_page("ashby-form.html")
    region = answered("q_region", "choice", "West")
    assert ashby.fill(page, region, None) == "ok"
    assert ashby.holds(page, region)
    page.wait_for_timeout(1200)  # the page empties the pick after 800 ms
    assert page.locator('[data-field-path="q_region"] input').input_value() == ""
    assert not ashby.holds(page, region)
    assert ashby.fill(page, answered("q_region", "choice", "South"), None) == "FAIL no option 'South'"


def test_ashby_holds_reads_what_shows_never_the_answer(fixture_page):
    """An option the box doesn't have, a box not on the page, a place with no pick: nothing shows = not held."""
    page = fixture_page("ashby-form.html")
    assert not ashby.holds(page, answered("q_years", "choice", "10+"))
    assert not ashby.holds(page, answered("q_gone", "text", "x"))
    assert not ashby.holds(page, answered("q_stack", "multichoice", ["Python"]))
    page.locator('[data-field-path="q_country"] input').fill("Austin, TX, United States")
    assert ashby.holds(page, answered("q_country", "location", "Austin, Texas"))
    assert not ashby.holds(page, answered("q_country", "location", "Boston, MA"))


def test_jazzhr_holds_reads_what_shows_never_the_answer(fixture_page):
    """Untouched dropdown = the no-answer option shows; no tick; a box not on the page: not held."""
    page = fixture_page("jazzhr-form.html")
    sel = lambda id, kind, a, opts=(): answered(id, kind, a, opts) | {"native": "jazzhr:select"}
    assert not jazzhr.holds(page, sel("resumator-over18-value", "yesno", "Yes", ["Yes", "No"]))
    assert not jazzhr.holds(page, sel("resumator-questionnaire-q1586173", "choice", "No answer"))
    ticks = answered("resumator-questionnaire-q1474076", "yesno", "Yes", ["YES", "NO"]) | {"native": "jazzhr:checkboxes"}
    assert not jazzhr.holds(page, ticks)
    assert jazzhr.fill(page, ticks, None) == "ok" and jazzhr.holds(page, ticks)
    page.locator("#resumator-checkbox-1474076-2").check()  # both ticked shows no single answer
    assert not jazzhr.holds(page, ticks)
    assert not jazzhr.holds(page, answered("resumator-gone-value", "text", "x"))
    page.locator("#resumator-phone-value").fill("(555) 010-0999")
    assert not jazzhr.holds(page, answered("resumator-phone-value", "phone", "555-010-0100"))


def test_jazzhr_upload_opens_attach_reads_the_name_and_the_pages_limit(fixture_page, tmp_path):
    """"Attach resume" shows the file box; ok = the box holds the file within the page's own "limit 5MB";
    an error JazzHR's script wrote by the resume box is passed on in its words."""
    page = fixture_page("jazzhr-form.html")
    resume = answered("resumator-resume-value", "file", True, title="Resume") | {"key": "resume"}
    good, big = tmp_path / "Ada_Lovelace_Resume.pdf", tmp_path / "Big_Resume.pdf"
    good.write_bytes(b"%PDF-1.4 test")
    big.write_bytes(b"%PDF-1.4 " + b"0" * (5 * 1024 * 1024 + 1))
    assert not page.locator("#resumator-resume-value").is_visible()
    assert jazzhr.fill(page, resume, str(good)) == "ok"
    assert page.locator("#resumator-resume-value").is_visible() and jazzhr.holds(page, resume)
    got = jazzhr.fill(page, resume, str(big))
    assert got.startswith("FAIL the file is bigger than the page allows") and "limit 5MB" in got
    page.evaluate("""() => document.getElementById('resumator-resume').insertAdjacentHTML('beforeend',
        '<span class="resumator_label_error">Please attach a resume</span>')""")
    assert jazzhr.fill(page, resume, str(good)) == "FAIL the page says 'Please attach a resume' - check the resume box"


def test_workable_holds_reads_what_shows_never_the_answer(fixture_page):
    """Nothing picked, a wrong pick, a box not on the page, a tick too many: not held."""
    page = fixture_page("workable-form.html")
    work = answered("QA_3", "yesno", "Yes", ["Yes", "No"])
    assert not workable.holds(page, work)
    assert workable.fill(page, work | {"answer": "No"}, None) == "ok"
    assert not workable.holds(page, work)
    degree = answered("CA_1", "choice", "Associate")
    assert not workable.holds(page, degree)
    assert workable.fill(page, degree | {"answer": "Bachelor's"}, None) == "ok" and not workable.holds(page, degree)
    shifts = answered("CA_9", "multichoice", ["Weekends"], ["Weekends", "Evenings", "Holiday"]) | {"native": "CA:multiple:152176,152177,152178"}
    assert workable.fill(page, shifts, None) == "ok" and workable.holds(page, shifts)
    page.locator('input[name="152177"]').check()
    assert not workable.holds(page, shifts)
    assert not workable.holds(page, answered("QA_99", "text", "x"))
    page.locator("#input_phone").fill("+1 555-0100")  # a dialling code in front is the box's
    assert workable.holds(page, answered("phone", "phone", "555-0100"))
    assert not workable.holds(page, answered("phone", "phone", "555-0199"))
    assert not workable.holds(page, answered("resume", "file", True) | {"key": "resume"})


def test_workable_upload_waits_for_storage_and_says_the_pages_words(fixture_page, monkeypatch, tmp_path):
    """Choosing the file sends it to storage at once (stand-in endpoint on the fixture host): ok only once
    the name shows and no error follows; the page's own words when it refuses or the upload fails."""
    monkeypatch.setattr(workable, "ERROR_WAIT_MS", 500)
    page = fixture_page("workable-form.html")
    resume = answered("resume", "file", True, title="Resume") | {"key": "resume"}
    good, big = tmp_path / "Ada_Lovelace_Resume.pdf", tmp_path / "Big_Resume.pdf"
    good.write_bytes(b"%PDF-1.4\n%%EOF\n")
    big.write_bytes(b"%PDF-1.4 " + b"0" * (5 * 1024 * 1024 + 1))
    assert workable.fill(page, resume, str(good)) == "ok" and workable.holds(page, resume)
    assert page.locator("#input_files_input_ph0t0").evaluate("e => e.files.length") == 0  # never the photo box
    assert workable.fill(page, resume, str(big)) == \
        "FAIL the page says 'File is too big' - choose the file again on the page, or check the resume box"
    assert not workable.holds(page, resume)
    page.route("**/workable-upload.json", lambda route: route.fulfill(status=500, body=""))
    assert workable.fill(page, resume, str(good)) == ("FAIL the page says 'Something went wrong. We are working on this, "
                                                      "please try again later.' - choose the file again on the page, or check the resume box")


def test_ashby_upload_waits_for_the_pages_verdict_and_says_its_words(fixture_page, monkeypatch, tmp_path):
    """A failed upload still shows the file name + Replace (3 of 3 employers, 2026-10-05): ok only once
    the page has said nothing failed for a while after the name; its own error words otherwise."""
    monkeypatch.setattr(ashby, "ERROR_WAIT_MS", 1000)
    page = fixture_page("ashby-form.html")
    resume = answered("_systemfield_resume", "file", True, title="Resume") | {"key": "resume"}
    good, bad = tmp_path / "Ada_Lovelace_Resume.pdf", tmp_path / "bad_Resume.pdf"
    for f in (good, bad):
        f.write_bytes(b"%PDF-1.4\n%%EOF\n")
    assert ashby.fill(page, resume, str(bad)) == \
        "FAIL the page says 'bad_Resume.pdf failed to upload' - choose the file again on the page, or check the resume box"
    assert ashby.fill(page, resume, str(good)) == "ok"


def test_bamboohr_holds_reads_what_shows_never_the_answer(fixture_page):
    """Untouched list shows "-Select-", no radio ticked, another pick, a box not on the page, no file: not held."""
    page = fixture_page("bamboohr-form.html")
    state = answered("state", "text", "New York")
    assert not bamboohr.holds(page, state)
    assert bamboohr.fill(page, state | {"answer": "Alaska"}, None) == "ok" and not bamboohr.holds(page, state)
    assert bamboohr.holds(page, answered("countryId", "choice", "United States"))  # preset by the page
    vet = answered("veteranStatusId", "choice", "Veteran")
    assert not bamboohr.holds(page, vet)
    assert bamboohr.fill(page, vet | {"answer": "Not a Veteran"}, None) == "ok" and not bamboohr.holds(page, vet)
    sponsor = answered("customQuestionAnswers.yes_no_1019", "yesno", "Yes") | {"native": "bamboohr:yes_no"}
    assert not bamboohr.holds(page, sponsor)
    assert bamboohr.fill(page, sponsor, None) == "ok" and bamboohr.holds(page, sponsor)
    assert not bamboohr.holds(page, answered("customQuestionAnswers.short_9", "text", "x"))
    page.locator("#phone").fill("+1 555-0100")  # a dialling code in front is the box's
    assert bamboohr.holds(page, answered("phone", "phone", "555-0100"))
    assert not bamboohr.holds(page, answered("phone", "phone", "555-0199"))
    resume = answered("resumeFileId", "file", True, title="Resume") | {"key": "resume", "native": "bamboohr:file 2 of 2"}
    assert not bamboohr.holds(page, resume)


def test_bamboohr_upload_waits_for_the_block_and_says_the_pages_words(fixture_page, monkeypatch, tmp_path):
    """Choosing the file sends it at once (stand-in endpoint on the fixture host): ok once the name shows,
    sent, with no error after; BambooHR's own banner words when it refuses or the upload fails - a banner
    left from an earlier try is not this one's. Never the cover letter box."""
    monkeypatch.setattr(bamboohr, "ERROR_WAIT_MS", 500)
    page = fixture_page("bamboohr-form.html")
    resume = answered("resumeFileId", "file", True, title="Resume") | {"key": "resume", "native": "bamboohr:file 2 of 2"}
    good = tmp_path / "Ada_Lovelace_Resume.pdf"
    good.write_bytes(b"%PDF-1.4\n%%EOF\n")
    assert bamboohr.fill(page, resume, str(good)) == "ok" and bamboohr.holds(page, resume)
    letter = page.locator("[data-fabric-component=FileUploadList]").first
    assert letter.inner_text() == ""  # never the cover letter box
    page.route("**/bamboohr-upload.json", lambda route: route.fulfill(
        status=200, content_type="application/json", body='{"status": "ERROR", "errorType": "invalid_file_size"}'))
    assert bamboohr.fill(page, resume, str(good)) == (
        "FAIL the page says 'Whoa, this is a big file (a little too big). The maximum file size you can upload is 20 MB.'"
        " - choose the file again on the page, or check the Resume box")
    assert not bamboohr.holds(page, resume)
    page.unroute("**/bamboohr-upload.json")
    page.route("**/bamboohr-upload.json", lambda route: route.fulfill(status=500, body=""))
    assert bamboohr.fill(page, resume, str(good)) == \
        "FAIL the page says 'Request failed with status code 500' - choose the file again on the page, or check the Resume box"


def test_survey_tally_is_counts_only():
    from apply import survey
    f = lambda **k: {"type": "t", "required": False, "survey": False, "resume": False, "file": False, "known": True,
                     "raw": {"title": "Why Acme?"}} | k
    got = survey.tally([("Lever", [f(type="standard:resume:file", file=True, resume=True, required=True),
                                   f(type="card:file-upload", file=True, known=False), f(survey=True)]),
                        ("Lever", None)])["Lever"]
    assert (got["employers"], got["closed"], got["survey_forms"]) == (2, 1, 1)
    assert (got["other_file_boxes"], got["employers_with_other_file"], got["unknown"]) == (1, 1, ["card:file-upload"])
    assert got["types"]["standard:resume:file"] == {"employers": 1, "fields": 1, "required": 1}
    assert "Acme" not in json.dumps(got)  # question text never in the counts
