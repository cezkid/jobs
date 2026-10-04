"""app/web/parser_test.py: corpus + scorer behind the resume parser test (METHOD.md in its study folder).

PDFs made here go to tmp_path; the readers outside the project (parser_read.py) are never run by the tests.
"""

import csv
import importlib.util
import io
import re

import pymupdf

import cfg

spec = importlib.util.spec_from_file_location("parser_test", cfg.APP / "web" / "parser_test.py")
pt = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pt)

MINI = {
    "name": "Your Name", "email": "your.name@example.com", "phone": "(555) 010-0199", "location": "City, State",
    "summary": "Analyst who builds weekly reports.",
    "jobs": [{"title": "Operations Analyst", "employer": "Company A", "dates": "Mar 2021 – Present",
              "bullets": ["Built a weekly staffing report for managers.", "Cut late deliveries by half."]}],
    "education": [{"degree": "Bachelor of Science", "school": "University A", "dates": "2016"}],
    "skills": ["Tools: Excel, SQL", "Languages: English, Spanish"],
}
T = pt.truth(MINI)


def plain(t=T):
    return "\n".join(b["text"] for b in t["blocks"])


def two_column_pdf(tmp_path, row_by_row: bool):
    """Name, contact + summary across the top; experience left, education + skills right. row_by_row: the file
    draws left and right lines in turns (as some templates do) - read in file order, the columns interleave."""
    blocks = T["blocks"]
    top = [b["text"] for b in blocks if b["section"] in ("name", "contact", "summary")]
    left = [b["text"] for b in blocks if b["section"] == "experience"]
    right = [b["text"] for b in blocks if b["section"] in ("education", "skills")]
    doc = pymupdf.open()
    page = doc.new_page()
    y = 50
    for line in top:
        page.insert_text((40, y), line, fontsize=8)
        y += 14
    y += 10
    if row_by_row:
        for i in range(max(len(left), len(right))):
            if i < len(left):
                page.insert_text((40, y + 14 * i), left[i], fontsize=8)
            if i < len(right):
                page.insert_text((360, y + 14 * i), right[i], fontsize=8)
    else:
        for col, x in ((left, 40), (right, 360)):
            for i, line in enumerate(col):
                page.insert_text((x, y + 14 * i), line, fontsize=8)
    path = tmp_path / "two.pdf"
    doc.save(path)
    with pymupdf.open(path) as d:
        return d[0].get_text("text")


def test_the_truth_itself_scores_clean():
    row = pt.score(T, plain())
    assert not row["broke"], row["broke_because"]
    assert row["blocks_not_found"] == 0 and row["page_order"] == 1.0 and row["job_headers_together"] == 1


def test_two_columns_read_in_turns_are_scored_as_wrong(tmp_path):
    row = pt.score(T, two_column_pdf(tmp_path, row_by_row=True))
    assert row["broke"]
    assert row["sections_mixed"] > 0
    assert "sections mixed" in row["broke_because"]
    assert row["lost_words"] == 0  # every word is there; only the order is wrong


def test_two_columns_read_column_by_column_pass(tmp_path):
    row = pt.score(T, two_column_pdf(tmp_path, row_by_row=False))
    assert not row["broke"], row["broke_because"]


def test_bullets_swapped_inside_a_section_are_out_of_order():
    lines = plain().splitlines()
    i = lines.index("Built a weekly staffing report for managers.")
    lines[i], lines[i + 1] = lines[i + 1], lines[i]
    row = pt.score(T, "\n".join(lines))
    assert row["within_section_order"] < 1 and row["sections_mixed"] == 0 and row["broke"]


def test_split_and_merged_words_are_counted_not_lost():
    text = plain().replace("Experience", "EXP E R I ENC E").replace("Education\nBachelor", "EducationBachelor")
    row = pt.score(T, text)
    assert (row["split_words"], row["merged_words"], row["lost_words"]) == (1, 1, 0)
    assert row["broke"]


def test_lost_text_and_job_header_over_two_lines():
    text = plain().replace("Operations Analyst | Company A | Mar 2021 – Present", "Mar 2021 – Present\nOperations Analyst | Company A")
    text = text.replace("Cut late deliveries by half.\n", "")
    row = pt.score(T, text)
    assert row["job_headers_together"] == 0
    assert row["lost_words"] == 5
    assert "job headers together 0/1" in row["broke_because"]


def test_name_lower_down_and_a_broken_email():
    lines = plain().splitlines()
    text = "\n".join(lines[1:] + lines[:1]).replace("your.name@example.com", "your.name@ example.com")
    row = pt.score(T, text)
    assert (row["name_first_line"], row["name_found"], row["email"], row["phone"]) == (False, True, False, True)


def test_a_missing_name_never_borrows_the_email():
    row = pt.score(T, "\n".join(plain().splitlines()[1:]))
    assert row["name_found"] is False and row["blocks_not_found"] == 1


def test_results_are_one_row_per_layout_and_reader_and_repeat_exactly():
    t = pt.truth(pt.load_facts())
    readings = {"readers": {r: {layout: plain(t) for layout in pt.LAYOUTS} for r in ("b", "a")}}
    outs = []
    for _ in range(2):
        buf = io.StringIO()
        pt.results(t, readings, buf)
        outs.append(buf.getvalue())
    assert outs[0] == outs[1]
    rows = list(csv.DictReader(io.StringIO(outs[0])))
    assert [(r["layout"], r["reader"]) for r in rows[:2]] == [("one-column", "a"), ("one-column", "b")]
    assert len(rows) == 2 * len(pt.LAYOUTS) and all(r["broke"] == "false" for r in rows)


def test_corpus_is_fresh_and_placeholder_only():
    # build in memory, compare with the committed files: stale or a non-repeatable byte = listed
    assert pt.build(check=True) == []
    assert len(pt.LAYOUTS) >= 6
    facts = pt.load_facts()
    assert facts["name"] == "Your Name" and facts["email"].endswith("@example.com")
    assert all(re.fullmatch(r"Company [A-Z]", j["employer"]) for j in facts["jobs"])
    assert all(re.fullmatch(r"University [A-Z]", e["school"]) for e in facts["education"])
    keys = [tuple(pt.block_key(b)) for b in pt.truth(facts)["blocks"]]
    assert len(keys) == len(set(keys))  # every block's opening is its own


def test_words_merged_across_columns_are_merged_not_lost():
    # a sidebar line read onto the end of a job header: "PresentCity" - truth words that are not neighbours
    text = plain().replace("Mar 2021 – Present", "Mar 2021 – PresentCity,").replace("City, State\n", "State\n")
    row = pt.score(T, text)
    assert (row["merged_words"], row["lost_words"]) == (1, 0)


def test_dates_ahead_of_the_title_on_the_same_line_are_kept_together():
    # a table layout: dates in the left cell, title + employer in the right, one row
    text = plain().replace("Operations Analyst | Company A | Mar 2021 – Present", "Mar 2021 – Present  Operations Analyst | Company A")
    row = pt.score(T, text)
    assert not row["broke"], row["broke_because"]
    assert row["job_headers_together"] == 1 and row["blocks_not_found"] == 0


def test_data_page_file_is_the_study_results():
    # the data page publishes <name>.csv next to its page; it must be the study's own results, byte for byte
    published = cfg.APP / "web" / "research" / "resume-parser-test-2026-10.csv"
    assert published.read_bytes() == (pt.STUDY / "results.csv").read_bytes()
