import copy

import pymupdf
import pytest
import typst

import cfg
from resume import render, schema

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
        str(render.TEMPLATE), font_paths=[str(render.FONTS)], ignore_system_fonts=True,
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
        stub, = render.runts(doc)
    assert stub["text"] == "export tooling across two teams" and stub["fill"] < render.MIN_LINE_FILL
    # detail names the text and both ways out, so the writer never has to guess
    detail = failed(results)["line-fill"]
    assert stub["text"] in detail and f"cut {stub['cut']}" in detail and f"add ~{stub['add']}" in detail


def test_line_fill_reports_but_never_fails_untailored(master, tmp_path):
    master["roles"][0]["bullets"][0]["claim"] = stub_bullet()
    _, results = render.render(render.page_model(master), tmp_path, budget=False)
    assert "line-fill" not in failed(results)
    assert "across two teams" in {n: d for n, _, d in results}["line-fill (info)"]


def test_deliberate_break_after_short_line_is_not_a_stub(master, tmp_path):
    # entry heading, then the subline on its own row via "\": a short row that never wrapped
    model = render.page_model(master)
    path, _ = render.render(model, tmp_path, budget=False)
    with pymupdf.open(path) as doc:
        assert [r["text"] for r in render.runts(doc)] == []


def test_third_page_fails_pages(master, tmp_path):
    master["roles"] *= 12
    for n, role in enumerate(master["roles"]):
        role["id"] = f"{role['id']}-{n}"
    _, results = render.render(render.page_model(master), tmp_path, budget=True)
    assert "3 page(s)" in failed(results)["pages"]


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
