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


def test_roles_must_be_newest_first(master):
    master["roles"].reverse()
    assert any("newest-first" in e for e in errors_for(master))


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
