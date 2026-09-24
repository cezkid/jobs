import copy
from datetime import date

import pymupdf
import pytest

from resume import handoff, import_pdf, schema

TODAY = date(2026, 9, 16)
SOURCE = """Jane Doe
github.com/janedoe | Springfield, IL | jane@example.com
PROFESSIONAL EXPERIENCE
Acme Inc. Remote
Support platform
Senior Software Engineer    Feb 2023 - Present
Built retrieval search over support docs, deflected 23% of
tier-1 tickets
Globex Corporation
Software Engineer     2019 \u2013 2023
Led design system migration across 6 teams (Vue)
Software Engineer Intern    2018 \u2013 2019
Wrote Storybook stories
EDUCATION
State University
B.S. Computer Science
LANGUAGES
English and Spanish
"""
MAPPED = {
    "contact": {
        "name": "Jane Doe", "email": "jane@example.com", "phone": None,
        "location": "Springfield, IL", "links": ["github.com/janedoe"],
    },
    "summary": None,
    "roles": [
        {
            "company": "Acme Inc.", "title": "Senior Software Engineer", "location": "Remote",
            "blurb": "Support platform", "dates": "Feb 2023 - Present",
            "bullets": [{
                "claim": "Built retrieval search over support docs, deflected 23% of tier-1 tickets",
                "metrics": ["23% of tier-1 tickets"], "stack": [], "ai_work": True,
            }],
        },
        {
            "company": "Globex Corporation", "title": "Software Engineer", "location": None, "blurb": None,
            "dates": "2019 \u2013 2023",
            "bullets": [{
                "claim": "Led design system migration across 6 teams (Vue)",
                "metrics": ["6 teams"], "stack": ["Vue"], "ai_work": False,
            }],
        },
        {
            "company": "Globex Corporation", "title": "Software Engineer Intern", "location": None, "blurb": None,
            "dates": "2018 \u2013 2019",
            "bullets": [{"claim": "Wrote Storybook stories", "metrics": [], "stack": ["Storybook"], "ai_work": False}],
        },
    ],
    "projects": [],
    "skills": [],
    "education": [{
        "institution": "State University", "degree": "B.S.", "field": "Computer Science", "details": None, "end": None,
    }],
    "certifications": [],
    "languages": ["English", "Spanish"],
    "other": [],
}


@pytest.fixture
def mapped() -> dict:
    return copy.deepcopy(MAPPED)


def test_verbatim_mapping_traces_and_recovers(mapped):
    assert import_pdf.untraced(mapped, SOURCE) == []
    ratio, dropped = import_pdf.recovery(mapped, SOURCE)
    assert dropped == ["English and Spanish"]
    assert ratio >= 0.95


def test_rephrased_claim_untraced(mapped):
    mapped["roles"][0]["bullets"][0]["claim"] = "Built RAG search over support docs"
    assert import_pdf.untraced(mapped, SOURCE) == ["roles[0].bullets[0].claim: 'Built RAG search over support docs'"]


def test_added_legal_identifier_untraced(mapped):
    mapped["roles"][1]["company"] = "Globex Corporation LLC"
    assert import_pdf.untraced(mapped, SOURCE) == ["roles[1].company: 'Globex Corporation LLC'"]


def test_omitted_line_lowers_recovery(mapped):
    mapped["roles"][2]["bullets"] = []
    ratio, dropped = import_pdf.recovery(mapped, SOURCE)
    assert "Wrote Storybook stories" in dropped
    assert ratio < import_pdf.MIN_RECOVERY


def test_build_validates_and_keeps_year_only_dates_as_years(mapped):
    master, assumptions = import_pdf.build(mapped, TODAY)
    assert schema.validate(master) == []
    assert [r["id"] for r in master["roles"]] == ["acme", "globex", "globex-software-engineer-intern"]
    assert master["roles"][0]["start"] == "2023-02" and master["roles"][0]["end"] == schema.PRESENT
    # no invented month: the PDF said 2019 - 2023, so the file says 2019 and 2023
    assert master["roles"][1]["start"] == "2019" and master["roles"][1]["end"] == "2023"
    assert assumptions == []
    assert master["roles"][0]["bullets"][0] == {
        "id": "acme-1",
        "claim": "Built retrieval search over support docs, deflected 23% of tier-1 tickets",
        "metrics": ["23% of tier-1 tickets"],
        "stack": [],
        "ai_work": True,
    }


def test_build_collapses_kept_line_breaks(mapped):
    mapped["summary"] = "Frontend engineer\n  Vue + TypeScript"
    master, _ = import_pdf.build(mapped, TODAY)
    assert master["summary"] == "Frontend engineer Vue + TypeScript"


def test_ai_era_only_where_source_holds_ai_work(mapped):
    master, _ = import_pdf.build(mapped, TODAY)
    assert [r["ai_era"] for r in master["roles"]] == [True, False, False]


def test_future_end_flagged(mapped):
    mapped["roles"][0]["dates"] = "Feb 2023 - Oct 2026"
    _, assumptions = import_pdf.build(mapped, TODAY)
    assert "roles[0].end: 2026-10 after today" in assumptions


def test_duration_in_dates_left_for_hand_edit(mapped):
    mapped["roles"][0]["dates"] = "6 Summers"
    master, assumptions = import_pdf.build(mapped, TODAY)
    assert "roles[0]: dates '6 Summers' not start - end, set by hand" in assumptions
    assert "roles[0].start: missing" in schema.validate(master)


def test_unparseable_endpoint_left_for_hand_edit(mapped):
    mapped["roles"][0]["dates"] = "Spring 2023 - Present"
    master, assumptions = import_pdf.build(mapped, TODAY)
    assert "roles[0].start: unparseable date 'spring 2023', set by hand" in assumptions
    assert master["roles"][0]["end"] == schema.PRESENT


def pdf_with(tmp_path, text: str):
    path = tmp_path / "resume.pdf"
    with pymupdf.open() as doc:
        doc.new_page().insert_text((72, 72), text, fontname="helv")
        doc.save(path)
    return path


def test_extract_strips_bullet_glyphs(tmp_path):
    text = import_pdf.extract(pdf_with(tmp_path, "Jane Doe\n\u2022 Built search"))
    assert "\u2022" not in text and "Built search" in text


def test_extract_rejects_glyph_id_text(tmp_path):
    with pytest.raises(ValueError, match="ToUnicode"):
        import_pdf.extract(pdf_with(tmp_path, "0123 4567 89 ## %% 0123"))


def test_mapped_fixture_matches_answer_schema(mapped):
    assert handoff.violations(mapped, import_pdf.MAPPED_SCHEMA, "answer") == []


def test_all_caps_credential_counts_only_named_headings_skip():
    lines = import_pdf.content_lines("Work Experience:\nSKILLS & ABILITIES\nACTIVE TS/SCI CLEARANCE\nBLS/ACLS CERTIFIED\n")
    assert lines == ["ACTIVE TS/SCI CLEARANCE", "BLS/ACLS CERTIFIED"]


def test_dropped_credential_line_is_reported_and_other_section_traces_it(mapped):
    source = SOURCE + "SECURITY CLEARANCE\nACTIVE TS/SCI CLEARANCE\n"
    assert "ACTIVE TS/SCI CLEARANCE" in import_pdf.recovery(mapped, source)[1]
    mapped["other"] = [{"heading": "SECURITY CLEARANCE", "lines": ["ACTIVE TS/SCI CLEARANCE"]}]
    assert import_pdf.untraced(mapped, source) == []
    assert "ACTIVE TS/SCI CLEARANCE" not in import_pdf.recovery(mapped, source)[1]
    master, _ = import_pdf.build(mapped, TODAY)
    assert master["other"] == [{"heading": "SECURITY CLEARANCE", "lines": ["ACTIVE TS/SCI CLEARANCE"]}]
    assert schema.validate(master) == []


def test_every_left_out_line_is_printed_plainly(capsys):
    import_pdf.left_out(["Volunteer, Riverside Food Bank", "English and Spanish"])
    out = capsys.readouterr().out
    assert "2 line(s) of the PDF are not fully in the resume details" in out
    assert "  - Volunteer, Riverside Food Bank\n" in out and "  - English and Spanish\n" in out
    import_pdf.left_out([])
    assert "nothing" in capsys.readouterr().out


def test_undated_project_and_year_only_certificate_build_as_written(mapped):
    mapped["projects"] = [{"name": "Garden planner", "dates": None, "bullets": [
        {"claim": "Wrote Storybook stories", "metrics": [], "stack": [], "ai_work": False}]}]
    mapped["certifications"] = [{"name": "First Aid", "issuer": None, "date": "2021"}]
    master, _ = import_pdf.build(mapped, TODAY)
    assert "start" not in master["projects"][0]
    assert master["certifications"] == [{"name": "First Aid", "date": "2021"}]
    assert schema.validate(master) == []


def test_roles_out_of_order_are_sorted_newest_first_and_said(mapped):
    mapped["roles"].reverse()
    master, assumptions = import_pdf.build(mapped, TODAY)
    assert [r["title"] for r in master["roles"]] == [
        "Senior Software Engineer", "Software Engineer", "Software Engineer Intern"]
    assert "the PDF listed jobs out of date order - they are now newest first" in assumptions
    assert schema.validate(master) == []
