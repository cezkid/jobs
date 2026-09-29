from datetime import date

import yaml

import cfg
from resume import feedback

DETAILS = {
    "contact": {"name": "Ada Lovelace", "email": "ada@example.com", "location": "Austin, TX"},
    "roles": [{"company": "Acme Inc.", "title": "Software Engineer", "start": "2023-02", "end": "present", "bullets": [
        "Cut checkout time 40% by moving work off the main thread.",
        "Led a 4-person team through the Vue 3 migration of every checkout, account and search screen.",
        "Wrote Jest tests for the checkout screens.",
        "Paired 12 screens with the REST APIs feeding them.",
    ]}],
}
TODAY = date(2026, 9, 24)


def write(tmp_path, details=DETAILS):
    path = tmp_path / "Resume details.yml"
    path.write_text(yaml.safe_dump(details), encoding="utf-8")
    return path


def test_areas_count_numbers_and_what_the_lines_show(tmp_path):
    report, result, moved = feedback.run(write(tmp_path), TODAY, tmp_path / "state.json")
    areas = result["areas"]
    assert areas["Numbers and scope"] == (feedback.GOOD, "3 of 4 lines say how many, how much or what changed")
    assert areas["Leadership"] == (feedback.GOOD, "1 line(s) show it")
    # "paired screens with APIs" pairs code, not people; leading a team is teamwork
    assert [c for _, c in result["shown"]["Teamwork"]] == [DETAILS["roles"][0]["bullets"][1]] and moved == []
    text = report.read_text(encoding="utf-8")
    assert "- Wrote Jest tests for the checkout screens. (Software Engineer at Acme Inc.)" in text
    assert "Help me add numbers to my resume" in text and "Page layout not scored here" in text
    assert "Presentation" not in text and "## At a glance" in text


def test_links_to_the_guide_that_exists():
    assert (cfg.ROOT / "My Resume" / feedback.GUIDE).resolve() == (cfg.ROOT / "Guides" / "What makes a good resume.md").resolve()
    assert (cfg.ROOT / "Guides" / "What makes a good resume.md").exists()


def test_second_run_says_what_moved(tmp_path):
    state = tmp_path / "state.json"
    feedback.run(write(tmp_path), TODAY, state)
    better = {**DETAILS, "roles": [{**DETAILS["roles"][0], "bullets": [
        *DETAILS["roles"][0]["bullets"][:2], "Wrote 120 Jest tests for the checkout screens.",
        "Paired 12 screens with the REST APIs feeding them."]}]}
    _, _, moved = feedback.run(write(tmp_path, better), TODAY, state)
    assert moved == ["Numbers and scope: Good -> Strong (4 of 4 lines say how many, how much or what changed)"]


def test_wording_and_personal_notes_land_in_their_sections(tmp_path):
    details = {**DETAILS, "contact": {**DETAILS["contact"], "location": "12 Main St, Austin, TX 78701"},
               "roles": [{**DETAILS["roles"][0], "bullets": ["Organised 3 theatre events a year for 200 guests."]}]}
    report, result, _ = feedback.run(write(tmp_path, details), TODAY, tmp_path / "state.json")
    assert result["areas"]["Wording"][0] == feedback.LOOK
    assert result["areas"]["Personal details and dates"][0] == feedback.LOOK
    text = report.read_text(encoding="utf-8")
    assert "theatre -> theater" in text.split("## Wording notes")[1].split("##")[0]
    assert "street address" in text.split("## Details and dates")[1]


def test_breaks_get_a_note_by_length_and_a_running_search_none_as_a_fault(tmp_path):
    details = {**DETAILS, "roles": [
        {**DETAILS["roles"][0], "start": "2020-01", "end": "2025-06"},
        {**DETAILS["roles"][0], "company": "Beta LLC", "start": "2017-01", "end": "2018-06"},
    ]}
    report, result, _ = feedback.run(write(tmp_path, details), TODAY, tmp_path / "state.json")
    text = report.read_text(encoding="utf-8").split("## Details and dates")[1]
    assert "- 18-month break between jobs (2018-06 to 2020-01). Worth a line, plus recent work" in text
    assert "- 14-month break since your last job (2025-06 to now). Your search so far" in text


def aged(end: str, **extra) -> dict:
    return {**DETAILS, "education": [{"institution": "State University", "degree": "BA", "end": end}],
            "certifications": [{"name": "Certified Nursing Assistant", "date": "2004-03"}], **extra}


def test_degree_20_years_old_adds_the_bundle_note_once(tmp_path):
    old_job = {"company": "Beta LLC", "title": "Clerk", "start": "2003-01", "end": "2008-06", "bullets": ["Filed 40 forms a day."]}
    details = aged("2004-05", roles=[*DETAILS["roles"], old_job])
    report, result, _ = feedback.run(write(tmp_path, details), TODAY, tmp_path / "state.json")
    text = report.read_text(encoding="utf-8")
    assert {n[0] for n in result["notes"]} >= {"old-graduation-year", "old-certification-year"}
    assert text.count("every year that lets a reader guess age") == 1
    assert "the 1 job(s) that ended 15+ years ago" in text and "60% said" in text and "older" not in text


def test_bundle_note_waits_for_20_years_and_for_a_year_still_showing(tmp_path):
    report, _, _ = feedback.run(write(tmp_path, aged("2009-05")), TODAY, tmp_path / "state.json")
    text = report.read_text(encoding="utf-8")
    assert "BA ended 2009; hide_year: true leaves the year off" in text
    assert "every year that lets a reader guess age" not in text
    hidden = aged("2004-05")
    hidden["education"][0]["hide_year"] = True
    hidden["certifications"][0]["hide_year"] = True
    report, result, _ = feedback.run(write(tmp_path, hidden), TODAY, tmp_path / "state.json")
    assert result["bundle"] is None and "every year that lets a reader guess age" not in report.read_text(encoding="utf-8")
