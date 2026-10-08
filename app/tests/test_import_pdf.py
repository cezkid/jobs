import copy
from collections import Counter
from datetime import date
from pathlib import Path

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


@pytest.mark.parametrize("dates, start, end", [
    ("10/24 - Present", "2024-10", schema.PRESENT),
    ("07/07 - 06/13", "2007-07", "2013-06"),
    ("03/2019 - 11/2021", "2019-03", "2021-11"),
    ("06/98 - 12/99", "1998-06", "1999-12"),
])
def test_word_numeric_dates_parse(dates, start, end):
    assumptions = []
    assert import_pdf.parse_range(dates, "roles[0]", TODAY, assumptions) == {"start": start, "end": end}
    assert assumptions == []


def test_two_digit_year_turns_1900s_only_past_next_year():
    # TODAY is 2026: "27" can be a start date next year, "28" can't => 1928
    assert import_pdf.endpoint("01/27", TODAY) == "2027-01"
    assert import_pdf.endpoint("01/28", TODAY) == "1928-01"


@pytest.mark.parametrize("bad", ["13/20", "00/2020"])
def test_numeric_month_out_of_range_left_for_hand_edit(bad):
    assumptions = []
    parsed = import_pdf.parse_range(f"{bad} - Present", "roles[0]", TODAY, assumptions)
    assert parsed == {"start": None, "end": schema.PRESENT}
    assert assumptions == [f"roles[0].start: unparseable date {bad!r}, set by hand"]


def pdf_with(tmp_path, text: str):
    path = tmp_path / "resume.pdf"
    with pymupdf.open() as doc:
        doc.new_page().insert_text((72, 72), text, fontname="helv")
        doc.save(path)
    return path


def test_extract_strips_bullet_glyphs(tmp_path):
    text = import_pdf.extract(pdf_with(tmp_path, "Jane Doe\n\u2022 Built search"))
    assert "\u2022" not in text and "Built search" in text


@pytest.mark.parametrize("line", ["o\tLed hiring", "o Led hiring", "  o Led hiring", "\uf0a7 Led hiring", "\uf0b7Led hiring"])
def test_word_bullets_stripped(line):
    assert import_pdf.LINE_BULLET.sub("", line).strip() == "Led hiring"


@pytest.mark.parametrize("line", ["onboarding new hires", "owned the roadmap", "Led a team o five"])
def test_words_starting_or_holding_o_untouched(line):
    assert import_pdf.LINE_BULLET.sub("", line) == line


def test_extract_strips_word_o_bullet(tmp_path):
    text = import_pdf.extract(pdf_with(tmp_path, "Jane Doe\no Led hiring\nonboarding new hires"))
    assert text.split("\n")[1].strip() == "Led hiring" and "onboarding new hires" in text


def test_extract_rejects_glyph_id_text(tmp_path):
    with pytest.raises(ValueError, match="ToUnicode"):
        import_pdf.extract(pdf_with(tmp_path, "0123 4567 89 ## %% 0123"))


def test_mapped_fixture_matches_answer_schema(mapped):
    assert handoff.violations(mapped, import_pdf.MAPPED_SCHEMA, "answer") == []


def test_all_caps_credential_counts_only_named_headings_skip():
    lines = import_pdf.content_lines("Work Experience:\nSKILLS & ABILITIES\nACTIVE TS/SCI CLEARANCE\nBLS/ACLS CERTIFIED\n")
    assert lines == ["ACTIVE TS/SCI CLEARANCE", "BLS/ACLS CERTIFIED"]


@pytest.mark.parametrize("line", [
    "EDUCATION & PROFESSIONAL DEVELOPMENT", "Education and Professional Development:", "PROFESSIONAL DEVELOPMENT",
])
def test_professional_development_heading_is_skipped(line):
    assert import_pdf.content_lines(f"{line}\nLed professional development for 40 staff\n") == [
        "Led professional development for 40 staff"]


def test_copied_skill_group_label_counts_as_kept(mapped):
    source = "SKILLS\nAgile Practice - Scrum, Kanban\n"
    mapped["skills"] = [{"group": "Agile Practice", "items": ["Scrum", "Kanban"]}]
    assert import_pdf.recovery(mapped, source) == (1.0, [])
    assert all(".group" not in path for path, _ in import_pdf.traced_strings(mapped))


def test_made_up_skill_group_label_stays_untraced(mapped):
    source = SOURCE + "SKILLS\nScrum, Kanban\n"
    mapped["skills"] = [{"group": "Methods", "items": ["Scrum", "Kanban"]}]
    assert import_pdf.untraced(mapped, source) == []
    assert "Scrum, Kanban" not in import_pdf.recovery(mapped, source)[1]


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
    assert "2 line(s) of the resume file are not fully in the resume details" in out
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
    assert "the resume file listed jobs out of date order - they are now newest first" in assumptions
    assert schema.validate(master) == []


# Word export shape (plan-8yi): Symbol bullet byte B7 (A7 for the square) carries a ToUnicode map
# to private-use U+F0B7 / U+F0A7, 2nd level is a plain "o", dates MM/YY or MM/YYYY
WORD_SOURCE = """Alex Rivera
Riverton, OH | alex.rivera@example.com | (555) 010-0199
PROFESSIONAL SUMMARY
Operations lead for regional freight and warehouse teams.
PROFESSIONAL EXPERIENCE
Northwind Logistics\tColumbus, OH
Operations Manager\t10/24 - Present
\xb7\tCut dock-to-stock time 18% by redesigning the receiving flow
o\tTrained 12 new leads on the warehouse system
o Ran weekly safety reviews across 3 shifts
Contoso Freight\tDayton, OH
Shift Supervisor\t03/2019 - 09/2024
\xa7\tScheduled 40 drivers across two depots
Fabrikam Supply\tAkron, OH
Inventory Clerk\t07/07 - 06/13
\xb7\tCounted cycle stock for 2,000 bins each quarter
SKILLS
Agile Practice - Scrum, Kanban
Warehouse Systems - SAP EWM, Manhattan WMS
EDUCATION & PROFESSIONAL DEVELOPMENT
Ohio State University
B.S. Industrial Engineering\t05/2007
Lean Six Sigma Green Belt, ASQ\t03/2019
"""
WORD_MAPPED = {
    "contact": {
        "name": "Alex Rivera", "email": "alex.rivera@example.com", "phone": "(555) 010-0199",
        "location": "Riverton, OH", "links": [],
    },
    "summary": "Operations lead for regional freight and warehouse teams.",
    "roles": [
        {
            "company": "Northwind Logistics", "title": "Operations Manager", "location": "Columbus, OH", "blurb": None,
            "dates": "10/24 - Present",
            "bullets": [
                {"claim": "Cut dock-to-stock time 18% by redesigning the receiving flow",
                 "metrics": ["18%"], "stack": [], "ai_work": False},
                {"claim": "Trained 12 new leads on the warehouse system", "metrics": ["12 new leads"], "stack": [],
                 "ai_work": False},
                {"claim": "Ran weekly safety reviews across 3 shifts", "metrics": ["3 shifts"], "stack": [],
                 "ai_work": False},
            ],
        },
        {
            "company": "Contoso Freight", "title": "Shift Supervisor", "location": "Dayton, OH", "blurb": None,
            "dates": "03/2019 - 09/2024",
            "bullets": [{"claim": "Scheduled 40 drivers across two depots", "metrics": ["40 drivers"], "stack": [],
                         "ai_work": False}],
        },
        {
            "company": "Fabrikam Supply", "title": "Inventory Clerk", "location": "Akron, OH", "blurb": None,
            "dates": "07/07 - 06/13",
            "bullets": [{"claim": "Counted cycle stock for 2,000 bins each quarter", "metrics": ["2,000 bins"],
                         "stack": [], "ai_work": False}],
        },
    ],
    "projects": [],
    "skills": [
        {"group": "Agile Practice", "items": ["Scrum", "Kanban"]},
        {"group": "Warehouse Systems", "items": ["SAP EWM", "Manhattan WMS"]},
    ],
    "education": [{
        "institution": "Ohio State University", "degree": "B.S.", "field": "Industrial Engineering", "details": None,
        "end": "05/2007",
    }],
    "certifications": [{"name": "Lean Six Sigma Green Belt", "issuer": "ASQ", "date": "03/2019"}],
    "languages": [],
    "other": [],
}
SYMBOL_TO_UNICODE = b"""/CIDInit /ProcSet findresource begin 12 dict begin begincmap
/CMapName /Symbol-UCS def /CMapType 2 def
1 begincodespacerange <00> <FF> endcodespacerange
2 beginbfchar <B7> <F0B7> <A7> <F0A7> endbfchar
endcmap CMapName currentdict /CMap defineresource pop end end"""


def word_pdf(tmp_path):
    path = tmp_path / "word-resume.pdf"
    with pymupdf.open() as doc:
        page = doc.new_page()
        page.insert_text((72, 72), WORD_SOURCE, fontname="helv", fontsize=10)
        for font_xref, *_ in page.get_fonts():
            cmap = doc.get_new_xref()
            doc.update_object(cmap, "<<>>")
            doc.update_stream(cmap, SYMBOL_TO_UNICODE)
            doc.xref_set_key(font_xref, "ToUnicode", f"{cmap} 0 R")
        doc.save(path)
    return path


def test_word_resume_imports_whole_and_dated(tmp_path):
    pdf = word_pdf(tmp_path)
    with pymupdf.open(pdf) as doc:
        raw = doc[0].get_text()
    # reads back the way Word's PDF does, so the test proves the strip, not a stand-in glyph
    assert "\uf0b7" in raw and "\uf0a7" in raw and "\no\t" in raw
    source = import_pdf.extract(pdf)
    assert "\uf0b7" not in source and "\uf0a7" not in source
    mapped = copy.deepcopy(WORD_MAPPED)
    assert handoff.violations(mapped, import_pdf.MAPPED_SCHEMA, "answer") == []
    assert import_pdf.untraced(mapped, source) == []
    ratio, dropped = import_pdf.recovery(mapped, source)
    assert dropped == []
    assert ratio >= import_pdf.MIN_RECOVERY
    master, assumptions = import_pdf.build(mapped, TODAY)
    assert assumptions == []
    assert [(r["start"], r["end"]) for r in master["roles"]] == [
        ("2024-10", schema.PRESENT), ("2019-03", "2024-09"), ("2007-07", "2013-06")]
    assert master["education"][0]["end"] == "2007-05"
    assert master["certifications"][0]["date"] == "2019-03"
    assert schema.validate(master) == []


@pytest.mark.parametrize("text,start,end", [
    ("2021-03 - 2023-05", "2021-03", "2023-05"),
    ("2021-03 to present", "2021-03", "present"),
    ("Mar 2020 - Ongoing", "2020-03", "present"),
    ("Jan 2019 - Today", "2019-01", "present"),
    ("2018 to date", "2018", "present"),
    ("Jun 2017 - till date", "2017-06", "present"),
    ("2019-2021", "2019", "2021"),
])
def test_iso_and_word_endpoints_parse(text, start, end):
    """Each used to fall back to 'set by hand': ISO months split on their own hyphen."""
    assumptions = []
    got = import_pdf.parse_range(text, "roles[0]", date(2026, 10, 1), assumptions)
    assert (got, assumptions) == ({"start": start, "end": end}, [])


def word_docx(path, header: list[str], body: list[str]):
    """Made-up Word resume: contact lines in the page header, as Word templates put them."""
    import zipfile
    from xml.sax.saxutils import escape
    ns = 'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"'

    def paras(lines):
        return "".join("<w:p>" + "<w:r><w:tab/></w:r>".join(
            f'<w:r><w:t xml:space="preserve">{escape(cell)}</w:t></w:r>' for cell in line.split("\t")) + "</w:p>"
            for line in lines)
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("word/document.xml", f"<w:document {ns}><w:body>{paras(body)}</w:body></w:document>")
        z.writestr("word/header1.xml", f"<w:hdr {ns}>{paras(header)}</w:hdr>")
    return path


def test_word_docx_resume_imports_whole_and_dated(tmp_path):
    lines = [line.lstrip("\xb7\xa7o \t") for line in WORD_SOURCE.splitlines()]
    path = word_docx(tmp_path / "resume.docx", lines[:2], lines[2:])
    source = import_pdf.extract(path)
    assert source.splitlines()[:2] == ["Alex Rivera", "Riverton, OH | alex.rivera@example.com | (555) 010-0199"]
    mapped = copy.deepcopy(WORD_MAPPED)
    assert import_pdf.untraced(mapped, source) == []
    ratio, dropped = import_pdf.recovery(mapped, source)
    assert dropped == [] and ratio >= import_pdf.MIN_RECOVERY
    master, assumptions = import_pdf.build(mapped, TODAY)
    assert assumptions == [] and schema.validate(master) == []


@pytest.fixture
def resume_dir(tmp_path, monkeypatch):
    config = {"resume": {"input_pdf": "My Resume/Original resume.pdf", "master": "My Resume/Resume details.yml"}}
    monkeypatch.setattr(import_pdf.cfg, "resume_path", lambda c, key: tmp_path / c["resume"][key])
    monkeypatch.setattr(import_pdf.cfg, "DATA", tmp_path / ".data")
    monkeypatch.setattr(import_pdf, "TASK", tmp_path / ".data" / "resume-task.md")
    monkeypatch.setattr(import_pdf, "ANSWER", tmp_path / ".data" / "resume-mapped.json")
    return config, tmp_path


def test_prepare_copies_word_file_and_finish_reads_that_same_file(resume_dir):
    config, root = resume_dir
    lines = [line.lstrip("\xb7\xa7o \t") for line in WORD_SOURCE.splitlines()]
    dropped = word_docx(root / "Alex resume.docx", lines[:2], lines[2:])
    # an older PDF stays where it is, untouched, and is not what finish reads
    (root / "My Resume").mkdir()
    (root / "My Resume" / "Original resume.pdf").write_bytes(b"old")
    import_pdf.prepare(config, dropped, force=False)
    kept = root / "My Resume" / "Original resume.docx"
    assert kept.exists() and (root / "My Resume" / "Original resume.pdf").read_bytes() == b"old"
    assert import_pdf.source_file(config) == kept
    task = import_pdf.TASK.read_text(encoding="utf-8")
    assert "Northwind Logistics" in task and "<w:" not in task
    # finish checks against the text handed out, even once the file changes under it
    kept.write_bytes(b"changed")
    assert "Northwind Logistics" in import_pdf.recorded(config)[1]


def test_prepare_refuses_old_word_file_in_plain_words(resume_dir, monkeypatch):
    config, root = resume_dir
    monkeypatch.setattr(import_pdf.word.shutil, "which", lambda name: None)
    old = root / "Resume.doc"
    old.write_bytes(b"\xd0\xcf\x11\xe0")
    with pytest.raises(SystemExit) as stop:
        import_pdf.prepare(config, old, force=False)
    assert "older Word file" in str(stop.value) and "save a copy as Word Document (.docx) or PDF" in str(stop.value)
    assert not (root / "My Resume").exists()


def test_finish_without_a_record_reads_the_pdf(resume_dir):
    config, root = resume_dir
    assert import_pdf.source_file(config) == root / "My Resume" / "Original resume.pdf"


def test_heading_cell_on_a_tab_joined_line_is_skipped_too():
    assert import_pdf.content_lines("EXPERIENCE\tNorthwind Logistics\nSKILLS\n") == ["Northwind Logistics"]


# Made by Microsoft Word for Mac 16.113 (plan-xku.2): fake data, re-saved by Word + its PDF
# (Quartz print path). Remake: app/docs/resume/word-fixture/.
WORD_MADE = Path(__file__).parent / "fixtures" / "word"


def bullet(claim, *metrics):
    return {"claim": claim, "metrics": list(metrics), "stack": [], "ai_work": False}


WORD_MADE_MAPPED = {
    "contact": {"name": "Alex Rivera", "email": "alex.rivera@example.com", "phone": "(555) 010-0199",
                "location": "Riverton, OH", "links": ["linkedin.com/in/alex-rivera-example"]},
    "summary": "Operations lead for regional freight and warehouse teams, 14 years across receiving, inventory and dispatch.",
    "roles": [
        {"company": "Northwind Logistics", "title": "Operations Manager", "location": "Columbus, OH", "blurb": None,
         "dates": "10/2024 - Present", "bullets": [
             bullet("Cut dock-to-stock time 18% by redesigning the receiving flow", "18%"),
             bullet("Trained 12 new leads on the warehouse system", "12 new leads"),
             bullet("Ran weekly safety reviews across 3 shifts", "3 shifts"),
             bullet("Lowered overtime spend 9% in the first year", "9%")]},
        {"company": "Contoso Freight", "title": "Shift Supervisor", "location": "Dayton, OH", "blurb": None,
         "dates": "03/2019 - 09/2024", "bullets": [
             bullet("Scheduled 40 drivers across two depots", "40 drivers"),
             bullet("Kept on-time dispatch at 96% through two peak seasons", "96%")]},
        {"company": "Fabrikam Supply", "title": "Inventory Clerk", "location": "Akron, OH", "blurb": None,
         "dates": "07/2007 - 06/2013", "bullets": [bullet("Counted cycle stock for 2,000 bins each quarter", "2,000 bins")]},
    ],
    "projects": [],
    "skills": [{"group": "Warehouse Systems", "items": ["SAP EWM", "Manhattan WMS"]},
               {"group": "Lean Practice", "items": ["5S", "Kaizen", "Value Stream Mapping"]}],
    "education": [{"institution": "Ohio State University", "degree": "B.S.", "field": "Industrial Engineering",
                   "details": None, "end": "05/2007"}],
    "certifications": [{"name": "Lean Six Sigma Green Belt", "issuer": "ASQ", "date": "03/2019"},
                       {"name": "OSHA 30-Hour General Industry", "issuer": None, "date": "2021"}],
    "languages": [],
    "other": [],
}


def words(text):
    return Counter(w for line in text.splitlines() for w in import_pdf.WORD.findall(import_pdf.normalize(line)))


def test_word_made_fixture_is_words_own_save():
    import zipfile
    with zipfile.ZipFile(WORD_MADE / "word-resume.docx") as z:
        assert b"<Application>Microsoft Office Word</Application>" in z.read("docProps/app.xml")
        assert b"w:rsidR=" in z.read("word/document.xml") and "word/header1.xml" in z.namelist()
        assert b"CEZ Job Finder test" in z.read("docProps/core.xml")


@pytest.mark.parametrize("name", ["word-resume.docx", "word-resume.pdf"])
def test_word_made_resume_passes_the_import_gates_as_docx_and_as_its_pdf(name):
    source = import_pdf.extract(WORD_MADE / name)
    mapped = copy.deepcopy(WORD_MADE_MAPPED)
    assert handoff.violations(mapped, import_pdf.MAPPED_SCHEMA, "answer") == []
    assert import_pdf.untraced(mapped, source) == []
    ratio, dropped = import_pdf.recovery(mapped, source)
    assert dropped == [] and ratio >= import_pdf.MIN_RECOVERY
    master, assumptions = import_pdf.build(mapped, TODAY)
    assert assumptions == [] and schema.validate(master) == []


def test_word_made_docx_and_its_pdf_read_the_same_words():
    docx = import_pdf.extract(WORD_MADE / "word-resume.docx")
    assert docx.splitlines()[:2] == [
        "Alex Rivera", "Riverton, OH | alex.rivera@example.com | (555) 010-0199 | linkedin.com/in/alex-rivera-example"]
    assert docx.count("Lean Six Sigma Green Belt") == 1
    assert words(docx) == words(import_pdf.extract(WORD_MADE / "word-resume.pdf"))


def test_text_a_box_clips_is_in_the_docx_not_its_pdf():
    """Word hides a text box's overflow on the page; the file still holds it. The Word reader keeps
    it (the user's own line) - a PDF of the same file loses it without a trace."""
    docx = import_pdf.extract(WORD_MADE / "word-resume-clipped.docx")
    pdf = import_pdf.extract(WORD_MADE / "word-resume-clipped.pdf")
    assert "OSHA 30-Hour General Industry, 2021" in docx and "OSHA" not in pdf
    assert words(docx) - words(pdf) == Counter({"osha": 1, "30": 1, "hour": 1, "general": 1, "industry": 1, "2021": 1})


STUDENT_SOURCE = """Sam Rivera
Columbus, OH | sam.rivera@example.com
EDUCATION
The Ohio State University
B.S. Statistics, Dean's List
Aug 2023 - Expected May 2027
GPA: 3.62/4.00
Relevant Coursework: Regression Analysis, Database Systems
LEADERSHIP & ACTIVITIES
Black Student Union
Treasurer    Sep 2024 - Present
Managed a $12,000 budget for 30 campus events a year
"""


def student_mapped() -> dict:
    return {
        "contact": {"name": "Sam Rivera", "email": "sam.rivera@example.com", "phone": None, "location": "Columbus, OH",
                    "links": []},
        "summary": None, "roles": [], "skills": [], "certifications": [], "languages": [], "other": [],
        "projects": [{"name": "Black Student Union", "role": "Treasurer", "section": "LEADERSHIP & ACTIVITIES",
                      "dates": "Sep 2024 - Present", "bullets": [{
                          "claim": "Managed a $12,000 budget for 30 campus events a year",
                          "metrics": ["$12,000", "30 campus events"], "stack": [], "ai_work": False}]}],
        "education": [{"institution": "The Ohio State University", "degree": "B.S.", "field": "Statistics",
                       "details": "Dean's List", "start": "Aug 2023", "end": "Expected May 2027", "gpa": "3.62/4.00",
                       "coursework": ["Regression Analysis", "Database Systems"]}],
    }


def test_student_resume_imports_whole_with_expected_date_gpa_courses_and_club():
    mapped = student_mapped()
    assert import_pdf.untraced(mapped, STUDENT_SOURCE) == []
    ratio, dropped = import_pdf.recovery(mapped, STUDENT_SOURCE)
    assert ratio >= import_pdf.MIN_RECOVERY and dropped == []
    master, assumptions = import_pdf.build(mapped, date(2026, 10, 7))
    assert assumptions == [] and schema.validate(master) == []
    assert master["education"][0] | {} == {
        "institution": "The Ohio State University", "degree": "B.S.", "field": "Statistics", "details": "Dean's List",
        "gpa": "3.62/4.00", "coursework": ["Regression Analysis", "Database Systems"], "start": "2023-08",
        "end": "2027-05", "expected": True}
    club = master["projects"][0]
    assert (club["name"], club["role"], club["section"], club["start"]) == \
        ("Black Student Union", "Treasurer", "LEADERSHIP & ACTIVITIES", "2024-09")


@pytest.mark.parametrize("text, end, expected", [
    ("Expected May 2027", "2027-05", True), ("May 2027 (expected)", "2027-05", True), ("Class of 2027", "2027", True),
    ("Class of 2025", "2025", None), ("Expected May 2025", "2025-05", True), ("May 2027", "2027-05", True)])
def test_graduation_words_parse_and_say_whether_still_studying(text, end, expected):
    mapped = student_mapped()
    mapped["education"][0].update(start=None, end=text)
    master, assumptions = import_pdf.build(mapped, date(2026, 10, 7))
    school = master["education"][0]
    assert (school["end"], school.get("expected")) == (end, expected)
    assert assumptions == []


def test_an_answer_without_the_student_fields_still_checks(mapped):
    import jsonschema
    jsonschema.validate(mapped, import_pdf.MAPPED_SCHEMA)
