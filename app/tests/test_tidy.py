import json

import jsonschema
import pytest
import yaml

import cfg
from resume import facts, schema, tidy

EXAMPLE = cfg.APP / "resume" / "master.example.yml"
DETAILS_SCHEMA = json.loads((cfg.APP / "resume" / "details.schema.json").read_text(encoding="utf-8"))
PLAIN = """
contact: {name: Ada Lovelace, email: ada@example.com, location: London}
roles:
- company: Acme Inc.
  title: Software Engineer
  start: 2023-02
  end: present
  bullets:
  - Cut checkout time 40% by moving work off the main thread.
- company: Acme Inc.
  title: Junior Software Engineer
  start: 2019-06
  end: 2022-11
  bullets:
  - Shipped the first version of the ordering screen.
"""


@pytest.fixture
def plain(tmp_path):
    path = tmp_path / "Resume details.yml"
    path.write_text(PLAIN, encoding="utf-8")
    return path


def notes(tmp_path):
    return tmp_path / "resume-index.yml"


def test_plain_file_loads_with_the_ids_the_importer_wrote(plain, tmp_path):
    # ids never reach the user's file, but tailored answers and job folders still key off them
    master = schema.load(plain, notes(tmp_path))
    assert [r["id"] for r in master["roles"]] == ["acme", "acme-junior-software-engineer"]
    assert [b["id"] for r in master["roles"] for b in r["bullets"]] == ["acme-1", "acme-junior-software-engineer-1"]
    assert schema.validate(master) == []


def test_ai_era_read_off_the_dates_unless_the_file_says_otherwise(plain, tmp_path):
    master = schema.load(plain, notes(tmp_path))
    assert [r["ai_era"] for r in master["roles"]] == [True, False]
    plain.write_text(PLAIN.replace("  start: 2023-02\n", "  start: 2023-02\n  ai_era: false\n"), encoding="utf-8")
    assert schema.load(plain, notes(tmp_path))["roles"][0]["ai_era"] is False


def test_notes_follow_the_claim_not_its_place_in_the_file(plain, tmp_path):
    master = schema.load(plain, notes(tmp_path))
    master["roles"][0]["bullets"][0]["metrics"] = ["40%"]
    master["roles"][0]["bullets"][0]["stack"] = ["Web Workers"]
    facts.write(master, notes(tmp_path))

    # same claim, other way up: notes stay with the sentence they were written for
    plain.write_text("\n".join(PLAIN.splitlines()[::-1]).replace("roles:", ""), encoding="utf-8")
    plain.write_text(PLAIN, encoding="utf-8")
    again = schema.load(plain, notes(tmp_path))
    assert again["roles"][0]["bullets"][0]["stack"] == ["Web Workers"]

    # reworded claim: notes drop off rather than describe a sentence that no longer says them
    plain.write_text(PLAIN.replace("Cut checkout time 40%", "Cut checkout time by a third"), encoding="utf-8")
    reworded = schema.load(plain, notes(tmp_path))
    assert reworded["roles"][0]["bullets"][0] == {"id": "acme-1", "claim": "Cut checkout time by a third by moving work off the main thread.", "metrics": [], "stack": []}


RICH = """
contact:
  name: Ada Lovelace
  email: ada@example.com
  location: London
roles:
- id: acme
  company: Acme Inc.
  title: Software Engineer
  start: 2023-02
  end: present
  ai_era: true
  bullets:
  - id: acme-1
    claim: Cut checkout time 40% by moving work off the main thread.
    metrics:
    - 40%
    stack:
    - Web Workers
    ai_work: false
"""


def test_tidy_keeps_every_fact_and_loses_the_bookkeeping(tmp_path):
    # the shape the importer used to write: four fields of bookkeeping around every claim
    path = tmp_path / "Resume details.yml"
    path.write_text(RICH, encoding="utf-8")
    before = schema.load(path, notes(tmp_path))
    _, backup, was, now = tidy.tidy(path, notes(tmp_path))
    assert schema.load(path, notes(tmp_path)) == before
    assert now < was
    assert yaml.safe_load(backup.read_text(encoding="utf-8")) == yaml.safe_load(RICH)
    written = path.read_text(encoding="utf-8")
    assert "id:" not in written and "metrics:" not in written and "ai_work" not in written
    assert written.startswith(tidy.HEADER[0])
    assert yaml.safe_load(notes(tmp_path).read_text(encoding="utf-8")) == {
        "cut checkout time 40% by moving work off the main thread.": {"metrics": ["40%"], "stack": ["Web Workers"]}}


def test_tidy_never_renumbers_a_bullet_someone_already_tailored_against(tmp_path):
    # older files name bullets after their subject; a tailored answer points at those names
    path = tmp_path / "Resume details.yml"
    path.write_text(EXAMPLE.read_text(encoding="utf-8"), encoding="utf-8")
    before = schema.load(path, notes(tmp_path))
    tidy.tidy(path, notes(tmp_path))
    after = schema.load(path, notes(tmp_path))
    assert after == before
    assert [b["id"] for e in after["roles"] for b in e["bullets"]] == ["acme-rag-search", "acme-inp", "globex-design-system"]


def test_tidy_refuses_to_write_a_file_that_would_read_back_differently(monkeypatch, tmp_path):
    path = tmp_path / "Resume details.yml"
    path.write_text(EXAMPLE.read_text(encoding="utf-8"), encoding="utf-8")
    monkeypatch.setattr(tidy, "scalar", lambda value: "changed")
    with pytest.raises(ValueError):
        tidy.tidy(path, notes(tmp_path))
    assert path.read_text(encoding="utf-8") == EXAMPLE.read_text(encoding="utf-8")


@pytest.mark.parametrize("claim", [
    "Won 4 advertisers: Dunkin' Donuts, Six Flags and Bowlero.",
    "- led the team through it",
    "12",
    "yes",
    'Called it "the rebuild" in every meeting',
    "#1 in organic search",
    "Kept costs down  ",
])
def test_punctuation_in_a_claim_survives_the_rewrite(claim, tmp_path):
    master = schema.expand(yaml.safe_load(PLAIN))
    master["roles"][0]["bullets"][0]["claim"] = claim
    text = tidy.dump(tidy.strip(master))
    assert yaml.safe_load(text)["roles"][0]["bullets"][0] == claim


def test_editor_marks_a_mistyped_fact(tmp_path):
    def errors(doc):
        return [e.message for e in jsonschema.Draft7Validator(DETAILS_SCHEMA).iter_errors(doc)]

    good = yaml.safe_load(PLAIN)
    assert errors(good) == []
    assert errors(yaml.safe_load(EXAMPLE.read_text(encoding="utf-8"))) == []
    typo = yaml.safe_load(PLAIN)
    typo["roles"][0]["compnay"] = typo["roles"][0].pop("company")
    assert errors(typo)
    bad_date = yaml.safe_load(PLAIN)
    bad_date["roles"][0]["start"] = "Feb 2023"
    assert errors(bad_date)
    assert errors({"contact": good["contact"]})  # roles missing entirely


def test_a_job_moved_before_the_ai_era_is_not_handed_an_ai_note_it_never_carried(plain, tmp_path):
    # the notes are keyed by the claim, so they outlive the dates: re-attaching the flag would
    # fail the whole file over a line the user only changed the dates on
    master = schema.load(plain, notes(tmp_path))
    master["roles"][0]["bullets"][0]["ai_work"] = True
    facts.write(master, notes(tmp_path))
    assert schema.load(plain, notes(tmp_path))["roles"][0]["bullets"][0]["ai_work"] is True

    plain.write_text(PLAIN.replace("  start: 2023-02\n  end: present", "  start: 2019-01\n  end: 2019-06")
                     .replace("  start: 2019-06\n  end: 2022-11", "  start: 2018-01\n  end: 2018-06"), encoding="utf-8")
    moved = schema.load(plain, notes(tmp_path))
    assert moved["roles"][0]["ai_era"] is False
    assert "ai_work" not in moved["roles"][0]["bullets"][0]


def test_header_says_wording_wins_but_employer_title_and_dates_are_checked():
    header = " ".join(tidy.HEADER)
    assert "your edits always win" not in header
    assert "wording always wins" in header and "only to fix a mistake" in header


def test_new_sections_round_trip_and_the_editor_accepts_them(tmp_path):
    doc = yaml.safe_load(PLAIN)
    doc["roles"][1].update(start="2019", end="2022")
    doc["career_break"] = [{"reason": "Caring for a family member", "start": "2022", "end": "2023-01"}]
    doc["education"] = [{"institution": "State University", "degree": "BA", "end": "2004", "hide_year": True}]
    doc["other"] = [{"heading": "Volunteer Work", "lines": ["Riverside Food Bank, driver, 2020 - 2022"]}]
    assert [e.message for e in jsonschema.Draft7Validator(DETAILS_SCHEMA).iter_errors(doc)] == []
    typed = yaml.safe_load(PLAIN.replace("start: 2019-06", "start: 2019"))  # a year typed bare is fine too
    assert [e.message for e in jsonschema.Draft7Validator(DETAILS_SCHEMA).iter_errors(typed)] == []
    path = tmp_path / "Resume details.yml"
    path.write_text(yaml.safe_dump(doc), encoding="utf-8")
    before = schema.load(path, notes(tmp_path))
    tidy.tidy(path, notes(tmp_path))
    assert schema.load(path, notes(tmp_path)) == before
    written = path.read_text(encoding="utf-8")
    assert written.index("career_break:") < written.index("education:") < written.index("other:")


def test_headline_is_one_optional_line_that_round_trips(tmp_path):
    doc = yaml.safe_load(PLAIN)
    doc["headline"] = "Software Engineer | Python, SQL"
    assert [e.message for e in jsonschema.Draft7Validator(DETAILS_SCHEMA).iter_errors(doc)] == []
    path = tmp_path / "Resume details.yml"
    path.write_text(yaml.safe_dump(doc), encoding="utf-8")
    before = schema.load(path, notes(tmp_path))
    tidy.tidy(path, notes(tmp_path))
    assert schema.load(path, notes(tmp_path)) == before
    written = path.read_text(encoding="utf-8")
    assert written.index("contact:") < written.index("headline:") < written.index("roles:")
    assert schema.validate({**before, "headline": "two\nlines"}) == ["master.headline: one line of text"]
