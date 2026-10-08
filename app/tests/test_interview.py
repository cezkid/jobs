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
