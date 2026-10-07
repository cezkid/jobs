from datetime import date

import pytest

from resume import knockout

TODAY = date(2026, 10, 1)


@pytest.mark.parametrize("text, years", [
    ("5+ years of experience in software development", 5),
    ("10-15 years of progressive experience in FP&A", 10),
    ("At least five years of experience building production software", 5),
    ("5+ years accounting experience within an e-commerce, retail or CPG environment", 5),
    ("8+ years in manufacturing or hardware cost accounting.", 8),
    ("Minimum of one year post-graduate clinical experience", 1),
    ("Must be at least 18 years of age.", None),
    ("Must be at least 16 years old", None),
    ("CPMA certification a plus (must be obtained within 1 year of hire).", None),
    ("Strong communication skills", None),
    # school, not work (a student's internship asks): "work" inside "coursework", "of" after the years
    ("Completed at least 2 years of undergraduate study", None),
    ("Completed 2 years of coursework in accounting", None),
    ("Two years of college or equivalent", None),
    ("Completed at least two years of a four-year degree program", None),
    ("2+ years of work experience in retail", 2),
])
def test_years_asked_reads_the_lower_bound_never_age_or_deadlines(text, years):
    assert knockout.years_asked(text) == years


@pytest.mark.parametrize("text, level", [
    ("Bachelor's degree in Accounting, Finance, or related field required", "bachelor's"),
    ("Bachelor's or Master's degree in Computer Science", "bachelor's"),
    ("Master's or Doctorate degree in construction management", "master's"),
    ("A Ph.D. in a relevant humanities discipline", "doctorate"),
    ("CPA required; MBA a plus", None),
    ("Eager to master specialized vein procedures rapidly", None),
    ("Currently pursuing an undergraduate degree in Finance", None),
    ("Bachelor's degree in Computer Science, Engineering, or equivalent practical experience.", None),
    ("Bachelor's degree required, or demonstrated equivalent combination of education and training", None),
    ("MD or DO degree; board certification in your specialty", None),
    ("High school diploma", "high school"),
])
def test_degree_asked_is_the_lowest_level_named_and_skips_what_says_nothing(text, level):
    assert knockout.degree_asked(text) == level


def test_degree_held_reads_written_or_short_forms():
    held = [knockout.degree_held({"degree": d}) for d in ("BS", "B.S.", "Associate of Applied Science", "MBA",
                                                          "PhD", "Juris Doctor", "Certificate in Welding",
                                                          "B.S. in Computer Science", "BA Economics")]
    assert held == ["bachelor's", "bachelor's", "associate's", "master's", "doctorate", None, None,
                    "bachelor's", "bachelor's"]


def master(years_worked: int, degree: str | None) -> dict:
    return {"roles": [{"start": f"{2026 - years_worked}-01", "end": "present", "bullets": []}],
            "education": [{"institution": "State College", "degree": degree}] if degree else []}


def test_only_a_visible_shortfall_is_said_quoting_the_posting():
    job = {"requirements": [
        {"text": "5+ years of experience in customer support", "priority": "required"},
        {"text": "Bachelor's degree in Business", "priority": "required"},
        {"text": "10+ years of experience leading teams", "priority": "preferred"}]}
    assert knockout.shortfalls(master(3, "AA"), job, TODAY) == [
        'Asks 5+ years ("5+ years of experience in customer support"). Your dated jobs add up to 3.',
        "Asks a bachelor's degree (\"Bachelor's degree in Business\"). Your highest in your resume details: associate's."]
    assert knockout.shortfalls(master(9, "BS"), job, TODAY) == []
    assert "none listed" in knockout.shortfalls(master(9, None), job, TODAY)[0]


def test_an_education_entry_it_cannot_read_says_nothing_about_degrees():
    job = {"requirements": [{"text": "Master's degree in Social Work", "priority": "required"}]}
    assert knockout.shortfalls(master(9, "Juris Doctor"), job, TODAY) == []


def test_overlapping_jobs_count_once():
    m = {"roles": [{"start": "2020-01", "end": "2022-12"}, {"start": "2021-06", "end": "2023-12"}]}
    assert knockout.dated_years(m, TODAY) == 4
