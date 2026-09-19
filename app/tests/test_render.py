import copy

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
    assert "#flags $cost_model *bold* @team <tag> [x]" in render.pdftotext(path, None)


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
