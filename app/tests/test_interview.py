import copy
from datetime import date

import pytest

import interview
from resume import schema
from test_tailor import EXAMPLE, JOB


@pytest.fixture
def master() -> dict:
    return copy.deepcopy(schema.load(EXAMPLE))


TAILORED = {"summary": "", "skills": [], "inferences": [],
            "entries": [{"id": "acme", "title_mirror": None, "bullets": [
                {"text": "Cut checkout INP 410ms -> 170ms moving cart recalculation to Web Workers", "sources": ["acme-inp"]}]}],
            "coverage": [{"requirement": 0, "evidence": ["acme-inp"], "note": "Vue on page"},
                         {"requirement": 1, "evidence": [], "note": "no GraphQL"}]}


def test_requirements_listed_with_their_backing_lines_and_gaps(master):
    out = "\n".join(interview.context(master, JOB, TAILORED, {"state": "interview", "state_at": "2026-09-30T12:00:00Z"}))
    assert "where it stands: Interview since 2026-09-30" in out
    assert "- (required) 5+ years Vue [shown - a line with a number]" in out
    assert "    line: Cut checkout INP 410ms -> 170ms" in out
    assert "- (preferred) GraphQL [NOT shown]" in out


def test_pay_stated_or_said_to_be_missing_and_text_marked_untrusted(master):
    out = interview.context(master, JOB, None, None)
    assert "pay: none stated in the posting's data" in out[1] and out[-1] == interview.UNTRUSTED
    paid = {**JOB, "enrichment": {"salary_min": 120000, "salary_max": 150000, "salary_currency": "USD"}}
    assert interview.context(master, paid, None, None)[1] == "pay: 120000-150000 USD"


def test_without_a_tailored_resume_lists_requirements_only(master):
    out = interview.context(master, JOB, None, None)
    assert "no tailored resume for it - requirements only:" in out and "- (preferred) GraphQL" in out


def test_a_degree_in_progress_marks_a_student_and_a_finished_one_does_not(master):
    today = date(2026, 10, 8)
    assert not any(line.startswith("student:") for line in interview.context(master, JOB, None, None, today))
    master["education"].append({"institution": "City College", "degree": "M.S.", "field": "Statistics",
                                "end": "2027-05", "expected": True})
    out = interview.context(master, JOB, None, None, today)
    assert out[1] == "student: M.S., Statistics, City College (expected May 2027) (job-interview #Students)"
    assert out[2].startswith("pay:")


def test_a_hidden_year_or_a_passed_date_is_never_practised_as_a_date(master):
    today = date(2026, 10, 8)
    master["education"][0].update(end="2027-05", expected=True, hide_year=True)
    assert interview.student(master, today) == "student: B.S., Computer Science, State University (in progress) (job-interview #Students)"
    master["education"][0].update(end="2026-05", hide_year=False)
    assert "(expected May 2026) - date passed: ask if they finished" in interview.student(master, today)


# compliance + risk: lines from real postings (2026-10-09) - the duty sentences sit in the text, not
# the requirement list, and a story about AML work must never point to a case
AML_JOB = {"title": "AML Compliance Analyst", "company": "Acme Bank", "requirements": [
    {"text": "3+ years of BSA/AML experience", "priority": "required"},
    {"text": "Active CAMS certification required", "priority": "required"},
    {"text": "FINRA Series 7 and Series 24 licenses (required)", "priority": "required"}],
    "text": ("You will maintain policies and controls, assess financial-crime risks, manage transaction "
             "monitoring and KYC processes, and coordinate regulatory examinations.\n"
             "Review Verafin reports and escalate unusual activity for further investigation.\n"
             "Reconcile financial data across multiple systems, ensuring data accuracy and integrity.\n"
             "Act with integrity and sound judgment under pressure.\n"
             "Knowledge of the Bank Secrecy Act, OFAC, CDD and Reg CC; RCSA and KRI reporting.\n"
             "Offers are contingent on a background check, credit check and fingerprinting.")}


def test_the_postings_own_duty_sentences_and_named_rules_are_quoted():
    out = "\n".join(interview.posting_says(AML_JOB))
    assert "- rules it names: KYC, Bank Secrecy Act, OFAC, CDD, Reg CC" in out
    assert "- risk methods it names: RCSA, KRI" in out
    assert '- exam or audit work: "You will maintain policies and controls' in out
    assert '- escalating or challenging the business: "Review Verafin reports and escalate' in out
    # data's integrity is no ethics question; a person's is
    assert '- judgement or ethics: "Act with integrity and sound judgment under pressure."' in out
    assert "- checks it names: background check, credit check, fingerprinting" in out


def test_a_sentence_already_in_the_requirements_is_not_repeated_and_a_bare_posting_adds_nothing():
    job = {**AML_JOB, "text": "3+ years of BSA/AML experience, escalating alerts to the BSA Officer.",
           "requirements": [{"text": "3+ years of BSA/AML experience, escalating alerts to the BSA Officer.",
                             "priority": "required"}]}
    assert not any(line.startswith("- escalating") for line in interview.posting_says(job))
    assert interview.posting_says({"title": "Barista", "requirements": [], "text": "Make coffee for guests."}) == []


def test_confidential_work_in_the_posting_or_the_resume_gets_the_line(master):
    line = interview.confidential(master, AML_JOB)
    assert line.startswith("confidential work (") and "job-interview #Confidential work" in line
    assert interview.confidential(master, JOB) is None
    master["roles"][0]["bullets"].append("Cleared 60+ alerts a day; filed SARs with the BSA Officer")
    assert "SARs" in interview.confidential(master, JOB)


def test_licences_asked_say_where_they_stand_never_more(master):
    master["certifications"] = [{"name": "Series 7 (passed 2019; not currently registered)"},
                                {"name": "Certified Anti-Money Laundering Specialist (CAMS)"}]
    out = interview.licences(master, AML_JOB)
    assert out[0] == "licences asked (job-interview #Licences):"
    assert '- asks CAMS: on their resume as "Certified Anti-Money Laundering Specialist (CAMS)"' in out
    assert "- asks Series 24: not in their resume details - never claimed in an answer" in out
    assert '- asks Series 7: their resume says "Series 7 (passed 2019; not currently registered)"' in " ".join(out)
    master["certifications"] = [{"name": "Series 7"}, {"name": "Series 24 (passed 2018; not currently registered)"},
                                {"name": "CAMS"}]
    assert ('- asks Series 24: their resume says "Series 24 (passed 2018; not currently registered)" - '
            "said that way, never as held now") in interview.licences(master, AML_JOB)
    assert interview.licences(master, JOB) == []


def test_context_carries_the_compliance_lines_before_the_untrusted_line(master):
    out = interview.context(master, AML_JOB, None, None)
    assert out[-1] == interview.UNTRUSTED
    joined = "\n".join(out)
    assert joined.index("licences asked") < joined.index("the posting's text also names") < joined.index("confidential work")
