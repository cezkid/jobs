import copy
from datetime import date

import pytest

import cfg
from resume import schema

EXAMPLE = cfg.APP / "resume" / "master.example.yml"
TODAY = date(2026, 9, 16)


@pytest.fixture
def master() -> dict:
    return copy.deepcopy(schema.load(EXAMPLE))


def errors_for(master: dict) -> list[str]:
    return schema.validate(master)


def test_example_validates(master):
    assert errors_for(master) == []


def test_abbreviated_title_rejected(master):
    master["roles"][0]["title"] = "Sr. Software Engineer"
    assert any("abbreviated" in e for e in errors_for(master))


def test_company_without_legal_identifier_accepted(master):
    master["roles"][1]["company"] = "Mount Sinai Hospital"
    assert errors_for(master) == []


def test_ai_era_optional_defaults_false(master):
    del master["roles"][1]["ai_era"]
    assert errors_for(master) == []
    master["roles"][1]["bullets"][0]["ai_work"] = True
    assert any("ai_work bullet inside entry with ai_era false" in e for e in errors_for(master))


def test_ai_bullet_in_pre_ai_role_rejected(master):
    master["roles"][1]["bullets"][0]["ai_work"] = True
    assert any("ai_work bullet inside entry with ai_era false" in e for e in errors_for(master))


def test_duplicate_bullet_id_rejected(master):
    master["projects"][0]["bullets"][0]["id"] = "acme-inp"
    assert any("duplicate" in e for e in errors_for(master))


def test_full_date_rejected(master):
    master["roles"][1]["start"] = date(2019, 6, 1)
    assert any("not YYYY-MM" in e for e in errors_for(master))


def test_end_before_start_rejected(master):
    master["roles"][1]["end"] = "2018-01"
    assert any("before start" in e for e in errors_for(master))


def test_roles_out_of_order_named_in_plain_words(master):
    master["roles"].reverse()
    assert ("roles: 'Software Engineer at Globex Corporation' (started 2019-06) is listed above "
            "'Senior Software Engineer at Acme Inc.' (started 2023-02), which started later - "
            "put the newest first by moving one of them") in errors_for(master)


def test_missing_required_field_reported(master):
    del master["roles"][0]["bullets"][0]["claim"]
    assert "roles[0].bullets[0].claim: missing" in errors_for(master)


def test_no_gap_when_contiguous(master):
    assert schema.employment_gaps(master, TODAY) == []


def test_gap_over_six_months_reported(master):
    master["roles"][0]["start"] = "2023-09"
    assert schema.employment_gaps(master, TODAY) == [{"after": "2023-01", "before": "2023-09", "months": 7}]


def test_overlapping_role_covers_gap(master):
    master["roles"][0]["start"] = "2023-09"
    master["roles"].insert(1, {**master["roles"][1], "id": "side", "start": "2022-01", "end": "2023-08"})
    assert schema.employment_gaps(master, TODAY) == []


def test_trailing_gap_reported(master):
    master["roles"][0]["end"] = "2026-01"
    assert schema.employment_gaps(master, TODAY) == [{"after": "2026-01", "before": "2026-09", "months": 7}]


def test_a_job_with_no_lines_is_rejected(master):
    # details.schema.json says minItems 1; the page would show a heading with nothing under it
    master["roles"][0]["bullets"] = []
    assert any("bullets: empty" in e for e in errors_for(master))


def test_year_only_dates_accepted_and_compared_as_years(master):
    master["roles"][1].update(start="2019", end="2023")
    assert errors_for(master) == []
    master["roles"][1].update(start="2021-05", end="2021")  # same year: not "end before start"
    assert errors_for(master) == []
    master["roles"][1]["start"] = "2019-13"
    assert any("not YYYY-MM or YYYY" in e for e in errors_for(master))


def test_year_typed_without_quotes_reads_as_that_year():
    raw = {"roles": [{"company": "Acme", "title": "Clerk", "start": 2019, "end": "present", "bullets": ["Filed"]}],
           "certifications": [{"name": "First Aid", "date": 2021}]}
    expanded = schema.expand(raw)
    assert expanded["roles"][0]["start"] == "2019" and expanded["certifications"][0]["date"] == "2021"


def test_order_checked_at_the_precision_both_dates_carry(master):
    master["roles"][0]["start"] = "2019"
    master["roles"][1].update(start="2019-06", end="2019-09")
    assert not any("listed above" in e for e in errors_for(master))


def test_year_only_end_reads_as_the_whole_year():
    assert schema.in_ai_era({"end": "2023"}) and not schema.in_ai_era({"end": "2022"})
    roles = [{"start": "2021", "end": "present"}, {"start": "2017", "end": "2020"}]
    assert schema.employment_gaps({"roles": roles}, TODAY) == []


def test_career_break_covers_the_gap(master):
    master["roles"][1]["end"] = "2021-01"
    assert schema.employment_gaps(master, TODAY)
    master["career_break"] = [{"reason": "Caring for a family member", "start": "2021-02", "end": "2023-01"}]
    assert errors_for(master) == []
    assert schema.employment_gaps(master, TODAY) == []
    master["career_break"][0].pop("reason")
    assert "career_break[0].reason: missing" in errors_for(master)


def test_other_sections_need_a_heading_and_lines(master):
    master["other"] = [{"heading": "Volunteer Work", "lines": ["Riverside Food Bank, driver, 2020 - 2022"]}]
    assert errors_for(master) == []
    master["other"][0]["lines"] = []
    assert "other[0].lines: empty" in errors_for(master)


def test_project_dates_optional_but_never_half_given(master):
    del master["projects"][0]["start"], master["projects"][0]["end"]
    assert errors_for(master) == []
    master["projects"][0]["start"] = "2024-05"
    assert "projects[0].end: missing" in errors_for(master)


def test_no_jobs_yet_is_a_valid_file(master):
    master["roles"] = []
    assert errors_for(master) == []
    assert schema.employment_gaps(master, TODAY) == []
