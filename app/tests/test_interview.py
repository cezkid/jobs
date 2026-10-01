import copy

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
