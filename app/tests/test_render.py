import copy

import pymupdf
import pytest
import typst

import cfg
from resume import measure, render, schema, tailor, typeface

EXAMPLE = cfg.APP / "resume" / "master.example.yml"


@pytest.fixture
def master() -> dict:
    return copy.deepcopy(schema.load(EXAMPLE))


def failed(results) -> dict[str, str]:
    return {name: detail for name, ok, detail in results if not ok}


def test_page_model_orders_sections_and_labels_dates(master):
    model = render.page_model(master)
    assert [s["title"] for s in model["sections"]] == ["Experience", "Projects", "Skills", "Education", "Languages"]
    acme = model["sections"][0]["entries"][0]
    assert acme["subline"] == "Feb 2023 - Present | Remote | Customer support platform | acme.com"
    assert acme["bullets"][0] == master["roles"][0]["bullets"][0]["claim"]
    assert model["sections"][3]["entries"] == [{"heading": "State University", "bullets": [],
                                                "subline": "Bachelor of Science, Computer Science | Minor in Mathematics | 2019"}]
    assert render.file_name(model) == "Jane_Doe_Resume.pdf"


def test_example_master_passes_every_gate(master, tmp_path):
    _, results = render.render(render.page_model(master), tmp_path, budget=False)
    assert failed(results) == {}


def test_markup_characters_render_literally(master, tmp_path):
    master["roles"][0]["bullets"][0]["claim"] = "Shipped #flags $cost_model *bold* @team <tag> [x] under 5ms"
    path, results = render.render(render.page_model(master), tmp_path, budget=False)
    assert failed(results) == {}
    assert "#flags $cost_model *bold* @team <tag> [x]" in render.pdf_text(path, sort=True)


def test_prose_block_over_cap_fails(master, tmp_path):
    master["summary"] = " ".join(f"word{i}" for i in range(render.MAX_BLOCK_WORDS + 1))
    _, results = render.render(render.page_model(master), tmp_path, budget=False)
    assert set(failed(results)) == {"no-prose-block"}


def test_unscrubbed_typst_output_fails_metadata(master, tmp_path):
    model = render.page_model(master)
    path = tmp_path / render.file_name(model)
    path.write_bytes(typst.compile(
        str(render.TEMPLATE), font_paths=[str(typeface.folder(typeface.DEFAULT))], ignore_system_fonts=True,
        sys_inputs={"data": render.json.dumps(render.with_page(model))},
    ))
    assert "creator" in failed(render.check(path, model, budget=False))["metadata-wiped"]


def test_budget_enforced_only_when_asked(master, tmp_path):
    _, results = render.render(render.page_model(master), tmp_path, budget=True)
    assert set(failed(results)) == {"budget"}


def fill_one_page(master: dict, tmp_path) -> tuple[list, int]:
    """Add one-line bullets until the page is three-quarters full or more, still one page."""
    n = 0
    while True:
        model = render.page_model(master)
        path, results = render.render(model, tmp_path, budget=True)
        with pymupdf.open(path) as doc:
            used = render.pages_used(doc)
        if used >= 0.85:
            assert used <= 1, "overshot onto a second page"
            return results, len(render.tokens(render.pdf_text(path, sort=True)))
        n += 1
        master["roles"][0]["bullets"].append({"id": f"acme-{n}", "claim": f"Shipped ledger export tooling for {n} regional payment teams in Vue"})


def test_one_page_resume_mostly_full_passes_budget(master, tmp_path):
    # the old fixed floor of 500 words sat above a full page (378 in Caladea): every one-page
    # resume failed, however right one page was for the career on it
    results, words = fill_one_page(master, tmp_path)
    assert words < 500
    assert "budget" not in failed(results), failed(results)


def test_one_page_window_is_a_share_of_the_page_not_a_fixed_count():
    assert render.word_windows(378, 1.0) == [(284, 378), (605, 756)]
    assert render.word_windows(350, 0.9)[0] == (292, 388)


def test_facts_too_thin_for_any_window_report_never_fail(master, tmp_path):
    model = render.page_model(master)
    words = sum(len(render.tokens(t)) for t in render.page_strings(model))
    _, results = render.render(model, tmp_path, budget=True, available=words)
    assert "budget" not in failed(results)
    assert "never padded" in {n: d for n, _, d in results}["budget (info)"]


def test_jr_in_a_name_or_employer_is_not_an_abbreviated_title(master, tmp_path):
    master["contact"]["name"] = "Robert Hayes Jr."
    master["roles"][0]["company"] = "Martin Luther King Jr. Hospital"
    _, results = render.render(render.page_model(master), tmp_path, budget=False)
    assert failed(results) == {}
    model = render.page_model(master)
    model["sections"][0]["entries"][0]["heading"] = "Sr. Software Engineer"
    _, results = render.render(model, tmp_path, budget=False)
    assert "no-abbreviated-title" in failed(results)


def stub_bullet() -> str:
    """Runs past one line, then leaves two words alone on the second."""
    return "Shipped " + "payment reconciliation and ledger export tooling " * 2 + "across two teams"


def test_stub_line_fails_line_fill(master, tmp_path):
    master["roles"][0]["bullets"][0]["claim"] = stub_bullet()
    path, results = render.render(render.page_model(master), tmp_path, budget=True)
    with pymupdf.open(path) as doc:
        stub = next(r for r in render.runts(doc, render.page_model(master)) if "two teams" in r["text"])
    assert stub["fill"] < render.MIN_LINE_FILL and stub["fixable"]
    # detail names the text and both ways out, so the writer never has to guess
    detail = failed(results)["line-fill"]
    assert stub["text"] in detail and f"cut {stub['cut']}" in detail and f"add ~{stub['add']}" in detail


def test_add_advice_aims_at_a_filled_row_not_at_the_floor(master, tmp_path, monkeypatch):
    """Worked back from MIN_LINE_FILL, the advice on a 39%-full row read "add ~1" - true, and
    useless: one character clears the gate and leaves 60% of the row empty."""
    master["roles"][0]["bullets"][0]["claim"] = stub_bullet()
    model = render.page_model(master)
    path, _ = render.render(model, tmp_path, budget=False)

    def asked(target: float) -> dict:
        monkeypatch.setattr(render, "TARGET_LINE_FILL", target)
        with pymupdf.open(path) as doc:
            return next(r for r in render.runts(doc, model) if "two teams" in r["text"])

    target, floor = render.TARGET_LINE_FILL, render.MIN_LINE_FILL  # monkeypatch moves them
    here = asked(target)["fill"]
    assert asked(here)["add"] <= 1, "aiming where the line already sits should ask for nothing"
    assert asked(floor)["add"] < asked(target)["add"]


def test_fill_target_sits_above_the_floor_and_short_of_the_edge():
    # short of the edge on purpose: the row has to absorb the words the advice asks for without
    # spilling the last one into a new row, which is the stub it was sent to remove
    assert render.MIN_LINE_FILL < render.TARGET_LINE_FILL < 1


def test_line_fill_reports_but_never_fails_untailored(master, tmp_path):
    master["roles"][0]["bullets"][0]["claim"] = stub_bullet()
    _, results = render.render(render.page_model(master), tmp_path, budget=False)
    assert "line-fill" not in failed(results)
    assert "across two teams" in {n: d for n, _, d in results}["line-fill (info)"]


def test_long_heading_never_makes_its_date_subline_a_stub(master, tmp_path):
    # a title this long fills its line (92%), so judging the break by how full the line looks
    # calls the "\"-forced subline a wrap. The tailorer cannot fix dates, so that deadlocks it.
    master["roles"][1]["title"] = "Software Engineer, Design Systems and Component Platform Group"
    model = render.page_model(master)
    path, _ = render.render(model, tmp_path, budget=False)
    with pymupdf.open(path) as doc:
        assert not [r for r in render.runts(doc, model) if "2019" in r["text"]]


def summary_ending_in_a_stub(font: str) -> str:
    """Grown a word at a time until it spills - which word that is depends on the font, so
    the summary is measured into shape rather than written out and left to rot."""
    words = ("Senior frontend engineer shipping Vue and TypeScript product UI with LLM-backed "
             "search over support docs and the eval harnesses behind them").split()
    out = []
    for word in words:
        out.append(word)
        lines, fill = measure.fit(font, " ".join(out), measure.SUMMARY)
        if lines == 2 and fill < render.MIN_LINE_FILL:
            return " ".join(out)
    raise AssertionError(f"no stub reachable in {font} from these words")


def test_summary_stub_is_seen_in_its_narrower_column(master, tmp_path):
    # resume.typ holds the summary to 90%, so its lines stop short of the column even when
    # full: judging the break by fill against the full column makes summary stubs invisible
    master["summary"] = summary_ending_in_a_stub(typeface.DEFAULT)
    model = render.page_model(master)
    path, _ = render.render(model, tmp_path, budget=False)
    with pymupdf.open(path) as doc:
        stub, = render.runts(doc, model)
    assert stub["text"] == master["summary"].rsplit(" ", 1)[1] and stub["fixable"]


def test_spilling_past_two_pages_fails_pages(master, tmp_path):
    # how many pages 12 copies of the roles fill depends on the font, so assert the rule the
    # gate states - past MAX_PAGES - not a page count only one family produces
    master["roles"] *= 12
    for n, role in enumerate(master["roles"]):
        role["id"] = f"{role['id']}-{n}"
    path, results = render.render(render.page_model(master), tmp_path, budget=True)
    with pymupdf.open(path) as doc:
        pages = doc.page_count
    assert pages > render.MAX_PAGES
    assert f"{pages} page(s)" in failed(results)["pages"]


def test_contact_line_reports_when_it_wraps(master, tmp_path):
    # a metro-area location is longer than a town, and the contact line is where that first shows
    master["contact"]["location"] = "Greater Springfield and Shelbyville Metropolitan Area"
    _, results = render.render(render.page_model(master), tmp_path, budget=False)
    detail = {n: d for n, _, d in results}["contact-line (info)"]
    assert "wraps to 2 rows" in detail
    assert "contact-line (info)" not in failed(results)


def test_contact_line_quiet_when_it_fits(master, tmp_path):
    _, results = render.render(render.page_model(master), tmp_path, budget=False)
    assert {n: d for n, _, d in results}["contact-line (info)"] == "fits one row"


def test_two_column_layout_fails_single_column(tmp_path):
    # right column written into the stream first: a parser reads across, a person reads down
    doc = pymupdf.open()
    page = doc.new_page()
    for x, side in ((320, "right"), (60, "left")):
        for y, line in ((100, "one"), (120, "two")):
            page.insert_text((x, y), f"{side} {line}")
    path = tmp_path / "two-column.pdf"
    doc.save(path)
    doc.close()
    assert render.tokens(render.pdf_text(path, sort=True)) != render.tokens(render.pdf_text(path, sort=False))


def test_contact_parts_carry_addresses_and_bare_host_gets_scheme(master):
    master["contact"]["links"] = ["linkedin.com/in/janedoe", "https://github.com/janedoe"]
    model = render.page_model(master)
    assert list(zip(model["contact"]["parts"], model["contact"]["part_urls"])) == [
        ("Springfield, IL", ""),
        ("jane@example.com", "mailto:jane@example.com"),
        ("+1 555 010 0100", "tel:+15550100100"),
        ("linkedin.com/in/janedoe", "https://linkedin.com/in/janedoe"),
        ("https://github.com/janedoe", "https://github.com/janedoe"),
    ]


def test_local_phone_keeps_its_digits_without_inventing_a_country_code(master):
    master["contact"]["phone"] = "(555) 010-0100"
    assert render.page_model(master)["contact"]["part_urls"][2] == "tel:5550100100"


def test_contact_links_reach_the_pdf_and_leave_the_text_layer_alone(master, tmp_path):
    master["contact"]["links"] = ["linkedin.com/in/janedoe"]
    model = render.page_model(master)
    path, results = render.render(model, tmp_path, budget=False)
    assert failed(results) == {}
    with pymupdf.open(path) as doc:
        targets = {link["uri"] for link in doc[0].get_links() if link.get("uri")}
        header = doc[0].get_text().splitlines()[1]
    assert targets == {
        "mailto:jane@example.com", "tel:+15550100100", "https://linkedin.com/in/janedoe",
    }
    assert header == render.SEP.join(render.page_model(master)["contact"]["parts"])


def test_part_without_an_address_stays_plain_text(master, tmp_path):
    master["contact"]["links"] = []
    master["contact"].pop("phone")
    model = render.page_model(master)
    assert model["contact"]["part_urls"] == ["", "mailto:jane@example.com"]
    path, results = render.render(model, tmp_path, budget=False)
    assert failed(results) == {}
    with pymupdf.open(path) as doc:
        assert [link["uri"] for link in doc[0].get_links()] == ["mailto:jane@example.com"]


def test_year_only_end_prints_years_on_both_ends(master):
    master["roles"][1].update(start="2019-06", end="2023")
    master["certifications"] = [{"name": "First Aid", "date": "2021"}, {"name": "CPR", "date": "2022-03"}]
    model = render.page_model(master)
    assert model["sections"][0]["entries"][1]["subline"] == "2019 - 2023"
    certs = next(s for s in model["sections"] if s["title"] == "Certifications")
    assert [l["text"] for l in certs["lines"]] == ["First Aid | 2021", "CPR | Mar 2022"]


def test_other_sections_follow_certifications_verbatim(master):
    master["certifications"] = [{"name": "First Aid"}]
    master["other"] = [{"heading": "Volunteer Work", "lines": ["Riverside Food Bank, driver, 2020 - 2022"]}]
    model = render.page_model(master)
    titles = [s["title"] for s in model["sections"]]
    assert titles[titles.index("Certifications") + 1] == "Volunteer Work"
    assert model["sections"][titles.index("Volunteer Work")]["lines"] == [{"text": "Riverside Food Bank, driver, 2020 - 2022"}]


def test_undated_project_renders_without_a_date(master):
    del master["projects"][0]["start"], master["projects"][0]["end"]
    project = render.page_model(master)["sections"][1]["entries"][0]
    assert project["subline"] is None


def test_education_leads_with_no_jobs_or_a_fresh_degree(master):
    today = render.date(2026, 9, 24)
    assert [s["title"] for s in render.page_model(master, today)["sections"]][0] == "Experience"
    master["education"][0]["end"] = "2026-05"
    master["roles"] = [{**master["roles"][0], "start": "2025-06"}]
    assert render.page_model(master, today)["sections"][0]["title"] == "Education"
    master["roles"][0]["start"] = "2023-06"  # three years of work: experience leads again
    assert render.page_model(master, today)["sections"][0]["title"] == "Experience"
    master["roles"] = []
    assert [s["title"] for s in render.page_model(master, today)["sections"]][:2] == ["Education", "Projects"]


def test_hide_year_leaves_the_graduation_year_off(master):
    master["education"][0]["hide_year"] = True
    education = next(s for s in render.page_model(master)["sections"] if s["title"] == "Education")
    assert education["entries"][0]["subline"] == "Bachelor of Science, Computer Science | Minor in Mathematics"


@pytest.mark.parametrize("written, printed", [
    ("BA", "Bachelor of Arts"), ("B.S. in Nursing", "Bachelor of Science in Nursing"), ("Ph.D.", "Doctor of Philosophy"),
    ("MBA", "Master of Business Administration"), ("Associate of Arts", "Associate of Arts"), ("GED", "GED"),
])
def test_degree_is_spelled_out_for_application_forms(written, printed):
    assert render.degree_name(written) == printed


def test_school_and_degree_read_back_on_their_own_lines(master, tmp_path):
    """One-line "BA, Field | School" came back from Workday as the school name: never again."""
    master["education"] = [{"institution": "Riverside State University", "degree": "BA",
                            "field": "Studio Art"},
                           {"institution": "Lakeview Community College", "degree": "AA", "field": "Graphic Design"}]
    path, results = render.render(render.page_model(master), tmp_path, budget=False)
    assert failed(results) == {}
    lines = [l.strip() for l in render.pdf_text(path, sort=True).splitlines() if l.strip()]
    at = lines.index("Riverside State University")
    assert lines[at + 1] == "Bachelor of Arts, Studio Art"
    assert lines[lines.index("Lakeview Community College") + 1] == "Associate of Arts, Graphic Design"


def test_entry_lines_gate_catches_a_merged_heading(master):
    model = render.page_model(master)
    reading = "State University Bachelor of Science, Computer Science | Minor in Mathematics | 2019"
    school = next(s for s in model["sections"] if s["title"] == "Education")
    assert render.unsplit_entries({"sections": [school]}, reading) == ["State University"]


def test_tailored_page_keeps_every_school(master):
    tailored = {"summary": None, "skills": [],
                "entries": [{"id": r["id"], "title_mirror": None, "bullets": []} for r in master["roles"]]}
    model = tailor.page_model(master, tailored)
    assert [e["heading"] for s in model["sections"] if s["title"] == "Education" for e in s["entries"]] == \
        [s["institution"] for s in master["education"]]


def test_career_break_sits_between_jobs_by_date_and_renders(master, tmp_path):
    master["roles"][1]["end"] = "2021-01"
    master["career_break"] = [{"reason": "Caring for a family member", "start": "2021-02", "end": "2023-01"}]
    entries = render.page_model(master)["sections"][0]["entries"]
    assert [e["heading"] for e in entries] == [
        "Senior Software Engineer", "Career break - Caring for a family member", "Software Engineer"]
    assert entries[1]["subline"] == "Feb 2021 - Jan 2023" and entries[1]["bullets"] == []
    _, results = render.render(render.page_model(master), tmp_path, budget=False)
    assert failed(results) == {}


@pytest.mark.parametrize("name, file", [
    ("José Núñez", "Jose_Nunez_Resume.pdf"),
    ("Zoë Renée O'Brien", "Zoe_Renee_OBrien_Resume.pdf"),
    ("李娜", "Resume.pdf"),
])
def test_file_name_folds_accents_and_falls_back(name, file):
    assert render.file_name({"contact": {"name": name}}) == file


def test_headline_prints_between_contact_and_summary(master, tmp_path):
    master["headline"] = "Software Engineer | Vue, TypeScript, LLM search"
    path, results = render.render(render.page_model(master), tmp_path, budget=False)
    assert failed(results) == {}
    assert dict((n, d) for n, _, d in results)["headline (info)"] == "fits one row"
    text = render.pdf_text(path, sort=True)
    assert text.index("jane@") < text.index(master["headline"]) < text.index(master["summary"][:30])


def vmock_failing_template(tmp_path, monkeypatch):
    """The page as VMock scored it 2026-09-24: navy headings letterspaced, a job's lead under its heading."""
    old = render.TEMPLATE.read_text(encoding="utf-8")
    old = old.replace("#text(size: 11.5pt, weight: 600)", '#text(size: 11.5pt, weight: 600, fill: rgb("#1F3A5F"), tracking: 0.08em)')
    old = old.replace("if first { first-gap }", "if false { first-gap }")
    template = tmp_path / "resume.typ"
    template.write_text(old, encoding="utf-8")
    monkeypatch.setattr(render, "TEMPLATE", template)


def test_vmock_presentation_failures_fail_their_gates(master, tmp_path, monkeypatch):
    vmock_failing_template(tmp_path, monkeypatch)
    _, results = render.render(render.page_model(master), tmp_path / "out", budget=False)
    found = failed(results)
    assert set(found) == {"split-words", "text-color", "heading-gap"}
    assert "EXPERIENCE" in found["split-words"] and "#1F3A5F" in found["text-color"]


def test_black_is_the_page_ink_and_navy_is_not():
    assert render.near_black(0x1A1A1A) and render.near_black(0x000000)
    assert not render.near_black(0x1F3A5F) and not render.near_black(0x0000EE)
