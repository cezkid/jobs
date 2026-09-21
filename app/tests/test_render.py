import copy

import pymupdf
import pytest
import typst

import cfg
from resume import measure, render, schema, typeface

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
    assert model["sections"][3]["lines"] == [{"text": "B.S., Computer Science | State University | Minor in Mathematics | 2019"}]
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
