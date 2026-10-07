"""A student's resume: Education leads, "Expected May 2027", GPA as the transcript gives it,
relevant coursework, school time never read as a work break (plan-students)."""
import copy
from datetime import date

import pytest
import yaml

import cfg
from resume import lint, render, schema

STUDENT = cfg.APP / "tests" / "fixtures" / "student.yml"
TODAY = date(2026, 10, 7)


@pytest.fixture
def student() -> dict:
    return copy.deepcopy(schema.load(STUDENT))


def education(master: dict, today: date = TODAY) -> dict:
    return next(s for s in render.page_model(master, today)["sections"] if s["title"] == "Education")


def test_student_file_loads_and_education_leads_with_expected_date_gpa_and_courses(student):
    model = render.page_model(student, TODAY)
    assert [s["title"] for s in model["sections"]][0] == "Education"
    entry = education(student)["entries"][0]
    assert entry["subline"] == "Bachelor of Science, Statistics | Dean's List | GPA 3.62/4.00 | Expected May 2027"
    assert entry["bullets"] == []
    assert entry["note"] == "Relevant coursework: Regression Analysis, Database Systems, Data Visualization"


def test_student_page_passes_every_render_gate(student, tmp_path):
    model = render.page_model(student, TODAY)
    path = tmp_path / "r.pdf"
    path.write_bytes(render.compile_pdf(model))
    assert {name: detail for name, ok, detail in render.check(path, model, budget=False) if not ok} == {}
    assert "Relevant coursework: Regression Analysis" in " ".join(render.page_strings(model))


def test_hidden_year_on_a_degree_in_progress_says_in_progress(student):
    student["education"][0]["hide_year"] = True
    assert education(student)["entries"][0]["subline"].endswith("| In progress")


@pytest.mark.parametrize("end, studying", [("2026", False), ("2027", True), ("2026-12", True), ("2026-05", False)])
def test_in_progress_reads_a_year_alone_as_maybe_finished(end, studying):
    assert schema.in_progress({"end": end}, TODAY) is studying


def test_unquoted_gpa_is_refused_with_how_to_fix_it(student):
    student["education"][0]["gpa"] = 3.5
    assert schema.validate(student) == ['education[0].gpa: put it in quotes, exactly as the transcript gives it: "3.5"']


def test_campus_job_during_school_still_lets_the_degree_lead(student):
    # 25 months at the library since Sep 2024 + a summer internship: all of it after school began
    assert render.months_worked(student["roles"], TODAY) == 26
    assert render.education_first(student, TODAY)
    # without a start on file the work months count whole: two years of it and the work leads
    del student["education"][0]["start"]
    assert not render.education_first(student, TODAY)


def test_returning_adult_leads_with_work_and_their_own_choice_wins(student):
    student["roles"] = [{**student["roles"][1], "start": "2006-01", "end": "2024-06"}]
    student["education"][0]["start"] = "2024-08"
    assert not render.education_first(student, TODAY)
    student["education_first"] = True
    assert render.education_first(student, TODAY)
    assert schema.validate(student) == []


def test_months_worked_counts_overlaps_once_and_no_incoming_job():
    roles = [{"start": "2024-09", "end": "present"}, {"start": "2025-06", "end": "2025-08"},
             {"start": "2027-06", "end": "2027-08"}]  # an internship accepted for next summer
    assert render.months_worked(roles, TODAY) == 26


def test_expected_degree_never_turns_into_a_held_one_when_its_date_passes(student):
    later = date(2027, 8, 1)
    # no flag: the date alone said expected, and once past the page shows the year
    assert education(student, later)["entries"][0]["subline"].endswith("| 2027")
    student["education"][0]["expected"] = True
    assert education(student, later)["entries"][0]["subline"].endswith("| Expected May 2027")
    assert [f.rule for f in lint.master_findings(student, later)] == ["expected-date-passed"]
    assert lint.master_findings(student, TODAY) == []
    student["education"][0]["expected"] = False
    assert education(student, later)["entries"][0]["subline"].endswith("| 2027")


@pytest.mark.parametrize("gpa, ok", [("3.62", True), ("3.62/4.00", True), ("3.8 / 4.0", True), ("9.2/10", True),
                                     ("86%", True), ("3.62 (Major 3.80)", True), ("First Class Honours", False),
                                     ("about 3.5", False)])
def test_gpa_is_kept_as_the_transcript_writes_it_any_scale(student, gpa, ok):
    student["education"][0]["gpa"] = gpa
    assert (schema.validate(student) == []) is ok


def test_four_point_gpa_is_told_apart_from_other_scales():
    fits = [bool(schema.FOUR_POINT.match(g)) for g in ("3.62", "3.62/4.00", "3.8 / 4.0", "9.2/10", "86%", "3.9/5")]
    assert fits == [True, True, True, False, False, False]


def summers_only(student: dict) -> dict:
    intern = student["roles"][0]
    student["roles"] = [intern, {**intern, "start": "2024-06", "end": "2024-08"}]
    return student


def test_time_in_school_is_no_work_break(student):
    master = summers_only(student)
    assert schema.employment_gaps(master, TODAY) == []
    del master["education"][0]["start"]  # never guessed: without a start the months read as a break
    assert [g["months"] for g in schema.employment_gaps(master, TODAY)] == [9, 13]


def test_school_years_before_a_first_job_make_no_new_gap():
    master = {"roles": [{"start": "2020-01", "end": "present"}],
              "education": [{"institution": "U", "degree": "BA", "start": "2010-09", "end": "2014-05"}]}
    assert schema.employment_gaps(master, TODAY) == []
    # a master's in the middle of a gap closes only the months it covers
    master["roles"] = [{"start": "2020-01", "end": "present"}, {"start": "2012-01", "end": "2015-12"}]
    master["education"] = [{"institution": "U", "degree": "MS", "start": "2018-09", "end": "2019-12"}]
    assert schema.employment_gaps(master, TODAY) == [{"after": "2015-12", "before": "2018-09", "months": 32}]


def test_graduation_is_the_degree_in_progress_else_the_latest(student):
    student["education"].append({"institution": "Columbus State Community College", "degree": "AA", "end": "2023-05"})
    assert schema.graduation(student, TODAY) == "2027-05"
    student["education"][0]["end"] = "2026-05"
    assert schema.graduation(student, TODAY) == "2026-05"
    assert schema.graduation({"education": []}, TODAY) is None


def test_fixture_is_plain_user_facts():
    raw = yaml.safe_load(STUDENT.read_text(encoding="utf-8"))
    assert "id" not in raw["roles"][0] and isinstance(raw["roles"][0]["bullets"][0], str)
